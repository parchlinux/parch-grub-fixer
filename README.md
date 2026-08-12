# parch-grub-fixer

Detect Parch Linux installations on your disks and either repair the GRUB
bootloader or run a full system upgrade — all from a live USB.

## Features

- Scans local partitions and identifies Parch Linux root filesystems
  (ext4, btrfs with subvolumes, xfs, …) by reading `os-release`.
- Lets you pick the target system from an interactive, colorized menu.
- **Fix GRUB**: reinstalls GRUB (UEFI or BIOS) and regenerates `grub.cfg`.
- **Full system upgrade**: runs `pacman -Syu` inside the system.
- **Upgrade + Fix GRUB**: both operations in one go.
- Mounts uninstalled partitions read-only and temporarily, transparently
  bind-mounts `/dev`, `/proc`, `/sys` and copies `resolv.conf` for the chroot.

## Usage

```sh
sudo parch-grub-fixer
```

Run without installing:

```sh
PYTHONPATH=src sudo python3 -m parch_grub_fixer
```

## Requirements

- Root privileges (mounts, chroot, pacman)
- Linux with `util-linux` (`lsblk`, `findmnt`, `mount`), `grub`, `pacman`
- Python 3.9+ with `rich`

## Install

Build and install the package (as root):

```sh
python -m pip install .
parch-grub-fixer
```

Or package it for your pacman mirror with the included `PKGBUILD`:

```sh
makepkg -f
makepkg -i
```

## How detection works

For every partition the tool checks, if it is already mounted it reads
`/etc/os-release` directly; otherwise it mounts the partition read-only to a
temporary directory. A partition is considered a Parch installation when its
`ID` is `parch`. btrfs root subvolumes (`@`, `/`, `ROOT`) are tried explicitly.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).