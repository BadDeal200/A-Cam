#!/usr/bin/env python3
"""
Test FileGoat upload
"""

import requests
import os
import tempfile

def test_filegoat_upload():
    print("☁️ Testing FileGoat upload...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file from Gift Video Receiver with FileGoat")
        test_file = f.name
    
    try:
        print(f"📁 Test file: {test_file}")
        
        with open(test_file, "rb") as f:
            response = requests.post(
                "https://filego.at/upload",
                files={"file": (os.path.basename(test_file), f)},
                data={"expiry": 86400},  # 1 day in seconds
                timeout=30
            )
        
        print(f"📋 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 Response: {result}")
            
            if result.get('url'):
                print(f"\n✅ Upload successful!")
                print(f"🔗 Link: {result.get('url')}")
                print(f"🗑️ Delete URL: {result.get('delete_url', 'Not provided')}")
                print(f"⏰ Expires: 1 day")
            else:
                print(f"❌ No URL in response")
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.unlink(test_file)
            print("🧹 Test file cleaned up")

if __name__ == '__main__':
    test_filegoat_upload()