"""GRUB bootloader: reinstall and regenerate its configuration."""

import json
import os

from .chroot import ESP_MOUNTPOINTS, ParchChroot
from .config import console
from .utils import run

GRUB_BOOTLOADER_ID = "GRUB"


def is_efi():
    """True when the running host was booted in UEFI mode."""
    return os.path.isdir("/sys/firmware/efi")


def device_to_disk(device):
    """Return the parent disk of ``device``, e.g. /dev/nvme0n1p1 -> /dev/nvme0n1."""
    result = run(["lsblk", "-no", "PKNAME", device])
    if result.returncode == 0 and result.stdout.strip():
        return "/dev/" + result.stdout.strip()
    return None


def _find_esp(node):
    """Recursively look up the first vfat EFI partition inside ``node``."""
    if node.get("type") == "part" and (node.get("fstype") or "").lower() == "vfat":
        return node.get("path")
    for child in node.get("children", ()):
        found = _find_esp(child)
        if found:
            return found
    return None


def find_efi_partition(disk):
    """Return the EFI System Partition on ``disk`` (or ``None``)."""
    result = run(["lsblk", "-J", "-o", "PATH,FSTYPE,TYPE", disk])
    if result.returncode != 0:
        return None

    nodes = json.loads(result.stdout).get("blockdevices", ())
    for node in nodes:
        esp = _find_esp(node)
        if esp:
            return esp
    return None


def _existing_esp_mountpoint(ctx):
    """Return the in-chroot path of an already-mounted ESP (e.g. '/boot')."""
    for sub in ESP_MOUNTPOINTS:
        if ctx.is_mounted(ctx.root / sub):
            return f"/{sub}"
    return None


def repair_grub(ctx, device):
    """Reinstall GRUB on ``device``'s disk and regenerate grub.cfg."""
    disk = device_to_disk(device)
    if not disk:
        raise RuntimeError(
            f"Could not determine the parent disk of {device}."
        )

    if is_efi():
        esp_mount = _existing_esp_mountpoint(ctx)

        if not esp_mount:
            esp = find_efi_partition(disk)
            if esp:
                console.print(f"[dim]Mounting EFI partition {esp} at /boot[/dim]")
                ctx.mount_esp(esp, "boot")
                esp_mount = "/boot"

        if esp_mount:
            _install_efi_grub(ctx, esp_mount)
            return

        console.print(
            "[yellow]No EFI System Partition found, falling back to BIOS-style GRUB install.[/yellow]"
        )

    _install_legacy_grub(ctx, disk)


def _install_efi_grub(ctx, esp_mount):
    console.print("[bold]Reinstalling GRUB (UEFI)[/bold]")
    ctx.run(
        "grub-install",
        "--target=x86_64-efi",
        f"--efi-directory={esp_mount}",
        f"--bootloader-id={GRUB_BOOTLOADER_ID}",
        stream_output=True,
    )
    _regenerate_grub_config(ctx)


def _install_legacy_grub(ctx, disk):
    console.print(f"[bold]Reinstalling GRUB (BIOS) to {disk}[/bold]")
    ctx.run("grub-install", disk, stream_output=True)
    _regenerate_grub_config(ctx)


def _regenerate_grub_config(ctx):
    console.print("[bold]Regenerating GRUB configuration[/bold]")
    ctx.run("grub-mkconfig", "-o", "/boot/grub/grub.cfg", stream_output=True)