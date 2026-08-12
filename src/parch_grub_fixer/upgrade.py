"""Full system upgrade of the selected Parch installation."""

from .config import console


def upgrade_system(ctx):
    """Run ``pacman -Syu`` inside the chroot with real-time output."""
    console.print("[bold]Running full system upgrade (pacman -Syu)[/bold]")
    ctx.run("pacman", "-Syu", "--noconfirm", stream_output=True)
    console.print("[green]System upgrade finished.[/green]")