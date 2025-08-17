"""Firebase service for data persistence."""

import os
from typing import Optional, Protocol
import firebase_admin
from firebase_admin import credentials, firestore

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

    def update_last_sync_time(self) -> bool:
        """Update the last subscription sync timestamp."""
        ...

    def update_channel_notify_preference(self, channel_id: str, notify: bool) -> bool:
        """Update notification preference for a channel."""
        ...


class FirebaseService:
    """Firebase service implementation."""

    def __init__(self, credentials_file: str):
        self._credentials_file = credentials_file
        self._db: Optional[firestore.Client] = None
        self._initialize()

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

    def save_video(self, video: Video) -> bool:
        """Save video to Firebase."""
        if not self._db:
            return False

        try:
            video_data = video.to_dict()
            video_data['discovered_at'] = firestore.SERVER_TIMESTAMP

            self._db.collection('videos').document(video.video_id).set(
                video_data, merge=True
            )
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
            return True
        except Exception as e:
            print(f"[firebase] Error updating channel last video: {e}")
            return False

    def get_all_channels(self) -> list[Channel]:
        """Get all subscribed channels from Firebase."""
        if not self._db:
            return []

        try:
            docs = self._db.collection('subscriptions').get()
            channels = []

            for doc in docs:
                data = doc.to_dict()
                channel = Channel(
                    channel_id=doc.id,
                    title=data.get('title', doc.id),
                    thumbnail=data.get('thumbnail'),
                    last_video_id=data.get('last_video_id', ''),
                    notify=data.get('notify', True)  # Default to True for backward compatibility
                )
                channels.append(channel)

            return channels
        except Exception as e:
            print(f"[firebase] Error getting channels: {e}")
            return []

    def get_channel(self, channel_id: str) -> Channel:
        """Get a specific channel by ID."""
        if not self._db:
            raise ValueError("Firebase not available")

        try:
            doc = self._db.collection('subscriptions').document(channel_id).get()
            if not doc.exists:
                raise KeyError(f"Channel {channel_id} not found")

            data = doc.to_dict()
            return Channel(
                channel_id=channel_id,
                title=data.get('title', channel_id),
                thumbnail=data.get('thumbnail'),
                last_video_id=data.get('last_video_id', ''),
                notify=data.get('notify', True)  # Default to True for backward compatibility
            )
        except Exception as e:
            print(f"[firebase] Error getting channel {channel_id}: {e}")
            raise

    def channel_exists(self, channel_id: str) -> bool:
        """Check if a channel exists in Firebase."""
        if not self._db:
            return False

        try:
            doc = self._db.collection('subscriptions').document(channel_id).get()
            return doc.exists
        except Exception as e:
            print(f"[firebase] Error checking channel existence: {e}")
            return False

    def update_last_sync_time(self) -> bool:
        """Update the last subscription sync timestamp."""
        if not self._db:
            return False

        try:
            self._db.collection('bot_state').document('sync_info').set({
                'last_subs_sync': firestore.SERVER_TIMESTAMP
            }, merge=True)
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

    def update_last_sync_time(self) -> bool:
        print("[firebase] Firebase not available, skipping sync time update")
        return False

    def update_channel_notify_preference(self, channel_id: str, notify: bool) -> bool:
        print(f"[firebase] Firebase not available, cannot update notification preference for {channel_id}")
        return False
