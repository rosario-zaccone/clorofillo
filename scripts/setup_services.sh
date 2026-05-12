#!/bin/bash

# Get the project root directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER="$(whoami)"

echo "Setting up systemd services for Clorofillo..."
echo "Project directory: $PROJECT_DIR"
echo "User: $USER"
echo ""

# Verify project structure
if [ ! -f "$PROJECT_DIR/scripts/start.sh" ]; then
    echo "Error: scripts/start.sh not found in $PROJECT_DIR"
    echo "Make sure you run this script from the Clorofillo project root directory"
    exit 1
fi

echo "Project directory verified"
echo ""

# Create clorofillo.service
echo "Creating clorofillo.service..."
sudo tee /etc/systemd/system/clorofillo.service > /dev/null <<EOF
[Unit]
Description=Clorofillo App
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/start.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "clorofillo.service created at /etc/systemd/system/clorofillo.service"
else
    echo "Failed to create clorofillo.service"
    exit 1
fi

echo ""

# Create pigpiod.service
echo "Creating pigpiod.service..."
sudo tee /lib/systemd/system/pigpiod.service > /dev/null <<EOF
[Unit]
Description=Daemon required to control GPIO pins via pigpio

[Service]
ExecStart=/usr/bin/pigpiod -l
ExecStop=/bin/systemctl kill pigpiod
Type=forking

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "pigpiod.service created at /lib/systemd/system/pigpiod.service"
else
    echo "Failed to create pigpiod.service"
    exit 1
fi

echo ""

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

if [ $? -eq 0 ]; then
    echo "Systemd daemon reloaded"
else
    echo "Failed to reload systemd daemon"
    exit 1
fi

echo ""

# Enable services for auto-start
echo "Enabling services for auto-start on boot..."
sudo systemctl enable pigpiod.service
sudo systemctl enable clorofillo.service

if [ $? -eq 0 ]; then
    echo "Services enabled for auto-start"
else
    echo "Failed to enable services"
    exit 1
fi

echo ""

# Show service status
echo "Current service status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo systemctl status pigpiod.service --no-pager
echo ""
sudo systemctl status clorofillo.service --no-pager
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ask if user wants to start services now
read -p "Do you want to start the services now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting pigpiod.service..."
    sudo systemctl start pigpiod.service
    
    echo "Starting clorofillo.service..."
    sudo systemctl start clorofillo.service
    
    echo ""
    echo "Services started!"
    echo ""
    echo "Updated service status:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sudo systemctl status pigpiod.service --no-pager
    echo ""
    sudo systemctl status clorofillo.service --no-pager
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Useful debugging commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  View service status:"
echo "    sudo systemctl status clorofillo.service"
echo "    sudo systemctl status pigpiod.service"
echo ""
echo "  View live logs:"
echo "    journalctl -u clorofillo.service -f"
echo "    journalctl -u pigpiod.service -f"
echo ""
echo "  Manage services:"
echo "    sudo systemctl restart clorofillo.service"
echo "    sudo systemctl stop clorofillo.service"
echo "    sudo systemctl start clorofillo.service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
