"""Video-related data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from firebase_admin import firestore


@dataclass(frozen=True)
class Video:
    """Represents a YouTube video."""

    video_id: str
    title: str
    channel_ref: Union[firestore.DocumentReference, str]
    link: str
    thumbnail: Optional[str] = None
    published_at: Optional[str] = None
    view_count: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Firebase storage."""
        return {
            'video_id': self.video_id,
            'title': self.title,
            'channel_ref': self.channel_ref,
            'link': self.link,
            'thumbnail': self.thumbnail,
            'published_at': self.published_at,
            'view_count': self.view_count
        }
    
    @classmethod
    def from_rss_entry(cls, entry, channel_ref: Union[firestore.DocumentReference, str]) -> "Video":
        """Create Video from RSS feed entry."""
        vid = getattr(entry, "yt_videoid", None) or entry.get("id")
        title = entry.get("title", "Untitled")
        link = entry.get("link") or f"https://www.youtube.com/watch?v={vid}" if vid else None
        thumbnail = entry.get("media_thumbnail", [{}])[0].get("url") or entry.get("media_content", [{}])[0].get("url")

        published = entry.get("published_parsed")
        published_at = None
        if published:
            try:
                from datetime import timezone
                published_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                pass

        return cls(
            video_id=vid,
            title=title,
            channel_ref=channel_ref,
            link=link,
            thumbnail=thumbnail,
            published_at=published_at,
            view_count=None  # RSS feeds don't provide view count
        )