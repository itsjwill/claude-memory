# Claude Memory — Persistent Memory for Claude Code That Never Forgets

[![Stars](https://img.shields.io/github/stars/itsjwill/claude-memory?style=social)](https://github.com/itsjwill/claude-memory)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Updated](https://img.shields.io/badge/Updated-2026-blue.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-blueviolet.svg)]()

### Free alternative to Mem.ai, Notion AI Memory, Rewind AI, and Personal AI

> Give Claude Code photographic memory. Every decision, every learning, every client detail — captured automatically, recalled instantly, backed up forever. Zero manual work.

## What You Get

| Feature | What It Does | How It Works |
|---------|-------------|--------------|
| **Auto-Capture** | Saves decisions, learnings, errors, client info silently | Detects patterns in conversation, stores via MCP |
| **Session Recall** | Loads relevant context when you start a new session | Semantic search over recent memories + cloud fallback |
| **Cloud Backup** | Never lose a memory, even after local compaction | Supabase sync every 5 minutes, never deletes |
| **Semantic Search** | Find memories by meaning, not just keywords | SQLite-vec embeddings (all-MiniLM-L6-v2, 384d) |
| **Session Summaries** | Auto-saves outcomes when you wrap up | `/session-end` captures decisions, open items |
| **Cloud Recall** | Search cloud for memories deleted locally | `/cloud-recall` searches Supabase when local is empty |

## The Problem: Claude Code Forgets Everything

Every time you start a new Claude Code session, you start from scratch. Past decisions vanish. Client details disappear. Architectural choices you made yesterday are gone.

The built-in MCP Memory Service tries to help, but its consolidation pipeline **destroys your data**:

| What Happens | Data Lost | Timeline |
|-------------|-----------|----------|
| Compression | 50-70% of content stripped | Ongoing |
| Forgetting | Low-quality memories permanently deleted | 30-90 days |
| Clustering | Similar memories merged, originals destroyed | Ongoing |

**Claude Memory fixes all of this.** Auto-capture + cloud backup = total recall, forever.

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

**That's it.** Claude will start capturing memories automatically on your next session.

## How It Works

### 1. Auto-Capture (Zero Effort)

Claude detects and captures these patterns silently — no action needed:

| Trigger | Example | Memory Type |
|---------|---------|-------------|
| Decisions | "Let's go with PostgreSQL" | `decision` |
| Learnings | "I learned that..." | `learning` |
| Errors Fixed | "The bug was caused by..." | `gotcha` |
| Client Info | "Their email is..." | `client` |
| Preferences | "I prefer tabs over spaces" | `preference` |
| References | "API key is in .env" | `reference` |
| Patterns | "We always use..." | `pattern` |

### 2. Manual Capture

```bash
/capture "Important architectural decision about the database"
/capture "Client prefers weekly updates" --type preference --tags client,process
```

### 3. Session Summaries

```
User: "Thanks, that's all for now"
Claude: [silently saves session summary with outcomes, decisions, open items]
```

### 4. Session Recall

Every new session, Claude automatically searches for:
- Current project context
- Recent activity (last 7 days)
- Related decisions and learnings
- Cloud backup (when local results are sparse)

You pick up exactly where you left off. No context loss.

### 5. Search Memories

```python
memory_search(query="database decisions", limit=10)
memory_list(tags=["client"])
```

## Cloud Backup — Total Recall Forever

The local memory service has a 6-phase consolidation pipeline that **destroys your data**. Cloud backup to Supabase ensures you never lose a single memory.

### How Cloud Sync Works

```
Local SQLite (read-only) → Supabase (Postgres + pgvector)
                           ├── Syncs every 5 minutes
                           ├── NEVER deletes (only marks local_deleted)
                           ├── Full deletion audit log
                           └── Semantic search via pgvector
```

### Setup Cloud Backup (5 minutes)

```bash
cd claude-memory
./setup-cloud.sh
```

This will:
1. Install Python dependencies (`supabase`, `python-dotenv`, `numpy`)
2. Prompt for your Supabase project URL and service key
3. Create the database schema (4 tables + pgvector)
4. Run initial sync of all memories
5. Install background daemon (syncs every 5 minutes)

**Cost:** Free. Supabase free tier (500MB) is more than enough for years of memories.

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

When local search comes up empty, search the cloud:

```
/cloud-recall "API authentication decision"
```

Finds memories that were deleted or compressed locally. The cloud preserves everything forever.

## Cost Comparison

| Solution | Price | Auto-Capture | Cloud Backup | Semantic Search | Open Source |
|----------|-------|-------------|-------------|-----------------|------------|
| **Claude Memory** | **Free** | **Yes** | **Yes (Supabase free)** | **Yes** | **Yes** |
| Mem.ai | $15/mo | Partial | Yes | Yes | No |
| Notion AI | $10/mo | No | Yes | Partial | No |
| Rewind AI | $19/mo | Yes | Yes | Yes | No |
| Personal AI | $40/mo | Yes | Yes | Yes | No |

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

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service) (installed automatically)
- [Supabase](https://supabase.com) account (optional, for cloud backup — free tier works)

## Memory Types

| Type | Use Case | Example |
|------|----------|---------|
| `decision` | Architectural and technical choices | "Chose PostgreSQL over MongoDB for ACID compliance" |
| `pattern` | Reusable code or workflow patterns | "Always use factory pattern for service initialization" |
| `learning` | New knowledge discovered | "Rate limiting kicks in at 100 req/min" |
| `preference` | User preferences | "Prefer functional components over class components" |
| `client` | Client-specific information | "Pinnacle Title — $1,500/mo, contact Russ" |
| `gotcha` | Pitfalls and warnings | "ccxt returns None for stop order average price" |
| `reference` | File paths, API locations, credentials | "API keys in /root/.env on production server" |

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

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Skills | Claude Code YAML frontmatter | Auto-capture, session management |
| Local Storage | SQLite-vec (all-MiniLM-L6-v2) | Fast semantic search (~5ms) |
| Cloud Storage | Supabase (Postgres + pgvector) | Permanent backup, never deletes |
| Quick Reference | MEMORY.md | Human-readable context file |
| Background Sync | launchd (macOS) | Auto-sync every 5 minutes |

## More From Us

| Repo | What It Does | Stars |
|------|-------------|-------|
| [vanta](https://github.com/itsjwill/vanta) | Open source AI video engine — free Synthesia/Runway alternative | ![Stars](https://img.shields.io/github/stars/itsjwill/vanta?style=social) |
| [nextjs-animated-components](https://github.com/itsjwill/nextjs-animated-components) | 110+ free animated React components for Next.js | ![Stars](https://img.shields.io/github/stars/itsjwill/nextjs-animated-components?style=social) |
| [seoctopus](https://github.com/itsjwill/seoctopus) | 8-armed SEO intelligence — MCP server + CLI with 23 tools | ![Stars](https://img.shields.io/github/stars/itsjwill/seoctopus?style=social) |

---

## Want to Build Real Projects With These Tools?

Stop collecting bookmarks. Start shipping.

Join **The Agentic Advantage** — where builders learn to turn tools into income.

[Join The Agentic Advantage](https://www.skool.com/ai-elite-9507/about?ref=67521860944147018da6145e3db6e51c)

---

## Contributing

Found something that should be here? Open a PR. Found something broken? Open an issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — Go build something. See [LICENSE](LICENSE).
