#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import os
import sys
from atila.collabo.django.utils import customized_management

@customized_management
def main():
    os.environ.setdefault ('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django") from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
