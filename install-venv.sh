#!/bin/bash
# install-venv.sh - Install using virtual environment only

echo "🎁 Gift Video Receiver - Virtual Environment Setup"
echo "==================================================="

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv

# Activate and install packages
echo "📦 Installing packages in virtual environment..."
source venv/bin/activate
pip install --upgrade pip
pip install flask flask-cors pyperclip

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 To run the server:"
echo "   source venv/bin/activate"
echo "   python3 server.py"
echo ""
echo "   Or simply run: ./run.sh"