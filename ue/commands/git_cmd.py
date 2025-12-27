"""Git tracking configuration commands."""

import click
from ue.utils.display import console


@click.group()
def git():
    """Configure git commit tracking."""
    pass


@git.command("mode")
@click.argument("mode", type=click.Choice(["auto", "local", "github", "both"]), required=False)
def git_mode(mode):
    """Get or set git tracking mode.

    Modes:
      auto   - Use GitHub if available, otherwise local repos
      local  - Only track local repos added with 'ue add-repo'
      github - Only use GitHub API (requires 'gh' CLI)
      both   - Track both sources (deduplicated)
    """
    from ue.config import load_config, set_git_tracking_mode
    from ue.activity.git import is_github_cli_available

    config = load_config()
    current = config.get("git_tracking_mode", "auto")

    if mode is None:
        # Show current mode and status
        repos = config.get("git_repos", [])
        gh_available = is_github_cli_available()

        console.print(f"\n[bold]Git Tracking Mode:[/bold] {current}")
        console.print(f"  GitHub CLI available: {'[green]yes[/green]' if gh_available else '[yellow]no[/yellow]'}")
        console.print(f"  Local repos configured: {len(repos)}")

        if repos:
            console.print("\n[bold]Tracked Repos:[/bold]")
            for repo in repos:
                console.print(f"  {repo}")

        console.print("\n[dim]Use 'ue git mode <mode>' to change mode[/dim]")
        console.print("[dim]Use 'ue add-repo <path>' to add local repos[/dim]")
        return

    set_git_tracking_mode(mode)
    console.print(f"[green]Git tracking mode set to: {mode}[/green]")

    # Show warnings based on mode
    config = load_config()
    repos = config.get("git_repos", [])

    if mode == "local" and not repos:
        console.print("[yellow]Warning: No local repos configured. Use 'ue add-repo <path>' to add some.[/yellow]")
    elif mode == "github" and not is_github_cli_available():
        console.print("[yellow]Warning: GitHub CLI not available. Run 'gh auth login' to authenticate.[/yellow]")
    elif mode == "both":
        if not repos:
            console.print("[yellow]Note: No local repos configured - will only show GitHub commits.[/yellow]")
        if not is_github_cli_available():
            console.print("[yellow]Note: GitHub CLI not available - will only show local commits.[/yellow]")


@git.command("repos")
def git_repos():
    """List configured local git repositories."""
    from pathlib import Path
    from ue.config import load_config

    config = load_config()
    repos = config.get("git_repos", [])

    if not repos:
        console.print("[dim]No local repos configured. Use 'ue add-repo <path>' to add some.[/dim]")
        return

    console.print("[bold]Tracked Local Repos:[/bold]")
    for repo_path in repos:
        path = Path(repo_path)
        exists = path.exists()
        has_git = (path / ".git").exists() if exists else False

        if has_git:
            console.print(f"  [green]{repo_path}[/green]")
        elif exists:
            console.print(f"  [yellow]{repo_path}[/yellow] (not a git repo)")
        else:
            console.print(f"  [red]{repo_path}[/red] (path not found)")


@git.command("remove-repo")
@click.argument("repo_path")
def git_remove_repo(repo_path):
    """Remove a local git repository from tracking."""
    from pathlib import Path
    from ue.config import load_config, save_config

    path = Path(repo_path).expanduser().resolve()
    path_str = str(path)

    config = load_config()
    repos = config.get("git_repos", [])

    if path_str in repos:
        repos.remove(path_str)
        config["git_repos"] = repos
        save_config(config)
        console.print(f"[yellow]Removed {path}[/yellow]")
    else:
        console.print(f"[red]{path} not in tracked repos[/red]")


@git.command("dismiss")
def git_dismiss_hint():
    """Dismiss the git setup hint message."""
    from ue.config import dismiss_git_hint, is_git_hint_dismissed

    if is_git_hint_dismissed():
        console.print("[dim]Hint already dismissed.[/dim]")
    else:
        dismiss_git_hint()
        console.print("[green]Git setup hint dismissed.[/green]")
