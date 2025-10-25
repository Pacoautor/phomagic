#!/usr/bin/env bash
set -o errexit

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Django collectstatic and migrations (no server start here)
python manage.py collectstatic --noinput
python manage.py migrate --noinput
