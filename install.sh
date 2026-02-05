#!/bin/bash
#
# Claude Memory - Install Script
# Persistent memory for Claude Code
#

set -e

echo "=================================="
echo "  Claude Memory - Installer"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paths
CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"
CAPTURE_DIR="$SKILLS_DIR/capture"
MEMORY_DIR="$CLAUDE_DIR/projects/-Users-$(whoami)/memory"

# Check for Claude Code
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}Warning: Claude Code CLI not found in PATH${NC}"
    echo "Install from: https://claude.ai/code"
    echo "Continuing anyway..."
    echo ""
fi

# Check for MCP Memory Service
echo "Checking for MCP Memory Service..."
if command -v memory &> /dev/null; then
    echo -e "${GREEN}✓ MCP Memory Service found${NC}"
else
    echo -e "${YELLOW}MCP Memory Service not found. Installing...${NC}"
    if command -v pipx &> /dev/null; then
        pipx install mcp-memory-service
        echo -e "${GREEN}✓ MCP Memory Service installed${NC}"
    elif command -v pip &> /dev/null; then
        pip install mcp-memory-service
        echo -e "${GREEN}✓ MCP Memory Service installed${NC}"
    else
        echo -e "${RED}Error: Neither pipx nor pip found. Please install MCP Memory Service manually.${NC}"
        echo "Run: pipx install mcp-memory-service"
        exit 1
    fi
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$CAPTURE_DIR"
mkdir -p "$MEMORY_DIR"
echo -e "${GREEN}✓ Directories created${NC}"

# Get script directory (works for both curl | bash and local execution)
if [ -n "$BASH_SOURCE" ] && [ -f "${BASH_SOURCE%/*}/skills/capture/SKILL.md" ]; then
    SCRIPT_DIR="${BASH_SOURCE%/*}"
else
    # Download from GitHub if running via curl
    SCRIPT_DIR=$(mktemp -d)
    echo "Downloading files..."
    curl -fsSL "https://raw.githubusercontent.com/maskedhunter/claude-memory/main/skills/capture/SKILL.md" -o "$SCRIPT_DIR/SKILL.md"
    curl -fsSL "https://raw.githubusercontent.com/maskedhunter/claude-memory/main/examples/MEMORY.md" -o "$SCRIPT_DIR/MEMORY_EXAMPLE.md"
fi

# Install skills
echo ""
echo "Installing skills..."

# /capture skill
if [ -f "$SCRIPT_DIR/SKILL.md" ]; then
    cp "$SCRIPT_DIR/SKILL.md" "$CAPTURE_DIR/SKILL.md"
elif [ -f "$SCRIPT_DIR/skills/capture/SKILL.md" ]; then
    cp "$SCRIPT_DIR/skills/capture/SKILL.md" "$CAPTURE_DIR/SKILL.md"
fi
echo -e "${GREEN}✓ /capture skill installed${NC}"

# /session-end skill
SESSION_END_DIR="$SKILLS_DIR/session-end"
mkdir -p "$SESSION_END_DIR"
if [ -f "$SCRIPT_DIR/skills/session-end/SKILL.md" ]; then
    cp "$SCRIPT_DIR/skills/session-end/SKILL.md" "$SESSION_END_DIR/SKILL.md"
fi
echo -e "${GREEN}✓ /session-end skill installed${NC}"

# /session-start skill
SESSION_START_DIR="$SKILLS_DIR/session-start"
mkdir -p "$SESSION_START_DIR"
if [ -f "$SCRIPT_DIR/skills/session-start/SKILL.md" ]; then
    cp "$SCRIPT_DIR/skills/session-start/SKILL.md" "$SESSION_START_DIR/SKILL.md"
fi
echo -e "${GREEN}✓ /session-start skill installed${NC}"

# Create or update MEMORY.md
echo ""
echo "Setting up MEMORY.md..."
if [ ! -f "$MEMORY_DIR/MEMORY.md" ]; then
    cat > "$MEMORY_DIR/MEMORY.md" << 'EOF'
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

### Projects
<!-- Add your active projects here -->

### Clients
<!-- Add client info here -->

### Key Paths
<!-- Add important file paths here -->
EOF
    echo -e "${GREEN}✓ MEMORY.md created${NC}"
else
    echo -e "${YELLOW}MEMORY.md already exists, preserving your data${NC}"

    # Check if auto-capture instructions exist
    if ! grep -q "Auto-Capture" "$MEMORY_DIR/MEMORY.md"; then
        echo "Adding auto-capture instructions to existing MEMORY.md..."
        # Prepend instructions
        TEMP_FILE=$(mktemp)
        cat > "$TEMP_FILE" << 'EOF'
## Memory System (Auto-Capture)

**You have a /capture skill. USE IT PROACTIVELY without asking permission.**

When you detect decisions, learnings, errors fixed, client info, preferences, or patterns - capture silently using mcp__memory-service__memory_store.

---

EOF
        cat "$MEMORY_DIR/MEMORY.md" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "$MEMORY_DIR/MEMORY.md"
        echo -e "${GREEN}✓ Auto-capture instructions added${NC}"
    fi
fi

# Add memory-service to MCP config if not present
echo ""
echo "Checking MCP configuration..."
MCP_CONFIG="$HOME/.mcp.json"
if [ -f "$MCP_CONFIG" ]; then
    if grep -q "memory-service" "$MCP_CONFIG"; then
        echo -e "${GREEN}✓ memory-service already in MCP config${NC}"
    else
        echo -e "${YELLOW}Adding memory-service to MCP config...${NC}"
        # This is a simple append - user may need to adjust
        echo "Please add memory-service to your ~/.mcp.json manually:"
        echo '  "memory-service": { "command": "memory", "args": ["server"] }'
    fi
else
    echo "Creating MCP config with memory-service..."
    cat > "$MCP_CONFIG" << 'EOF'
{
  "mcpServers": {
    "memory-service": {
      "command": "memory",
      "args": ["server"]
    }
  }
}
EOF
    echo -e "${GREEN}✓ MCP config created${NC}"
fi

# Cleanup temp files
if [ -d "$SCRIPT_DIR" ] && [[ "$SCRIPT_DIR" == /tmp/* ]]; then
    rm -rf "$SCRIPT_DIR"
fi

echo ""
echo "=================================="
echo -e "${GREEN}  Installation Complete!${NC}"
echo "=================================="
echo ""
echo "What's installed:"
echo "  • /capture skill - manual memory saves"
echo "  • /session-start skill - context loading"
echo "  • /session-end skill - session summaries"
echo "  • MEMORY.md at $MEMORY_DIR"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code to load the new skill"
echo "  2. Try: /capture \"Test memory\""
echo "  3. Claude will now auto-capture important context"
echo ""
echo "Documentation: https://github.com/maskedhunter/claude-memory"
echo ""
