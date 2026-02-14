# Claude Memory

**Persistent memory for Claude Code.** Never lose conversation context again.

Claude Memory automatically captures important context during your sessions, recalls it when you start new ones, and backs everything up to the cloud. No manual saving required. Total recall, forever.

## Features

- **Auto-Capture**: Claude automatically saves decisions, learnings, client info, and patterns
- **Semantic Search**: Find memories by meaning, not just keywords
- **Session Summaries**: Automatic end-of-session summaries
- **Context Recall**: Relevant memories loaded at session start
- **Silent Operation**: Captures happen in the background without interrupting your flow
- **Cloud Backup**: Supabase sync ensures you never lose a memory (optional)
- **Never Delete**: Consolidation creates summaries without destroying originals
- **Cloud Recall**: Search cloud for memories deleted or compressed locally

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/itsjwill/claude-memory/main/install.sh | bash
```

Or clone and run locally:

```bash
git clone https://github.com/itsjwill/claude-memory.git
cd claude-memory
./install.sh
```

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [MCP Memory Service](https://github.com/docsion/mcp-memory-service) (installed automatically)
- [Supabase](https://supabase.com) account (optional, for cloud backup - free tier works)

## How It Works

### 1. Auto-Capture (During Sessions)

Claude automatically detects and captures:

| Trigger | Example |
|---------|---------|
| Decisions | "Let's go with PostgreSQL" |
| Learnings | "I learned that..." |
| Errors Fixed | "The bug was caused by..." |
| Client Info | "Pinnacle's email is..." |
| Preferences | "I prefer tabs over spaces" |
| References | "API key is in .env" |
| Patterns | "We always use..." |

No action needed - Claude captures silently in the background.

### 2. Manual Capture

Use `/capture` when you want to explicitly save something:

```
/capture "Important architectural decision about the database"
/capture "Client prefers weekly updates" --type preference --tags client,process
```

### 3. Session Summaries

Claude automatically invokes `/session-end` when you're wrapping up:

```
User: "Thanks, that's all for now"
Claude: [silently saves session summary with outcomes, decisions, open items]
```

You can also invoke manually: `/session-end`

### 4. Session Recall

At the start of each session, Claude searches for relevant memories based on:
- Current project/directory
- Recent activity (last 7 days)
- Related topics
- Cloud backup (if local results are sparse)

### 5. Search Memories

Find stored memories anytime:

```
memory_search(query="database decisions", limit=10)
memory_list(tags=["client"])
```

## Cloud Backup (Supabase)

Cloud backup ensures **total recall** - every memory is preserved forever in the cloud, even if your local database gets compacted or corrupted.

### Why Cloud Backup?

The local memory service has a consolidation pipeline that can:
- **Compress** memories (losing 50-70% of content)
- **Delete** low-quality memories after 30-90 days
- **Merge** similar memories, discarding originals

With cloud backup enabled:
- Every memory syncs to Supabase every 5 minutes
- Cloud **NEVER deletes** - deleted memories are just marked
- Full content preserved in `deletion_log` as audit trail
- Restore any memory from cloud at any time

### Setup Cloud Backup

```bash
cd claude-memory
./setup-cloud.sh
```

This will:
1. Install Python dependencies (`supabase`, `python-dotenv`, `numpy`)
2. Prompt for your Supabase project URL and service key
3. Create the database schema
4. Run initial sync of all memories
5. Install a background daemon (syncs every 5 minutes)

### Cloud Commands

```bash
# Check sync status
python3 -m cloud.cli status

# Manual sync
python3 -m cloud.cli sync --once

# Search cloud memories
python3 -m cloud.cli search "trading bot architecture"

# Restore all from cloud (disaster recovery)
python3 -m cloud.cli restore --all

# Restore deleted memories
python3 -m cloud.cli restore --deleted

# Non-destructive summarization
python3 -m cloud.cli summarize --dry-run
```

### Cloud Recall Skill

Use `/cloud-recall` to search the cloud when local results are missing:

```
/cloud-recall "API authentication decision"
```

This searches Supabase for memories that may have been deleted or compressed locally.

## Memory Types

| Type | Use Case |
|------|----------|
| `decision` | Architectural and technical choices |
| `pattern` | Reusable code or workflow patterns |
| `learning` | New knowledge discovered |
| `preference` | User preferences |
| `client` | Client-specific information |
| `gotcha` | Pitfalls and warnings |
| `reference` | File paths, API locations, credentials |

## Architecture

```
Claude Code
  ├── Skills (capture, session-start, session-end, cloud-recall)
  ├── MCP Memory Service (local SQLite + embeddings)
  │     └── Fast semantic search (~5ms)
  └── Cloud Sync (Supabase)
        ├── Postgres + pgvector (permanent storage)
        ├── Never deletes (only marks local_deleted)
        ├── Deletion audit log (full content preserved)
        └── Background daemon (every 5 min)
```

## Configuration

After installation, memories are stored in:
- **Primary**: MCP Memory Service (SQLite with embeddings)
- **Cloud**: Supabase Postgres + pgvector (optional, never deletes)
- **Quick Reference**: `~/.claude/projects/*/memory/MEMORY.md`

Cloud config: `~/.claude-memory-cloud.env`

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/itsjwill/claude-memory/main/uninstall.sh | bash
```

Or manually:

```bash
rm -rf ~/.claude/skills/capture
rm -rf ~/.claude/skills/cloud-recall
# Memories in MCP service and Supabase are preserved
```

## How It's Built

Claude Memory uses:
- **Claude Code Skills**: Custom skills with YAML frontmatter
- **MCP Memory Service**: SQLite-vec for semantic search with embeddings
- **Supabase**: Postgres + pgvector for permanent cloud storage
- **MEMORY.md**: Human-readable quick reference file
- **launchd**: Background daemon for automatic sync (macOS)

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT - See [LICENSE](LICENSE)
