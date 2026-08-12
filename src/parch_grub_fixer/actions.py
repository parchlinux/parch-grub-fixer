"""High-level workflows: prepare a chroot and run the chosen action."""

from pathlib import Path

from .chroot import ParchChroot
from .config import MOUNT_ROOT, WORKDIR_PREFIX, console
from .grub import repair_grub
from .system import get_mountpoint
from .upgrade import upgrade_system
from .utils import ensure_dir, run

# Action numbers shown to the user (see ui.ACTIONS).
ACTION_UPGRADE = 1
ACTION_REPAIR = 2
ACTION_BOTH = 3
ACTION_EXIT = 4


def _mount_system(device):
    """Return (mountpoint, owned) for the given device.

    ``owned`` is True when this function mounted the device itself, in which
    case the caller must unmount it afterwards.
    """
    mountpoint = get_mountpoint(device)
    if mountpoint:
        return mountpoint, False

    mountpoint = str(Path(MOUNT_ROOT) / (WORKDIR_PREFIX + device.replace("/", "_")))
    ensure_dir(mountpoint)

    result = run(["mount", device, mountpoint])
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to mount {device} at {mountpoint}: {result.stderr.strip()}"
        )

    return mountpoint, True


def run_workflow(system, action):
    """Run the requested operation against the selected Parch system."""
    device = system["device"]
    mountpoint, owned = _mount_system(device)

    console.print(
        f"[bold green]Working on {device}[/bold green] [dim](mounted at {mountpoint})[/dim]"
    )
    console.rule("[bold]Inside the system[/bold]")

    ctx = ParchChroot(mountpoint)

    try:
        ctx.prepare()

        if action in (ACTION_UPGRADE, ACTION_BOTH):
            upgrade_system(ctx)

        if action in (ACTION_REPAIR, ACTION_BOTH):
            repair_grub(ctx, device)

        return 0

    finally:
        ctx.cleanup()
        if owned:
            run(["umount", mountpoint])
            try:
                Path(mountpoint).rmdir()
            except OSError:
                pass