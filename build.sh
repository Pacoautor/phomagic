#!/usr/bin/env bash
# build.sh — Inicializa carpetas de medios en Render

echo "=== Preparando entorno para Phomagic ==="
mkdir -p /opt/render/project/src/media/lineas
python manage.py collectstatic --noinput
echo "=== Carpetas de medios listas ==="
