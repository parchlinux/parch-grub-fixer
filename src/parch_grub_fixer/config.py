"""Application-wide constants and the shared Rich console."""

from rich.console import Console

APP_NAME = "parch-grub-fixer"
APP_VERSION = "1.0.0"

MOUNT_ROOT = "/mnt"
WORKDIR_PREFIX = "parch-grub-fixer-"

SUPPORTED_FILESYSTEMS = {
    "ext2",
    "ext3",
    "ext4",
    "btrfs",
    "xfs",
    "f2fs",
}

# On many Parch setups the OS image lives on a dedicated btrfs subvolume.
BTRFS_SUBVOLUMES = ("/", "/@", "@", "ROOT")

console = Console()

LOGO = r"""
 ____                _        ____            _       _____ _
|  _ \ __ _ _ __ ___| |__    / ___|_ __ _   _| |__   |  ___(_)_  _____ _ __
| |_) / _` | '__/ __| '_ \  | |  _| '__| | | | '_ \  | |_  | \ \/ / _ \ '__|
|  __/ (_| | | (__| | | | | | |_| | |  | |_| | |_) | |  _| | |>  <  __/ |
|_|   \__,_|_|  \___|_| |_|  \____|_|   \__,_|_.__/  |_|   |_/_/\_\___|_|
"""