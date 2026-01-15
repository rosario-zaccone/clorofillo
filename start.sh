#!/bin/bash

set -a
[ -f .env ] && . .env
set +a

if [ -z "$WIFI_SSID" ] || [ -z "$WIFI_PASSWD" ]; then
    echo "SSID or PASSWD not set in .env"
    exit 1
fi

connect_wifi() {
    nmcli connection delete "$SSID" 2>/dev/null
    nmcli dev wifi connect "$SSID" password "$PASSWD" >/dev/null 2>&1
}

while true; do
    connect_wifi
    IP=$(hostname -I | awk '{print $1}')
    if [ -n "$IP" ]; then
        echo "Connected to Wi-Fi! IP: $IP"
        break
    else
        echo "Connection failed, retrying in 10 seconds..."
        sleep 10
    fi
done

poetry run python src/clorofillo/app.py &
wait
