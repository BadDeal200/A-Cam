#!/bin/bash
# install.sh - Setup script for Parrot OS

echo "🎁 Gift Video Receiver - Installation"
echo "======================================"

# Check if running on Parrot OS or Debian-based system
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "📋 Detected OS: $PRETTY_NAME"
fi

# ============================================
# Option 1: Install using apt (Recommended)
# ============================================
echo ""
echo "📦 Installing Python packages using apt..."
sudo apt update
sudo apt install -y python3-flask python3-flask-cors python3-pip

# Check if python3-venv is available (for virtual environment)
if ! dpkg -l | grep -q python3-venv; then
    echo "📦 Installing python3-venv..."
    sudo apt install -y python3-venv
fi

# ============================================
# Option 2: Create virtual environment (Alternative)
# ============================================
echo ""
echo "🔧 Setting up Python virtual environment (recommended for pip packages)..."
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install pyperclip in virtual environment if needed
pip install pyperclip

echo "✅ Virtual environment created at: ./venv"
echo "   To activate: source venv/bin/activate"

# ============================================
# Check ngrok
# ============================================
echo ""
if ! command -v ngrok &> /dev/null; then
    echo "⚠️ ngrok is not installed!"
    echo ""
    echo "📥 To install ngrok on Parrot OS (x86_64):"
    echo "   cd /tmp"
    echo "   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip"
    echo "   unzip ngrok-v3-stable-linux-amd64.zip"
    echo "   sudo mv ngrok /usr/local/bin/"
    echo "   ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    echo "   Or for ARM64 (Raspberry Pi, etc.):"
    echo "   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.zip"
else
    echo "✅ ngrok is installed"
fi

# ============================================
# Make scripts executable
# ============================================
chmod +x server.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 To run the server:"
echo "   Method 1 (using venv): source venv/bin/activate && python3 server.py"
echo "   Method 2 (using system): python3 server.py"
echo ""
echo "📝 If you get import errors, install missing packages:"
echo "   sudo apt install python3-<package_name>"
echo "   or use: pip install <package_name> (inside venv)"