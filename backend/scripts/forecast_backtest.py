#!/usr/bin/env python3
"""
Standalone runner for forecast_backtest.
Enables running directly via:
    python backend/scripts/forecast_backtest.py
or:
    python manage.py forecast_backtest
"""

import os
import sys

# Setup Django environment
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hubSettings.settings")

import django
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    call_command("forecast_backtest", *sys.argv[1:])
