# Contributing to Claude Memory

Thanks for wanting to make Claude Memory better. Here's how.

## How to Contribute

1. **Fork** the repo
2. **Create a branch** (`git checkout -b feature/your-feature`)
3. **Make your changes**
4. **Test** that install.sh still works end-to-end
5. **Submit a PR** with a clear description of what changed and why

## What We're Looking For

- **Bug fixes** — something broken? Fix it, open a PR
- **New memory types** — useful capture patterns we missed
- **Cloud provider support** — AWS, Firebase, etc. (Supabase is default but shouldn't be the only option)
- **Platform support** — Linux systemd daemon, Windows task scheduler (macOS launchd is done)
- **Better embeddings** — faster or more accurate models for semantic search
- **Documentation** — clearer setup guides, video walkthroughs, translations

## Quality Standards

- Must have working code — no "coming soon" or placeholder PRs
- Must solve a real problem for Claude Code users
- Include honest assessment of trade-offs or limitations
- Don't break existing install.sh or cloud sync flows
- Test with a real Claude Code session before submitting

## Reporting Issues

Found a bug? Open an issue with:
- What you expected to happen
- What actually happened
- Your OS and Python version
- Relevant log output (check `/tmp/claude-memory-sync.log`)

## Code Style

- Python: Follow existing patterns in the codebase
- Shell scripts: Use `set -e` and quote variables
- Keep it simple — this tool should stay lightweight

## Questions?

Open a discussion or issue. We're friendly.
