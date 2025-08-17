#!/bin/bash

# -----------------------------
# Config - EDIT THESE
# -----------------------------
BOT_NAME="youtube-new-video-bot"
USER_NAME=$(whoami)
BOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$BOT_DIR/venv"
BOT_FILE="main.py"
ENV_FILE="$BOT_DIR/.env"
SERVICE_FILE="/etc/systemd/system/${BOT_NAME}.service"

# -----------------------------
# Create systemd service file
# -----------------------------
echo "Creating systemd service file at $SERVICE_FILE"

sudo bash -c "cat > $SERVICE_FILE <<EOL
[Unit]
Description=YouTube → Telegram Notification Bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BOT_DIR
Environment=\"PATH=$VENV_DIR/bin\"
Environment=\"PYTHONUNBUFFERED=1\"
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/python -u $BOT_DIR/$BOT_FILE
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL"

# -----------------------------
# Reload systemd and enable service
# -----------------------------
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling service to start on boot..."
sudo systemctl enable $BOT_NAME.service

echo "Starting the service..."
sudo systemctl start $BOT_NAME.service

echo "Done!"
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status $BOT_NAME.service"
echo "  View logs:    sudo journalctl -u $BOT_NAME.service -f"
echo "  Stop service: sudo systemctl stop $BOT_NAME.service"
echo "  Start service: sudo systemctl start $BOT_NAME.service"
echo "  Restart service: sudo systemctl restart $BOT_NAME.service"
