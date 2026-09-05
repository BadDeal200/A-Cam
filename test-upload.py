#!/usr/bin/env python3
"""
Test FileGoat upload
"""

import requests
import os
import tempfile

def test_filegoat_upload():
    import uuid
    print("☁️ Testing FileGoat upload...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file from Gift Video Receiver with FileGoat")
        test_file = f.name
    
    try:
        print(f"📁 Test file: {test_file}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://filego.at",
            "Referer": "https://filego.at/",
        }
        
        with open(test_file, "rb") as f:
            response = requests.post(
                "https://filego.at/api/file/upload",
                files={"file": (os.path.basename(test_file), f)},
                headers=headers,
                timeout=30
            )
        
        print(f"📋 Step 1 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            file_ids = result.get("fileIds")
            print(f"📋 File IDs: {file_ids}")
            
            if file_ids:
                bucket_payload = {
                    "fileIds": file_ids,
                    "deleteTime": 1,
                    "extendOnView": False,
                    "clientId": str(uuid.uuid4())
                }
                bucket_headers = headers.copy()
                bucket_headers["Content-Type"] = "application/json"
                
                bucket_response = requests.post(
                    "https://filego.at/api/bucket",
                    json=bucket_payload,
                    headers=bucket_headers,
                    timeout=30
                )
                
                print(f"📋 Step 2 Response status: {bucket_response.status_code}")
                if bucket_response.status_code == 200:
                    bucket_result = bucket_response.json()
                    slug = bucket_result.get("slug")
                    if slug:
                        cloud_url = f"https://filego.at/bucket/{slug}"
                        print(f"\n✅ Upload successful!")
                        print(f"🔗 Link: {cloud_url}")
                        print(f"⏰ Expires: 1 day")
                    else:
                        print("❌ No slug in bucket response")
                else:
                    print(f"❌ Bucket creation failed: {bucket_response.text}")
            else:
                print(f"❌ No fileIds in upload response")
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