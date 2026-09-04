#!/bin/bash
# install.sh - Setup script for Festival Video Receiver (Termux compatible)

echo "🎉 Festival Video Receiver - Installation"
echo "=========================================="

# Install Python dependencies (no pyperclip needed)
echo "📦 Installing Python dependencies..."
pip3 install flask flask-cors

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    echo "⚠️ ngrok is not installed!"
    echo ""
    echo "📥 To install ngrok in Termux:"
    echo "1. Visit: https://ngrok.com/download"
    echo "2. Download the ARM64 version for Linux"
    echo "3. Extract it: unzip ngrok-stable-linux-arm64.zip"
    echo "4. Move it: mv ngrok /data/data/com.termux/files/usr/bin/"
    echo "5. Authenticate: ngrok config add-authtoken YOUR_TOKEN"
else
    echo "✅ ngrok is installed"
fi

# Make the script executable
chmod +x festival-receiver.py

echo ""
echo "✅ Installation complete!"
echo "🚀 Run the tool with: ./festival-receiver.py"