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
    poll_cron: str
    init_mode: bool
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create configuration from environment variables."""
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        
        if not telegram_bot_token or not telegram_chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        
        return cls(
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            youtube_client_secret_file=os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "youtube-client-secret.json"),
            youtube_token_file=os.getenv("YOUTUBE_TOKEN_FILE", "youtube-token.json"),
            firebase_credentials_file=os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase-service-account.json"),
            youtube_scopes=["https://www.googleapis.com/auth/youtube.readonly"],
            poll_cron=os.getenv("POLL_CRON", "*/10 * * * *"),    # Every 10 minutes
            init_mode=os.getenv("INIT_MODE", "false").lower() in ("1", "true", "yes", "y")
        )
    
    def validate(self) -> None:
        """Validate configuration values."""
        try:
            croniter(self.poll_cron)
        except ValueError as e:
            raise ValueError(f"Invalid POLL_CRON expression: {e}")