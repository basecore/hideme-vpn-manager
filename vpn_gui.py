#!/usr/bin/env python3
# ==============================================================================
# hide.me VPN Manager GUI - Autostart & Auto-Connect Edition
# ==============================================================================
__version__ = "12.0.0"
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
def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Module '{package}' not found. Installing automatically...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    finally:
        globals()[package] = __import__(package)

if sys.platform.startswith('linux'):
    install_and_import('requests')

# --- Configuration Paths ---
CONFIG_DIR = "/etc/hide.me"
VERSION_FILE = os.path.join(CONFIG_DIR, ".gui_version")
AUTO_UPDATE_FILE = os.path.join(CONFIG_DIR, ".auto_update")
AUTO_CONNECT_FILE = os.path.join(CONFIG_DIR, ".auto_connect")

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
        # Create a passwordless sudo rule for this specific script
        sudo_rule = f"{user} ALL=(root) NOPASSWD: {python_exe} {script_path}\n"
        try:
            with open(sudoers_file, "w") as f:
                f.write(sudo_rule)
            os.chmod(sudoers_file, 0o440)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create sudoers rule:\n{e}")
            return

        # Create the autostart entry for the user
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
            # Ensure the real user owns their autostart file
            uid = pwd.getpwnam(user).pw_uid
            gid = pwd.getpwnam(user).pw_gid
            os.chown(desktop_file, uid, gid)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create autostart entry:\n{e}")
    else:
        # Remove both files if disabling
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

def check_for_updates(manual=False):
    try:
        resp = requests.get("https://api.github.com/repos/eventure/hide.client.linux/releases/latest", timeout=3)
        if resp.status_code == 200:
            latest_tag = resp.json().get("tag_name", "").lstrip("v")
            local_ver = "0.0.0"
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    local_ver = f.read().strip()
            
            if latest_tag and latest_tag != local_ver:
                ans = messagebox.askyesno(
                    "Update Available", 
                    f"A new version of hide.me VPN ({latest_tag}) is available!\nYour version: {local_ver}\n\nDo you want to download and install it automatically?"
                )
                if ans:
                    run_hideme_installer()
                    messagebox.showinfo("Update Complete", "hide.me has been updated successfully!\n\nPlease restart the application.")
                    sys.exit(0)
                else:
                    if not manual:
                        os.makedirs(CONFIG_DIR, exist_ok=True)
                        with open(VERSION_FILE, "w") as f:
                            f.write(latest_tag)
            else:
                if manual:
                    messagebox.showinfo("Up to Date", f"You are already using the latest version ({local_ver}).")
    except Exception as e:
        pass


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
        self.root.geometry("480x880")
        
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
        
        self.status_var = tk.StringVar(value="🔴 UNPROTECTED")
        self.ip_var = tk.StringVar(value="IP: Loading...")
        self.location_var = tk.StringVar(value="Location: -")
        self.last_state = None
        
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
        threading.Thread(target=self.monitor_daemon, daemon=True).start()
        
        # --- AUTO-CONNECT LOGIC ---
        if self.auto_connect_var.get() and not self.check_process():
            # Wait 2 seconds for UI and network stack to settle before connecting
            self.root.after(2000, self.connect_vpn)

    def on_closing(self):
        if self.check_process():
            res = messagebox.askyesno(
                "Disconnect VPN?",
                "Closing the application will DISCONNECT your VPN and leave your internet traffic unprotected.\n\nAre you sure you want to close and browse unprotected?",
                icon='warning'
            )
            if res:
                print("Closing application: Disconnecting VPN safely...")
                self.disconnect_vpn()
                time.sleep(1.5)
                self.root.destroy()
                sys.exit(0)
            else:
                return 
        else:
            self.root.destroy()
            sys.exit(0)

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

        # Tab 2: Security & Filters
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

        # --- Automation Switches ---
        f4 = ttk.Frame(tab_adv, style='Card.TFrame')
        f4.pack(fill='x', padx=15, pady=(15, 5))
        c_up = ttk.Checkbutton(f4, text="Check updates on start", variable=self.auto_update_var, command=self.toggle_auto_update)
        c_up.pack(side='left')
        ttk.Button(f4, text="Check Now", style='Small.TButton', command=lambda: check_for_updates(manual=True)).pack(side='right', padx=(10,0))
        
        f5 = ttk.Frame(tab_adv, style='Card.TFrame')
        f5.pack(fill='x', padx=15, pady=5)
        c_auto = ttk.Checkbutton(f5, text="Launch on system startup", variable=self.auto_start_var, command=self.toggle_auto_start)
        c_auto.pack(side='left')
        ToolTip(c_auto, "Creates a secure sudoers rule so this app can start automatically\nin the background without asking for your password.")

        f6 = ttk.Frame(tab_adv, style='Card.TFrame')
        f6.pack(fill='x', padx=15, pady=5)
        c_conn = ttk.Checkbutton(f6, text="Auto-connect on launch", variable=self.auto_connect_var, command=self.toggle_auto_connect)
        c_conn.pack(side='left')

        # Tab 4: About / Info
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

    def toggle_auto_update(self):
        save_auto_update_pref(self.auto_update_var.get())

    def toggle_auto_start(self):
        setup_autostart(self.auto_start_var.get())
        
    def toggle_auto_connect(self):
        save_auto_connect_pref(self.auto_connect_var.get())

    def check_process(self):
        try:
            return subprocess.run(['pgrep', '-x', 'hide.me'], stdout=subprocess.DEVNULL).returncode == 0
        except Exception:
            return False

    def monitor_daemon(self):
        while True:
            is_running = self.check_process()
            if is_running != self.last_state:
                self.last_state = is_running
                if is_running:
                    self.status_var.set("🟢 PROTECTED")
                    self.lbl_status.configure(foreground=self.color_success)
                    self.fetch_ip_async(connected=True)
                else:
                    self.status_var.set("🔴 UNPROTECTED")
                    self.lbl_status.configure(foreground=self.color_danger)
                    self.fetch_ip_async(connected=False)
            time.sleep(2)

    def fetch_ip_async(self, connected):
        def task():
            if connected:
                time.sleep(4)
            self.ip_var.set("Searching IP...")
            self.location_var.set("Location: Loading...")
            try:
                resp = requests.get("https://ipinfo.io/json", timeout=5)
                data = resp.json()
                self.ip_var.set(f"Your IP: {data.get('ip', 'Unknown')}")
                self.location_var.set(f"Location: {data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}")
            except Exception:
                self.ip_var.set("IP: Could not be checked")
                self.location_var.set("Location: Unknown")
        threading.Thread(target=task, daemon=True).start()

    def connect_vpn(self):
        cmd = ["sudo", "hide.me"]
        
        if self.split_var.get() and self.subnet_var.get().strip():
            cmd.extend(["-s", self.subnet_var.get().strip()])
        
        if self.protocol_var.get() == "IPv4":
            cmd.append("-4")
        elif self.protocol_var.get() == "IPv6":
            cmd.append("-6")
            
        if self.pf_var.get():
            cmd.append("-pf")
            
        if not self.killswitch_var.get():
            cmd.append("-k=false")

        if self.no_ads_var.get(): cmd.append("-noAds")
        if self.no_malware_var.get(): cmd.append("-noMalware")
        if self.no_trackers_var.get(): cmd.append("-noTrackers")
        if self.safe_search_var.get(): cmd.append("-safeSearch")
        if self.force_dns_var.get(): cmd.append("-forceDns")

        if self.use_config_var.get() and self.config_path_var.get():
            cmd.extend(["-c", self.config_path_var.get()])
        if self.use_token_var.get() and self.token_path_var.get():
            cmd.extend(["-t", self.token_path_var.get()])
        if self.use_custom_dns_var.get() and self.custom_dns_var.get():
            cmd.extend(["-d", self.custom_dns_var.get()])

        cmd.append("connect")
        
        srv_display = self.server_var.get().strip()
        srv = self.server_mapping.get(srv_display, srv_display)
        
        if srv == "Custom Server...":
            messagebox.showwarning("Notice", "Please enter a valid server name in the dropdown menu.")
            return
        elif srv == "Random Free Server":
            srv = random.choice(self.free_servers)
            print(f"Randomizer selected: {srv}")
            
        cmd.append(srv)
        
        try:
            print("Executing:", " ".join(cmd)) 
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start VPN:\n{e}")

    def disconnect_vpn(self):
        subprocess.Popen(["sudo", "killall", "hide.me"])

if __name__ == "__main__":
    if not sys.platform.startswith('linux'):
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Unsupported OS", "This hide.me VPN Manager is built exclusively for Linux.")
            root.destroy()
        except:
            print("Error: This tool is for Linux only.")
        sys.exit(1)
    
    if os.geteuid() != 0:
        print("Notice: This script requires Root/Sudo privileges.")
        print("Please start it using: sudo python3 vpn_gui.py")
        sys.exit(1)
        
    root = tk.Tk()
    root.withdraw()
    
    if not is_hideme_installed():
        res = messagebox.askyesno(
            "Installation Required", 
            "The hide.me CLI is not installed on this system.\n\nDo you want to install it automatically now?"
        )
        if res:
            run_hideme_installer()
            messagebox.showinfo("Success", "Installation completed!\n\nThe application will now close. Please start it again.")
            sys.exit(0)
        else:
            sys.exit(1)
            
    if get_auto_update_pref():
        check_for_updates(manual=False)
    
    root.deiconify()
    app = HideMeVPNApp(root)
    root.mainloop()
