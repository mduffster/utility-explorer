"""Git activity tracking via GitHub API."""

import json
import subprocess
from datetime import datetime, timedelta

from ue.db import log_activity, get_activity


def get_github_username() -> str | None:
    """Get the authenticated GitHub username."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_github_commits(since_days: int = 7) -> list[dict]:
    """Fetch recent commits from GitHub across all repos using search API."""
    username = get_github_username()
    if not username:
        return []

    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%d")
    commits = []

    try:
        # Use GitHub search API to find commits by author
        # This searches across all repos
        result = subprocess.run(
            ["gh", "api", "search/commits",
             "-X", "GET",
             "-f", f"q=author:{username} committer-date:>={since_date}",
             "-f", "sort=committer-date",
             "-f", "per_page=100",
             "--jq", ".items[] | {sha: .sha, message: .commit.message, date: .commit.committer.date, repo: .repository.name, author: .commit.author.name}"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return []

        # Parse the JSON lines output
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                commit = json.loads(line)
                commits.append({
                    "hash": commit["sha"],
                    "author": commit.get("author", username),
                    "email": "",
                    "timestamp": commit["date"],
                    "message": commit.get("message", "").split("\n")[0],  # first line only
                    "repo": commit["repo"],
                })
            except (json.JSONDecodeError, KeyError):
                continue

    except Exception:
        return []

    return commits


def sync_git_commits(since_days: int = 7) -> dict:
    """
    Sync commits from GitHub.

    Returns dict with counts.
    """
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

    commits = get_github_commits(since_days)
    repos_seen = set()
    total_logged = 0

    for commit in commits:
        repos_seen.add(commit["repo"])

        if commit["hash"] in existing_hashes:
            continue

        # Parse timestamp
        timestamp = commit["timestamp"]
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()

        log_activity(
            activity_type="commit",
            description=f"[{commit['repo']}] {commit['message'][:80]}",
            timestamp=timestamp,
            source="github",
            metadata=json.dumps(commit),
        )
        existing_hashes.add(commit["hash"])
        total_logged += 1

    return {"logged": total_logged, "repos_scanned": len(repos_seen)}
