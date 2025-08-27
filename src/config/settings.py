"""Configuration management for YouTube Video Bot."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from croniter import croniter

load_dotenv()


@dataclass(frozen=True)
class BotConfig:
    """Immutable configuration for the bot."""
    
    # Telegram configuration
    telegram_bot_token: str
    telegram_chat_id: str
    
    # File paths
    youtube_client_secret_file: str
    youtube_token_file: str
    firebase_credentials_file: str
    
    # API scopes
    youtube_scopes: list[str]
    
    # Timing configuration
    video_cron: str
    channel_cron: str
    summary_cron: str
    init_mode: bool
    
    # Redis configuration
    upstash_redis_url: str
    app_name: str
    
    # OAuth configuration
    oauth_port_start: int
    oauth_timeout: int
    oauth_auto_browser: bool
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create configuration from environment variables."""
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        upstash_redis_url = os.getenv("UPSTASH_REDIS_URL", "").strip()
        
        if not telegram_bot_token or not telegram_chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        
        if not upstash_redis_url:
            raise ValueError("UPSTASH_REDIS_URL must be set")
        
        return cls(
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            youtube_client_secret_file=os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "youtube-client-secret.json"),
            youtube_token_file=os.getenv("YOUTUBE_TOKEN_FILE", "youtube-token.json"),
            firebase_credentials_file=os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase-service-account.json"),
            youtube_scopes=["https://www.googleapis.com/auth/youtube.readonly"],
            video_cron=os.getenv("VIDEO_CRON", "0 * * * *"),        # Every hour
            channel_cron=os.getenv("CHANNEL_CRON", "0 0 * * *"),   # Daily at midnight
            summary_cron=os.getenv("SUMMARY_CRON", "0 16 * * *"),  # Daily at 00:00 UTC+8 (16:00 UTC)
            init_mode=os.getenv("INIT_MODE", "false").lower() in ("1", "true", "yes", "y"),
            upstash_redis_url=upstash_redis_url,
            app_name=os.getenv("APP_NAME", "youtube-bot"),
            oauth_port_start=int(os.getenv("OAUTH_PORT_START", "8080")),
            oauth_timeout=int(os.getenv("OAUTH_TIMEOUT", "300")),
            oauth_auto_browser=os.getenv("OAUTH_AUTO_BROWSER", "true").lower() in ("1", "true", "yes", "y")
        )
    
    def validate(self) -> None:
        """Validate configuration values."""
        try:
            croniter(self.video_cron)
        except ValueError as e:
            raise ValueError(f"Invalid VIDEO_CRON expression: {e}")
        
        try:
            croniter(self.channel_cron)
        except ValueError as e:
            raise ValueError(f"Invalid CHANNEL_CRON expression: {e}")
        
        try:
            croniter(self.summary_cron)
        except ValueError as e:
            raise ValueError(f"Invalid SUMMARY_CRON expression: {e}")