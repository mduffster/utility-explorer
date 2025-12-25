"""Block tracking commands."""

import click
from ue.utils.display import console
from ue.utils.dates import get_effective_date


@click.group()
def block():
    """Track time block completions."""
    pass


@block.command("done")
@click.argument("name")
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD), defaults to today")
@click.option("--notes", "-n", help="Optional notes")
@click.option("--minutes", "-m", type=int, help="Duration in minutes")
def block_done(name, date, notes, minutes):
    """Mark a block as completed."""
    from ue.db import log_block_completion

    if date is None:
        date = get_effective_date().isoformat()

    log_block_completion(
        block_name=name,
        date=date,
        status="completed",
        notes=notes,
        duration_minutes=minutes,
    )
    console.print(f"[green]Marked '{name}' as completed for {date}[/green]")


@block.command("skip")
@click.argument("name")
@click.option("--reason", "-r", required=True, help="Why was it skipped?")
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD), defaults to today")
def block_skip(name, reason, date):
    """Mark a block as skipped with a reason."""
    from ue.db import log_block_completion

    if date is None:
        date = get_effective_date().isoformat()

    log_block_completion(
        block_name=name,
        date=date,
        status="skipped",
        reason=reason,
    )
    console.print(f"[yellow]Marked '{name}' as skipped for {date}[/yellow]")


@block.command("partial")
@click.argument("name")
@click.option("--reason", "-r", help="What happened?")
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD), defaults to today")
@click.option("--minutes", "-m", type=int, help="Duration in minutes")
def block_partial(name, reason, date, minutes):
    """Mark a block as partially completed."""
    from ue.db import log_block_completion

    if date is None:
        date = get_effective_date().isoformat()

    log_block_completion(
        block_name=name,
        date=date,
        status="partial",
        reason=reason,
        duration_minutes=minutes,
    )
    console.print(f"[blue]Marked '{name}' as partial for {date}[/blue]")


@block.command("target")
@click.argument("name")
@click.argument("weekly_count", type=int)
@click.option("--workstream", "-w", help="Associated workstream")
def block_target(name, weekly_count, workstream):
    """Set weekly target for a block (0 = daily)."""
    from ue.db import set_block_target

    set_block_target(block_name=name, weekly_target=weekly_count, workstream=workstream)
    if weekly_count == 0:
        console.print(f"[green]Set '{name}' as a daily block[/green]")
    else:
        console.print(f"[green]Set '{name}' target: {weekly_count}x per week[/green]")


@block.command("list")
def block_list():
    """Show today's blocks and weekly progress."""
    from datetime import timedelta
    from rich.table import Table
    from ue.db import get_block_targets, get_block_completions, get_week_block_summary

    targets = get_block_targets()
    today = get_effective_date()
    today_str = today.isoformat()
    week_start = (today - timedelta(days=today.weekday())).isoformat()

    if not targets:
        console.print("[dim]No block targets set. Use 'ue block target <name> <weekly_count>'[/dim]")
        return

    table = Table(title=f"Blocks - Week of {week_start}", show_header=True, header_style="bold")
    table.add_column("Block", width=20)
    table.add_column("Target", width=10)
    table.add_column("Done", width=8)
    table.add_column("Today", width=10)
    table.add_column("Stream", width=12)

    # Get today's completions
    today_completions = {c["block_name"]: c for c in get_block_completions(since=today_str)}

    for target in targets:
        name = target["block_name"]
        weekly = target["weekly_target"]
        summary = get_week_block_summary(name)

        target_str = "daily" if weekly == 0 else f"{weekly}x/wk"
        done_str = str(summary["completed"])

        # Color coding
        if weekly > 0:
            if summary["completed"] >= weekly:
                done_str = f"[green]{done_str}[/green]"
            elif summary["completed"] >= weekly // 2:
                done_str = f"[yellow]{done_str}[/yellow]"
            else:
                done_str = f"[red]{done_str}[/red]"

        # Today's status
        today_status = "-"
        if name in today_completions:
            status = today_completions[name]["status"]
            if status == "completed":
                today_status = "[green]done[/green]"
            elif status == "skipped":
                today_status = "[red]skipped[/red]"
            elif status == "partial":
                today_status = "[yellow]partial[/yellow]"

        table.add_row(
            name,
            target_str,
            done_str,
            today_status,
            target.get("workstream") or "-",
        )

    console.print(table)


# Standalone did command for interactive block completion
@click.command("did")
def did():
    """Interactive block completion - pick a block you just did."""
    from rich.prompt import Prompt
    from ue.db import get_block_targets, get_block_completions, log_block_completion, get_week_block_summary

    targets = get_block_targets()

    if not targets:
        console.print("[dim]No blocks configured. Use 'ue block target <name> <weekly_count>'[/dim]")
        return

    today = get_effective_date().isoformat()
    today_completions = {c["block_name"]: c for c in get_block_completions(since=today)}

    console.print("\n[bold]Blocks:[/bold]\n")
    for i, t in enumerate(targets, 1):
        name = t["block_name"]
        weekly = t["weekly_target"]
        summary = get_week_block_summary(name)

        # Status indicator
        if name in today_completions:
            status = today_completions[name]["status"]
            if status == "completed":
                status_str = " [green]✓ done today[/green]"
            elif status == "skipped":
                status_str = " [yellow]skipped today[/yellow]"
            else:
                status_str = " [blue]partial today[/blue]"
        else:
            status_str = ""

        # Progress
        if weekly == 0:
            progress = "[dim](daily)[/dim]"
        else:
            progress = f"[dim]({summary['completed']}/{weekly} this week)[/dim]"

        console.print(f"  {i}. {name} {progress}{status_str}")

    console.print()
    choice = Prompt.ask(
        "Which did you do? (number or 'q' to quit)",
        default="q"
    )

    if choice.lower() == 'q':
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(targets):
            block = targets[idx]
            log_block_completion(block["block_name"], today, "completed")
            console.print(f"\n[green]Logged: {block['block_name']} ✓[/green]")
        else:
            console.print("[red]Invalid number[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")
