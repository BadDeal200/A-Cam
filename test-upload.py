#!/usr/bin/env python3
"""
Test Local Ngrok Server Media Upload & Direct Viewing
"""

import os
import tempfile
import requests

def test_local_upload():
    print("🌐 Testing Local Ngrok Server upload...")
    
    # Create a test video dummy file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.webm', delete=False) as f:
        f.write(b"DUMMY WEBM DATA FOR TESTING")
        test_file = f.name
    
    try:
        print(f"📁 Test file: {test_file}")
        
        with open(test_file, "rb") as f:
            response = requests.post(
                "http://localhost:5000/upload",
                files={"media": (os.path.basename(test_file), f, "video/webm")},
                data={"type": "video"},
                timeout=10
            )
        
        print(f"📋 Response Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Upload successful!")
            print(f"📁 Saved Name:  {result.get('filename')}")
            print(f"📺 Direct Link: {result.get('view_url')}")
            print(f"🖼️ Gallery:     {result.get('gallery_url')}")
        else:
            print(f"❌ Upload failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)
            print("🧹 Test file cleaned up")

if __name__ == '__main__':
    test_local_upload()