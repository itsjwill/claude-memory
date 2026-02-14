"""Non-destructive summarization engine.

Creates NEW summary memories from clusters of related memories.
Originals are NEVER deleted or modified - summaries are purely additive.

Summary memories are linked to their source memories via the
`summarized_from` field containing source content hashes.
"""

import json
import logging
import sqlite3
import struct
from collections import defaultdict
from pathlib import Path
from typing import Optional

from . import config
from . import client

logger = logging.getLogger("claude-memory-cloud")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cluster_memories(memories: list[dict], threshold: float = 0.75) -> list[list[dict]]:
    """Simple greedy clustering by cosine similarity.

    Groups memories where similarity > threshold.
    Only clusters memories that have embeddings.
    """
    with_embeddings = [m for m in memories if m.get("embedding")]
    if not with_embeddings:
        return []

    assigned = set()
    clusters = []

    for i, mem_a in enumerate(with_embeddings):
        if i in assigned:
            continue

        cluster = [mem_a]
        assigned.add(i)

        for j, mem_b in enumerate(with_embeddings):
            if j in assigned:
                continue

            sim = _cosine_similarity(mem_a["embedding"], mem_b["embedding"])
            if sim >= threshold:
                cluster.append(mem_b)
                assigned.add(j)

        # Only create summaries for clusters of 3+ memories
        if len(cluster) >= 3:
            clusters.append(cluster)

    return clusters


def _generate_summary(cluster: list[dict]) -> str:
    """Generate a summary from a cluster of related memories.

    Preserves key information from all memories in the cluster.
    """
    # Collect all content
    contents = [m["content"] for m in cluster]

    # Collect all unique tags
    all_tags = set()
    for m in cluster:
        if m.get("tags"):
            for tag in m["tags"].split(","):
                tag = tag.strip()
                if tag:
                    all_tags.add(tag)

    # Collect memory types
    types = set(m.get("memory_type", "note") for m in cluster)

    # Build summary
    lines = [
        f"[SUMMARY of {len(cluster)} related memories]",
        f"Types: {', '.join(sorted(types))}",
        f"Tags: {', '.join(sorted(all_tags))}" if all_tags else "",
        "",
        "Key points:",
    ]

    for i, content in enumerate(contents, 1):
        # Keep first 200 chars of each memory
        truncated = content[:200].strip()
        if len(content) > 200:
            truncated += "..."
        lines.append(f"  {i}. {truncated}")

    return "\n".join(line for line in lines if line is not None)


def summarize(
    similarity_threshold: float = 0.75,
    min_cluster_size: int = 3,
    dry_run: bool = False,
) -> dict:
    """Run non-destructive summarization.

    1. Reads all memories from cloud (with embeddings)
    2. Clusters semantically similar memories
    3. Creates NEW summary memories
    4. Links summaries to originals via summarized_from
    5. NEVER touches or deletes originals

    Args:
        similarity_threshold: Min cosine similarity for clustering (0-1)
        min_cluster_size: Min memories per cluster to create summary
        dry_run: If True, only show what would be created

    Returns:
        Stats dict
    """
    stats = {
        "total_memories": 0,
        "clusters_found": 0,
        "summaries_created": 0,
        "memories_covered": 0,
        "dry_run": dry_run,
    }

    # Get all active memories from cloud
    memories = client.get_all_memories(include_deleted=False)
    stats["total_memories"] = len(memories)

    if len(memories) < min_cluster_size:
        logger.info(f"Only {len(memories)} memories - need at least {min_cluster_size} for summarization")
        return stats

    # Filter out existing summaries (don't summarize summaries)
    non_summaries = [m for m in memories if not m.get("is_summary")]

    # Cluster by semantic similarity
    clusters = _cluster_memories(non_summaries, threshold=similarity_threshold)
    stats["clusters_found"] = len(clusters)

    if not clusters:
        logger.info("No clusters found above similarity threshold")
        return stats

    logger.info(f"Found {len(clusters)} clusters to summarize")

    for i, cluster in enumerate(clusters):
        source_hashes = [m["content_hash"] for m in cluster]
        summary_content = _generate_summary(cluster)

        # Collect tags from all cluster members
        all_tags = set()
        for m in cluster:
            if m.get("tags"):
                for tag in m["tags"].split(","):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)
        all_tags.add("auto-summary")

        if dry_run:
            logger.info(f"\n--- Cluster {i+1} ({len(cluster)} memories) ---")
            logger.info(f"Tags: {', '.join(sorted(all_tags))}")
            logger.info(f"Summary preview:\n{summary_content[:300]}...")
            stats["memories_covered"] += len(cluster)
            continue

        # Create summary in cloud
        import hashlib
        summary_hash = hashlib.sha256(summary_content.encode()).hexdigest()[:32]

        success = client.upsert_memory(
            content_hash=f"summary_{summary_hash}",
            content=summary_content,
            tags=",".join(sorted(all_tags)),
            memory_type="pattern",
            metadata={
                "is_summary": True,
                "summarized_from": source_hashes,
                "cluster_size": len(cluster),
                "source": "non_destructive_summarizer",
            },
        )

        # Also update the cloud record to mark it as a summary
        if success:
            try:
                _client = client._get_client()
                _client.table("memories").update({
                    "is_summary": True,
                    "summarized_from": source_hashes,
                }).eq("content_hash", f"summary_{summary_hash}").execute()
            except Exception:
                pass

            stats["summaries_created"] += 1
            stats["memories_covered"] += len(cluster)
            logger.info(f"  Created summary for cluster {i+1} ({len(cluster)} memories)")

    return stats
