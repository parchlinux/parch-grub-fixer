"""Allow running the tool with ``python -m parch_grub_fixer``."""

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())