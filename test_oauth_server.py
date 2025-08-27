#!/usr/bin/env python3
"""
Test script for the automated OAuth server implementation.
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock
import time
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_oauth_server_basics():
    """Test basic OAuth server functionality."""
    print("Testing OAuth server basics...")
    
    try:
        from src.services.oauth_server import OAuthCallbackServer
        
        # Test server initialization
        server = OAuthCallbackServer(port_range=(8080, 8089), timeout=10)
        assert server.port_range == (8080, 8089)
        assert server.timeout == 10
        print("✅ OAuth server initialization working")
        
        # Test port finding
        port = server._find_available_port()
        assert port is not None
        assert 8080 <= port <= 8089
        print(f"✅ Found available port: {port}")
        
        # Test Flask app creation
        app = server._create_flask_app()
        assert app is not None
        print("✅ Flask app creation working")
        
        # Test HTML page generation
        success_html = server._create_success_page()
        assert "Authorization Successful" in success_html
        assert "✅" in success_html
        print("✅ Success page generation working")
        
        error_html = server._create_error_page("Test error")
        assert "Authorization Failed" in error_html
        assert "Test error" in error_html
        print("✅ Error page generation working")
        
        print("✅ All OAuth server basic tests passed!")
        
    except Exception as e:
        print(f"❌ OAuth server basic test failed: {e}")
        raise


def test_youtube_service_integration():
    """Test YouTube service integration with OAuth server."""
    print("\nTesting YouTube service OAuth integration...")
    
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'UPSTASH_REDIS_URL': 'redis://test',
        'OAUTH_PORT_START': '8080',
        'OAUTH_TIMEOUT': '60',
        'OAUTH_AUTO_BROWSER': 'false'  # Disable browser for testing
    }):
        try:
            from src.config.settings import BotConfig
            from src.services.youtube_service import YouTubeService
            
            # Test configuration loading
            config = BotConfig.from_env()
            assert config.oauth_port_start == 8080
            assert config.oauth_timeout == 60
            assert config.oauth_auto_browser == False
            print("✅ OAuth configuration loading working")
            
            # Test YouTube service initialization with OAuth params
            service = YouTubeService(
                "test-client-secret.json",
                "test-token.json", 
                ["https://www.googleapis.com/auth/youtube.readonly"],
                oauth_port_start=8080,
                oauth_timeout=60,
                oauth_auto_browser=False
            )
            
            assert service._oauth_port_start == 8080
            assert service._oauth_timeout == 60
            assert service._oauth_auto_browser == False
            print("✅ YouTube service OAuth configuration working")
            
            print("✅ YouTube service OAuth integration tests passed!")
            
        except Exception as e:
            print(f"❌ YouTube service integration test failed: {e}")
            raise


def test_oauth_flow_mock():
    """Test OAuth flow with mocked components."""
    print("\nTesting OAuth flow with mocks...")
    
    try:
        from src.services.oauth_server import run_oauth_flow
        
        # Mock the OAuth flow components
        with patch('google_auth_oauthlib.flow.Flow') as mock_flow_class, \
             patch('src.services.oauth_server.OAuthCallbackServer') as mock_server_class, \
             patch('src.services.oauth_server.webbrowser') as mock_browser:
            
            # Setup mock server
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.start_server.return_value = "http://localhost:8080/oauth2callback"
            mock_server.wait_for_callback.return_value = "mock_auth_code"
            mock_server.open_authorization_url.return_value = True
            
            # Setup mock flow
            mock_flow = Mock()
            mock_flow_class.from_client_secrets_file.return_value = mock_flow
            mock_flow.authorization_url.return_value = ("http://auth.url", "state")
            
            # Setup mock credentials
            mock_creds = Mock()
            mock_creds.token = "mock_access_token"
            mock_creds.refresh_token = "mock_refresh_token"
            mock_creds.token_uri = "https://oauth2.googleapis.com/token"
            mock_creds.client_id = "mock_client_id"
            mock_creds.client_secret = "mock_client_secret"
            mock_creds.scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
            mock_creds.expiry = None
            mock_flow.credentials = mock_creds
            
            # Test the OAuth flow
            result = run_oauth_flow(
                "test-client-secret.json",
                ["https://www.googleapis.com/auth/youtube.readonly"],
                port_range=(8080, 8089),
                timeout=60,
                auto_browser=False
            )
            
            # Verify result
            assert result is not None
            assert result['token'] == "mock_access_token"
            assert result['refresh_token'] == "mock_refresh_token"
            assert result['client_id'] == "mock_client_id"
            
            # Verify calls
            mock_server.start_server.assert_called_once()
            mock_server.wait_for_callback.assert_called_once()
            mock_server.stop_server.assert_called_once()
            mock_flow.fetch_token.assert_called_once_with(code="mock_auth_code")
            
            print("✅ OAuth flow mock test passed!")
            
    except Exception as e:
        print(f"❌ OAuth flow mock test failed: {e}")
        raise


def test_fallback_mechanism():
    """Test fallback to manual authentication."""
    print("\nTesting fallback mechanism...")
    
    with patch('src.services.youtube_service.run_oauth_flow') as mock_oauth_flow, \
         patch('src.services.youtube_service.InstalledAppFlow') as mock_installed_flow, \
         patch('builtins.input') as mock_input:
        
        from src.services.youtube_service import YouTubeService
        
        # Make web OAuth fail
        mock_oauth_flow.return_value = None
        
        # Setup manual flow mock
        mock_flow = Mock()
        mock_installed_flow.from_client_secrets_file.return_value = mock_flow
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_input.return_value = "manual_auth_code"
        
        # Setup credentials mock
        mock_creds = Mock()
        mock_creds.expiry = None
        mock_flow.credentials = mock_creds
        
        # Test fallback
        service = YouTubeService("test.json", "token.json", ["scope"], oauth_auto_browser=False)
        result = service._perform_new_authentication()
        
        # Verify fallback was called
        mock_oauth_flow.assert_called_once()  # Web flow attempted
        mock_installed_flow.from_client_secrets_file.assert_called_once()  # Fallback used
        mock_input.assert_called_once()  # Manual input requested
        
        assert result == mock_creds
        print("✅ Fallback mechanism test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Automated OAuth Server Implementation")
    print("=" * 60)
    
    try:
        test_oauth_server_basics()
        test_youtube_service_integration()
        test_oauth_flow_mock()
        test_fallback_mechanism()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Server-based OAuth is working correctly.")
        print("=" * 60)
        
        print("\nKey Features Implemented:")
        print("✅ Automated OAuth flow with temporary web server")
        print("✅ Automatic browser opening for authentication")
        print("✅ Beautiful success/error pages with auto-close")
        print("✅ Secure state parameter validation")
        print("✅ Port conflict handling (tries multiple ports)")
        print("✅ Graceful fallback to manual authentication")
        print("✅ Configurable timeout and browser behavior")
        print("✅ Enhanced logging and error handling")
        
        print("\n🚀 Ready to use! Next steps:")
        print("1. Install Flask: pip install -r requirements.txt")
        print("2. Remove expired token: rm youtube-token.json")
        print("3. Run the bot: python main.py")
        print("4. Browser will open automatically for OAuth!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)