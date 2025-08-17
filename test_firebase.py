#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase-service-account.json")

def test_firebase_connection():
    print("Testing Firebase connection...")
    
    try:
        if not firebase_admin._apps:
            if os.path.exists(FIREBASE_CREDENTIALS_FILE):
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with service account")
            else:
                firebase_admin.initialize_app()
                print("✅ Firebase initialized with default credentials")
        
        db = firestore.client()
        print("✅ Firestore client created successfully")
        
        # Test write operation
        test_data = {
            'test_field': 'Hello Firebase!',
            'timestamp': firestore.SERVER_TIMESTAMP,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        doc_ref = db.collection('test').document('connection_test')
        doc_ref.set(test_data)
        print("✅ Test document written successfully")
        
        # Test read operation
        doc = doc_ref.get()
        if doc.exists:
            print(f"✅ Test document read successfully: {doc.to_dict()}")
        else:
            print("❌ Test document not found")
        
        # Clean up test document
        doc_ref.delete()
        print("✅ Test document deleted successfully")
        
        print("\n🎉 Firebase integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_firebase_connection()
    sys.exit(0 if success else 1)