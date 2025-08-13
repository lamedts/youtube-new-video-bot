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

2. Create a `.env` file based on `.env.sample` with your configuration:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - Other optional settings (see `.env.sample`)

3. Set up YouTube API credentials:
   - Create a project in Google Cloud Console
   - Enable the YouTube Data API v3
   - Download the `client_secret.json` file

4. Run the bot:
   ```bash
   python main.py
   ```

On first run, you'll be prompted to authenticate with Google to access your YouTube subscriptions.

## Configuration

- `SUBS_REFRESH_MINUTES`: How often to sync subscriptions (default: 1440 minutes / 24 hours)
- `VIDEO_POLL_SECONDS`: How often to check for new videos (default: 600 seconds / 10 minutes)
- `INIT_MODE`: Set to `true` to skip notifications on first run (default: false)

## Files

- `main.py`: Main bot code
- `state.json`: Persistent state (auto-generated)
- `token.json`: OAuth tokens (auto-generated)
- `client_secret.json`: Google API credentials (you provide this)