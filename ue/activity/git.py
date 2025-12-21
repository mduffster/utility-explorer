"""Git activity tracking."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from ue.db import log_activity, get_activity
from ue.config import load_config


def get_commits_from_repo(repo_path: Path, since_days: int = 7) -> list[dict]:
    """Get commits from a git repository."""
    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%d")

    try:
        result = subprocess.run(
            [
                "git", "log",
                f"--since={since_date}",
                "--format=%H|%an|%ae|%ai|%s",
                "--all"
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "timestamp": parts[3],
                    "message": parts[4],
                    "repo": repo_path.name,
                })
        return commits

    except Exception:
        return []


def sync_git_commits(since_days: int = 7) -> dict:
    """
    Sync commits from configured git repos.

    Returns dict with counts.
    """
    config = load_config()
    repos = config.get("git_repos", [])

    # Always include current repo if it's a git repo
    cwd = Path.cwd()
    if (cwd / ".git").exists():
        repos = [str(cwd)] + [r for r in repos if Path(r).resolve() != cwd.resolve()]

    total_logged = 0
    existing_hashes = set()

    # Get existing commit hashes to avoid duplicates
    existing = get_activity(activity_type="commit")
    for act in existing:
        if act.get("metadata"):
            try:
                meta = json.loads(act["metadata"])
                if "hash" in meta:
                    existing_hashes.add(meta["hash"])
            except Exception:
                pass

    for repo_path_str in repos:
        repo_path = Path(repo_path_str).expanduser().resolve()
        if not repo_path.exists():
            continue

        commits = get_commits_from_repo(repo_path, since_days)

        for commit in commits:
            if commit["hash"] in existing_hashes:
                continue

            # Parse timestamp
            timestamp = commit["timestamp"]
            try:
                # Git format: 2024-01-15 10:30:45 -0500
                dt = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
                timestamp = dt.isoformat()
            except Exception:
                timestamp = datetime.now().isoformat()

            log_activity(
                activity_type="commit",
                description=f"[{commit['repo']}] {commit['message'][:80]}",
                timestamp=timestamp,
                source="git",
                metadata=json.dumps(commit),
            )
            existing_hashes.add(commit["hash"])
            total_logged += 1

    return {"logged": total_logged, "repos_scanned": len(repos)}
