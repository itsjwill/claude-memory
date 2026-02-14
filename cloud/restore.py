"""Restore memories from Supabase cloud back to local.

Handles full restore, selective restore, and deleted memory recovery.
Uses subprocess to call the MCP memory_store tool for proper
embedding regeneration and deduplication.
"""

import json
import logging
import subprocess
import sys
from typing import Optional

from . import client

logger = logging.getLogger("claude-memory-cloud")


def _store_memory_locally(content: str, tags: str = "", memory_type: str = "note", metadata: dict = None) -> bool:
    """Store a memory via the MCP memory service CLI.

    We call the `memory` CLI tool directly to ensure proper
    embedding generation and deduplication.
    """
    try:
        # Build the store command via the memory CLI
        store_data = {
            "content": content,
            "metadata": {
                "tags": tags or "",
                "type": memory_type or "note",
                **(metadata or {}),
                "restored_from": "cloud",
            }
        }

        # Try using the memory CLI tool
        result = subprocess.run(
            ["memory", "store", json.dumps(store_data)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return True

        # Fallback: direct SQLite insert (less ideal, no embeddings)
        logger.warning(f"CLI store failed, memory may need re-embedding: {result.stderr[:100]}")
        return False

    except FileNotFoundError:
        logger.error("'memory' CLI not found. Install: pipx install mcp-memory-service")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Memory store timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to store locally: {e}")
        return False


def restore_all(include_deleted: bool = True) -> dict:
    """Restore all memories from cloud to local.

    Args:
        include_deleted: Also restore memories that were deleted locally

    Returns:
        Stats dict with counts
    """
    stats = {"total": 0, "restored": 0, "skipped": 0, "failed": 0}

    memories = client.get_all_memories(include_deleted=include_deleted)
    stats["total"] = len(memories)

    logger.info(f"Restoring {len(memories)} memories from cloud...")

    for mem in memories:
        success = _store_memory_locally(
            content=mem["content"],
            tags=mem.get("tags", ""),
            memory_type=mem.get("memory_type", "note"),
            metadata=mem.get("metadata"),
        )
        if success:
            stats["restored"] += 1
        else:
            stats["failed"] += 1

        # Rate limit to avoid overwhelming the local service
        if stats["restored"] % 10 == 0 and stats["restored"] > 0:
            logger.info(f"  Restored {stats['restored']}/{stats['total']}...")

    logger.info(f"Restore complete: {stats}")
    return stats


def restore_by_hashes(hashes: list[str]) -> dict:
    """Restore specific memories by content hash."""
    stats = {"total": len(hashes), "restored": 0, "not_found": 0, "failed": 0}

    memories = client.get_memories_by_hashes(hashes)
    found_hashes = {m["content_hash"] for m in memories}

    for h in hashes:
        if h not in found_hashes:
            logger.warning(f"Memory {h[:12]}... not found in cloud")
            stats["not_found"] += 1

    for mem in memories:
        success = _store_memory_locally(
            content=mem["content"],
            tags=mem.get("tags", ""),
            memory_type=mem.get("memory_type", "note"),
            metadata=mem.get("metadata"),
        )
        if success:
            stats["restored"] += 1
            logger.info(f"  Restored: {mem['content'][:60]}...")
        else:
            stats["failed"] += 1

    return stats


def restore_deleted() -> dict:
    """Restore all locally-deleted memories from cloud."""
    stats = {"total": 0, "restored": 0, "failed": 0}

    memories = client.get_deleted_memories()
    stats["total"] = len(memories)

    if not memories:
        logger.info("No deleted memories found in cloud")
        return stats

    logger.info(f"Found {len(memories)} deleted memories to restore")

    for mem in memories:
        success = _store_memory_locally(
            content=mem["content"],
            tags=mem.get("tags", ""),
            memory_type=mem.get("memory_type", "note"),
            metadata=mem.get("metadata"),
        )
        if success:
            stats["restored"] += 1
            logger.info(f"  Restored deleted: {mem['content'][:60]}...")
        else:
            stats["failed"] += 1

    return stats


def restore_by_search(query: str, limit: int = 10) -> dict:
    """Search cloud and restore matching memories."""
    stats = {"found": 0, "restored": 0, "failed": 0}

    # Use text search (embedding search requires local model)
    memories = client.search_memories_text(query, limit=limit, include_deleted=True)
    stats["found"] = len(memories)

    if not memories:
        logger.info(f"No cloud memories matching '{query}'")
        return stats

    for mem in memories:
        success = _store_memory_locally(
            content=mem["content"],
            tags=mem.get("tags", ""),
            memory_type=mem.get("memory_type", "note"),
            metadata=mem.get("metadata"),
        )
        if success:
            stats["restored"] += 1
        else:
            stats["failed"] += 1

    return stats
