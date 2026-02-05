# Claude Memory

**Persistent memory for Claude Code.** Never lose conversation context again.

Claude Memory automatically captures important context during your sessions and recalls it when you start new ones. No manual saving required.

## Features

- **Auto-Capture**: Claude automatically saves decisions, learnings, client info, and patterns
- **Semantic Search**: Find memories by meaning, not just keywords
- **Session Summaries**: Automatic end-of-session summaries
- **Context Recall**: Relevant memories loaded at session start
- **Silent Operation**: Captures happen in the background without interrupting your flow

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-memory/main/install.sh | bash
```

Or clone and run locally:

```bash
git clone https://github.com/YOUR_USERNAME/claude-memory.git
cd claude-memory
./install.sh
```

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- [MCP Memory Service](https://github.com/anthropics/mcp-memory-service) (installed automatically)

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

### 5. Search Memories

Find stored memories anytime:

```
memory_search(query="database decisions", limit=10)
memory_list(tags=["client"])
```

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

## Configuration

After installation, memories are stored in:
- **Primary**: MCP Memory Service (SQLite with embeddings)
- **Quick Reference**: `~/.claude/projects/*/memory/MEMORY.md`

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-memory/main/uninstall.sh | bash
```

Or manually:

```bash
rm -rf ~/.claude/skills/capture
# Memories in MCP service are preserved
```

## How It's Built

Claude Memory uses:
- **Claude Code Skills**: Custom `/capture` skill with YAML frontmatter
- **MCP Memory Service**: SQLite-vec for semantic search with embeddings
- **MEMORY.md**: Human-readable quick reference file

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT - See [LICENSE](LICENSE)
