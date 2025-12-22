"""Command-line interface."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option()
def cli():
    """Utility Explorer - Personal productivity tools."""
    pass


@cli.command()
def setup():
    """Set up Google API credentials."""
    from ue.config import CREDENTIALS_PATH, DATA_DIR

    console.print("\n[bold]Google API Setup[/bold]\n")
    console.print("To use Gmail and Calendar integration, you need to:")
    console.print()
    console.print("1. Go to [link]https://console.cloud.google.com/[/link]")
    console.print("2. Create a new project (or select existing)")
    console.print("3. Enable the Gmail API and Google Calendar API:")
    console.print("   - Go to 'APIs & Services' > 'Library'")
    console.print("   - Search for 'Gmail API' and enable it")
    console.print("   - Search for 'Google Calendar API' and enable it")
    console.print("4. Create OAuth credentials:")
    console.print("   - Go to 'APIs & Services' > 'Credentials'")
    console.print("   - Click 'Create Credentials' > 'OAuth client ID'")
    console.print("   - Select 'Desktop application'")
    console.print("   - Download the JSON file")
    console.print(f"5. Save the file as: [cyan]{CREDENTIALS_PATH}[/cyan]")
    console.print()
    console.print(f"Data directory: [cyan]{DATA_DIR}[/cyan]")

    if CREDENTIALS_PATH.exists():
        console.print("\n[green]credentials.json found![/green]")
        console.print("Run [cyan]ue sync[/cyan] to authenticate and fetch data.")
    else:
        console.print(f"\n[yellow]Waiting for credentials.json at {CREDENTIALS_PATH}[/yellow]")


@cli.command()
@click.option("--days", default=7, help="Days of history to sync")
def sync(days):
    """Sync data from Gmail, Calendar, and git."""
    from ue.inbox.gmail import sync_gmail_inbox, sync_gmail_sent
    from ue.inbox.calendar import sync_calendar
    from ue.activity.git import sync_git_commits

    console.print("[bold]Syncing...[/bold]\n")

    try:
        result = sync_gmail_inbox(days=days)
        console.print(f"  Gmail inbox: {result['fetched']} emails")
    except Exception as e:
        console.print(f"  [red]Gmail inbox error: {e}[/red]")

    try:
        result = sync_gmail_sent(days=days)
        console.print(f"  Gmail sent: {result['logged']} emails logged")
    except Exception as e:
        console.print(f"  [red]Gmail sent error: {e}[/red]")

    try:
        result = sync_calendar(days_ahead=days)
        console.print(f"  Calendar: {result['fetched']} events")
    except Exception as e:
        console.print(f"  [red]Calendar error: {e}[/red]")

    try:
        result = sync_git_commits(since_days=days)
        console.print(f"  Git: {result['logged']} commits from {result['repos_scanned']} repos")
    except Exception as e:
        console.print(f"  [red]Git error: {e}[/red]")

    console.print("\n[green]Sync complete![/green]")


@cli.command()
def dashboard():
    """Show the main dashboard."""
    from ue.dashboard import show_dashboard
    show_dashboard()


# Alias 'd' for dashboard
@cli.command("d")
def dashboard_short():
    """Show the main dashboard (shortcut)."""
    from ue.dashboard import show_dashboard
    show_dashboard()


@cli.command()
@click.option("--limit", "-n", default=20, help="Number of items to show")
def inbox(limit):
    """Show email inbox."""
    from ue.dashboard import show_inbox
    show_inbox(source="gmail", limit=limit)


@cli.command()
@click.option("--days", "-d", default=7, help="Days ahead to show")
def calendar(days):
    """Show upcoming calendar events."""
    from ue.dashboard import show_calendar
    show_calendar(days=days)


@cli.command()
@click.option("--days", "-d", default=7, help="Days of history")
@click.option("--type", "-t", "activity_type", help="Filter by type")
def activity(days, activity_type):
    """Show activity log."""
    from ue.dashboard import show_activity
    show_activity(days=days, activity_type=activity_type)


@cli.group()
def log():
    """Log activities manually."""
    pass


@log.command("application")
@click.argument("company")
@click.option("--role", "-r", help="Role/position applied for")
@click.option("--notes", "-n", help="Additional notes")
def log_application_cmd(company, role, notes):
    """Log a job application."""
    from ue.activity.manual import log_application
    log_application(company=company, role=role, notes=notes)
    console.print(f"[green]Logged application to {company}[/green]")


@log.command("win")
@click.argument("description")
@click.option("--workstream", "-w", help="Workstream (ai-research, terrasol, blog, consulting)")
@click.option("--notes", "-n", help="Additional notes")
def log_win_cmd(description, workstream, notes):
    """Log a win or accomplishment."""
    from ue.activity.manual import log_win
    log_win(description=description, workstream=workstream, notes=notes)
    console.print(f"[green]Logged win: {description}[/green]")


@cli.group()
def mark():
    """Mark inbox items."""
    pass


@mark.command("respond")
@click.argument("item_id")
def mark_needs_response(item_id):
    """Mark an item as needing response."""
    from ue.db import get_db

    db = get_db()
    # Handle both numeric index and full ID
    if item_id.isdigit():
        # Get by row number
        items = db.execute(
            "SELECT id FROM inbox_items ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (1, int(item_id) - 1)
        ).fetchall()
        if items:
            item_id = items[0]["id"]
        else:
            console.print("[red]Item not found[/red]")
            return

    db.execute("UPDATE inbox_items SET needs_response = 1 WHERE id = ?", (item_id,))
    db.commit()
    db.close()
    console.print(f"[green]Marked as needing response[/green]")


@mark.command("done")
@click.argument("item_id")
def mark_responded(item_id):
    """Mark an item as responded to."""
    from ue.db import get_db

    db = get_db()
    if item_id.isdigit():
        items = db.execute(
            "SELECT id FROM inbox_items ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (1, int(item_id) - 1)
        ).fetchall()
        if items:
            item_id = items[0]["id"]
        else:
            console.print("[red]Item not found[/red]")
            return

    db.execute(
        "UPDATE inbox_items SET needs_response = 0, responded = 1 WHERE id = ?",
        (item_id,)
    )
    db.commit()
    db.close()
    console.print(f"[green]Marked as done[/green]")


@mark.command("workstream")
@click.argument("item_id")
@click.argument("workstream")
def mark_workstream(item_id, workstream):
    """Assign a workstream to an item."""
    from ue.db import get_db

    valid = ["ai-research", "terrasol", "blog", "consulting"]
    if workstream not in valid:
        console.print(f"[red]Invalid workstream. Choose from: {', '.join(valid)}[/red]")
        return

    db = get_db()
    if item_id.isdigit():
        items = db.execute(
            "SELECT id FROM inbox_items ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (1, int(item_id) - 1)
        ).fetchall()
        if items:
            item_id = items[0]["id"]
        else:
            console.print("[red]Item not found[/red]")
            return

    db.execute("UPDATE inbox_items SET workstream = ? WHERE id = ?", (workstream, item_id))
    db.commit()
    db.close()
    console.print(f"[green]Assigned to {workstream}[/green]")


@cli.command()
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


# Task commands
@cli.group()
def task():
    """Manage time-sensitive tasks."""
    pass


@task.command("add")
@click.argument("title")
@click.option("--due", "-d", required=True, help="Due date (YYYY-MM-DD or 'wed', 'friday', etc.)")
@click.option("--workstream", "-w", help="Workstream")
@click.option("--priority", "-p", type=click.Choice(["low", "normal", "high"]), default="normal")
@click.option("--notes", "-n", help="Additional notes")
def task_add(title, due, workstream, priority, notes):
    """Add a task with a deadline."""
    from datetime import datetime, timedelta
    from ue.db import add_task

    # Parse natural language dates
    due_date = None
    if due:
        due_lower = due.lower()
        today = datetime.now().date()

        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_abbrevs = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

        if due_lower == "today":
            due_date = today.isoformat()
        elif due_lower == "tomorrow":
            due_date = (today + timedelta(days=1)).isoformat()
        elif due_lower in day_names or due_lower in day_abbrevs:
            # Find next occurrence of that day
            if due_lower in day_abbrevs:
                target_day = day_abbrevs.index(due_lower)
            else:
                target_day = day_names.index(due_lower)
            days_ahead = target_day - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            due_date = (today + timedelta(days=days_ahead)).isoformat()
        else:
            # Assume YYYY-MM-DD format
            due_date = due

    task_id = add_task(
        title=title,
        due_date=due_date,
        workstream=workstream,
        priority=priority,
        notes=notes,
    )

    if due_date:
        console.print(f"[green]Added task #{task_id}: {title} (due {due_date})[/green]")
    else:
        console.print(f"[green]Added task #{task_id}: {title}[/green]")


@task.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include completed tasks")
def task_list(show_all):
    """List pending tasks."""
    from datetime import datetime
    from rich.table import Table
    from ue.db import get_tasks, get_overdue_tasks

    tasks = get_tasks(status="pending")
    overdue = {t["id"] for t in get_overdue_tasks()}
    today = datetime.now().strftime("%Y-%m-%d")

    if not tasks:
        console.print("[dim]No pending tasks[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=4)
    table.add_column("Task", width=40)
    table.add_column("Due", width=12)
    table.add_column("Pri", width=6)
    table.add_column("Stream", width=12)

    for t in tasks:
        due_str = t["due_date"] or "-"
        if t["id"] in overdue:
            due_str = f"[red]{due_str} ![/red]"
        elif t["due_date"] == today:
            due_str = f"[yellow]{due_str}[/yellow]"

        pri_str = t["priority"]
        if t["priority"] == "high":
            pri_str = f"[red]{pri_str}[/red]"

        table.add_row(
            str(t["id"]),
            t["title"][:40],
            due_str,
            pri_str,
            t["workstream"] or "-",
        )

    console.print(table)


@task.command("done")
@click.argument("task_id", type=int)
def task_done(task_id):
    """Mark a task as complete."""
    from ue.db import complete_task
    complete_task(task_id)
    console.print(f"[green]Task #{task_id} completed![/green]")


@task.command("cancel")
@click.argument("task_id", type=int)
def task_cancel(task_id):
    """Cancel a task."""
    from ue.db import cancel_task
    cancel_task(task_id)
    console.print(f"[yellow]Task #{task_id} cancelled[/yellow]")


# Block tracking commands
@cli.group()
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
    from datetime import datetime
    from ue.db import log_block_completion

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

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
    from datetime import datetime
    from ue.db import log_block_completion

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

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
    from datetime import datetime
    from ue.db import log_block_completion

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

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
    from datetime import datetime, timedelta
    from rich.table import Table
    from ue.db import get_block_targets, get_block_completions, get_week_block_summary

    targets = get_block_targets()
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")

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
    today_completions = {c["block_name"]: c for c in get_block_completions(since=today)}

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


def get_at_risk_blocks():
    """Calculate which blocks are at risk of not being hit this week."""
    from datetime import datetime, timedelta
    from ue.db import get_block_targets, get_week_block_summary

    today = datetime.now().date()
    # Days left in week (0 = Monday, 6 = Sunday)
    day_of_week = today.weekday()
    days_left = 6 - day_of_week  # Including today

    targets = get_block_targets()
    at_risk = []

    for target in targets:
        name = target["block_name"]
        weekly_target = target["weekly_target"]

        if weekly_target == 0:
            # Daily block - not tracked as "at risk" in same way
            continue

        summary = get_week_block_summary(name)
        completed = summary["completed"]
        remaining = weekly_target - completed

        if remaining > 0 and remaining > days_left:
            # Can't possibly hit target
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "status": "impossible"
            })
        elif remaining > 0 and remaining == days_left:
            # Must do it every remaining day
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "status": "critical"
            })
        elif remaining > 0 and day_of_week >= 3:  # Thursday or later
            # It's late in week and still have items remaining
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "status": "warning"
            })

    return at_risk


@cli.command()
def am():
    """Morning standup - start your day."""
    from datetime import datetime, timedelta
    from rich.panel import Panel
    from ue.db import get_inbox_items, get_block_targets, get_block_completions
    from ue.db import get_upcoming_tasks, get_overdue_tasks
    from ue.inbox.calendar import get_upcoming_events

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    day_name = today.strftime("%A")
    date_str = today.strftime("%B %d, %Y")

    console.print()
    console.print(Panel(f"[bold]Good morning![/bold] {day_name}, {date_str}", style="blue"))

    # Overdue and upcoming tasks (DEADLINES)
    overdue = get_overdue_tasks()
    upcoming = get_upcoming_tasks(days=7)

    if overdue:
        console.print("\n[bold red]OVERDUE[/bold red]")
        for t in overdue:
            console.print(f"  [red]  {t['title']} (was due {t['due_date']})[/red]")

    # Show tasks due soon (not overdue)
    due_soon = [t for t in upcoming if t["due_date"] >= today_str]
    if due_soon:
        console.print("\n[bold yellow]DEADLINES[/bold yellow]")
        for t in due_soon[:5]:
            days_until = (datetime.strptime(t["due_date"], "%Y-%m-%d").date() - today.date()).days
            if days_until == 0:
                due_str = "[yellow]today[/yellow]"
            elif days_until == 1:
                due_str = "[yellow]tomorrow[/yellow]"
            else:
                due_str = f"in {days_until} days"
            console.print(f"    {t['title']} ({due_str})")

    # At-risk blocks
    at_risk = get_at_risk_blocks()
    if at_risk:
        console.print("\n[bold red]BLOCKS AT RISK[/bold red]")
        for block in at_risk:
            if block["status"] == "impossible":
                console.print(f"  [red]  {block['name']}: {block['completed']}/{block['target']} - can't hit target[/red]")
            elif block["status"] == "critical":
                console.print(f"  [red]  {block['name']}: {block['completed']}/{block['target']} - must do every remaining day[/red]")
            else:
                console.print(f"  [yellow]  {block['name']}: {block['completed']}/{block['target']} - {block['remaining']} left, {block['days_left']} days[/yellow]")
    else:
        console.print("\n[green]All blocks on track this week[/green]")

    # Today's calendar
    console.print("\n[bold]TODAY'S CALENDAR[/bold]")
    try:
        events = get_upcoming_events(hours=12)
        if events:
            for event in events[:8]:
                start = event.get("start", {})
                time_str = ""
                if "dateTime" in start:
                    dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M %p")
                summary = event.get("summary", "(no title)")
                console.print(f"  {time_str:>8}  {summary}")
        else:
            console.print("  [dim]No events today[/dim]")
    except Exception as e:
        console.print(f"  [dim]Could not fetch calendar: {e}[/dim]")

    # Inbox needing response
    needs_response = get_inbox_items(needs_response=True, limit=5)
    if needs_response:
        console.print(f"\n[bold yellow]NEEDS RESPONSE ({len(needs_response)})[/bold yellow]")
        for item in needs_response[:5]:
            age_days = (today - datetime.fromisoformat(item["timestamp"].replace("Z", ""))).days
            age_str = f"{age_days}d" if age_days > 0 else "today"
            console.print(f"  [{age_str}] {item['source']}: {(item['subject'] or '')[:50]}")

    # Suggested focus
    console.print("\n[bold]SUGGESTED FOCUS[/bold]")
    if at_risk:
        critical = [b for b in at_risk if b["status"] in ("impossible", "critical")]
        if critical:
            console.print(f"  [red]Priority: {critical[0]['name']} (at risk)[/red]")
        else:
            console.print(f"  [yellow]Consider: {at_risk[0]['name']} ({at_risk[0]['remaining']} remaining this week)[/yellow]")
    else:
        # Check for daily blocks not done today
        targets = get_block_targets()
        today_str = today.strftime("%Y-%m-%d")
        today_completions = {c["block_name"]: c for c in get_block_completions(since=today_str)}
        daily_blocks = [t for t in targets if t["weekly_target"] == 0]
        undone_daily = [b for b in daily_blocks if b["block_name"] not in today_completions]
        if undone_daily:
            console.print(f"  Daily: {', '.join(b['block_name'] for b in undone_daily)}")
        else:
            console.print("  [dim]All daily blocks done - nice![/dim]")

    console.print()


@cli.command()
def pm():
    """Evening review - end your day."""
    from datetime import datetime
    from rich.prompt import Prompt
    from rich.panel import Panel
    from ue.db import get_block_targets, get_block_completions, log_block_completion, get_activity
    from ue.activity.manual import log_win

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    console.print()
    console.print(Panel("[bold]Evening Review[/bold]", style="magenta"))

    # Show what was accomplished today
    today_activity = get_activity(since=today_str + "T00:00:00")
    if today_activity:
        console.print("\n[bold]TODAY'S ACTIVITY[/bold]")
        by_type = {}
        for act in today_activity:
            t = act["activity_type"]
            by_type[t] = by_type.get(t, 0) + 1
        for t, count in by_type.items():
            console.print(f"  {t}: {count}")

    # Walk through blocks
    console.print("\n[bold]BLOCK CHECK-IN[/bold]")
    targets = get_block_targets()
    today_completions = {c["block_name"]: c for c in get_block_completions(since=today_str)}

    for target in targets:
        name = target["block_name"]
        weekly = target["weekly_target"]

        # Skip 1x/week blocks if already done this week
        if weekly > 0 and weekly == 1:
            from ue.db import get_week_block_summary
            summary = get_week_block_summary(name)
            if summary["completed"] >= weekly:
                continue

        if name in today_completions:
            status = today_completions[name]["status"]
            console.print(f"  [dim]{name}: {status}[/dim]")
            continue

        # Only ask about daily blocks or blocks not yet hit this week
        if weekly == 0 or True:  # Ask about all for now
            response = Prompt.ask(
                f"  {name}",
                choices=["done", "skip", "partial", "n/a"],
                default="n/a"
            )

            if response == "done":
                log_block_completion(name, today_str, "completed")
                console.print(f"    [green]done[/green]")
            elif response == "skip":
                reason = Prompt.ask("    Why?", default="")
                log_block_completion(name, today_str, "skipped", reason=reason if reason else None)
                console.print(f"    [yellow]skipped[/yellow]")
            elif response == "partial":
                reason = Prompt.ask("    What happened?", default="")
                log_block_completion(name, today_str, "partial", reason=reason if reason else None)
                console.print(f"    [blue]partial[/blue]")
            # n/a = don't log anything

    # Capture any wins
    console.print("\n[bold]WINS[/bold]")
    win = Prompt.ask("  Any wins today? (or enter to skip)", default="")
    if win:
        log_win(win)
        console.print(f"    [green]logged![/green]")

    # Preview tomorrow
    at_risk = get_at_risk_blocks()
    if at_risk:
        console.print("\n[bold]TOMORROW'S PRIORITY[/bold]")
        for block in at_risk[:2]:
            console.print(f"  [yellow]{block['name']}: {block['remaining']} remaining, {block['days_left']} days left[/yellow]")

    console.print("\n[magenta]Good night![/magenta]\n")


# Keep old review as alias
@cli.command()
def review():
    """Daily review (alias for 'pm')."""
    from click import Context
    ctx = Context(pm)
    ctx.invoke(pm)


@cli.command()
@click.option("--copy", "copy_mode", is_flag=True, help="Print context for manual copy/paste instead of calling API")
def focus(copy_mode):
    """Get AI-powered recommendation for what to focus on now."""
    from ue.focus import get_focus, print_context

    if copy_mode:
        console.print(print_context())
        console.print("\n[dim]Copy the above and paste into claude.ai[/dim]")
        return

    try:
        result = get_focus()
        console.print()
        console.print(result)
        console.print()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]Error calling API: {e}[/red]")
        console.print("[dim]Try --copy mode to use claude.ai instead[/dim]")


if __name__ == "__main__":
    cli()
