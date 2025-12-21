"""Activity tracking module."""

from ue.activity.git import sync_git_commits
from ue.activity.manual import log_application, log_win

__all__ = ["sync_git_commits", "log_application", "log_win"]
