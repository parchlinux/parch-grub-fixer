"""Low-level helpers: subprocess execution and small filesystem utilities."""

import os
import shlex
import subprocess
import sys

from .config import console


class CommandError(RuntimeError):
    """Raised when a shell command exits with a non-zero status."""

    def __init__(self, command, result):
        detail = (result.stderr or "").strip() or f"exit code {result.returncode}"
        super().__init__(
            f"Command failed: {shlex.join(map(str, command))}\n{detail}"
        )
        self.command = command
        self.result = result


def run(command, *, check=False, input=None):
    """Run a command capturing its output.

    Return a ``subprocess.CompletedProcess``. Raise :class:`CommandError`
    instead when ``check`` is true and the command fails.
    """
    result = subprocess.run(
        [str(arg) for arg in command],
        capture_output=True,
        text=True,
        input=input,
    )
    if check and result.returncode != 0:
        raise CommandError(command, result)
    return result


def stream(command, *, input=None):
    """Run a command and forward its output to the console in real time."""
    return subprocess.run(
        [str(arg) for arg in command],
        text=True,
        input=input,
    )


def check_root():
    """Exit cleanly if the tool is not run as root (it needs mount/pacman)."""
    if os.geteuid() != 0:
        console.print(
            "[red]This tool must be run with root privileges[/red]"
        )
        sys.exit(1)


def ensure_dir(path):
    """Create ``path`` (and parents) if it does not exist."""
    os.makedirs(path, exist_ok=True)