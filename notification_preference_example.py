#!/usr/bin/env python3
"""
Example script demonstrating notification preference functionality.

This shows how to use the new notify field to control which channels
send notifications locally, since YouTube API doesn't expose bell settings.
"""

import sys
from src.config.settings import BotConfig
from src.services.bot_service import YouTubeBotService


def demonstrate_notification_preferences():
    """Demonstrate how to manage notification preferences."""
    
    print("🔔 Notification Preference Management Demo")
    print("=" * 50)
    
    try:
        # Load configuration
        config = BotConfig.from_env()
        bot_service = YouTubeBotService(config)
        
        # Example: Get all channels and their notification status
        print("\n📋 Current Channel Notification Settings:")
        channels = bot_service._firebase_service.get_all_channels()
        
        for channel in channels:
            status = "🔔 Enabled" if channel.notify else "🔕 Disabled"
            print(f"  {channel.title}: {status}")
        
        # Example: Toggle notifications for a specific channel
        if channels:
            example_channel = channels[0]
            print(f"\n🔄 Toggling notifications for: {example_channel.title}")
            
            # Toggle notification preference
            success = bot_service.toggle_channel_notifications(example_channel.channel_id)
            
            if success:
                # Get updated status
                updated_channel = bot_service._firebase_service.get_channel(example_channel.channel_id)
                new_status = "🔔 Enabled" if updated_channel.notify else "🔕 Disabled"
                print(f"   New status: {new_status}")
            else:
                print("   ❌ Failed to toggle notifications")
        
        # Example: Set specific notification preference
        if len(channels) > 1:
            example_channel = channels[1]
            print(f"\n🎯 Setting notifications OFF for: {example_channel.title}")
            
            success = bot_service.set_channel_notifications(example_channel.channel_id, False)
            
            if success:
                print("   ✅ Notifications disabled")
            else:
                print("   ❌ Failed to disable notifications")
        
        print("\n💡 Benefits of local notification preferences:")
        print("   • Control notifications per channel without YouTube API limits")
        print("   • Independent of YouTube's bell notification settings")
        print("   • Persisted in Firebase for consistency across restarts")
        print("   • Backward compatible (existing channels default to enabled)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure Firebase is properly configured and accessible.")


if __name__ == "__main__":
    demonstrate_notification_preferences()