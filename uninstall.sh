#!/bin/bash
#
# Claude Memory - Uninstall Script
#

set -e

echo "=================================="
echo "  Claude Memory - Uninstaller"
echo "=================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CAPTURE_DIR="$HOME/.claude/skills/capture"

echo "This will remove the /capture skill."
echo "Your memories in MCP Memory Service will be preserved."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$CAPTURE_DIR" ]; then
        rm -rf "$CAPTURE_DIR"
        echo -e "${GREEN}✓ /capture skill removed${NC}"
    else
        echo -e "${YELLOW}Skill directory not found${NC}"
    fi

    echo ""
    echo "Uninstall complete."
    echo ""
    echo "Note: Your memories are preserved in MCP Memory Service."
    echo "To also clear memories, run: memory_cleanup()"
else
    echo "Uninstall cancelled."
fi
