# YouTube New Video Bot

A Python bot that monitors your YouTube subscriptions and sends notifications to Telegram when new videos are published.

## Features

- Automatically syncs your YouTube subscriptions
- Monitors RSS feeds for new videos
- Sends notifications with video thumbnails to Telegram
- Configurable polling intervals
- Persistent state management

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your configuration:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID

3. Set up YouTube API credentials:
   - Create a project in Google Cloud Console
   - Enable the YouTube Data API v3
   - Download the `client_secret.json` file

4. Run the bot:
   ```bash
   python main.py
   ```

On first run, you'll get an authorization URL to visit in your browser. Copy the code and paste it back into the terminal.

## Running as a Service

Use the provided script to set up systemd service:
```bash
chmod +x setup_systemd.sh
./setup_systemd.sh
```

To update environment variables after starting the service:
1. Edit your `.env` file
2. Restart the service: `sudo systemctl restart youtube-new-video-bot.service`

To view logs:
```bash
# View recent logs
sudo journalctl -u youtube-new-video-bot.service

# Follow logs in real-time
sudo journalctl -u youtube-new-video-bot.service -f
```

## Configuration

- `SUBS_REFRESH_MINUTES`: How often to sync subscriptions (default: 1440 minutes / 24 hours)
- `VIDEO_POLL_SECONDS`: How often to check for new videos (default: 600 seconds / 10 minutes)
- `INIT_MODE`: Set to `true` to skip notifications on first run (default: false)

## Files

- `main.py`: Main bot code
- `state.json`: Persistent state (auto-generated)
- `token.json`: OAuth tokens (auto-generated)
- `client_secret.json`: Google API credentials (you provide this)