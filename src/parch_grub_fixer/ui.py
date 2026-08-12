"""Terminal UI helpers: interactive selection prompts."""

from rich.table import Table

from .config import console

ACTIONS = (
    ("Full system upgrade", "Update all packages inside the selected system"),
    ("Fix GRUB bootloader", "Reinstall GRUB and regenerate its configuration"),
    ("Upgrade + Fix GRUB", "Run both operations one after the other"),
)


def select_system(systems):
    """Show detected installations and return the user's choice."""
    table = Table(title="Detected Parch Linux installations")
    table.add_column("#", justify="right")
    table.add_column("Device")
    table.add_column("Filesystem")

    for index, system in enumerate(systems, 1):
        table.add_row(str(index), system["device"], system["fstype"])

    console.print(table)

    while True:
        raw = console.input("\n[bold]Select a system: [/bold]")

        try:
            choice = int(raw)
        except ValueError:
            console.print("[red]Please enter a number.[/red]")
            continue

        if 1 <= choice <= len(systems):
            return systems[choice - 1]

        console.print(
            f"[red]Please choose a number between 1 and {len(systems)}.[/red]"
        )


def select_action():
    """Show available actions and return the user's choice as an int.

    Returns ``len(ACTIONS) + 1`` for exit.
    """
    console.print("\n[bold]Choose an action[/bold]")

    for index, (title, description) in enumerate(ACTIONS, 1):
        console.print(
            f"[cyan]{index}[/cyan] {title} [dim]- {description}[/dim]"
        )

    console.print(f"[cyan]{len(ACTIONS) + 1}[/cyan] Exit")

    while True:
        raw = console.input("\n[bold]Action: [/bold]")

        try:
            choice = int(raw)
        except ValueError:
            console.print("[red]Please enter a number.[/red]")
            continue

        if 1 <= choice <= len(ACTIONS) + 1:
            return choice

        console.print("[red]Invalid choice.[/red]")