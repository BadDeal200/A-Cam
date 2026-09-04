#!/bin/bash
# run.sh - Quick launcher with virtual environment support

echo "🎁 Starting Gift Video Receiver Server..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "📦 Using virtual environment..."
    source venv/bin/activate
else
    echo "📦 Using system Python..."
fi

# Run the server
python3 server.py