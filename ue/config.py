"""Configuration management."""

import json
from pathlib import Path

# All data lives here
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
