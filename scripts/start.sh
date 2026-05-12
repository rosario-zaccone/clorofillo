#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Wait for internet connection
echo "Checking internet connection..."
for i in {1..30}; do
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        echo "Internet available!"
        break
    fi
    echo "Attempt $i/30..."
    sleep 5
done

# Start app
echo "Starting application..."
exec /home/rosario/.local/bin/poetry run python -m clorofillo.app
