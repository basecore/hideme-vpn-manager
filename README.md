# 🛡️ hide.me VPN Manager GUI (Linux)

![hide.me VPN Manager GUI](gui_main_1.png)

A modern, feature-rich, and highly interactive graphical user interface (GUI) for the official **hide.me VPN Linux CLI**. Built with Python and PyQt6, this application seamlessly bridges the power of the terminal with a beautiful desktop experience. 

Designed specifically for Linux, it completely manages the CLI background processes, WireGuard network routing, and offers advanced options like split tunneling, kill switch, and live map tracking without ever touching the terminal.

## ✨ Features

* 📊 **Customizable Dashboard:** Build your own dashboard layout with widgets like Quick Connect, Live Traffic Monitor, IP Checker, and Favourite Locations.
* 🗺️ **Live Interactive Map:** Integrated Leaflet web-engine map that displays server locations and your current IP status.
* 🌓 **Dark & Light Mode:** Beautiful UI with native Qt Fusion styling for perfect visibility in any environment.
* ⚡ **Smart Server Switching:** Bulletproof `Deep Cleanup` function that automatically clears ghost WireGuard interfaces, IPv4, and IPv6 routes to prevent "file exists" errors during fast server switching.
* 🛡️ **Advanced Filters & StealthGuard:** Toggle CLI flags directly from the GUI (Ad-Blocker, No-Trackers, Kill Switch, Malware Blocking, LAN Bypass, and Custom Split-Tunneling).
* 🔧 **Expert Settings:** Change protocols (IPv4/IPv6), Force DNS, disable DoH, and define custom WireGuard listening ports & DPD timeouts.
* 📈 **Live Metrics:** Real-time download/upload traffic monitoring and built-in server ping testing.
* 🖥️ **System Integration:** System tray icon (minimize to taskbar) and native Linux desktop notifications.
* 🔄 **Auto-Updates:** Automatically checks and installs updates for the underlying `hide.me` CLI.

## 📋 Prerequisites

Since this GUI manages network interfaces and routing tables via the official CLI, it requires a Linux environment and `sudo` privileges.

* **OS:** Linux (Debian/Ubuntu-based recommended)
* **Python:** Python 3.8+
* **hide.me CLI:** Automatically installed by the app if missing.

*The app will attempt to auto-install missing Python packages (`python3-pyqt6`, `python3-pyqt6.qtwebengine`, `python3-requests`, `fonts-noto-color-emoji`) via `apt` on its first run.*

## 🚀 Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/basecore/hideme-vpn-manager.git
   cd hideme-vpn-manager
   ```

2. **Run the application:**
   Because the hide.me CLI requires root permissions to configure WireGuard (`wg`) interfaces and routing tables (`ip route`), the GUI must be executed with `sudo`:
   ```bash
   sudo python3 hideme_gui.py
   ```

## 🛠️ Troubleshooting

* **VPN hangs on "Connecting..."?** 
  Our V51 routing engine handles cleanups automatically. However, if your internet connection ever drops entirely due to a system crash while the VPN was active, simply open the app, go to **Settings -> Expert** and click the red **"⚠️ Emergency Network Reset (Fix Internet)"** button.
* **Map not loading?** 
  Make sure `PyQt6-WebEngine` is installed on your system.
* **Graphical glitches?**
  Ensure you are using the latest version of the script. We use Qt's native `Fusion` palette for maximum compatibility across different Linux desktop environments (GNOME, KDE, etc.).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/basecore/hideme-vpn-manager/issues) if you want to contribute.

## 📄 License & Disclaimer

This is an open-source project created to enhance the Linux user experience. It is an unofficial GUI wrapper and is **not** officially affiliated with, endorsed, or maintained by *hide.me VPN* or *eVenture Ltd.* 
