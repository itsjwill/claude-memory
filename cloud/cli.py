#!/usr/bin/env python3
"""CLI for Claude Memory Cloud Sync.

Usage:
    claude-memory-cloud sync --daemon     # Background continuous sync
    claude-memory-cloud sync --once       # One-shot sync
    claude-memory-cloud restore --all     # Full cloud -> local restore
    claude-memory-cloud restore --hash X  # Restore specific memory
    claude-memory-cloud restore --deleted # Restore locally-deleted memories
    claude-memory-cloud search "query"    # Search cloud memories
    claude-memory-cloud status            # Show sync health + counts
    claude-memory-cloud summarize         # Non-destructive summarization
    claude-memory-cloud setup             # Interactive Supabase setup
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("claude-memory-cloud")


def cmd_sync(args):
    """Sync local memories to cloud."""
    from . import config
    if not config.is_configured():
        print("Supabase not configured. Run: claude-memory-cloud setup")
        sys.exit(1)

    from . import sync

    if args.daemon:
        print(f"Starting sync daemon (interval: {config.SYNC_INTERVAL}s)...")
        print(f"Device: {config.DEVICE_NAME}")
        print(f"Local DB: {config.LOCAL_DB_PATH}")
        print(f"Cloud: {config.SUPABASE_URL}")
        print("Press Ctrl+C to stop.\n")
        sync.sync_daemon()
    else:
        print("Running one-shot sync...")
        stats = sync.sync_once()
        print(f"\nSync complete:")
        print(f"  New/updated: {stats['new_memories']}")
        print(f"  Deletions marked: {stats['deleted_marked']}")
        print(f"  Graph edges: {stats['graph_edges']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {stats['duration_ms']}ms")
        if stats.get("error_message"):
            print(f"  Error: {stats['error_message']}")


def cmd_restore(args):
    """Restore memories from cloud to local."""
    from . import config
    if not config.is_configured():
        print("Supabase not configured. Run: claude-memory-cloud setup")
        sys.exit(1)

    from . import restore

    if args.all:
        print("Restoring ALL memories from cloud...")
        stats = restore.restore_all(include_deleted=True)
    elif args.deleted:
        print("Restoring locally-deleted memories from cloud...")
        stats = restore.restore_deleted()
    elif args.hash:
        hashes = args.hash.split(",")
        print(f"Restoring {len(hashes)} memories by hash...")
        stats = restore.restore_by_hashes(hashes)
    elif args.search:
        print(f"Searching and restoring: '{args.search}'...")
        stats = restore.restore_by_search(args.search, limit=args.limit)
    else:
        print("Specify --all, --deleted, --hash, or --search")
        sys.exit(1)

    print(f"\nRestore complete: {json.dumps(stats, indent=2)}")


def cmd_search(args):
    """Search cloud memories."""
    from . import config
    if not config.is_configured():
        print("Supabase not configured. Run: claude-memory-cloud setup")
        sys.exit(1)

    from . import client

    query = " ".join(args.query)
    print(f"Searching cloud for: '{query}'")
    print(f"Include deleted: {args.include_deleted}\n")

    results = client.search_memories_text(
        query,
        limit=args.limit,
        include_deleted=args.include_deleted,
    )

    if not results:
        print("No results found.")
        return

    for i, mem in enumerate(results, 1):
        deleted_tag = " [DELETED LOCALLY]" if mem.get("local_deleted") else ""
        summary_tag = " [SUMMARY]" if mem.get("is_summary") else ""
        print(f"--- {i}. {mem.get('memory_type', 'note')}{deleted_tag}{summary_tag} ---")
        print(f"Hash: {mem['content_hash'][:16]}...")
        print(f"Tags: {mem.get('tags', 'none')}")
        content = mem["content"]
        if len(content) > 300:
            content = content[:300] + "..."
        print(f"Content: {content}")
        print()

    print(f"Found {len(results)} results.")


def cmd_status(args):
    """Show sync status and cloud stats."""
    from . import config

    print("=" * 50)
    print("  Claude Memory Cloud Status")
    print("=" * 50)
    print()

    # Config
    cfg = config.get_config_summary()
    print(f"Configuration:")
    print(f"  Supabase URL:   {cfg['supabase_url']}")
    print(f"  Service Key:    {cfg['supabase_key']}")
    print(f"  Local DB:       {cfg['local_db_path']}")
    print(f"  DB exists:      {'yes' if cfg['local_db_exists'] else 'NO'}")
    print(f"  Device:         {cfg['device_name']}")
    print(f"  Sync interval:  {cfg['sync_interval']}s")
    print(f"  Configured:     {'yes' if cfg['configured'] else 'NO'}")
    print()

    if not cfg["configured"]:
        print("Run 'claude-memory-cloud setup' to configure Supabase.")
        return

    # Cloud stats
    from . import client
    stats = client.get_cloud_stats()
    if "error" in stats:
        print(f"Cloud error: {stats['error']}")
        return

    print(f"Cloud Storage:")
    print(f"  Total memories:    {stats['total_memories']}")
    print(f"  Active:            {stats['active_memories']}")
    print(f"  Deleted locally:   {stats['locally_deleted']}")
    print(f"  Summaries:         {stats['summaries']}")
    print(f"  Graph edges:       {stats['graph_edges']}")
    print(f"  Deletion log:      {stats['deletion_log_entries']}")
    print()

    # Sync state
    sync_state = client.get_sync_state()
    print(f"Sync State:")
    print(f"  Last sync:         {sync_state.get('last_sync_at', 'never')}")
    print(f"  Memories synced:   {sync_state.get('memories_synced', 0)}")
    print(f"  Status:            {sync_state.get('status', 'unknown')}")

    # Local stats
    if cfg["local_db_exists"]:
        import sqlite3
        try:
            conn = sqlite3.connect(f"file:{cfg['local_db_path']}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL")
            local_count = cursor.fetchone()[0]
            conn.close()
            print()
            print(f"Local Storage:")
            print(f"  Active memories:   {local_count}")

            # Compare
            if stats["total_memories"] > 0:
                cloud_only = stats["total_memories"] - local_count
                if cloud_only > 0:
                    print(f"  Cloud-only:        {cloud_only} (preserved from deletion)")
        except Exception as e:
            print(f"\nLocal DB read error: {e}")


def cmd_summarize(args):
    """Run non-destructive summarization."""
    from . import config
    if not config.is_configured():
        print("Supabase not configured. Run: claude-memory-cloud setup")
        sys.exit(1)

    from . import summarize

    print(f"Running non-destructive summarization...")
    print(f"  Similarity threshold: {args.threshold}")
    print(f"  Min cluster size: {args.min_cluster}")
    print(f"  Dry run: {args.dry_run}")
    print()

    stats = summarize.summarize(
        similarity_threshold=args.threshold,
        min_cluster_size=args.min_cluster,
        dry_run=args.dry_run,
    )

    print(f"\nSummarization complete:")
    print(f"  Total memories:    {stats['total_memories']}")
    print(f"  Clusters found:    {stats['clusters_found']}")
    print(f"  Summaries created: {stats['summaries_created']}")
    print(f"  Memories covered:  {stats['memories_covered']}")
    if stats.get("dry_run"):
        print("  (dry run - no changes made)")


def cmd_setup(args):
    """Interactive Supabase setup."""
    from . import config

    print("=" * 50)
    print("  Claude Memory Cloud Setup")
    print("=" * 50)
    print()
    print("You need a Supabase project (free tier works).")
    print("1. Go to https://supabase.com and create a project")
    print("2. Go to Project Settings > API")
    print("3. Copy the Project URL and service_role key")
    print()

    url = input("Supabase Project URL: ").strip()
    key = input("Supabase service_role key: ").strip()

    if not url or not key:
        print("Both URL and key are required.")
        sys.exit(1)

    # Write env file
    env_path = config.ENV_FILE_PATH
    env_content = f"""# Claude Memory Cloud Configuration
# Generated by setup-cloud

SUPABASE_URL={url}
SUPABASE_SERVICE_KEY={key}
CLAUDE_MEMORY_DEVICE_NAME={config._get_device_name()}
CLAUDE_MEMORY_SYNC_INTERVAL=300
CLAUDE_MEMORY_SYNC_ENABLED=true
"""

    env_path.write_text(env_content)
    print(f"\nCredentials saved to {env_path}")

    # Reload config
    import importlib
    importlib.reload(config)

    # Test connection
    print("\nTesting Supabase connection...")
    try:
        # Re-import with new config
        from supabase import create_client
        test_client = create_client(url, key)
        # Try a simple query
        test_client.table("memories").select("id").limit(1).execute()
        print("Connection successful!")
        tables_exist = True
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            tables_exist = False
            print("Connection successful! (tables not created yet)")
        else:
            print(f"Connection test: {e}")
            tables_exist = False

    # Create tables
    if not tables_exist:
        print("\nCreating database tables...")
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            schema_sql = schema_path.read_text()
            print("Run this SQL in your Supabase SQL Editor:")
            print("  1. Go to your Supabase dashboard")
            print("  2. Click 'SQL Editor' in the sidebar")
            print("  3. Paste the contents of cloud/schema.sql")
            print("  4. Click 'Run'")
            print(f"\n  Schema file: {schema_path}")
        else:
            print(f"Schema file not found: {schema_path}")

    # Update mcp.json to disable consolidation
    print("\nDisabling destructive consolidation...")
    mcp_config_path = Path.home() / ".mcp.json"
    if mcp_config_path.exists():
        try:
            mcp_config = json.loads(mcp_config_path.read_text())
            if "mcpServers" in mcp_config and "memory-service" in mcp_config["mcpServers"]:
                ms = mcp_config["mcpServers"]["memory-service"]
                if "env" not in ms:
                    ms["env"] = {}
                ms["env"]["MCP_CONSOLIDATION_ENABLED"] = "false"
                mcp_config_path.write_text(json.dumps(mcp_config, indent=2))
                print(f"Updated {mcp_config_path} - consolidation disabled")
            else:
                print(f"memory-service not found in {mcp_config_path}")
        except Exception as e:
            print(f"Could not update mcp.json: {e}")
            print(f"Manually add to {mcp_config_path}:")
            print('  "env": { "MCP_CONSOLIDATION_ENABLED": "false" }')

    # Run initial sync
    print("\nRunning initial sync...")
    try:
        from . import sync
        stats = sync.sync_once()
        print(f"Synced {stats['new_memories']} memories to cloud!")
    except Exception as e:
        print(f"Initial sync will run on next daemon start: {e}")

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Run the schema SQL in Supabase SQL Editor")
    print("  2. Start sync: python3 -m cloud.cli sync --daemon")
    print("  3. Or install the background daemon:")
    print("     cp com.claude-memory.sync.plist ~/Library/LaunchAgents/")
    print("     launchctl load ~/Library/LaunchAgents/com.claude-memory.sync.plist")


def main():
    parser = argparse.ArgumentParser(
        prog="claude-memory-cloud",
        description="Claude Memory Cloud Sync - Supabase backup for total recall",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync memories to cloud")
    sync_parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon")
    sync_parser.add_argument("--once", action="store_true", default=True, help="Run once (default)")

    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore from cloud")
    restore_parser.add_argument("--all", action="store_true", help="Restore all memories")
    restore_parser.add_argument("--deleted", action="store_true", help="Restore deleted memories")
    restore_parser.add_argument("--hash", type=str, help="Restore by hash (comma-separated)")
    restore_parser.add_argument("--search", type=str, help="Search and restore")
    restore_parser.add_argument("--limit", type=int, default=10, help="Max results for search")

    # search
    search_parser = subparsers.add_parser("search", help="Search cloud memories")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument("--include-deleted", action="store_true", help="Include deleted")

    # status
    subparsers.add_parser("status", help="Show sync status")

    # summarize
    sum_parser = subparsers.add_parser("summarize", help="Non-destructive summarization")
    sum_parser.add_argument("--threshold", type=float, default=0.75, help="Similarity threshold")
    sum_parser.add_argument("--min-cluster", type=int, default=3, help="Min cluster size")
    sum_parser.add_argument("--dry-run", action="store_true", help="Preview only")

    # setup
    subparsers.add_parser("setup", help="Interactive Supabase setup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "sync": cmd_sync,
        "restore": cmd_restore,
        "search": cmd_search,
        "status": cmd_status,
        "summarize": cmd_summarize,
        "setup": cmd_setup,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
