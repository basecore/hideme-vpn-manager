#!/usr/bin/env python3
# ==============================================================================
# hide.me VPN Manager GUI - History Log & System Tray Edition
# ==============================================================================
__version__ = "15.0.0"
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
from PIL import Image, ImageDraw

# --- Configuration Paths ---
CONFIG_DIR = "/etc/hide.me"
VERSION_FILE = os.path.join(CONFIG_DIR, ".gui_version")
AUTO_UPDATE_FILE = os.path.join(CONFIG_DIR, ".auto_update")
AUTO_CONNECT_FILE = os.path.join(CONFIG_DIR, ".auto_connect")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.log")

# --- User & Autostart Logic ---
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
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create sudoers rule:\n{e}")
            return

        os.makedirs(desktop_dir, exist_ok=True)
        desktop_content = f"""[Desktop Entry]
Type=Application
Exec=sudo {python_exe} {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=hide.me VPN Manager
Comment=Starts hide.me VPN securely on boot
"""
        try:
            with open(desktop_file, "w") as f:
                f.write(desktop_content)
            uid = pwd.getpwnam(user).pw_uid
            gid = pwd.getpwnam(user).pw_gid
            os.chown(desktop_file, uid, gid)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create autostart entry:\n{e}")
    else:
        if os.path.exists(sudoers_file):
            os.remove(sudoers_file)
        if os.path.exists(desktop_file):
            os.remove(desktop_file)

# --- App Config Settings ---
def get_auto_update_pref():
    if os.path.exists(AUTO_UPDATE_FILE):
        with open(AUTO_UPDATE_FILE, "r") as f:
            return f.read().strip().lower() == "true"
    return True 

def save_auto_update_pref(state):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(AUTO_UPDATE_FILE, "w") as f:
        f.write(str(state))

def get_auto_connect_pref():
    if os.path.exists(AUTO_CONNECT_FILE):
        with open(AUTO_CONNECT_FILE, "r") as f:
            return f.read().strip().lower() == "true"
    return False

def save_auto_connect_pref(state):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(AUTO_CONNECT_FILE, "w") as f:
        f.write(str(state))

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
                    if "/" in subnet:
                        return subnet
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
        if self.tw:
            self.tw.destroy()

class HideMeVPNApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"hide.me VPN Pro - {__user__}")
        self.root.geometry("540x880")
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
        
        self.status_var = tk.StringVar(value="⚠️ UNPROTECTED")
        self.ip_var = tk.StringVar(value="IP: Loading...")
        self.location_var = tk.StringVar(value="Location: -")
        self.last_state = None
        self.last_logged_ip = None
        
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
        
        # Variables
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
        
        # Persistent Preferences
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
        
        # Treeview (History Table) Styling
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
        
        # Status Card
        status_card = ttk.Frame(self.root, style='Card.TFrame')
        status_card.pack(fill='x', padx=20, pady=5, ipady=10)
        self.lbl_status = ttk.Label(status_card, textvariable=self.status_var, style='Status.TLabel', anchor='center')
        self.lbl_status.pack(fill='x', pady=(5, 5))
        ttk.Label(status_card, textvariable=self.ip_var, style='IP.TLabel', anchor='center').pack(fill='x')
        ttk.Label(status_card, textvariable=self.location_var, style='IP.TLabel', foreground=self.text_white, font=('Helvetica', 10), anchor='center').pack(fill='x', pady=(2, 0))
        
        # Server Selection
        server_card = ttk.Frame(self.root, style='Card.TFrame')
        server_card.pack(fill='x', padx=20, pady=5, ipady=5)
        ttk.Label(server_card, text="Select Location:", style='Card.TLabel', font=('Helvetica', 10, 'bold'), foreground=self.text_grey).pack(anchor='w', padx=15, pady=(5, 2))
        ttk.Combobox(server_card, textvariable=self.server_var, values=list(self.server_mapping.keys()), font=('Helvetica', 11)).pack(fill='x', padx=15, pady=(0, 5))

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
        
