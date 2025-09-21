#!/usr/bin/env python3
"""
Migration script to update Video documents to use DocumentReference for channels.

This script will:
1. Query all existing video documents
2. For each video with channel_id field, replace it with channel_ref DocumentReference
3. Remove the old channel_id and channel_title fields
4. Preserve all other video data
"""

import os
import sys
from typing import Optional

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime


class VideoChannelMigration:
    """Handles migration of video documents to use DocumentReference for channels."""

    def __init__(self, credentials_file: str, dry_run: bool = True):
        self.credentials_file = credentials_file
        self.dry_run = dry_run
        self.db: Optional[firestore.Client] = None
        self.stats = {
            'total_videos': 0,
            'videos_migrated': 0,
            'videos_skipped': 0,
            'errors': 0
        }

        self._initialize_firebase()

    def _initialize_firebase(self) -> None:
        """Initialize Firebase connection."""
        try:
            if not firebase_admin._apps:
                if os.path.exists(self.credentials_file):
                    cred = credentials.Certificate(self.credentials_file)
                    firebase_admin.initialize_app(cred)
                    print(f"[migration] Initialized Firebase with service account: {self.credentials_file}")
                else:
                    firebase_admin.initialize_app()
                    print("[migration] Initialized Firebase with default credentials")

            self.db = firestore.client()
            print("[migration] Firebase client ready")
        except Exception as e:
            print(f"[migration] Error initializing Firebase: {e}")
            raise

    def run_migration(self) -> None:
        """Run the complete migration process."""
        print(f"[migration] Starting video channel migration (dry_run={self.dry_run})")
        print(f"[migration] Timestamp: {datetime.now().isoformat()}")

        try:
            # Get all video documents
            videos_collection = self.db.collection('videos')
            docs = videos_collection.get()
            self.stats['total_videos'] = len(docs)

            print(f"[migration] Found {self.stats['total_videos']} video documents")

            # Process each video document
            for doc in docs:
                self._migrate_video_document(doc)

            # Print final statistics
            self._print_final_stats()

        except Exception as e:
            print(f"[migration] Error during migration: {e}")
            self.stats['errors'] += 1
            raise

    def _migrate_video_document(self, doc) -> None:
        """Migrate a single video document."""
        try:
            data = doc.to_dict()
            video_id = doc.id

            # Check if this document needs migration
            if not self._needs_migration(data):
                print(f"[migration] Skipping {video_id}: already migrated or missing channel_id")
                self.stats['videos_skipped'] += 1
                return

            # Prepare the migration data
            channel_id = data.get('channel_id')
            if not channel_id:
                print(f"[migration] Skipping {video_id}: no channel_id found")
                self.stats['videos_skipped'] += 1
                return

            # Create DocumentReference for the channel
            channel_ref = self.db.collection('subscriptions').document(channel_id)

            # Prepare update data
            update_data = {
                'channel_ref': channel_ref
            }

            # Prepare fields to delete
            fields_to_delete = []
            if 'channel_id' in data:
                fields_to_delete.append('channel_id')
            if 'channel_title' in data:
                fields_to_delete.append('channel_title')

            # Execute the migration
            if self.dry_run:
                print(f"[migration] DRY RUN - Would migrate {video_id}:")
                print(f"  - Add channel_ref -> subscriptions/{channel_id}")
                if fields_to_delete:
                    print(f"  - Remove fields: {', '.join(fields_to_delete)}")
            else:
                # Update the document
                doc.reference.update(update_data)

                # Delete old fields
                for field in fields_to_delete:
                    doc.reference.update({field: firestore.DELETE_FIELD})

                print(f"[migration] Migrated {video_id}: channel_id={channel_id} -> channel_ref")

            self.stats['videos_migrated'] += 1

        except Exception as e:
            print(f"[migration] Error migrating video {doc.id}: {e}")
            self.stats['errors'] += 1

    def _needs_migration(self, data: dict) -> bool:
        """Check if a video document needs migration."""
        # Skip if already has channel_ref
        if 'channel_ref' in data:
            return False

        # Needs migration if has channel_id
        return 'channel_id' in data

    def _print_final_stats(self) -> None:
        """Print final migration statistics."""
        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Total videos found:     {self.stats['total_videos']}")
        print(f"Videos migrated:        {self.stats['videos_migrated']}")
        print(f"Videos skipped:         {self.stats['videos_skipped']}")
        print(f"Errors encountered:     {self.stats['errors']}")
        print("="*50)

        if self.dry_run:
            print("\nThis was a DRY RUN - no changes were made to the database.")
            print("Run with --execute to perform the actual migration.")
        else:
            print("\nMigration completed successfully!")


def main():
    """Main entry point for the migration script."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate video documents to use channel DocumentReference')
    parser.add_argument('--credentials', '-c',
                       default='credentials/firebase-adminsdk.json',
                       help='Path to Firebase service account credentials file')
    parser.add_argument('--execute', action='store_true',
                       help='Execute the migration (default is dry-run)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Run in dry-run mode (default)')

    args = parser.parse_args()

    # Determine if this is a dry run
    dry_run = not args.execute

    if dry_run:
        print("Running in DRY RUN mode - no changes will be made")
        print("Use --execute flag to perform actual migration")
    else:
        print("EXECUTING MIGRATION - changes will be made to the database")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Migration cancelled")
            return

    try:
        migration = VideoChannelMigration(args.credentials, dry_run=dry_run)
        migration.run_migration()

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()