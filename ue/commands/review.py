"""Weekly and monthly review commands."""

import click
from datetime import timedelta
from collections import defaultdict

from ue.utils.display import console
from ue.utils.dates import get_effective_date
from ue.utils.analysis import (
    calculate_block_streak,
    calculate_completion_rate,
    compare_weeks,
    get_week_bounds,
)


@click.command()
def week():
    """Weekly review - see patterns and progress for the week."""
    from rich.panel import Panel
    from rich.table import Table
    from ue.commands.sync import auto_sync_if_stale
    from ue.db import (
        get_block_targets,
        get_block_completions,
        get_tasks_completed_since,
        get_tasks,
        get_overdue_tasks,
        get_activity,
    )

    auto_sync_if_stale()

    today = get_effective_date()
    week_start, week_end = get_week_bounds(today, weeks_ago=0)
    prev_week_start, prev_week_end = get_week_bounds(today, weeks_ago=1)

    week_start_str = week_start.isoformat()
    week_end_str = week_end.isoformat()
    prev_week_start_str = prev_week_start.isoformat()
    prev_week_end_str = prev_week_end.isoformat()

    # Days elapsed in current week
    days_elapsed = today.weekday() + 1

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}[/bold]",
            style="blue",
        )
    )

    # === BLOCKS ===
    targets = get_block_targets()

    if targets:
        # Get all completions for current and previous week (for streak calculation)
        all_completions = get_block_completions(since=prev_week_start_str)
        current_week_completions = [
            c for c in all_completions if c["date"] >= week_start_str
        ]
        prev_week_completions = [
            c for c in all_completions
            if prev_week_start_str <= c["date"] <= prev_week_end_str
        ]

        console.print("\n[bold dim]BLOCKS[/bold dim]")
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Block", width=16)
        table.add_column("Progress", width=10)
        table.add_column("Rate", width=6, justify="right")
        table.add_column("Streak", width=8, justify="right")
        table.add_column("vs Last", width=12)

        for target in targets:
            name = target["block_name"]
            weekly_target = target["weekly_target"]

            # Current week completions for this block
            completed = sum(
                1 for c in current_week_completions
                if c["block_name"] == name and c["status"] == "completed"
            )

            # Previous week completions for this block
            prev_completed = sum(
                1 for c in prev_week_completions
                if c["block_name"] == name and c["status"] == "completed"
            )

            # Calculate metrics
            if weekly_target == 0:
                # Daily block
                progress = f"{completed}/{days_elapsed}"
                rate = calculate_completion_rate(completed, 0, days_elapsed)
            else:
                progress = f"{completed}/{weekly_target}"
                rate = calculate_completion_rate(completed, weekly_target, days_elapsed)

            streak = calculate_block_streak(name, all_completions)
            streak_str = f"{streak} day{'s' if streak != 1 else ''}" if streak > 0 else "-"

            # Comparison to last week
            if prev_completed == 0 and completed > 0:
                vs_last = "[dim]new[/dim]"
            else:
                vs_last = compare_weeks(completed, prev_completed)

            # Color coding
            rate_str = f"{rate:.0f}%"
            if rate >= 80:
                rate_str = f"[green]{rate_str}[/green]"
            elif rate >= 50:
                rate_str = f"[yellow]{rate_str}[/yellow]"
            else:
                rate_str = f"[red]{rate_str}[/red]"

            table.add_row(name[:16], progress, rate_str, streak_str, vs_last)

        console.print(table)

    # === TASKS ===
    completed_tasks = get_tasks_completed_since(week_start_str + "T00:00:00")
    pending_tasks = get_tasks(status="pending")
    overdue_tasks = get_overdue_tasks()

    console.print("\n[bold dim]TASKS[/bold dim]")
    console.print(f"  [green]\u2713[/green] Completed: {len(completed_tasks)}")
    console.print(f"  [dim]\u25cb[/dim] Pending: {len(pending_tasks)}")
    if overdue_tasks:
        console.print(f"  [red]![/red] Overdue: {len(overdue_tasks)}")

    # === WINS ===
    activity = get_activity(since=week_start_str + "T00:00:00", limit=500)
    wins = [a for a in activity if a["activity_type"] == "win"]

    if wins:
        console.print("\n[bold dim]WINS THIS WEEK[/bold dim]")
        for win in wins[:5]:
            console.print(f"  [green]\u2022[/green] {win['description']}")
        if len(wins) > 5:
            console.print(f"  [dim]...and {len(wins) - 5} more[/dim]")

    # === ACTIVITY ===
    by_type = defaultdict(int)
    for act in activity:
        by_type[act["activity_type"]] += 1

    # Only show if there's activity beyond wins
    other_activity = {k: v for k, v in by_type.items() if k != "win"}
    if other_activity:
        console.print("\n[bold dim]ACTIVITY[/bold dim]")
        for act_type, count in sorted(other_activity.items(), key=lambda x: -x[1]):
            label = act_type.replace("_", " ").title()
            console.print(f"  {label}: {count}")

    console.print()


@click.command()
def month():
    """Monthly review - see trends and patterns over 4 weeks."""
    from rich.panel import Panel
    from rich.table import Table
    from ue.commands.sync import auto_sync_if_stale
    from ue.db import (
        get_block_targets,
        get_block_completions_range,
        get_tasks_completed_since,
        get_activity,
    )
    from ue.config import load_config

    auto_sync_if_stale()

    today = get_effective_date()

    # Get 4 weeks of data
    weeks = []
    for i in range(4):
        start, end = get_week_bounds(today, weeks_ago=3 - i)  # Oldest first
        weeks.append((start, end))

    month_start = weeks[0][0]
    month_end = weeks[3][1]

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]Monthly Review ({month_start.strftime('%b %d')} - {month_end.strftime('%b %d')})[/bold]",
            style="blue",
        )
    )

    # === BLOCK TRENDS ===
    targets = get_block_targets()

    if targets:
        all_completions = get_block_completions_range(
            month_start.isoformat(), month_end.isoformat()
        )

        console.print("\n[bold dim]BLOCK TRENDS (4 weeks)[/bold dim]")
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Block", width=14)
        table.add_column("W1", width=5, justify="center")
        table.add_column("W2", width=5, justify="center")
        table.add_column("W3", width=5, justify="center")
        table.add_column("W4", width=5, justify="center")
        table.add_column("Avg", width=5, justify="right")
        table.add_column("Streak", width=8, justify="right")

        for target in targets:
            name = target["block_name"]
            weekly_target = target["weekly_target"]

            week_counts = []
            for start, end in weeks:
                count = sum(
                    1 for c in all_completions
                    if c["block_name"] == name
                    and c["status"] == "completed"
                    and start.isoformat() <= c["date"] <= end.isoformat()
                )
                week_counts.append(count)

            # Calculate average
            total = sum(week_counts)
            if weekly_target == 0:
                # Daily - average per week (out of 7)
                avg = (total / 28) * 7  # Average weekly completions
                avg_pct = (avg / 7) * 100
            else:
                avg_pct = (total / (weekly_target * 4)) * 100

            # Format week columns
            def fmt_week(count, target):
                if target == 0:
                    return f"{count}/7"
                return f"{count}/{target}"

            # Color the average
            avg_str = f"{avg_pct:.0f}%"
            if avg_pct >= 80:
                avg_str = f"[green]{avg_str}[/green]"
            elif avg_pct >= 50:
                avg_str = f"[yellow]{avg_str}[/yellow]"
            else:
                avg_str = f"[red]{avg_str}[/red]"

            # Get current streak (need more completions for streak calc)
            streak_completions = get_block_completions_range(
                (today - timedelta(days=60)).isoformat(), today.isoformat()
            )
            streak = calculate_block_streak(name, streak_completions)
            streak_str = f"{streak}d" if streak > 0 else "-"

            table.add_row(
                name[:14],
                fmt_week(week_counts[0], weekly_target),
                fmt_week(week_counts[1], weekly_target),
                fmt_week(week_counts[2], weekly_target),
                fmt_week(week_counts[3], weekly_target),
                avg_str,
                streak_str,
            )

        console.print(table)

    # === TASK VELOCITY ===
    console.print("\n[bold dim]TASK VELOCITY[/bold dim]")
    week_task_counts = []
    peak_week = 0
    peak_count = 0

    for i, (start, end) in enumerate(weeks):
        completed = get_tasks_completed_since(start.isoformat() + "T00:00:00")
        # Filter to tasks completed within this week
        week_completed = [
            t for t in completed
            if t["completed_at"] and t["completed_at"][:10] <= end.isoformat()
        ]
        count = len(week_completed)
        week_task_counts.append(count)
        if count > peak_count:
            peak_count = count
            peak_week = i

    for i, count in enumerate(week_task_counts):
        label = f"Week {i + 1}"
        peak_marker = " [green]<- peak[/green]" if i == peak_week and count > 0 else ""
        console.print(f"  {label}: {count} completed{peak_marker}")

    # Trend calculation
    if len(week_task_counts) >= 2:
        first_half = sum(week_task_counts[:2])
        second_half = sum(week_task_counts[2:])
        if second_half > first_half * 1.2:
            trend = "[green]↑ trending up[/green]"
        elif second_half < first_half * 0.8:
            trend = "[red]↓ trending down[/red]"
        else:
            trend = "[dim]→ stable[/dim]"
        console.print(f"  Trend: {trend}")

    # === WINS ===
    activity = get_activity(since=month_start.isoformat() + "T00:00:00", limit=1000)
    wins = [a for a in activity if a["activity_type"] == "win"]

    if wins:
        console.print(f"\n[bold dim]WINS THIS MONTH ({len(wins)})[/bold dim]")
        for win in wins[:5]:
            console.print(f"  [green]\u2022[/green] {win['description']}")
        if len(wins) > 5:
            console.print(f"  [dim]...and {len(wins) - 5} more[/dim]")

    # === WORKSTREAM DISTRIBUTION ===
    config = load_config()
    workstreams = config.get("workstreams", {})

    if workstreams and activity:
        by_ws = defaultdict(int)
        for act in activity:
            ws = act["workstream"] or "(unassigned)"
            by_ws[ws] += 1

        total = sum(by_ws.values())
        if total > 0:
            console.print("\n[bold dim]WORKSTREAM DISTRIBUTION[/bold dim]")
            for ws, count in sorted(by_ws.items(), key=lambda x: -x[1]):
                pct = (count / total) * 100
                bar_len = int(pct / 5)  # Scale to max ~20 chars
                bar = "\u2588" * bar_len
                console.print(f"  {ws}: {pct:.0f}% {bar}")

    console.print()
