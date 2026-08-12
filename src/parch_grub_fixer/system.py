"""Detect Parch Linux installations on the local disks."""

import json
import os
import tempfile

from .config import BTRFS_SUBVOLUMES, SUPPORTED_FILESYSTEMS, console
from .utils import run


def get_partitions():
    """List mountable disk partitions (e.g. ``/dev/sda1``) on this machine."""
    result = run(["lsblk", "-J", "-o", "PATH,FSTYPE,TYPE"])
    if result.returncode != 0:
        raise RuntimeError(f"lsblk failed: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    partitions = []

    for device in data.get("blockdevices", ()):
        if device.get("type") != "part":
            continue

        fstype = (device.get("fstype") or "").lower()
        if fstype not in SUPPORTED_FILESYSTEMS:
            continue

        partitions.append(
            {
                "device": device.get("path"),
                "fstype": fstype or "unknown",
            }
        )

    return partitions


def get_mountpoint(device):
    """Return where ``device`` is currently mounted, or ``None``."""
    result = run(["findmnt", "-n", "-o", "TARGET", device])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def read_os_release_id(mountpoint):
    """Return the ``ID`` field from os-release, or ``None``."""
    for relpath in ("etc/os-release", "usr/lib/os-release"):
        release = os.path.join(mountpoint, relpath)
        if not os.path.isfile(release):
            continue

        try:
            with open(release, "r", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("ID="):
                return line[3:].strip().strip('"').lower()

    return None


def is_parch_root(mountpoint):
    """True when the mounted partition is a Parch Linux root."""
    return read_os_release_id(mountpoint) == "parch"


def _read_subvol_mount(root, device, subvol):
    mountpoint = os.path.join(root, subvol.replace("/", "_"))
    os.makedirs(mountpoint, exist_ok=True)

    options = "ro" if subvol == "/" else f"ro,subvol={subvol}"
    result = run(["mount", "-o", options, device, mountpoint])
    if result.returncode != 0:
        os.rmdir(mountpoint)
        return False

    found = is_parch_root(mountpoint)
    run(["umount", mountpoint])
    os.rmdir(mountpoint)
    return found


def is_parch(device):
    """Check whether ``device`` contains a Parch Linux root filesystem."""
    # The partition is already mounted somewhere (e.g. the host root '/').
    existing = get_mountpoint(device)
    if existing:
        return is_parch_root(existing)

    workdir = tempfile.mkdtemp(prefix="parch-grub-fixer-")

    try:
        result = run(["mount", "-o", "ro", device, workdir])
        if result.returncode == 0:
            try:
                return is_parch_root(workdir)
            finally:
                run(["umount", workdir])
        elif result.stderr and "subvol" in result.stderr.lower():
            for subvol in BTRFS_SUBVOLUMES:
                if _read_subvol_mount(workdir, device, subvol):
                    return True
        return False
    finally:
        try:
            os.rmdir(workdir)
        except OSError:
            pass


def detect_parch():
    """Return a list of partitions that appear to host a Parch installation."""
    found = []

    for partition in get_partitions():
        device = partition["device"]

        with console.status(f"[cyan]Scanning {device}...[/cyan]"):
            if is_parch(device):
                found.append(partition)

    return found