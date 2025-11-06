#!/bin/bash
set -e

echo "=== RAILWAY STARTUP SCRIPT ==="
echo "Checking environment variables..."

# Mostrar todas las variables que contienen "OPENAI" o "API"
env | grep -i "openai\|api" || echo "No OPENAI/API variables found"

# Si OPENAI_API_KEY no está definida, intentar obtenerla
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY is not set!"
    echo "Available variables:"
    env | sort
    exit 1
else
    echo "OPENAI_API_KEY is set (length: ${#OPENAI_API_KEY})"
    export OPENAI_API_KEY="$OPENAI_API_KEY"
fi

# Iniciar Django
echo "Starting gunicorn..."
exec gunicorn photopro_app.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 60
