"""Workstream management commands."""

import click
from ue.utils.display import console


@click.group()
def workstream():
    """Manage workstreams for organizing tasks and blocks."""
    pass


@workstream.command("add")
@click.argument("name")
@click.option("--priority", "-p", type=click.Choice(["high", "mid", "low"]), default="mid",
              help="Priority level (high, mid, low)")
@click.option("--color", "-c", default="blue",
              help="Color for display (green, yellow, blue, red, cyan, magenta, dim)")
def workstream_add(name, priority, color):
    """Add a new workstream."""
    from ue.config import load_config, save_config

    config = load_config()
    workstreams = config.get("workstreams", {})

    if name in workstreams:
        console.print(f"[yellow]Workstream '{name}' already exists. Use 'ue workstream set' to modify.[/yellow]")
        return

    workstreams[name] = {"priority": priority, "color": color}
    config["workstreams"] = workstreams
    save_config(config)
    console.print(f"[green]Added workstream '{name}' (priority: {priority})[/green]")


@workstream.command("list")
def workstream_list():
    """List all workstreams."""
    from rich.table import Table
    from ue.config import load_config

    config = load_config()
    workstreams = config.get("workstreams", {})

    if not workstreams:
        console.print("[dim]No workstreams configured. Use 'ue workstream add <name>' to create one.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", width=20)
    table.add_column("Priority", width=10)
    table.add_column("Color", width=10)

    # Sort by priority
    priority_order = {"high": 0, "mid": 1, "low": 2}
    sorted_ws = sorted(workstreams.items(), key=lambda x: priority_order.get(x[1].get("priority", "low"), 2))

    for name, ws in sorted_ws:
        priority = ws.get("priority", "mid")
        color = ws.get("color", "blue")

        # Color the priority
        if priority == "high":
            pri_str = f"[red]{priority}[/red]"
        elif priority == "mid":
            pri_str = f"[yellow]{priority}[/yellow]"
        else:
            pri_str = f"[dim]{priority}[/dim]"

        table.add_row(name, pri_str, color)

    console.print(table)


@workstream.command("remove")
@click.argument("name")
def workstream_remove(name):
    """Remove a workstream."""
    from ue.config import load_config, save_config

    config = load_config()
    workstreams = config.get("workstreams", {})

    if name not in workstreams:
        console.print(f"[red]Workstream '{name}' not found[/red]")
        return

    del workstreams[name]
    config["workstreams"] = workstreams
    save_config(config)
    console.print(f"[yellow]Removed workstream '{name}'[/yellow]")


@workstream.command("set")
@click.argument("name")
@click.option("--priority", "-p", type=click.Choice(["high", "mid", "low"]),
              help="Priority level (high, mid, low)")
@click.option("--color", "-c",
              help="Color for display (green, yellow, blue, red, cyan, magenta, dim)")
def workstream_set(name, priority, color):
    """Update a workstream's settings."""
    from ue.config import load_config, save_config

    config = load_config()
    workstreams = config.get("workstreams", {})

    if name not in workstreams:
        console.print(f"[red]Workstream '{name}' not found. Use 'ue workstream add' to create it.[/red]")
        return

    if priority:
        workstreams[name]["priority"] = priority
    if color:
        workstreams[name]["color"] = color

    config["workstreams"] = workstreams
    save_config(config)
    console.print(f"[green]Updated workstream '{name}'[/green]")
