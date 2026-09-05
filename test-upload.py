#!/usr/bin/env python3
"""
Test tempfile.org upload
"""

import requests
import os
import tempfile

def test_tempfile_upload():
    print("☁️ Testing tempfile.org upload...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file from Gift Video Receiver")
        test_file = f.name
    
    try:
        print(f"📁 Test file: {test_file}")
        
        with open(test_file, "rb") as f:
            response = requests.post(
                "https://tempfile.org/api/upload/local",
                files={"files": f},
                data={"expiryHours": "1"},
                timeout=30
            )
        
        print(f"📋 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 Response: {result}")
            
            if result.get('files') and len(result['files']) > 0:
                file_info = result['files'][0]
                print(f"\n✅ Upload successful!")
                print(f"🔗 Link: {file_info.get('url')}")
                print(f"🗑️ Delete URL: {file_info.get('deleteUrl')}")
                print(f"⏰ Expires: {file_info.get('expires')}")
                print(f"📁 Filename: {file_info.get('name')}")
                print(f"📊 Size: {file_info.get('size')} bytes")
            else:
                print(f"❌ No file info in response")
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
    test_tempfile_upload()