#!/bin/bash
# install-curl.sh - Install curl for fallback upload method

echo "📦 Installing curl for fallback upload method..."
sudo apt update
sudo apt install -y curl

echo "✅ curl installed!"