#!/usr/bin/env python3
"""
Test transfa upload - Run this to verify your setup
"""

import transfa
import os
import tempfile

def test_transfa():
    print("☁️ Testing transfa upload...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file for transfa upload from Gift Video Receiver")
        test_file = f.name
    
    try:
        print(f"📁 Test file: {test_file}")
        
        # Upload to transfa
        result = transfa.upload(test_file, ttl="1h")
        
        if result and hasattr(result, 'url'):
            print(f"✅ Upload successful!")
            print(f"🔗 Link: {result.url}")
            if hasattr(result, 'delete_token'):
                print(f"🗑️ Delete token: {result.delete_token}")
            print(f"⏰ Expires in: 1 hour")
        else:
            print(f"❌ Upload failed: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.unlink(test_file)
            print("🧹 Test file cleaned up")

if __name__ == '__main__':
    test_transfa()