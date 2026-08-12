"""Command line entry point for parch-grub-fixer."""

import sys

from . import __version__
from .actions import ACTION_EXIT, run_workflow
from .config import LOGO, console
from .system import detect_parch
from .ui import select_action, select_system
from .utils import check_root


def main():
    """Run the interactive parch-grub-fixer flow."""
    check_root()

    console.print(LOGO)
    console.print(f"[dim]parch-grub-fixer {__version__}[/dim]")
    console.rule("[bold cyan]Scanning disks[/bold cyan]")

    try:
        systems = detect_parch()
    except OSError as exc:
        console.print(f"[red]Failed to scan disks:[/red] {exc}")
        return 1

    if not systems:
        console.print("[red]No Parch Linux installations were found.[/red]")
        return 1

    system = select_system(systems)
    console.print(
        f"\n[green]Selected:[/green] {system['device']} [dim]({system['fstype']})[/dim]"
    )

    action = select_action()

    if action == ACTION_EXIT:
        console.print("Exiting...")
        return 0

    try:
        return run_workflow(system, action)
    except Exception as exc:
        console.print(f"\n[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())