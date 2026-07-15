import os
import shutil
import subprocess
import tempfile

from utils import run


class Chroot:

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="parch-root-")
        self.mounted = False

    def mount(self, device):

        result = run([
            "mount",
            device,
            self.root
        ])

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        self.mounted = True

        for path in (
            "dev",
            "proc",
            "sys",
            "run",
        ):

            os.makedirs(
                os.path.join(self.root, path),
                exist_ok=True,
            )

            result = run([
                "mount",
                "--bind",
                f"/{path}",
                os.path.join(self.root, path),
            ])

            if result.returncode != 0:
                raise RuntimeError(result.stderr)

    def run(self, command):

        if not self.mounted:
            raise RuntimeError("System is not mounted.")

        return subprocess.run(
            [
                "arch-chroot",
                self.root,
                *command,
            ],
            text=True,
        )

    def cleanup(self):

        if not self.mounted:
            return

        for path in (
            "run",
            "sys",
            "proc",
            "dev",
        ):

            run([
                "umount",
                os.path.join(self.root, path),
            ])

        run([
            "umount",
            self.root,
        ])

        shutil.rmtree(
            self.root,
            ignore_errors=True,
        )

        self.mounted = False