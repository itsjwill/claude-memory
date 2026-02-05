# Claude Memory - Cross-Session Context

## Memory System

### Auto-Capture (IMPORTANT - Read This)

**You have a /capture skill. USE IT PROACTIVELY without asking permission.**

When you detect ANY of these in conversation, silently capture to memory:
- Decisions made ("decided to", "let's go with", "chose")
- Learnings ("I learned", "turns out", "realized", "discovered")
- Errors resolved ("fixed the bug", "the problem was")
- Client info (names, emails, phones, addresses, invoices)
- Preferences ("I prefer", "I like", "don't like")
- References (API paths, file locations, credentials locations)
- Patterns ("always do", "convention", "standard approach")

**How to capture:** Use mcp__memory-service__memory_store with content and metadata (type, tags).

### Session-Start Recall

At the START of each session, search for relevant context:
```
mcp__memory-service__memory_search(query="<current project or topic>", limit=5, time_expr="last 7 days")
```

### Quick Commands
- `/capture "content"` - Manual memory save
- `memory_search(query="topic")` - Find memories
- `memory_list()` - Browse all memories

---

## Quick Reference

Add your frequently-accessed info below. This file is auto-loaded at session start.

### Active Projects

| Project | Path | Notes |
|---------|------|-------|
| Example Project | ~/projects/example | Main development |

### Clients

#### Example Client
- Contact: John Doe
- Email: john@example.com
- Service: Monthly consulting ($X/mo)

### Key File Locations

| What | Where |
|------|-------|
| API Keys | ~/.env |
| Config | ~/.config/app |

### Patterns

#### Example Pattern
1. Step one
2. Step two
3. Step three
