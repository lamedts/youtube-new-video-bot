"""Main bot service orchestrator."""

import time
import threading

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
              f"VIDEO_POLL_SECONDS={self._config.video_poll_seconds}, "
              f"SUBS_REFRESH_MINUTES={self._config.subs_refresh_minutes}")
        
        # Send startup notification
        self._send_startup_notification()
        
        # Start background tasks
        subscription_thread = threading.Thread(target=self._run_subscription_refresher, daemon=True)
        video_thread = threading.Thread(target=self._run_video_poller, daemon=True)
        
        subscription_thread.start()
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
                      f"Video Poll: {self._config.video_poll_seconds}s\n"
                      f"Subscription Sync: {self._config.subs_refresh_minutes}min\n"
                      f"Init Mode: {self._config.init_mode}")
        
        user_title = user_info.title if user_info else None
        self._telegram_service.send_startup_message(user_title, sub_count, config_info)
    
    def _run_subscription_refresher(self) -> None:
        """Background task to refresh subscriptions."""
        self._sync_subscriptions()
        
        while True:
            time.sleep(self._config.subs_refresh_minutes * 60)
            self._sync_subscriptions()
    
    def _run_video_poller(self) -> None:
        """Background task to poll for new videos."""
        while True:
            self._poll_videos_once()
            time.sleep(self._config.video_poll_seconds)
    
    def _sync_subscriptions(self) -> None:
        """Sync YouTube subscriptions."""
        print("[subs] Syncing subscriptions…")
        
        try:
            subscription_tuples = self._youtube_service.fetch_all_subscriptions()
            newly_added = []
            
            for channel_id, title in subscription_tuples:
                channel = Channel(channel_id=channel_id, title=title or channel_id)
                
                # Check if channel already exists in Firebase
                is_new = not self._firebase_service.channel_exists(channel_id)
                
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
            
            print(f"[subs] Added {len(newly_added)} new channels.")
            
        except Exception as e:
            print(f"[subs] Error during sync: {e}")
    
    def _poll_videos_once(self) -> None:
        """Poll for new videos from all subscribed channels."""
        changes = 0
        channels = self._firebase_service.get_all_channels()
        
        for channel in channels:
            latest_video = self._rss_service.get_latest_video(channel)
            
            if not latest_video or not latest_video.video_id:
                continue
            
            # Check if this is a new video
            if not channel.last_video_id:
                # First-time bootstrap
                self._process_new_video(channel, latest_video, is_bootstrap=True)
            elif latest_video.video_id != channel.last_video_id:
                # New video detected
                self._process_new_video(channel, latest_video, is_bootstrap=False)
                changes += 1
        
        if changes > 0:
            print(f"[rss] Sent {changes} new video notifications.")
        else:
            print("[rss] No new videos found.")
    
    def _process_new_video(self, channel: Channel, video: Video, is_bootstrap: bool) -> None:
        """Process a new video discovery."""
        # Save to Firebase
        self._firebase_service.save_video(video)
        self._firebase_service.update_channel_last_video(channel.channel_id, video.video_id)
        
        # Send notification (unless in init mode for bootstrap or notifications disabled)
        should_notify = not (is_bootstrap and self._config.init_mode) and channel.notify
        if should_notify:
            self._telegram_service.send_video_notification(video)
        elif not channel.notify:
            print(f"[bot] Skipping notification for {channel.title} (notifications disabled)")
    
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