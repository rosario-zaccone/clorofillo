#!/bin/bash

PIDS=$(pgrep -f "io_app.py")

if [ -z "$PIDS" ]; then
  echo "io_app.py is not running"
  exit 0
fi

echo "Killing io_app.py (PID: $PIDS)"
kill $PIDS

sleep 2

for pid in $PIDS; do
  if kill -0 "$pid" 2>/dev/null; then
    echo "Force killing PID $pid"
    kill -9 "$pid"
  fi
done

echo "Done."
