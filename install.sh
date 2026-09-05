#!/bin/bash
# install.sh - Setup script for Parrot OS with Ngrok Direct Receiver

echo "🎁 Gift Video Receiver - Installation"
echo "======================================"

# Check if running on Parrot OS or Debian-based system
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "📋 Detected OS: $PRETTY_NAME"
fi

# Install using apt
echo ""
echo "📦 Installing Python packages using apt..."
sudo apt update
sudo apt install -y python3-flask python3-flask-cors python3-pip python3-venv python3-requests

# Create virtual environment
echo ""
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install required packages
echo ""
echo "📦 Installing Python packages with pip..."
pip install --upgrade pip
pip install flask flask-cors requests werkzeug

# Check ngrok
echo ""
if ! command -v ngrok &> /dev/null; then
    echo "⚠️ ngrok is not installed!"
    echo ""
    echo "📥 To install ngrok on Parrot OS:"
    echo "   cd /tmp"
    echo "   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip"
    echo "   unzip ngrok-v3-stable-linux-amd64.zip"
    echo "   sudo mv ngrok /usr/local/bin/"
    echo "   ngrok config add-authtoken YOUR_TOKEN"
    echo ""
else
    echo "✅ ngrok is installed"
fi

# Make scripts executable
chmod +x server.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "🌐 Direct Ngrok Server is ready!"
echo "   Received media files are saved locally and accessible live via Ngrok."
echo ""
echo "🚀 To run the server:"
echo "   source venv/bin/activate"
echo "   python3 server.py"
echo ""
echo "   Or simply: ./run.sh"