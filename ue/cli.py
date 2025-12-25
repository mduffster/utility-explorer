"""Command-line interface."""

import click
from ue.utils.display import console, print_logo


@click.group()
@click.version_option()
def cli():
    """Utility Explorer - Personal productivity tools."""
    pass


@cli.command()
def setup():
    """Set up Google API credentials."""
    from ue.config import CREDENTIALS_PATH, DATA_DIR

    console.print()
    print_logo()
    console.print("\n[bold]Google API Setup[/bold]\n")
    console.print("To use Gmail and Calendar integration, you need to:")
    console.print()
    console.print("1. Go to [link]https://console.cloud.google.com/[/link]")
    console.print("2. Create a new project (or select existing)")
    console.print("3. Enable the Gmail API and Google Calendar API:")
    console.print("   - Go to 'APIs & Services' > 'Library'")
    console.print("   - Search for 'Gmail API' and enable it")
    console.print("   - Search for 'Google Calendar API' and enable it")
    console.print("4. Configure OAuth consent screen:")
    console.print("   - Go to 'APIs & Services' > 'OAuth consent screen'")
    console.print("   - Set up the consent screen (External is fine)")
    console.print("   - [bold]Push to Production[/bold] (or add yourself as a test user)")
    console.print("5. Create OAuth credentials:")
    console.print("   - Go to 'APIs & Services' > 'Credentials'")
    console.print("   - Click 'Create Credentials' > 'OAuth client ID'")
    console.print("   - Select 'Desktop application'")
    console.print("   - Download the JSON file")
    console.print(f"6. Save the file as: [cyan]{CREDENTIALS_PATH}[/cyan]")
    console.print()
    console.print(f"Data directory: [cyan]{DATA_DIR}[/cyan]")

    if CREDENTIALS_PATH.exists():
        console.print("\n[green]credentials.json found![/green]")
    else:
        console.print(f"\n[yellow]Waiting for credentials.json at {CREDENTIALS_PATH}[/yellow]")

    # GitHub CLI setup
    console.print("\n[bold]GitHub CLI Setup[/bold]\n")
    console.print("To track git commits across your repos:")
    console.print()
    console.print("1. Install GitHub CLI: [link]https://cli.github.com/[/link]")
    console.print("2. Authenticate: [cyan]gh auth login[/cyan]")
    console.print()

    # Check if gh is installed and authenticated
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            console.print("[green]GitHub CLI authenticated![/green]")
        else:
            console.print("[yellow]GitHub CLI not authenticated. Run: gh auth login[/yellow]")
    except FileNotFoundError:
        console.print("[yellow]GitHub CLI not installed. Visit: https://cli.github.com/[/yellow]")
    except Exception:
        console.print("[yellow]Could not check GitHub CLI status[/yellow]")

    console.print("\n" + "-" * 40)
    console.print("\nRun [cyan]ue sync[/cyan] to fetch data from all sources.")


# Import and register commands from modules
from ue.commands.sync import (
    sync, dashboard, dashboard_short, inbox, calendar, activity, add_repo
)
from ue.commands.task import task, done
from ue.commands.block import block, did
from ue.commands.routines import am, pm, review, status, focus
from ue.commands.log import log, mark
from ue.commands.demo import demo_setup, demo_reset
from ue.commands.workstream import workstream

# Sync/display commands
cli.add_command(sync)
cli.add_command(dashboard)
cli.add_command(dashboard_short)
cli.add_command(inbox)
cli.add_command(calendar)
cli.add_command(activity)
cli.add_command(add_repo)

# Task commands
cli.add_command(task)
cli.add_command(done)

# Block commands
cli.add_command(block)
cli.add_command(did)

# Routine commands
cli.add_command(am)
cli.add_command(pm)
cli.add_command(review)
cli.add_command(status)
cli.add_command(focus)

# Log/mark commands
cli.add_command(log)
cli.add_command(mark)

# Demo commands
cli.add_command(demo_setup)
cli.add_command(demo_reset)

# Workstream commands
cli.add_command(workstream)


if __name__ == "__main__":
    cli()
