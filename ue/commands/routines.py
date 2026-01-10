"""Daily routine commands - am, pm, status, focus."""

import click
from ue.utils.display import console, print_logo
from ue.utils.dates import get_effective_date
from ue.utils.analysis import get_at_risk_blocks
from ue.commands.sync import auto_sync_if_stale


@click.command()
def am():
    """Morning standup - start your day."""
    auto_sync_if_stale()
    from datetime import datetime, timedelta
    import json as json_mod
    from rich.panel import Panel
    from ue.db import get_inbox_items, get_block_targets, get_block_completions
    from ue.db import get_upcoming_tasks, get_overdue_tasks, get_activity
    from ue.inbox.calendar import get_upcoming_events
    from ue.config import load_config

    today = get_effective_date()
    today_str = today.isoformat()
    day_name = today.strftime("%A")
    date_str = today.strftime("%B %d, %Y")

    console.print()
    print_logo()
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
            days_until = (datetime.strptime(t["due_date"], "%Y-%m-%d").date() - today).days
            if days_until == 0:
                due_str = "[yellow]today[/yellow]"
            elif days_until == 1:
                due_str = "[yellow]tomorrow[/yellow]"
            else:
                due_str = f"in {days_until} days"
            console.print(f"    {t['title']} ({due_str})")

    # At-risk and behind-pace blocks
    at_risk = get_at_risk_blocks()
    if at_risk:
        # Sort by urgency: impossible > at_risk > try_to_do > daily_pending
        # Then by workstream priority within each tier
        config = load_config()
        workstreams = config.get("workstreams", {})
        priority_order = {"high": 0, "mid": 1, "low": 2}
        status_order = {"impossible": 0, "at_risk": 1, "try_to_do": 2, "daily_pending": 3}

        def sort_key(block):
            ws = block.get("workstream")
            ws_pri = priority_order.get(workstreams.get(ws, {}).get("priority", "low"), 2) if ws else 3
            return (status_order.get(block["status"], 4), ws_pri)

        sorted_blocks = sorted(at_risk, key=sort_key)

        # Show all critical (impossible/at_risk), but limit try_to_do to keep total at 3 max
        critical = [b for b in sorted_blocks if b["status"] in ("impossible", "at_risk")]
        others = [b for b in sorted_blocks if b["status"] not in ("impossible", "at_risk")]
        max_others = max(0, 3 - len(critical))
        to_show = critical + others[:max_others]

        console.print("\n[bold yellow]BLOCKS[/bold yellow]")
        for block in to_show:
            if block["status"] == "impossible":
                console.print(f"  [red]{block['name']}: {block['completed']}/{block['target']} - can't hit target[/red]")
            elif block["status"] == "at_risk":
                console.print(f"  [red]{block['name']}: {block['completed']}/{block['target']} - at risk[/red]")
            elif block["status"] == "try_to_do":
                console.print(f"  [yellow]{block['name']}: {block['completed']}/{block['target']} - try to do[/yellow]")
            elif block["status"] == "daily_pending":
                console.print(f"  [yellow]{block['name']}: not done today[/yellow]")
    else:
        console.print("\n[green]All blocks on track[/green]")

    # Today's calendar (only if Google is configured)
    from ue.config import is_google_configured
    if is_google_configured():
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

    # Recent commits by repo
    week_start = today - timedelta(days=today.weekday())
    week_activity = get_activity(activity_type="commit", since=week_start.isoformat())
    if week_activity:
        console.print("\n[bold]COMMITS THIS WEEK[/bold]")
        # Group by repo
        by_repo = {}
        for act in week_activity:
            if act.get("metadata"):
                try:
                    meta = json_mod.loads(act["metadata"])
                    repo = meta.get("repo", "unknown")
                    by_repo[repo] = by_repo.get(repo, 0) + 1
                except Exception:
                    pass
        for repo, count in sorted(by_repo.items(), key=lambda x: -x[1]):
            console.print(f"  {repo}: {count} commit{'s' if count != 1 else ''}")
    else:
        # Empty state handling - show hint once if git not configured
        from ue.config import is_git_hint_dismissed, load_config
        from ue.activity.git import is_github_cli_available

        config = load_config()
        repos = config.get("git_repos", [])
        gh_available = is_github_cli_available()

        # Only show hint if: no repos AND gh not available AND hint not dismissed
        if not repos and not gh_available and not is_git_hint_dismissed():
            console.print("\n[bold dim]COMMITS[/bold dim]")
            console.print("  [dim]No git tracking configured.[/dim]")
            console.print("  [dim]Run 'ue add-repo <path>' or 'gh auth login'[/dim]")
            console.print("  [dim]('ue git dismiss' to hide this)[/dim]")

    # Check for missed days
    show_catchup_hint()

    # Suggested focus
    console.print("\n[bold]SUGGESTED FOCUS[/bold]")
    if at_risk:
        # Get workstream priorities
        config = load_config()
        workstreams = config.get("workstreams", {})
        priority_order = {"high": 0, "mid": 1, "low": 2}

        # Get block -> workstream mapping
        block_targets = {t["block_name"]: t.get("workstream") for t in get_block_targets()}

        def get_priority(block):
            ws = block_targets.get(block["name"])
            if ws and ws in workstreams:
                return priority_order.get(workstreams[ws].get("priority", "low"), 2)
            return 3  # No workstream = lowest priority

        # Priority order: impossible > at_risk > try_to_do > daily_pending
        # Within each tier, sort by workstream priority
        critical = sorted([b for b in at_risk if b["status"] in ("impossible", "at_risk")], key=get_priority)
        try_to_do = sorted([b for b in at_risk if b["status"] == "try_to_do"], key=get_priority)
        daily = sorted([b for b in at_risk if b["status"] == "daily_pending"], key=get_priority)

        if critical:
            console.print(f"  [red]Priority: {critical[0]['name']} ({critical[0]['completed']}/{critical[0]['target']} - at risk)[/red]")
        elif try_to_do:
            console.print(f"  [yellow]Try to do: {try_to_do[0]['name']} ({try_to_do[0]['completed']}/{try_to_do[0]['target']})[/yellow]")
        elif daily:
            console.print(f"  [yellow]Today: {', '.join(b['name'] for b in daily)}[/yellow]")
    else:
        console.print("  [green]All blocks on track - nice![/green]")

    console.print()


@click.command()
def pm():
    """Evening review - end your day."""
    from rich.prompt import Prompt
    from rich.panel import Panel
    from ue.db import get_block_targets, get_block_completions, log_block_completion, get_activity
    from ue.db import get_week_block_summary
    from ue.activity.manual import log_win

    today = get_effective_date()
    today_str = today.isoformat()

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

    # Check for missed days
    show_catchup_hint()

    console.print("\n[magenta]Good night![/magenta]\n")


@click.command()
def review():
    """Daily review (alias for 'pm')."""
    from click import Context
    ctx = Context(pm)
    ctx.invoke(pm)


@click.command()
def status():
    """Show week-to-date status with completed and pending tasks."""
    auto_sync_if_stale()
    from datetime import datetime, timedelta
    from rich.panel import Panel
    from ue.db import (
        get_tasks, get_tasks_completed_since, get_overdue_tasks,
        get_block_targets, get_week_block_summary
    )

    today = get_effective_date()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.isoformat()
    day_name = today.strftime("%A")
    day_of_week = today.weekday()  # 0=Mon, 6=Sun
    days_elapsed = day_of_week + 1  # Mon=1, Sun=7

    console.print()
    console.print(Panel(
        f"[bold]Week Status[/bold] - {week_start.strftime('%b %d')} to {today.strftime('%b %d')} ({day_name})",
        style="cyan"
    ))

    # === BLOCKS SECTION ===
    targets = get_block_targets()
    if targets:
        console.print(f"\n[bold]Blocks[/bold]")

        for target in targets:
            name = target["block_name"]
            weekly = target["weekly_target"]
            summary = get_week_block_summary(name)
            completed = summary["completed"]

            if weekly == 0:
                # Daily block - show completed/days elapsed
                target_str = f"{completed}/{days_elapsed} days"
                if completed >= days_elapsed:
                    console.print(f"  [green]{name}: {target_str}[/green]")
                elif completed >= days_elapsed - 1:
                    console.print(f"  [yellow]{name}: {target_str}[/yellow]")
                else:
                    console.print(f"  [red]{name}: {target_str}[/red]")
            else:
                # Weekly target block
                target_str = f"{completed}/{weekly}"
                if completed >= weekly:
                    console.print(f"  [green]{name}: {target_str}[/green]")
                elif completed >= weekly // 2:
                    console.print(f"  [yellow]{name}: {target_str}[/yellow]")
                else:
                    console.print(f"  [red]{name}: {target_str}[/red]")

    # === TASKS SECTION ===
    # Get completed tasks this week
    completed_tasks = get_tasks_completed_since(week_start_str)

    # Get pending tasks
    pending = get_tasks(status="pending")
    overdue = get_overdue_tasks()
    overdue_ids = {t["id"] for t in overdue}

    # Summary counts
    console.print(f"\n[bold]Tasks[/bold]")
    console.print(f"  Completed this week: [green]{len(completed_tasks)}[/green]")
    console.print(f"  Still pending:       [yellow]{len(pending)}[/yellow]")
    if overdue:
        console.print(f"  Overdue:             [red]{len(overdue)}[/red]")

    # Completed tasks list
    if completed_tasks:
        console.print(f"\n[bold green]Completed This Week ({len(completed_tasks)})[/bold green]")
        for t in completed_tasks:
            completed_dt = datetime.fromisoformat(t["completed_at"])
            day_str = completed_dt.strftime("%a")
            ws_str = f" [dim]({t['workstream']})[/dim]" if t["workstream"] else ""
            console.print(f"  [green][/green] {t['title']}{ws_str} [dim]{day_str}[/dim]")
    else:
        console.print(f"\n[dim]No tasks completed this week yet[/dim]")

    # Pending tasks list
    if pending:
        console.print(f"\n[bold yellow]Still To Do ({len(pending)})[/bold yellow]")
        for t in pending:
            due_str = ""
            if t["due_date"]:
                if t["id"] in overdue_ids:
                    due_str = f" [red](overdue: {t['due_date']})[/red]"
                elif t["due_date"] == today.isoformat():
                    due_str = f" [yellow](due today)[/yellow]"
                else:
                    due_str = f" [dim](due {t['due_date']})[/dim]"

            pri_marker = ""
            if t["priority"] == "high":
                pri_marker = "[red]![/red] "

            ws_str = f" [dim]({t['workstream']})[/dim]" if t["workstream"] else ""
            console.print(f"  {pri_marker}{t['title']}{ws_str}{due_str}")
    else:
        console.print(f"\n[green]All tasks complete![/green]")

    # Check for missed days
    show_catchup_hint()

    console.print()


@click.command()
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


def show_catchup_hint():
    """Show hint about missed days if any consecutive days have no activity."""
    from ue.utils.analysis import get_consecutive_missed_days

    missed = get_consecutive_missed_days()
    if not missed:
        return

    if len(missed) == 1:
        day_str = missed[0].strftime("%b %d")
        console.print(f"\n[dim]You didn't log activity on {day_str}. Run 'ue catchup' to log.[/dim]")
    else:
        first = missed[0].strftime("%b %d")
        last = missed[-1].strftime("%b %d")
        console.print(f"\n[dim]You didn't log activity on {first} - {last}. Run 'ue catchup' to log.[/dim]")


@click.command()
def catchup():
    """Log blocks for days you missed."""
    from rich.prompt import Prompt
    from rich.panel import Panel
    from ue.utils.analysis import get_consecutive_missed_days
    from ue.db import get_block_targets, get_block_completions, log_block_completion
    from ue.activity.manual import log_win

    missed = get_consecutive_missed_days()

    if not missed:
        console.print("\n[green]No missed days to catch up on![/green]\n")
        return

    console.print()
    console.print(Panel("[bold]Catch Up[/bold] - Log blocks for missed days", style="cyan"))

    # Show missed days and let user pick which to review
    console.print("\n[bold]Days with no activity:[/bold]\n")
    for i, day in enumerate(missed, 1):
        day_name = day.strftime("%A")
        day_str = day.strftime("%b %d")
        console.print(f"  {i}. {day_name}, {day_str}")

    console.print()
    console.print("[dim]Enter numbers to review (e.g., '1,3' or '1-3' or 'all'), or 'q' to quit[/dim]")
    choice = Prompt.ask("Which days?", default="all")

    if choice.lower() == 'q':
        return

    # Parse selection
    selected_indices = set()
    if choice.lower() == 'all':
        selected_indices = set(range(len(missed)))
    else:
        for part in choice.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-')
                    for i in range(int(start) - 1, int(end)):
                        if 0 <= i < len(missed):
                            selected_indices.add(i)
                except ValueError:
                    pass
            else:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(missed):
                        selected_indices.add(idx)
                except ValueError:
                    pass

    if not selected_indices:
        console.print("[dim]No valid days selected[/dim]")
        return

    selected_days = [missed[i] for i in sorted(selected_indices)]
    targets = get_block_targets()

    # Review each selected day
    for day in selected_days:
        day_name = day.strftime("%A")
        day_str = day.strftime("%b %d")
        date_iso = day.isoformat()

        console.print()
        console.print(Panel(f"[bold]{day_name}, {day_str}[/bold]", style="yellow"))

        # Get any existing completions for this day (shouldn't be any, but check)
        day_completions = {
            c["block_name"]: c
            for c in get_block_completions(since=date_iso)
            if c["date"] == date_iso
        }

        for target in targets:
            name = target["block_name"]

            if name in day_completions:
                status = day_completions[name]["status"]
                console.print(f"  [dim]{name}: {status}[/dim]")
                continue

            response = Prompt.ask(
                f"  {name}",
                choices=["done", "skip", "partial", "n/a"],
                default="n/a"
            )

            if response == "done":
                log_block_completion(name, date_iso, "completed")
                console.print(f"    [green]done[/green]")
            elif response == "skip":
                reason = Prompt.ask("    Why?", default="")
                log_block_completion(name, date_iso, "skipped", reason=reason if reason else None)
                console.print(f"    [yellow]skipped[/yellow]")
            elif response == "partial":
                reason = Prompt.ask("    What happened?", default="")
                log_block_completion(name, date_iso, "partial", reason=reason if reason else None)
                console.print(f"    [blue]partial[/blue]")
            # n/a = don't log anything

        # Ask about wins for this day
        win = Prompt.ask(f"  Any wins on {day_str}? (or enter to skip)", default="")
        if win:
            log_win(win)
            console.print(f"    [green]logged![/green]")

    console.print("\n[green]Catch-up complete![/green]\n")
