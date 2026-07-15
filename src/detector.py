import os
import tempfile
import subprocess

from utils import run


SUPPORTED_FILESYSTEMS = {
    "ext4",
    "btrfs",
}


def get_partitions():
    result = run([
        "lsblk",
        "-pn",
        "-o",
        "NAME,FSTYPE,TYPE",
    ])

    partitions = []

    for line in result.stdout.splitlines():
        cols = line.split()

        if len(cols) != 3:
            continue

        name, fstype, ptype = cols

        if ptype != "part":
            continue


        partitions.append(
            {
                "device": name,
                "fstype": fstype or "unknown",
            }
        )

    return partitions


def get_mountpoint(device):
    result = run([
        "findmnt",
        "-n",
        "-o",
        "TARGET",
        device,
    ])

    if result.returncode == 0:
        return result.stdout.strip()

    return None


def check_os_release(mountpoint):
    os_release = os.path.join(
        mountpoint,
        "etc",
        "os-release",
    )

    if not os.path.exists(os_release):
        return False

    try:
        with open(os_release) as f:
            content = f.read()

        return "ID=parch" in content

    except PermissionError:
        return False


def is_parch(device):
    # Already mounted (for example /)
    existing_mount = get_mountpoint(device)

    if existing_mount:
        return check_os_release(existing_mount)

    # Temporary mount for unmounted partitions
    mountpoint = tempfile.mkdtemp(
        prefix="parch-check-"
    )

    try:
        result = run(
            [
                "mount",
                "-o",
                "ro",
                device,
                mountpoint,
            ],
        )

        if result.returncode != 0:
            return False

        return check_os_release(mountpoint)

    finally:
        subprocess.run(
            [
                "umount",
                mountpoint,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            os.rmdir(mountpoint)
        except OSError:
            pass


def detect_parch():
    found = []

    for partition in get_partitions():
        device = partition["device"]

        if is_parch(device):
            found.append(partition)

    return found