import os
import time
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

import requests
import feedparser
from dotenv import load_dotenv

# Google / YouTube API
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# -----------------------------
# Load .env
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

STATE_FILE = os.getenv("STATE_FILE", "state.json")
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("TOKEN_FILE", "token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

SUBS_REFRESH_MINUTES = int(os.getenv("SUBS_REFRESH_MINUTES", "1440"))
VIDEO_POLL_SECONDS = int(os.getenv("VIDEO_POLL_SECONDS", "600"))
INIT_MODE = os.getenv("INIT_MODE", "false").lower() in ("1", "true", "yes", "y")

# -----------------------------
# State management
# -----------------------------
def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"channels": {}, "last_subs_sync": None}

def save_state(state: Dict[str, Any]) -> None:
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)

STATE = load_state()

# -----------------------------
# Telegram helpers
# -----------------------------
def tg_send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print("Telegram send_message exception:", e)

def tg_send_photo(photo_url: str, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print("Telegram send_photo exception:", e)

# -----------------------------
# YouTube OAuth (headless)
# -----------------------------
def get_youtube_client():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Use console flow for headless server
            creds = flow.run_console()
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

# -----------------------------
# Get authenticated user info
# -----------------------------
def get_my_channel_info(youtube):
    try:
        resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            return None
        ch = items[0]
        return {
            "title": ch["snippet"]["title"],
            "subs_count": ch["statistics"].get("subscriberCount", "N/A"),
            "video_count": ch["statistics"].get("videoCount", "N/A"),
            "channel_id": ch["id"]
        }
    except Exception as e:
        print("[user_info] Error:", e)
        return None

# -----------------------------
# Subscriptions sync
# -----------------------------
def fetch_all_subscriptions(youtube) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    page_token = None
    while True:
        resp = youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50,
            pageToken=page_token
        ).execute()
        for it in resp.get("items", []):
            sn = it.get("snippet", {})
            res = sn.get("resourceId", {})
            cid = res.get("channelId")
            title = sn.get("title", "")
            if cid:
                items.append((cid, title))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items

def ensure_channel_in_state(channel_id: str, title: str) -> bool:
    if channel_id in STATE["channels"]:
        if title and STATE["channels"][channel_id].get("title") != title:
            STATE["channels"][channel_id]["title"] = title
            save_state(STATE)
        return False
    STATE["channels"][channel_id] = {
        "title": title or channel_id,
        "last_video_id": "",
        "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    }
    save_state(STATE)
    return True

def sync_subscriptions():
    print("[subs] Syncing subscriptions…")
    try:
        yt = get_youtube_client()
        subs = fetch_all_subscriptions(yt)
        newly_added = []
        for cid, title in subs:
            added = ensure_channel_in_state(cid, title)
            if added:
                newly_added.append((cid, title))
        STATE["last_subs_sync"] = datetime.now(timezone.utc).isoformat()
        save_state(STATE)

        for cid, title in newly_added:
            msg = f"🆕 *New subscription detected*\n*{title}*\nhttps://www.youtube.com/channel/{cid}"
            if not INIT_MODE:
                tg_send_message(msg)
        print(f"[subs] Added {len(newly_added)} new channels.")
    except Exception as e:
        print("[subs] Error during sync:", e)

# -----------------------------
# RSS polling with thumbnails
# -----------------------------
def get_latest_video(channel_id: str, rss_url: str):
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            return None
        latest = feed.entries[0]
        vid = getattr(latest, "yt_videoid", None) or latest.get("id")
        title = latest.get("title", "Untitled")
        link = latest.get("link") or f"https://www.youtube.com/watch?v={vid}" if vid else None
        thumbnail = latest.get("media_thumbnail", [{}])[0].get("url") or latest.get("media_content", [{}])[0].get("url")
        return vid, title, link, thumbnail
    except Exception as e:
        print(f"[rss] Error parsing {rss_url}: {e}")
        return None

def poll_videos_once():
    changes = 0
    for cid, info in list(STATE["channels"].items()):
        rss = info["rss_url"]
        title = info.get("title", cid)
        last_seen = info.get("last_video_id", "")

        latest = get_latest_video(cid, rss)
        if not latest:
            continue
        vid, vtitle, link, thumbnail = latest
        if not vid:
            continue

        # first-time bootstrap
        if not last_seen:
            STATE["channels"][cid]["last_video_id"] = vid
            save_state(STATE)
            if not INIT_MODE:
                text = f"📺 *{title}*\nNew video: *{vtitle}*\n{link}"
                if thumbnail:
                    tg_send_photo(thumbnail, text)
                else:
                    tg_send_message(text)
            continue

        if vid != last_seen:
            STATE["channels"][cid]["last_video_id"] = vid
            save_state(STATE)
            text = f"📺 *{title}*\nNew video: *{vtitle}*\n{link}"
            if thumbnail:
                tg_send_photo(thumbnail, text)
            else:
                tg_send_message(text)
            changes += 1
    if changes:
        print(f"[rss] Sent {changes} new video notifications.")
    else:
        print("[rss] No new videos found.")

# -----------------------------
# Schedulers
# -----------------------------
def run_subscription_refresher():
    sync_subscriptions()
    while True:
        time.sleep(SUBS_REFRESH_MINUTES * 60)
        sync_subscriptions()

def run_video_poller():
    while True:
        poll_videos_once()
        time.sleep(VIDEO_POLL_SECONDS)

# -----------------------------
# Main
# -----------------------------
def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    # Initialize YouTube client for startup info
    yt = get_youtube_client()
    info = get_my_channel_info(yt)
    if info:
        msg = f"🚀 YouTube → Telegram bot 'youtube-new-video-bot' has started.\n"
        msg += f"User: *{info['title']}*\n"
        msg += f"Channel ID: `{info['channel_id']}`\n"
        msg += f"Subscribers: {info['subs_count']}\n"
        msg += f"Videos: {info['video_count']}"
    else:
        msg = "🚀 YouTube → Telegram bot 'youtube-new-video-bot' has started.\nCould not fetch user info."

    tg_send_message(msg)

    print("YouTube → Telegram notifier starting…")
    print(f"INIT_MODE={INIT_MODE}, VIDEO_POLL_SECONDS={VIDEO_POLL_SECONDS}, SUBS_REFRESH_MINUTES={SUBS_REFRESH_MINUTES}")

    t1 = threading.Thread(target=run_subscription_refresher, daemon=True)
    t2 = threading.Thread(target=run_video_poller, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Shutting down…")

if __name__ == "__main__":
    main()
