"""Mount helpers and ``chroot`` execution inside a Parch root."""

from pathlib import Path

from .config import console
from .utils import CommandError, run, stream

# Sources that must be bind-mounted into the chroot before running pacman/grub.
BIND_SOURCES = ("/dev", "/dev/pts", "/proc", "/sys")

# Directories where a UEFI System Partition is usually mounted.
ESP_MOUNTPOINTS = ("boot", "efi")


class ParchChroot:
    """Operate on a mounted Parch root via ``chroot``.

    Call :meth:`prepare` to bind-mount hosts filesystems, perform actions with
    :meth:`run`, and always finish with :meth:`cleanup`.
    """

    def __init__(self, root):
        self.root = Path(root)
        self._mounted = []

    # Filesystem preparation

    def prepare(self):
        """Bind-mount /dev, /proc, /sys and copy resolv.conf into the chroot."""
        for source in BIND_SOURCES:
            target = self.root / source.lstrip("/")
            if self.is_mounted(target):
                continue

            target.mkdir(parents=True, exist_ok=True)
            result = run(["mount", "--bind", source, str(target)])
            if result.returncode != 0:
                raise CommandError(
                    ["mount", "--bind", source, str(target)], result
                )
            self._mounted.append(target)

        self._copy_resolv_conf()

    def _copy_resolv_conf(self):
        """Give the chroot working DNS so pacman mirrors can be reached."""
        host_resolv = Path("/etc/resolv.conf")
        if not host_resolv.is_file():
            return

        target = self.root / "etc/resolv.conf"
        try:
            target.write_text(host_resolv.read_text())
        except OSError:
            console.print(
                "[yellow]Warning: could not copy /etc/resolv.conf into the chroot.[/yellow]"
            )

    def mount_esp(self, esp_device, subdir="boot"):
        """Mount the EFI System Partition inside the chroot."""
        target = self.root / subdir
        if self.is_mounted(target):
            return

        target.mkdir(parents=True, exist_ok=True)
        result = run(["mount", esp_device, str(target)])
        if result.returncode != 0:
            raise CommandError(["mount", esp_device, str(target)], result)
        self._mounted.append(target)

    def is_mounted(self, path):
        """True when ``path`` is already a mountpoint."""
        result = run(["findmnt", str(path)])
        return result.returncode == 0

    def cleanup(self):
        """Unmount everything this instance mounted"""
        for target in reversed(self._mounted):
            run(["umount", "-l", str(target)])
        self._mounted.clear()

    # Command execution

    def run(self, *command, stream_output=False, check=True, input=None):
        """Run a command inside the chroot."""
        full = ["chroot", str(self.root)] + [str(arg) for arg in command]
        runner = stream if stream_output else run
        result = runner(full, input=input)

        if check and result.returncode != 0:
            detail = (result.stderr or "").strip() or f"exit code {result.returncode}"
            raise RuntimeError(
                f"Command failed inside chroot: {' '.join(full)}\n{detail}"
            )
        return result