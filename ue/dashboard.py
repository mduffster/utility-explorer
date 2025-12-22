"""Dashboard views."""

from datetime import datetime, timedelta
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ue.db import get_inbox_items, get_activity
from ue.config import load_config


console = Console()


def show_dashboard():
    """Show the main dashboard."""
    config = load_config()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=7)).isoformat()

    # Get inbox items needing response
    needs_response = get_inbox_items(needs_response=True, limit=20)

    # Get today's activity
    today_activity = get_activity(since=today_start)
    week_activity = get_activity(since=week_start)

    # Header
    console.print()
    console.print(Panel(
        f"[bold]Utility Explorer[/bold] - {now.strftime('%A, %B %d, %Y')}",
        style="blue"
    ))

    # Nudges
    if needs_response:
        oldest = min(needs_response, key=lambda x: x["timestamp"])
        oldest_date = datetime.fromisoformat(oldest["timestamp"].replace("Z", ""))
        days_old = (now - oldest_date).days

        nudge = Text()
        nudge.append(f"\n  {len(needs_response)} items need response", style="yellow bold")
        if days_old > 0:
            nudge.append(f" (oldest: {days_old} days)", style="red" if days_old > 3 else "yellow")
        console.print(nudge)

    # Inbox section
    console.print("\n[bold underline]INBOX[/bold underline]")

    if needs_response:
        inbox_table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        inbox_table.add_column("Source", style="dim", width=10)
        inbox_table.add_column("From", width=25)
        inbox_table.add_column("Subject", width=40)
        inbox_table.add_column("Age", width=8)
        inbox_table.add_column("Stream", width=12)

        for item in needs_response[:10]:
            item_date = datetime.fromisoformat(item["timestamp"].replace("Z", ""))
            age_days = (now - item_date).days
            age_str = f"{age_days}d" if age_days > 0 else "today"
            age_style = "red" if age_days > 3 else ("yellow" if age_days > 1 else "")

            inbox_table.add_row(
                item["source"],
                (item["sender"] or "")[:25],
                (item["subject"] or "")[:40],
                Text(age_str, style=age_style),
                item["workstream"] or "-",
            )

        console.print(inbox_table)
    else:
        console.print("  [dim]No items marked as needing response[/dim]")

    # Activity section
    console.print("\n[bold underline]TODAY'S ACTIVITY[/bold underline]")

    if today_activity:
        # Group by type
        by_type = defaultdict(list)
        for act in today_activity:
            by_type[act["activity_type"]].append(act)

        for act_type, items in by_type.items():
            icon = {
                "email_sent": "[green]",
                "commit": "[blue]",
                "application": "[magenta]",
                "win": "[yellow]",
            }.get(act_type, "")
            console.print(f"  {icon}{act_type}[/]: {len(items)}")
            for item in items[:3]:
                console.print(f"    [dim]- {item['description'][:60]}[/dim]")
    else:
        console.print("  [dim]No activity logged today[/dim]")

    # Week summary
    console.print("\n[bold underline]THIS WEEK[/bold underline]")

    week_by_type = defaultdict(int)
    for act in week_activity:
        week_by_type[act["activity_type"]] += 1

    if week_by_type:
        summary_parts = []
        for act_type, count in sorted(week_by_type.items()):
            summary_parts.append(f"{count} {act_type}")
        console.print(f"  {', '.join(summary_parts)}")
    else:
        console.print("  [dim]No activity logged this week[/dim]")

    console.print()


def show_inbox(source: str = None, limit: int = 20):
    """Show inbox items."""
    items = get_inbox_items(source=source, limit=limit)

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=8)
    table.add_column("Source", width=10)
    table.add_column("From", width=25)
    table.add_column("Subject", width=45)
    table.add_column("Time", width=12)
    table.add_column("Needs Reply", width=10)

    for i, item in enumerate(items):
        needs = "[yellow]YES[/yellow]" if item["needs_response"] else ""
        timestamp = item["timestamp"][:10] if item["timestamp"] else ""

        table.add_row(
            str(i + 1),
            item["source"],
            (item["sender"] or "")[:25],
            (item["subject"] or "")[:45],
            timestamp,
            needs,
        )

    console.print(table)


def show_activity(days: int = 7, activity_type: str = None):
    """Show activity log."""
    since = (datetime.now() - timedelta(days=days)).isoformat()
    items = get_activity(since=since, activity_type=activity_type)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", width=12)
    table.add_column("Type", width=15)
    table.add_column("Description", width=50)
    table.add_column("Stream", width=12)

    for item in items:
        timestamp = item["timestamp"][:10] if item["timestamp"] else ""
        table.add_row(
            timestamp,
            item["activity_type"],
            item["description"][:50],
            item["workstream"] or "-",
        )

    console.print(table)


def show_calendar(days: int = 7):
    """Show upcoming calendar events."""
    from ue.db import get_db

    now = datetime.now()
    future = now + timedelta(days=days)

    db = get_db()
    items = db.execute(
        """
        SELECT subject, sender, timestamp, snippet FROM inbox_items
        WHERE source = 'calendar'
        AND timestamp >= ?
        AND timestamp <= ?
        ORDER BY timestamp ASC
        """,
        (now.isoformat(), future.isoformat()),
    ).fetchall()
    db.close()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", width=12)
    table.add_column("Time", width=8)
    table.add_column("Event", width=40)
    table.add_column("With", width=30)

    for item in items:
        ts = item["timestamp"]
        date_str = ts[:10] if ts else ""
        time_str = ts[11:16] if ts and len(ts) > 11 else ""

        table.add_row(
            date_str,
            time_str,
            (item["subject"] or "")[:40],
            (item["sender"] or "")[:30],
        )

    console.print(table)
