"""Display utilities - console, logo, formatting."""

from rich.console import Console

console = Console()

LOGO = "[green][■■■□□] utility-explorer[/green]"


def print_logo():
    """Print the utility-explorer logo."""
    console.print(LOGO)
