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
        self._app_name = app_name
        self._redis = None
        
        print(f"[redis] Initializing Redis connection...")
        print(f"[redis] App name: {app_name}")
        
        try:
            # Parse Upstash Redis URL to extract components
            if redis_url.startswith(('redis://', 'rediss://')):
                # Extract token and endpoint from URL: redis://[username]:TOKEN@endpoint:port
                import re
                import os
                
                # Try different URL patterns
                patterns = [
                    r'redis(?:s)?://default:([^@]+)@([^:]+):(\d+)',  # redis://default:token@host:port
                    r'redis(?:s)?://([^@]+)@([^:]+):(\d+)',          # redis://token@host:port
                    r'redis(?:s)?://:([^@]+)@([^:]+):(\d+)',         # redis://:token@host:port
                ]
                
                parsed = False
                for pattern in patterns:
                    match = re.match(pattern, redis_url)
                    if match:
                        groups = match.groups()
                        if len(groups) == 3:
                            token, host, port = groups
                        else:
                            continue
                            
                        endpoint = f"https://{host}"
                        print(f"[redis] Parsed endpoint: {host}")
                        print(f"[redis] Token length: {len(token)} chars")
                        
                        # Try both initialization methods
                        try:
                            self._redis = Redis(url=endpoint, token=token)
                            print(f"[redis] Initialized with url/token parameters")
                            parsed = True
                            break
                        except Exception as e1:
                            print(f"[redis] url/token method failed: {e1}")
                            try:
                                # Try alternative initialization
                                import os
                                os.environ['UPSTASH_REDIS_REST_URL'] = endpoint
                                os.environ['UPSTASH_REDIS_REST_TOKEN'] = token
                                self._redis = Redis.from_env()
                                print(f"[redis] Initialized with environment variables")
                                parsed = True
                                break
                            except Exception as e2:
                                print(f"[redis] Environment method failed: {e2}")
                                continue
                
                if not parsed:
                    print(f"[redis] Could not parse Redis URL with any known pattern")
                    print(f"[redis] URL format: {redis_url[:50]}...")
                    raise ValueError(f"Unsupported Redis URL format")
                    
            else:
                # Assume it's already an HTTPS endpoint
                print(f"[redis] Treating as HTTPS endpoint: {redis_url}")
                import os
                
                # Check if we have a separate token in environment
                token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
                if token:
                    print(f"[redis] Using separate token from UPSTASH_REDIS_REST_TOKEN")
                    self._redis = Redis(url=redis_url, token=token)
                else:
                    print(f"[redis] No separate token found, trying direct URL")
                    self._redis = Redis(url=redis_url)
                
            print(f"[redis] Redis client created successfully")
            
        except Exception as e:
            print(f"[redis] Error during Redis initialization: {e}")
            print(f"[redis] This usually means:")
            print(f"[redis]   1. Invalid UPSTASH_REDIS_URL format")
            print(f"[redis]   2. Incorrect token or endpoint")
            print(f"[redis]   3. Network connectivity issues")
            print(f"[redis] Please check your Upstash console for the correct URL")
            self._redis = None

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
        if self._redis is None:
            print("[redis] Redis client is None - initialization failed")
            return False
            
        try:
            # For upstash-redis, try a simple operation instead of ping
            # Use a test key to verify connectivity
            test_key = f"{self._app_name}:connection_test"
            self._redis.set(test_key, "test", ex=10)  # Set with 10 second expiry
            result = self._redis.get(test_key)
            if result == "test":
                print("[redis] Connection test successful")
                self._redis.delete(test_key)  # Clean up test key
                return True
            else:
                print(f"[redis] Connection test failed - unexpected result: {result}")
                return False
        except Exception as e:
            print(f"[redis] Connection test failed with error: {e}")
            return False