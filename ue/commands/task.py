"""Task management commands."""

import click
from ue.utils.display import console
from ue.utils.dates import parse_due_date


@click.group()
def task():
    """Manage time-sensitive tasks."""
    pass


@task.command("add")
@click.argument("title", required=False, default=None)
@click.option("--due", "-d", help="Due date (YYYY-MM-DD or 'wed', 'friday', etc.)")
@click.option("--workstream", "-w", help="Workstream")
@click.option("--priority", "-p", type=click.Choice(["low", "normal", "high"]), default=None)
@click.option("--notes", "-n", help="Additional notes")
def task_add(title, due, workstream, priority, notes):
    """Add a task with a deadline. Run without args for interactive mode."""
    from rich.prompt import Prompt
    from ue.db import add_task
    from ue.config import load_config

    # Interactive mode if no title provided
    if title is None:
        console.print("\n[bold]Add a task[/bold]\n")

        # 1. Get task title
        title = Prompt.ask("  Task name")
        if not title.strip():
            console.print("[red]Task name required[/red]")
            return

        # 2. Select priority
        priorities = ["low", "normal", "high"]
        console.print("\n  [bold]Priority:[/bold]")
        for i, p in enumerate(priorities, 1):
            marker = ""
            if p == "high":
                marker = " [red](urgent)[/red]"
            elif p == "normal":
                marker = " [dim](default)[/dim]"
            console.print(f"    {i}. {p}{marker}")

        priority_choice = Prompt.ask("\n  Select priority", default="2")
        try:
            idx = int(priority_choice) - 1
            if 0 <= idx < len(priorities):
                priority = priorities[idx]
            else:
                priority = "normal"
        except ValueError:
            priority = "normal"

        # 3. Select workstream
        config = load_config()
        workstreams = list(config.get("workstreams", {}).keys())

        if workstreams:
            console.print("\n  [bold]Workstream:[/bold]")
            console.print("    0. [dim](none)[/dim]")
            for i, ws in enumerate(workstreams, 1):
                console.print(f"    {i}. {ws}")

            ws_choice = Prompt.ask("\n  Select workstream", default="0")
            try:
                idx = int(ws_choice)
                if idx == 0:
                    workstream = None
                elif 1 <= idx <= len(workstreams):
                    workstream = workstreams[idx - 1]
                else:
                    workstream = None
            except ValueError:
                workstream = None

        # 4. Due date (optional)
        due = Prompt.ask("\n  Due date (today, tomorrow, wed, 2024-01-15, or skip)", default="")
        console.print()

    # Parse due date
    due_date = parse_due_date(due) if due else None

    # Default priority if not set
    if priority is None:
        priority = "normal"

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


@task.command("edit")
@click.argument("task_id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--due", "-d", help="New due date (or 'none' to clear)")
@click.option("--workstream", "-w", help="New workstream (or 'none' to clear)")
@click.option("--priority", "-p", type=click.Choice(["low", "normal", "high"]), help="New priority")
@click.option("--notes", "-n", help="New notes")
def task_edit(task_id, title, due, workstream, priority, notes):
    """Edit an existing task."""
    from ue.db import get_task, update_task

    task = get_task(task_id)
    if not task:
        console.print(f"[red]Task #{task_id} not found[/red]")
        return

    # Handle 'none' values for clearing fields
    clear_due = due and due.lower() == "none"
    clear_workstream = workstream and workstream.lower() == "none"

    # Parse due date if provided and not clearing
    due_date = None
    if due and not clear_due:
        due_date = parse_due_date(due)

    # Don't pass workstream if clearing
    ws_value = None if clear_workstream else workstream

    updated = update_task(
        task_id,
        title=title,
        due_date=due_date,
        workstream=ws_value,
        priority=priority,
        notes=notes,
        clear_due=clear_due,
        clear_workstream=clear_workstream,
    )

    if updated:
        console.print(f"[green]Task #{task_id} updated[/green]")
        # Show current state
        task = get_task(task_id)
        console.print(f"  Title: {task['title']}")
        console.print(f"  Due: {task['due_date'] or '-'}")
        console.print(f"  Priority: {task['priority']}")
        console.print(f"  Workstream: {task['workstream'] or '-'}")
    else:
        console.print(f"[yellow]No changes made to task #{task_id}[/yellow]")


# Standalone done command for interactive task completion
@click.command("done")
def done():
    """Interactive task completion - pick a task to mark done."""
    from datetime import datetime
    from rich.prompt import Prompt
    from ue.db import get_tasks, complete_task, get_overdue_tasks
    from ue.utils.dates import get_effective_date

    tasks = get_tasks(status="pending")

    if not tasks:
        console.print("[dim]No pending tasks[/dim]")
        return

    overdue = {t["id"] for t in get_overdue_tasks()}
    today = get_effective_date().isoformat()

    console.print("\n[bold]Pending tasks:[/bold]\n")
    for i, t in enumerate(tasks, 1):
        due_str = ""
        if t["due_date"]:
            if t["id"] in overdue:
                due_str = f" [red](overdue: {t['due_date']})[/red]"
            elif t["due_date"] == today:
                due_str = f" [yellow](due today)[/yellow]"
            else:
                due_str = f" [dim](due {t['due_date']})[/dim]"

        console.print(f"  {i}. {t['title']}{due_str}")

    console.print()
    choice = Prompt.ask(
        "Which task is done? (number or 'q' to quit)",
        default="q"
    )

    if choice.lower() == 'q':
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tasks):
            task = tasks[idx]
            complete_task(task["id"])
            console.print(f"\n[green]Completed: {task['title']}[/green]")
        else:
            console.print("[red]Invalid number[/red]")
    except ValueError:
        console.print("[red]Invalid input[/red]")
