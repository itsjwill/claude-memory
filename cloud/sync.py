"""Sync engine: Local SQLite -> Supabase cloud backup.

Reads the local mcp-memory-service SQLite database (read-only)
and syncs all memories + embeddings to Supabase.

Cloud NEVER deletes. If a memory is deleted locally, it gets
marked local_deleted=true in Supabase and logged to deletion_log.
"""

import logging
import sqlite3
import struct
import time
from pathlib import Path
from typing import Optional

from . import config
from . import client

logger = logging.getLogger("claude-memory-cloud")


def _open_local_db() -> sqlite3.Connection:
    """Open local SQLite database in read-only mode."""
    db_path = config.LOCAL_DB_PATH
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Local database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _deserialize_embedding(blob: bytes) -> Optional[list[float]]:
    """Deserialize sqlite-vec embedding blob to float list.

    sqlite-vec stores embeddings as packed float32 arrays.
    384 dimensions * 4 bytes = 1536 bytes.
    """
    if blob is None:
        return None

    try:
        num_floats = len(blob) // 4
        return list(struct.unpack(f"{num_floats}f", blob))
    except Exception as e:
        logger.warning(f"Failed to deserialize embedding ({len(blob)} bytes): {e}")
        return None


def _get_local_memories(conn: sqlite3.Connection, since_updated_at: float = 0) -> list[dict]:
    """Get memories from local DB that were updated after the given timestamp."""
    cursor = conn.cursor()

    query = """
        SELECT
            content_hash, content, tags, memory_type, metadata,
            created_at, updated_at, deleted_at
        FROM memories
        WHERE updated_at > ? OR (updated_at IS NULL AND created_at > ?)
        ORDER BY COALESCE(updated_at, created_at) ASC
    """
    cursor.execute(query, (since_updated_at, since_updated_at))

    memories = []
    for row in cursor.fetchall():
        mem = dict(row)
        # Parse metadata JSON
        if mem.get("metadata"):
            try:
                import json
                mem["metadata"] = json.loads(mem["metadata"])
            except (json.JSONDecodeError, TypeError):
                mem["metadata"] = {}
        else:
            mem["metadata"] = {}
        memories.append(mem)

    return memories


def _get_local_embeddings(conn: sqlite3.Connection, content_hashes: list[str]) -> dict[str, list[float]]:
    """Get embeddings for specific content hashes from local DB.

    sqlite-vec uses a virtual table. We query it by rowid which maps
    to the memories table via content_hash.
    """
    if not content_hashes:
        return {}

    embeddings = {}
    cursor = conn.cursor()

    # The memory_embeddings virtual table stores vectors
    # We need to find the mapping between content_hash and rowid
    for content_hash in content_hashes:
        try:
            # Try to get embedding via rowid lookup
            cursor.execute(
                "SELECT rowid FROM memories WHERE content_hash = ?",
                (content_hash,)
            )
            row = cursor.fetchone()
            if row is None:
                continue

            rowid = row[0]

            # Query the vec0 virtual table
            cursor.execute(
                "SELECT embedding FROM memory_embeddings WHERE rowid = ?",
                (rowid,)
            )
            emb_row = cursor.fetchone()
            if emb_row and emb_row[0]:
                embedding = _deserialize_embedding(emb_row[0])
                if embedding:
                    embeddings[content_hash] = embedding
        except Exception as e:
            # Virtual table may not exist or have different schema
            logger.debug(f"Could not get embedding for {content_hash[:12]}: {e}")

    return embeddings


def _get_all_local_hashes(conn: sqlite3.Connection) -> set[str]:
    """Get all content hashes currently in local DB."""
    cursor = conn.cursor()
    cursor.execute("SELECT content_hash FROM memories WHERE deleted_at IS NULL")
    return {row[0] for row in cursor.fetchall()}


def _get_locally_deleted(conn: sqlite3.Connection) -> list[str]:
    """Get content hashes of soft-deleted memories."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT content_hash FROM memories WHERE deleted_at IS NOT NULL")
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []


def sync_once() -> dict:
    """Run a single sync cycle. Returns sync statistics."""
    stats = {
        "new_memories": 0,
        "updated_memories": 0,
        "deleted_marked": 0,
        "graph_edges": 0,
        "errors": 0,
        "duration_ms": 0,
    }

    start = time.time()

    try:
        conn = _open_local_db()
    except FileNotFoundError as e:
        logger.error(str(e))
        return {**stats, "errors": 1, "error_message": str(e)}

    try:
        # Get last sync state
        sync_state = client.get_sync_state()
        last_sync = sync_state.get("last_sync_updated_at", 0) or 0

        client.update_sync_state(last_sync, sync_state.get("memories_synced", 0), "syncing")

        # Get changed memories since last sync
        memories = _get_local_memories(conn, since_updated_at=last_sync)
        logger.info(f"Found {len(memories)} memories to sync (since {last_sync})")

        if not memories:
            # Check for deletions even if no new memories
            deleted_hashes = _get_locally_deleted(conn)
            for h in deleted_hashes:
                if client.mark_locally_deleted(h, "local_soft_delete"):
                    stats["deleted_marked"] += 1

            client.update_sync_state(last_sync, sync_state.get("memories_synced", 0), "idle")
            stats["duration_ms"] = int((time.time() - start) * 1000)
            return stats

        # Get embeddings for these memories
        hashes = [m["content_hash"] for m in memories]
        embeddings = _get_local_embeddings(conn, hashes)
        logger.info(f"Retrieved {len(embeddings)} embeddings")

        # Prepare batch
        batch = []
        max_updated_at = last_sync
        for mem in memories:
            row = {
                "content_hash": mem["content_hash"],
                "content": mem["content"],
                "tags": mem.get("tags"),
                "memory_type": mem.get("memory_type"),
                "metadata": mem.get("metadata", {}),
                "created_at": mem.get("created_at"),
                "updated_at": mem.get("updated_at"),
            }

            if mem["content_hash"] in embeddings:
                row["embedding"] = embeddings[mem["content_hash"]]

            # Handle soft-deleted memories
            if mem.get("deleted_at") is not None:
                # Don't sync to memories table, just mark deletion
                if client.mark_locally_deleted(mem["content_hash"], "local_soft_delete"):
                    stats["deleted_marked"] += 1
                continue

            batch.append(row)

            # Track the latest updated_at
            updated = mem.get("updated_at") or mem.get("created_at") or 0
            if updated > max_updated_at:
                max_updated_at = updated

        # Batch upsert to Supabase
        if batch:
            success, failed = client.upsert_memories_batch(batch)
            stats["new_memories"] = success
            stats["errors"] = failed
            logger.info(f"Synced {success} memories ({failed} failed)")

        # Sync memory graph associations
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source_hash, target_hash, similarity, relationship_type, metadata
                FROM memory_graph
            """)
            for row in cursor.fetchall():
                row_dict = dict(row)
                metadata = row_dict.get("metadata")
                if metadata:
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                if client.upsert_graph_edge(
                    row_dict["source_hash"],
                    row_dict["target_hash"],
                    row_dict.get("similarity", 0),
                    row_dict.get("relationship_type", "semantic"),
                    metadata,
                ):
                    stats["graph_edges"] += 1
        except Exception as e:
            logger.debug(f"Graph sync skipped: {e}")

        # Update sync state
        total_synced = (sync_state.get("memories_synced", 0) or 0) + stats["new_memories"]
        client.update_sync_state(max_updated_at, total_synced, "idle")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        stats["errors"] += 1
        stats["error_message"] = str(e)
        try:
            client.update_sync_state(0, 0, f"error: {str(e)[:100]}")
        except Exception:
            pass
    finally:
        conn.close()

    stats["duration_ms"] = int((time.time() - start) * 1000)
    return stats


def sync_daemon():
    """Run continuous sync loop."""
    logger.info(f"Starting sync daemon (interval: {config.SYNC_INTERVAL}s)")
    logger.info(f"Device: {config.DEVICE_NAME}")
    logger.info(f"Local DB: {config.LOCAL_DB_PATH}")
    logger.info(f"Cloud: {config.SUPABASE_URL}")

    # Initial full sync
    logger.info("Running initial sync...")
    stats = sync_once()
    logger.info(f"Initial sync: {stats}")

    # Continuous loop
    while True:
        time.sleep(config.SYNC_INTERVAL)
        try:
            stats = sync_once()
            if stats["new_memories"] > 0 or stats["deleted_marked"] > 0:
                logger.info(
                    f"Sync: +{stats['new_memories']} memories, "
                    f"{stats['deleted_marked']} deletions marked, "
                    f"{stats['duration_ms']}ms"
                )
        except KeyboardInterrupt:
            logger.info("Sync daemon stopped")
            break
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")
            time.sleep(30)  # Back off on errors
