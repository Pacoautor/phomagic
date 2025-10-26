#!/usr/bin/env bash
set -o errexit
export RENDER=true

python -m pip install --upgrade pip
pip install -r requirements.txt

