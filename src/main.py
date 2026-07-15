from rich.console import Console

from detector import detect_parch
from ui import select_system, select_action
from utils import LOGO
from chroot import Chroot


console = Console()


def main():
    console.print(LOGO)

    console.rule("[bold cyan]1. Scanning Disks[/bold cyan]")

    console.print(
        "[bold cyan]Scanning disks...[/bold cyan]"
    )

    systems = detect_parch()

    if not systems:
        console.print(
            "[red]No Parch installations found[/red]"
        )
        return

    selected = select_system(systems)

    console.print(
        f"\nSelected: [green]{selected['device']}[/green]"
    )

    console.rule("[bold cyan]2. Selecting Action[/bold cyan]")

    action = select_action()

    if action == 4:
        console.print("Exiting...")
        return
    
    chroot = Chroot()

    try:
        console.rule("[bold cyan]3. Preparing Chroot[/bold cyan]")

        chroot.mount(selected['device'])

        if action == 1:
            console.rule("[bold cyan]4. Executing Upgrade[/bold cyan]")

            chroot.run([
                "cat",
                "/etc/os-release",
            ])

            console.print("Upgrade finished. Exiting...")

        elif action == 2:
            console.rule("[bold cyan]4. Repairing grub[/bold cyan]")

            chroot.run([
                "grub-mkconfig",
                "-o",
                "/boot/grub/grub.cfg",
            ])

            console.print("Grub repaired. Exiting...")

        elif action == 3:
            console.rule("[bold cyan]4. Executing upgrade[/bold cyan]")

            chroot.run([
                "pacman",
                "-Syu"
            ])

            console.print("Upgrade finished")
            console.rule("[bold cyan]5. Repairing grub[/bold cyan]")

            chroot.run([
                "grub-mkconfig",
                "-o",
                "/boot/grub/grub.cfg",
            ])

            console.print("Grub repaired. Exiting...")

    finally:
        chroot.cleanup()


if __name__ == "__main__":
    main()