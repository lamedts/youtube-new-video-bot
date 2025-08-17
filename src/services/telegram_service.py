"""Telegram notification service."""

import requests
from typing import Optional

from ..models.video import Video


class TelegramService:
    """Service for sending Telegram notifications."""
    
    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str) -> bool:
        """Send a text message."""
        url = f"{self._base_url}/sendMessage"
        data = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, data=data, timeout=15)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[telegram] Error sending message: {e}")
            return False
    
    def send_photo(self, photo_url: str, caption: str) -> bool:
        """Send a photo with caption."""
        url = f"{self._base_url}/sendPhoto"
        data = {
            "chat_id": self._chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, data=data, timeout=15)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[telegram] Error sending photo: {e}")
            return False
    
    def send_video_notification(self, video: Video) -> bool:
        """Send notification for a new video."""
        text = f"📺 *{video.channel_title}*\nNew video: *{video.title}*\n{video.link}"
        
        if video.thumbnail:
            return self.send_photo(video.thumbnail, text)
        else:
            return self.send_message(text)
    
    def send_startup_message(self, user_info: Optional[str], subscription_count: int, config_info: str) -> bool:
        """Send bot startup notification."""
        if user_info:
            message = f"🚀 YouTube → Telegram bot 'youtube-new-video-bot' has started.\n"
            message += f"User: *{user_info}*\n"
            message += f"Subscriptions: {subscription_count}\n\n"
            message += config_info
        else:
            message = f"🚀 YouTube → Telegram bot 'youtube-new-video-bot' has started.\n"
            message += f"Could not fetch user info.\n"
            message += f"Subscriptions: {subscription_count}\n\n"
            message += config_info
        
        return self.send_message(message)
    
    def send_new_subscription_notification(self, channel_title: str, channel_id: str) -> bool:
        """Send notification for a new subscription."""
        message = f"🆕 *New subscription detected*\n*{channel_title}*\nhttps://www.youtube.com/channel/{channel_id}"
        return self.send_message(message)