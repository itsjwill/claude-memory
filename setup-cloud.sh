#!/bin/bash
#
# Claude Memory Cloud Setup
# Interactive Supabase configuration for cloud backup
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD}  Claude Memory Cloud Setup${NC}"
echo -e "${BOLD}  Never lose a memory again${NC}"
echo -e "${BOLD}================================================${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required. Install from python.org${NC}"
    exit 1
fi

# Install dependencies
echo -e "${CYAN}Installing dependencies...${NC}"
pip3 install supabase python-dotenv numpy 2>/dev/null || {
    echo -e "${YELLOW}pip install failed, trying pipx inject...${NC}"
    pipx inject mcp-memory-service supabase python-dotenv 2>/dev/null || {
        echo -e "${RED}Could not install dependencies.${NC}"
        echo "Run manually: pip3 install supabase python-dotenv numpy"
        exit 1
    }
}
echo -e "${GREEN}Dependencies installed${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run Python setup
echo ""
cd "$SCRIPT_DIR"
python3 -m cloud.cli setup

# Install launchd daemon (macOS)
if [[ "$(uname)" == "Darwin" ]]; then
    echo ""
    read -p "Install background sync daemon? (Y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        PLIST_SRC="$SCRIPT_DIR/com.claude-memory.sync.plist"
        PLIST_DST="$HOME/Library/LaunchAgents/com.claude-memory.sync.plist"

        if [ -f "$PLIST_SRC" ]; then
            # Update paths in plist
            sed "s|CLOUD_DIR_PLACEHOLDER|$SCRIPT_DIR|g" "$PLIST_SRC" > "$PLIST_DST"

            # Load the daemon
            launchctl unload "$PLIST_DST" 2>/dev/null || true
            launchctl load "$PLIST_DST"

            echo -e "${GREEN}Background sync daemon installed and started${NC}"
            echo "  Syncs every 5 minutes automatically"
            echo "  Check: launchctl list | grep claude-memory"
        else
            echo -e "${YELLOW}Plist not found at $PLIST_SRC${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}Cloud backup is ready!${NC}"
echo ""
echo "Commands:"
echo "  python3 -m cloud.cli status     # Check status"
echo "  python3 -m cloud.cli sync       # Manual sync"
echo "  python3 -m cloud.cli search X   # Search cloud"
echo "  python3 -m cloud.cli restore    # Restore from cloud"
echo ""
