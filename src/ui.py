from rich.console import Console
from rich.table import Table


console = Console()


def select_system(systems):
    table = Table()

    table.add_column("#")
    table.add_column("Device")
    table.add_column("Filesystem")

    for i, system in enumerate(systems, 1):
        table.add_row(
            str(i),
            system["device"],
            system["fstype"],
        )

    console.print(table)

    while True:
        try:
            choice = int(
                console.input("\nSelect installation: ")
            )

            if 1 <= choice <= len(systems):
                return systems[choice - 1]

        except ValueError:
            pass

        console.print(
            "[red]Invalid choice[/red]"
        )


def select_action():
    console.print(
        """
[1] Full system upgrade
[2] Fix GRUB
[3] Upgrade + Fix GRUB
[4] Exit
"""
    )

    while True:
        choice = console.input("Choose action: ")

        if choice in range(1, 5):
            return int(choice)

        console.print(
            "[red]Invalid choice[/red]"
        )