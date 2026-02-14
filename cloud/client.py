"""Supabase client for Claude Memory Cloud Sync.

Handles all CRUD operations against Supabase (Postgres + pgvector).
Cloud NEVER deletes - only marks local_deleted=true.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from . import config

logger = logging.getLogger("claude-memory-cloud")

# Lazy import supabase
_client = None


def _get_client():
    """Get or create Supabase client (lazy init)."""
    global _client
    if _client is None:
        if not config.is_configured():
            raise RuntimeError(
                "Supabase not configured. Run: setup-cloud.sh\n"
                f"Or set SUPABASE_URL and SUPABASE_SERVICE_KEY in {config.ENV_FILE_PATH}"
            )
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def upsert_memory(
    content_hash: str,
    content: str,
    tags: Optional[str] = None,
    memory_type: Optional[str] = None,
    metadata: Optional[dict] = None,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
    embedding: Optional[list] = None,
) -> bool:
    """Upsert a memory to Supabase. Returns True on success."""
    client = _get_client()

    data = {
        "content_hash": content_hash,
        "content": content,
        "tags": tags,
        "memory_type": memory_type,
        "metadata": metadata or {},
        "created_at": created_at,
        "updated_at": updated_at,
        "source_device": config.DEVICE_NAME,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "local_deleted": False,
    }

    if embedding is not None:
        data["embedding"] = embedding

    try:
        result = client.table("memories").upsert(
            data,
            on_conflict="content_hash"
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to upsert memory {content_hash[:12]}: {e}")
        return False


def upsert_memories_batch(memories: list[dict]) -> tuple[int, int]:
    """Batch upsert memories. Returns (success_count, fail_count)."""
    client = _get_client()
    success = 0
    failed = 0

    # Supabase handles batch upserts natively
    batch = []
    for mem in memories:
        row = {
            "content_hash": mem["content_hash"],
            "content": mem["content"],
            "tags": mem.get("tags"),
            "memory_type": mem.get("memory_type"),
            "metadata": mem.get("metadata", {}),
            "created_at": mem.get("created_at"),
            "updated_at": mem.get("updated_at"),
            "source_device": config.DEVICE_NAME,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "local_deleted": False,
        }
        if mem.get("embedding"):
            row["embedding"] = mem["embedding"]
        batch.append(row)

    # Process in chunks of 50 (Supabase limit)
    chunk_size = 50
    for i in range(0, len(batch), chunk_size):
        chunk = batch[i:i + chunk_size]
        try:
            client.table("memories").upsert(
                chunk,
                on_conflict="content_hash"
            ).execute()
            success += len(chunk)
        except Exception as e:
            logger.error(f"Batch upsert failed (chunk {i // chunk_size}): {e}")
            # Fall back to individual inserts for this chunk
            for row in chunk:
                try:
                    client.table("memories").upsert(
                        row,
                        on_conflict="content_hash"
                    ).execute()
                    success += 1
                except Exception as e2:
                    logger.error(f"Individual upsert failed {row['content_hash'][:12]}: {e2}")
                    failed += 1

    return success, failed


def mark_locally_deleted(content_hash: str, reason: str = "consolidation") -> bool:
    """Mark a memory as deleted locally (NEVER deletes from cloud).
    Also logs the full original to deletion_log for audit trail."""
    client = _get_client()

    try:
        # Get the full original before marking
        result = client.table("memories").select("*").eq(
            "content_hash", content_hash
        ).execute()

        if result.data:
            original = result.data[0]

            # Log to deletion_log (preserves forever)
            client.table("deletion_log").insert({
                "content_hash": content_hash,
                "original_content": original["content"],
                "original_tags": original.get("tags"),
                "original_type": original.get("memory_type"),
                "original_metadata": original.get("metadata"),
                "reason": reason,
                "device_name": config.DEVICE_NAME,
            }).execute()

        # Mark as locally deleted (NOT actual delete)
        client.table("memories").update({
            "local_deleted": True,
        }).eq("content_hash", content_hash).execute()

        return True
    except Exception as e:
        logger.error(f"Failed to mark deletion for {content_hash[:12]}: {e}")
        return False


def search_memories(
    query_embedding: list[float],
    limit: int = 10,
    include_deleted: bool = False,
) -> list[dict]:
    """Semantic search via pgvector cosine similarity."""
    client = _get_client()

    try:
        result = client.rpc("search_memories", {
            "query_embedding": query_embedding,
            "match_count": limit,
            "include_deleted": include_deleted,
        }).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Cloud search failed: {e}")
        # Fallback: text search
        return search_memories_text(str(query_embedding[:5]), limit, include_deleted)


def search_memories_text(
    query: str,
    limit: int = 10,
    include_deleted: bool = False,
) -> list[dict]:
    """Full-text search fallback (when embeddings not available)."""
    client = _get_client()

    try:
        q = client.table("memories").select("*").ilike("content", f"%{query}%")
        if not include_deleted:
            q = q.eq("local_deleted", False)
        result = q.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        return []


def get_all_memories(include_deleted: bool = True) -> list[dict]:
    """Get all memories from cloud (for restore)."""
    client = _get_client()
    all_memories = []
    offset = 0
    page_size = 1000

    while True:
        try:
            q = client.table("memories").select("*")
            if not include_deleted:
                q = q.eq("local_deleted", False)
            result = q.order("created_at").range(offset, offset + page_size - 1).execute()

            if not result.data:
                break
            all_memories.extend(result.data)
            if len(result.data) < page_size:
                break
            offset += page_size
        except Exception as e:
            logger.error(f"Failed to fetch memories (offset {offset}): {e}")
            break

    return all_memories


def get_memories_by_hashes(hashes: list[str]) -> list[dict]:
    """Get specific memories by content hash."""
    client = _get_client()

    try:
        result = client.table("memories").select("*").in_(
            "content_hash", hashes
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch by hashes: {e}")
        return []


def get_deleted_memories() -> list[dict]:
    """Get all locally-deleted memories (for restore)."""
    client = _get_client()

    try:
        result = client.table("memories").select("*").eq(
            "local_deleted", True
        ).order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch deleted memories: {e}")
        return []


def upsert_graph_edge(
    source_hash: str,
    target_hash: str,
    similarity: float,
    relationship_type: str = "semantic",
    metadata: Optional[dict] = None,
) -> bool:
    """Upsert a memory association edge."""
    client = _get_client()

    try:
        client.table("memory_graph").upsert({
            "source_hash": source_hash,
            "target_hash": target_hash,
            "similarity": similarity,
            "relationship_type": relationship_type,
            "metadata": metadata or {},
        }, on_conflict="source_hash,target_hash").execute()
        return True
    except Exception as e:
        logger.error(f"Failed to upsert graph edge: {e}")
        return False


def get_sync_state() -> dict:
    """Get the current sync state for this device."""
    client = _get_client()

    try:
        result = client.table("sync_state").select("*").eq(
            "device_name", config.DEVICE_NAME
        ).execute()

        if result.data:
            return result.data[0]
        return {
            "device_name": config.DEVICE_NAME,
            "last_sync_updated_at": 0,
            "memories_synced": 0,
            "status": "never_synced",
        }
    except Exception as e:
        logger.error(f"Failed to get sync state: {e}")
        return {"last_sync_updated_at": 0, "memories_synced": 0, "status": "error"}


def update_sync_state(last_sync_updated_at: float, memories_synced: int, status: str = "idle") -> bool:
    """Update sync state for this device."""
    client = _get_client()

    try:
        client.table("sync_state").upsert({
            "device_name": config.DEVICE_NAME,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "last_sync_updated_at": last_sync_updated_at,
            "memories_synced": memories_synced,
            "status": status,
        }, on_conflict="device_name").execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update sync state: {e}")
        return False


def get_cloud_stats() -> dict:
    """Get cloud memory statistics."""
    client = _get_client()

    try:
        total = client.table("memories").select("id", count="exact").execute()
        active = client.table("memories").select("id", count="exact").eq(
            "local_deleted", False
        ).execute()
        deleted = client.table("memories").select("id", count="exact").eq(
            "local_deleted", True
        ).execute()
        summaries = client.table("memories").select("id", count="exact").eq(
            "is_summary", True
        ).execute()
        edges = client.table("memory_graph").select("id", count="exact").execute()
        deletions = client.table("deletion_log").select("id", count="exact").execute()

        return {
            "total_memories": total.count or 0,
            "active_memories": active.count or 0,
            "locally_deleted": deleted.count or 0,
            "summaries": summaries.count or 0,
            "graph_edges": edges.count or 0,
            "deletion_log_entries": deletions.count or 0,
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {"error": str(e)}


def run_schema(schema_sql: str) -> bool:
    """Execute schema SQL against Supabase."""
    client = _get_client()

    # Split into individual statements
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]

    for stmt in statements:
        try:
            client.postgrest.session.headers.update({
                "Prefer": "return=minimal"
            })
            # Use the SQL endpoint via rpc
            client.rpc("exec_sql", {"query": stmt + ";"}).execute()
        except Exception:
            # Some statements may fail on retry (already exists), that's OK
            pass

    return True
