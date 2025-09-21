"""Firebase service for data persistence."""

import os
from typing import Optional, Protocol
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import pytz

from ..models.video import Video
from ..models.channel import Channel


class FirebaseRepository(Protocol):
    """Protocol for Firebase repository operations."""

    def save_video(self, video: Video) -> bool:
        """Save video to Firebase."""
        ...

    def save_subscription(self, channel: Channel) -> bool:
        """Save subscription to Firebase."""
        ...

    def update_channel_last_video(self, channel_id: str, video_id: str) -> bool:
        """Update last processed video for a channel."""
        ...

    def get_all_channels(self) -> list[Channel]:
        """Get all subscribed channels from Firebase."""
        ...

    def get_channel(self, channel_id: str) -> Channel:
        """Get a specific channel by ID."""
        ...

    def channel_exists(self, channel_id: str) -> bool:
        """Check if a channel exists in Firebase."""
        ...

    def channels_exist_batch(self, channel_ids: list[str]) -> dict[str, bool]:
        """Check if multiple channels exist in Firebase."""
        ...

    def update_last_sync_time(self) -> bool:
        """Update the last subscription sync timestamp."""
        ...

    def update_channel_notify_preference(self, channel_id: str, notify: bool) -> bool:
        """Update notification preference for a channel."""
        ...

    def get_daily_stats(self) -> dict[str, int]:
        """Get current daily Firestore operation stats."""
        ...


class FirebaseService:
    """Firebase service implementation."""

    def __init__(self, credentials_file: str):
        self._credentials_file = credentials_file
        self._db: Optional[firestore.Client] = None
        self._channels_cache: Optional[list[Channel]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 1380  # Cache for 23 hours
        
        # Firestore operation counters
        self._read_count = 0
        self._write_count = 0
        self._last_reset_date: Optional[str] = None
        self._utc8_tz = pytz.timezone('Asia/Shanghai')  # UTC+8
        
        self._initialize()
        self._check_and_reset_counters()

    def _initialize(self) -> None:
        """Initialize Firebase connection."""
        try:
            if not firebase_admin._apps:
                if os.path.exists(self._credentials_file):
                    cred = credentials.Certificate(self._credentials_file)
                    firebase_admin.initialize_app(cred)
                    print("[firebase] Initialized with service account")
                else:
                    firebase_admin.initialize_app()
                    print("[firebase] Initialized with default credentials")

            self._db = firestore.client()
        except Exception as e:
            print(f"[firebase] Error initializing Firebase: {e}")
            self._db = None

    @property
    def is_available(self) -> bool:
        """Check if Firebase is available."""
        return self._db is not None

    def _get_current_utc8_date(self) -> str:
        """Get current date in UTC+8 timezone as YYYY-MM-DD string."""
        utc8_now = datetime.now(self._utc8_tz)
        return utc8_now.strftime('%Y-%m-%d')

    def _check_and_reset_counters(self) -> None:
        """Check if counters need to be reset for a new day (UTC+8)."""
        current_date = self._get_current_utc8_date()
        
        if self._last_reset_date != current_date:
            if self._last_reset_date is not None:
                print(f"[firebase] Daily reset - Previous day stats: {self._read_count} reads, {self._write_count} writes")
            
            self._read_count = 0
            self._write_count = 0
            self._last_reset_date = current_date
            print(f"[firebase] Counters reset for {current_date} (UTC+8)")

    def _increment_read_counter(self, count: int = 1) -> None:
        """Increment the read counter and check for daily reset."""
        self._check_and_reset_counters()
        self._read_count += count

    def _increment_write_counter(self, count: int = 1) -> None:
        """Increment the write counter and check for daily reset."""
        self._check_and_reset_counters()
        self._write_count += count

    def get_daily_stats(self) -> dict[str, int]:
        """Get current daily Firestore operation stats."""
        self._check_and_reset_counters()
        return {
            'reads': self._read_count,
            'writes': self._write_count,
            'date': self._last_reset_date
        }

    def _log_current_stats(self) -> None:
        """Log current Firestore operation stats."""
        stats = self.get_daily_stats()
        print(f"[firebase] Daily stats ({stats['date']}): {stats['reads']} reads, {stats['writes']} writes")

    def save_video(self, video: Video) -> bool:
        """Save video to Firebase."""
        if not self._db:
            return False

        try:
            video_data = video.to_dict()
            video_data['discovered_at'] = firestore.SERVER_TIMESTAMP

            # Convert channel_ref to DocumentReference if it's a string (channel_id)
            if isinstance(video.channel_ref, str):
                video_data['channel_ref'] = self._db.collection('subscriptions').document(video.channel_ref)

            self._db.collection('videos').document(video.video_id).set(
                video_data, merge=True
            )
            self._increment_write_counter()
            self._log_current_stats()
            # print(f"[firebase] Saved video: {video.title}")
            return True
        except Exception as e:
            print(f"[firebase] Error saving video: {e}")
            return False

    def save_subscription(self, channel: Channel) -> bool:
        """Save subscription to Firebase."""
        if not self._db:
            return False

        try:
            channel_data = channel.to_dict()
            channel_data['subscribed_at'] = firestore.SERVER_TIMESTAMP

            self._db.collection('subscriptions').document(channel.channel_id).set(
                channel_data, merge=True
            )
            self._increment_write_counter()
            self._log_current_stats()
            # Invalidate cache since channels list changed
            self._invalidate_cache()
            # print(f"[firebase] Saved subscription: {channel.title}")
            return True
        except Exception as e:
            print(f"[firebase] Error saving subscription: {e}")
            return False

    def update_channel_last_video(self, channel_id: str, video_id: str) -> bool:
        """Update last processed video for a channel."""
        if not self._db:
            return False

        try:
            self._db.collection('subscriptions').document(channel_id).update({
                'last_video_id': video_id,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            self._increment_write_counter()
            self._log_current_stats()
            return True
        except Exception as e:
            print(f"[firebase] Error updating channel last video: {e}")
            return False

    def _is_cache_valid(self) -> bool:
        """Check if the channels cache is still valid."""
        if not self._cache_timestamp or not self._channels_cache:
            return False

        cache_age = datetime.now() - self._cache_timestamp
        return cache_age.total_seconds() < (self._cache_ttl_minutes * 60)

    def _invalidate_cache(self) -> None:
        """Invalidate the channels cache."""
        self._channels_cache = None
        self._cache_timestamp = None

    def get_all_channels(self) -> list[Channel]:
        """Get all subscribed channels from Firebase with caching."""
        if not self._db:
            return []

        # Return cached data if valid
        if self._is_cache_valid():
            return self._channels_cache.copy()

        try:
            docs = self._db.collection('subscriptions').get()
            self._increment_read_counter(len(docs))
            self._log_current_stats()
            channels = []

            for doc in docs:
                data = doc.to_dict()

                # Parse last_upload_at if it exists
                last_upload_at = None
                last_upload_str = data.get('last_upload_at')
                if last_upload_str:
                    try:
                        last_upload_at = datetime.fromisoformat(last_upload_str)
                    except (ValueError, TypeError):
                        last_upload_at = None

                channel = Channel(
                    channel_id=doc.id,
                    title=data.get('title', doc.id),
                    thumbnail=data.get('thumbnail'),
                    last_video_id=data.get('last_video_id', ''),
                    notify=data.get('notify', True),  # Default to True for backward compatibility
                    last_upload_at=last_upload_at
                )
                channels.append(channel)

            # Cache the results
            self._channels_cache = channels
            self._cache_timestamp = datetime.now()
            print(f"[firebase] Cached {len(channels)} channels for {self._cache_ttl_minutes} minutes")

            return channels
        except Exception as e:
            print(f"[firebase] Error getting channels: {e}")
            return []

    def get_channel(self, channel_id: str) -> Channel:
        """Get a specific channel by ID."""
        if not self._db:
            raise ValueError("Firebase not available")

        # First try to get from cache if valid
        if self._is_cache_valid() and self._channels_cache:
            for channel in self._channels_cache:
                if channel.channel_id == channel_id:
                    return channel
            # If not in cache, channel doesn't exist
            raise KeyError(f"Channel {channel_id} not found")

        try:
            doc = self._db.collection('subscriptions').document(channel_id).get()
            self._increment_read_counter()
            self._log_current_stats()
            if not doc.exists:
                raise KeyError(f"Channel {channel_id} not found")

            data = doc.to_dict()

            # Parse last_upload_at if it exists
            last_upload_at = None
            last_upload_str = data.get('last_upload_at')
            if last_upload_str:
                try:
                    last_upload_at = datetime.fromisoformat(last_upload_str)
                except (ValueError, TypeError):
                    last_upload_at = None

            return Channel(
                channel_id=channel_id,
                title=data.get('title', channel_id),
                thumbnail=data.get('thumbnail'),
                last_video_id=data.get('last_video_id', ''),
                notify=data.get('notify', True),  # Default to True for backward compatibility
                last_upload_at=last_upload_at
            )
        except Exception as e:
            print(f"[firebase] Error getting channel {channel_id}: {e}")
            raise

    def channel_exists(self, channel_id: str) -> bool:
        """Check if a channel exists in Firebase."""
        if not self._db:
            return False

        # First check cache if valid
        if self._is_cache_valid() and self._channels_cache:
            return any(channel.channel_id == channel_id for channel in self._channels_cache)

        try:
            doc = self._db.collection('subscriptions').document(channel_id).get()
            self._increment_read_counter()
            self._log_current_stats()
            return doc.exists
        except Exception as e:
            print(f"[firebase] Error checking channel existence: {e}")
            return False

    def channels_exist_batch(self, channel_ids: list[str]) -> dict[str, bool]:
        """Check if multiple channels exist in Firebase using cached data when possible."""
        if not self._db:
            return {channel_id: False for channel_id in channel_ids}

        # If cache is valid, use it for all checks
        if self._is_cache_valid() and self._channels_cache:
            cached_ids = {channel.channel_id for channel in self._channels_cache}
            return {channel_id: channel_id in cached_ids for channel_id in channel_ids}

        # Otherwise fall back to individual checks (could be optimized further with batch gets)
        results = {}
        for channel_id in channel_ids:
            results[channel_id] = self.channel_exists(channel_id)
        return results

    def update_last_sync_time(self) -> bool:
        """Update the last subscription sync timestamp."""
        if not self._db:
            return False

        try:
            self._db.collection('bot_state').document('sync_info').set({
                'last_subs_sync': firestore.SERVER_TIMESTAMP
            }, merge=True)
            self._increment_write_counter()
            self._log_current_stats()
            return True
        except Exception as e:
            print(f"[firebase] Error updating sync time: {e}")
            return False

    def update_channel_notify_preference(self, channel_id: str, notify: bool) -> bool:
        """Update notification preference for a channel."""
        if not self._db:
            return False

        try:
            self._db.collection('subscriptions').document(channel_id).update({
                'notify': notify,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            self._increment_write_counter()
            self._log_current_stats()
            # Invalidate cache since channel data changed
            self._invalidate_cache()
            print(f"[firebase] Updated notification preference for {channel_id}: {notify}")
            return True
        except Exception as e:
            print(f"[firebase] Error updating notification preference: {e}")
            return False


class NullFirebaseService:
    """Null object pattern for when Firebase is not available."""

    @property
    def is_available(self) -> bool:
        return False

    def save_video(self, video: Video) -> bool:
        print("[firebase] Firebase not available, skipping video save")
        return False

    def save_subscription(self, channel: Channel) -> bool:
        print("[firebase] Firebase not available, skipping subscription save")
        return False

    def update_channel_last_video(self, channel_id: str, video_id: str) -> bool:
        print("[firebase] Firebase not available, skipping channel update")
        return False

    def get_all_channels(self) -> list[Channel]:
        print("[firebase] Firebase not available, returning empty channel list")
        return []

    def get_channel(self, channel_id: str) -> Channel:
        print(f"[firebase] Firebase not available, cannot get channel {channel_id}")
        raise ValueError("Firebase not available")

    def channel_exists(self, channel_id: str) -> bool:
        print("[firebase] Firebase not available, assuming channel doesn't exist")
        return False

    def channels_exist_batch(self, channel_ids: list[str]) -> dict[str, bool]:
        print("[firebase] Firebase not available, assuming no channels exist")
        return {channel_id: False for channel_id in channel_ids}

    def update_last_sync_time(self) -> bool:
        print("[firebase] Firebase not available, skipping sync time update")
        return False

    def update_channel_notify_preference(self, channel_id: str, notify: bool) -> bool:
        print(f"[firebase] Firebase not available, cannot update notification preference for {channel_id}")
        return False

    def get_daily_stats(self) -> dict[str, int]:
        print("[firebase] Firebase not available, returning empty stats")
        return {'reads': 0, 'writes': 0, 'date': 'N/A'}
