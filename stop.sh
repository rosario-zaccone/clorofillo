#!/bin/bash

process_names=("app.py" "io_app.py")

for name in "${process_names[@]}"; do
    pids=$(pgrep -f "$name")

    if [[ -n "$pids" ]]; then
        echo "🛑 Trovato processo: $name"
        echo "$pids" | while read pid; do
            echo "➡️  Uccido PID $pid..."
            kill -9 "$pid" && echo "✅ PID $pid ucciso"
        done
    else
        echo "✔️  Nessun processo attivo: $name"
    fi
done
