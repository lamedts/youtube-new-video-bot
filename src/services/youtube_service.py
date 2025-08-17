"""YouTube API service."""

import os
from typing import List, Tuple, Optional
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import feedparser

from ..models.channel import UserChannelInfo, Channel
from ..models.video import Video


class YouTubeService:
    """Service for YouTube API operations."""
    
    def __init__(self, client_secret_file: str, token_file: str, scopes: List[str]):
        self._client_secret_file = client_secret_file
        self._token_file = token_file
        self._scopes = scopes
        self._client = None
    
    def _get_authenticated_client(self):
        """Get authenticated YouTube client."""
        if self._client:
            return self._client
        
        creds = None
        if os.path.exists(self._token_file):
            creds = Credentials.from_authorized_user_file(self._token_file, self._scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._client_secret_file, self._scopes
                )
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Please visit this URL to authorize the application: {auth_url}")
                auth_code = input("Enter the authorization code: ")
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            
            with open(self._token_file, "w") as f:
                f.write(creds.to_json())
        
        self._client = build("youtube", "v3", credentials=creds)
        return self._client
    
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
            print(f"[youtube] Error getting user info: {e}")
            return None
    
    def fetch_all_subscriptions(self) -> List[Tuple[str, str]]:
        """Fetch all user subscriptions."""
        items: List[Tuple[str, str]] = []
        page_token = None
        youtube = self._get_authenticated_client()
        
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
                    
                    if channel_id:
                        items.append((channel_id, title))
                
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"[youtube] Error fetching subscriptions: {e}")
                break
        
        return items


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