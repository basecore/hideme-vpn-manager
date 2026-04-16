#!/usr/bin/env python3
# ==============================================================================
# hide.me VPN Manager GUI - Ultimate Interactive Edition (v51)
# ==============================================================================
__version__ = "51.0.0"
__date__ = "April 15, 2026"
__ai_model__ = "Perplexity / Gemini 3.1 Pro"

import os
import sys
import subprocess
import time
import random
import json
import logging
import shutil
import re
import requests

# --- Security Flags for QtWebEngine running as root (sudo) ---
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-web-security"

try: 
    import pwd
except ImportError: 
    pass

def open_os_url(url):
    try:
        user = os.environ.get('SUDO_USER')
        if user:
            subprocess.Popen(['sudo', '-u', user, 'xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Failed to open URL: {e}")

def auto_install_dependencies():
    missing = False
    try:
        import PyQt6
        import requests
    except ImportError:
        missing = True

    if missing:
        print("\n" + "="*70)
        print(" 🔄 DOWNLOADING MISSING PACKAGES (AUTO-INSTALLING) 🔄")
        print("="*70)
        if shutil.which("apt"):
            packages = ["python3-pyqt6", "python3-pyqt6.qtwebengine", "python3-requests", "fonts-noto-color-emoji"]
            try:
                subprocess.run(["apt-get", "update", "-qq"], check=True)
                subprocess.run(["apt-get", "install", "-y"] + packages, check=True)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except subprocess.CalledProcessError:
                sys.exit(1)
        else:
            sys.exit(1)

auto_install_dependencies()

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QGridLayout, QFrame, QCheckBox, QLineEdit, 
                             QComboBox, QSystemTrayIcon, QMenu, QRadioButton, 
                             QTabWidget, QMessageBox, QTableWidget, QTextEdit,
                             QTableWidgetItem, QHeaderView, QAbstractItemView, 
                             QInputDialog, QDialog, QDialogButtonBox, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QFont, QPalette

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    WEB_ENGINE_AVAILABLE = True

    class MapPage(QWebEnginePage):
        def __init__(self, parent, connect_callback):
            super().__init__(parent)
            self.connect_callback = connect_callback
        def acceptNavigationRequest(self, url, _type, isMainFrame):
            if url.scheme() == "hideme":
                self.connect_callback(url.host())
                return False
            return super().acceptNavigationRequest(url, _type, isMainFrame)
except ImportError:
    WEB_ENGINE_AVAILABLE = False

CONFIG_DIR = "/etc/hide.me"
LOG_FILE = os.path.join(CONFIG_DIR, "system_logs.json")
THEME_FILE = os.path.join(CONFIG_DIR, "theme.conf")
DASH_FILE = os.path.join(CONFIG_DIR, "dashboard.json")
FAV_FILE = os.path.join(CONFIG_DIR, "favorites.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

# 1. Erweiterte Free-Server-Liste mit Flaggen
SERVER_LIST = {
    "free-de": {"name": "🇩🇪 Frankfurt (DE)", "lat": 50.4779, "lon": 12.3713, "flag": "🇩🇪"},
    "free-fr": {"name": "🇫🇷 Paris (FR)", "lat": 48.8566, "lon": 2.3522, "flag": "🇫🇷"},
    "free-nl": {"name": "🇳🇱 Amsterdam (NL)", "lat": 52.3676, "lon": 4.9041, "flag": "🇳🇱"},
    "free-ch": {"name": "🇨🇭 Zurich (CH)", "lat": 47.1751, "lon": 8.4239, "flag": "🇨🇭"},
    "free-uk": {"name": "🇬🇧 London (UK)", "lat": 51.4543, "lon": -0.9781, "flag": "🇬🇧"},
    "free-us": {"name": "🇺🇸 Los Angeles (US)", "lat": 39.0997, "lon": -94.5786, "flag": "🇺🇸"},
    "free-fi": {"name": "🇫🇮 Helsinki (FI)", "lat": 60.1695, "lon": 24.9354, "flag": "🇫🇮"}
}

def get_local_subnet():
    try:
        route_out = subprocess.check_output(["ip", "route"]).decode()
        default_iface = next((l.split()[l.split().index("dev")+1] for l in route_out.splitlines() if l.startswith("default") and "dev" in l), None)
        if default_iface:
            return next((l.split()[0] for l in route_out.splitlines() if default_iface in l and "scope link" in l), "192.168.178.0/24")
    except: pass
    return "192.168.178.0/24"

def cleanup_zombie_network():
    try:
        subprocess.run(["sudo", "killall", "hide.me"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        time.sleep(0.3)
        subprocess.run(["sudo", "killall", "-9", "hide.me"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["sudo", "ip", "link", "delete", "vpn"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["sudo", "ip", "-4", "route", "flush", "table", "55555"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["sudo", "ip", "-6", "route", "flush", "table", "55555"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        try:
            out = subprocess.check_output(["ip", "-4", "rule", "show"]).decode()
            for line in out.splitlines():
                if "lookup 55555" in line:
                    subprocess.run(["sudo", "ip", "-4", "rule", "delete", "table", "55555"], stderr=subprocess.DEVNULL)
        except: pass
        try:
            out_v6 = subprocess.check_output(["ip", "-6", "rule", "show"]).decode()
            for line in out_v6.splitlines():
                if "lookup 55555" in line:
                    subprocess.run(["sudo", "ip", "-6", "rule", "delete", "table", "55555"], stderr=subprocess.DEVNULL)
        except: pass
    except: pass

class QtLogger(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)

class VpnProcessReaderThread(QThread):
    new_log = pyqtSignal(str)
    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True
    def run(self):
        while self.running and self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if line:
                self.new_log.emit(line.decode().strip())
            else:
                time.sleep(0.1)

class VpnMonitorThread(QThread):
    state_changed = pyqtSignal(bool)
    def run(self):
        last_state = None
        while True:
            try:
                is_running = subprocess.run(['pgrep', '-x', 'hide.me'], stdout=subprocess.DEVNULL).returncode == 0
                if is_running != last_state:
                    last_state = is_running
                    self.state_changed.emit(is_running)
            except: pass
            time.sleep(1.5)

class TrafficThread(QThread):
    traffic_updated = pyqtSignal(str, str, str, str)
    def __init__(self):
        super().__init__()
        self.last_rx = None
        self.last_tx = None
        self.session_base_rx = None
        self.session_base_tx = None
    def fmt_bytes(self, value, per_second=False):
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(max(0, value))
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024.0
            idx += 1
        suffix = "/s" if per_second else ""
        return f"{value:.2f} {units[idx]}{suffix}"
    def run(self):
        while True:
            try:
                curr_rx, curr_tx = 0, 0
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()[2:]
                vpn_active = any(l.split()[0].strip(':').startswith(('tun', 'wg', 'vpn', 'hide')) for l in lines)
                for line in lines:
                    parts = line.split()
                    iface = parts[0].strip(':')
                    if vpn_active:
                        if not iface.startswith(('tun', 'wg', 'vpn', 'hide')): continue
                    else:
                        if not iface.startswith(('en', 'eth', 'wl', 'wlan')): continue
                    curr_rx += int(parts[1])
                    curr_tx += int(parts[9])
                
                rx_speed = 0 if self.last_rx is None else curr_rx - self.last_rx
                tx_speed = 0 if self.last_tx is None else curr_tx - self.last_tx
                self.last_rx, self.last_tx = curr_rx, curr_tx

                if vpn_active and self.session_base_rx is None:
                    self.session_base_rx = curr_rx
                    self.session_base_tx = curr_tx
                elif not vpn_active:
                    self.session_base_rx = None
                    self.session_base_tx = None

                total_rx = 0
                total_tx = 0
                if vpn_active and self.session_base_rx is not None:
                    total_rx = curr_rx - self.session_base_rx
                    total_tx = curr_tx - self.session_base_tx

                self.traffic_updated.emit(
                    self.fmt_bytes(rx_speed, True),
                    self.fmt_bytes(tx_speed, True),
                    self.fmt_bytes(total_rx, False),
                    self.fmt_bytes(total_tx, False)
                )
            except: pass
            time.sleep(1)

class IpFetcherThread(QThread):
    ip_fetched = pyqtSignal(str, str, str, str, str, bool) 
    def __init__(self, is_connected):
        super().__init__()
        self.is_connected = is_connected

    def fetch_json(self, url):
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                return r.json()
        except: pass
        return {}

    def run(self):
        time.sleep(2.5)
        loc = self.fetch_json("https://ipinfo.io/json")
        ipv4 = self.fetch_json("https://api4.ipify.org?format=json").get("ip", "Not available")
        ipv6 = self.fetch_json("https://api6.ipify.org?format=json").get("ip", "Not available")

        city = loc.get("city", "Unknown")
        country = loc.get("country", "")
        coords = loc.get("loc", "")

        self.ip_fetched.emit(ipv4, ipv6, city, country, coords, self.is_connected)

class PingThread(QThread):
    ping_result = pyqtSignal(str)
    def __init__(self, server):
        super().__init__()
        self.server = server
    def run(self):
        try:
            out = subprocess.check_output(["ping", "-c", "3", "-W", "1", f"{self.server}.hideservers.net"], stderr=subprocess.STDOUT).decode()
            match = re.search(r'min/avg/max/mdev = [\d\.]+/(.*?)/', out)
            if match:
                self.ping_result.emit(f"{int(float(match.group(1)))} ms")
                return
        except: pass
        self.ping_result.emit("Failed")

class PingAllServersThread(QThread):
    ping_updated = pyqtSignal(str, str)
    def run(self):
        for code in SERVER_LIST.keys():
            try:
                out = subprocess.check_output(["ping", "-c", "1", "-W", "1", f"{code}.hideservers.net"], stderr=subprocess.STDOUT).decode()
                match = re.search(r'time=([\d\.]+) ms', out)
                if match:
                    self.ping_updated.emit(code, f"{int(float(match.group(1)))} ms")
            except:
                pass

class BestLocationFinderThread(QThread):
    best_found = pyqtSignal(str, float)
    def run(self):
        best_server = "free-de"
        lowest_ping = float('inf')
        for code in SERVER_LIST.keys():
            try:
                out = subprocess.check_output(["ping", "-c", "1", "-W", "1", f"{code}.hideservers.net"], stderr=subprocess.STDOUT).decode()
                match = re.search(r'time=([\d\.]+) ms', out)
                if match:
                    ping_val = float(match.group(1))
                    if ping_val < lowest_ping:
                        lowest_ping = ping_val
                        best_server = code
            except: pass
        self.best_found.emit(best_server, lowest_ping)

class ServerListFetcherThread(QThread):
    list_fetched = pyqtSignal(dict)
    def run(self):
        try:
            out = subprocess.check_output(["hide.me", "list"], stderr=subprocess.DEVNULL, timeout=5).decode()
            new_servers = {}
            for line in out.splitlines():
                if "|" in line and "Name" not in line and "---" not in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        code = parts[1].strip()
                        new_servers[code] = {"name": name, "lat": 40.0, "lon": 10.0}
            if new_servers:
                self.list_fetched.emit(new_servers)
        except Exception as e:
            pass

class CliAutoUpdateThread(QThread):
    result = pyqtSignal(str)
    def run(self):
        try:
            subprocess.run("curl -sL https://hide.me/install.sh | bash", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.result.emit("CLI updated successfully in background.")
        except Exception as e:
            self.result.emit(f"CLI background update failed: {e}")

class CardWidget(QFrame):
    def __init__(self, title="", is_square=False):
        super().__init__()
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(15, 15, 15, 15)
        if is_square:
            self.setFixedSize(270, 270)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if title:
            title_lbl = QLabel(title)
            title_lbl.setObjectName("CardTitle")
            self.layout.addWidget(title_lbl)

class DashboardEditDialog(QDialog):
    def __init__(self, current_layout, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Dashboard Layout")
        self.setFixedSize(400, 550)
        self.layout_selections = []
        options = ["Quick Connect", "My IP Address", "My Account", "Live Traffic Monitor", 
                   "Favourite Locations", "Startpage", "Mini Map", "Empty"]
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        desc_lbl = QLabel("Select widgets for your dashboard grid\n(3 Top, 3 Bottom):")
        desc_lbl.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        desc_lbl.setWordWrap(True)
        main_layout.addWidget(desc_lbl)
        for i in range(6):
            cb = QComboBox()
            cb.addItems(options)
            cb.setFixedHeight(32)
            cb.setStyleSheet("padding: 4px; font-size: 13px;")
            if i < len(current_layout) and current_layout[i] in options:
                cb.setCurrentText(current_layout[i])
            self.layout_selections.append(cb)
            lbl = QLabel(f"Slot {i+1}:")
            lbl.setStyleSheet("color: #334155;" if parent and parent.current_theme == "light" else "color: #CBD5E1;")
            main_layout.addWidget(lbl)
            main_layout.addWidget(cb)
        main_layout.addStretch()
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

    def get_layout(self):
        return [cb.currentText() for cb in self.layout_selections]

class HideMeOfficialUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("hide.me VPN Manager")
        self.resize(1150, 750)
        
        self.is_connected = False
        self._last_state = None
        self.current_connected_server = None
        self.conn_start_time = 0
        self.current_features_str = "-"
        self.last_connected_combo_text = None
        self.live_map_lat = None
        self.live_map_lon = None
        self.vpn_subprocess = None
        self.reader_thread = None
        self._active_ip_threads = []
        
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        self.current_theme = self.load_theme()
        self.favorites = self.load_favorites()
        self.dash_layout_config = self.load_dash_config()
        self.log_entries = self.load_logs()
        self.app_settings = self.load_app_settings()

# --- NEU: Bekannte, dynamische Servernamen laden ---
        known_names = self.app_settings.get("known_server_names", {})
        for code, name in known_names.items():
            if code in SERVER_LIST:
                SERVER_LIST[code]["name"] = name
        # ---------------------------------------------------
        
        self.init_logger()
        self.log_debug("Application initializing...")
        
        cleanup_zombie_network()
        self.check_and_install_cli()
        
        self.init_ui()
        self.apply_styles()
        self.setup_tray()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.dashboard_ping_timer = QTimer(self)
        self.dashboard_ping_timer.timeout.connect(self.update_dashboard_ping)
        
        self.monitor_thread = VpnMonitorThread()
        self.monitor_thread.state_changed.connect(self.update_ui_state)
        self.monitor_thread.start()
        
        self.traffic_thread = TrafficThread()
        self.traffic_thread.traffic_updated.connect(self.update_traffic)
        self.traffic_thread.start()
        
        QTimer.singleShot(2000, self.run_auto_update_if_enabled)
        self.fetch_ip(False)
        self.update_account_labels()
        
        self.fetch_servers_background()
        self.start_ping_all()

        if self.app_settings.get("auto_connect", False):
            QTimer.singleShot(1000, lambda: self.connect_vpn(None))

    def init_logger(self):
        self.logger = logging.getLogger("hide_me_gui")
        self.logger.setLevel(logging.DEBUG)
        self.qt_handler = QtLogger(self.append_debug_log)
        self.qt_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(self.qt_handler)

    def log_debug(self, msg, level=logging.INFO):
        if level == logging.ERROR: self.logger.error(msg)
        elif level == logging.WARNING: self.logger.warning(msg)
        else: self.logger.info(msg)

    def append_debug_log(self, msg):
        if hasattr(self, 'txt_debug'): 
            self.txt_debug.append(msg)
            
    def fetch_servers_background(self):
        self.server_fetcher = ServerListFetcherThread()
        self.server_fetcher.list_fetched.connect(self.on_servers_fetched)
        self.server_fetcher.start()

    # 2. Emoji-Preservation: Flaggen-Rettung beim Neuladen der CLI-Liste
    def on_servers_fetched(self, new_servers):
        global SERVER_LIST
        known = self.app_settings.get("known_server_names", {})
        
        for code, data in new_servers.items():
            if code in SERVER_LIST:
                data['lat'] = SERVER_LIST[code]['lat']
                data['lon'] = SERVER_LIST[code]['lon']
                saved_flag = SERVER_LIST[code].get("flag", "")
                if saved_flag:
                    data['flag'] = saved_flag
                    if not data['name'].startswith(saved_flag):
                        data['name'] = f"{saved_flag} {data['name']}"
                
                # Namen für den nächsten Neustart merken
                known[code] = data['name']
                        
        if new_servers:
            SERVER_LIST = new_servers
            # Gesammelte Namen in die Datei schreiben
            self.app_settings["known_server_names"] = known
            self.save_app_settings()
            
            self.log_debug(f"Loaded {len(SERVER_LIST)} servers dynamically from CLI.")
            self.update_map_html(self.current_connected_server)
            self.update_mini_map()
            self.refresh_server_dropdowns()
            if hasattr(self, 'card_fav'):
                self.render_favorites()

    def start_ping_all(self):
        self.ping_all_thread = PingAllServersThread()
        self.ping_all_thread.ping_updated.connect(self.on_ping_updated)
        self.ping_all_thread.start()

    def on_ping_updated(self, code, ping_str):
        if code in SERVER_LIST:
            SERVER_LIST[code]["ping"] = ping_str
            self.refresh_server_dropdowns()

    # 3. Dynamische Dropdown-Aktualisierung mit Erhalt der Auswahl
    def refresh_server_dropdowns(self):
        opts = ["⚡ Best Location", "🎲 Random Location"]
        for k, v in SERVER_LIST.items():
            ping_text = f"  ({v['ping']})" if "ping" in v else ""
            opts.append(f"{v['name']}{ping_text}")
            
        saved_loc = self.app_settings.get("selected_location", "⚡ Best Location")
        
        active_opt = saved_loc
        for opt in opts:
            if opt.startswith(saved_loc) or saved_loc.startswith(opt.split("  (")[0]):
                active_opt = opt
                break
                
        if hasattr(self, 'dash_combo_loc'):
            self.dash_combo_loc.blockSignals(True)
            self.dash_combo_loc.clear()
            self.dash_combo_loc.addItems(opts)
            self.dash_combo_loc.setCurrentText(active_opt)
            self.dash_combo_loc.blockSignals(False)
            
        if hasattr(self, 'combo_loc'):
            self.combo_loc.blockSignals(True)
            self.combo_loc.clear()
            self.combo_loc.addItems(opts)
            self.combo_loc.setCurrentText(active_opt)
            self.combo_loc.blockSignals(False)

    def update_account_labels(self):
        is_paid = self.app_settings.get("is_paid", False)
        plan_text = "Premium Plan" if is_paid else "Free Plan"
        if hasattr(self, "lbl_sidebar_acc"):
            self.lbl_sidebar_acc.setText(f"Your Account\n{plan_text}")
        if hasattr(self, "lbl_dash_account"):
            exp_text = "Expires: Unknown" if is_paid else "Never (Free)"
            self.lbl_dash_account.setText(f"Current Plan\n{plan_text} / CLI\n\nPlan Expiration\n{exp_text}\n\nEnvironment\n{sys.platform}")

    def update_dashboard_ping(self):
        if not self.is_connected or not self.current_connected_server or not hasattr(self, "lbl_pingdash"):
            return
        self.dash_pinger = PingThread(self.current_connected_server)
        self.dash_pinger.ping_result.connect(lambda res: self.lbl_pingdash.setText(f"Ping: {res}"))
        self.dash_pinger.start()

    def check_and_install_cli(self):
        try:
            if subprocess.run(['which', 'hide.me'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                subprocess.run("curl -sL https://hide.me/install.sh | bash", shell=True, check=True)
        except Exception as e: pass

    def run_auto_update_if_enabled(self):
        if hasattr(self, 'chk_autoupdate') and self.chk_autoupdate.isChecked():
            if hasattr(self, 'auto_upd_thread') and self.auto_upd_thread.isRunning(): return
            self.auto_upd_thread = CliAutoUpdateThread()
            self.auto_upd_thread.result.connect(self.log_debug)
            self.auto_upd_thread.start()

    def load_app_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: pass
        return {"debug_mode": False, "incognito_mode": False}

    def save_app_settings(self):
        with open(SETTINGS_FILE, "w") as f: json.dump(self.app_settings, f)

    def save_selected_location(self, text):
        base_name = text.split("  (")[0] if "  (" in text else text
        self.app_settings["selected_location"] = base_name
        self.save_app_settings()
        
        if hasattr(self, 'dash_combo_loc') and self.dash_combo_loc.currentText() != text:
            self.dash_combo_loc.blockSignals(True)
            self.dash_combo_loc.setCurrentText(text)
            self.dash_combo_loc.blockSignals(False)
        if hasattr(self, 'combo_loc') and self.combo_loc.currentText() != text:
            self.combo_loc.blockSignals(True)
            self.combo_loc.setCurrentText(text)
            self.combo_loc.blockSignals(False)

    def load_theme(self):
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, "r") as f: return f.read().strip()
        return "light"

    def load_dash_config(self):
        default = ["Quick Connect", "My IP Address", "My Account", "Live Traffic Monitor", "Favourite Locations", "Mini Map"]
        if os.path.exists(DASH_FILE):
            try:
                with open(DASH_FILE, "r") as f: return json.load(f)
            except: pass
        return default

    def save_dash_config(self):
        with open(DASH_FILE, "w") as f: json.dump(self.dash_layout_config, f)

    def load_favorites(self):
        if os.path.exists(FAV_FILE):
            try:
                with open(FAV_FILE, "r") as f: return json.load(f)
            except: pass
        return []

    def save_favorites(self):
        with open(FAV_FILE, "w") as f: json.dump(self.favorites, f)

    def load_logs(self):
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f: return json.load(f)
            except: pass
        return []

    def save_logs(self):
        if getattr(self, 'is_shutting_down', False):
            return
        with open(LOG_FILE, "w") as f: 
            json.dump(self.log_entries[-50:], f)

    def add_log_entry(self, state, ip, location, features="-"):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {"time": ts, "state": state, "ip": ip, "loc": location, "features": features}
        self.log_entries.append(entry)
        self.save_logs()
        self.refresh_log_table()

    def send_os_notification(self, title, message):
        if not hasattr(self, 'chk_notif') or not self.chk_notif.isChecked(): return
        try:
            user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
            uid = pwd.getpwnam(user).pw_uid
            cmd = f"sudo -u {user} DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus notify-send '{title}' '{message}' -i network-vpn"
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(45)
        top_layout = QHBoxLayout(top_bar)
        
        top_layout.addWidget(QLabel("hide.me VPN", objectName="LogoText"))
        top_layout.addStretch()
        
        self.btn_theme = QPushButton("🌙" if self.current_theme == "light" else "☀️")
        self.btn_theme.setObjectName("TopIconBtn")
        self.btn_theme.setToolTip("Toggle Light/Dark Theme")
        self.btn_theme.clicked.connect(self.toggle_theme)
        
        btn_bug = QPushButton("🐛")
        btn_bug.setObjectName("TopIconBtn")
        btn_bug.setToolTip("Report a bug on GitHub")
        btn_bug.clicked.connect(lambda: open_os_url("https://github.com/basecore/hideme-vpn-manager/issues"))
        
        top_layout.addWidget(self.btn_theme)
        top_layout.addWidget(btn_bug)
        main_layout.addWidget(top_bar)

        self.status_banner = QLabel("⚠️ UNPROTECTED - VPN is NOT active! Your traffic is exposed.")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setStyleSheet("background-color: #FF4C4C; color: white; font-weight: bold; font-size: 14px; padding: 6px;")
        main_layout.addWidget(self.status_banner)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(0)
        main_layout.addLayout(body_layout)

        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 15, 0, 15); sidebar_layout.setSpacing(5)
        
        self.nav_btns = {}
        menu_items = ["Dashboard", "Locations", "Map", "Settings", "System", "Logs", "Info", "Debug Console"]
        for item in menu_items:
            btn = QPushButton(f"  {item}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=item: self.switch_page(i))
            self.nav_btns[item] = btn
            sidebar_layout.addWidget(btn)
            
        self.nav_btns["Dashboard"].setChecked(True)
        self.nav_btns["Debug Console"].setVisible(self.app_settings.get("debug_mode", False))
        
        sidebar_layout.addStretch()
        self.lbl_sidebar_acc = QLabel("Your Account\nFree Plan")
        self.lbl_sidebar_acc.setStyleSheet("color: white; padding-left: 20px; font-weight: bold;")
        sidebar_layout.addWidget(self.lbl_sidebar_acc)
        body_layout.addWidget(sidebar)

        self.stacked = QStackedWidget()
        self.stacked.setObjectName("MainContent")
        body_layout.addWidget(self.stacked)
        
        self.setup_dashboard()
        self.setup_locations()
        self.setup_map()
        self.setup_settings()
        self.setup_system()
        self.setup_logs()
        self.setup_info()
        self.setup_debug()

    def edit_dashboard(self):
        dlg = DashboardEditDialog(self.dash_layout_config, self)
        if dlg.exec():
            self.dash_layout_config = dlg.get_layout()
            self.save_dash_config()
            self.build_dashboard_grid()

    def build_dashboard_grid(self):
        while self.dash_grid.count():
            item = self.dash_grid.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
            
        for i, name in enumerate(self.dash_layout_config):
            row = i // 3
            col = i % 3
            widget = self.create_widget_by_name(name)
            self.dash_grid.addWidget(widget, row, col)

    def create_widget_by_name(self, name):
        if name == "Quick Connect":
            c = CardWidget("Quick connect", is_square=True)
            self.dash_combo_loc = QComboBox()
            opts = ["⚡ Best Location", "🎲 Random Location"] + [v["name"] for v in SERVER_LIST.values()]
            self.dash_combo_loc.addItems(opts)
            self.dash_combo_loc.setFixedHeight(35)
            saved_loc = self.app_settings.get("selected_location", "⚡ Best Location")
            if saved_loc in opts:
                self.dash_combo_loc.setCurrentText(saved_loc)
            self.dash_combo_loc.currentTextChanged.connect(self.save_selected_location)
            self.btn_connect = QPushButton("  ⏻   Enable VPN")
            self.btn_connect.setObjectName("ConnectBtn")
            self.btn_connect.setFixedHeight(50)
            self.btn_connect.clicked.connect(lambda: self.connect_vpn(None, source_combo=self.dash_combo_loc))
            c.layout.addWidget(self.dash_combo_loc)
            c.layout.addSpacing(10)
            c.layout.addWidget(self.btn_connect)
            c.layout.addStretch()
            return c
            
        elif name == "My IP Address":
            c = CardWidget("My IP Address", is_square=True)
            self.lbl_ip4 = QLabel("IPv4\nLoading...\n\nLocation\n-")
            self.lbl_ip6 = QLabel("IPv6\nLoading...")
            c.layout.addWidget(self.lbl_ip4)
            c.layout.addWidget(self.lbl_ip6)
            c.layout.addStretch()
            return c
            
        elif name == "My Account":
            c = CardWidget("My account", is_square=True)
            plan_type = "Premium (Paid)" if self.app_settings.get("is_paid", False) else "Free Plan"
            exp_text = "Expires: Unknown" if self.app_settings.get("is_paid", False) else "Never (Free)"
            self.lbl_dash_account = QLabel(f"Current Plan\n{plan_type} / CLI\n\nPlan Expiration\n{exp_text}\n\nEnvironment\n{sys.platform}")
            c.layout.addWidget(self.lbl_dash_account)
            c.layout.addStretch()
            return c
            
        elif name == "Live Traffic Monitor":
            c = CardWidget("Live Traffic Monitor", is_square=True)
            self.lbl_rx = QLabel("↓ 0.00 KB/s")
            self.lbl_tx = QLabel("↑ 0.00 KB/s")
            self.lbl_session = QLabel("Session: ↓ 0.00 MB | ↑ 0.00 MB")
            self.lbl_pingdash = QLabel("Ping: - ms")
            
            ts = "font-family: monospace; font-size: 16px; font-weight: bold; margin-top: 5px;"
            self.lbl_rx.setStyleSheet(ts + "color: #2BAEE0;")
            self.lbl_tx.setStyleSheet(ts + "color: #FF4C4C;")
            self.lbl_session.setStyleSheet("color: #64748B; font-weight: 600; margin-top: 6px;")
            self.lbl_pingdash.setStyleSheet("color: #fbbf24; font-weight: bold; margin-top: 4px;")
            
            c.layout.addWidget(QLabel("Download", objectName="CardTitle"))
            c.layout.addWidget(self.lbl_rx)
            c.layout.addWidget(QLabel("Upload", objectName="CardTitle"))
            c.layout.addWidget(self.lbl_tx)
            c.layout.addWidget(self.lbl_session)
            c.layout.addWidget(self.lbl_pingdash)
            c.layout.addStretch()
            return c
            
        elif name == "Favourite Locations":
            self.card_fav = CardWidget("Favourite Locations", is_square=True)
            self.render_favorites()
            return self.card_fav
            
        elif name == "Mini Map":
            c = CardWidget("Location Map", is_square=True)
            if WEB_ENGINE_AVAILABLE:
                self.mini_map_view = QWebEngineView()
                self.mini_map_view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                self.mini_map_view.setPage(MapPage(self.mini_map_view, self.connect_vpn))
                c.layout.addWidget(self.mini_map_view)
                self.update_mini_map()
            else:
                c.layout.addWidget(QLabel("Map Engine missing."))
            return c
            
        elif name == "Startpage":
            c = CardWidget("Startpage", is_square=True)
            c.layout.addWidget(QLabel("Privacy Search\nFollow us on Github"))
            btn_git = QPushButton("GitHub")
            btn_git.clicked.connect(lambda: open_os_url("https://github.com/basecore/hideme-vpn-manager/tree/main"))
            c.layout.addWidget(btn_git)
            c.layout.addStretch()
            return c
            
        else:
            return CardWidget("Empty Slot", is_square=True)

    def render_favorites(self):
        for i in reversed(range(self.card_fav.layout.count())):
            w = self.card_fav.layout.itemAt(i).widget()
            if w and w.objectName() != "CardTitle": w.deleteLater()
            
        for code in self.favorites:
            if code in SERVER_LIST:
                h = QHBoxLayout()
                b = QPushButton(SERVER_LIST[code]["name"])
                b.clicked.connect(lambda ch, c=code: self.connect_vpn(c))
                bx = QPushButton("X"); bx.setFixedWidth(30)
                bx.clicked.connect(lambda ch, c=code: self.remove_favorite(c))
                h.addWidget(b); h.addWidget(bx)
                w = QWidget(); w.setLayout(h)
                self.card_fav.layout.addWidget(w)
                
        if len(self.favorites) < 3:
            btn_add = QPushButton("+\nAdd favourite location")
            btn_add.clicked.connect(self.add_favorite)
            self.card_fav.layout.addWidget(btn_add)
            
        self.card_fav.layout.addStretch()

    def add_favorite(self):
        options = [f"{v['name']} ({k})" for k, v in SERVER_LIST.items() if k not in self.favorites]
        if not options: return
        item, ok = QInputDialog.getItem(self, "Add Favorite", "Select Server:", options, 0, False)
        if ok and item:
            code = item.split("(")[-1].strip(")")
            self.favorites.append(code)
            self.save_favorites()
            self.render_favorites()

    def remove_favorite(self, code):
        if code in self.favorites:
            self.favorites.remove(code)
            self.save_favorites()
            self.render_favorites()

    def setup_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Dashboard", objectName="PageHeader"))
        header_layout.addStretch()
        btn_edit = QPushButton("📝 Edit Mode")
        btn_edit.setObjectName("PageActionBtn")
        btn_edit.setToolTip("Customize the widgets shown on your Dashboard")
        btn_edit.clicked.connect(self.edit_dashboard)
        header_layout.addWidget(btn_edit)
        layout.addLayout(header_layout)

        grid_container = QWidget()
        self.dash_grid = QGridLayout(grid_container)
        self.dash_grid.setSpacing(15)
        self.build_dashboard_grid()
        
        layout.addWidget(grid_container, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.stacked.addWidget(page)

    def setup_locations(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Locations", objectName="PageHeader"))
        
        card = CardWidget(is_square=False)
        lbl = QLabel("Filter and select server:"); lbl.setObjectName("CardTitle")
        card.layout.addWidget(lbl)
        
        self.combo_loc = QComboBox()
        opts = ["⚡ Best Location", "🎲 Random Location"] + [v["name"] for v in SERVER_LIST.values()]
        self.combo_loc.addItems(opts)
        self.combo_loc.setFixedHeight(40)
        saved_loc = self.app_settings.get("selected_location", "⚡ Best Location")
        if saved_loc in opts:
            self.combo_loc.setCurrentText(saved_loc)
        self.combo_loc.currentTextChanged.connect(self.save_selected_location)       
        btn_ping = QPushButton("Test Ping")
        btn_ping.setFixedHeight(40)
        btn_ping.clicked.connect(self.run_ping)
        self.lbl_ping_res = QLabel("- ms")
        self.lbl_ping_res.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 14px;")
        
        h_box = QHBoxLayout()
        h_box.addWidget(btn_ping); h_box.addWidget(self.lbl_ping_res); h_box.addStretch()
        
        card.layout.addWidget(self.combo_loc)
        card.layout.addLayout(h_box)
        card.layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        self.stacked.addWidget(page)

    def setup_map(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if WEB_ENGINE_AVAILABLE:
            self.map_view = QWebEngineView()
            self.map_view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.map_view.setPage(MapPage(self.map_view, self.connect_vpn))
            layout.addWidget(self.map_view)
            self.update_map_html()
        else:
            lbl = QLabel("Map Engine unavailable.\nPlease install PyQt6-WebEngine.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            
        self.stacked.addWidget(page)

    def update_map_html(self, focus_code=None):
        if not WEB_ENGINE_AVAILABLE: return
        is_dark = (self.current_theme == "dark")
        bg_color = "#0D1623" if is_dark else "#F3F5F7"
        popup_bg = "#132233" if is_dark else "#FFFFFF"
        popup_text = "white" if is_dark else "#334155"
        border = "#1C2E42" if is_dark else "#CBD5E1"
        tile_layer = "dark_all" if is_dark else "light_all"
        markers_js = ""
        center_lat, center_lon, zoom = 40, -10, 3
        
        if not self.is_connected and self.live_map_lat and self.live_map_lon:
            center_lat, center_lon, zoom = self.live_map_lat, self.live_map_lon, 4
            markers_js += f"L.circleMarker([{self.live_map_lat}, {self.live_map_lon}], {{radius: 8, fillColor: '#FF4C4C', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map).bindPopup(\"<b style='color:#FF4C4C;'>Your Unprotected Location</b>\");"
        
        for code, data in SERVER_LIST.items():
            name = data['name'].split(" ")[1] if " " in data['name'] else data['name']
            color = "green" if code == focus_code and self.is_connected else "#2BAEE0"
            lat = data['lat']
            lon = data['lon']
            
            if code == focus_code and self.is_connected:
                if self.live_map_lat and self.live_map_lon:
                    lat = self.live_map_lat
                    lon = self.live_map_lon
                center_lat, center_lon, zoom = lat, lon, 5

            markers_js += f"""
            var m = L.circleMarker([{lat}, {lon}], {{radius: 8, fillColor: '{color}', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map);
            m.bindPopup("<b style='color:{color};'>{name}</b><br><br><a href='hideme://{code}' style='display:block; text-align:center; padding:5px; background:#2BAEE0; color:white; text-decoration:none; border-radius:4px;'>Connect</a>");
            """

        html = f"""<!DOCTYPE html><html><head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
        <style>body,html,#map{{height:100%;margin:0;padding:0;background-color:{bg_color};}} .leaflet-popup-content-wrapper{{background:{popup_bg};color:{popup_text};border:1px solid {border};}} .leaflet-popup-tip{{background:{popup_bg};border:1px solid {border};}}</style></head>
        <body><div id="map"></div><script>
        var map=L.map('map',{{zoomControl:true}}).setView([{center_lat}, {center_lon}], {zoom});
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/{tile_layer}/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'&copy; OpenStreetMap'}}).addTo(map);
        {markers_js}
        setTimeout(function(){{map.invalidateSize();}},500);</script></body></html>"""
        if hasattr(self, 'map_view'): self.map_view.setHtml(html)

    def update_mini_map(self):
        if not WEB_ENGINE_AVAILABLE or not hasattr(self, 'mini_map_view'): return
        is_dark = (self.current_theme == "dark")
        bg_color = "#132233" if is_dark else "white"
        tile_layer = "dark_all" if is_dark else "light_all"
        
        center_lat, center_lon, zoom = 40, -10, 1
        markers_js = ""
        
        if self.is_connected and self.current_connected_server in SERVER_LIST:
            d = SERVER_LIST[self.current_connected_server]
            lat = self.live_map_lat if self.live_map_lat else d['lat']
            lon = self.live_map_lon if self.live_map_lon else d['lon']
            
            center_lat, center_lon, zoom = lat, lon, 3
            markers_js = f"L.circleMarker([{lat}, {lon}], {{radius: 6, fillColor: 'green', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map);"
        elif not self.is_connected and self.live_map_lat and self.live_map_lon:
            center_lat, center_lon, zoom = self.live_map_lat, self.live_map_lon, 3
            markers_js = f"L.circleMarker([{self.live_map_lat}, {self.live_map_lon}], {{radius: 6, fillColor: '#FF4C4C', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map);"

        html = f"""<!DOCTYPE html><html><head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
        <style>body,html,#map{{height:100%;margin:0;padding:0;background-color:{bg_color};}}</style></head>
        <body><div id="map"></div><script>
        var map=L.map('map',{{zoomControl:false, dragging:false, scrollWheelZoom:false}}).setView([{center_lat}, {center_lon}], {zoom});
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/{tile_layer}/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        {markers_js}
        setTimeout(function(){{map.invalidateSize();}},500);</script></body></html>"""
        self.mini_map_view.setHtml(html)

    def setup_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Settings", objectName="PageHeader"))
        
        tabs = QTabWidget()
        
        # --- NEW ACCOUNT TAB ---
        t_acc = QWidget(); l_acc = QVBoxLayout(t_acc)
        self.r_free = QRadioButton("Free Plan (Default)"); self.r_paid = QRadioButton("Premium / Paid Account")
        is_paid = self.app_settings.get("is_paid", False)
        if is_paid: self.r_paid.setChecked(True)
        else: self.r_free.setChecked(True)
        
        self.inp_user = QLineEdit(self.app_settings.get("username", "")); self.inp_user.setPlaceholderText("hide.me Username")
        self.inp_pass = QLineEdit(self.app_settings.get("password", "")); self.inp_pass.setPlaceholderText("hide.me Password")
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password) 
        
        self.r_free.toggled.connect(self.save_account_settings)
        self.r_paid.toggled.connect(self.save_account_settings)
        self.inp_user.textChanged.connect(self.save_account_settings)
        self.inp_pass.textChanged.connect(self.save_account_settings)
        
        l_acc.addWidget(QLabel("Select your hide.me subscription plan:", objectName="CardTitle"))
        l_acc.addWidget(self.r_free); l_acc.addWidget(self.r_paid)
        
        self.acc_creds_widget = QWidget(); l_creds = QVBoxLayout(self.acc_creds_widget); l_creds.setContentsMargins(0,10,0,0)
        l_creds.addWidget(QLabel("Username:")); l_creds.addWidget(self.inp_user)
        l_creds.addWidget(QLabel("Password:")); l_creds.addWidget(self.inp_pass)
        l_creds.addWidget(QLabel("🔒 Credentials are saved locally and passed securely via access tokens.", styleSheet="color: #8CA93A; font-size: 11px; margin-top: 5px;"))
        self.acc_creds_widget.setVisible(is_paid)
        self.r_paid.toggled.connect(self.acc_creds_widget.setVisible)
        
        l_acc.addWidget(self.acc_creds_widget); l_acc.addStretch()
        tabs.addTab(t_acc, "Account")
        # -----------------------
        
        t_proto = QWidget(); l_proto = QVBoxLayout(t_proto)
        self.r_auto = QRadioButton("Automatic (Recommended)"); self.r_auto.setChecked(True)
        self.r_v4 = QRadioButton("IPv4 Only (-4)")
        self.r_v6 = QRadioButton("IPv6 Only (-6)")
        for r in [self.r_auto, self.r_v4, self.r_v6]: l_proto.addWidget(r)
        l_proto.addStretch(); tabs.addTab(t_proto, "Protocol")
        
        t_kill = QWidget(); l_kill = QVBoxLayout(t_kill)
        self.chk_kill = QCheckBox("IP Leak Protection (Kill Switch)"); self.chk_kill.setChecked(True)
        self.chk_lan = QCheckBox("Allow local network connections (LAN access)"); self.chk_lan.setChecked(True)
        self.inp_lan = QLineEdit(get_local_subnet()); self.inp_lan.setFixedWidth(180)
        h_lan = QHBoxLayout(); h_lan.addWidget(self.chk_lan); h_lan.addWidget(self.inp_lan); h_lan.addStretch()
        l_kill.addWidget(self.chk_kill); l_kill.addLayout(h_lan)
        l_kill.addWidget(QLabel("\nExecute custom script when triggered:", objectName="CardTitle"))
        self.inp_script = QLineEdit("/path/to/script.sh"); l_kill.addWidget(self.inp_script)
        l_kill.addStretch(); tabs.addTab(t_kill, "Kill Switch")
        
        t_filt = QWidget(); l_filt = QVBoxLayout(t_filt)
        l_filt.addWidget(QLabel("Split Tunneling (Bypass VPN):", objectName="CardTitle"))
        self.chk_split = QCheckBox("Exclude specific external IP addresses or subnets (-s)")
        self.inp_subnet = QLineEdit(); self.inp_subnet.setPlaceholderText("e.g. 8.8.8.8/32, 10.0.0.0/8")
        l_filt.addWidget(self.chk_split); l_filt.addWidget(self.inp_subnet)
        
        l_filt.addWidget(QLabel("\nStealthGuard & Server Filters:", objectName="CardTitle"))
        self.chk_pf = QCheckBox("Port Forwarding (-pf)")
        self.chk_track = QCheckBox("Block Trackers (-noTrackers)"); self.chk_track.setChecked(True)
        self.chk_ads = QCheckBox("Block Ads (-noAds)")
        self.chk_malware = QCheckBox("Block Malware (-noMalware)")
        self.chk_malicious = QCheckBox("Block Malicious Sites (--noMalicious)")
        self.chk_illegal = QCheckBox("Block Illegal Content (--noIllegal)")
        self.chk_safe = QCheckBox("Enforce SafeSearch (--safeSearch)")
        for c in [self.chk_pf, self.chk_track, self.chk_ads, self.chk_malware, self.chk_malicious, self.chk_illegal, self.chk_safe]: 
            l_filt.addWidget(c)
        l_filt.addStretch(); tabs.addTab(t_filt, "Routing & Filters")

        t_adv = QWidget(); l_adv = QVBoxLayout(t_adv)
        self.chk_debug_mode = QCheckBox("Enable Background Logging in Console")
        self.chk_debug_mode.setToolTip("Will show hide.me background logs in the console.")
        self.chk_debug_mode.setChecked(self.app_settings.get("debug_mode", False))
        self.chk_debug_mode.stateChanged.connect(self.toggle_debug_mode)
        self.chk_incognito = QCheckBox("Incognito Mode (Wipe connection logs on exit)")
        self.chk_incognito.setChecked(self.app_settings.get("incognito_mode", False))
        self.chk_incognito.stateChanged.connect(self.toggle_incognito)
        l_adv.addWidget(self.chk_debug_mode); l_adv.addWidget(self.chk_incognito)
        l_adv.addStretch(); tabs.addTab(t_adv, "Advanced")

        t_exp = QWidget(); l_exp = QVBoxLayout(t_exp)
        l_exp.addWidget(QLabel("DNS & Name Resolution:", objectName="CardTitle"))
        self.chk_doh = QCheckBox("Disable DNS-over-HTTPS (--doh)")
        self.chk_force_dns = QCheckBox("Force DNS handling on VPN server (--forceDns)")
        self.inp_dns = QLineEdit(); self.inp_dns.setPlaceholderText("Custom DNS Servers (comma separated, e.g. 1.1.1.1:53)")
        l_exp.addWidget(self.chk_doh); l_exp.addWidget(self.chk_force_dns); l_exp.addWidget(self.inp_dns)
        
        l_exp.addWidget(QLabel("\nWireGuard & Network Interfaces:", objectName="CardTitle"))
        h_iface = QHBoxLayout(); h_iface.addWidget(QLabel("Interface Name (-i):")); self.inp_iface = QLineEdit(); self.inp_iface.setPlaceholderText("vpn"); h_iface.addWidget(self.inp_iface); l_exp.addLayout(h_iface)
        h_port = QHBoxLayout(); h_port.addWidget(QLabel("Listen Port (-l):")); self.inp_port = QLineEdit(); self.inp_port.setPlaceholderText("Random"); h_port.addWidget(self.inp_port); l_exp.addLayout(h_port)
        h_dpd = QHBoxLayout(); h_dpd.addWidget(QLabel("DPD Timeout (--dpd):")); self.inp_dpd = QLineEdit(); self.inp_dpd.setPlaceholderText("e.g. 1m0s"); h_dpd.addWidget(self.inp_dpd); l_exp.addLayout(h_dpd)
        
        l_exp.addWidget(QLabel("\nTroubleshooting:", objectName="CardTitle"))
        btn_reset = QPushButton("⚠️ Emergency Network Reset (Fix Internet)")
        btn_reset.setStyleSheet("background-color: #FF4C4C; color: white;")
        btn_reset.clicked.connect(self.emergency_reset)
        l_exp.addWidget(btn_reset)
        l_exp.addStretch(); tabs.addTab(t_exp, "Expert")

        layout.addWidget(tabs)
        self.stacked.addWidget(page)

    def save_account_settings(self):
        self.app_settings["is_paid"] = self.r_paid.isChecked()
        self.app_settings["username"] = self.inp_user.text().strip()
        self.app_settings["password"] = self.inp_pass.text().strip()
        self.save_app_settings()
        self.update_account_labels()

    def emergency_reset(self):
        self.log_debug("Executing emergency network reset...")
        self.disconnect_vpn()
        cleanup_zombie_network()
        QMessageBox.information(self, "Reset Complete", "Network interfaces and routes have been forcefully cleared.\nYour internet should work normally again.")

    def toggle_debug_mode(self):
        is_enabled = self.chk_debug_mode.isChecked()
        self.app_settings["debug_mode"] = is_enabled
        self.save_app_settings()
        if "Debug Console" in self.nav_btns:
            self.nav_btns["Debug Console"].setVisible(is_enabled)
            if not is_enabled and self.stacked.currentIndex() == 7: 
                self.switch_page("Settings")

    def toggle_incognito(self):
        self.app_settings["incognito_mode"] = self.chk_incognito.isChecked()
        self.save_app_settings()

    def toggle_auto_connect(self):
        self.app_settings["auto_connect"] = self.chk_autoconnect.isChecked()
        self.save_app_settings()

    def toggle_auto_start(self):
        import os
        import shutil
        import subprocess
        
        is_enabled = self.chk_autostart.isChecked()
        self.app_settings["auto_start"] = is_enabled
        self.save_app_settings()
        
        user = os.environ.get("SUDO_USER") or os.environ.get("USER")
        if not user or user == "root":
            user = os.getlogin()

        autostart_dir = os.path.expanduser(f"~{user}/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "hidemegui.desktop")
        sudoers_file = "/etc/sudoers.d/hidemegui_autostart"
        script_path = os.path.abspath(__file__)
        
        if is_enabled:
            sudoers_rule = f"{user} ALL=(ALL) NOPASSWD: /usr/bin/python3 {script_path}\n"
            
            try:
                with open(sudoers_file, "w") as f:
                    f.write(sudoers_rule)
                os.chmod(sudoers_file, 0o440)
            except PermissionError:
                subprocess.run(f'echo "{sudoers_rule}" | pkexec tee {sudoers_file}', shell=True)
                subprocess.run(f'pkexec chmod 440 {sudoers_file}', shell=True)

            os.makedirs(autostart_dir, exist_ok=True)
            desktop_content = f"""[Desktop Entry]
Type=Application
Exec=sudo /usr/bin/python3 {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=hide.me VPN
Comment=Start hide.me VPN Manager on login
"""
            with open(desktop_file, "w") as f:
                f.write(desktop_content)
                
            try:
                shutil.chown(desktop_file, user=user)
            except Exception:
                pass
                
        else:
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
            
            try:
                if os.path.exists(sudoers_file):
                    os.remove(sudoers_file)
            except PermissionError:
                subprocess.run(f'pkexec rm -f {sudoers_file}', shell=True)

    def toggle_auto_update(self):
        self.app_settings["auto_update"] = self.chk_autoupdate.isChecked()
        self.save_app_settings()
    
    def toggle_notif(self):
        self.app_settings["notifications"] = self.chk_notif.isChecked()
        self.save_app_settings()

    def wipe_traces(self):
        self.is_shutting_down = True 
        
        if self.app_settings.get("incognito_mode", False):
            self.log_entries = []
            if hasattr(self, 'txt_debug'): 
                self.txt_debug.clear()
            if os.path.exists(LOG_FILE):
                try: 
                    os.remove(LOG_FILE)
                except: 
                    pass

    def setup_system(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("System", objectName="PageHeader"))
        
        tabs = QTabWidget()
        t_opts = QWidget(); l_opts = QVBoxLayout(t_opts)
        
        self.chk_autostart = QCheckBox("Launch hide.me on system startup")
        self.chk_autostart.setChecked(self.app_settings.get("auto_start", False))
        self.chk_autostart.stateChanged.connect(self.toggle_auto_start)
        
        self.chk_autoconnect = QCheckBox("Auto-connect VPN on app launch")
        self.chk_autoconnect.setChecked(self.app_settings.get("auto_connect", False))
        self.chk_autoconnect.stateChanged.connect(self.toggle_auto_connect)
        
        self.chk_autoupdate = QCheckBox("Auto-check and install CLI updates on startup")
        self.chk_autoupdate.setChecked(self.app_settings.get("auto_update", True))
        self.chk_autoupdate.stateChanged.connect(self.toggle_auto_update)
        
        self.chk_notif = QCheckBox("Enable Native Desktop Notifications")
        self.chk_notif.setChecked(self.app_settings.get("notifications", True))
        self.chk_notif.stateChanged.connect(self.toggle_notif)
        
        self.chk_tray = QCheckBox("System Tray Integration (Minimize to Taskbar)")
        self.chk_tray.setChecked(self.app_settings.get("tray_icon", True))
        self.chk_tray.stateChanged.connect(self.toggle_tray_visibility)
        l_opts.addWidget(QLabel("Automation Setup:", objectName="CardTitle"))
        for c in [self.chk_autostart, self.chk_autoconnect, self.chk_autoupdate]: l_opts.addWidget(c)
        l_opts.addWidget(QLabel("\nDesktop Integration:", objectName="CardTitle"))
        for c in [self.chk_notif, self.chk_tray]: l_opts.addWidget(c)
        l_opts.addStretch(); tabs.addTab(t_opts, "Options")
        
        layout.addWidget(tabs)
        self.stacked.addWidget(page)

    def setup_logs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Logs & Messages", objectName="PageHeader"))
        
        card = CardWidget(is_square=False)
        self.log_table = QTableWidget(0, 5) 
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "VPN State", "IP Address", "Location", "Features"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        btn_clear = QPushButton("Clear / Delete Logs")
        btn_clear.clicked.connect(self.clear_logs)
        btn_clear.setFixedWidth(150)
        
        card.layout.addWidget(self.log_table); card.layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(card)
        self.stacked.addWidget(page)
        self.refresh_log_table()

    def setup_info(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Info & Updates", objectName="PageHeader"))
        card = CardWidget(is_square=False)
        card.layout.addWidget(QLabel(f"hide.me VPN Manager GUI\nVersion: {__version__} | Date: {__date__}", objectName="PrimaryText"))
        card.layout.addWidget(QLabel(f"This advanced interface maps CLI capabilities to a modern desktop experience.\nDeveloped as an open source project.", styleSheet="color: #2BAEE0; font-weight: bold; margin-top: 10px; margin-bottom: 20px;"))
        
        self.btn_update = QPushButton("🔄 Smart Updates: Check GitHub API"); self.btn_update.setFixedHeight(40); self.btn_update.clicked.connect(self.run_update_check)
        btn_git = QPushButton("⭐ View GitHub Repository"); btn_git.setFixedHeight(40); btn_git.clicked.connect(lambda: open_os_url("https://github.com/basecore/hideme-vpn-manager/tree/main"))
        btn_issues = QPushButton("🐛 Report an Issue / Bug"); btn_issues.setFixedHeight(40); btn_issues.clicked.connect(lambda: open_os_url("https://github.com/basecore/hideme-vpn-manager/issues"))
        
        card.layout.addWidget(self.btn_update); card.layout.addWidget(btn_git); card.layout.addWidget(btn_issues); card.layout.addStretch(); layout.addWidget(card)
        self.stacked.addWidget(page)

    def setup_debug(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Debug Console", objectName="PageHeader"))
        card = CardWidget(is_square=False)
        self.txt_debug = QTextEdit(); self.txt_debug.setReadOnly(True); self.txt_debug.setStyleSheet("font-family: monospace; font-size: 12px; background: black; color: #00FF00;")
        btn_clear = QPushButton("Clear Console"); btn_clear.clicked.connect(self.txt_debug.clear)
        card.layout.addWidget(self.txt_debug); card.layout.addWidget(btn_clear); layout.addWidget(card)
        self.stacked.addWidget(page)

    def run_update_check(self):
        if hasattr(self, 'upd_thread') and self.upd_thread.isRunning(): return
        self.log_debug("Update check started...")

    def refresh_log_table(self):
        if not hasattr(self, 'log_table'): return
        self.log_table.setRowCount(0)
        for entry in reversed(self.log_entries):
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem(entry["time"]))
            self.log_table.setItem(row, 1, QTableWidgetItem(entry["state"]))
            self.log_table.setItem(row, 2, QTableWidgetItem(entry["ip"]))
            self.log_table.setItem(row, 3, QTableWidgetItem(entry["loc"]))
            self.log_table.setItem(row, 4, QTableWidgetItem(entry.get("features", "-")))

    def clear_logs(self):
        self.log_entries = []
        self.save_logs()
        self.refresh_log_table()

    def apply_styles(self):
        is_dark = (self.current_theme == "dark")
        bg_main = "#0D1623" if is_dark else "#F3F5F7"
        bg_top = "#0A111A" if is_dark else "#172B40"
        bg_side = "#111E2D" if is_dark else "#27B4E6"
        text_main = "white" if is_dark else "#0F172A"
        text_side = "#8B9BB4" if is_dark else "white"
        text_sub = "#8B9BB4" if is_dark else "#64748B"
        card_bg = "#132233" if is_dark else "white"
        card_border = "#1C2E42" if is_dark else "#E2E8F0"
        btn_bg = "#2BAEE0" if is_dark else "#27B4E6"
        btn_hover = "#1A9BD0" if is_dark else "#1DA1D1"
        pagebtnbg = "#132233" if is_dark else "#E2E8F0"
        pagebtntext = "white" if is_dark else "#0F172A"
        pagebtnborder = "#2BAEE0" if is_dark else "#CBD5E1"
        pagebtnhover = "#1C2E42" if is_dark else "#CBD5E1"
        
        palette = QApplication.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        QApplication.setPalette(palette)
        
        css = f"""
            QMainWindow, #MainContent, QDialog {{ background-color: {bg_main}; }}
            #TopBar {{ background-color: {bg_top}; }}
            #LogoText {{ color: white; font-weight: bold; font-size: 14px; margin-left: 10px; }}
            #TopIconBtn {{ background: transparent; color: white; font-size: 16px; border: none; padding: 5px 10px; }}
            #TopIconBtn:hover {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}
            #PageActionBtn {{ background-color: {pagebtnbg}; color: {pagebtntext}; border: 1px solid {pagebtnborder}; padding: 8px 12px; border-radius: 4px; font-weight: bold; }}
            #PageActionBtn:hover {{ background-color: {pagebtnhover}; }}
            #SideBar {{ background-color: {bg_side}; }}
            #SideBar QPushButton {{ background-color: transparent; color: {text_side}; text-align: left; padding: 15px 20px; font-size: 14px; border: none; font-weight: bold; }}
            #SideBar QPushButton:hover {{ background-color: rgba(255,255,255,0.1); color: white; }}
            #SideBar QPushButton:checked {{ background-color: rgba(0,0,0,0.15); color: white; border-left: 4px solid white; }}
            #PageHeader {{ font-size: 22px; color: {text_main}; font-weight: bold; margin-bottom: 10px; }}
            #Card {{ background-color: {card_bg}; border-radius: 6px; border: 1px solid {card_border}; }}
            #CardTitle {{ color: {text_sub}; font-size: 13px; font-weight: bold; margin-bottom: 5px; }}
            #PrimaryText {{ color: {text_main}; font-weight: bold; font-size: 14px; margin-bottom: 5px; }}
            #ConnectBtn {{ background-color: {btn_bg}; color: white; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; text-align: left; padding-left: 20px; }}
            #ConnectBtn:hover {{ background-color: {btn_hover}; }}
            QLabel, QCheckBox, QRadioButton {{ color: {text_main}; font-size: 13px; }}
            QLineEdit, QComboBox {{ padding: 8px; border: 1px solid {card_border}; border-radius: 4px; background: {bg_main}; color: {text_main}; font-weight: 500; }}
            QComboBox QAbstractItemView {{ background-color: {bg_main}; color: {text_main}; selection-background-color: {btn_bg}; }}
            QTabWidget::pane {{ border: 1px solid {card_border}; background: {card_bg}; }}
            QTabBar::tab {{ background: {bg_main}; color: {text_sub}; padding: 10px 20px; border: 1px solid {card_border}; }}
            QTabBar::tab:selected {{ background: {card_bg}; color: {text_main}; font-weight: bold; border-bottom: none; }}
            QTableWidget {{ background: {card_bg}; color: {text_main}; gridline-color: {card_border}; border: none; }}
            QHeaderView::section {{ background: {bg_main}; color: {text_sub}; border: none; padding: 5px; }}
            QMessageBox {{ background-color: {card_bg}; color: {text_main}; }}
            QPushButton {{ background-color: {bg_main}; color: {text_main}; padding: 8px; border-radius: 4px; border: 1px solid {card_border}; font-weight:bold; }}
            QPushButton:hover {{ background-color: {card_bg}; }}
            QToolTip {{ color: #ffffff; background-color: #132233; border: 1px solid #2BAEE0; font-size: 12px; padding: 4px; }}
        """
        self.setStyleSheet(css)

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        with open(THEME_FILE, "w") as f: f.write(self.current_theme)
        self.btn_theme.setText("🌙" if self.current_theme == "light" else "☀️")
        self.apply_styles()
        self.update_map_html(self.current_connected_server)
        self.update_mini_map()

    def switch_page(self, name):
        for n, btn in self.nav_btns.items():
            if n != name: btn.setChecked(False)
            else: btn.setChecked(True)
        pages = {"Dashboard": 0, "Locations": 1, "Map": 2, "Settings": 3, "System": 4, "Logs": 5, "Info": 6, "Debug Console": 7}
        self.stacked.setCurrentIndex(pages.get(name, 0))

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_icon("#8B9BB4"))
        menu = QMenu()
        a1 = QAction("Show / Hide App", self); a1.triggered.connect(lambda: self.show() if self.isHidden() else self.hide())
        a2 = QAction("Connect / Disconnect VPN", self); a2.triggered.connect(lambda: self.connect_vpn(None))
        a3 = QAction("Quit", self); a3.triggered.connect(self.force_quit)
        for a in [a1, a2, a3]: menu.addAction(a)
        self.tray_icon.setContextMenu(menu)
        if hasattr(self, 'chk_tray') and self.chk_tray.isChecked(): self.tray_icon.show()

    def force_quit(self):
        if self.is_connected:
            self.disconnect_vpn()
        self.wipe_traces()
        QApplication.instance().quit()

    def toggle_tray_visibility(self):
        self.app_settings["tray_icon"] = self.chk_tray.isChecked()
        self.save_app_settings()
        if self.chk_tray.isChecked(): self.tray_icon.show()
        else: self.tray_icon.hide()

    def create_icon(self, color_hex):
        pixmap = QPixmap(64, 64); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color_hex)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56); painter.end()
        return QIcon(pixmap)

    def closeEvent(self, event):
        if self.is_connected:
            reply = QMessageBox.question(self, '🛡️ VPN Active', "Your VPN connection is currently ACTIVE.\n\nMinimize to tray?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                event.ignore(); self.hide()
            elif reply == QMessageBox.StandardButton.No:
                self.disconnect_vpn(); self.wipe_traces(); event.accept(); QApplication.instance().quit()
            else:
                event.ignore()
        else:
            if hasattr(self, 'chk_tray') and self.chk_tray.isChecked():
                event.ignore(); self.hide()
            else:
                self.wipe_traces(); event.accept(); QApplication.instance().quit()

    def update_timer(self):
        elapsed = int(time.time() - self.conn_start_time)
        hrs, rem = divmod(elapsed, 3600); mins, secs = divmod(rem, 60)
        if hasattr(self, 'btn_connect') and self.btn_connect.text().startswith("  🔒"):
            self.btn_connect.setText(f"  🔒   {hrs:02d}:{mins:02d}:{secs:02d}  ⚡")

    def run_ping(self):
        sel = self.combo_loc.currentText()
        if sel == "🎲 Random Location": return
        elif sel == "⚡ Best Location":
            self.ping_best_finder = BestLocationFinderThread(); self.ping_best_finder.best_found.connect(lambda c, p: self.lbl_ping_res.setText(f"{SERVER_LIST.get(c, {}).get('name', c)} ({int(p)} ms)")); self.ping_best_finder.start()
        else:
            code = next((k for k, v in SERVER_LIST.items() if v["name"] == sel), "free-de")
            self.pinger = PingThread(code); self.pinger.ping_result.connect(self.lbl_ping_res.setText); self.pinger.start()

    def fetch_ip(self, connected_state):
        if not hasattr(self, '_active_ip_threads'): 
            self._active_ip_threads = []
        self._active_ip_threads = [t for t in self._active_ip_threads if t.isRunning()]
        t = IpFetcherThread(connected_state)
        t.ip_fetched.connect(self.on_ip_fetched)
        self._active_ip_threads.append(t)
        t.start()

    # 4. Länderflaggen-Korrektur (z.B. bei Falkenstein)
    def on_ip_fetched(self, ipv4, ipv6, city, country_code, loc_str_coords, was_connected):
        if was_connected != self.is_connected:
            return

        flag = ""
        if len(country_code) == 2 and country_code.isalpha():
            flag = ''.join(chr(ord(c) + 127397) for c in country_code.upper()) + " "
            
        loc_str = f"{city}, {flag}{country_code}" if country_code else city
        
        if hasattr(self, 'lbl_ip4'):
            self.lbl_ip4.setText(f"IPv4\n{ipv4}\n\nLocation\n{loc_str}")
        if hasattr(self, 'lbl_ip6'):
            self.lbl_ip6.setText(f"IPv6\n{ipv6}")
            
        if loc_str_coords and "," in loc_str_coords:
            try:
                lat, lon = loc_str_coords.split(",")
                self.live_map_lat = float(lat)
                self.live_map_lon = float(lon)
            except: pass
        else:
            self.live_map_lat = None
            self.live_map_lon = None
            
        if was_connected: 
            self.add_log_entry("Connected", ipv4, loc_str, self.current_features_str)
            if city != "Unknown" and self.current_connected_server in SERVER_LIST:
                current_name = SERVER_LIST[self.current_connected_server]["name"]
                if city not in current_name:
                    
                    old_base_name = current_name
                    correct_flag = flag.strip() if flag else SERVER_LIST[self.current_connected_server].get("flag", "🌍")
                    
                    new_base_name = f"{correct_flag} {city} ({country_code})"
                    SERVER_LIST[self.current_connected_server]["name"] = new_base_name
                    SERVER_LIST[self.current_connected_server]["flag"] = correct_flag
                    self.log_debug(f"Updated location name dynamically to {city}")
                    
                    # --- NEU: Den aktuellen Namen dauerhaft merken ---
                    known = self.app_settings.get("known_server_names", {})
                    known[self.current_connected_server] = new_base_name
                    self.app_settings["known_server_names"] = known
                    self.save_app_settings()
                    # -------------------------------------------------
                    
                    self.status_banner.setText(f"🔒 PROTECTED - Connected to {new_base_name}")
                    
                    # 2. FIX: Auswahl-Historie synchronisieren, damit das Dropdown nicht "wegspringt"
                    if self.app_settings.get("selected_location", "") == old_base_name:
                        self.app_settings["selected_location"] = new_base_name
                        self.save_app_settings()
                        
                    if self.last_connected_combo_text and self.last_connected_combo_text.startswith(old_base_name):
                        self.last_connected_combo_text = new_base_name
                    
                    self.refresh_server_dropdowns()
                    if hasattr(self, 'card_fav'):
                        self.render_favorites()
        else:
            self.add_log_entry("Disconnected", ipv4, loc_str, "Unprotected")
            
        self.update_map_html(self.current_connected_server)
        self.update_mini_map()

    def update_traffic(self, rx, tx, total_rx, total_tx):
        if hasattr(self, 'lbl_rx'): self.lbl_rx.setText(f"↓ {rx}"); self.lbl_tx.setText(f"↑ {tx}")
        if hasattr(self, 'lbl_session'): self.lbl_session.setText(f"Session: ↓ {total_rx} | ↑ {total_tx}")

    def update_ui_state(self, connected):
        if self._last_state == connected: return
        self._last_state = connected
        
        self.is_connected = connected
        if connected:
            self.conn_start_time = time.time(); self.timer.start(1000)
            if hasattr(self, "lbl_pingdash"):
                self.lbl_pingdash.setText("Ping: measuring...")
            self.update_dashboard_ping()
            self.dashboard_ping_timer.start(300000)
            server_name = SERVER_LIST.get(self.current_connected_server, {}).get("name", self.current_connected_server)
            self.status_banner.setText(f"🔒 PROTECTED - Connected to {server_name}")
            self.status_banner.setStyleSheet("background-color: #8CA93A; color: white; font-weight: bold; font-size: 14px; padding: 6px;")
            if hasattr(self, 'btn_connect'):
                self.btn_connect.setText("  🔒   00:00:00  ⚡")
                self.btn_connect.setStyleSheet("background-color: #8CA93A; color: white; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; text-align: left; padding-left: 20px;")
            self.tray_icon.setIcon(self.create_icon("#8CA93A"))
            self.send_os_notification("hide.me VPN", "Protected! Connection established.")
            
            self.fetch_servers_background()
        else:
            self.current_connected_server = None
            self.live_map_lat = None
            self.live_map_lon = None
            self.timer.stop()
            self.dashboard_ping_timer.stop()
            if hasattr(self, "lbl_pingdash"):
                self.lbl_pingdash.setText("Ping: - ms")
            self.status_banner.setText("⚠️ UNPROTECTED - VPN is NOT active! Your internet traffic is exposed.")
            self.status_banner.setStyleSheet("background-color: #FF4C4C; color: white; font-weight: bold; font-size: 14px; padding: 6px;")
            if hasattr(self, 'btn_connect'):
                self.btn_connect.setText("  ⏻   Enable VPN")
                self.btn_connect.setStyleSheet("") 
            self.tray_icon.setIcon(self.create_icon("#8B9BB4"))
            self.send_os_notification("hide.me VPN", "Unprotected! VPN Disconnected.")
            
        self.fetch_ip(connected)

    def disconnect_vpn(self):
        try:
            if self.vpn_subprocess:
                self.vpn_subprocess.terminate()
                try:
                    self.vpn_subprocess.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.vpn_subprocess.kill()
                self.vpn_subprocess = None
            cleanup_zombie_network()
        except: pass

    def connect_vpn(self, server_code=None, source_combo=None):
        combo = source_combo if source_combo else (self.combo_loc if hasattr(self, 'combo_loc') else None)
        sel = combo.currentText() if combo else "⚡ Best Location"
        
        if sel == "🎲 Random Location": target_code = random.choice(list(SERVER_LIST.keys()))
        elif sel == "⚡ Best Location": target_code = "best"
        else: 
            target_code = "free-de"
            for k, v in SERVER_LIST.items():
                if sel.startswith(v["name"]):
                    target_code = k
                    break

        if server_code is not None: target_code = server_code

        if self.is_connected:
            if server_code is None:
                # 3. FIX: Ping-Werte ignorieren beim Prüfen, ob wir trennen oder wechseln sollen
                base_sel = sel.split("  (")[0] if "  (" in sel else sel
                base_last = self.last_connected_combo_text.split("  (")[0] if self.last_connected_combo_text else None
                
                if base_sel == base_last:
                    self.disconnect_vpn()
                    return
            else:
                if target_code == self.current_connected_server:
                    self.disconnect_vpn()
                    return

            if hasattr(self, 'btn_connect'): self.btn_connect.setText("  🔄 Switching...")
            self.disconnect_vpn()
            self.last_connected_combo_text = sel
            
            if target_code == "best": QTimer.singleShot(2500, self._start_best_finder)
            else: QTimer.singleShot(2500, lambda: self._execute_vpn_connection(target_code))
            return

        self.last_connected_combo_text = sel
        if target_code == "best": self._start_best_finder()
        else: self._execute_vpn_connection(target_code)

    def _start_best_finder(self):
        if hasattr(self, 'btn_connect'): self.btn_connect.setText("  Searching best...")
        self.best_finder = BestLocationFinderThread()
        self.best_finder.best_found.connect(lambda code, ping: self._execute_vpn_connection(code))
        self.best_finder.start()

    def _execute_vpn_connection(self, server_code):
        cleanup_zombie_network()
        self.current_connected_server = server_code
        feats = []; split_targets = []
        if hasattr(self, 'chk_kill') and self.chk_kill.isChecked(): feats.append("KS")
        if hasattr(self, 'chk_pf') and self.chk_pf.isChecked(): feats.append("PF")
        if hasattr(self, 'chk_ads') and self.chk_ads.isChecked(): feats.append("NoAds")
        if hasattr(self, 'chk_track') and self.chk_track.isChecked(): feats.append("NoTrack")
        if hasattr(self, 'chk_malware') and self.chk_malware.isChecked(): feats.append("NoMalware")
        if hasattr(self, 'chk_malicious') and self.chk_malicious.isChecked(): feats.append("NoMalicious")
        if hasattr(self, 'chk_illegal') and self.chk_illegal.isChecked(): feats.append("NoIllegal")
        if hasattr(self, 'chk_safe') and self.chk_safe.isChecked(): feats.append("SafeSearch")
        if hasattr(self, 'chk_force_dns') and self.chk_force_dns.isChecked(): feats.append("ForceDNS")
        
        if hasattr(self, 'chk_lan') and self.chk_lan.isChecked():
            lan_val = self.inp_lan.text().strip()
            if lan_val: feats.append("LAN-Bypass"); split_targets.append(lan_val)
        if hasattr(self, 'chk_split') and self.chk_split.isChecked():
            custom_split = self.inp_subnet.text().strip()
            if custom_split: feats.append("Custom-Split"); split_targets.append(custom_split)

        self.current_features_str = ", ".join(feats) if feats else "None"
        cmd = ["sudo", "hide.me"]
        
        if split_targets: cmd.extend(["-s", ",".join(split_targets)])
        if hasattr(self, 'r_v4') and self.r_v4.isChecked(): cmd.append("-4")
        elif hasattr(self, 'r_v6') and self.r_v6.isChecked(): cmd.append("-6")
        if hasattr(self, 'chk_kill') and not self.chk_kill.isChecked(): cmd.append("-k=false")
        if hasattr(self, 'chk_pf') and self.chk_pf.isChecked(): cmd.append("-pf")
        if hasattr(self, 'chk_ads') and self.chk_ads.isChecked(): cmd.append("-noAds")
        if hasattr(self, 'chk_malware') and self.chk_malware.isChecked(): cmd.append("-noMalware")
        if hasattr(self, 'chk_track') and self.chk_track.isChecked(): cmd.append("-noTrackers")
        if hasattr(self, 'chk_malicious') and self.chk_malicious.isChecked(): cmd.append("--noMalicious")
        if hasattr(self, 'chk_illegal') and self.chk_illegal.isChecked(): cmd.extend(["--noIllegal", "content,warez,spyware,copyright"])
        if hasattr(self, 'chk_safe') and self.chk_safe.isChecked(): cmd.append("--safeSearch")
        if hasattr(self, 'chk_doh') and self.chk_doh.isChecked(): cmd.append("--doh")
        if hasattr(self, 'chk_force_dns') and self.chk_force_dns.isChecked(): cmd.append("--forceDns")
        if hasattr(self, 'inp_dns') and self.inp_dns.text().strip(): cmd.extend(["-d", self.inp_dns.text().strip()])
        if hasattr(self, 'inp_iface') and self.inp_iface.text().strip(): cmd.extend(["-i", self.inp_iface.text().strip()])
        if hasattr(self, 'inp_port') and self.inp_port.text().strip(): cmd.extend(["-l", self.inp_port.text().strip()])
        if hasattr(self, 'inp_dpd') and self.inp_dpd.text().strip(): cmd.extend(["--dpd", self.inp_dpd.text().strip()])
        
        cmd.append("connect"); cmd.append(server_code)
        
        safe_cmd_log = list(cmd)
        if self.app_settings.get("is_paid", False):
            user = self.app_settings.get("username", "")
            pwd = self.app_settings.get("password", "")
            if user and pwd:
                cmd.extend(["-username", user, "-password", pwd])
                safe_cmd_log.extend(["-username", user, "-password", "***SECURE***"])
        
        try: 
            self.log_debug(f"Executing: {' '.join(safe_cmd_log)}")
            self.vpn_subprocess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            
            if self.reader_thread and self.reader_thread.isRunning():
                self.reader_thread.running = False
                self.reader_thread.wait()
                
            self.reader_thread = VpnProcessReaderThread(self.vpn_subprocess)
            self.reader_thread.new_log.connect(self.log_debug)
            self.reader_thread.start()
            
            if hasattr(self, 'btn_connect'): self.btn_connect.setText("  Connecting...")
        except Exception as e: pass

if __name__ == '__main__':
    if "--no-sandbox" not in sys.argv:
        sys.argv.append("--no-sandbox")
    
    if "--disable-web-security" not in sys.argv:
        sys.argv.append("--disable-web-security")

    if not sys.platform.startswith("linux"):
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Unsupported Operating System")
        msg.setText("This interface is exclusively designed for Linux and the hide.me CLI.")
        msg.exec()
        sys.exit(1)
        
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    
    default_font = QApplication.font()
    sys_family = default_font.family()
    families = [f for f in default_font.families() if f != "Noto Color Emoji"]
    if sys_family not in families:
        families.insert(0, sys_family)
    families.append("Noto Color Emoji")
    default_font.setFamilies(families)
    app.setFont(default_font)
    
    if hasattr(os, 'geteuid') and os.geteuid() != 0:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Root Privileges Required")
        msg.setText("The hide.me CLI requires Root/Sudo privileges to configure WireGuard interfaces and routing tables securely.\n\n"
                    "Please restart the application using the terminal:\n"
                    "sudo python3 hideme_gui.py")
        msg.exec()
        sys.exit(1)
        
    window = HideMeOfficialUI()
    window.show()
    sys.exit(app.exec())
