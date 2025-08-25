"""Redis service for storing video data and managing summaries."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import asdict

from upstash_redis import Redis

from ..models.video import Video


class RedisService:
    """Service for managing video data in Redis with app-prefixed keys."""

    def __init__(self, redis_url: str, app_name: str = "youtube-bot"):
        """Initialize Redis service with app name prefix."""
        self._redis = Redis.from_url(redis_url)
        self._app_name = app_name

    def _get_videos_key(self, date_str: Optional[str] = None) -> str:
        """Get Redis key for storing videos with app prefix."""
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self._app_name}:videos:{date_str}"

    def _get_filtered_count_key(self, date_str: Optional[str] = None) -> str:
        """Get Redis key for storing filtered video count with app prefix."""
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self._app_name}:filtered_count:{date_str}"

    def store_video(self, video: Video) -> None:
        """Store a video in Redis for later summary."""
        try:
            key = self._get_videos_key()
            video_data = {
                **asdict(video),
                "stored_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Add video to the list for today
            self._redis.lpush(key, json.dumps(video_data))
            
            # Set expiry to 7 days to prevent indefinite accumulation
            self._redis.expire(key, 604800)  # 7 days in seconds
            
        except Exception as e:
            print(f"[redis] Error storing video {video.video_id}: {e}")

    def get_stored_videos(self, date_str: Optional[str] = None) -> List[Video]:
        """Retrieve all stored videos for a given date."""
        try:
            key = self._get_videos_key(date_str)
            video_data_list = self._redis.lrange(key, 0, -1)
            
            videos = []
            for video_data in video_data_list:
                try:
                    data = json.loads(video_data)
                    # Remove stored_at field before creating Video object
                    data.pop('stored_at', None)
                    video = Video(**data)
                    videos.append(video)
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"[redis] Error parsing video data: {e}")
                    continue
            
            return videos
            
        except Exception as e:
            print(f"[redis] Error retrieving videos: {e}")
            return []

    def increment_filtered_count(self, count: int = 1, date_str: Optional[str] = None) -> None:
        """Increment the filtered video count for a given date."""
        try:
            key = self._get_filtered_count_key(date_str)
            self._redis.incrby(key, count)
            
            # Set expiry to 7 days to prevent indefinite accumulation
            self._redis.expire(key, 604800)  # 7 days in seconds
            
        except Exception as e:
            print(f"[redis] Error incrementing filtered count: {e}")

    def get_filtered_count(self, date_str: Optional[str] = None) -> int:
        """Get count of filtered videos for a given date."""
        try:
            key = self._get_filtered_count_key(date_str)
            return int(self._redis.get(key) or 0)
            
        except Exception as e:
            print(f"[redis] Error getting filtered count: {e}")
            return 0

    def clear_stored_videos(self, date_str: Optional[str] = None) -> int:
        """Clear all stored videos for a given date and return count of cleared items."""
        try:
            videos_key = self._get_videos_key(date_str)
            filtered_key = self._get_filtered_count_key(date_str)
            
            count = self._redis.llen(videos_key) or 0
            self._redis.delete(videos_key)
            self._redis.delete(filtered_key)  # Also clear filtered count
            return count
            
        except Exception as e:
            print(f"[redis] Error clearing videos: {e}")
            return 0

    def get_video_count(self, date_str: Optional[str] = None) -> int:
        """Get count of stored videos for a given date."""
        try:
            key = self._get_videos_key(date_str)
            return self._redis.llen(key) or 0
            
        except Exception as e:
            print(f"[redis] Error getting video count: {e}")
            return 0

    def is_available(self) -> bool:
        """Check if Redis connection is available."""
        try:
            self._redis.ping()
            return True
        except Exception:
            return False