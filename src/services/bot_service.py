"""Main bot service orchestrator."""

import time
import threading
from datetime import datetime
from croniter import croniter

from ..config.settings import BotConfig
from ..models.channel import Channel
from ..models.video import Video
from ..services.firebase_service import FirebaseService, FirebaseRepository
from ..services.youtube_service import YouTubeService, RSSService
from ..services.telegram_service import TelegramService


class YouTubeBotService:
    """Main service that orchestrates all bot operations."""

    def __init__(self, config: BotConfig):
        self._config = config

        # Initialize services
        self._youtube_service = YouTubeService(
            config.youtube_client_secret_file,
            config.youtube_token_file,
            config.youtube_scopes
        )
        self._rss_service = RSSService()
        self._telegram_service = TelegramService(
            config.telegram_bot_token,
            config.telegram_chat_id
        )

        # Initialize Firebase (required for this version)
        try:
            self._firebase_service: FirebaseRepository = FirebaseService(config.firebase_credentials_file)
            if not self._firebase_service.is_available:
                raise ValueError("Firebase is required but not available")
        except Exception as e:
            print(f"[bot] Firebase initialization failed: {e}")
            print("[bot] Firebase is required for data persistence. Please check your configuration.")
            raise

    def start(self) -> None:
        """Start the bot."""
        print("YouTube → Telegram notifier starting…")
        print(f"INIT_MODE={self._config.init_mode}, "
              f"VIDEO_CRON={self._config.video_cron}, "
              f"CHANNEL_CRON={self._config.channel_cron}")

        # Send startup notification
        self._send_startup_notification()

        # Start background tasks
        channel_thread = threading.Thread(target=self._run_channel_sync, daemon=True)
        video_thread = threading.Thread(target=self._run_video_poll, daemon=True)
        
        channel_thread.start()
        video_thread.start()

        # Keep main thread alive
        try:
            while True:
                time.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            print("Shutting down…")

    def _send_startup_notification(self) -> None:
        """Send startup notification to Telegram."""
        user_info = self._youtube_service.get_user_channel_info()

        try:
            subscriptions = self._youtube_service.fetch_all_subscriptions()
            sub_count = len(subscriptions)
        except Exception:
            sub_count = "Unknown"

        config_info = (f"⚙️ *Bot Configuration*\n"
                      f"Video Poll Cron: `{self._config.video_cron}`\n"
                      f"Channel Sync Cron: `{self._config.channel_cron}`\n"
                      f"Init Mode: {self._config.init_mode}")

        user_title = user_info.title if user_info else None
        self._telegram_service.send_startup_message(user_title, sub_count, config_info)

    def _run_channel_sync(self) -> None:
        """Background task to sync channel subscriptions.
        
        Uses YouTube Data API v3 - CONSUMES API QUOTA.
        Keep frequency low to minimize costs.
        """
        # Initial sync on startup
        self._sync_subscriptions()
        
        cron = croniter(self._config.channel_cron, datetime.now())
        
        while True:
            next_sync = cron.get_next(datetime)
            print(f"[channel] Next channel sync scheduled at: {next_sync.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate sleep time until next execution
            sleep_seconds = (next_sync - datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            
            self._sync_subscriptions()

    def _run_video_poll(self) -> None:
        """Background task to poll for new videos.
        
        Uses RSS feeds - NO API QUOTA COST.
        Can run frequently without cost concerns.
        """
        cron = croniter(self._config.video_cron, datetime.now())
        
        while True:
            next_poll = cron.get_next(datetime)
            print(f"[video] Next video poll scheduled at: {next_poll.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate sleep time until next execution
            sleep_seconds = (next_poll - datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            
            self._poll_videos_once()

    def _sync_subscriptions(self) -> None:
        """Sync YouTube subscriptions using YouTube Data API v3.
        
        WARNING: This method consumes API quota (1 unit per subscription).
        """
        print("[subs] Syncing subscriptions… (using YouTube Data API - costs quota)")

        try:
            subscription_tuples = self._youtube_service.fetch_all_subscriptions()
            newly_added = []

            for channel_id, title, thumbnail in subscription_tuples:
                # Check if channel already exists in Firebase
                is_new = not self._firebase_service.channel_exists(channel_id)
                
                if is_new:
                    # New channel - create with default notify=True
                    channel = Channel(
                        channel_id=channel_id,
                        title=title or channel_id,
                        thumbnail=thumbnail
                    )
                else:
                    # Existing channel - get current settings and preserve notify preference
                    existing_channel = self._firebase_service.get_channel(channel_id)
                    channel = Channel(
                        channel_id=channel_id,
                        title=title or channel_id,
                        thumbnail=thumbnail,
                        last_video_id=existing_channel.last_video_id,
                        notify=existing_channel.notify,  # Preserve existing notify setting
                        last_upload_at=existing_channel.last_upload_at
                    )

                # Save to Firebase (will merge if exists)
                self._firebase_service.save_subscription(channel)

                if is_new:
                    newly_added.append(channel)

            # Update sync timestamp
            self._firebase_service.update_last_sync_time()

            # Send notifications for new subscriptions
            for channel in newly_added:
                if not self._config.init_mode:
                    self._telegram_service.send_new_subscription_notification(
                        channel.title, channel.channel_id
                    )

            print(f"[subs] Subscription sync completed. Added {len(newly_added)} new channels.")

        except Exception as e:
            print(f"[subs] Error during sync: {e}")

    def _poll_videos_once(self) -> None:
        """Poll for new videos from all subscribed channels using RSS feeds.
        
        Uses RSS feeds - NO API quota cost.
        """
        print("[rss] polling new videos (using RSS - free)")
        new_videos = []
        channels = self._firebase_service.get_all_channels()
        
        # Filter channels to only poll those with notifications enabled
        channels_to_poll = [channel for channel in channels if channel.notify]
        channels_skipped = len(channels) - len(channels_to_poll)
        
        if channels_skipped > 0:
            print(f"[rss] Skipping {channels_skipped} channels with notifications disabled")

        for channel in channels_to_poll:
            latest_video = self._rss_service.get_latest_video(channel)

            if not latest_video or not latest_video.video_id:
                continue

            # Check if this is a new video
            if not channel.last_video_id:
                # First-time bootstrap - save video but only notify if INIT_MODE=false
                self._process_new_video(channel, latest_video)
                if not self._config.init_mode:
                    new_videos.append(latest_video)
            elif latest_video.video_id != channel.last_video_id:
                # New video detected - always include in notifications
                self._process_new_video(channel, latest_video)
                new_videos.append(latest_video)

        # Send summary notification for all new videos
        if new_videos:
            # All videos are from channels with notifications enabled (pre-filtered)
            self._telegram_service.send_video_summary_notification(new_videos)
            print(f"[rss] Sent summary notification for {len(new_videos)} new videos.")
        else:
            print("[rss] Video polling completed. No new videos found.")

    def _process_new_video(self, channel: Channel, video: Video) -> None:
        """Process a new video discovery."""
        from datetime import datetime
        
        # Save to Firebase
        self._firebase_service.save_video(video)
        self._firebase_service.update_channel_last_video(channel.channel_id, video.video_id)
        
        # Update the channel's last upload time based on video's published_at
        if video.published_at:
            try:
                upload_time = datetime.fromisoformat(video.published_at.replace('Z', '+00:00'))
                # Update channel with new last_upload_at
                updated_channel = Channel(
                    channel_id=channel.channel_id,
                    title=channel.title,
                    thumbnail=channel.thumbnail,
                    last_video_id=video.video_id,
                    notify=channel.notify,
                    last_upload_at=upload_time
                )
                self._firebase_service.save_subscription(updated_channel)
            except (ValueError, TypeError):
                # If we can't parse the date, just update without last_upload_at
                pass

    def toggle_channel_notifications(self, channel_id: str) -> bool:
        """Toggle notification preference for a channel."""
        try:
            # Get current channel state
            channel = self._firebase_service.get_channel(channel_id)

            # Toggle the notification preference
            new_notify_state = not channel.notify

            # Update in Firebase
            success = self._firebase_service.update_channel_notify_preference(channel_id, new_notify_state)

            if success:
                state_text = "enabled" if new_notify_state else "disabled"
                print(f"[bot] Notifications {state_text} for channel: {channel.title}")
                return True
            else:
                print(f"[bot] Failed to update notification preference for channel: {channel.title}")
                return False

        except Exception as e:
            print(f"[bot] Error toggling notifications for channel {channel_id}: {e}")
            return False

    def set_channel_notifications(self, channel_id: str, notify: bool) -> bool:
        """Set notification preference for a channel."""
        try:
            success = self._firebase_service.update_channel_notify_preference(channel_id, notify)

            if success:
                channel = self._firebase_service.get_channel(channel_id)
                state_text = "enabled" if notify else "disabled"
                print(f"[bot] Notifications {state_text} for channel: {channel.title}")
                return True
            else:
                print(f"[bot] Failed to update notification preference for channel {channel_id}")
                return False

        except Exception as e:
            print(f"[bot] Error setting notifications for channel {channel_id}: {e}")
            return False

    def _should_notify_for_channel(self, channel_id: str) -> bool:
        """Check if notifications should be sent for a specific channel."""
        try:
            channel = self._firebase_service.get_channel(channel_id)
            return channel.notify
        except Exception:
            # If we can't get the channel, default to not notifying
            return False
