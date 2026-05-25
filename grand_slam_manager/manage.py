#!/usr/bin/env python
"""Django command-line utility for Victory's."""
"""Entrada CLI de Django para tareas locales.

Usa `DJANGO_SETTINGS_MODULE=grand_slam_manager.settings` y permite comandos como
`runserver`, `check`, `migrate` o `collectstatic`.
"""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grand_slam_manager.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
