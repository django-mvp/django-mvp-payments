#!/usr/bin/env python
"""Management entry point for the demo project."""

import os
import sys


def main() -> None:
    """Run a management command against the demo project's settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
