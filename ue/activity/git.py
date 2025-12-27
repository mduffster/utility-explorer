"""Git activity tracking via GitHub API and local repos."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from ue.db import log_activity, get_activity


def is_github_cli_available() -> bool:
    """Check if GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, Exception):
        return False


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


def get_local_commits(repo_paths: list[str], since_days: int = 7) -> list[dict]:
    """Fetch recent commits from local git repositories.

    Returns same format as get_github_commits() for consistency.
    """
    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%d")
    commits = []

    for repo_path in repo_paths:
        path = Path(repo_path)
        if not (path / ".git").exists():
            continue

        repo_name = path.name

        try:
            # Get commits since date with format: hash|author|email|date|message
            result = subprocess.run(
                [
                    "git", "-C", str(path), "log",
                    f"--since={since_date}",
                    "--format=%H|%an|%ae|%aI|%s",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                continue

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 4)
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "timestamp": parts[3],
                        "message": parts[4],
                        "repo": repo_name,
                        "source": "local",
                    })
        except Exception:
            continue

    return commits


def get_commits_for_mode(mode: str, repo_paths: list[str], since_days: int = 7) -> list[dict]:
    """Get commits based on tracking mode.

    Handles mode selection and deduplication for "both" mode.
    """
    commits = []

    if mode == "auto":
        # GitHub first, fall back to local
        if is_github_cli_available():
            commits = get_github_commits(since_days)
            for c in commits:
                c["source"] = "github"
        elif repo_paths:
            commits = get_local_commits(repo_paths, since_days)

    elif mode == "github":
        commits = get_github_commits(since_days)
        for c in commits:
            c["source"] = "github"

    elif mode == "local":
        commits = get_local_commits(repo_paths, since_days)

    elif mode == "both":
        # Get from both sources
        github_commits = get_github_commits(since_days)
        for c in github_commits:
            c["source"] = "github"

        local_commits = get_local_commits(repo_paths, since_days)

        # Deduplicate by hash - prefer GitHub data if both have same commit
        seen_hashes = {c["hash"] for c in github_commits}
        commits = github_commits.copy()

        for c in local_commits:
            if c["hash"] not in seen_hashes:
                commits.append(c)
                seen_hashes.add(c["hash"])

    return commits


def sync_git_commits(since_days: int = 7) -> dict:
    """
    Sync commits based on configured tracking mode.

    Returns dict with counts and status info.
    """
    from ue.config import load_config, get_git_tracking_mode

    config = load_config()
    repo_paths = config.get("git_repos", [])
    mode = get_git_tracking_mode()

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

    commits = get_commits_for_mode(mode, repo_paths, since_days)
    repos_seen = set()
    total_logged = 0
    skipped = 0

    for commit in commits:
        repos_seen.add(commit["repo"])

        if commit["hash"] in existing_hashes:
            skipped += 1
            continue

        # Parse timestamp
        timestamp = commit["timestamp"]
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()

        source = commit.get("source", "unknown")
        log_activity(
            activity_type="commit",
            description=f"[{commit['repo']}] {commit['message'][:80]}",
            timestamp=timestamp,
            source=source,
            metadata=json.dumps(commit),
        )
        existing_hashes.add(commit["hash"])
        total_logged += 1

    return {
        "logged": total_logged,
        "repos_scanned": len(repos_seen),
        "skipped": skipped,
        "mode": mode,
        "has_repos": bool(repo_paths),
        "github_available": is_github_cli_available(),
    }
