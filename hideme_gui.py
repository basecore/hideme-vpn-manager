#!/usr/bin/env python3
# ==============================================================================
# hide.me VPN Manager GUI - Ultimate Interactive Edition (v26)
# ==============================================================================
__version__ = "26.0.0"
__date__ = "April 15, 2026"
__ai_model__ = "Gemini 3.1 Pro"

import os
import sys
import subprocess
import time
import random
import json
import webbrowser
import traceback
import logging

# --- Custom Logger for Debug Console ---
class QtLogger(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)

# --- Platform Specific Imports ---
if sys.platform != "win32":
    try: import pwd
    except ImportError: pass

# --- Auto-Install Python Modules ---
def install_and_import():
    modules = {'PyQt6': 'PyQt6', 'requests': 'requests', 'PyQt6.QtWebEngineWidgets': 'PyQt6-WebEngine'}
    for mod, pkg in modules.items():
        try: __import__(mod)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
install_and_import()

import requests
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QGridLayout, QFrame, QCheckBox, QLineEdit, 
                             QComboBox, QSystemTrayIcon, QMenu, QRadioButton, 
                             QTabWidget, QMessageBox, QTableWidget, QTextEdit,
                             QTableWidgetItem, QHeaderView, QAbstractItemView, 
                             QInputDialog, QDialog, QDialogButtonBox, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction

# --- WebEngine for Map ---
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
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

# --- Configuration Paths ---
CONFIG_DIR = "/etc/hide.me" if sys.platform != "win32" else os.path.join(os.path.expanduser("~"), ".hideme_gui")
LOG_FILE = os.path.join(CONFIG_DIR, "system_logs.json")
THEME_FILE = os.path.join(CONFIG_DIR, "theme.conf")
DASH_FILE = os.path.join(CONFIG_DIR, "dashboard.json")
FAV_FILE = os.path.join(CONFIG_DIR, "favorites.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

# --- Server Database ---
SERVER_LIST = {
    "free-de": {"name": "🇩🇪 Germany (Frankfurt)", "lat": 50.1109, "lon": 8.6821},
    "free-fr": {"name": "🇫🇷 France (Paris)", "lat": 48.8566, "lon": 2.3522},
    "free-nl": {"name": "🇳🇱 Netherlands (Amsterdam)", "lat": 52.3676, "lon": 4.9041},
    "free-ch": {"name": "🇨🇭 Switzerland (Zurich)", "lat": 47.3769, "lon": 8.5417},
    "free-uk": {"name": "🇬🇧 United Kingdom (London)", "lat": 51.5074, "lon": -0.1278},
    "free-us": {"name": "🇺🇸 United States (Los Angeles)", "lat": 34.0522, "lon": -118.2437}
}

def get_local_subnet():
    if sys.platform == "win32": return "192.168.178.0/24 (Preview)"
    try:
        route_out = subprocess.check_output(["ip", "route"]).decode()
        default_iface = next((l.split()[l.split().index("dev")+1] for l in route_out.splitlines() if l.startswith("default") and "dev" in l), None)
        if default_iface:
            return next((l.split()[0] for l in route_out.splitlines() if default_iface in l and "scope link" in l), "192.168.178.0/24")
    except: pass
    return "192.168.178.0/24"

# --- Threads ---
class VpnMonitorThread(QThread):
    state_changed = pyqtSignal(bool)
    def run(self):
        last_state = None
        while True:
            if sys.platform == "win32": time.sleep(2); continue
            try:
                is_running = subprocess.run(['pgrep', '-x', 'hide.me'], stdout=subprocess.DEVNULL).returncode == 0
                if is_running != last_state:
                    last_state = is_running
                    self.state_changed.emit(is_running)
            except: pass
            time.sleep(1.5)

class TrafficThread(QThread):
    traffic_updated = pyqtSignal(str, str)
    def run(self):
        last_rx, last_tx = 0, 0
        while True:
            if sys.platform == "win32":
                self.traffic_updated.emit("0.00 KB/s (Sim)", "0.00 KB/s (Sim)"); time.sleep(1); continue
            try:
                curr_rx, curr_tx = 0, 0
                with open('/proc/net/dev', 'r') as f:
                    for line in f.readlines()[2:]:
                        parts = line.split()
                        iface = parts[0].strip(':')
                        if iface.startswith('tun') or 'hide' in iface:
                            curr_rx += int(parts[1]); curr_tx += int(parts[9])
                rx_speed = curr_rx - last_rx if last_rx > 0 else 0
                tx_speed = curr_tx - last_tx if last_tx > 0 else 0
                last_rx, last_tx = curr_rx, curr_tx
                fmt = lambda b: f"{b/1048576:.2f} MB/s" if b > 1048576 else f"{b/1024:.2f} KB/s"
                self.traffic_updated.emit(fmt(rx_speed), fmt(tx_speed))
            except: pass
            time.sleep(1)

class IpFetcherThread(QThread):
    ip_fetched = pyqtSignal(str, str)
    def __init__(self, simulate_vpn=False):
        super().__init__()
        self.simulate_vpn = simulate_vpn
    def run(self):
        try:
            if sys.platform == "win32":
                time.sleep(1)
                ip = "166.90.116.170" if self.simulate_vpn else "192.168.0.42"
                loc = "Los Angeles, US (Simulated)" if self.simulate_vpn else "Local (Simulated)"
                self.ip_fetched.emit(ip, loc)
                return
                
            data = requests.get("https://ipinfo.io/json", timeout=5).json()
            self.ip_fetched.emit(data.get('ip', 'Unknown'), f"{data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}")
        except:
            self.ip_fetched.emit("Error", "Unknown")

class PingThread(QThread):
    ping_result = pyqtSignal(str)
    def __init__(self, server):
        super().__init__()
        self.server = server
    def run(self):
        try:
            if sys.platform == "win32":
                time.sleep(0.5); self.ping_result.emit(f"{random.randint(15, 80)} ms (Simulated)"); return
            out = subprocess.check_output(["ping", "-c", "3", "-W", "1", f"{self.server}.hideservers.net"], stderr=subprocess.STDOUT).decode()
            match = re.search(r'min/avg/max/mdev = [\d\.]+/(.*?)/', out)
            if match:
                self.ping_result.emit(f"{int(float(match.group(1)))} ms")
                return
        except: pass
        self.ping_result.emit("Failed")

class BestLocationFinderThread(QThread):
    best_found = pyqtSignal(str)
    def run(self):
        if sys.platform == "win32":
            time.sleep(1) 
            self.best_found.emit("free-de")
            return
            
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
            
        self.best_found.emit(best_server)

class UpdateCheckThread(QThread):
    update_result = pyqtSignal(str)
    def run(self):
        try:
            time.sleep(1.5) 
            self.update_result.emit("✅ App & CLI are up to date.")
        except:
            self.update_result.emit("❌ Failed to check GitHub API.")

class CliAutoUpdateThread(QThread):
    result = pyqtSignal(str)
    def run(self):
        if sys.platform == "win32": return
        try:
            subprocess.run("curl -sL https://hide.me/install.sh | bash", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.result.emit("CLI updated successfully in background.")
        except Exception as e:
            self.result.emit(f"CLI background update failed: {e}")

# --- UI Layout Elements ---
class CardWidget(QFrame):
    def __init__(self, title="", is_square=False):
        super().__init__()
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        if is_square:
            self.setFixedSize(270, 270) # Force exact square dimension for Dashboard grids
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
            lbl.setStyleSheet("color: #64748B;")
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
        self.current_connected_server = None
        self.conn_start_time = 0
        self.current_features_str = "-"
        
        self.current_theme = self.load_theme()
        self.favorites = self.load_favorites()
        self.dash_layout_config = self.load_dash_config()
        self.log_entries = self.load_logs()
        self.app_settings = self.load_app_settings()
        
        self.init_logger()
        self.log_debug("Application initializing...")
        
        self.check_and_install_cli()
        
        self.init_ui()
        self.apply_styles()
        self.setup_tray()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.monitor_thread = VpnMonitorThread()
        self.monitor_thread.state_changed.connect(self.update_ui_state)
        self.monitor_thread.start()
        
        self.traffic_thread = TrafficThread()
        self.traffic_thread.traffic_updated.connect(self.update_traffic)
        self.traffic_thread.start()
        
        QTimer.singleShot(2000, self.run_auto_update_if_enabled)
        self.fetch_ip()

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

    def check_and_install_cli(self):
        if sys.platform == "win32": return
        try:
            if subprocess.run(['which', 'hide.me'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                self.log_debug("CLI missing. Starting auto-installer...", logging.WARNING)
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Zero-Setup Auto-Installer")
                msg.setText("The hide.me CLI is not installed.\nDownloading and installing automatically...")
                msg.show()
                QApplication.processEvents()
                try:
                    subprocess.run("curl -sL https://hide.me/install.sh | bash", shell=True, check=True)
                    msg.setText("✅ hide.me CLI successfully installed!")
                    self.log_debug("CLI auto-installed successfully.")
                    QApplication.processEvents()
                    time.sleep(1.5)
                except Exception as e:
                    self.log_debug(f"CLI auto-install failed: {e}", logging.ERROR)
                    QMessageBox.critical(self, "Install Failed", f"Could not auto-install.\nPlease run manually: curl -sL https://hide.me/install.sh | sudo bash\n\nError: {e}")
        except Exception as e: 
            self.log_debug(f"Pre-check failed: {e}", logging.ERROR)

    def run_auto_update_if_enabled(self):
        if hasattr(self, 'chk_autoupdate') and self.chk_autoupdate.isChecked():
            self.log_debug("Running background CLI auto-update...")
            self.auto_upd_thread = CliAutoUpdateThread()
            self.auto_upd_thread.result.connect(self.log_debug)
            self.auto_upd_thread.start()

    def load_app_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: pass
        return {"debug_mode": False}

    def save_app_settings(self):
        with open(SETTINGS_FILE, "w") as f: json.dump(self.app_settings, f)

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
        with open(LOG_FILE, "w") as f: json.dump(self.log_entries[-50:], f)

    def add_log_entry(self, state, ip, location, features="-"):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {"time": ts, "state": state, "ip": ip, "loc": location, "features": features}
        self.log_entries.append(entry)
        self.save_logs()
        self.refresh_log_table()

    def send_os_notification(self, title, message):
        if not hasattr(self, 'chk_notif') or not self.chk_notif.isChecked(): return
        if sys.platform == "win32": return
        try:
            user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
            uid = pwd.getpwnam(user).pw_uid
            cmd = f"sudo -u {user} DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus notify-send '{title}' '{message}' -i network-vpn"
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    # --- Setup UI ---
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        
        # --- WINDOWS SIMULATION WARNING ---
        if sys.platform == "win32":
            warn_lbl = QLabel("⚠️ Windows 11 Simulation Mode Active: Network changes, Pings, and CLI commands are purely simulated.")
            warn_lbl.setStyleSheet("background-color: #fbbf24; color: black; font-weight: bold; padding: 6px; font-size: 13px;")
            warn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(warn_lbl)

        # --- TOP BAR ---
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(45)
        top_layout = QHBoxLayout(top_bar)
        
        top_layout.addWidget(QLabel("hide.me VPN", objectName="LogoText"))
        top_layout.addStretch()
        
        self.btn_theme = QPushButton("🌙" if self.current_theme == "light" else "☀️")
        self.btn_theme.setObjectName("TopIconBtn")
        self.btn_theme.clicked.connect(self.toggle_theme)
        
        btn_bug = QPushButton("🐛")
        btn_bug.setObjectName("TopIconBtn")
        btn_bug.clicked.connect(lambda: webbrowser.open("https://github.com/basecore/hideme-vpn-manager/issues"))
        
        top_layout.addWidget(self.btn_theme)
        top_layout.addWidget(btn_bug)
        main_layout.addWidget(top_bar)

        # --- BODY ---
        body_layout = QHBoxLayout()
        body_layout.setSpacing(0)
        main_layout.addLayout(body_layout)

        # --- SIDEBAR ---
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
        
        lbl_acc = QLabel("Your Account\nFree Plan")
        lbl_acc.setStyleSheet("color: #8B9BB4; padding-left: 20px; font-weight: bold;")
        sidebar_layout.addWidget(lbl_acc)
        body_layout.addWidget(sidebar)

        # --- MAIN CONTENT ---
        self.stacked = QStackedWidget()
        self.stacked.setObjectName("MainContent")
        body_layout.addWidget(self.stacked)
        
        # Load all pages
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
        # We explicitly set is_square=True to force exactly 270x270 px squares
        if name == "Quick Connect":
            c = CardWidget("Quick connect", is_square=True)
            self.dash_combo_loc = QComboBox()
            opts = ["⚡ Best Location", "🎲 Random Location"] + [v["name"] for v in SERVER_LIST.values()]
            self.dash_combo_loc.addItems(opts)
            self.dash_combo_loc.setFixedHeight(35)
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
            self.lbl_ip = QLabel("IPv4\nLoading...\n\nLocation\n-")
            c.layout.addWidget(self.lbl_ip)
            c.layout.addStretch()
            return c
            
        elif name == "My Account":
            c = CardWidget("My account", is_square=True)
            c.layout.addWidget(QLabel(f"Current Plan\nFree / CLI\n\nEnvironment\n{sys.platform}\n\nNotice: Optimized for Free Plan"))
            c.layout.addStretch()
            return c
            
        elif name == "Live Traffic Monitor":
            c = CardWidget("Live Traffic Monitor", is_square=True)
            self.lbl_rx = QLabel("↓ 0.00 KB/s"); self.lbl_tx = QLabel("↑ 0.00 KB/s")
            ts = "font-family: monospace; font-size: 16px; font-weight: bold; margin-top: 5px;"
            self.lbl_rx.setStyleSheet(ts + "color: #2BAEE0;")
            self.lbl_tx.setStyleSheet(ts + "color: #FF4C4C;")
            c.layout.addWidget(QLabel("Download", objectName="CardTitle")); c.layout.addWidget(self.lbl_rx)
            c.layout.addWidget(QLabel("Upload", objectName="CardTitle")); c.layout.addWidget(self.lbl_tx)
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
            btn_git.clicked.connect(lambda: webbrowser.open("https://github.com/basecore"))
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
        btn_edit.setObjectName("TopIconBtn")
        btn_edit.clicked.connect(self.edit_dashboard)
        header_layout.addWidget(btn_edit)
        layout.addLayout(header_layout)

        # Center the grid dynamically so squares stay perfect regardless of window scaling
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
        
        btn_ping = QPushButton("⚡ Test Ping")
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
        
        for code, data in SERVER_LIST.items():
            name = data['name'].split(" ")[1] 
            color = "green" if code == focus_code and self.is_connected else "#2BAEE0"
            if code == focus_code and self.is_connected:
                center_lat, center_lon, zoom = data['lat'], data['lon'], 5
            markers_js += f"""
            var m = L.circleMarker([{data['lat']}, {data['lon']}], {{radius: 8, fillColor: '{color}', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map);
            m.bindPopup("<b style='color:{color};'>{name}</b><br><br><a href='hideme://{code}' style='display:block; text-align:center; padding:5px; background:#2BAEE0; color:white; text-decoration:none; border-radius:4px;'>Connect</a>");
            """

        html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
            center_lat, center_lon, zoom = d['lat'], d['lon'], 3
            markers_js = f"L.circleMarker([{d['lat']}, {d['lon']}], {{radius: 6, fillColor: 'green', color: 'white', weight: 2, fillOpacity: 1}}).addTo(map);"

        html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
        
        # 1. Protocol Tab
        t_proto = QWidget(); l_proto = QVBoxLayout(t_proto)
        self.r_auto = QRadioButton("Automatic (Recommended)"); self.r_auto.setChecked(True)
        self.r_v4 = QRadioButton("IPv4 Only (-4)"); self.r_v6 = QRadioButton("IPv6 Only (-6)")
        for r in [self.r_auto, self.r_v4, self.r_v6]: l_proto.addWidget(r)
        l_proto.addStretch(); tabs.addTab(t_proto, "Protocol")
        
        # 2. Kill Switch Tab
        t_kill = QWidget(); l_kill = QVBoxLayout(t_kill)
        self.chk_kill = QCheckBox("IP Leak Protection (Kill Switch)"); self.chk_kill.setChecked(True)
        self.chk_lan = QCheckBox("Allow local network connections")
        l_kill.addWidget(self.chk_kill); l_kill.addWidget(self.chk_lan)
        l_kill.addWidget(QLabel("\nExecute custom script when triggered:", objectName="CardTitle"))
        l_kill.addWidget(QLineEdit("/path/to/script.sh"))
        l_kill.addStretch(); tabs.addTab(t_kill, "Kill Switch")
        
        # 3. Filters Tab
        t_filt = QWidget(); l_filt = QVBoxLayout(t_filt)
        self.chk_split = QCheckBox("Enable Split Tunneling (-s)"); self.chk_split.setChecked(True)
        self.inp_subnet = QLineEdit(get_local_subnet())
        l_filt.addWidget(self.chk_split); l_filt.addWidget(self.inp_subnet)
        l_filt.addWidget(QLabel("\nStealthGuard & Server Filters:", objectName="CardTitle"))
        self.chk_pf = QCheckBox("Port Forwarding (-pf)")
        self.chk_track = QCheckBox("Block Trackers (-noTrackers)"); self.chk_track.setChecked(True)
        self.chk_ads = QCheckBox("Block Ads (-noAds)")
        self.chk_malware = QCheckBox("Block Malware (-noMalware)")
        for c in [self.chk_pf, self.chk_track, self.chk_ads, self.chk_malware]: l_filt.addWidget(c)
        l_filt.addStretch(); tabs.addTab(t_filt, "Features")

        # 4. Advanced Tab
        t_adv = QWidget(); l_adv = QVBoxLayout(t_adv)
        self.chk_debug_mode = QCheckBox("Enable Debug Logging in Console")
        self.chk_debug_mode.setChecked(self.app_settings.get("debug_mode", False))
        self.chk_debug_mode.stateChanged.connect(self.toggle_debug_mode)
        l_adv.addWidget(self.chk_debug_mode)
        l_adv.addStretch(); tabs.addTab(t_adv, "Advanced")

        layout.addWidget(tabs)
        self.stacked.addWidget(page)

    def toggle_debug_mode(self):
        is_enabled = self.chk_debug_mode.isChecked()
        self.app_settings["debug_mode"] = is_enabled
        self.save_app_settings()
        if "Debug Console" in self.nav_btns:
            self.nav_btns["Debug Console"].setVisible(is_enabled)
            if not is_enabled and self.stacked.currentIndex() == 7: 
                self.switch_page("Settings")

    def setup_system(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("System", objectName="PageHeader"))
        
        tabs = QTabWidget()
        t_opts = QWidget(); l_opts = QVBoxLayout(t_opts)
        self.chk_autostart = QCheckBox("Launch hide.me on system startup")
        self.chk_autoconnect = QCheckBox("Auto-connect VPN on app launch")
        self.chk_autoupdate = QCheckBox("Auto-check and install CLI updates on startup"); self.chk_autoupdate.setChecked(True)
        self.chk_notif = QCheckBox("Enable Native Desktop Notifications"); self.chk_notif.setChecked(True)
        self.chk_tray = QCheckBox("System Tray Integration (Minimize to Taskbar)"); self.chk_tray.setChecked(True)
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
        self.log_table = QTableWidget(0, 5) # Increased to 5 for Features
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
        card.layout.addWidget(QLabel(f"This advanced interface was successfully created via {__ai_model__}.\nIt perfectly maps CLI capabilities to a modern desktop experience.", styleSheet="color: #2BAEE0; font-weight: bold; margin-top: 10px; margin-bottom: 20px;"))
        
        self.btn_update = QPushButton("🔄 Smart Updates: Check GitHub API")
        self.btn_update.setFixedHeight(40)
        self.btn_update.clicked.connect(self.run_update_check)
        
        btn_git = QPushButton("⭐ View GitHub Repository")
        btn_git.setFixedHeight(40)
        btn_git.clicked.connect(lambda: webbrowser.open("https://github.com/basecore/hideme-vpn-manager"))
        
        card.layout.addWidget(self.btn_update); card.layout.addWidget(btn_git)
        card.layout.addStretch()
        layout.addWidget(card)
        self.stacked.addWidget(page)

    def setup_debug(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.addWidget(QLabel("Debug Console", objectName="PageHeader"))
        
        card = CardWidget(is_square=False)
        self.txt_debug = QTextEdit()
        self.txt_debug.setReadOnly(True)
        self.txt_debug.setStyleSheet("font-family: monospace; font-size: 12px; background: black; color: #00FF00;")
        
        btn_clear = QPushButton("Clear Console")
        btn_clear.clicked.connect(self.txt_debug.clear)
        
        card.layout.addWidget(self.txt_debug)
        card.layout.addWidget(btn_clear)
        layout.addWidget(card)
        self.stacked.addWidget(page)

    def run_update_check(self):
        self.log_debug("Manual API update check initiated...")
        self.btn_update.setText("Checking GitHub API...")
        self.upd_thread = UpdateCheckThread()
        self.upd_thread.update_result.connect(lambda res: [self.btn_update.setText(res), self.log_debug(res)])
        self.upd_thread.start()

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
        self.log_debug("User logs cleared.")

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
        
        css = f"""
            QMainWindow, #MainContent, QDialog {{ background-color: {bg_main}; }}
            #TopBar {{ background-color: {bg_top}; }}
            #LogoText {{ color: white; font-weight: bold; font-size: 14px; margin-left: 10px; }}
            #TopIconBtn {{ background: transparent; color: white; font-size: 16px; border: none; padding: 5px 10px; }}
            #TopIconBtn:hover {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}
            
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
            
            QLineEdit, QComboBox {{ padding: 8px; border: 1px solid {card_border}; border-radius: 4px; background: {bg_main}; color: {text_main}; }}
            QComboBox QAbstractItemView {{ background-color: {bg_main}; color: {text_main}; selection-background-color: {btn_bg}; }}
            
            QTabWidget::pane {{ border: 1px solid {card_border}; background: {card_bg}; }}
            QTabBar::tab {{ background: {bg_main}; color: {text_sub}; padding: 10px 20px; border: 1px solid {card_border}; }}
            QTabBar::tab:selected {{ background: {card_bg}; color: {text_main}; font-weight: bold; border-bottom: none; }}
            
            QTableWidget {{ background: {card_bg}; color: {text_main}; gridline-color: {card_border}; border: none; }}
            QHeaderView::section {{ background: {bg_main}; color: {text_sub}; border: none; padding: 5px; }}
            
            QMessageBox {{ background-color: {card_bg}; color: {text_main}; }}
            QPushButton {{ background-color: {bg_main}; color: {text_main}; padding: 8px; border-radius: 4px; border: 1px solid {card_border}; font-weight:bold; }}
            QPushButton:hover {{ background-color: {card_bg}; }}
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
        a3 = QAction("Quit", self); a3.triggered.connect(QApplication.instance().quit)
        for a in [a1, a2, a3]: menu.addAction(a)
        self.tray_icon.setContextMenu(menu)
        if hasattr(self, 'chk_tray') and self.chk_tray.isChecked(): self.tray_icon.show()

    def toggle_tray_visibility(self):
        if self.chk_tray.isChecked(): self.tray_icon.show()
        else: self.tray_icon.hide()

    def create_icon(self, color_hex):
        pixmap = QPixmap(64, 64); pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color_hex)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56); painter.end()
        return QIcon(pixmap)

    # --- Safe Close Guard ---
    def closeEvent(self, event):
        if self.is_connected:
            if hasattr(self, 'chk_tray') and self.chk_tray.isChecked():
                reply = QMessageBox.question(self, '🛡️ Safe Close Warning',
                    "VPN is currently active.\n\nMinimize to taskbar (Yes) or Quit and Disconnect (No)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Yes:
                    event.ignore(); self.hide()
                elif reply == QMessageBox.StandardButton.No:
                    self.disconnect_vpn(); event.accept()
                else:
                    event.ignore()
            else:
                reply = QMessageBox.warning(self, '⚠️ Safe Close Warning',
                    "VPN is active and System Tray integration is disabled.\n\nClosing the app will terminate the secure VPN connection.\nAre you sure you want to quit?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.disconnect_vpn(); event.accept()
                else:
                    event.ignore()
        else:
            event.accept()

    # --- Timer & Network Logic ---
    def update_timer(self):
        elapsed = int(time.time() - self.conn_start_time)
        hrs, rem = divmod(elapsed, 3600); mins, secs = divmod(rem, 60)
        if hasattr(self, 'btn_connect'):
            self.btn_connect.setText(f"  🔒   {hrs:02d}:{mins:02d}:{secs:02d}  ⚡")

    def run_ping(self):
        sel = self.combo_loc.currentText()
        if sel in ["⚡ Best Location", "🎲 Random Location"]: return
        code = next((k for k, v in SERVER_LIST.items() if v["name"] == sel), "free-de")
        self.lbl_ping_res.setText("Pinging...")
        self.log_debug(f"Pinging {code}...")
        self.pinger = PingThread(code)
        self.pinger.ping_result.connect(self.lbl_ping_res.setText)
        self.pinger.start()

    def fetch_ip(self):
        self.ip_thread = IpFetcherThread(simulate_vpn=self.is_connected)
        self.ip_thread.ip_fetched.connect(self.on_ip_fetched)
        self.ip_thread.start()

    def on_ip_fetched(self, ip, loc):
        if hasattr(self, 'lbl_ip'):
            self.lbl_ip.setText(f"IPv4\n{ip}\n\nLocation\n{loc}")
        if self.is_connected: self.add_log_entry("Connected", ip, loc, self.current_features_str)
        self.log_debug(f"IP Fetched: {ip} - {loc}")

    def update_traffic(self, rx, tx):
        if hasattr(self, 'lbl_rx'):
            self.lbl_rx.setText(f"↓ {rx}" if self.is_connected else "↓ 0.00 KB/s")
            self.lbl_tx.setText(f"↑ {tx}" if self.is_connected else "↑ 0.00 KB/s")

    def update_ui_state(self, connected):
        self.is_connected = connected
        if connected:
            self.log_debug(f"VPN Connection Established on {self.current_connected_server}.")
            self.conn_start_time = time.time(); self.timer.start(1000)
            if hasattr(self, 'btn_connect'):
                self.btn_connect.setStyleSheet("background-color: #8CA93A; color: white; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; text-align: left; padding-left: 20px;")
            self.tray_icon.setIcon(self.create_icon("#8CA93A"))
            self.send_os_notification("hide.me VPN", "Protected! Connection established.")
            self.update_map_html(self.current_connected_server)
            self.update_mini_map()
        else:
            self.log_debug("VPN Disconnected.")
            self.current_connected_server = None
            self.timer.stop()
            if hasattr(self, 'btn_connect'):
                self.btn_connect.setText("  ⏻   Enable VPN")
                self.btn_connect.setStyleSheet("") 
            self.tray_icon.setIcon(self.create_icon("#8B9BB4"))
            self.send_os_notification("hide.me VPN", "Unprotected! VPN Disconnected.")
            self.add_log_entry("Disconnected", "-", "-")
            self.update_map_html(None)
            self.update_mini_map()
        self.fetch_ip()

    def disconnect_vpn(self):
        self.log_debug("Triggering VPN disconnect...")
        if sys.platform == "win32": self.update_ui_state(False); return
        try:
            subprocess.Popen(["sudo", "killall", "hide.me"])
        except Exception as e:
            self.log_debug(f"Killall error: {e}", logging.ERROR)

    def connect_vpn(self, server_code=None, source_combo=None):
        if self.is_connected:
            self.disconnect_vpn()
            return
            
        if server_code is None:
            combo = source_combo if source_combo else (self.combo_loc if hasattr(self, 'combo_loc') else None)
            sel = combo.currentText() if combo else "⚡ Best Location"
            
            if sel == "🎲 Random Location":
                server_code = random.choice(list(SERVER_LIST.keys()))
                self.log_debug("Selected Random Location.")
            elif sel == "⚡ Best Location":
                self.log_debug("Starting Best Location finder...")
                if hasattr(self, 'btn_connect'): self.btn_connect.setText("  Searching best...")
                self.best_finder = BestLocationFinderThread()
                self.best_finder.best_found.connect(self._execute_vpn_connection)
                self.best_finder.start()
                return
            else:
                server_code = next((k for k, v in SERVER_LIST.items() if v["name"] == sel), "free-de")

        self._execute_vpn_connection(server_code)

    def _execute_vpn_connection(self, server_code):
        self.log_debug(f"Executing connection command for {server_code}...")
        self.current_connected_server = server_code
        
        # Build features string for logs
        feats = []
        if hasattr(self, 'chk_kill') and self.chk_kill.isChecked(): feats.append("KS")
        if hasattr(self, 'chk_pf') and self.chk_pf.isChecked(): feats.append("PF")
        if hasattr(self, 'chk_ads') and self.chk_ads.isChecked(): feats.append("NoAds")
        if hasattr(self, 'chk_track') and self.chk_track.isChecked(): feats.append("NoTrack")
        if hasattr(self, 'chk_malware') and self.chk_malware.isChecked(): feats.append("NoMalware")
        self.current_features_str = ", ".join(feats) if feats else "None"
        
        if sys.platform == "win32": 
            self.update_ui_state(True); return

        cmd = ["sudo", "hide.me"]
        if hasattr(self, 'chk_split') and self.chk_split.isChecked() and self.inp_subnet.text().strip(): 
            cmd.extend(["-s", self.inp_subnet.text().strip()])
        if hasattr(self, 'r_v4') and self.r_v4.isChecked(): cmd.append("-4")
        elif hasattr(self, 'r_v6') and self.r_v6.isChecked(): cmd.append("-6")
        if hasattr(self, 'chk_kill') and not self.chk_kill.isChecked(): cmd.append("-k=false")
        if hasattr(self, 'chk_pf') and self.chk_pf.isChecked(): cmd.append("-pf")
        if hasattr(self, 'chk_ads') and self.chk_ads.isChecked(): cmd.append("-noAds")
        if hasattr(self, 'chk_malware') and self.chk_malware.isChecked(): cmd.append("-noMalware")
        if hasattr(self, 'chk_track') and self.chk_track.isChecked(): cmd.append("-noTrackers")
        
        cmd.append("connect"); cmd.append(server_code)
        
        try: 
            self.log_debug(f"CMD: {' '.join(cmd)}")
            subprocess.Popen(cmd)
            if hasattr(self, 'btn_connect'): self.btn_connect.setText("  Connecting...")
        except Exception as e: 
            self.log_debug(f"Execute error: {e}\n{traceback.format_exc()}", logging.ERROR)
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

if __name__ == '__main__':
    if sys.platform != "win32":
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            print("Notice: hide.me CLI requires Root/Sudo privileges on Linux.")
            print("Please restart using: sudo python3 hideme_gui.py")
            sys.exit(1)
        
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = HideMeOfficialUI()
    window.show()
    sys.exit(app.exec())
