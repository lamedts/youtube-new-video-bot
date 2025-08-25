#!/usr/bin/env python3
"""
Remove YouTube Shorts from Firestore

This script scans the Firestore 'videos' collection and removes videos 
that do not have the full YouTube watch URL format (https://www.youtube.com/watch?v=*).
This includes YouTube Shorts and other non-standard video formats.
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.firebase_service import FirebaseService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def is_full_youtube_video(video_data: Dict[str, Any]) -> bool:
    """Check if video has full YouTube watch URL format (not a short)."""
    link = video_data.get('link', '')
    if not link:
        return False
    
    # Check if the URL matches the full YouTube watch format
    return link.startswith("https://www.youtube.com/watch?v=")


def get_all_videos(firebase_service: FirebaseService) -> List[Dict[str, Any]]:
    """Get all videos from Firestore."""
    if not firebase_service._db:
        return []
    
    try:
        print("[remove-short] Fetching all videos from Firestore...")
        docs = firebase_service._db.collection('videos').get()
        videos = []
        
        for doc in docs:
            video_data = doc.to_dict()
            video_data['doc_id'] = doc.id  # Store document ID
            videos.append(video_data)
        
        print(f"[remove-short] Found {len(videos)} total videos in Firestore")
        return videos
        
    except Exception as e:
        print(f"[remove-short] Error fetching videos: {e}")
        return []


def delete_video(firebase_service: FirebaseService, doc_id: str, title: str) -> bool:
    """Delete a video from Firestore."""
    if not firebase_service._db:
        return False
    
    try:
        firebase_service._db.collection('videos').document(doc_id).delete()
        print(f"[remove-short] Deleted: {title[:50]}{'...' if len(title) > 50 else ''}")
        return True
    except Exception as e:
        print(f"[remove-short] Error deleting video {doc_id}: {e}")
        return False


def main():
    """Main execution function."""
    print("=" * 60)
    print("YouTube Shorts Removal Tool")
    print("=" * 60)
    
    # Initialize Firebase
    firebase_credentials_file = os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase-service-account.json")
    
    if not os.path.exists(firebase_credentials_file):
        print(f"[remove-short] Error: Firebase credentials file not found: {firebase_credentials_file}")
        print("[remove-short] Please ensure FIREBASE_CREDENTIALS_FILE is set correctly in .env")
        sys.exit(1)
    
    try:
        firebase_service = FirebaseService(firebase_credentials_file)
        if not firebase_service.is_available:
            print("[remove-short] Error: Firebase service not available")
            sys.exit(1)
        
        print("[remove-short] Firebase connection established")
        
    except Exception as e:
        print(f"[remove-short] Error initializing Firebase: {e}")
        sys.exit(1)
    
    # Get all videos
    all_videos = get_all_videos(firebase_service)
    if not all_videos:
        print("[remove-short] No videos found or error occurred. Exiting.")
        return
    
    # Analyze videos
    full_videos = []
    short_videos = []
    
    for video in all_videos:
        if is_full_youtube_video(video):
            full_videos.append(video)
        else:
            short_videos.append(video)
    
    print(f"\n[remove-short] Video Analysis:")
    print(f"  - Full YouTube videos: {len(full_videos)}")
    print(f"  - Shorts/non-standard videos: {len(short_videos)}")
    
    if not short_videos:
        print("\n[remove-short] No shorts found to remove. All videos are in full format.")
        return
    
    # Show some examples of videos to be removed
    print(f"\n[remove-short] Examples of videos to be removed:")
    for i, video in enumerate(short_videos[:5]):  # Show first 5
        title = video.get('title', 'Unknown Title')
        link = video.get('link', 'No Link')
        print(f"  {i+1}. {title[:60]}{'...' if len(title) > 60 else ''}")
        print(f"     URL: {link}")
    
    if len(short_videos) > 5:
        print(f"     ... and {len(short_videos) - 5} more")
    
    # Confirmation prompt
    print(f"\n[remove-short] WARNING: This will permanently delete {len(short_videos)} videos from Firestore!")
    print("[remove-short] This action cannot be undone.")
    
    while True:
        confirm = input("\n[remove-short] Do you want to proceed? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            break
        elif confirm in ['no', 'n']:
            print("[remove-short] Operation cancelled.")
            return
        else:
            print("[remove-short] Please enter 'yes' or 'no'")
    
    # Delete shorts
    print(f"\n[remove-short] Starting deletion of {len(short_videos)} shorts...")
    deleted_count = 0
    failed_count = 0
    
    start_time = datetime.now()
    
    for i, video in enumerate(short_videos, 1):
        doc_id = video['doc_id']
        title = video.get('title', 'Unknown Title')
        
        print(f"[remove-short] [{i}/{len(short_videos)}] ", end="")
        
        if delete_video(firebase_service, doc_id, title):
            deleted_count += 1
        else:
            failed_count += 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Summary
    print("\n" + "=" * 60)
    print("REMOVAL SUMMARY")
    print("=" * 60)
    print(f"Total videos processed: {len(short_videos)}")
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed to delete: {failed_count}")
    print(f"Remaining full videos: {len(full_videos)}")
    print(f"Operation duration: {duration:.2f} seconds")
    print("=" * 60)
    
    if deleted_count > 0:
        print(f"[remove-short] ✅ Successfully removed {deleted_count} shorts from Firestore")
    
    if failed_count > 0:
        print(f"[remove-short] ⚠️  {failed_count} deletions failed - please check the logs above")
    
    print("[remove-short] Operation completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[remove-short] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[remove-short] Unexpected error: {e}")
        sys.exit(1)