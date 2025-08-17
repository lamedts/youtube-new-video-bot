#!/usr/bin/env python3
"""
Test script for the refactored YouTube bot.
"""

import os
import sys
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import BotConfig
from src.models.video import Video
from src.models.channel import Channel
from src.services.firebase_service import NullFirebaseService


def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    
    # Mock environment variables
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VIDEO_POLL_SECONDS': '300',
        'SUBS_REFRESH_MINUTES': '720',
        'YOUTUBE_CLIENT_SECRET_FILE': 'test-client-secret.json',
        'YOUTUBE_TOKEN_FILE': 'test-token.json'
    }):
        config = BotConfig.from_env()
        assert config.telegram_bot_token == 'test_token'
        assert config.telegram_chat_id == 'test_chat_id'
        assert config.video_poll_seconds == 300
        assert config.subs_refresh_minutes == 720
        assert config.youtube_client_secret_file == 'test-client-secret.json'
        assert config.youtube_token_file == 'test-token.json'
        assert config.firebase_credentials_file == 'firebase-service-account.json'
        
        config.validate()  # Should not raise
        print("✅ Configuration test passed")


def test_models():
    """Test data models."""
    print("Testing models...")
    
    # Test Channel model
    channel = Channel(
        channel_id="UC123",
        title="Test Channel"
    )
    
    assert channel.rss_url == "https://www.youtube.com/feeds/videos.xml?channel_id=UC123"
    assert channel.notify == True  # Default value
    
    channel_dict = channel.to_dict()
    assert channel_dict['channel_id'] == "UC123"
    assert channel_dict['title'] == "Test Channel"
    assert channel_dict['notify'] == True
    
    # Test Channel with notify=False
    channel_no_notify = Channel(
        channel_id="UC456",
        title="Silent Channel",
        notify=False
    )
    assert channel_no_notify.notify == False
    
    # Test from_state_dict with notify field
    state_data = {
        "title": "Test Channel",
        "last_video_id": "video123",
        "notify": False
    }
    channel_from_state = Channel.from_state_dict("UC789", state_data)
    assert channel_from_state.notify == False
    
    # Test from_state_dict without notify field (backward compatibility)
    state_data_legacy = {
        "title": "Legacy Channel",
        "last_video_id": "video456"
    }
    channel_legacy = Channel.from_state_dict("UC000", state_data_legacy)
    assert channel_legacy.notify == True  # Should default to True
    
    # Test Video model
    video = Video(
        video_id="video123",
        title="Test Video",
        channel_id="UC123",
        channel_title="Test Channel",
        link="https://youtube.com/watch?v=video123"
    )
    
    video_dict = video.to_dict()
    assert video_dict['video_id'] == "video123"
    assert video_dict['title'] == "Test Video"
    
    print("✅ Models test passed")


def test_firebase_service():
    """Test Firebase service."""
    print("Testing Firebase service...")
    
    # Test null Firebase service
    null_service = NullFirebaseService()
    assert not null_service.is_available
    
    channel = Channel(channel_id="UC123", title="Test")
    video = Video(
        video_id="video123",
        title="Test Video",
        channel_id="UC123",
        channel_title="Test Channel",
        link="https://youtube.com/watch?v=video123"
    )
    
    # These should not crash
    null_service.save_subscription(channel)
    null_service.save_video(video)
    null_service.update_channel_last_video("UC123", "video123")
    
    # Test new Firebase-only methods
    channels = null_service.get_all_channels()
    assert len(channels) == 0
    
    exists = null_service.channel_exists("UC123")
    assert not exists
    
    sync_result = null_service.update_last_sync_time()
    assert not sync_result
    
    # Test new notification preference methods
    notify_result = null_service.update_channel_notify_preference("UC123", False)
    assert not notify_result
    
    print("✅ Firebase service test passed")


def main():
    """Run all tests."""
    print("Running refactored code tests...\n")
    
    try:
        test_config()
        test_models()
        test_firebase_service()
        
        print("\n🎉 All tests passed! Firebase-only implementation is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()