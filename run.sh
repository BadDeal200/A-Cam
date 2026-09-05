#!/bin/bash
# run.sh - Quick launcher

echo "🎁 Starting Gift Video Receiver Server with tempfile.org..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "📦 Using virtual environment..."
    source venv/bin/activate
fi

# Run the server
python3 server.py