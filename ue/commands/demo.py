"""Demo mode commands for showcasing the tool."""

import click
from ue.utils.display import console


@click.command("demo-setup")
def demo_setup():
    """Set up demo data for showcasing the tool. Only works in demo mode (UE_DEMO=1)."""
    from datetime import datetime, timedelta
    import json
    from ue.config import DEMO_MODE, DATA_DIR, CONFIG_PATH
    from ue.db import get_db, add_task, set_block_target, log_block_completion, complete_task

    if not DEMO_MODE:
        console.print("[red]Demo setup only works in demo mode.[/red]")
        console.print("Run with: [cyan]UE_DEMO=1 ue demo-setup[/cyan]")
        return

    console.print(f"[bold]Setting up demo data in {DATA_DIR}[/bold]\n")

    # Create demo config
    demo_config = {
        "workstreams": {
            "work": {"priority": "high", "color": "green"},
            "side-project": {"priority": "mid", "color": "blue"},
            "learning": {"priority": "mid", "color": "yellow"},
            "health": {"priority": "low", "color": "cyan"}
        },
        "git_repos": [],
        "watch_dirs": [],
        "last_sync": datetime.now().isoformat()
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(demo_config, indent=2))
    console.print("  Created config with workstreams")

    # Initialize DB
    db = get_db()
    db.close()

    # Create block targets
    blocks = [
        ("Deep Work", 5, "work"),
        ("Exercise", 4, "health"),
        ("Reading", 3, "learning"),
        ("Side Project", 2, "side-project"),
        ("Meditation", 0, "health"),  # daily
    ]
    for name, target, ws in blocks:
        set_block_target(name, target, ws)
    console.print(f"  Created {len(blocks)} block targets")

    # Add some block completions for this week
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())

    completions = [
        ("Deep Work", week_start, "completed"),
        ("Deep Work", week_start + timedelta(days=1), "completed"),
        ("Exercise", week_start, "completed"),
        ("Exercise", week_start + timedelta(days=1), "completed"),
        ("Reading", week_start, "completed"),
        ("Side Project", week_start, "completed"),
    ]
    for name, date, status in completions:
        log_block_completion(name, date.isoformat(), status)
    console.print(f"  Logged {len(completions)} block completions")

    # Create tasks
    tasks = [
        ("Review PR from teammate", (today + timedelta(days=1)).isoformat(), "work", "high"),
        ("Write blog post draft", (today + timedelta(days=3)).isoformat(), "side-project", "normal"),
        ("Update project README", (today + timedelta(days=5)).isoformat(), "side-project", "low"),
        ("Schedule dentist appointment", (today + timedelta(days=2)).isoformat(), None, "normal"),
        ("Research new framework", None, "learning", "low"),
    ]
    for title, due, ws, pri in tasks:
        add_task(title, due, ws, pri)
    console.print(f"  Created {len(tasks)} tasks")

    # Mark one task as done
    complete_task(1)  # Mark first task done
    console.print("  Marked 1 task as completed")

    console.print("\n[green]Demo setup complete![/green]")
    console.print("\nRun demo commands with:")
    console.print("  [cyan]UE_DEMO=1 ue status[/cyan]")
    console.print("  [cyan]UE_DEMO=1 ue am[/cyan]")
    console.print("  [cyan]UE_DEMO=1 ue did[/cyan]")
    console.print("  [cyan]UE_DEMO=1 ue done[/cyan]")
    console.print("  [cyan]UE_DEMO=1 ue task add[/cyan]")


@click.command("demo-reset")
def demo_reset():
    """Reset demo data. Only works in demo mode (UE_DEMO=1)."""
    import shutil
    from ue.config import DEMO_MODE, DATA_DIR

    if not DEMO_MODE:
        console.print("[red]Demo reset only works in demo mode.[/red]")
        console.print("Run with: [cyan]UE_DEMO=1 ue demo-reset[/cyan]")
        return

    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
        console.print(f"[yellow]Removed {DATA_DIR}[/yellow]")
    else:
        console.print("[dim]Demo directory doesn't exist[/dim]")

    console.print("\nRun [cyan]UE_DEMO=1 ue demo-setup[/cyan] to recreate demo data")
