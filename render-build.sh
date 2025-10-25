#!/usr/bin/env bash
set -o errexit

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Force DEBUG=true only during build so DB points to BASE_DIR and not /data
export DEBUG=true

# Only collect static at build time (no DB required, but safe if any code touches DB)
python manage.py collectstatic --noinput
