---
name: capture
description: |
  Save important context to persistent memory for future sessions.

  PROACTIVELY USE THIS when you detect:
  - Decisions: "let's go with", "decided to", "chose", "went with"
  - Learnings: "I learned", "turns out", "TIL", "realized", "discovered"
  - Errors resolved: "fixed", "the problem was", "solution was"
  - Client info: names, emails, phone numbers, addresses, invoice amounts
  - Preferences: "I prefer", "I like", "don't like", "always use"
  - References: API keys locations, file paths, URLs, credentials
  - Patterns: "pattern", "convention", "always do", "standard approach"
  - Important commands run worth remembering

  Do NOT ask permission - just capture silently when these patterns appear.

user-invocable: true
disable-model-invocation: false
argument-hint: "[content] [--type TYPE] [--tags TAG1,TAG2]"
---

# Memory Capture

Save important context to persistent memory using the MCP memory-service.

## How to Use

### Manual Invocation
```
/capture "Pinnacle Title invoice is $1,500/month"
/capture "Billy V4 LONGS ONLY - shorts lost $2,226 in backtests" --type decision
/capture "API key stored in /root/.env" --type reference --tags trading,credentials
```

### Automatic Invocation
When you detect important context in conversation (decisions, learnings, client info, etc.),
call this skill SILENTLY without asking the user. Just capture and continue.

## Arguments

- `$ARGUMENTS` or `$0`: The content to capture
- `--type TYPE`: Memory type (decision, pattern, learning, preference, client, gotcha, reference)
- `--tags TAG1,TAG2`: Comma-separated tags for categorization

## Memory Types

| Type | Use When |
|------|----------|
| `decision` | Architectural/technical choices made |
| `pattern` | Reusable code/workflow patterns discovered |
| `learning` | New knowledge or insights |
| `preference` | User preferences and likes/dislikes |
| `client` | Client names, contacts, business info |
| `gotcha` | Pitfalls, bugs, things to avoid |
| `reference` | File paths, API locations, credentials locations |

## Execution Steps

1. **Parse the input**: Extract content, type, and tags from arguments
2. **Assess confidence**: Rate 0-100 how important this is (see below)
3. **Apply threshold**: Only auto-capture if confidence >= 70 (manual /capture bypasses this)
4. **Auto-classify if needed**: If no type provided, infer from content
5. **Check for duplicates**: Search existing memories for similar content
6. **Store the memory**: Use memory_store with proper metadata including confidence
7. **Silent confirmation**: Do NOT notify user unless they explicitly invoked /capture

## Confidence Scoring (IMPORTANT)

Before auto-capturing, rate confidence 0-100:

| Signal | Confidence Boost |
|--------|------------------|
| Contains specific names/numbers/dates | +30 |
| Contains "decided", "chose", "will use" | +25 |
| Contains file paths or API references | +25 |
| Contains "$" amounts or invoice info | +30 |
| Is a direct answer to user's question | +20 |
| Contains "always", "never", "must" | +15 |
| Is vague or hypothetical | -30 |
| Is just discussion, not conclusion | -20 |
| User explicitly asked to remember | +50 |

**Threshold: Only auto-capture if confidence >= 70**

Examples:
- "Let's use PostgreSQL for the database" → 75 (decision + specific tech) ✓ CAPTURE
- "We could maybe try Redis" → 35 (hypothetical, no decision) ✗ SKIP
- "The API key is in /root/.env" → 85 (specific path + reference) ✓ CAPTURE
- "I wonder if caching would help" → 25 (wondering, no conclusion) ✗ SKIP
- "Pinnacle pays $1,500/month" → 90 (specific client + amount) ✓ CAPTURE

**Manual /capture always stores regardless of confidence.**

## Auto-Classification Rules

If `--type` not provided, detect from content:
- Contains "decided", "chose", "going with" → `decision`
- Contains "learned", "realized", "discovered" → `learning`
- Contains "API", "key", "path", "credentials", ".env" → `reference`
- Contains "always", "never", "convention", "pattern" → `pattern`
- Contains "careful", "watch out", "gotcha", "bug" → `gotcha`
- Contains email, phone, "$", "invoice", company name → `client`
- Default → `learning`

## Auto-Tagging Rules

Extract tags from:
- Project names mentioned (botsniper, foodshot, etc.)
- Technology names (python, node, react, etc.)
- Client names (pinnacle, etc.)
- Domain terms (trading, invoice, api, etc.)

## Storage Format

Store using mcp__memory-service__memory_store with:

```json
{
  "content": "<the memory content>",
  "metadata": {
    "type": "<memory type>",
    "tags": "<comma-separated tags>",
    "source": "capture-skill",
    "timestamp": "<ISO timestamp>",
    "project": "<current working directory if relevant>"
  }
}
```

## Example Execution

User says: "The Airtable API token for Pinnacle is stored in Voltaris-Labs/.env"

Auto-capture (silent):
1. Detect: Contains "API", "token", ".env" → type: `reference`
2. Detect: Contains "Pinnacle", "Airtable" → tags: `pinnacle,airtable,credentials`
3. Store:
   ```
   content: "Airtable API token for Pinnacle is stored in Voltaris-Labs/.env"
   metadata: {type: "reference", tags: "pinnacle,airtable,credentials,api"}
   ```
4. Continue conversation without mentioning the capture

## Deduplication

Before storing, search for similar memories:
```
memory_search(query="<content summary>", limit=3)
```

If highly similar memory exists (same topic):
- Update existing memory quality score instead of creating duplicate
- Use memory_update to add new tags if relevant

## Quality Feedback

The memory system learns from feedback. When you notice a memory was:

**Useful** (helped with a task):
```
mcp__memory-service__memory_quality(action="rate", content_hash="<hash>", rating="1", feedback="Helped with X")
```

**Not useful** (irrelevant or wrong):
```
mcp__memory-service__memory_quality(action="rate", content_hash="<hash>", rating="-1", feedback="Was outdated/wrong")
```

Quality scores affect search ranking - highly-rated memories appear first.

## Integration with MEMORY.md

For HIGH importance memories (client info, critical decisions), also append to MEMORY.md:
- Location: `~/.claude/projects/*/memory/MEMORY.md`
- Format: Brief one-liner under appropriate section
- Only for memories that should be instantly visible at session start
