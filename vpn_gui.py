#!/usr/bin/env python3
# ==============================================================================
# hide.me VPN Manager GUI - Ultimate Monitor Edition (v16)
# ==============================================================================
__version__ = "16.0.0"
__date__ = "April 15, 2026"
__user__ = "Sebastian Rößer"

import os
import sys
import subprocess
import threading
import time
import shutil
import random
import webbrowser
import pwd
import re
import tkinter as tk
from tkinter import ttk, messagebox

# --- Auto-Install Python Modules ---
def install_and_import(import_name, install_name=None):
    if install_name is None:
        install_name = import_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"Module '{import_name}' not found. Installing automatically...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])
    finally:
        globals()[import_name] = __import__(import_name)

if sys.platform.startswith('linux'):
    install_and_import('requests')
    install_and_import('pystray')
    install_and_import('PIL', 'Pillow')

import pystray
import requests
from PIL import Image, ImageDraw

# --- Configuration Paths ---
CONFIG_DIR = "/etc/hide.me"
VERSION_FILE = os.path.join(CONFIG_DIR, ".gui_version")
AUTO_UPDATE_FILE = os.path.join(CONFIG_DIR, ".auto_update")
AUTO_CONNECT_FILE = os.path.join(CONFIG_DIR, ".auto_connect")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.log")

# --- OS Helpers (Notifications & Autostart) ---
def send_notification(title, message):
    """Sends a native Linux desktop notification using notify-send"""
    try:
        user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
        uid = pwd.getpwnam(user).pw_uid
        # Run as the real user so the notification shows up on their desktop
        cmd = f"sudo -u {user} DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus notify-send '{title}' '{message}' -i network-vpn"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_real_user():
    return os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))

def get_real_home():
    user = get_real_user()
    try:
        return pwd.getpwnam(user).pw_dir
    except:
        return os.path.expanduser('~')

def is_autostart_enabled():
    home = get_real_home()
    desktop_file = os.path.join(home, ".config", "autostart", "hideme-vpn-gui.desktop")
    return os.path.exists(desktop_file)

def setup_autostart(enable):
    user = get_real_user()
    home = get_real_home()
    script_path = os.path.abspath(sys.argv[0])
    python_exe = sys.executable

    desktop_dir = os.path.join(home, ".config", "autostart")
    desktop_file = os.path.join(desktop_dir, "hideme-vpn-gui.desktop")
    sudoers_file = "/etc/sudoers.d/hideme_vpn_gui"

    if enable:
        sudo_rule = f"{user} ALL=(root) NOPASSWD: {python_exe} {script_path}\n"
        try:
            with open(sudoers_file, "w") as f:
                f.write(sudo_rule)
            os.chmod(sudoers_file, 0o440)
            os.makedirs(desktop_dir, exist_ok=True)
            desktop_content = f"[Desktop Entry]\nType=Application\nExec=sudo {python_exe} {script_path}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName=hide.me VPN Manager\nComment=Starts hide.me VPN securely on boot\n"
            with open(desktop_file, "w") as f:
                f.write(desktop_content)
            uid = pwd.getpwnam(user).pw_uid
            gid = pwd.getpwnam(user).pw_gid
            os.chown(desktop_file, uid, gid)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create autostart entry:\n{e}")
    else:
        if os.path.exists(sudoers_file): os.remove(sudoers_file)
        if os.path.exists(desktop_file): os.remove(desktop_file)

def get_auto_update_pref():
    if os.path.exists(AUTO_UPDATE_FILE):
        with open(AUTO_UPDATE_FILE, "r") as f: return f.read().strip().lower() == "true"
    return True 

def save_auto_update_pref(state):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(AUTO_UPDATE_FILE, "w") as f: f.write(str(state))

def get_auto_connect_pref():
    if os.path.exists(AUTO_CONNECT_FILE):
        with open(AUTO_CONNECT_FILE, "r") as f: return f.read().strip().lower() == "true"
    return False

def save_auto_connect_pref(state):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(AUTO_CONNECT_FILE, "w") as f: f.write(str(state))

def get_local_subnet():
    try:
        route_out = subprocess.check_output(["ip", "route"]).decode()
        default_interface = None
        for line in route_out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if "dev" in parts:
                    default_interface = parts[parts.index("dev") + 1]
                break
        if default_interface:
            for line in route_out.splitlines():
                if default_interface in line and "scope link" in line:
                    subnet = line.split()[0]
                    if "/" in subnet: return subnet
    except Exception:
        pass
    return "192.168.178.0/24"


# --- UI Components ---
class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tw, text=self.text, justify='left',
                          background="#0ACCF9", foreground="#000000", relief='flat',
                          font=("Helvetica", 9, "bold"), padding=(8, 5))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw: self.tw.destroy()

class HideMeVPNApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"hide.me VPN Pro - {__user__}")
        self.root.geometry("540x940") # Taller for new traffic info
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.bg_main = "#10151E"
        self.bg_card = "#1A2230"
        self.brand_cyan = "#0ACCF9"
        self.text_white = "#FFFFFF"
        self.text_grey = "#8B9BB4"
        self.color_danger = "#FF4C4C"
        self.color_success = "#2ea043"
        
        self.root.configure(bg=self.bg_main)
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.setup_styles()
        
        # State Variables
        self.status_var = tk.StringVar(value="⚠️ UNPROTECTED")
        self.ip_var = tk.StringVar(value="IP: Loading...")
        self.location_var = tk.StringVar(value="Location: -")
        self.traffic_var = tk.StringVar(value="Traffic: ↓ 0.00 KB/s | ↑ 0.00 KB/s")
        self.ping_var = tk.StringVar(value="Ping: - ms")
        self.last_state = None
        self.last_logged_ip = None
        
        # Traffic Monitor State
        self.last_rx = 0
        self.last_tx = 0
        self.traffic_running = False
        
        # Server Mapping
        self.server_mapping = {
            "🎲 Random Free Server": "Random Free Server",
            "🇩🇪 free-de": "free-de",
            "🇫🇷 free-fr": "free-fr",
            "🇳🇱 free-nl": "free-nl",
            "🇨🇭 free-ch": "free-ch",
            "🇬🇧 free-uk": "free-uk",
            "🇺🇸 free-us": "free-us",
            "🇫🇮 free-fi": "free-fi",
            "🇸🇬 free-sg": "free-sg",
            "⚙️ Custom Server...": "Custom Server..."
        }
        self.free_servers = ["free-de", "free-fr", "free-nl", "free-ch", "free-uk", "free-us", "free-fi", "free-sg"]
        self.server_var = tk.StringVar(value="🎲 Random Free Server")
        
        # Config Variables
        self.split_var = tk.BooleanVar(value=True)       
        self.subnet_var = tk.StringVar(value=get_local_subnet()) 
        self.protocol_var = tk.StringVar(value="Auto")   
        self.pf_var = tk.BooleanVar(value=False)         
        self.killswitch_var = tk.BooleanVar(value=True)  
        
        self.no_ads_var = tk.BooleanVar(value=False)     
        self.no_malware_var = tk.BooleanVar(value=True)  
        self.no_trackers_var = tk.BooleanVar(value=False)
        self.safe_search_var = tk.BooleanVar(value=False)
        self.force_dns_var = tk.BooleanVar(value=False)  
        
        self.use_config_var = tk.BooleanVar(value=False) 
        self.config_path_var = tk.StringVar(value="/etc/hide.me/config.yaml")
        self.use_token_var = tk.BooleanVar(value=False)  
        self.token_path_var = tk.StringVar(value="/etc/hide.me/accessToken.txt")
        self.use_custom_dns_var = tk.BooleanVar(value=False) 
        self.custom_dns_var = tk.StringVar(value="1.1.1.1,1.0.0.1")
        
        self.auto_update_var = tk.BooleanVar(value=get_auto_update_pref())
        self.auto_start_var = tk.BooleanVar(value=is_autostart_enabled())
        self.auto_connect_var = tk.BooleanVar(value=get_auto_connect_pref())
        
        self.build_ui()
        self.setup_tray()
        
        threading.Thread(target=self.monitor_daemon, daemon=True).start()
        
        if self.auto_connect_var.get() and not self.check_process():
            self.root.after(2000, self.connect_vpn)

    # --- System Tray Logic ---
    def create_tray_icon(self, connected):
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if connected:
            draw.ellipse((4, 4, 60, 60), fill=self.brand_cyan)
            draw.line((18, 34, 28, 44), fill="white", width=6)
            draw.line((28, 44, 46, 20), fill="white", width=6)
        else:
            draw.ellipse((6, 6, 58, 58), outline=self.text_grey, width=6)
            draw.line((16, 16, 48, 48), fill=self.text_grey, width=6)
        return image

    def setup_tray(self):
        try:
            self.img_disconnected = self.create_tray_icon(connected=False)
            self.img_connected = self.create_tray_icon(connected=True)
            menu = pystray.Menu(
                pystray.MenuItem("Show / Hide Window", self.toggle_window_from_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Connect VPN", lambda: self.root.after(0, self.connect_vpn)),
                pystray.MenuItem("Disconnect VPN", lambda: self.root.after(0, self.disconnect_vpn)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit App", self.force_quit)
            )
            self.tray_icon = pystray.Icon("HideMeVPN", self.img_disconnected, "hide.me VPN: UNPROTECTED", menu=menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"System Tray not supported or failed to load: {e}")

    def toggle_window_from_tray(self, icon=None, item=None):
        self.root.after(0, self._sync_toggle_window)
        
    def _sync_toggle_window(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self.root.withdraw()

    def force_quit(self, icon=None, item=None):
        self.root.after(0, self._sync_force_quit)

    def _sync_force_quit(self):
        if self.check_process():
            self.disconnect_vpn()
            time.sleep(1.5)
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)

    def on_closing(self):
        if self.check_process():
            res = messagebox.askyesnocancel(
                "Keep Running?",
                "Do you want to CLOSE the application and DISCONNECT the VPN completely?\n\n"
                "Click 'No' to minimize it to the System Tray and keep the VPN running in the background.",
                icon='question'
            )
            if res is True:
                self._sync_force_quit()
            elif res is False:
                self.root.withdraw()
            else:
                return
        else:
            self._sync_force_quit()

    def setup_styles(self):
        self.style.configure('TFrame', background=self.bg_main)
        self.style.configure('Card.TFrame', background=self.bg_card)
        self.style.configure('TLabel', background=self.bg_main, foreground=self.text_white, font=('Helvetica', 10))
        self.style.configure('Card.TLabel', background=self.bg_card, foreground=self.text_white)
        self.style.configure('Brand.TLabel', background=self.bg_main, foreground=self.brand_cyan, font=('Helvetica', 22, 'bold'))
        self.style.configure('Status.TLabel', background=self.bg_card, foreground=self.text_grey, font=('Helvetica', 15, 'bold'))
        self.style.configure('IP.TLabel', background=self.bg_card, foreground=self.brand_cyan, font=('Helvetica', 11, 'bold'))
        self.style.configure('Traffic.TLabel', background=self.bg_card, foreground="#9ca3af", font=('Courier', 10, 'bold')) # Monospace for speed
        self.style.configure('Ping.TLabel', background=self.bg_card, foreground="#fbbf24", font=('Helvetica', 9, 'bold'))
        self.style.configure('TCheckbutton', background=self.bg_card, foreground=self.text_white, font=('Helvetica', 10))
        self.style.map('TCheckbutton', background=[('active', self.bg_card)], indicatorcolor=[('selected', self.brand_cyan)])
        self.style.configure('TRadiobutton', background=self.bg_card, foreground=self.text_white, font=('Helvetica', 10))
        self.style.map('TRadiobutton', background=[('active', self.bg_card)], indicatorcolor=[('selected', self.brand_cyan)])
        self.style.configure('TNotebook', background=self.bg_main, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.bg_card, foreground=self.text_white, padding=[10, 5], font=('Helvetica', 10, 'bold'))
        self.style.map('TNotebook.Tab', background=[('selected', self.brand_cyan)], foreground=[('selected', '#000000')])
        self.style.configure('Connect.TButton', font=('Helvetica', 12, 'bold'), background=self.brand_cyan, foreground="#000000", borderwidth=0)
        self.style.map('Connect.TButton', background=[('active', '#3FE0FF')])
        self.style.configure('Disconnect.TButton', font=('Helvetica', 12, 'bold'), background=self.color_danger, foreground=self.text_white, borderwidth=0)
        self.style.map('Disconnect.TButton', background=[('active', '#FF7373')])
        self.style.configure('Small.TButton', font=('Helvetica', 9, 'bold'), background="#2d3748", foreground=self.text_white)
        self.style.map('Small.TButton', background=[('active', '#4a5568')])
        self.style.configure('Link.TButton', font=('Helvetica', 10, 'bold'), background="#1e293b", foreground=self.brand_cyan)
        self.style.map('Link.TButton', background=[('active', '#334155')])
        self.style.configure("Treeview", background=self.bg_card, foreground=self.text_white, fieldbackground=self.bg_card, borderwidth=0, font=('Helvetica', 9))
        self.style.map('Treeview', background=[('selected', self.brand_cyan)], foreground=[('selected', 'black')])
        self.style.configure("Treeview.Heading", background=self.bg_main, foreground=self.text_grey, font=('Helvetica', 9, 'bold'))

    def build_ui(self):
        # Header
        logo_frame = ttk.Frame(self.root)
        logo_frame.pack(pady=(15, 0))
        ttk.Label(logo_frame, text="hide.me", style='Brand.TLabel').pack(side='left')
        ttk.Label(logo_frame, text=" VPN", font=('Helvetica', 22), foreground=self.text_white, background=self.bg_main).pack(side='left')
        info_text = f"v{__version__} | {__date__} | User: {__user__}"
        ttk.Label(self.root, text=info_text, font=('Helvetica', 9), foreground=self.text_grey).pack(pady=(0, 10))
        
        # Status Card (Now includes Traffic Monitor)
        status_card = ttk.Frame(self.root, style='Card.TFrame')
        status_card.pack(fill='x', padx=20, pady=5, ipady=10)
        self.lbl_status = ttk.Label(status_card, textvariable=self.status_var, style='Status.TLabel', anchor='center')
        self.lbl_status.pack(fill='x', pady=(5, 5))
        ttk.Label(status_card, textvariable=self.ip_var, style='IP.TLabel', anchor='center').pack(fill='x')
        ttk.Label(status_card, textvariable=self.location_var, style='IP.TLabel', foreground=self.text_white, font=('Helvetica', 10), anchor='center').pack(fill='x', pady=(2, 5))
        
        # Traffic Monitor Label
        ttk.Label(status_card, textvariable=self.traffic_var, style='Traffic.TLabel', anchor='center').pack(fill='x', pady=(0, 5))
        
        # Server Selection (Now includes Ping Tester)
        server_card = ttk.Frame(self.root, style='Card.TFrame')
        server_card.pack(fill='x', padx=20, pady=5, ipady=5)
        
        top_srv = ttk.Frame(server_card, style='Card.TFrame')
        top_srv.pack(fill='x', padx=15, pady=(5, 2))
        ttk.Label(top_srv, text="Select Location:", style='Card.TLabel', font=('Helvetica', 10, 'bold'), foreground=self.text_grey).pack(side='left')
        ttk.Label(top_srv, textvariable=self.ping_var, style='Ping.TLabel').pack(side='right')

        bot_srv = ttk.Frame(server_card, style='Card.TFrame')
        bot_srv.pack(fill='x', padx=15, pady=(0, 5))
        ttk.Combobox(bot_srv, textvariable=self.server_var, values=list(self.server_mapping.keys()), font=('Helvetica', 11)).pack(side='left', fill='x', expand=True)
        btn_ping = ttk.Button(bot_srv, text="⚡ Ping", style='Small.TButton', width=6, command=self.test_ping)
        btn_ping.pack(side='right', padx=(10, 0))
        ToolTip(btn_ping, "Test the latency of the selected server.")

        # --- Tabs ---
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=20, pady=5)
        
        # Tab 1: Network
        tab_net = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(tab_net, text="Network")
        split_frame = ttk.Frame(tab_net, style='Card.TFrame')
        split_frame.pack(fill='x', padx=15, pady=(15, 5))
        c1 = ttk.Checkbutton(split_frame, text="Split Tunneling (-s)", variable=self.split_var)
        c1.pack(side='left')
        ttk.Entry(split_frame, textvariable=self.subnet_var, width=18).pack(side='right', fill='x', expand=True, padx=(10,0))
        ToolTip(c1, "Bypass the VPN for local IPs (e.g. Router, NAS).\nYour current subnet is automatically populated.")
        ttk.Checkbutton(tab_net, text="Enable Kill-Switch (-k)", variable=self.killswitch_var).pack(anchor='w', padx=15, pady=5)
        ttk.Checkbutton(tab_net, text="Enable Port-Forwarding (-pf)", variable=self.pf_var).pack(anchor='w', padx=15, pady=5)
        ttk.Label(tab_net, text="Protocol:", style='Card.TLabel', font=('Helvetica', 10, 'bold')).pack(anchor='w', padx=15, pady=(10, 2))
        pf_frame = ttk.Frame(tab_net, style='Card.TFrame')
        pf_frame.pack(fill='x', padx=15)
        ttk.Radiobutton(pf_frame, text="Auto", variable=self.protocol_var, value="Auto").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(pf_frame, text="IPv4 Only (-4)", variable=self.protocol_var, value="IPv4").pack(side='left', padx=10)
        ttk.Radiobutton(pf_frame, text="IPv6 Only (-6)", variable=self.protocol_var, value="IPv6").pack(side='left', padx=10)

        # Tab 2: Filters
        tab_filter = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(tab_filter, text="Filters")
        ttk.Label(tab_filter, text="Note: Filters are processed remotely on the server.", style='Card.TLabel', foreground=self.text_grey).pack(anchor='w', padx=15, pady=(15, 10))
        ttk.Checkbutton(tab_filter, text="Block Ads (-noAds)", variable=self.no_ads_var).pack(anchor='w', padx=15, pady=4)
        ttk.Checkbutton(tab_filter, text="Block Malware (-noMalware)", variable=self.no_malware_var).pack(anchor='w', padx=15, pady=4)
        ttk.Checkbutton(tab_filter, text="Block Trackers (-noTrackers)", variable=self.no_trackers_var).pack(anchor='w', padx=15, pady=4)
        ttk.Checkbutton(tab_filter, text="Force SafeSearch (-safeSearch)", variable=self.safe_search_var).pack(anchor='w', padx=15, pady=4)
        ttk.Checkbutton(tab_filter, text="Force hide.me DNS (-forceDns)", variable=self.force_dns_var).pack(anchor='w', padx=15, pady=4)

        # Tab 3: Advanced
        tab_adv = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(tab_adv, text="Advanced")
        f1 = ttk.Frame(tab_adv, style='Card.TFrame')
        f1.pack(fill='x', padx=15, pady=(15, 5))
        ttk.Checkbutton(f1, text="Custom Config (-c)", variable=self.use_config_var).pack(side='left')
        ttk.Entry(f1, textvariable=self.config_path_var, width=15).pack(side='right', fill='x', expand=True, padx=(10,0))
        f2 = ttk.Frame(tab_adv, style='Card.TFrame')
        f2.pack(fill='x', padx=15, pady=5)
        ttk.Checkbutton(f2, text="Token Path (-t)", variable=self.use_token_var).pack(side='left')
        ttk.Entry(f2, textvariable=self.token_path_var, width=15).pack(side='right', fill='x', expand=True, padx=(10,0))
        f3 = ttk.Frame(tab_adv, style='Card.TFrame')
        f3.pack(fill='x', padx=15, pady=5)
        ttk.Checkbutton(f3, text="Custom DNS (-d)", variable=self.use_custom_dns_var).pack(side='left')
        ttk.Entry(f3, textvariable=self.custom_dns_var, width=15).pack(side='right', fill='x', expand=True, padx=(10,0))
        f5 = ttk.Frame(tab_adv, style='Card.TFrame')
        f5.pack(fill='x', padx=15, pady=(15, 5))
        c_auto = ttk.Checkbutton(f5, text="Launch on system startup", variable=self.auto_start_var, command=self.toggle_auto_start)
        c_auto.pack(side='left')
        f6 = ttk.Frame(tab_adv, style='Card.TFrame')
        f6.pack(fill='x', padx=15, pady=5)
        c_conn = ttk.Checkbutton(f6, text="Auto-connect on launch", variable=self.auto_connect_var, command=self.toggle_auto_connect)
        c_conn.pack(side='left')
        
        # Tab 4: History
        tab_history = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(tab_history, text="History")
        tree_frame = ttk.Frame(tab_history)
        tree_frame.pack(fill='both', expand=True, padx=15, pady=(15, 5))
        cols = ("Time", "Status", "IP", "Location")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=8)
        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("Status", text="Status")
        self.history_tree.heading("IP", text="IP")
        self.history_tree.heading("Location", text="Location")
        self.history_tree.column("Time", width=120, anchor='center')
        self.history_tree.column("Status", width=110, anchor='center')
        self.history_tree.column("IP", width=100, anchor='center')
        self.history_tree.column("Location", width=110, anchor='center')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        ttk.Button(tab_history, text="Clear History", style='Small.TButton', command=self.clear_history).pack(pady=(5, 10))
        self.load_history()

        # Tab 5: About
        tab_about = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(tab_about, text="About")
        ttk.Label(tab_about, text="hideme-vpn-manager", font=('Helvetica', 14, 'bold'), style='Card.TLabel').pack(pady=(20, 5))
        ttk.Label(tab_about, text="Powered by Python & Gemini 3.1 Pro Thinking", style='Card.TLabel', foreground=self.text_grey).pack(pady=(0, 20))
        def open_repo(): webbrowser.open("https://github.com/basecore/hideme-vpn-manager/tree/main")
        def open_issues(): webbrowser.open("https://github.com/basecore/hideme-vpn-manager/issues")
        ttk.Button(tab_about, text="⭐ View GitHub Repository", style='Link.TButton', command=open_repo).pack(pady=5, padx=30, fill='x', ipady=5)
        ttk.Button(tab_about, text="🐛 Report an Issue", style='Link.TButton', command=open_issues).pack(pady=5, padx=30, fill='x', ipady=5)

        # Footer Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=20, pady=15)
        ttk.Button(btn_frame, text="CONNECT", style='Connect.TButton', command=self.connect_vpn).pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=12)
        ttk.Button(btn_frame, text="DISCONNECT", style='Disconnect.TButton', command=self.disconnect_vpn).pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=12)

    # --- Feature: History Log ---
    def log_history(self, status, ip, location):
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        log_entry = f"{timestamp}|{status}|{ip}|{location}\n"
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(HISTORY_FILE, "a") as f: f.write(log_entry)
            self.root.after(0, lambda: self.history_tree.insert("", 0, values=(timestamp, status, ip, location)))
        except:
            pass

    def load_history(self):
        for item in self.history_tree.get_children(): self.history_tree.delete(item)
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    for line in f.readlines():
                        parts = line.strip().split('|')
                        if len(parts) == 4:
                            self.history_tree.insert("", 0, values=(parts[0], parts[1], parts[2], parts[3]))
            except:
                pass

    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to delete all connection logs?"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            self.load_history()

    # --- Feature: Ping Tester ---
    def test_ping(self):
        """Pings the selected hide.me server to measure latency"""
        self.ping_var.set("Ping: Testing...")
        srv_display = self.server_var.get().strip()
        srv = self.server_mapping.get(srv_display, srv_display)
        
        if srv == "Random Free Server" or srv == "Custom Server...":
            self.ping_var.set("Ping: N/A")
            return
            
        def run_ping():
            try:
                # E.g. "free-de" -> "free-de.hideservers.net"
                host = f"{srv}.hideservers.net"
                # Ping 3 times, wait 1 second max
                cmd = ["ping", "-c", "3", "-W", "1", host]
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
                # Parse average ping from "rtt min/avg/max/mdev = 23.4/24.1/25.0/0.8 ms"
                match = re.search(r'min/avg/max/mdev = [\d\.]+/(.*?)/', output)
                if match:
                    avg_ms = float(match.group(1))
                    self.ping_var.set(f"Ping: {int(avg_ms)} ms")
                else:
                    self.ping_var.set("Ping: Failed")
            except Exception:
                self.ping_var.set("Ping: Failed")
                
        threading.Thread(target=run_ping, daemon=True).start()

    # --- Feature: Live Traffic Monitor ---
    def get_network_bytes(self):
        """Reads total RX and TX bytes from all VPN-like interfaces"""
        try:
            rx_bytes = 0
            tx_bytes = 0
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
                for line in lines[2:]:
                    parts = line.split()
                    iface = parts[0].strip(':')
                    # hide.me CLI usually creates 'tun0', 'tun1', etc.
                    if iface.startswith('tun') or 'hide' in iface:
                        rx_bytes += int(parts[1])
                        tx_bytes += int(parts[9])
            return rx_bytes, tx_bytes
        except:
            return 0, 0

    def monitor_traffic(self):
        """Background thread updating the download/upload speed labels"""
        self.traffic_running = True
        self.last_rx, self.last_tx = self.get_network_bytes()
        
        while self.traffic_running:
            time.sleep(1)
            current_rx, current_tx = self.get_network_bytes()
            
            # Calculate bytes per second
            rx_speed = current_rx - self.last_rx
            tx_speed = current_tx - self.last_tx
            
            self.last_rx = current_rx
            self.last_tx = current_tx
            
            # Formatting (KB/s or MB/s)
            if rx_speed > 1048576: rx_str = f"{rx_speed/1048576:.2f} MB/s"
            else: rx_str = f"{rx_speed/1024:.2f} KB/s"
            
            if tx_speed > 1048576: tx_str = f"{tx_speed/1048576:.2f} MB/s"
            else: tx_str = f"{tx_speed/1024:.2f} KB/s"
            
            self.traffic_var.set(f"Traffic: ↓ {rx_str} | ↑ {tx_str}")

    # --- Toggles & Network Core ---
    def toggle_auto_start(self): setup_autostart(self.auto_start_var.get())
    def toggle_auto_connect(self): save_auto_connect_pref(self.auto_connect_var.get())

    def check_process(self):
        try: return subprocess.run(['pgrep', '-x', 'hide.me'], stdout=subprocess.DEVNULL).returncode == 0
        except Exception: return False

    def monitor_daemon(self):
        while True:
            is_running = self.check_process()
            if is_running != self.last_state:
                self.last_state = is_running
                if is_running:
                    # VPN CONNECTED
                    self.status_var.set("🛡️ PROTECTED")
                    self.lbl_status.configure(foreground=self.color_success)
                    send_notification("hide.me VPN", "Connection established! You are now protected.")
                    
                    if hasattr(self, 'tray_icon'):
                        self.tray_icon.icon = self.img_connected
                        self.tray_icon.title = "hide.me VPN: PROTECTED"
                        
                    # Start Traffic Monitor
                    if not self.traffic_running:
                        threading.Thread(target=self.monitor_traffic, daemon=True).start()
                        
                    self.fetch_ip_async(connected=True)
                else:
                    # VPN DISCONNECTED
                    self.status_var.set("⚠️ UNPROTECTED")
                    self.lbl_status.configure(foreground=self.color_danger)
                    self.traffic_running = False
                    self.traffic_var.set("Traffic: ↓ 0.00 KB/s | ↑ 0.00 KB/s")
                    send_notification("hide.me VPN", "Disconnected. You are no longer protected.")
                    
                    if hasattr(self, 'tray_icon'):
                        self.tray_icon.icon = self.img_disconnected
                        self.tray_icon.title = "hide.me VPN: UNPROTECTED"
                        
                    self.fetch_ip_async(connected=False)
            time.sleep(2)

    def fetch_ip_async(self, connected):
        def task():
            if connected: time.sleep(4)
            self.ip_var.set("Searching IP...")
            self.location_var.set("Location: Loading...")
            try:
                resp = requests.get("https://ipinfo.io/json", timeout=5)
                data = resp.json()
                ip_str = data.get('ip', 'Unknown')
                loc_str = f"{data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}"
                
                self.ip_var.set(f"Your IP: {ip_str}")
                self.location_var.set(f"Location: {loc_str}")
                
                status_str = "🛡️ PROTECTED" if connected else "⚠️ UNPROTECTED"
                if self.last_logged_ip != ip_str:
                    self.last_logged_ip = ip_str
                    self.log_history(status_str, ip_str, loc_str)
            except Exception:
                self.ip_var.set("IP: Could not be checked")
                self.location_var.set("Location: Unknown")
        threading.Thread(target=task, daemon=True).start()

    def connect_vpn(self):
        cmd = ["sudo", "hide.me"]
        if self.split_var.get() and self.subnet_var.get().strip(): cmd.extend(["-s", self.subnet_var.get().strip()])
        if self.protocol_var.get() == "IPv4": cmd.append("-4")
        elif self.protocol_var.get() == "IPv6": cmd.append("-6")
        if self.pf_var.get(): cmd.append("-pf")
        if not self.killswitch_var.get(): cmd.append("-k=false")
        if self.no_ads_var.get(): cmd.append("-noAds")
        if self.no_malware_var.get(): cmd.append("-noMalware")
        if self.no_trackers_var.get(): cmd.append("-noTrackers")
        if self.safe_search_var.get(): cmd.append("-safeSearch")
        if self.force_dns_var.get(): cmd.append("-forceDns")
        if self.use_config_var.get() and self.config_path_var.get(): cmd.extend(["-c", self.config_path_var.get()])
        if self.use_token_var.get() and self.token_path_var.get(): cmd.extend(["-t", self.token_path_var.get()])
        if self.use_custom_dns_var.get() and self.custom_dns_var.get(): cmd.extend(["-d", self.custom_dns_var.get()])

        cmd.append("connect")
        srv_display = self.server_var.get().strip()
        srv = self.server_mapping.get(srv_display, srv_display)
        if srv == "Custom Server...":
            messagebox.showwarning("Notice", "Please enter a valid server name.")
            return
        elif srv == "Random Free Server":
            srv = random.choice(self.free_servers)
        cmd.append(srv)
        
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start VPN:\n{e}")

    def disconnect_vpn(self):
        subprocess.Popen(["sudo", "killall", "hide.me"])

if __name__ == "__main__":
    if not sys.platform.startswith('linux'):
        print("Error: This tool is for Linux only.")
        sys.exit(1)
    
    if os.geteuid() != 0:
        print("Notice: This script requires Root/Sudo privileges.")
        print("Please start it using: sudo python3 vpn_gui.py")
        sys.exit(1)
        
    root = tk.Tk()
    root.deiconify()
    app = HideMeVPNApp(root)
    root.mainloop()
