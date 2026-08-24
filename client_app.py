import asyncio
import base64
import csv
import json
import os
import random
import re
import subprocess
import sys
import threading
import hashlib
import winreg
import hmac
import tkinter as tk
import urllib.request
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, scrolledtext, filedialog
from urllib.parse import quote
from cryptography.fernet import Fernet
from playwright.async_api import async_playwright

# ==================== THÔNG TIN PHIÊN BẢN & BẢO MẬT ====================
CURRENT_VERSION = "2.1.0"
VERSION_CHECK_URL = "https://raw.githubusercontent.com/phat-boop/facebook-auto-tool/refs/heads/main/version.json"

SECRET_SALT = b"FB_TOOL_SECRET_SALT_2026"
LICENSE_FILE = "license.lic"
SETTINGS_FILE = "settings.json"

SEARCH_KEYWORDS = [
    "Bảo", "Trâm", "Thư", "Phong", "Hoàng", "Lan Anh", "Diệu", "Mai", "Kiệt", "Huy", 
    "Huyền", "Ngọc", "Quỳnh", "Thanh", "Tùng", "Hà", "Linh", "Duy", "Phương", "Hải", 
    "Nam", "Hạnh", "Thảo", "Vân", "Hương", "Nhung", "Bình", "Cường", "Đức", "Hùng", 
    "Tuấn", "Minh", "Quang", "Thành", "Trung", "Vũ", "Xuân", "Yến", "Anh", "Bích", 
    "Châu", "Diễm", "Giang", "Hiếu", "Hoài", "Hồng", "Khánh", "Kiều", "Lan", "Ngân", 
    "Như", "Trang", "Trinh", "Tú", "Tuệ"
]

ADD_FRIEND_SELECTORS = (
    'div[role="button"]:has-text("Thêm bạn bè"), '
    'div[role="button"]:has-text("Add friend"), '
    'div[role="button"]:has-text("Add Friend"), '
    'div[aria-label="Thêm bạn bè"], '
    'div[aria-label="Add friend"], '
    'div[aria-label="Add Friend"]'
)

MESSAGE_BTN_SELECTORS = (
    'div[role="button"]:has-text("Nhắn tin"), '
    'div[role="button"]:has-text("Message"), '
    'div[aria-label="Nhắn tin"], '
    'div[aria-label="Message"]'
)

CHAT_INPUT_SELECTORS = (
    'div[role="textbox"][contenteditable="true"]',
    'div[aria-label="Tin nhắn"]',
    'div[aria-label="Message"]'
)

CANCEL_REQUEST_SELECTORS = (
    'div[role="button"]:has-text("Hủy lời mời"), '
    'div[role="button"]:has-text("Hủy yêu cầu"), '
    'div[role="button"]:has-text("Cancel request"), '
    'div[aria-label="Hủy lời mời"], '
    'div[aria-label="Cancel request"]'
)

def check_for_updates():
    """Tự động kiểm tra, tự tải bản mới đè lên bản cũ và khởi động lại"""
    try:
        req = urllib.request.Request(VERSION_CHECK_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                latest_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url", "")
                changelog = data.get("changelog", "Nâng cấp tính năng và sửa lỗi.")

                if latest_version > CURRENT_VERSION:
                    confirm = messagebox.askyesno(
                        "Cập nhật tự động",
                        f"Đã có phiên bản mới: v{latest_version} (Bản hiện tại: v{CURRENT_VERSION})\n\n"
                        f"Nội dung mới:\n{changelog}\n\n"
                        "Bạn có muốn phần mềm tự động cập nhật ngay bây giờ không?"
                    )
                    
                    if confirm and download_url:
                        temp_file = "update_temp.exe"
                        urllib.request.urlretrieve(download_url, temp_file)

                        current_exe = sys.executable
                        bat_script = f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{temp_file}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
                        with open("updater.bat", "w", encoding="utf-8") as f:
                            f.write(bat_script)

                        messagebox.showinfo("Cập nhật", "Đã tải xong! Ứng dụng sẽ tự khởi động lại sau 2 giây.")
                        os.system("start updater.bat")
                        os._exit(0)
    except Exception:
        pass

def get_hwid():
    """Lấy mã định danh phần cứng máy tính duy nhất và bảo mật"""
    unique_parts = []
    
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        machine_guid, _ = winreg.QueryValueEx(registry_key, "MachineGuid")
        winreg.CloseKey(registry_key)
        if machine_guid:
            unique_parts.append(str(machine_guid).strip())
    except Exception:
        pass

    try:
        vol_cmd = "vol C:"
        output = subprocess.check_output(vol_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")
        match = re.search(r"Serial Number is ([A-Fa-f0-9-]+)", output, re.IGNORECASE)
        if match:
            unique_parts.append(match.group(1).strip())
    except Exception:
        pass

    try:
        ps_cmd = 'powershell -Command "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"'
        ps_out = subprocess.check_output(ps_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore").strip()
        if ps_out and "UUID" not in ps_out:
            unique_parts.append(ps_out)
    except Exception:
        pass

    raw_id = "-".join(unique_parts) if unique_parts else "FALLBACK_DEVICE_DEFAULT"
    hashed_hwid = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:16].upper()
    return f"HWID-{hashed_hwid}"

def verify_license(key_str: str):
    """Xác thực Key ngắn định dạng XXXX-XXXX-XXXX-XXXX"""
    try:
        clean_key = key_str.strip().replace("-", "").upper()
        if len(clean_key) != 16:
            return False, "Định dạng Key không hợp lệ!"

        days_hex = clean_key[:4]
        signature = clean_key[4:]

        days_offset = int(days_hex, 16)
        epoch = datetime(2026, 1, 1)
        expire_at = epoch + timedelta(days=days_offset)

        current_hwid = get_hwid().strip().upper()
        raw_payload = f"{current_hwid}-{days_hex}"
        expected_sig = hmac.new(SECRET_SALT, raw_payload.encode(), hashlib.sha256).hexdigest()[:12].upper()

        if not hmac.compare_digest(signature, expected_sig):
            return False, "Mã máy không khớp hoặc Key đã bị chỉnh sửa!"

        if datetime.now() > expire_at:
            return False, f"Key bản quyền đã hết hạn vào ngày {expire_at.strftime('%d/%m/%Y')}."

        return True, expire_at.strftime("%d/%m/%Y")
    except Exception:
        return False, "Key không hợp lệ!"

def parse_cookies(cookie_raw: str):
    cookies_list = []
    pairs = cookie_raw.strip().split(';')
    for pair in pairs:
        if '=' in pair:
            name, value = pair.strip().split('=', 1)
            cookies_list.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".facebook.com",
                "path": "/"
            })
    return cookies_list

def parse_proxy(proxy_raw: str):
    if not proxy_raw or not proxy_raw.strip():
        return None
    parts = proxy_raw.strip().split(':')
    if len(parts) == 4:
        return {"server": f"http://{parts[0]}:{parts[1]}", "username": parts[2], "password": parts[3]}
    elif len(parts) == 2:
        return {"server": f"http://{parts[0]}:{parts[1]}"}
    return None

def reset_rotating_proxy(api_url: str):
    """Gửi yêu cầu đổi IP qua đường link API của nhà cung cấp Proxy xoay"""
    if not api_url or not api_url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(api_url.strip(), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception:
        return False

def spin_text(text: str) -> str:
    """Xử lý cú pháp Spin-Tax {A|B|C} để tạo nội dung ngẫu nhiên chống trùng lặp"""
    if not text:
        return ""
    pattern = re.compile(r'\{([^{}]+)\}')
    while True:
        match = pattern.search(text)
        if not match:
            break
        choices = match.group(1).split('|')
        text = text[:match.start()] + random.choice(choices) + text[match.end():]
    return text

def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    """Gửi cảnh báo tức thì về Telegram Bot"""
    if not bot_token or not chat_id:
        return
    try:
        clean_token = bot_token.strip()
        clean_id = chat_id.strip()
        url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
        payload = json.dumps({"chat_id": clean_id, "text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception:
        pass



class LicenseCheckDialog:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.hwid = get_hwid()

        self.root.title("Kích hoạt bản quyền phần mềm")
        self.root.geometry("500x260")
        self.root.resizable(False, False)

        ttk.Label(root, text="MÃ MÁY (Gửi mã này cho Admin để nhận Key):", font=("Arial", 9, "bold")).pack(pady=(15, 5))
        self.ent_hwid = ttk.Entry(root, font=("Consolas", 10), justify="center")
        self.ent_hwid.insert(0, self.hwid)
        self.ent_hwid.config(state="readonly")
        self.ent_hwid.pack(fill="x", padx=20, pady=5)

        ttk.Label(root, text="NHẬP KEY BẢN QUYỀN:", font=("Arial", 9, "bold")).pack(pady=(10, 5))
        self.ent_key = ttk.Entry(root, font=("Consolas", 10))
        self.ent_key.pack(fill="x", padx=20, pady=5)

        ttk.Button(root, text="KÍCH HOẠT", command=self.activate).pack(pady=15)

    def activate(self):
        key = self.ent_key.get().strip()
        is_valid, msg = verify_license(key)
        if is_valid:
            with open(LICENSE_FILE, "w", encoding="utf-8") as f:
                f.write(key)
            messagebox.showinfo("Thành công", f"Kích hoạt thành công!\nHạn dùng: {msg}")
            self.root.destroy()
            self.on_success()
        else:
            messagebox.showerror("Lỗi", msg)
def get_installed_browser_path():
    """Tìm đường dẫn thực tế của Chrome hoặc Edge trên máy Windows"""
    possible_paths = [
        # Google Chrome
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        # Microsoft Edge (máy Windows nào cũng có)
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

# ==================== BẢNG MÀU CHUYÊN NGHIỆP (THEMES) ====================
THEMES = {
    "Dark Charcoal (Mặc định)": {
        "bg": "#18191A",
        "card": "#242526",
        "primary": "#2D88FF",
        "text": "#E4E6EB",
        "border": "#3E4042",
        "entry_bg": "#3A3B3C",
        "entry_fg": "#FFFFFF",
        "log_bg": "#121212",
        "log_fg": "#00FF66"
    },
    "Cyberpunk Neon": {
        "bg": "#0D1117",
        "card": "#161B22",
        "primary": "#00F0FF",
        "text": "#F0F6FC",
        "border": "#30363D",
        "entry_bg": "#21262D",
        "entry_fg": "#00F0FF",
        "log_bg": "#010409",
        "log_fg": "#FF007F"
    },
    "Deep Navy (Xanh Đêm)": {
        "bg": "#0A192F",
        "card": "#172A45",
        "primary": "#64FFDA",
        "text": "#CCD6F6",
        "border": "#233554",
        "entry_bg": "#0F2038",
        "entry_fg": "#FFFFFF",
        "log_bg": "#050C1A",
        "log_fg": "#64FFDA"
    },
    "Light Modern (Sáng)": {
        "bg": "#F0F2F5",
        "card": "#FFFFFF",
        "primary": "#1877F2",
        "text": "#050505",
        "border": "#CED0D4",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#000000",
        "log_bg": "#1E1E1E",
        "log_fg": "#00FF66"
    }
}
class ImportAccountDialog(tk.Toplevel):
    """Cửa sổ Pop-up Nhập tài khoản đa định dạng chuyên nghiệp với phân tích dữ liệu thông minh"""
    def __init__(self, parent, on_import_callback):
        super().__init__(parent)
        self.title("Thêm tài khoản vào hệ thống")
        self.geometry("680x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_import_callback = on_import_callback

        self.configure(bg="#0B0F19")

        # Tiêu đề & Chọn định dạng
        frame_top = tk.Frame(self, bg="#131C2E", padx=15, pady=10, highlightbackground="#1E293B", highlightthickness=1)
        frame_top.pack(fill="x", padx=10, pady=10)

        tk.Label(frame_top, text="Chọn định dạng dữ liệu:", font=("Segoe UI", 9, "bold"), bg="#131C2E", fg="#38BDF8").grid(row=0, column=0, sticky="w")
        
        self.format_mode = tk.StringVar(value="UID|Pass|2FA|Cookie")
        formats = [
            "UID|Pass|2FA|Cookie",
            "UID|Pass|2FA",
            "Tên|Cookie",
            "UID|Pass|2FA|Cookie|Proxy",
            "Tùy chỉnh (Phân cách bằng |)"
        ]
        self.cbo_format = ttk.Combobox(frame_top, values=formats, textvariable=self.format_mode, state="readonly", width=32)
        self.cbo_format.grid(row=0, column=1, padx=10, sticky="w")

        # Khung nhập dữ liệu
        frame_txt = tk.Frame(self, bg="#131C2E", padx=10, pady=10, highlightbackground="#1E293B", highlightthickness=1)
        frame_txt.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(frame_txt, text="Dán danh sách tài khoản vào đây (Mỗi dòng 1 nick):", font=("Segoe UI", 9), bg="#131C2E", fg="#94A3B8").pack(anchor="w", pady=(0, 5))
        self.txt_input = scrolledtext.ScrolledText(frame_txt, bg="#070B14", fg="#E2E8F0", font=("Consolas", 10), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_input.pack(fill="both", expand=True)

        # Nút hành động
        frame_btns = tk.Frame(self, bg="#0B0F19", pady=10)
        frame_btns.pack(fill="x", padx=10)

        btn_add = tk.Button(frame_btns, text="✔ THÊM TÀI KHOẢN", font=("Segoe UI", 10, "bold"), bg="#0284C7", fg="#FFFFFF", relief="flat", padx=20, pady=6, cursor="hand2", command=self.process_import)
        btn_add.pack(side="right", padx=5)

        btn_close = tk.Button(frame_btns, text="HỦY BỎ", font=("Segoe UI", 10), bg="#1E293B", fg="#94A3B8", relief="flat", padx=15, pady=6, cursor="hand2", command=self.destroy)
        btn_close.pack(side="right", padx=5)

    def process_import(self):
        raw_data = self.txt_input.get("1.0", "end").strip()
        if not raw_data:
            messagebox.showwarning("Thông báo", "Vui lòng nhập ít nhất 1 dòng dữ liệu!", parent=self)
            return

        lines = [l.strip() for l in raw_data.splitlines() if l.strip()]
        fmt = self.format_mode.get()
        parsed_accounts = []

        for line in lines:
            parts = line.split('|')
            uid, pwd, fa2, cookie, proxy, name = "", "", "", "", "Không dùng", ""

            if fmt == "UID|Pass|2FA|Cookie":
                uid = parts[0] if len(parts) > 0 else ""
                pwd = parts[1] if len(parts) > 1 else ""
                fa2 = parts[2] if len(parts) > 2 else ""
                cookie = parts[3] if len(parts) > 3 else ""
                name = uid or f"Nick_{len(parsed_accounts)+1}"
            elif fmt == "UID|Pass|2FA":
                uid = parts[0] if len(parts) > 0 else ""
                pwd = parts[1] if len(parts) > 1 else ""
                fa2 = parts[2] if len(parts) > 2 else ""
                name = uid or f"Nick_{len(parsed_accounts)+1}"
            elif fmt == "Tên|Cookie":
                name = parts[0] if len(parts) > 0 else f"Nick_{len(parsed_accounts)+1}"
                cookie = parts[1] if len(parts) > 1 else ""
                m = re.search(r'c_user=(\d+)', cookie)
                if m: uid = m.group(1)
            elif fmt == "UID|Pass|2FA|Cookie|Proxy":
                uid = parts[0] if len(parts) > 0 else ""
                pwd = parts[1] if len(parts) > 1 else ""
                fa2 = parts[2] if len(parts) > 2 else ""
                cookie = parts[3] if len(parts) > 3 else ""
                proxy = parts[4] if len(parts) > 4 else "Không dùng"
                name = uid or f"Nick_{len(parsed_accounts)+1}"
            else:
                name = parts[0]
                cookie = parts[1] if len(parts) > 1 else ""

            parsed_accounts.append({
                "name": name,
                "uid": uid,
                "pwd": pwd,
                "2fa": fa2,
                "cookie": cookie,
                "proxy": proxy,
                "raw": line
            })

        self.on_import_callback(parsed_accounts)
        messagebox.showinfo("Thành công", f"Đã nạp thành công {len(parsed_accounts)} tài khoản vào bảng!", parent=self)
        self.destroy()




class MainToolApp:
    def __init__(self, root, expire_date):
        self.root = root
        self.expire_date = expire_date
        self.root.title(f"Facebook Auto Add Friends Pro v{CURRENT_VERSION} - Phát triển bởi: ĐẶNG PHÁT - Hạn dùng: {expire_date}")
        self.root.geometry("1380x880")
        self.root.minsize(1280, 800)
        self.is_running = False

        self.theme_name = "Dark Charcoal (Mặc định)"
        self.T = THEMES[self.theme_name]

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_layout()
        self.load_settings()
        self._start_clock()

        threading.Thread(target=check_for_updates, daemon=True).start()

    def _build_layout(self):
        self.root.configure(bg="#0B0F19")

        # 1. HEADER
        self.frame_header = tk.Frame(self.root, bg="#151D2E", height=55, padx=15, pady=6, highlightbackground="#1E293B", highlightthickness=1)
        self.frame_header.pack(fill="x", side="top")

        f_title = tk.Frame(self.frame_header, bg="#151D2E")
        f_title.pack(side="left", padx=5)
        self.lbl_logo = tk.Label(f_title, text="⚡", font=("Segoe UI", 18), fg="#38BDF8", bg="#151D2E")
        self.lbl_logo.pack(side="left", padx=(0, 8))
        
        f_text = tk.Frame(f_title, bg="#151D2E")
        f_text.pack(side="left")
        self.lbl_app_name = tk.Label(f_text, text="Facebook Auto Add Friends Pro", font=("Segoe UI", 11, "bold"), fg="#FFFFFF", bg="#151D2E")
        self.lbl_app_name.pack(anchor="w")
        self.lbl_app_sub = tk.Label(f_text, text="Bản quyền © ĐẶNG PHÁT | Tự động kết bạn & Nuôi nick", font=("Segoe UI", 8), fg="#94A3B8", bg="#151D2E")
        self.lbl_app_sub.pack(anchor="w")

        f_tabs = tk.Frame(self.frame_header, bg="#151D2E")
        f_tabs.pack(side="left", padx=40)

        self.btn_tab_main = tk.Button(f_tabs, text="🏠 TRANG CHỦ", font=("Segoe UI", 9, "bold"), bg="#0284C7", fg="#FFFFFF", relief="flat", padx=15, pady=5, cursor="hand2", command=lambda: self.switch_tab(0))
        self.btn_tab_main.pack(side="left", padx=4)

        self.btn_tab_data = tk.Button(f_tabs, text="📊 THỐNG KÊ & QUẢN LÝ", font=("Segoe UI", 9, "bold"), bg="#222F43", fg="#94A3B8", relief="flat", padx=15, pady=5, cursor="hand2", command=lambda: self.switch_tab(1))
        self.btn_tab_data.pack(side="left", padx=4)

        f_right = tk.Frame(self.frame_header, bg="#151D2E")
        f_right.pack(side="right", padx=5)

        tk.Label(f_right, text="Giao diện:", font=("Segoe UI", 9), fg="#94A3B8", bg="#151D2E").pack(side="left", padx=4)
        self.cbo_theme = ttk.Combobox(f_right, values=list(THEMES.keys()), state="readonly", width=16)
        self.cbo_theme.set(self.theme_name)
        self.cbo_theme.pack(side="left", padx=4)
        self.cbo_theme.bind("<<ComboboxSelected>>", self.on_change_theme)

        # 2. FOOTER (Pack trước body để luôn cố định ở đáy)
        self.frame_footer = tk.Frame(self.root, bg="#131B2E", height=28, padx=15, pady=4, highlightbackground="#1E293B", highlightthickness=1)
        self.frame_footer.pack(fill="x", side="bottom")

        self.lbl_status_indicator = tk.Label(self.frame_footer, text="● Sẵn sàng", font=("Segoe UI", 9, "bold"), fg="#10B981", bg="#131B2E")
        self.lbl_status_indicator.pack(side="left")

        self.lbl_author = tk.Label(self.frame_footer, text="⚡ Software by ĐẶNG PHÁT", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131B2E")
        self.lbl_author.pack(side="left", padx=25)

        self.lbl_clock = tk.Label(self.frame_footer, text="", font=("Segoe UI", 9), fg="#94A3B8", bg="#131B2E")
        self.lbl_clock.pack(side="right", padx=5)

        # 3. BODY CONTAINER
        self.body_container = tk.Frame(self.root, bg="#0B0F19")
        self.body_container.pack(fill="both", expand=True)

        self.tab1_view = tk.Frame(self.body_container, bg="#0B0F19")
        self.tab2_view = tk.Frame(self.body_container, bg="#0B0F19")

        self.tab_main = self.tab1_view
        self.tab_data = self.tab2_view

        self._build_tab_main()
        self._build_tab_data()

        self.tab1_view.pack(fill="both", expand=True)

    def switch_tab(self, tab_idx):
        if tab_idx == 0:
            self.tab2_view.pack_forget()
            self.tab1_view.pack(fill="both", expand=True)
            self.btn_tab_main.config(bg="#0284C7", fg="#FFFFFF")
            self.btn_tab_data.config(bg="#222F43", fg="#94A3B8")
        else:
            self.tab1_view.pack_forget()
            self.tab2_view.pack(fill="both", expand=True)
            self.btn_tab_data.config(bg="#0284C7", fg="#FFFFFF")
            self.btn_tab_main.config(bg="#222F43", fg="#94A3B8")

    def _create_card(self, parent, title, icon=""):
        f_card = tk.Frame(parent, bg=self.T["card"], highlightbackground=self.T["border"], highlightthickness=1, padx=12, pady=10)
        f_header = tk.Frame(f_card, bg=self.T["card"])
        f_header.pack(fill="x", pady=(0, 8))
        tk.Label(f_header, text=f"{icon} {title}".strip(), font=("Segoe UI", 9, "bold"), fg=self.T["primary"], bg=self.T["card"]).pack(side="left")
        return f_card

    def _start_clock(self):
        def update():
            now = datetime.now()
            now_str = now.strftime("🕒 %H:%M:%S   📅 %d/%m/%Y")
            if hasattr(self, 'lbl_clock') and self.lbl_clock.winfo_exists():
                self.lbl_clock.config(text=now_str)
            self.root.after(1000, update)
        update()

    def on_change_theme(self, event=None):
        theme_name = self.cbo_theme.get()
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name):
        """Đổi toàn bộ màu sắc phần mềm theo Theme được chọn"""
        t = THEMES.get(theme_name, THEMES["Dark Charcoal (Mặc định)"])
        self.current_theme = theme_name

        self.root.configure(bg=t["bg"])
        
        # Cập nhật Style TTK
        self.style.configure("TLabelframe", background=t["card"], bordercolor=t["border"], relief="solid", borderwidth=1)
        self.style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"), foreground=t["primary"], background=t["card"])
        self.style.configure("TFrame", background=t["card"])
        
        self.style.configure("TLabel", background=t["card"], font=("Segoe UI", 9), foreground=t["text"])
        self.style.configure("TRadiobutton", background=t["card"], font=("Segoe UI", 9), foreground=t["text"])
        self.style.configure("TCheckbutton", background=t["card"], font=("Segoe UI", 9), foreground=t["text"])

        self.style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=5, background=t["primary"], foreground="#FFFFFF")
        self.style.map("TButton", background=[("active", t["border"]), ("!disabled", t["primary"])], foreground=[("!disabled", "#FFFFFF")])

        self.style.configure("TNotebook", background=t["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[15, 6], background=t["border"], foreground=t["text"])
        self.style.map("TNotebook.Tab", background=[("selected", t["primary"])], foreground=[("selected", "#FFFFFF")])

        # Style Treeview
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background=t["border"], foreground=t["text"])
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), background=t["card"], foreground=t["text"], fieldbackground=t["card"], borderwidth=0)
        self.style.map("Treeview", background=[("selected", t["primary"])], foreground=[("selected", "#FFFFFF")])

        # Style Progressbar
        self.style.configure("Horizontal.TProgressbar", troughcolor=t["border"], background=t["primary"], bordercolor=t["card"])

        # Cập nhật màu các ô ScrolledText
        for txt in [self.txt_accounts, self.txt_proxies, self.txt_targets]:
            txt.configure(bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["primary"], relief="solid", bd=1)
        
        self.txt_log.configure(bg=t["log_bg"], fg=t["log_fg"], relief="solid", bd=1)

    # [BẮT ĐẦU THAY THẾ TOÀN BỘ _build_tab_main VÀ _build_tab_data:]
    # [BẮT ĐẦU THAY THẾ _build_tab_main:]
    def _build_tab_main(self):
        paned_main = tk.PanedWindow(self.tab_main, orient="horizontal", bg="#0A0E1A", bd=0, sashwidth=6, sashrelief="ridge")
        paned_main.pack(fill="both", expand=True, padx=10, pady=8)

        # ==================== CỘT TRÁI (GIỮ NGUYÊN BỐ CỤC ĐẸP) ====================
        paned_left = tk.PanedWindow(paned_main, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=5, sashrelief="ridge")
        paned_main.add(paned_left, minsize=380)

        # 1. Cookie Card
        card1 = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card1, minsize=110, height=180)

        f1_head = tk.Frame(card1, bg="#131C2E")
        f1_head.pack(fill="x", pady=(0, 2))
        tk.Label(f1_head, text="👤 1. DANH SÁCH COOKIE NICK", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f1_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_accounts_file).pack(side="right")

        tk.Label(card1, text="Nhập danh sách Cookie (Tên|Cookie):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w")
        self.txt_accounts = scrolledtext.ScrolledText(card1, bg="#070B14", fg="#E2E8F0", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_accounts.pack(fill="both", expand=True, pady=2)

        f1_bot = tk.Frame(card1, bg="#131C2E")
        f1_bot.pack(fill="x")
        self.lbl_acc_count = tk.Label(f1_bot, text="Tổng: 0 nick   👥 0", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E")
        self.lbl_acc_count.pack(side="left")
        tk.Button(f1_bot, text="🗑 Xóa tất cả", font=("Segoe UI", 8), bg="#131C2E", fg="#F87171", relief="flat", cursor="hand2", command=lambda: self.txt_accounts.delete("1.0", "end")).pack(side="right")

        # 3. Chức năng tự động Card
        card3 = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card3, minsize=180, height=320)

        f3_head = tk.Frame(card3, bg="#131C2E")
        f3_head.pack(fill="x", pady=(0, 2))
        tk.Label(f3_head, text="⚡ 3. CHỨC NĂNG TỰ ĐỘNG", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        
        def toggle_all(val):
            for v in self.mode_vars.values(): v.set(val)

        tk.Button(f3_head, text="Bỏ chọn hết", font=("Segoe UI", 7), bg="#1E293B", fg="#94A3B8", relief="flat", cursor="hand2", command=lambda: toggle_all(False)).pack(side="right", padx=2)
        tk.Button(f3_head, text="Chọn tất cả", font=("Segoe UI", 7), bg="#1E293B", fg="#38BDF8", relief="flat", cursor="hand2", command=lambda: toggle_all(True)).pack(side="right", padx=2)

        canvas_modes = tk.Canvas(card3, bg="#131C2E", highlightthickness=0, bd=0)
        scroll_modes = ttk.Scrollbar(card3, orient="vertical", command=canvas_modes.yview)
        f_modes_grid = tk.Frame(canvas_modes, bg="#131C2E")

        f_modes_grid.bind("<Configure>", lambda e: canvas_modes.configure(scrollregion=canvas_modes.bbox("all")))
        canvas_window = canvas_modes.create_window((0, 0), window=f_modes_grid, anchor="nw")
        canvas_modes.configure(yscrollcommand=scroll_modes.set)

        def _on_canvas_configure(e):
            canvas_modes.itemconfig(canvas_window, width=e.width)
        canvas_modes.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas_modes.yview_scroll(int(-1 * (event.delta / 120)), "units")

        card3.bind("<Enter>", lambda e: canvas_modes.bind_all("<MouseWheel>", _on_mousewheel))
        card3.bind("<Leave>", lambda e: canvas_modes.unbind_all("<MouseWheel>"))

        canvas_modes.pack(side="top", fill="both", expand=True)
        scroll_modes.pack(side="right", fill="y")
        for i in range(3): f_modes_grid.columnconfigure(i, weight=1)

        self.mode_vars = {}
        all_modes = [
            ("🔍 1. Tìm Tên ngẫu nhiên", "by_name"),
            ("💬 6. Nhắn tin UID/Bạn bè", "auto_inbox"),
            ("🎯 11. Quét UID Tương tác", "scrape_uid"),
            ("👥 2. Tham gia Nhóm FB", "by_group"),
            ("❤️ 7. Seeding Bài Nhóm", "seed_group"),
            ("🚩 12. Tự động Tạo Fanpage", "create_page"),
            ("📇 3. Quét UID / Profile", "by_uid"),
            ("ℹ️ 8. Cập nhật Tiểu sử Bio", "change_bio"),
            ("🚀 13. Đăng bài lên Page", "post_page"),
            ("➕ 4. Tham gia Nhóm (Join)", "join_group"),
            ("🖼️ 9. Thay đổi Avatar/Bìa", "change_avatar"),
            ("🔴 14. Bão Seeding Live", "seed_live"),
            ("📝 5. Tự động Đăng bài", "auto_post"),
            ("🤝 10. Mời Bạn vào Nhóm", "invite_group"),
            ("🔑 15. Tự động Đổi Pass", "change_pass"),
            ("🔐 16. Bật Bảo Mật 2FA", "enable_2fa"),
            ("🚪 17. Đăng xuất Thiết bị", "logout_sessions"),
            ("👑 18. Thêm Admin Page", "add_page_admin"),
            ("🏷️ 19. Đổi Tên Fanpage", "update_page_name"),
            ("👍 20. Mời Bạn Like Page", "invite_like_page"),
            ("📩 21. Inbox Người Comment", "inbox_commenters"),
            ("📢 22. Đăng Bài Group Đã Vào", "post_joined_groups"),
            ("🖼️ 23. Bình Luận Kèm Ảnh", "comment_with_image"),
            ("👥 24. Quét Member Nhóm", "scrape_group_members"),
            ("📞 25. Quét SĐT/Email Profile", "scrape_contacts"),
            ("🎵 26. TikTok Chéo Follow", "tiktok_follow_cmt")
        ]

        for i, (text, val) in enumerate(all_modes):
            r, c = divmod(i, 3)
            var = tk.BooleanVar(value=True if val == "by_name" else False)
            self.mode_vars[val] = var
            tk.Checkbutton(
                f_modes_grid, text=text, variable=var,
                font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14",
                activebackground="#131C2E", activeforeground="#38BDF8", cursor="hand2"
            ).grid(row=r, column=c, sticky="w", padx=2, pady=2)

        tk.Label(card3, text="Nhập Link/ID Group, UID, Pass mới HOẶC File ảnh (mỗi dòng 1 mục):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w", pady=(2, 1))
        self.txt_targets = scrolledtext.ScrolledText(card3, height=2, bg="#070B14", fg="#E2E8F0", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_targets.pack(fill="x")

        # Log Card
        card_log = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card_log, minsize=100, height=180)

        tk.Label(card_log, text="📜 NHẬT KÝ HOẠT ĐỘNG", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 2))
        self.txt_log = scrolledtext.ScrolledText(card_log, bg="#070B14", fg="#00FF66", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1, state="disabled")
        self.txt_log.pack(fill="both", expand=True)

        # ==================== CỘT PHẢI (THIẾT KẾ ĐẦY ĐỦ, CHUYÊN NGHIỆP) ====================
        paned_right = tk.PanedWindow(paned_main, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=5, sashrelief="ridge")
        paned_main.add(paned_right, minsize=420)

        # R1: Card Danh sách Proxy
        card2 = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card2, minsize=120, height=150)

        f2_head = tk.Frame(card2, bg="#131C2E")
        f2_head.pack(fill="x", pady=(0, 2))
        tk.Label(f2_head, text="🌐 2. DANH SÁCH PROXY", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f2_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_proxies_file).pack(side="right")

        tk.Label(card2, text="Nhập danh sách Proxy (IP:Port hoặc IP:Port:User:Pass):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w")
        self.txt_proxies = scrolledtext.ScrolledText(card2, bg="#070B14", fg="#E2E8F0", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_proxies.pack(fill="both", expand=True, pady=2)

        f2_cfg = tk.Frame(card2, bg="#131C2E")
        f2_cfg.pack(fill="x")
        self.proxy_mode = tk.StringVar(value="fixed_ratio")
        for txt, val in [("Cố định", "fixed_ratio"), ("Random", "random"), ("API Xoay", "rotating_api")]:
            tk.Radiobutton(f2_cfg, text=txt, variable=self.proxy_mode, value=val, font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left", padx=4)

        tk.Label(f2_cfg, text="Số nick/Proxy:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(8, 2))
        self.ent_proxy_ratio = tk.Entry(f2_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_proxy_ratio.insert(0, "20")
        self.ent_proxy_ratio.pack(side="left")

        f2_api = tk.Frame(card2, bg="#131C2E")
        f2_api.pack(fill="x", pady=(2, 0))
        tk.Label(f2_api, text="Link API đổi IP:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left")
        self.ent_proxy_api = tk.Entry(f2_api, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_proxy_api.pack(side="left", fill="x", expand=True, padx=4)

        f2_bot = tk.Frame(card2, bg="#131C2E")
        f2_bot.pack(fill="x", pady=(2, 0))
        tk.Label(f2_bot, text="Tổng: 0 proxy   🌐 0", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left")
        tk.Button(f2_bot, text="🗑 Xóa tất cả", font=("Segoe UI", 8), bg="#131C2E", fg="#F87171", relief="flat", cursor="hand2", command=lambda: self.txt_proxies.delete("1.0", "end")).pack(side="right")

        # R2: Card Tự Động Reg Nick Đa Nền Tảng (Mới - Tối ưu không gian)
        card_reg = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card_reg, minsize=140, height=170)

        f_reg_head = tk.Frame(card_reg, bg="#131C2E")
        f_reg_head.pack(fill="x", pady=(0, 4))
        tk.Label(f_reg_head, text="🤖 4. TỰ ĐỘNG REG NICK ĐA NỀN TẢNG (PRO)", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")

        f_reg_cfg = tk.Frame(card_reg, bg="#131C2E")
        f_reg_cfg.pack(fill="x", pady=2)
        
        self.chk_reg_fb = tk.BooleanVar(value=False)
        self.chk_reg_tiktok = tk.BooleanVar(value=False)
        self.chk_reg_insta = tk.BooleanVar(value=False)

        tk.Checkbutton(f_reg_cfg, text="Reg FB (Hotmail)", variable=self.chk_reg_fb, font=("Segoe UI", 8, "bold"), fg="#38BDF8", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Checkbutton(f_reg_cfg, text="Reg TikTok", variable=self.chk_reg_tiktok, font=("Segoe UI", 8, "bold"), fg="#F43F5E", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left", padx=8)
        tk.Checkbutton(f_reg_cfg, text="Reg Instagram", variable=self.chk_reg_insta, font=("Segoe UI", 8, "bold"), fg="#EC4899", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left", padx=8)

        f_reg_inputs = tk.Frame(card_reg, bg="#131C2E")
        f_reg_inputs.pack(fill="x", pady=2)
        tk.Label(f_reg_inputs, text="Pass tạo mặc định:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left")
        self.ent_reg_pass = tk.Entry(f_reg_inputs, width=16, font=("Segoe UI", 8), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_reg_pass.insert(0, "DangPhat@2026Secure")
        self.ent_reg_pass.pack(side="left", padx=4)

        tk.Label(card_reg, text="Dán danh sách Mail Reg (Mail|PassMail - Mỗi dòng 1 mail):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w", pady=(2, 0))
        self.txt_reg_mails = scrolledtext.ScrolledText(card_reg, height=3, bg="#070B14", fg="#E2E8F0", font=("Consolas", 8), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_reg_mails.pack(fill="both", expand=True, pady=2)

        # R3: Card Nuôi Nick Chống Checkpoint
        card4 = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card4, minsize=140, height=180)

        tk.Label(card4, text="🛡️ 5. LUỒNG & NUÔI NICK CHỐNG CHECKPOINT", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 2))

        f4_sys = tk.Frame(card4, bg="#131C2E")
        f4_sys.pack(fill="x", pady=2)
        tk.Label(f4_sys, text="Số luồng chạy song song:", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_threads = tk.Entry(f4_sys, width=4, font=("Segoe UI", 8, "bold"), bg="#070B14", fg="#38BDF8", justify="center", relief="solid", bd=1)
        self.ent_threads.insert(0, "3")
        self.ent_threads.pack(side="left", padx=4)

        self.chk_headless = tk.BooleanVar(value=False)
        self.chk_warmup = tk.BooleanVar(value=True)
        self.chk_cancel_old = tk.BooleanVar(value=True)
        self.chk_watch_reels = tk.BooleanVar(value=True)
        self.chk_view_stories = tk.BooleanVar(value=True)
        self.chk_browse_web = tk.BooleanVar(value=True)
        self.chk_interact_page = tk.BooleanVar(value=True)
        self.chk_check_notif = tk.BooleanVar(value=True)
        self.chk_chat_react = tk.BooleanVar(value=True)

        f4_checks = tk.Frame(card4, bg="#131C2E")
        f4_checks.pack(fill="both", expand=True, pady=2)
        for i in range(3): f4_checks.columnconfigure(i, weight=1)
        c_list = [
            ("Chạy ẩn trình duyệt", self.chk_headless),
            ("Lướt Newfeed đệm (30s)", self.chk_warmup),
            ("Hủy lời mời cũ", self.chk_cancel_old),
            ("Xem Reels Video", self.chk_watch_reels),
            ("Xem Story bạn bè", self.chk_view_stories),
            ("Lướt báo ngoài (20s)", self.chk_browse_web),
            ("Like/Follow Fanpage", self.chk_interact_page),
            ("Xem Thông báo", self.chk_check_notif),
            ("Thả tim Messenger", self.chk_chat_react)
        ]
        for i, (txt, var) in enumerate(c_list):
            r, c = divmod(i, 3)
            tk.Checkbutton(f4_checks, text=txt, variable=var, font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14", cursor="hand2").grid(row=r, column=c, sticky="w", padx=2, pady=1)

        f4_tele = tk.Frame(card4, bg="#131C2E")
        f4_tele.pack(fill="x", pady=(2, 0))
        tk.Label(f4_tele, text="Telegram Token:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left")
        self.ent_tele_token = tk.Entry(f4_tele, width=16, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_tele_token.pack(side="left", padx=2)

        tk.Label(f4_tele, text="Chat ID:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(4, 2))
        self.ent_tele_chatid = tk.Entry(f4_tele, width=10, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_tele_chatid.pack(side="left")

        # R4: Card Thông số & Điều khiển
        f_bottom_right = tk.Frame(paned_right, bg="#0A0E1A")
        paned_right.add(f_bottom_right, minsize=140, height=160)

        card5 = tk.Frame(f_bottom_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=6)
        card5.pack(fill="x", pady=(0, 4))

        tk.Label(card5, text="⚙️ 6. THÔNG SỐ GỬI KẾT BẠN & TƯƠNG TÁC", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 2))

        f5_cfg = tk.Frame(card5, bg="#131C2E")
        f5_cfg.pack(fill="x", expand=True)
        tk.Label(f5_cfg, text="Chỉ tiêu bạn/nick:", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_target = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_target.insert(0, "25")
        self.ent_target.pack(side="left", padx=4)

        tk.Label(f5_cfg, text="Delay click (s):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(15, 2))
        self.ent_min_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_min_delay.insert(0, "15")
        self.ent_min_delay.pack(side="left", padx=2)
        tk.Label(f5_cfg, text="-", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_max_delay.insert(0, "35")
        self.ent_max_delay.pack(side="left", padx=2)

        f_action_btns = tk.Frame(f_bottom_right, bg="#0A0E1A")
        f_action_btns.pack(fill="x", pady=(0, 4))
        self.btn_start = tk.Button(f_action_btns, text="▶ BẮT ĐẦU CHẠY", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", cursor="hand2", command=self.start_thread)
        self.btn_start.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.btn_stop = tk.Button(f_action_btns, text="⏹ DỪNG LẠI", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="#FFFFFF", relief="flat", cursor="hand2", state="disabled", command=self.stop_bot)
        self.btn_stop.pack(side="right", fill="both", expand=True, padx=(4, 0))

        f_stats = tk.Frame(f_bottom_right, bg="#0A0E1A")
        f_stats.pack(fill="both", expand=True)
        for i in range(4): f_stats.columnconfigure(i, weight=1)

        def make_stat_box(parent, title, val, col_idx, color):
            bx = tk.Frame(parent, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, pady=3)
            bx.grid(row=0, column=col_idx, sticky="nsew", padx=2)
            lbl_v = tk.Label(bx, text=val, font=("Segoe UI", 11, "bold"), fg=color, bg="#131C2E")
            lbl_v.pack(expand=True)
            tk.Label(bx, text=title, font=("Segoe UI", 7), fg="#94A3B8", bg="#131C2E").pack(pady=(0, 1))
            return lbl_v

        self.lbl_stat_total = make_stat_box(f_stats, "Tổng nick", "0", 0, "#38BDF8")
        self.lbl_stat_running = make_stat_box(f_stats, "Đang chạy", "0", 1, "#F59E0B")
        self.lbl_stat_success = make_stat_box(f_stats, "Thành công", "0", 2, "#10B981")
        self.lbl_stat_failed = make_stat_box(f_stats, "Thất bại", "0", 3, "#EF4444")
# [KẾT THÚC THAY THẾ]

    def _build_tab_data(self):
        # PanedWindow dọc cho Tab 2 (Kéo dãn thanh công cụ / Bảng dữ liệu)
        paned_data = tk.PanedWindow(self.tab_data, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=4, sashrelief="ridge")
        paned_data.pack(fill="both", expand=True, padx=8, pady=6)

        # 1. Thanh Ribbon Nút Bấm Xanh
        frame_ribbon = tk.Frame(paned_data, bg="#131C2E", padx=10, pady=6, highlightbackground="#1E293B", highlightthickness=1)
        paned_data.add(frame_ribbon, minsize=45, height=52)

        def make_btn(text, cmd, color="#0284C7"):
            return tk.Button(frame_ribbon, text=text, font=("Segoe UI", 8, "bold"), bg=color, fg="#FFFFFF",
                             relief="flat", padx=10, pady=4, cursor="hand2", command=cmd)

        make_btn("➕ Nhập Tài Khoản", self.open_import_dialog).pack(side="left", padx=2)
        make_btn("🌐 Open Profile", self.open_selected_profile).pack(side="left", padx=2)
        make_btn("🔍 Check Live/Die", self.check_live_selected).pack(side="left", padx=2)
        make_btn("🔑 Get Token EAAB", self.get_token_selected).pack(side="left", padx=2)
        make_btn("🔐 Lấy mã 2FA", self.generate_2fa_dialog).pack(side="left", padx=2)
        make_btn("🗑 Xóa Chọn", self.delete_selected_rows, color="#EF4444").pack(side="left", padx=2)

        f_search = tk.Frame(frame_ribbon, bg="#131C2E")
        f_search.pack(side="left", padx=(10, 2))
        tk.Label(f_search, text="🔍 Tìm:", font=("Segoe UI", 8), fg="#38BDF8", bg="#131C2E").pack(side="left", padx=(0, 2))
        self.ent_search_tree = tk.Entry(f_search, width=15, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_search_tree.pack(side="left", padx=2)

        def filter_table(event=None):
            kw = self.ent_search_tree.get().strip().lower()
            for item in self.tree.get_children():
                vals = [str(v).lower() for v in self.tree.item(item, "values")]
                if not kw or any(kw in v for v in vals):
                    self.tree.reattach(item, "", "end")
                else:
                    self.tree.detach(item)
        self.ent_search_tree.bind("<KeyRelease>", filter_table)

        make_btn("📊 Xuất Báo Cáo CSV", self.export_to_csv, color="#10B981").pack(side="right", padx=2)

        # 2. Bảng dữ liệu trung tâm Dark Theme
        frame_tree = tk.Frame(paned_data, bg="#0A0E1A")
        paned_data.add(frame_tree, minsize=200)

        columns = ("id", "uid", "name", "2fa", "proxy", "sent_today", "current_friends", "status")
        self.tree = ttk.Treeview(frame_tree, columns=columns, show="headings")

        self.tree.heading("id", text="STT")
        self.tree.heading("uid", text="UID Tài Khoản")
        self.tree.heading("name", text="Tên / Ghi Chú")
        self.tree.heading("2fa", text="2FA Secret")
        self.tree.heading("proxy", text="Proxy")
        self.tree.heading("sent_today", text="Đã gửi/chạy")
        self.tree.heading("current_friends", text="Số bạn bè")
        self.tree.heading("status", text="Trạng Thái Live")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("uid", width=140, anchor="center")
        self.tree.column("name", width=130)
        self.tree.column("2fa", width=120, anchor="center")
        self.tree.column("proxy", width=160)
        self.tree.column("sent_today", width=90, anchor="center")
        self.tree.column("current_friends", width=100, anchor="center")
        self.tree.column("status", width=130, anchor="center")

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        # 3. Thanh trạng thái dưới đáy
        self.lbl_footer_status = tk.Label(self.tab_data, text="Tổng số nick: 0 | Sẵn sàng hoạt động.", font=("Segoe UI", 9), fg="#94A3B8", bg="#131C2E", anchor="w", padx=10, pady=4)
        self.lbl_footer_status.pack(fill="x", side="bottom")
# [KẾT THÚC THAY THẾ]



    def update_footer_count(self):
        total = len(self.tree.get_children())
        self.lbl_footer_status.config(text=f"Tổng số nick: {total} | Sẵn sàng hoạt động.")

    def update_tree_row(self, item_id, current_friends=None, sent_today=None, status=None):
        """Cập nhật dữ liệu hàng trong bảng Treeview theo thời gian thực an toàn luồng"""
        def _update():
            if self.tree.exists(item_id):
                vals = list(self.tree.item(item_id, "values"))
                if current_friends is not None:
                    vals[6] = str(current_friends)
                if sent_today is not None:
                    vals[5] = str(sent_today)
                if status is not None:
                    vals[7] = str(status)
                self.tree.item(item_id, values=vals)
        self.root.after(0, _update)

    def log(self, text):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", f"{text}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")
    def open_import_dialog(self):
        ImportAccountDialog(self.root, self.add_accounts_to_table)

    def add_accounts_to_table(self, account_list):
        start_idx = len(self.tree.get_children()) + 1
        for i, acc in enumerate(account_list, start=start_idx):
            self.tree.insert("", "end", iid=str(i), values=(
                i, acc["uid"], acc["name"], acc["2fa"], acc["proxy"], "0", "Chưa kiểm tra", "Sẵn sàng"
            ))
            if acc["cookie"]:
                self.txt_accounts.insert("end", f"{acc['name']}|{acc['cookie']}\n")
        if hasattr(self, 'lbl_stat_total'):
            self.lbl_stat_total.config(text=str(len(self.tree.get_children())))
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {len(self.tree.get_children())} nick")

    def delete_selected_rows(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn dòng cần xóa!")
            return
        for item in selected: 
            self.tree.delete(item)
        if hasattr(self, 'lbl_stat_total'):
            self.lbl_stat_total.config(text=str(len(self.tree.get_children())))
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {len(self.tree.get_children())} nick")

    
    # [BẮT ĐẦU THAY THẾ save_settings VÀ load_settings:]
    def save_settings(self):
        modes_saved = {k: v.get() for k, v in self.mode_vars.items()} if hasattr(self, 'mode_vars') else {}
        data = {
            "selected_theme": self.current_theme,
            "accounts": self.txt_accounts.get("1.0", "end").strip(),
            "proxies": self.txt_proxies.get("1.0", "end").strip(),
            "targets": self.txt_targets.get("1.0", "end").strip(),
            "selected_modes": modes_saved,
            "proxy_mode": self.proxy_mode.get(),
            "proxy_ratio": self.ent_proxy_ratio.get(),
            "threads": self.ent_threads.get(),
            "headless": self.chk_headless.get(),
            "warmup": self.chk_warmup.get(),
            "cancel_old": self.chk_cancel_old.get(),
            "target": self.ent_target.get(),
            "min_delay": self.ent_min_delay.get(),
            "max_delay": self.ent_max_delay.get(),
            "browse_web": self.chk_browse_web.get(),
            "interact_page": self.chk_interact_page.get(),
            "check_notif": self.chk_check_notif.get(),
            "chat_react": self.chk_chat_react.get(),
            "tele_token": self.ent_tele_token.get().strip(),
            "tele_chatid": self.ent_tele_chatid.get().strip(),
            # Lưu thêm phần cấu hình Reg nick đa nền tảng
            "reg_fb": self.chk_reg_fb.get() if hasattr(self, 'chk_reg_fb') else False,
            "reg_tiktok": self.chk_reg_tiktok.get() if hasattr(self, 'chk_reg_tiktok') else False,
            "reg_insta": self.chk_reg_insta.get() if hasattr(self, 'chk_reg_insta') else False,
            "reg_pass": self.ent_reg_pass.get().strip() if hasattr(self, 'ent_reg_pass') else "",
            "reg_mails": self.txt_reg_mails.get("1.0", "end").strip() if hasattr(self, 'txt_reg_mails') else ""
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "selected_theme" in data and data["selected_theme"] in THEMES:
                self.cbo_theme.set(data["selected_theme"])
                self.apply_theme(data["selected_theme"])
            if "accounts" in data: self.txt_accounts.insert("1.0", data["accounts"])
            if "proxies" in data: self.txt_proxies.insert("1.0", data["proxies"])
            if "targets" in data: self.txt_targets.insert("1.0", data["targets"])
            if "selected_modes" in data and hasattr(self, 'mode_vars'):
                for k, val in data["selected_modes"].items():
                    if k in self.mode_vars:
                        self.mode_vars[k].set(val)
            if "proxy_mode" in data: self.proxy_mode.set(data["proxy_mode"])
            if "proxy_ratio" in data: self.ent_proxy_ratio.delete(0, "end"); self.ent_proxy_ratio.insert(0, data["proxy_ratio"])
            if "threads" in data: self.ent_threads.delete(0, "end"); self.ent_threads.insert(0, data["threads"])
            if "headless" in data: self.chk_headless.set(data["headless"])
            if "warmup" in data: self.chk_warmup.set(data["warmup"])
            if "cancel_old" in data: self.chk_cancel_old.set(data["cancel_old"])
            if "target" in data: self.ent_target.delete(0, "end"); self.ent_target.insert(0, data["target"])
            if "min_delay" in data: self.ent_min_delay.delete(0, "end"); self.ent_min_delay.insert(0, data["min_delay"])
            if "max_delay" in data: self.ent_max_delay.delete(0, "end"); self.ent_max_delay.insert(0, data["max_delay"])
            if "browse_web" in data: self.chk_browse_web.set(data["browse_web"])
            if "interact_page" in data: self.chk_interact_page.set(data["interact_page"])
            if "check_notif" in data: self.chk_check_notif.set(data["check_notif"])
            if "chat_react" in data: self.chk_chat_react.set(data["chat_react"])
            if "tele_token" in data: self.ent_tele_token.delete(0, "end"); self.ent_tele_token.insert(0, data["tele_token"])
            if "tele_chatid" in data: self.ent_tele_chatid.delete(0, "end"); self.ent_tele_chatid.insert(0, data["tele_chatid"])
            
            # Khôi phục dữ liệu Reg nick
            if "reg_fb" in data and hasattr(self, 'chk_reg_fb'): self.chk_reg_fb.set(data["reg_fb"])
            if "reg_tiktok" in data and hasattr(self, 'chk_reg_tiktok'): self.chk_reg_tiktok.set(data["reg_tiktok"])
            if "reg_insta" in data and hasattr(self, 'chk_reg_insta'): self.chk_reg_insta.set(data["reg_insta"])
            if "reg_pass" in data and hasattr(self, 'ent_reg_pass'): 
                self.ent_reg_pass.delete(0, "end")
                self.ent_reg_pass.insert(0, data["reg_pass"])
            if "reg_mails" in data and hasattr(self, 'txt_reg_mails'): 
                self.txt_reg_mails.insert("1.0", data["reg_mails"])
        except Exception:
            pass
# [KẾT THÚC THAY THẾ]


    def on_close(self):
        try:
            self.is_running = False
            self.save_settings()
        except Exception:
            pass
        finally:
            self.root.destroy()
            os._exit(0)

    def import_accounts_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text & CSV", "*.txt *.csv"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.txt_accounts.delete("1.0", "end")
                self.txt_accounts.insert("1.0", f.read())

    def import_proxies_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text & CSV", "*.txt *.csv"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.txt_proxies.delete("1.0", "end")
                self.txt_proxies.insert("1.0", f.read())

    def export_to_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Cảnh báo", "Bảng dữ liệu đang trống!")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV File", "*.csv")])
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["STT", "Tên Nick", "Proxy", "Đã gửi", "Số bạn", "Trạng thái", "Thời gian"])
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in items:
                    vals = list(self.tree.item(item, "values"))
                    vals.append(now_str)
                    writer.writerow(vals)
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo tại:\n{file_path}")
    def reload_table_from_text(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        acc_lines = [l.strip() for l in self.txt_accounts.get("1.0", "end").splitlines() if l.strip() and not l.startswith("#")]
        proxy_lines = [p.strip() for p in self.txt_proxies.get("1.0", "end").splitlines() if p.strip() and not p.startswith("#")]
        ratio = int(self.ent_proxy_ratio.get()) if self.ent_proxy_ratio.get().isdigit() else 20

        for idx, line in enumerate(acc_lines, 1):
            parts = line.split('|')
            acc_name = parts[0] if len(parts) > 0 else f"Nick_{idx}"
            
            # Tự động trích xuất UID từ Cookie nếu có
            uid_found = acc_name
            if len(parts) > 1:
                m = re.search(r'c_user=(\d+)', parts[1])
                if m: uid_found = m.group(1)

            assigned_proxy = "Không dùng"
            if proxy_lines:
                if self.proxy_mode.get() == "random":
                    assigned_proxy = random.choice(proxy_lines)
                else:
                    proxy_idx = (idx - 1) // ratio
                    assigned_proxy = proxy_lines[proxy_idx] if proxy_idx < len(proxy_lines) else proxy_lines[-1]

            # Nạp đủ 8 cột: STT, UID, Tên Nick, 2FA, Proxy, Đã gửi, Số bạn bè, Trạng thái
            self.tree.insert("", "end", iid=str(idx), values=(
                idx, uid_found, acc_name, "None", assigned_proxy, "0", "Chưa kiểm tra", "Sẵn sàng"
            ))

    def start_thread(self):
        self.save_settings()
        self.reload_table_from_text()
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(text="● Đang chạy...", fg="#F59E0B")
        threading.Thread(target=self.run_process, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.log("[!] Đang gửi lệnh dừng đến tất cả các luồng...")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(text="● Đã dừng", fg="#EF4444")

    def run_process(self):
        asyncio.run(self.main_worker())

    async def run_change_password(self, page, acc_name, idx, old_pass, new_pass):
        """Tự động đổi mật khẩu tài khoản qua giao diện Accounts Center"""
        if not old_pass or not new_pass:
            self.log(f"[-] [{acc_name}] Thiếu mật khẩu cũ hoặc mật khẩu mới để đổi!")
            return 0

        self.log(f"[*] [{acc_name}] Đang truy cập trang đổi mật khẩu...")
        try:
            await page.goto("https://accountscenter.facebook.com/password_and_security/password", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            acc_row = page.locator('div[role="button"]:has-text("Facebook"), div[role="link"]:has-text("Facebook")').first
            if await acc_row.count() > 0 and await acc_row.is_visible():
                await acc_row.click()
                await asyncio.sleep(3)

            inputs = await page.locator('input[type="password"]').all()
            if len(inputs) >= 3:
                await inputs[0].fill(old_pass)
                await asyncio.sleep(1)
                await inputs[1].fill(new_pass)
                await asyncio.sleep(1)
                await inputs[2].fill(new_pass)
                await asyncio.sleep(2)

                save_btn = page.locator('div[role="button"]:has-text("Đổi mật khẩu"), div[role="button"]:has-text("Change password"), div[role="button"]:has-text("Lưu thay đổi")').first
                if await save_btn.count() > 0 and await save_btn.is_visible():
                    await save_btn.click()
                    await asyncio.sleep(6)
                    self.log(f"[✔] [{acc_name}] Đổi mật khẩu thành công: {new_pass}")
                    return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy biểu mẫu đổi mật khẩu.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi đổi mật khẩu: {e}")
        return 0

    async def run_enable_2fa(self, page, acc_name, idx):
        """Tự động truy cập bật xác thực 2 yếu tố (2FA) và lấy Secret Key"""
        self.log(f"[*] [{acc_name}] Đang mở cài đặt xác thực 2 yếu tố (2FA)...")
        try:
            await page.goto("https://accountscenter.facebook.com/password_and_security/two_factor", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            acc_row = page.locator('div[role="button"]:has-text("Facebook"), div[role="link"]:has-text("Facebook")').first
            if await acc_row.count() > 0 and await acc_row.is_visible():
                await acc_row.click()
                await asyncio.sleep(3)

            app_auth = page.locator('div[role="button"]:has-text("Ứng dụng xác thực"), div[role="button"]:has-text("Authentication app")').first
            if await app_auth.count() > 0 and await app_auth.is_visible():
                await app_auth.click()
                await asyncio.sleep(3)

            body_text = await page.inner_text("body")
            key_match = re.search(r'([A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4}\s?[A-Z2-7]{4})', body_text)
            if key_match:
                secret_key = key_match.group(1).replace(" ", "").upper()
                with open("2fa_keys_saved.txt", "a", encoding="utf-8") as f:
                    f.write(f"{acc_name}|{secret_key}\n")
                self.log(f"[✔] [{acc_name}] Lấy 2FA Key thành công: {secret_key}")
                return 1
            self.log(f"[-] [{acc_name}] Không lấy được chuỗi 2FA Secret Key.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi bật 2FA: {e}")
        return 0

    async def run_logout_other_sessions(self, page, acc_name, idx):
        """Tự động đăng xuất tất cả các thiết bị/phiên đăng nhập khác"""
        self.log(f"[*] [{acc_name}] Đang kiểm tra danh sách phiên đăng nhập...")
        try:
            await page.goto("https://accountscenter.facebook.com/password_and_security/login_activity", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            acc_row = page.locator('div[role="button"]:has-text("Facebook"), div[role="link"]:has-text("Facebook")').first
            if await acc_row.count() > 0 and await acc_row.is_visible():
                await acc_row.click()
                await asyncio.sleep(3)

            select_all_btn = page.locator('div[role="button"]:has-text("Chọn tất cả"), div[role="button"]:has-text("Select all")').first
            if await select_all_btn.count() > 0 and await select_all_btn.is_visible():
                await select_all_btn.click()
                await asyncio.sleep(2)

                logout_btn = page.locator('div[role="button"]:has-text("Đăng xuất"), div[role="button"]:has-text("Log out")').first
                if await logout_btn.count() > 0 and await logout_btn.is_visible():
                    await logout_btn.click()
                    await asyncio.sleep(3)
                    self.log(f"[✔] [{acc_name}] Đã đăng xuất toàn bộ thiết bị cũ lạ!")
                    return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy nút đăng xuất thiết bị.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi xóa session cũ: {e}")
        return 0
    async def run_add_page_admin(self, page, acc_name, idx, page_url, target_uid_or_name):
        """Tự động cấp quyền Quản trị viên / Biên tập viên cho Fanpage Profile"""
        if not page_url or not target_uid_or_name:
            self.log(f"[-] [{acc_name}] Thiếu Link Page hoặc UID/Tên nick cần thêm Admin!")
            return 0
        self.log(f"[*] [{acc_name}] Đang mở cài đặt cấp quyền Page: {page_url}...")
        try:
            settings_url = page_url.rstrip('/') + "/settings/?tab=profile_access"
            await page.goto(settings_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            # Bấm Thêm người mới (Add new)
            add_btn = page.locator('div[role="button"]:has-text("Thêm mới"), div[role="button"]:has-text("Add new"), div[aria-label="Thêm mới"]').first
            if await add_btn.count() > 0 and await add_btn.is_visible():
                await add_btn.click()
                await asyncio.sleep(2)
                
                next_btn = page.locator('div[role="button"]:has-text("Tiếp"), div[role="button"]:has-text("Next")').first
                if await next_btn.count() > 0: await next_btn.click()
                await asyncio.sleep(2)

                # Tìm và chọn UID/Tên cần phân quyền
                search_input = page.locator('input[placeholder*="Tìm kiếm"], input[placeholder*="Search"]').first
                if await search_input.count() > 0:
                    await search_input.fill(target_uid_or_name)
                    await asyncio.sleep(3)
                    
                    user_res = page.locator('div[role="listbox"] div[role="option"], div[role="button"]:has-text("' + target_uid_or_name + '")').first
                    if await user_res.count() > 0:
                        await user_res.click()
                        await asyncio.sleep(2)

                        give_access = page.locator('div[role="button"]:has-text("Cấp quyền truy cập"), div[role="button"]:has-text("Give access")').first
                        if await give_access.count() > 0:
                            await give_access.click()
                            await asyncio.sleep(4)
                            self.log(f"[✔] [{acc_name}] Đã gửi lời mời Admin Page cho: {target_uid_or_name}")
                            return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy mục quản lý quyền Page.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi phân quyền Admin Page: {e}")
        return 0

    async def run_update_page_info(self, page, acc_name, idx, page_url, new_page_name):
        """Tự động đổi tên Fanpage theo yêu cầu"""
        if not page_url or not new_page_name:
            self.log(f"[-] [{acc_name}] Thiếu link Page hoặc Tên mới cần đổi!")
            return 0
        self.log(f"[*] [{acc_name}] Đang truy cập cài đặt đổi tên Page: {new_page_name}...")
        try:
            settings_url = page_url.rstrip('/') + "/settings/?tab=general"
            await page.goto(settings_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            edit_btn = page.locator('div[role="button"]:has-text("Chỉnh sửa"), div[role="button"]:has-text("Edit")').first
            if await edit_btn.count() > 0:
                await edit_btn.click()
                await asyncio.sleep(2)

                name_input = page.locator('input[name="name"], input[aria-label*="Tên"]').first
                if await name_input.count() > 0:
                    await name_input.fill("")
                    await name_input.fill(new_page_name)
                    await asyncio.sleep(2)

                    review_btn = page.locator('div[role="button"]:has-text("Xem lại thay đổi"), div[role="button"]:has-text("Review change")').first
                    if await review_btn.count() > 0:
                        await review_btn.click()
                        await asyncio.sleep(4)
                        self.log(f"[✔] [{acc_name}] Đã gửi yêu cầu đổi tên Page: {new_page_name}")
                        return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy nút chỉnh sửa tên Page.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi đổi tên Page: {e}")
        return 0

    async def run_invite_friends_like_page(self, page, acc_name, idx, page_url):
        """Mời toàn bộ danh sách bạn bè thích Fanpage"""
        if not page_url:
            self.log(f"[-] [{acc_name}] Thiếu đường dẫn Fanpage để mời bạn!")
            return 0
        self.log(f"[*] [{acc_name}] Đang mở Fanpage để mời bạn bè like: {page_url}...")
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            # Mở menu 3 chấm trên Page
            more_btn = page.locator('div[aria-label="Xem thêm tùy chọn"], div[aria-label="More options"], div[aria-label="Khác"]').first
            if await more_btn.count() > 0:
                await more_btn.click()
                await asyncio.sleep(2)

            invite_btn = page.locator('div[role="menuitem"]:has-text("Mời bạn bè"), div[role="menuitem"]:has-text("Invite friends")').first
            if await invite_btn.count() > 0:
                await invite_btn.click()
                await asyncio.sleep(3)

                select_all = page.locator('div[role="checkbox"]:has-text("Chọn tất cả"), div[role="checkbox"]:has-text("Select all")').first
                if await select_all.count() > 0:
                    await select_all.click()
                    await asyncio.sleep(2)

                send_invites = page.locator('div[role="button"]:has-text("Gửi lời mời"), div[role="button"]:has-text("Send invites")').first
                if await send_invites.count() > 0:
                    await send_invites.click()
                    await asyncio.sleep(4)
                    self.log(f"[✔] [{acc_name}] Đã gửi lời mời thích Page thành công!")
                    return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy chức năng mời bạn bè thích Page.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi mời like Page: {e}")
        return 0

    async def run_inbox_post_commenters(self, page, acc_name, idx, post_url, message_content, max_inbox=10):
        """Tự động quét người bình luận trên bài viết và gửi tin nhắn trực tiếp"""
        if not post_url or not message_content:
            self.log(f"[-] [{acc_name}] Thiếu link bài viết hoặc nội dung tin nhắn!")
            return 0
        self.log(f"[*] [{acc_name}] Đang mở bài viết để quét người comment: {post_url}...")
        sent_count = 0
        try:
            await page.goto(post_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            # Cuộn trang nhẹ để tải bình luận
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(3)

            # Tìm các nút 'Gửi tin nhắn' hoặc 'Phản hồi trong tin nhắn' trên bình luận
            msg_btns = page.locator('div[role="button"]:has-text("Nhắn tin"), div[role="button"]:has-text("Message"), div[aria-label*="Nhắn tin"]')
            count = await msg_btns.count()

            for i in range(min(count, max_inbox)):
                if not self.is_running: break
                btn = msg_btns.nth(i)
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)

                    # Nhập nội dung tin nhắn (hỗ trợ spin-tax)
                    spun_text = spin_text(message_content)
                    input_box = page.locator('div[role="textbox"][contenteditable="true"]').first
                    if await input_box.count() > 0:
                        await input_box.fill(spun_text)
                        await asyncio.sleep(1)
                        await page.keyboard.press("Enter")
                        sent_count += 1
                        self.log(f"[✔] [{acc_name}] Đã gửi tin nhắn cho khách hàng {i+1}: {spun_text[:30]}...")
                        await asyncio.sleep(random.randint(10, 20))
            return sent_count
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi nhắn tin người comment: {e}")
        return sent_count

    async def run_post_joined_groups(self, page, acc_name, idx, post_content, max_groups=5):
        """Tự động đăng bài lên các nhóm mà nick đã tham gia"""
        if not post_content:
            self.log(f"[-] [{acc_name}] Thiếu nội dung bài đăng!")
            return 0
        self.log(f"[*] [{acc_name}] Đang truy cập danh sách nhóm đã tham gia...")
        posted_count = 0
        try:
            await page.goto("https://www.facebook.com/groups/joins", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            group_links = await page.eval_on_selector_all(
                'a[href*="/groups/"]',
                'elements => elements.map(e => e.href).filter(h => !h.includes("/joins") && !h.includes("/feed"))'
            )
            unique_groups = list(dict.fromkeys(group_links))[:max_groups]

            for g_url in unique_groups:
                if not self.is_running: break
                self.log(f"[*] [{acc_name}] Đang đăng bài vào nhóm: {g_url}...")
                await page.goto(g_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(4)

                post_box = page.locator('div[role="button"]:has-text("Bạn viết gì đi..."), div[role="button"]:has-text("Write something..."), div[aria-label*="Tạo bài viết"]').first
                if await post_box.count() > 0:
                    await post_box.click()
                    await asyncio.sleep(2)

                    text_input = page.locator('div[role="textbox"][contenteditable="true"]').first
                    if await text_input.count() > 0:
                        spun_post = spin_text(post_content)
                        await text_input.fill(spun_post)
                        await asyncio.sleep(2)

                        submit_btn = page.locator('div[role="button"]:has-text("Đăng"), div[role="button"]:has-text("Post")').first
                        if await submit_btn.count() > 0:
                            await submit_btn.click()
                            await asyncio.sleep(5)
                            posted_count += 1
                            self.log(f"[✔] [{acc_name}] Đăng bài nhóm thành công!")
                            await asyncio.sleep(random.randint(15, 30))
            return posted_count
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi đăng bài nhóm đã tham gia: {e}")
        return posted_count

    async def run_comment_with_image(self, page, acc_name, idx, target_url, comment_text, image_path):
        """Bình luận kèm hình ảnh sản phẩm vào bài viết"""
        if not target_url:
            self.log(f"[-] [{acc_name}] Thiếu đường dẫn bài viết cần bình luận!")
            return 0
        self.log(f"[*] [{acc_name}] Đang mở bài viết để bình luận ảnh: {target_url}...")
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            # Khung nhập bình luận
            cmt_box = page.locator('div[role="textbox"][contenteditable="true"][aria-label*="bình luận"], div[role="textbox"][contenteditable="true"][aria-label*="Comment"]').first
            if await cmt_box.count() > 0:
                spun_cmt = spin_text(comment_text) if comment_text else "👍"
                await cmt_box.fill(spun_cmt)
                await asyncio.sleep(2)

                # Đính kèm ảnh nếu có đường dẫn hợp lệ
                if image_path and os.path.exists(image_path):
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    if await file_input.count() > 0:
                        await file_input.set_input_files(image_path)
                        await asyncio.sleep(4)

                await page.keyboard.press("Enter")
                await asyncio.sleep(4)
                self.log(f"[✔] [{acc_name}] Đã bình luận kèm ảnh thành công!")
                return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy ô nhập bình luận.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi bình luận kèm ảnh: {e}")
        return 0

    async def run_scrape_group_members(self, page, acc_name, idx, group_url, max_members=100):
        """Quét danh sách thành viên trong nhóm và xuất ra file group_members.txt"""
        if not group_url:
            self.log(f"[-] [{acc_name}] Thiếu đường dẫn Nhóm để quét thành viên!")
            return 0
        self.log(f"[*] [{acc_name}] Đang mở nhóm để quét thành viên: {group_url}...")
        scraped_uids = set()
        try:
            members_url = group_url.rstrip('/') + "/members"
            await page.goto(members_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            scroll_times = 0
            while len(scraped_uids) < max_members and scroll_times < 15 and self.is_running:
                links = await page.eval_on_selector_all(
                    'a[href*="/user/"], a[href*="facebook.com/profile.php?id="]',
                    'elements => elements.map(e => e.href)'
                )
                for link in links:
                    uid_match = re.search(r'id=(\d+)', link) or re.search(r'user/(\d+)', link)
                    if uid_match:
                        scraped_uids.add(uid_match.group(1))

                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
                scroll_times += 1

            if scraped_uids:
                with open("group_members_scraped.txt", "a", encoding="utf-8") as f:
                    for uid in scraped_uids:
                        f.write(f"{uid}\n")
                self.log(f"[✔] [{acc_name}] Đã quét thành công {len(scraped_uids)} UID thành viên (Lưu tại: group_members_scraped.txt)")
                return len(scraped_uids)
            self.log(f"[-] [{acc_name}] Không tìm thấy danh sách thành viên.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi quét thành viên nhóm: {e}")
        return len(scraped_uids)

    async def run_scrape_contact_info(self, page, acc_name, idx, profile_urls):
        """Quét Số điện thoại & Email hiển thị công khai trên phần giới thiệu Profile"""
        if not profile_urls:
            self.log(f"[-] [{acc_name}] Thiếu danh sách Profile để quét thông tin!")
            return 0
        self.log(f"[*] [{acc_name}] Bắt đầu quét thông tin liên hệ...")
        extracted_count = 0
        try:
            for p_url in profile_urls:
                if not self.is_running: break
                about_url = p_url.rstrip('/') + "/about_contact_and_basic_info"
                await page.goto(about_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(3)

                body_text = await page.inner_text("body")
                phones = re.findall(r'(?:0|\+84)[3|5|7|8|9][0-9]{8}', body_text)
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body_text)

                valid_phones = list(set(phones))
                valid_emails = [e for e in list(set(emails)) if "facebook.com" not in e]

                if valid_phones or valid_emails:
                    extracted_count += 1
                    with open("contacts_scraped.txt", "a", encoding="utf-8") as f:
                        f.write(f"{p_url} | SĐT: {', '.join(valid_phones)} | Email: {', '.join(valid_emails)}\n")
                    self.log(f"[✔] [{acc_name}] Tìm thấy: {p_url} (SĐT: {len(valid_phones)}, Mail: {len(valid_emails)})")
                await asyncio.sleep(random.randint(5, 10))
            return extracted_count
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi quét thông tin liên hệ: {e}")
        return extracted_count

    # [BẮT ĐẦU DÁN CÁC HÀM REG NICK VÀO ĐÂY:]
    async def run_reg_facebook_hotmail(self, page, acc_name, proxy_str, hotmail_line):
        """Tự động đăng ký tài khoản Facebook bằng Hotmail/Outlook kèm Proxy"""
        parts = hotmail_line.split('|')
        email = parts[0].strip() if len(parts) > 0 else ""
        mail_pwd = parts[1].strip() if len(parts) > 1 else "DangPhat@2026"
        fb_pwd = self.ent_reg_pass.get().strip() or "FbAuto@2026Secure"
        
        if not email:
            self.log(f"[-] [{acc_name}] Thiếu email Hotmail để tạo nick Facebook!")
            return 0

        self.log(f"[*] [{acc_name}] Bắt đầu Reg Facebook với mail: {email}...")
        try:
            await page.goto("https://www.facebook.com/r.php", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)

            # Điền họ tên ngẫu nhiên
            first_name = random.choice(["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ"])
            last_name = random.choice(["Bảo", "Trâm", "Anh", "Huy", "Linh", "Minh", "Quang", "Vy", "Hải"])
            
            await page.fill('input[name="firstname"]', last_name)
            await page.fill('input[name="lastname"]', first_name)
            await page.fill('input[name="reg_email__"]', email)
            await asyncio.sleep(1)
            
            re_email = page.locator('input[name="reg_email_confirmation__"]')
            if await re_email.count() > 0 and await re_email.is_visible():
                await re_email.fill(email)

            await page.fill('input[name="reg_passwd__"]', fb_pwd)

            # Chọn ngày sinh ngẫu nhiên (18-35 tuổi)
            await page.select_option('select[name="birthday_day"]', str(random.randint(1, 28)))
            await page.select_option('select[name="birthday_month"]', str(random.randint(1, 12)))
            await page.select_option('select[name="birthday_year"]', str(random.randint(1993, 2005)))

            # Giới tính (1: Nữ, 2: Nam)
            gender_val = str(random.choice([1, 2]))
            await page.click(f'input[name="sex"][value="{gender_val}"]')
            await asyncio.sleep(1)

            submit_btn = page.locator('button[name="websubmit"]').first
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await asyncio.sleep(6)
                
                with open("reg_facebook_success.txt", "a", encoding="utf-8") as f:
                    f.write(f"{email}|{fb_pwd}|{mail_pwd}|{proxy_str}\n")
                self.log(f"[✔] [{acc_name}] Reg Facebook thành công: {email}|{fb_pwd}")
                return 1
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi Reg Facebook: {e}")
        return 0

    async def run_reg_tiktok(self, page, acc_name, proxy_str, mail_line):
        """Tự động đăng ký nick TikTok bằng Email"""
        parts = mail_line.split('|')
        email = parts[0].strip() if len(parts) > 0 else ""
        pwd = self.ent_reg_pass.get().strip() or "TikTok@2026Secure"
        if not email: return 0

        self.log(f"[*] [{acc_name}] Đang mở trang đăng ký TikTok: {email}...")
        try:
            await page.goto("https://www.tiktok.com/signup/phone-or-email/email", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            email_inp = page.locator('input[name="email"], input[placeholder*="Email"]').first
            pwd_inp = page.locator('input[type="password"]').first
            
            if await email_inp.count() > 0 and await pwd_inp.count() > 0:
                await email_inp.fill(email)
                await asyncio.sleep(1)
                await pwd_inp.fill(pwd)
                await asyncio.sleep(1)

                send_code_btn = page.locator('button:has-text("Gửi mã"), button:has-text("Send code")').first
                if await send_code_btn.count() > 0:
                    await send_code_btn.click()
                    with open("reg_tiktok_pending.txt", "a", encoding="utf-8") as f:
                        f.write(f"{email}|{pwd}|{proxy_str}\n")
                    self.log(f"[✔] [{acc_name}] Đã gửi mã xác nhận TikTok tới: {email}")
                    return 1
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi Reg TikTok: {e}")
        return 0

    async def run_reg_instagram(self, page, acc_name, proxy_str, mail_line):
        """Tự động đăng ký tài khoản Instagram qua Email"""
        parts = mail_line.split('|')
        email = parts[0].strip() if len(parts) > 0 else ""
        pwd = self.ent_reg_pass.get().strip() or "Insta@2026Secure"
        if not email: return 0

        self.log(f"[*] [{acc_name}] Đang mở trang đăng ký Instagram: {email}...")
        try:
            await page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            email_inp = page.locator('input[name="emailOrPhone"]').first
            name_inp = page.locator('input[name="fullName"]').first
            user_inp = page.locator('input[name="username"]').first
            pass_inp = page.locator('input[name="password"]').first

            if await email_inp.count() > 0:
                uname = email.split('@')[0] + str(random.randint(100, 999))
                await email_inp.fill(email)
                await name_inp.fill("Nguyễn " + random.choice(["Vy", "Linh", "Hải", "Bảo"]))
                await user_inp.fill(uname)
                await pass_inp.fill(pwd)
                await asyncio.sleep(2)

                submit_btn = page.locator('button[type="submit"]').first
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    await asyncio.sleep(4)
                    with open("reg_instagram_success.txt", "a", encoding="utf-8") as f:
                        f.write(f"{uname}|{email}|{pwd}|{proxy_str}\n")
                    self.log(f"[✔] [{acc_name}] Tạo Instagram thành công: {uname}")
                    return 1
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi Reg Instagram: {e}")
        return 0
# [KẾT THÚC DÁN HÀM REG]

    async def run_tiktok_keyword_follow_comment(self, page, acc_name, idx, keyword, comment_template, max_videos=5, min_del=25, max_del=50):
        """Tự động tìm kiếm video TikTok: Xử lý popup -> Xem video -> Follow -> Thả tim -> Like Top Comment -> Bình luận"""
        if not keyword:
            self.log(f"[-] [{acc_name}] Thiếu từ khóa tìm kiếm video TikTok!")
            return 0

        self.log(f"[*] [{acc_name}] 🔍 Đang tìm video TikTok theo từ khóa: '{keyword}'...")
        success_count = 0
        try:
            search_url = f"https://www.tiktok.com/search/video?q={quote(keyword)}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(random.randint(4, 6))

            first_video = page.locator('div[data-e2e="search_video-item"], a[href*="/video/"]').first
            if await first_video.count() > 0:
                await first_video.click()
                await asyncio.sleep(4)
            else:
                self.log(f"[-] [{acc_name}] Không tìm thấy video với từ khóa '{keyword}'.")
                return 0

            for v_idx in range(max_videos):
                if not self.is_running:
                    break

                # Đóng popup nếu xuất hiện
                popup_close = page.locator('div[data-e2e="modal-close-inner-button"], button:has-text("Không phải bây giờ"), button[aria-label="Đóng"]').first
                if await popup_close.count() > 0 and await popup_close.is_visible():
                    await popup_close.click()

                # Xem video đệm (8 - 14s)
                watch_time = random.randint(8, 14)
                self.log(f"[*] [{acc_name}] [Video {v_idx+1}/{max_videos}] Đang xem video ({watch_time}s)...")
                await asyncio.sleep(watch_time)

                # Follow chủ kênh
                follow_btn = page.locator('button:has-text("Follow"), button:has-text("Theo dõi"), button[data-e2e="feed-follow"]').first
                if await follow_btn.count() > 0 and await follow_btn.is_visible():
                    btn_txt = await follow_btn.inner_text()
                    if "Follow" in btn_txt or "Theo dõi" in btn_txt:
                        await follow_btn.click()
                        await asyncio.sleep(random.randint(1, 3))

                # Thả tim video
                like_btn = page.locator('span[data-e2e="like-icon"], button[aria-label*="Like"], button[aria-label*="Thích"]').first
                if await like_btn.count() > 0 and await like_btn.is_visible():
                    await like_btn.click()
                    await asyncio.sleep(1)

                # Like 1 bình luận top
                cmt_like_btn = page.locator('div[data-e2e="comment-like-icon"]').first
                if await cmt_like_btn.count() > 0 and await cmt_like_btn.is_visible():
                    await cmt_like_btn.click()
                    await asyncio.sleep(1)

                # Gõ bình luận Spin-tax
                cmt_box = page.locator('div[contenteditable="true"][data-e2e="comment-input"], div[aria-label*="Thêm bình luận"]').first
                if await cmt_box.count() > 0:
                    await cmt_box.click()
                    await asyncio.sleep(1)

                    spun_comment = spin_text(comment_template)
                    for char in spun_comment:
                        await page.keyboard.type(char, delay=random.randint(40, 100))
                    
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    success_count += 1
                    self.log(f"[✔] [{acc_name}] Đã tương tác & comment video {v_idx+1}: '{spun_comment}'")

                # Giãn cách an toàn trước khi chuyển video
                sleep_delay = random.randint(min_del, max_del)
                self.log(f"[⏳] Nghỉ an toàn {sleep_delay}s...")
                await asyncio.sleep(sleep_delay)

                # Chuyển video kế tiếp
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(3)

            return success_count
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi Seeding TikTok: {e}")
        return success_count

    async def process_account(self, playwright_instance, idx, acc_name, cookie_str, assigned_proxy_str, semaphore):
        async with semaphore:
            if not self.is_running: return

            self.update_tree_row(str(idx), status="Đang chạy...")
            self.log(f"\n[🚀 LUỒNG BẮT ĐẦU] Nick {idx}: {acc_name} (Proxy: {assigned_proxy_str or 'None'})")

            cookies = parse_cookies(cookie_str)
            proxy_cfg = parse_proxy(assigned_proxy_str)
            is_headless = self.chk_headless.get()

            target_total = int(self.ent_target.get())
            min_del = int(self.ent_min_delay.get())
            max_del = int(self.ent_max_delay.get())
            
            
            targets = [l.strip() for l in self.txt_targets.get("1.0", "end").splitlines() if l.strip()]
            if self.proxy_mode.get() == "rotating_api" and self.ent_proxy_api.get().strip():
                self.log(f"[*] [{acc_name}] Đang gửi yêu cầu đổi IP mạng...")
                reset_rotating_proxy(self.ent_proxy_api.get().strip())
                await asyncio.sleep(3)
            
            try:
                browser_exe = get_installed_browser_path()
                launch_kwargs = {
                    "headless": is_headless,
                    "proxy": proxy_cfg,
                    "args": ["--disable-blink-features=AutomationControlled"]
                }
                if browser_exe:
                    launch_kwargs["executable_path"] = browser_exe

                browser = await playwright_instance.chromium.launch(**launch_kwargs)
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                await context.add_cookies(cookies)
                page = await context.new_page()

                if self.chk_browse_web.get(): await self.browse_external_web(page, acc_name)
                if self.chk_warmup.get(): await self.warm_up_feed(page, acc_name)
                if self.chk_watch_reels.get(): await self.watch_facebook_reels(page, acc_name)
                if self.chk_view_stories.get(): await self.view_facebook_stories(page, acc_name)
                if self.chk_check_notif.get(): await self.check_notifications(page, acc_name)
                if self.chk_chat_react.get(): await self.react_messenger(page, acc_name)
                if self.chk_interact_page.get(): await self.interact_fanpage(page, acc_name)
                if self.chk_cancel_old.get(): await self.cancel_old_requests(page, acc_name)

                cur_friends = await self.get_current_friends_count(page)
                self.update_tree_row(str(idx), current_friends=cur_friends)

                total_sent = 0
                mail_lines = [m.strip() for m in self.txt_reg_mails.get("1.0", "end").splitlines() if m.strip()]
                target_mail = mail_lines[idx - 1] if idx <= len(mail_lines) else (mail_lines[0] if mail_lines else "")

                if self.chk_reg_fb.get() and target_mail:
                    await self.run_reg_facebook_hotmail(page, acc_name, assigned_proxy_str, target_mail)
                if self.chk_reg_tiktok.get() and target_mail:
                    await self.run_reg_tiktok(page, acc_name, assigned_proxy_str, target_mail)
                if self.chk_reg_insta.get() and target_mail:
                    await self.run_reg_instagram(page, acc_name, assigned_proxy_str, target_mail)

                if self.mode_vars.get("by_name", tk.BooleanVar()).get():
                    total_sent += await self.run_add_by_name(page, acc_name, idx, target_total, min_del, max_del)

                # 2. Thành viên nhóm
                if self.mode_vars.get("by_group", tk.BooleanVar()).get():
                    total_sent += await self.run_add_by_group(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 3. Theo UID / Profile
                if self.mode_vars.get("by_uid", tk.BooleanVar()).get():
                    total_sent += await self.run_add_by_uid(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 4. Tham gia nhóm
                if self.mode_vars.get("join_group", tk.BooleanVar()).get():
                    await self.run_join_groups(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 5. Tự động đăng bài
                if self.mode_vars.get("auto_post", tk.BooleanVar()).get():
                    await self.run_auto_post(page, acc_name, idx, targets)

                # 6. Tự động gửi tin nhắn
                if self.mode_vars.get("auto_inbox", tk.BooleanVar()).get():
                    await self.run_auto_inbox(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 7. Seeding bài viết nhóm
                if self.mode_vars.get("seed_group", tk.BooleanVar()).get():
                    await self.run_seed_group(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 8. Cập nhật Bio
                if self.mode_vars.get("change_bio", tk.BooleanVar()).get():
                    await self.run_change_bio(page, acc_name, idx, targets)

                # 9. Thay đổi Avatar/Ảnh bìa
                if self.mode_vars.get("change_avatar", tk.BooleanVar()).get():
                    await self.run_change_avatar(page, acc_name, idx, targets)

                # 10. Mời bạn vào nhóm
                if self.mode_vars.get("invite_group", tk.BooleanVar()).get():
                    await self.run_invite_friends_to_group(page, acc_name, idx, targets, target_total, min_del, max_del)

                # 11. Quét UID tương tác
                if self.mode_vars.get("scrape_uid", tk.BooleanVar()).get():
                    await self.run_scrape_uid_post(page, acc_name, idx, targets)

                # 12. Tạo Fanpage
                if self.mode_vars.get("create_page", tk.BooleanVar()).get():
                    await self.run_create_page(page, acc_name, idx, targets)

                # 13. Đăng bài lên Fanpage
                if self.mode_vars.get("post_page", tk.BooleanVar()).get():
                    await self.run_post_page(page, acc_name, idx, targets)

                # 14. Seeding Livestream
                if self.mode_vars.get("seed_live", tk.BooleanVar()).get():
                    await self.run_seed_live(page, acc_name, idx, targets)

                # 15. Đổi mật khẩu
                if self.mode_vars.get("change_pass", tk.BooleanVar()).get():
                    new_pwd = targets[0].strip() if targets else "DangPhat@2026Secure!"
                    await self.run_change_password(page, acc_name, idx, "OldPassMacDinh", new_pwd)

                # 16. Bật 2FA
                if self.mode_vars.get("enable_2fa", tk.BooleanVar()).get():
                    await self.run_enable_2fa(page, acc_name, idx)

                # 17. Đăng xuất thiết bị cũ
                if self.mode_vars.get("logout_sessions", tk.BooleanVar()).get():
                    await self.run_logout_other_sessions(page, acc_name, idx)

                # 18. Thêm Admin Fanpage
                if self.mode_vars.get("add_page_admin", tk.BooleanVar()).get():
                    target_page = targets[0] if len(targets) > 0 else "https://www.facebook.com/me"
                    target_admin = targets[1] if len(targets) > 1 else "UID_HOAC_TEN"
                    await self.run_add_page_admin(page, acc_name, idx, target_page, target_admin)

                # 19. Đổi tên Fanpage
                if self.mode_vars.get("update_page_name", tk.BooleanVar()).get():
                    target_page = targets[0] if len(targets) > 0 else "https://www.facebook.com/me"
                    new_name = targets[1] if len(targets) > 1 else "Fanpage Mới 2026"
                    await self.run_update_page_info(page, acc_name, idx, target_page, new_name)

                # 20. Mời like Page
                if self.mode_vars.get("invite_like_page", tk.BooleanVar()).get():
                    target_page = targets[0] if targets else "https://www.facebook.com/me"
                    await self.run_invite_friends_like_page(page, acc_name, idx, target_page)

                # 21. Nhắn tin người comment
                if self.mode_vars.get("inbox_commenters", tk.BooleanVar()).get():
                    post_link = targets[0] if len(targets) > 0 else "https://www.facebook.com/"
                    msg_txt = targets[1] if len(targets) > 1 else "Chào {bạn|anh|chị}, em tư vấn ạ!"
                    await self.run_inbox_post_commenters(page, acc_name, idx, post_link, msg_txt)

                # 22. Đăng bài group đã vào
                if self.mode_vars.get("post_joined_groups", tk.BooleanVar()).get():
                    post_content = targets[0] if targets else "Nội dung bài viết mẫu {chất lượng|uy tín}!"
                    await self.run_post_joined_groups(page, acc_name, idx, post_content)

                # 23. Bình luận kèm ảnh
                if self.mode_vars.get("comment_with_image", tk.BooleanVar()).get():
                    post_link = targets[0] if len(targets) > 0 else "https://www.facebook.com/"
                    cmt_text = targets[1] if len(targets) > 1 else "{Tư vấn|Quan tâm} ạ!"
                    img_path = targets[2] if len(targets) > 2 else ""
                    await self.run_comment_with_image(page, acc_name, idx, post_link, cmt_text, img_path)

                # 24. Quét member nhóm
                if self.mode_vars.get("scrape_group_members", tk.BooleanVar()).get():
                    group_link = targets[0] if targets else "https://www.facebook.com/groups/feed"
                    await self.run_scrape_group_members(page, acc_name, idx, group_link, max_members=target_total)

                # 25. Quét SĐT/Email
                if self.mode_vars.get("scrape_contacts", tk.BooleanVar()).get():
                    await self.run_scrape_contact_info(page, acc_name, idx, targets)

                # 26. Tương tác từ khóa & Chéo Follow TikTok
                if self.mode_vars.get("tiktok_follow_cmt", tk.BooleanVar()).get():
                    kw = targets[0] if len(targets) > 0 else "người mới xây kênh"
                    cmt_template = targets[1] if len(targets) > 1 else "{Chào bạn|Hello idol|Chào bạn mới|Chào mọi người} {mình cùng kết nối|giao lưu học hỏi|cùng tương tác phát triển|đồng hành cùng nhau} {nhé ạ|nha|nhé bạn|nè} {em mới tập xây kênh|kênh mới tạo mong được giao lưu|cùng cố gắng nhé mn} {❤️|✨|🔥|👏}!"
                    total_sent += await self.run_tiktok_keyword_follow_comment(page, acc_name, idx, kw, cmt_template, max_videos=target_total, min_del=min_del, max_del=max_del)


                await context.close()
                await browser.close()
                self.update_tree_row(str(idx), sent_today=total_sent, status="Hoàn thành")
                self.log(f"[✔ XONG] Nick {acc_name} đã hoàn thành ({total_sent} lời mời).")

            except Exception as e:
                self.update_tree_row(str(idx), status="Lỗi/Checkpoint")
                self.log(f"[-] Lỗi nick {acc_name}: {e}")
                # Bắn cảnh báo về Telegram
                t_token = self.ent_tele_token.get().strip()
                t_id = self.ent_tele_chatid.get().strip()
                if t_token and t_id:
                    send_telegram_alert(t_token, t_id, f"⚠️ CẢNH BÁO: Nick [{acc_name}] gặp sự cố/checkpoint!\nChi tiết: {e}")

    async def main_worker(self):
        acc_lines = [l.strip() for l in self.txt_accounts.get("1.0", "end").splitlines() if l.strip() and not l.startswith("#")]
        proxy_lines = [p.strip() for p in self.txt_proxies.get("1.0", "end").splitlines() if p.strip() and not p.startswith("#")]

        if not acc_lines:
            self.log("[-] Không có tài khoản nào để chạy!")
            self.stop_bot()
            return

        threads_count = int(self.ent_threads.get()) if self.ent_threads.get().isdigit() else 3
        ratio = int(self.ent_proxy_ratio.get()) if self.ent_proxy_ratio.get().isdigit() else 20
        semaphore = asyncio.Semaphore(threads_count)

        self.log(f"\n{'='*55}\n[⚡] BẮT ĐẦU TIẾN TRÌNH VỚI {threads_count} LUỒNG SONG SONG\n{'='*55}")

        async with async_playwright() as p:
            tasks = []
            for idx, line in enumerate(acc_lines, 1):
                parts = line.split('|')
                acc_name = parts[0] if len(parts) > 0 else f"Nick_{idx}"
                cookie_str = parts[1] if len(parts) > 1 else ""
                if not cookie_str: continue

                assigned_proxy_str = None
                if proxy_lines:
                    if self.proxy_mode.get() == "random":
                        assigned_proxy_str = random.choice(proxy_lines)
                    else:
                        p_idx = (idx - 1) // ratio
                        assigned_proxy_str = proxy_lines[p_idx] if p_idx < len(proxy_lines) else proxy_lines[-1]

                tasks.append(self.process_account(p, idx, acc_name, cookie_str, assigned_proxy_str, semaphore))

            await asyncio.gather(*tasks)

        self.log("\n[🎉] TOÀN BỘ CÁC LUỒNG ĐÃ HOÀN TẤT.")
        # Bắn thông báo hoàn tất về Telegram
        t_token = self.ent_tele_token.get().strip()
        t_id = self.ent_tele_chatid.get().strip()
        if t_token and t_id:
            send_telegram_alert(t_token, t_id, "🎉 THÔNG BÁO: Toàn bộ dàn nick đã hoàn thành tất cả tiến trình!")
        self.stop_bot()

    def check_live_selected(self):
        selected = self.tree.selection() or self.tree.get_children()
        if not selected:
            messagebox.showwarning("Chú ý", "Bảng đang trống!")
            return

        def worker():
            for item in selected:
                vals = list(self.tree.item(item, "values"))
                acc_name = vals[1]
                acc_lines = [l.strip() for l in self.txt_accounts.get("1.0", "end").splitlines() if l.strip()]
                uid = None
                for line in acc_lines:
                    if line.startswith(acc_name):
                        m = re.search(r'c_user=(\d+)', line)
                        if m: uid = m.group(1)
                        break

                if uid:
                    try:
                        url = f"https://graph.facebook.com/{uid}/picture?type=normal"
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            status_live = "Live" if "static.xx.fbcdn.net" not in resp.geturl() else "Checkpoint/Die"
                    except Exception:
                        status_live = "Checkpoint/Die"
                else:
                    status_live = "Không có UID"

                self.update_tree_row(item, status=status_live)
            messagebox.showinfo("Hoàn tất", "Đã kiểm tra xong tình trạng Live/Die.")

        threading.Thread(target=worker, daemon=True).start()

    def open_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn 1 dòng tài khoản để mở Profile!")
            return

        item = selected[0]
        vals = self.tree.item(item, "values")
        acc_name = vals[2] if len(vals) > 2 else vals[1]
        proxy_str = vals[4] if len(vals) > 4 else "Không dùng"

        acc_lines = [l.strip() for l in self.txt_accounts.get("1.0", "end").splitlines() if l.strip()]
        cookie_str = ""
        for line in acc_lines:
            if line.startswith(acc_name):
                parts = line.split('|')
                if len(parts) > 1: cookie_str = parts[1]
                break

        profiles_dir = os.path.join(os.getcwd(), "browser_profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        profile_path = os.path.join(profiles_dir, f"profile_{acc_name}")

        def launch():
            async def run():
                async with async_playwright() as p:
                    proxy_cfg = parse_proxy(proxy_str if proxy_str != "Không dùng" else "")
                    browser_exe = get_installed_browser_path()
                    launch_kwargs = {
                        "user_data_dir": profile_path,
                        "headless": False,
                        "proxy": proxy_cfg,
                        "args": ["--disable-blink-features=AutomationControlled"]
                    }
                    if browser_exe:
                        launch_kwargs["executable_path"] = browser_exe

                    context = await p.chromium.launch_persistent_context(**launch_kwargs)

                    if cookie_str:
                        await context.add_cookies(parse_cookies(cookie_str))
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto("https://www.facebook.com/")
                    while len(context.pages) > 0:
                        await asyncio.sleep(1)
            asyncio.run(run())

        threading.Thread(target=launch, daemon=True).start()

    def get_token_selected(self):
        """Trích xuất Access Token EAAB từ Cookie tài khoản"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn 1 dòng tài khoản để lấy Token!")
            return

        item = selected[0]
        vals = self.tree.item(item, "values")
        acc_name = vals[2] if len(vals) > 2 else vals[1]
        
        acc_lines = [l.strip() for l in self.txt_accounts.get("1.0", "end").splitlines() if l.strip()]
        cookie_str = ""
        for line in acc_lines:
            if line.startswith(acc_name):
                parts = line.split('|')
                if len(parts) > 1: cookie_str = parts[1]
                break

        if not cookie_str:
            messagebox.showerror("Lỗi", "Không tìm thấy chuỗi Cookie của nick này!")
            return

        def extract_worker():
            try:
                req = urllib.request.Request(
                    "https://adsmanager.facebook.com/adsmanager/manage/campaigns",
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Cookie': cookie_str
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html_content = resp.read().decode('utf-8', errors='ignore')
                    token_match = re.search(r'(EAAB\w+)', html_content)
                    
                    if token_match:
                        token = token_match.group(1)
                        self.root.clipboard_clear()
                        self.root.clipboard_append(token)
                        messagebox.showinfo("Thành công", f"Đã lấy được Token EAAB (Đã tự động Copy vào Clipboard):\n\n{token[:45]}...")
                    else:
                        messagebox.showwarning("Thông báo", "Cookie không hợp lệ hoặc không trích xuất được Token EAAB.")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lấy Token: {e}")

        threading.Thread(target=extract_worker, daemon=True).start()

    def generate_2fa_dialog(self):
        """Tạo mã xác thực 2FA 6 số nhanh từ 2FA Private Key"""
        from tkinter import simpledialog
        key_2fa = simpledialog.askstring("Tạo mã 2FA", "Nhập mã bí mật 2FA (Secret Key gồm 16-32 ký tự):")
        if not key_2fa: return
        
        try:
            import struct, time
            clean_secret = key_2fa.replace(" ", "").upper()
            missing_padding = len(clean_secret) % 8
            if missing_padding:
                clean_secret += '=' * (8 - missing_padding)
            
            key_bytes = base64.b32decode(clean_secret, casefold=True)
            time_counter = int(time.time() // 30)
            time_bytes = struct.pack(">Q", time_counter)
            
            h = hmac.new(key_bytes, time_bytes, hashlib.sha1).digest()
            offset = h[19] & 0xF
            code = ((h[offset] & 0x7F) << 24 | (h[offset + 1] & 0xFF) << 16 | (h[offset + 2] & 0xFF) << 8 | (h[offset + 3] & 0xFF)) % 1000000
            str_code = f"{code:06d}"
            
            self.root.clipboard_clear()
            self.root.clipboard_append(str_code)
            messagebox.showinfo("Mã 2FA", f"Mã xác thực 2FA hiện tại: {str_code}\n(Đã tự động Copy)")
        except Exception:
            messagebox.showerror("Lỗi", "Mã 2FA Secret Key không hợp lệ!")

def main():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            saved_key = f.read().strip()
        is_valid, exp_date = verify_license(saved_key)
        if is_valid:
            root = tk.Tk()
            app = MainToolApp(root, exp_date)
            root.mainloop()
            sys.exit(0)

    root = tk.Tk()
    def launch_main():
        root.destroy()
        main_root = tk.Tk()
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            k = f.read().strip()
        _, exp = verify_license(k)
        app = MainToolApp(main_root, exp)
        main_root.mainloop()
        sys.exit(0)

    app = LicenseCheckDialog(root, launch_main)
    root.mainloop()

if __name__ == "__main__":
    main()