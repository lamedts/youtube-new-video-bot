# YouTube New Video Bot

A Python bot that monitors your YouTube subscriptions and sends notifications to Telegram when new videos are published.

## Features

- Automatically syncs your YouTube subscriptions
- Monitors RSS feeds for new videos
- Sends notifications with video thumbnails to Telegram
- **Firebase integration for data persistence**
- Stores video metadata and subscription information in Firebase Firestore
- **Local notification preferences** - Control notifications per channel since YouTube API doesn't expose bell settings
- Configurable polling intervals
- Cloud-based state management (Firebase-only, no local files)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your configuration (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your values:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `YOUTUBE_CLIENT_SECRET_FILE`: Path to YouTube API credentials file
   - `YOUTUBE_TOKEN_FILE`: Path to YouTube OAuth token file
   - `FIREBASE_CREDENTIALS_FILE`: Path to Firebase service account JSON file

3. Set up YouTube API credentials:
   - Create a project in Google Cloud Console
   - Enable the YouTube Data API v3
   - Download the credentials file and save as `youtube-client-secret.json`

4. Set up Firebase (required):
   - Create a Firebase project in the [Firebase Console](https://console.firebase.google.com)
   - Enable Firestore Database by visiting: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=YOUR_PROJECT_ID
   - Create a service account and download the JSON credentials file
   - Save the credentials file as `firebase-service-account.json` (or update `FIREBASE_CREDENTIALS_FILE` in `.env`)
   
   **Note**: Firebase is required for this bot to function. All data is stored in Firestore.

5. Test Firebase connection (optional):
   ```bash
   python test_firebase.py
   ```

6. Run the bot:
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

- `VIDEO_CRON`: Cron expression for how often to check for new videos via RSS feed (default: "0 * * * *" - every hour) - **FREE**
- `CHANNEL_CRON`: Cron expression for how often to sync channel subscriptions via YouTube Data API (default: "0 0 * * *" - daily at midnight) - **COSTS API QUOTA**
- `INIT_MODE`: Set to `true` to skip notifications on first run (default: false)

## API Usage & Costs

This bot uses two different methods to gather information:

### Video Polling (FREE)
- Uses RSS feeds to check for new videos
- No API quota consumption
- Can run frequently without cost concerns
- Controlled by `VIDEO_CRON`

### Channel Syncing (COSTS QUOTA)
- Uses YouTube Data API v3 to sync subscription list
- Consumes API quota (1 unit per subscription fetched)
- Should run less frequently to conserve quota
- Default: daily at midnight via `CHANNEL_CRON`
- YouTube Data API provides 10,000 units/day for free

**Recommendation**: Keep `CHANNEL_CRON` infrequent (daily or less) to minimize API costs, but `VIDEO_CRON` can run as often as needed since RSS is free.

## Notification Preferences

Since YouTube's API doesn't expose the bell notification settings that users configure on YouTube, this bot implements local notification preferences:

### Features
- **Per-channel control**: Enable/disable notifications for individual channels
- **Backward compatible**: Existing channels default to notifications enabled
- **Firebase persisted**: Preferences survive bot restarts
- **Independent of YouTube**: Works regardless of YouTube's bell icon settings

### Usage Examples
```python
from src.config.settings import BotConfig
from src.services.bot_service import YouTubeBotService

# Initialize bot
config = BotConfig.from_env()
bot_service = YouTubeBotService(config)

# Disable notifications for a specific channel
bot_service.set_channel_notifications("UC123456789", False)

# Enable notifications for a channel
bot_service.set_channel_notifications("UC123456789", True)

# Toggle current notification setting
bot_service.toggle_channel_notifications("UC123456789")
```

### Technical Details
- Notifications are controlled by the `notify` field in the Channel model
- Default value is `True` for all new and existing channels
- When `notify=False`, videos are still tracked but no Telegram notifications are sent
- See `notification_preference_example.py` for a complete demonstration

## Firebase Collections

The bot stores data in two main Firestore collections:

### `videos` collection
Each document represents a discovered video with the following fields:
- `video_id`: YouTube video ID
- `title`: Video title
- `channel_id`: YouTube channel ID
- `channel_title`: Channel name
- `link`: Video URL
- `thumbnail`: Thumbnail image URL
- `discovered_at`: Timestamp when the bot discovered the video
- `published_at`: Video publication timestamp

### `subscriptions` collection
Each document represents a subscribed channel with the following fields:
- `channel_id`: YouTube channel ID
- `title`: Channel name
- `subscribed_at`: When the subscription was first detected
- `last_video_id`: Last processed video ID
- `last_updated`: Timestamp of last update
- `notify`: Local notification preference (true/false)
- `rss_url`: Channel RSS feed URL

## Files

- `main.py`: Main bot code (clean architecture)
- `test_firebase.py`: Firebase connection test script
- `test_refactored.py`: Tests for refactored code
- `notification_preference_example.py`: Example showing notification preference management
- `.env.example`: Example environment configuration
- `youtube-token.json`: YouTube OAuth tokens (auto-generated)
- `youtube-client-secret.json`: YouTube API credentials (you provide this)
- `firebase-service-account.json`: Firebase credentials (you provide this)