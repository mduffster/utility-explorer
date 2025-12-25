"""Manual activity logging commands."""

import click
from ue.utils.display import console


@click.group()
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


@click.group()
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
