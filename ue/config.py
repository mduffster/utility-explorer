"""Configuration management."""

import json
import os
from pathlib import Path

# Check for demo mode - uses separate data directory
DEMO_MODE = os.environ.get("UE_DEMO", "").lower() in ("1", "true", "yes")

# All data lives here
if DEMO_MODE:
    DATA_DIR = Path.home() / ".utility-explorer-demo"
else:
    DATA_DIR = Path.home() / ".utility-explorer"

DB_PATH = DATA_DIR / "ue.db"
CREDENTIALS_PATH = DATA_DIR / "credentials.json"
TOKEN_PATH = DATA_DIR / "token.json"
CONFIG_PATH = DATA_DIR / "config.json"

# Google API scopes
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load user configuration."""
    ensure_data_dir()
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "workstreams": {
            "ai-research": {"priority": "high", "color": "green"},
            "terrasol": {"priority": "mid", "color": "yellow"},
            "blog": {"priority": "mid", "color": "blue"},
            "consulting": {"priority": "low", "color": "dim"},
        },
        "git_repos": [],  # paths to repos to track
        "watch_dirs": [],  # paths to watch for new docs
    }


def save_config(config: dict):
    """Save user configuration."""
    ensure_data_dir()
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_last_sync() -> str | None:
    """Get timestamp of last sync."""
    config = load_config()
    return config.get("last_sync")


def set_last_sync(timestamp: str):
    """Set timestamp of last sync."""
    config = load_config()
    config["last_sync"] = timestamp
    save_config(config)


def is_sync_stale(max_age_minutes: int = 60) -> bool:
    """Check if sync data is stale (older than max_age_minutes)."""
    from datetime import datetime

    last_sync = get_last_sync()
    if not last_sync:
        return True

    try:
        last_dt = datetime.fromisoformat(last_sync)
        age_minutes = (datetime.now() - last_dt).total_seconds() / 60
        return age_minutes > max_age_minutes
    except (ValueError, TypeError):
        return True
