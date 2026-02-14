"""Configuration loader for Claude Memory Cloud Sync.

Loads Supabase credentials and sync settings from:
1. Environment variables (highest priority)
2. ~/.claude-memory-cloud.env file
3. Defaults
"""

import os
import platform
import socket
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    ENV_FILE = Path.home() / ".claude-memory-cloud.env"
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
except ImportError:
    pass


def _get_default_db_path() -> str:
    """Auto-detect the mcp-memory-service SQLite database path."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        path = home / "Library" / "Application Support" / "mcp-memory" / "sqlite_vec.db"
    elif system == "Linux":
        path = home / ".local" / "share" / "mcp-memory" / "sqlite_vec.db"
    else:
        path = home / ".mcp-memory" / "sqlite_vec.db"

    if path.exists():
        return str(path)

    # Fallback: check common locations
    fallbacks = [
        home / ".mcp_memory_service" / "memories.db",
        home / ".mcp-memory" / "sqlite_vec.db",
    ]
    for fb in fallbacks:
        if fb.exists():
            return str(fb)

    return str(path)  # Return default even if not found yet


def _get_device_name() -> str:
    """Generate a device name from hostname."""
    return socket.gethostname().split(".")[0].lower()


# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Local database
LOCAL_DB_PATH = os.getenv("CLAUDE_MEMORY_DB_PATH", _get_default_db_path())

# Sync settings
SYNC_INTERVAL = int(os.getenv("CLAUDE_MEMORY_SYNC_INTERVAL", "300"))
SYNC_ENABLED = os.getenv("CLAUDE_MEMORY_SYNC_ENABLED", "true").lower() == "true"
DEVICE_NAME = os.getenv("CLAUDE_MEMORY_DEVICE_NAME", _get_device_name())

# Embedding settings
EMBEDDING_DIM = int(os.getenv("CLAUDE_MEMORY_EMBEDDING_DIM", "384"))

# Paths
ENV_FILE_PATH = Path.home() / ".claude-memory-cloud.env"
CLOUD_DIR = Path(__file__).parent


def is_configured() -> bool:
    """Check if Supabase credentials are configured."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def get_config_summary() -> dict:
    """Return a summary of current configuration."""
    return {
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "(not set)",
        "supabase_key": "***" + SUPABASE_SERVICE_KEY[-8:] if SUPABASE_SERVICE_KEY else "(not set)",
        "local_db_path": LOCAL_DB_PATH,
        "local_db_exists": Path(LOCAL_DB_PATH).exists(),
        "sync_interval": SYNC_INTERVAL,
        "sync_enabled": SYNC_ENABLED,
        "device_name": DEVICE_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "configured": is_configured(),
    }
