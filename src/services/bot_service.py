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
from ..services.redis_service import RedisService


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

        # Initialize Redis service
        try:
            self._redis_service = RedisService(config.upstash_redis_url, config.app_name)
            if not self._redis_service.is_available():
                raise ValueError("Redis is required but not available")
        except Exception as e:
            print(f"[bot] Redis initialization failed: {e}")
            print("[bot] Redis is required for video storage. Please check your UPSTASH_REDIS_URL.")
            raise

    def start(self) -> None:
        """Start the bot."""
        print("YouTube → Telegram notifier starting…")
        print(f"INIT_MODE={self._config.init_mode}, "
              f"VIDEO_CRON={self._config.video_cron}, "
              f"CHANNEL_CRON={self._config.channel_cron}, "
              f"SUMMARY_CRON={self._config.summary_cron}")

        # Send startup notification
        self._send_startup_notification()

        # Start background tasks
        channel_thread = threading.Thread(target=self._run_channel_sync, daemon=True)
        video_thread = threading.Thread(target=self._run_video_poll, daemon=True)
        summary_thread = threading.Thread(target=self._run_summary_sender, daemon=True)
        
        channel_thread.start()
        video_thread.start()
        summary_thread.start()

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
                      f"Summary Cron: `{self._config.summary_cron}`\n"
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

    def _run_summary_sender(self) -> None:
        """Background task to send daily video summaries.
        
        Retrieves videos from Redis and sends summary notifications.
        Clears Redis data after successful summary send.
        """
        cron = croniter(self._config.summary_cron, datetime.now())
        
        while True:
            next_summary = cron.get_next(datetime)
            print(f"[summary] Next summary scheduled at: {next_summary.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate sleep time until next execution
            sleep_seconds = (next_summary - datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            
            self._send_daily_summary()

    def _send_daily_summary(self) -> None:
        """Send daily summary of stored videos and clear Redis data."""
        try:
            print("[summary] Generating daily video summary...")
            
            # Get stored videos and filtered count from Redis
            stored_videos = self._redis_service.get_stored_videos()
            filtered_count = self._redis_service.get_filtered_count()
            
            if not stored_videos and filtered_count == 0:
                print("[summary] No videos found in Redis. No summary to send.")
                return
            
            # Send summary notification with filtered count
            self._telegram_service.send_video_summary_notification(stored_videos, filtered_count)
            
            video_count = len(stored_videos)
            summary_info = f"[summary] Sent daily summary with {video_count} videos"
            if filtered_count > 0:
                summary_info += f" ({filtered_count} shorts/non-standard filtered out)"
            print(f"{summary_info}.")
            
            # Clear Redis data after successful send
            cleared_count = self._redis_service.clear_stored_videos()
            print(f"[summary] Cleared {cleared_count} videos and filtered count from Redis.")
            
        except Exception as e:
            print(f"[summary] Error sending daily summary: {e}")

    def _is_full_youtube_video(self, video: Video) -> bool:
        """Check if video has full YouTube watch URL format (not a short)."""
        if not video.link:
            return False
        
        # Check if the URL matches the full YouTube watch format
        return video.link.startswith("https://www.youtube.com/watch?v=")

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
        firestore_filtered_count = 0
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
                video_saved = self._process_new_video(channel, latest_video)
                if video_saved and not self._config.init_mode:
                    new_videos.append(latest_video)
                elif not video_saved:
                    firestore_filtered_count += 1
            elif latest_video.video_id != channel.last_video_id:
                # New video detected - always include in notifications
                video_saved = self._process_new_video(channel, latest_video)
                if video_saved:
                    new_videos.append(latest_video)
                else:
                    firestore_filtered_count += 1

        # Store new videos in Redis (all videos here are already full YouTube videos)
        if new_videos:
            stored_count = 0
            for video in new_videos:
                self._redis_service.store_video(video)
                stored_count += 1
            
            print(f"[rss] Stored {stored_count} new videos in Redis for later summary.")
        
        # Report filtering statistics
        if firestore_filtered_count > 0:
            print(f"[rss] Filtered out {firestore_filtered_count} shorts/non-standard videos (not saved to Firestore).")
            # Store filtered count in Redis for summary reporting
            self._redis_service.increment_filtered_count(firestore_filtered_count)
        
        if not new_videos and firestore_filtered_count == 0:
            print("[rss] Video polling completed. No new videos found.")

    def _process_new_video(self, channel: Channel, video: Video) -> bool:
        """Process a new video discovery. Returns True if video was saved, False if filtered out."""
        from datetime import datetime
        
        # Filter out shorts before saving to Firestore
        if not self._is_full_youtube_video(video):
            return False
        
        # Save to Firebase (only full videos, not shorts)
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
        
        return True

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
