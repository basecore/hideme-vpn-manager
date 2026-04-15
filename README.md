# 🛡️ hide.me VPN Manager for Linux

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, sleek, and feature-rich Graphical User Interface (GUI) for the official `hide.me` Linux CLI client. 

While the official hide.me CLI is incredibly powerful, remembering and typing out long strings of flags for split-tunneling, ad-blocking, and custom DNS can be tedious. This tool wraps all that functionality into a beautiful, dark-mode desktop application built purely with Python's built-in `tkinter`.

✨ *Proudly generated and engineered with the help of **Gemini 3.1 Pro Thinking** to provide a superior, user-friendly desktop alternative to terminal-only VPN management on Linux.*

---

## 📸 Screenshots

<div align="center">
  <img src="gui1.png" alt="Main Interface & Network Settings" width="400"/>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="gui2.png" alt="Security Filters & Advanced Options" width="400"/>
</div>

*Left: The Main Dashboard showing real-time IP, Location, and Split-Tunneling Network Tab.*  
*Right: The Advanced Options and Security Filters (Ad-Blocker, Custom DNS, Configs).*

---

## ✨ Features

* 🎨 **Modern Brand Design:** Matches the official hide.me dark mode aesthetics (Deep Navy & Bright Turquoise).
* 🚀 **Zero-Setup Auto-Installer:** Checks if the hide.me CLI is installed upon startup. If not, it automatically downloads and installs it for you.
* 🔄 **Smart Updates:** Built-in version checker pings the GitHub API to notify you of CLI updates and installs them with one click.
* 🌍 **Visual Server Selection:** Easily pick your desired location using intuitive country flags (e.g., 🇩🇪, 🇫🇷, 🇺🇸) or hit the **Random Server Picker** to instantly connect to a random free server.
* 🔀 **Intelligent Split Tunneling (-s):** Automatically detects your local home subnet (e.g., `192.168.178.0/24`) so you can stay connected to your NAS, Home Assistant, and local printers while the VPN is active.
* 🛑 **Safe Close Warning:** If you accidentally close the app while connected, it prompts a safety warning to prevent you from suddenly browsing unprotected. Once confirmed, it safely disconnects and restores your routing tables.
* 🛡️ **1-Click Security Filters:** Toggle ad-blockers, malware protection, tracking protection, and forced SafeSearch directly from the UI.
* 📍 **Live IP & Geolocation:** Displays your current IP address and physical location (City, Country) in real-time.
* 🐧 **Linux OS Guard:** Prevents accidental crashes if the script is run on Windows or macOS by displaying a clean UI notification.

---

## 🛠️ Prerequisites

* A Linux-based Operating System (Ubuntu, Linux Mint, Debian, Arch, etc.)
* Python 3 installed
* Root/Sudo privileges (Required by the hide.me CLI to modify network routes and interfaces)

*(Note: The script uses the `requests` library for IP geolocation. If it's missing, the script will automatically install it via `pip` on its first run!)*

---

## 🚀 Installation & Usage

**1. Clone the repository:**
```bash
git clone https://github.com/basecore/hideme-vpn-manager.git
cd hideme-vpn-manager
```

**2. Run the application:**
Because the VPN needs to modify network interfaces and routing tables, the GUI must be started with `sudo`.
```bash
sudo python3 vpn_gui.py
```

**3. First Run:**
If you don't have the `hide.me` CLI installed yet, the GUI will prompt you and handle the entire installation process in the background. Simply follow the on-screen instructions!

---

## ⚙️ How It Works (The Tabs)

The GUI is divided into four easy-to-use tabs:

### 1. Network
Manage how your traffic flows. Enable **Split Tunneling** (the app auto-fills your subnet), toggle the **Kill-Switch**, enable **Port-Forwarding**, or force specific tunneling protocols (IPv4 / IPv6).

### 2. Filters
Hide.me offers powerful server-side filtering. Use this tab to block Ads, Malware, and Trackers before they even reach your computer. You can also force `hide.me` DNS servers to prevent DNS leaks.

### 3. Advanced
For power users. Load a custom `.yaml` configuration file, change the path to your Access Token, specify custom DNS servers (like Cloudflare's `1.1.1.1`), and manage startup update checks.

### 4. About
Quick access to the GitHub repository and issue tracker for reporting bugs or requesting new features.

---

## ⚠️ Disclaimer

This is an unofficial, open-source community project. It is not affiliated with, officially maintained, or endorsed by **eVenture Ltd.** or **hide.me**. 

All VPN connections, encryption, and routing are handled entirely by the official open-source [hide.me Linux CLI](https://github.com/eventure/hide.client.linux). This Python script merely serves as a graphical wrapper to construct and execute the CLI commands cleanly.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/basecore/hideme-vpn-manager/issues).

If you like this project, please consider giving it a ⭐!
