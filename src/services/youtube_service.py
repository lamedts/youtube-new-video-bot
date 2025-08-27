"""YouTube API service."""

import os
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
import feedparser

from ..models.channel import UserChannelInfo, Channel
from ..models.video import Video
from .oauth_server import run_oauth_flow


class YouTubeService:
    """Service for YouTube API operations."""
    
    def __init__(self, client_secret_file: str, token_file: str, scopes: List[str], 
                 oauth_port_start: int = 8080, oauth_timeout: int = 300, oauth_auto_browser: bool = True):
        self._client_secret_file = client_secret_file
        self._token_file = token_file
        self._scopes = scopes
        self._client = None
        self._oauth_port_start = oauth_port_start
        self._oauth_timeout = oauth_timeout
        self._oauth_auto_browser = oauth_auto_browser
    
    def _get_authenticated_client(self):
        """Get authenticated YouTube client with robust token refresh logic."""
        # Check if we need to refresh existing client credentials
        if self._client and hasattr(self, '_last_token_check'):
            # Check token status every 30 minutes to be proactive
            if datetime.now() - self._last_token_check < timedelta(minutes=30):
                return self._client
        
        creds = None
        if os.path.exists(self._token_file):
            try:
                creds = Credentials.from_authorized_user_file(self._token_file, self._scopes)
                print(f"[youtube] Loaded credentials from {self._token_file}")
            except Exception as e:
                print(f"[youtube] Error loading token file: {e}")
                creds = None
        
        # Enhanced credential validation and refresh logic
        if creds:
            creds_refreshed = self._ensure_valid_credentials(creds)
            if creds_refreshed:
                creds = creds_refreshed
            elif not creds.valid:
                print("[youtube] Credentials invalid and refresh failed, need new authentication")
                creds = None
        
        # If no valid credentials, start new authentication flow
        if not creds:
            creds = self._perform_new_authentication()
        
        # Save updated credentials and create client
        if creds:
            try:
                with open(self._token_file, "w") as f:
                    f.write(creds.to_json())
                print(f"[youtube] Saved updated credentials to {self._token_file}")
                
                self._client = build("youtube", "v3", credentials=creds)
                self._last_token_check = datetime.now()
                print("[youtube] YouTube API client initialized successfully")
                return self._client
            except Exception as e:
                print(f"[youtube] Error saving credentials or building client: {e}")
                raise
        
        raise Exception("Failed to obtain valid YouTube API credentials")
    
    def _ensure_valid_credentials(self, creds):
        """Ensure credentials are valid, refreshing if needed."""
        if not creds:
            return None
            
        # Check if token will expire soon (within 5 minutes) or is already expired
        now = datetime.now()
        if creds.expiry:
            expires_soon = creds.expiry <= now + timedelta(minutes=5)
            if expires_soon:
                print(f"[youtube] Token expires at {creds.expiry}, refreshing proactively...")
            elif creds.expired:
                print("[youtube] Token has expired, attempting refresh...")
        
        # If credentials are invalid or will expire soon, try to refresh
        if not creds.valid or (creds.expiry and creds.expiry <= now + timedelta(minutes=5)):
            if creds.refresh_token:
                try:
                    print("[youtube] Refreshing access token...")
                    creds.refresh(Request())
                    print(f"[youtube] Token refreshed successfully, expires at: {creds.expiry}")
                    return creds
                except RefreshError as e:
                    print(f"[youtube] Refresh failed: {e}")
                    print("[youtube] Refresh token may be invalid, need new authentication")
                    return None
                except Exception as e:
                    print(f"[youtube] Unexpected error during refresh: {e}")
                    return None
            else:
                print("[youtube] No refresh token available, need new authentication")
                return None
        
        # Credentials are valid and not expiring soon
        if creds.expiry:
            time_until_expiry = creds.expiry - now
            print(f"[youtube] Token valid, expires in {time_until_expiry}")
        else:
            print("[youtube] Token valid (no expiry info)")
        
        return creds
    
    def _perform_new_authentication(self):
        """Perform new OAuth authentication flow using web server."""
        try:
            print("[youtube] Starting automated OAuth authentication flow...")
            
            # Try web-based OAuth flow first
            port_range = (self._oauth_port_start, self._oauth_port_start + 9)
            credentials_dict = run_oauth_flow(
                self._client_secret_file,
                self._scopes,
                port_range=port_range,
                timeout=self._oauth_timeout,
                auto_browser=self._oauth_auto_browser
            )
            
            if credentials_dict:
                # Convert dict back to Credentials object
                creds = Credentials(
                    token=credentials_dict['token'],
                    refresh_token=credentials_dict['refresh_token'],
                    token_uri=credentials_dict['token_uri'],
                    client_id=credentials_dict['client_id'],
                    client_secret=credentials_dict['client_secret'],
                    scopes=credentials_dict['scopes']
                )
                
                # Set expiry if available
                if credentials_dict.get('expiry'):
                    creds.expiry = datetime.fromisoformat(credentials_dict['expiry'])
                
                print(f"[youtube] Web-based authentication successful, expires at: {creds.expiry}")
                return creds
            
            # Fallback to manual flow if web flow fails
            print("[youtube] Web-based OAuth failed, falling back to manual flow...")
            return self._perform_manual_authentication()
            
        except Exception as e:
            print(f"[youtube] Automated authentication flow failed: {e}")
            print("[youtube] Falling back to manual authentication...")
            return self._perform_manual_authentication()
    
    def _perform_manual_authentication(self):
        """Perform manual OAuth authentication flow as fallback."""
        try:
            print("[youtube] Starting manual authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                self._client_secret_file, self._scopes
            )
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                include_granted_scopes='true'
            )
            print(f"[youtube] Please visit this URL to authorize the application:")
            print(f"[youtube] {auth_url}")
            
            auth_code = input("[youtube] Enter the authorization code: ")
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            print(f"[youtube] Manual authentication successful, expires at: {creds.expiry}")
            return creds
            
        except Exception as e:
            print(f"[youtube] Manual authentication flow failed: {e}")
            return None
    
    def get_user_channel_info(self) -> Optional[UserChannelInfo]:
        """Get authenticated user's channel information."""
        try:
            youtube = self._get_authenticated_client()
            resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
            
            items = resp.get("items", [])
            if not items:
                return None
            
            ch = items[0]
            return UserChannelInfo(
                title=ch["snippet"]["title"],
                subscriber_count=ch["statistics"].get("subscriberCount", "N/A"),
                video_count=ch["statistics"].get("videoCount", "N/A"),
                channel_id=ch["id"]
            )
        except Exception as e:
            return self._handle_api_error("get_user_channel_info", e)
    
    def fetch_all_subscriptions(self) -> List[Tuple[str, str, Optional[str]]]:
        """Fetch all user subscriptions with thumbnails."""
        items: List[Tuple[str, str, Optional[str]]] = []
        page_token = None
        
        try:
            youtube = self._get_authenticated_client()
        except Exception as e:
            print(f"[youtube] Failed to get authenticated client for subscriptions: {e}")
            return items
        
        while True:
            try:
                resp = youtube.subscriptions().list(
                    part="snippet",
                    mine=True,
                    maxResults=50,
                    pageToken=page_token
                ).execute()
                
                for item in resp.get("items", []):
                    snippet = item.get("snippet", {})
                    resource = snippet.get("resourceId", {})
                    channel_id = resource.get("channelId")
                    title = snippet.get("title", "")
                    
                    # Get thumbnail URL (prefer medium quality)
                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail_url = None
                    if thumbnails:
                        # Try different quality levels
                        for quality in ["medium", "high", "default"]:
                            if quality in thumbnails:
                                thumbnail_url = thumbnails[quality].get("url")
                                break
                    
                    if channel_id:
                        items.append((channel_id, title, thumbnail_url))
                
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
                    
            except Exception as e:
                error_handled = self._handle_api_error("fetch_subscriptions", e)
                if error_handled is None:  # Auth error, stop trying
                    break
                # For other errors, log and continue
                print(f"[youtube] Error fetching subscriptions page, continuing: {e}")
                break
        
        return items
    
    def _handle_api_error(self, operation: str, error: Exception):
        """Handle API errors with intelligent retry logic."""
        error_str = str(error)
        print(f"[youtube] Error in {operation}: {error}")
        
        # Check for authentication-related errors
        auth_errors = [
            "invalid_grant",
            "Token has been expired",
            "invalid_token",
            "unauthorized",
            "authentication required"
        ]
        
        if any(auth_error in error_str.lower() for auth_error in auth_errors):
            print("[youtube] Authentication error detected, clearing client cache...")
            self._client = None
            
            # Try once more with fresh authentication
            try:
                print("[youtube] Attempting to re-authenticate...")
                youtube = self._get_authenticated_client()
                print("[youtube] Re-authentication successful")
                return "retry"  # Signal caller to retry the operation
            except Exception as retry_error:
                print(f"[youtube] Re-authentication failed: {retry_error}")
                return None  # Signal permanent failure
        
        # For non-auth errors, just log and return None
        return None


class RSSService:
    """Service for RSS feed operations."""
    
    @staticmethod
    def get_latest_video(channel: Channel) -> Optional[Video]:
        """Get latest video from channel's RSS feed."""
        try:
            feed = feedparser.parse(channel.rss_url)
            if not feed.entries:
                return None
            
            latest = feed.entries[0]
            return Video.from_rss_entry(latest, channel.channel_id, channel.title)
            
        except Exception as e:
            print(f"[rss] Error parsing {channel.rss_url}: {e}")
            return None