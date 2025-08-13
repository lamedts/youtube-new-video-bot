#!/bin/bash

# -----------------------------
# Config - EDIT THESE
# -----------------------------
BOT_NAME="youtube-new-video-bot"
USER_NAME=$(whoami)
BOT_DIR="$HOME/youtube-new-video-bot"
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
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/python $BOT_DIR/$BOT_FILE
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
echo "Check status with: sudo systemctl status $BOT_NAME.service"
