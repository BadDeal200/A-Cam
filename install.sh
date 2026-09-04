#!/bin/bash
# install.sh - Setup script for Festival Video Receiver

echo "🎉 Festival Video Receiver - Installation"
echo "=========================================="

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it first."
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Installing..."
    sudo apt-get install -y python3-pip
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install flask flask-cors pyperclip

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    echo "⚠️ ngrok is not installed!"
    echo "📥 Download ngrok from: https://ngrok.com/download"
    echo "📖 After installation, authenticate with:"
    echo "   ngrok config add-authtoken YOUR_TOKEN"
else
    echo "✅ ngrok is installed"
fi

# Make the script executable
chmod +x festival-receiver.py

echo ""
echo "✅ Installation complete!"
echo "🚀 Run the tool with: ./festival-receiver.py"