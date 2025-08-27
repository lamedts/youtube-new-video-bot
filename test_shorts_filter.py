#!/usr/bin/env python3
"""
Test script to verify shorts filtering works correctly.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.video import Video
from src.models.channel import Channel
from src.services.bot_service import YouTubeBotService


def test_is_full_youtube_video():
    """Test the _is_full_youtube_video method."""
    print("Testing _is_full_youtube_video method...")
    
    # Create a mock bot service with minimal config
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VIDEO_CRON': '*/5 * * * *',
        'CHANNEL_CRON': '0 */12 * * *',
        'YOUTUBE_CLIENT_SECRET_FILE': 'test-client-secret.json',
        'YOUTUBE_TOKEN_FILE': 'test-token.json'
    }):
        # Mock the services to avoid actual initialization
        with patch('src.services.bot_service.YouTubeService'), \
             patch('src.services.bot_service.RSSService'), \
             patch('src.services.bot_service.TelegramService'), \
             patch('src.services.bot_service.FirebaseService'), \
             patch('src.services.bot_service.RedisService'):
            
            from src.config.settings import BotConfig
            config = BotConfig.from_env()
            bot_service = YouTubeBotService(config)
            
            # Test full YouTube video URLs (should return True)
            full_video = Video(
                video_id="dQw4w9WgXcQ",
                title="Never Gonna Give You Up",
                link="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            assert bot_service._is_full_youtube_video(full_video) == True
            print("✅ Full YouTube video URL detected correctly")
            
            # Test YouTube Shorts URLs (should return False)
            short_video = Video(
                video_id="shortID123",
                title="Test Short",
                link="https://www.youtube.com/shorts/shortID123",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            assert bot_service._is_full_youtube_video(short_video) == False
            print("✅ YouTube Shorts URL filtered correctly")
            
            # Test mobile YouTube URLs (should return False)
            mobile_video = Video(
                video_id="mobileID123",
                title="Test Mobile",
                link="https://m.youtube.com/watch?v=mobileID123",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            assert bot_service._is_full_youtube_video(mobile_video) == False
            print("✅ Mobile YouTube URL filtered correctly")
            
            # Test youtu.be URLs (should return False)
            short_link_video = Video(
                video_id="shortLinkID",
                title="Test Short Link",
                link="https://youtu.be/shortLinkID",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            assert bot_service._is_full_youtube_video(short_link_video) == False
            print("✅ youtu.be short link filtered correctly")
            
            # Test video with no link (should return False)
            no_link_video = Video(
                video_id="noLinkID",
                title="Test No Link",
                link=None,
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            assert bot_service._is_full_youtube_video(no_link_video) == False
            print("✅ Video with no link filtered correctly")
            
            print("✅ All filtering tests passed!")


def test_process_new_video_filtering():
    """Test that _process_new_video filters shorts correctly."""
    print("\nTesting _process_new_video filtering...")
    
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VIDEO_CRON': '*/5 * * * *',
        'CHANNEL_CRON': '0 */12 * * *',
        'YOUTUBE_CLIENT_SECRET_FILE': 'test-client-secret.json',
        'YOUTUBE_TOKEN_FILE': 'test-token.json'
    }):
        # Mock the services
        with patch('src.services.bot_service.YouTubeService'), \
             patch('src.services.bot_service.RSSService'), \
             patch('src.services.bot_service.TelegramService'), \
             patch('src.services.bot_service.FirebaseService') as mock_firebase, \
             patch('src.services.bot_service.RedisService'):
            
            from src.config.settings import BotConfig
            config = BotConfig.from_env()
            bot_service = YouTubeBotService(config)
            
            # Mock Firebase service methods
            mock_firebase_instance = Mock()
            bot_service._firebase_service = mock_firebase_instance
            
            # Test channel
            channel = Channel(
                channel_id="UCtest",
                title="Test Channel",
                last_video_id="old_video_id"
            )
            
            # Test with a short video (should return False and not save)
            short_video = Video(
                video_id="shortID123",
                title="Test Short",
                link="https://www.youtube.com/shorts/shortID123",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            
            result = bot_service._process_new_video(channel, short_video)
            assert result == False
            print("✅ Short video correctly filtered out (not saved)")
            
            # Verify Firebase methods were not called
            mock_firebase_instance.save_video.assert_not_called()
            mock_firebase_instance.update_channel_last_video.assert_not_called()
            
            # Test with a full video (should return True and save)
            full_video = Video(
                video_id="dQw4w9WgXcQ",
                title="Never Gonna Give You Up",
                link="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                published_at="2024-01-01T12:00:00Z",
                channel_id="UCtest",
                channel_title="Test Channel"
            )
            
            result = bot_service._process_new_video(channel, full_video)
            assert result == True
            print("✅ Full video correctly processed and saved")
            
            # Verify Firebase methods were called
            mock_firebase_instance.save_video.assert_called_once_with(full_video)
            mock_firebase_instance.update_channel_last_video.assert_called_once_with("UCtest", "dQw4w9WgXcQ")
            
            print("✅ All process_new_video tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing YouTube Shorts Filtering")
    print("=" * 60)
    
    try:
        test_is_full_youtube_video()
        test_process_new_video_filtering()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Shorts filtering is working correctly.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)