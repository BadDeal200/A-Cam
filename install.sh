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
if ! command -v ngrok &> /dev/null && [ ! -f ./ngrok ] && [ ! -f ./ngrok.exe ]; then
    echo "⚠️ ngrok is not installed!"
    echo "🔍 Identifying device OS and CPU architecture..."

    # Detect OS
    OS_NAME="$(uname -s 2>/dev/null || echo 'Linux')"
    case "$OS_NAME" in
        Linux*)     TARGET_OS="linux" ;;
        Darwin*)    TARGET_OS="darwin" ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT*) TARGET_OS="windows" ;;
        FreeBSD*)   TARGET_OS="freebsd" ;;
        *)          TARGET_OS="linux" ;;
    esac

    # Detect Architecture
    ARCH_NAME="$(uname -m 2>/dev/null || echo 'x86_64')"
    case "$ARCH_NAME" in
        x86_64|amd64)        TARGET_ARCH="amd64" ;;
        aarch64|arm64|armv8*) TARGET_ARCH="arm64" ;;
        armv7*|armv6*|arm)   TARGET_ARCH="arm" ;;
        i386|i686|x86)       TARGET_ARCH="386" ;;
        *)                   TARGET_ARCH="amd64" ;;
    esac

    echo "📋 System Info -> OS: $TARGET_OS | CPU Arch: $TARGET_ARCH"

    EXT="tgz"
    if [ "$TARGET_OS" = "windows" ]; then
        EXT="zip"
    fi

    DOWNLOAD_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-${TARGET_OS}-${TARGET_ARCH}.${EXT}"
    TMP_DIR="$(mktemp -d 2>/dev/null || echo '/tmp')"
    ARCHIVE_FILE="${TMP_DIR}/ngrok-download.${EXT}"

    echo "📥 Automatically downloading ngrok server..."
    echo "   URL: $DOWNLOAD_URL"

    if command -v curl &> /dev/null; then
        curl -fsSL "$DOWNLOAD_URL" -o "$ARCHIVE_FILE"
    elif command -v wget &> /dev/null; then
        wget -q "$DOWNLOAD_URL" -O "$ARCHIVE_FILE"
    elif command -v python3 &> /dev/null; then
        python3 -c "import urllib.request; urllib.request.urlretrieve('$DOWNLOAD_URL', '$ARCHIVE_FILE')"
    fi

    if [ -f "$ARCHIVE_FILE" ]; then
        echo "📦 Extracting ngrok..."
        BIN_NAME="ngrok"
        if [ "$TARGET_OS" = "windows" ]; then
            BIN_NAME="ngrok.exe"
        fi

        if [ "$EXT" = "zip" ]; then
            if command -v unzip &> /dev/null; then
                unzip -o -q "$ARCHIVE_FILE" -d "$TMP_DIR"
            elif command -v python3 &> /dev/null; then
                python3 -c "import zipfile; zipfile.ZipFile('$ARCHIVE_FILE').extractall('$TMP_DIR')"
            fi
        else
            if command -v tar &> /dev/null; then
                tar -xzf "$ARCHIVE_FILE" -C "$TMP_DIR"
            elif command -v python3 &> /dev/null; then
                python3 -c "import tarfile; tarfile.open('$ARCHIVE_FILE').extractall('$TMP_DIR')"
            fi
        fi

        if [ -f "${TMP_DIR}/${BIN_NAME}" ]; then
            if [ -w /usr/local/bin ] || [ "$(id -u 2>/dev/null)" -eq 0 ]; then
                mv "${TMP_DIR}/${BIN_NAME}" /usr/local/bin/
                chmod +x "/usr/local/bin/${BIN_NAME}"
                echo "✅ Installed ngrok to /usr/local/bin/${BIN_NAME}"
            elif command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
                sudo mv "${TMP_DIR}/${BIN_NAME}" /usr/local/bin/
                sudo chmod +x "/usr/local/bin/${BIN_NAME}"
                echo "✅ Installed ngrok to /usr/local/bin/${BIN_NAME}"
            else
                mv "${TMP_DIR}/${BIN_NAME}" ./
                chmod +x "./${BIN_NAME}"
                echo "✅ Installed ngrok to project directory (./${BIN_NAME})"
            fi
        else
            echo "❌ Extraction failed or binary missing."
        fi
        rm -rf "$TMP_DIR"
    else
        echo "❌ Automatic ngrok download failed."
        echo "   Please download manually from https://ngrok.com/download"
    fi
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