#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
<<<<<<< HEAD
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phomagic.settings')
=======
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photopro_app.settings')
>>>>>>> 54dc87cf5bddeb97076c30df6ac7fe69845bb4d6
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
<<<<<<< HEAD
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable?"
=======
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
>>>>>>> 54dc87cf5bddeb97076c30df6ac7fe69845bb4d6
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
