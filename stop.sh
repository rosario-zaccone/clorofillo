#!/bin/bash

# Array di nomi dei processi da cercare
process_names=("app.py" "io_app.py")

for name in "${process_names[@]}"; do
    # Trova tutti i PID del processo (escludendo grep stesso)
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
