"""Channel-related data models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Channel:
    """Represents a YouTube channel subscription."""

    channel_id: str
    title: str
    thumbnail: Optional[str] = None
    last_video_id: str = ""
    notify: bool = True  # Local preference for notifications

    @property
    def link(self) -> str:
        """Get YouTube channel URL."""
        return f"https://www.youtube.com/channel/{self.channel_id}"

    @property
    def rss_url(self) -> str:
        """Get RSS feed URL for this channel."""
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={self.channel_id}"

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "channel_id": self.channel_id,
            "title": self.title,
            "last_video_id": self.last_video_id,
            "notify": self.notify,
            'thumbnail': self.thumbnail,
            "link": self.link,
            "rss_url": self.rss_url
        }

    def to_state_dict(self) -> dict:
        """Convert to dictionary for local state storage."""
        return {
            "title": self.title,
            "thumbnail": self.thumbnail,
            "last_video_id": self.last_video_id,
            "notify": self.notify,
            "link": self.link,
            "rss_url": self.rss_url
        }

    @classmethod
    def from_state_dict(cls, channel_id: str, data: dict) -> "Channel":
        """Create Channel from state dictionary."""
        return cls(
            channel_id=channel_id,
            title=data.get("title", channel_id),
            thumbnail=data.get("thumbnail"),
            last_video_id=data.get("last_video_id", ""),
            notify=data.get("notify", True)  # Default to True for backward compatibility
        )


@dataclass(frozen=True)
class UserChannelInfo:
    """Represents authenticated user's channel information."""

    title: str
    channel_id: str
    subscriber_count: str
    video_count: str
