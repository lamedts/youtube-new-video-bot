"""Telegram notification service."""

import requests
from typing import Optional, List

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

    def send_video_summary_notification(self, new_videos: List[Video]) -> bool:
        """Send a summary notification for new videos."""
        if not new_videos:
            return True

        video_count = len(new_videos)
        message = f"📺 *{video_count} new video{'s' if video_count > 1 else ''} found!*"

        return self.send_message(message)
