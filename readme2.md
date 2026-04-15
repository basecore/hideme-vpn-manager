# hide.me VPN Manager GUI for Linux 🐧🔒

![Version](https://img.shields.io/badge/version-33.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An advanced, modern, and highly interactive Graphical User Interface (GUI) for the official [hide.me Linux CLI client](https://github.com/eventure/hide.client.linux). Built with Python and PyQt6, this tool maps all the powerful WireGuard-based command-line features into a sleek, user-friendly desktop experience.

> **Note:** This application is strictly designed for **Linux**. Windows and macOS are not supported, as hide.me already provides excellent native applications for those platforms.

---

## 📸 Screenshots

![hide.me Manager GUI](gui_new.png)

*(Upload a screenshot of the app and name it `gui_new.png` in the repository root to display it here).*

---

## ✨ Key Features

### 🛡️ Core VPN & Security
*   **Zero-Setup Auto-Installer:** Automatically detects if the hide.me CLI is missing and installs it securely.
*   **IP Leak Protection (Kill Switch):** Instantly blocks all internet traffic if the VPN connection drops.
*   **LAN Bypass:** Automatically detects your local subnet and allows access to local network devices (printers, NAS) while the VPN is active.
*   **Split Tunneling:** Exclude specific IPs or subnets from the VPN tunnel.

### 🎛️ SmartGuard & Content Filtering
Take full control over your DNS requests directly from the GUI:
*   Block **Ads & Trackers** network-wide.
*   Filter **Malware & Malicious Sites** (Phishing/Scams).
*   Block **Illegal Content** (Warez, Spyware, Copyrighted material).
*   Enforce **SafeSearch** on major search engines.

### 🗺️ Interactive Maps & Location Engine
*   **Live Node Map:** Interactive Leaflet-based map via WebEngine to visualize server locations.
*   **Best Location Finder:** Automated ping algorithm to find the server with the lowest latency.
*   **Favorites System:** Save and quickly connect to your most used locations.

### 💻 Desktop Integration & Customization
*   **Customizable Dashboard:** A 6-slot drag-and-drop style grid layout. Choose widgets like Live Traffic Monitor, IP Address, Mini Map, or Quick Connect.
*   **System Tray / Background Mode:** Minimize to the taskbar and receive native OS desktop notifications.
*   **Dark / Light Mode:** Fully themed UI that matches your desktop preferences.
*   **Safe Close Guard:** Prevents accidental VPN disconnections if you click the 'X' button while connected.

### 🕵️‍♂️ Advanced & Expert Modes
*   **Incognito Mode:** When enabled, automatically securely wipes all local connection logs, IPs, and debug data the moment you exit the app.
*   **Expert CLI Flags:** Custom DNS, Force DNS over VPN, Disable DNS-over-HTTPS (DoH), Custom Interface Names (`-i`), Listen Ports (`-l`), and DPD Timeouts (`--dpd`).
*   **Live Debug Console:** Monitor raw CLI outputs and background tasks in real-time.

---

## ⚙️ Prerequisites

*   **OS:** Linux (Ubuntu, Debian, Arch, Fedora, etc.)
*   **Python:** Version 3.8 or higher.
*   **Privileges:** `sudo` access is required (the hide.me CLI needs root privileges to configure WireGuard network interfaces and routing tables).

---

## 🚀 Installation & Usage

**1. Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/hideme2-vpn-manager.git
cd hideme2-vpn-manager
```

**2. Install Python Dependencies:**
*(Note: The script attempts to auto-install these on the first run, but manual installation is recommended).*
```bash
pip3 install PyQt6 requests PyQt6-WebEngine
```

**3. Run the Application:**
Because WireGuard routing requires system-level network modifications, you must launch the app with `sudo`:
```bash
sudo python3 hideme_gui.py
```

---

## 📂 Configuration & Logs

All configurations and logs are stored securely in `/etc/hide.me/`:
*   `settings.json` - App preferences (Dark mode, Incognito mode, Auto-start).
*   `dashboard.json` - Your custom widget layout.
*   `favorites.json` - Saved server locations.
*   `system_logs.json` - Connection history (Wiped automatically if *Incognito Mode* is active).

---

## ⚠️ Disclaimer

This is an **unofficial** GUI wrapper. It relies on the official open-source `hide.me` Linux CLI client created by eVenture Ltd. 
All VPN routing, encryption, and cryptographic key exchanges are securely handled by the official hide.me binaries, not by this Python script. This script only acts as a user-friendly controller.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/YOUR_USERNAME/hideme2-vpn-manager/issues).

**License:** MIT License
