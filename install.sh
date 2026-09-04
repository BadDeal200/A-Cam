#!/bin/bash
# install.sh - Setup script

echo "🎁 Gift Video Receiver - Installation"
echo "======================================"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install flask flask-cors

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    echo ""
    echo "⚠️ ngrok is not installed!"
    echo "📥 To install ngrok in Termux:"
    echo "   curl -O https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.zip"
    echo "   unzip ngrok-v3-stable-linux-arm64.zip"
    echo "   mv ngrok /data/data/com.termux/files/usr/bin/"
    echo "   ngrok config add-authtoken YOUR_TOKEN"
else
    echo "✅ ngrok is installed"
fi

# Make scripts executable
chmod +x server.py

echo ""
echo "✅ Installation complete!"
echo "🚀 Run the server: python3 server.py"