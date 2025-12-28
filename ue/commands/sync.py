"""Sync and data display commands."""

import click
from ue.utils.display import console


def run_sync(days: int = 7, quiet: bool = False):
    """Run sync and record timestamp. Used by sync command and auto-sync."""
    from datetime import datetime
    from ue.activity.git import sync_git_commits
    from ue.config import set_last_sync, is_google_configured

    if not quiet:
        console.print("[bold]Syncing...[/bold]\n")

    # Only sync Google services if credentials are configured
    if is_google_configured():
        from ue.inbox.gmail import sync_gmail_inbox, sync_gmail_sent
        from ue.inbox.calendar import sync_calendar

        try:
            result = sync_gmail_inbox(days=days)
            if not quiet:
                console.print(f"  Gmail inbox: {result['fetched']} emails")
        except Exception as e:
            if not quiet:
                console.print(f"  [red]Gmail inbox error: {e}[/red]")

        try:
            result = sync_gmail_sent(days=days)
            skipped = result.get('skipped', 0)
            if not quiet:
                msg = f"  Gmail sent: {result['logged']} emails logged"
                if skipped:
                    msg += f" ({skipped} already synced)"
                console.print(msg)
        except Exception as e:
            if not quiet:
                console.print(f"  [red]Gmail sent error: {e}[/red]")

        try:
            result = sync_calendar(days_ahead=days)
            if not quiet:
                console.print(f"  Calendar: {result['fetched']} events")
        except Exception as e:
            if not quiet:
                console.print(f"  [red]Calendar error: {e}[/red]")

    try:
        result = sync_git_commits(since_days=days)
        skipped = result.get('skipped', 0)
        mode = result.get('mode', 'unknown')
        if not quiet:
            if result['logged'] > 0 or result['repos_scanned'] > 0:
                mode_str = f" [{mode}]" if mode != "auto" else ""
                msg = f"  Git{mode_str}: {result['logged']} commits from {result['repos_scanned']} repos"
                if skipped:
                    msg += f" ({skipped} already synced)"
                console.print(msg)
            elif result.get('has_repos') or result.get('github_available'):
                console.print("  Git: no new commits")
            # If neither repos nor gh configured, stay silent
    except Exception as e:
        if not quiet:
            console.print(f"  [red]Git error: {e}[/red]")

    set_last_sync(datetime.now().isoformat())

    if not quiet:
        console.print("\n[green]Sync complete![/green]")


def auto_sync_if_stale():
    """Auto-sync if data is stale. Returns True if sync was run."""
    from ue.config import is_sync_stale

    if is_sync_stale():
        console.print("[dim]Auto-syncing...[/dim]")
        run_sync(quiet=True)
        console.print("[dim]Sync complete.[/dim]\n")
        return True
    return False


@click.command()
@click.option("--days", default=7, help="Days of history to sync")
def sync(days):
    """Sync data from Gmail, Calendar, and git."""
    run_sync(days=days, quiet=False)


@click.command()
def dashboard():
    """Show the main dashboard."""
    auto_sync_if_stale()
    from ue.dashboard import show_dashboard
    show_dashboard()


# Alias 'd' for dashboard
@click.command("d")
def dashboard_short():
    """Show the main dashboard (shortcut)."""
    auto_sync_if_stale()
    from ue.dashboard import show_dashboard
    show_dashboard()


@click.command()
@click.option("--limit", "-n", default=20, help="Number of items to show")
def inbox(limit):
    """Show email inbox."""
    from ue.config import is_google_configured
    if not is_google_configured():
        console.print("[dim]Gmail not configured. Run 'ue setup' for instructions.[/dim]")
        return
    from ue.dashboard import show_inbox
    show_inbox(source="gmail", limit=limit)


@click.command()
@click.option("--days", "-d", default=7, help="Days ahead to show")
def calendar(days):
    """Show upcoming calendar events."""
    from ue.config import is_google_configured
    if not is_google_configured():
        console.print("[dim]Google Calendar not configured. Run 'ue setup' for instructions.[/dim]")
        return
    from ue.dashboard import show_calendar
    show_calendar(days=days)


@click.command()
@click.option("--days", "-d", default=7, help="Days of history")
@click.option("--type", "-t", "activity_type", help="Filter by type")
def activity(days, activity_type):
    """Show activity log."""
    from ue.dashboard import show_activity
    show_activity(days=days, activity_type=activity_type)


@click.command()
@click.argument("repo_path")
def add_repo(repo_path):
    """Add a git repository to track."""
    from pathlib import Path
    from ue.config import load_config, save_config

    path = Path(repo_path).expanduser().resolve()
    if not (path / ".git").exists():
        console.print(f"[red]{path} is not a git repository[/red]")
        return

    config = load_config()
    repos = config.get("git_repos", [])
    if str(path) not in repos:
        repos.append(str(path))
        config["git_repos"] = repos
        save_config(config)
        console.print(f"[green]Added {path}[/green]")
    else:
        console.print(f"[yellow]Already tracking {path}[/yellow]")
