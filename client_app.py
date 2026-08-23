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
import subprocess
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
CURRENT_VERSION = "2.0.0"
# Link file version.json trên GitHub raw hoặc hosting cá nhân của bạn
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

                # So sánh phiên bản
                if latest_version > CURRENT_VERSION:
                    confirm = messagebox.askyesno(
                        "Cập nhật tự động",
                        f"Đã có phiên bản mới: v{latest_version} (Bản hiện tại: v{CURRENT_VERSION})\n\n"
                        f"Nội dung mới:\n{changelog}\n\n"
                        "Bạn có muốn phần mềm tự động cập nhật ngay bây giờ không?"
                    )
                    
                    if confirm and download_url:
                        # 1. Tải file .exe mới về lưu tạm thành update.exe
                        temp_file = "update_temp.exe"
                        urllib.request.urlretrieve(download_url, temp_file)

                        # 2. Tạo file kịch bản updater.bat để thay thế file cũ và mở lại app
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
                        os._exit(0) # Tắt ứng dụng hiện tại để file .bat thay thế file mới
    except Exception:
        pass

def get_hwid():
    """Lấy mã định danh phần cứng máy tính duy nhất và bảo mật"""
    unique_parts = []
    
    # 1. Lấy MachineGuid từ Windows Registry (Chuẩn tuyệt đối trên mọi bản Windows)
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        machine_guid, _ = winreg.QueryValueEx(registry_key, "MachineGuid")
        winreg.CloseKey(registry_key)
        if machine_guid:
            unique_parts.append(str(machine_guid).strip())
    except Exception:
        pass

    # 2. Lấy Serial của ổ đĩa C: (Volume Serial Number)
    try:
        vol_cmd = "vol C:"
        output = subprocess.check_output(vol_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")
        match = re.search(r"Serial Number is ([A-Fa-f0-9-]+)", output, re.IGNORECASE)
        if match:
            unique_parts.append(match.group(1).strip())
    except Exception:
        pass

    # 3. Lấy UUID bo mạch chủ qua PowerShell
    try:
        ps_cmd = 'powershell -Command "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"'
        ps_out = subprocess.check_output(ps_cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore").strip()
        if ps_out and "UUID" not in ps_out:
            unique_parts.append(ps_out)
    except Exception:
        pass

    # Ghép và băm thành một chuỗi HWID ngắn gọn 16 ký tự cố định cho từng máy
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

        # 1. Tính toán lại ngày hết hạn
        days_offset = int(days_hex, 16)
        epoch = datetime(2026, 1, 1)
        expire_at = epoch + timedelta(days=days_offset)

        # 2. Xác thực chữ ký băm với HWID hiện tại
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


class MainToolApp:
    def __init__(self, root, expire_date):
        self.root = root
        self.root.title(f"Facebook Auto Add Friends Pro v{CURRENT_VERSION} - Hạn dùng: {expire_date}")
        self.root.geometry("1060x860")
        self.is_running = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        tab_control = ttk.Notebook(root)
        self.tab_main = ttk.Frame(tab_control)
        self.tab_data = ttk.Frame(tab_control)
        tab_control.add(self.tab_main, text=" Bảng điều khiển & Cấu hình ")
        tab_control.add(self.tab_data, text=" Thống kê & Quản lý nick ")
        tab_control.pack(expand=1, fill="both", padx=5, pady=5)

        self._build_tab_main()
        self._build_tab_data()
        self.load_settings()

        # Kiểm tra bản cập nhật online
        threading.Thread(target=check_for_updates, daemon=True).start()

    def _build_tab_main(self):
        frame_top = ttk.Frame(self.tab_main)
        frame_top.pack(fill="both", expand=True, padx=5, pady=5)

        frame_acc = ttk.LabelFrame(frame_top, text=" 1. Danh sách Cookie Nick (Tên|Cookie) ")
        frame_acc.pack(side="left", fill="both", expand=True, padx=5)
        
        frame_acc_btns = ttk.Frame(frame_acc)
        frame_acc_btns.pack(fill="x", padx=5, pady=2)
        ttk.Button(frame_acc_btns, text="📁 Nhập .txt", command=self.import_accounts_file).pack(side="left", padx=2)
        ttk.Button(frame_acc_btns, text="🧹 Xóa", command=lambda: self.txt_accounts.delete("1.0", "end")).pack(side="right", padx=2)

        self.txt_accounts = scrolledtext.ScrolledText(frame_acc, height=8)
        self.txt_accounts.pack(fill="both", expand=True, padx=5, pady=5)

        frame_proxy = ttk.LabelFrame(frame_top, text=" 2. Danh sách Proxy (IP:Port hoặc IP:Port:User:Pass) ")
        frame_proxy.pack(side="right", fill="both", expand=True, padx=5)

        frame_proxy_btns = ttk.Frame(frame_proxy)
        frame_proxy_btns.pack(fill="x", padx=5, pady=2)
        ttk.Button(frame_proxy_btns, text="📁 Nhập Proxy .txt", command=self.import_proxies_file).pack(side="left", padx=2)
        ttk.Button(frame_proxy_btns, text="🧹 Xóa", command=lambda: self.txt_proxies.delete("1.0", "end")).pack(side="right", padx=2)

        self.txt_proxies = scrolledtext.ScrolledText(frame_proxy, height=6)
        self.txt_proxies.pack(fill="both", expand=True, padx=5, pady=5)

        frame_proxy_cfg = ttk.Frame(frame_proxy)
        frame_proxy_cfg.pack(fill="x", padx=5, pady=2)
        self.proxy_mode = tk.StringVar(value="fixed_ratio")
        ttk.Radiobutton(frame_proxy_cfg, text="Cố định", variable=self.proxy_mode, value="fixed_ratio").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(frame_proxy_cfg, text="Random", variable=self.proxy_mode, value="random").grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(frame_proxy_cfg, text="Số nick/Proxy:").grid(row=0, column=2, padx=5)
        self.ent_proxy_ratio = ttk.Entry(frame_proxy_cfg, width=4)
        self.ent_proxy_ratio.insert(0, "20")
        self.ent_proxy_ratio.grid(row=0, column=3, padx=2)

        frame_mode = ttk.LabelFrame(self.tab_main, text=" 3. Phương thức Tìm kiếm Khách hàng Mục tiêu ")
        frame_mode.pack(fill="x", padx=10, pady=5)

        self.add_mode = tk.StringVar(value="by_name")
        ttk.Radiobutton(frame_mode, text="1. Tìm kiếm theo Tên ngẫu nhiên", variable=self.add_mode, value="by_name").grid(row=0, column=0, sticky="w", padx=10, pady=4)
        ttk.Radiobutton(frame_mode, text="2. Thành viên Nhóm Facebook (Group)", variable=self.add_mode, value="by_group").grid(row=0, column=1, sticky="w", padx=10, pady=4)
        ttk.Radiobutton(frame_mode, text="3. Danh sách UID / Link Profile", variable=self.add_mode, value="by_uid").grid(row=0, column=2, sticky="w", padx=10, pady=4)
        ttk.Radiobutton(frame_mode, text="4. Tự động Tham gia Nhóm (Join Groups)", variable=self.add_mode, value="join_group").grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=4)
        ttk.Radiobutton(frame_mode, text="5. Tự động Đăng bài (Auto Post Timeline)", variable=self.add_mode, value="auto_post").grid(row=1, column=2, sticky="w", padx=10, pady=4)

        frame_targets = ttk.Frame(frame_mode)
        frame_targets.pack(fill="x", padx=10, pady=4)
        ttk.Label(frame_targets, text="Nhập Link/ID Group HOẶC Danh sách UID (Mỗi dòng 1 mục):").pack(anchor="w")
        self.txt_targets = scrolledtext.ScrolledText(frame_targets, height=4)
        self.txt_targets.pack(fill="x", expand=True, pady=2)

        frame_system = ttk.LabelFrame(self.tab_main, text=" 4. Luồng & Nuôi Nick Chống Checkpoint ")
        frame_system.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_system, text="Số luồng chạy song song:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ent_threads = ttk.Entry(frame_system, width=4)
        self.ent_threads.insert(0, "3")
        self.ent_threads.grid(row=0, column=1, padx=2, sticky="w")

        self.chk_headless = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_system, text="Chạy ẩn trình duyệt", variable=self.chk_headless).grid(row=0, column=2, padx=15, sticky="w")

        self.chk_warmup = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_system, text="Lướt Newfeed đệm (30s)", variable=self.chk_warmup).grid(row=0, column=3, padx=15, sticky="w")

        self.chk_cancel_old = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_system, text="Hủy lời mời cũ", variable=self.chk_cancel_old).grid(row=0, column=4, padx=15, sticky="w")

        self.chk_watch_reels = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_system, text="Xem Reels Video", variable=self.chk_watch_reels).grid(row=1, column=2, padx=15, pady=4, sticky="w")

        self.chk_view_stories = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_system, text="Xem Story bạn bè", variable=self.chk_view_stories).grid(row=1, column=3, padx=15, pady=4, sticky="w")
        frame_cfg = ttk.LabelFrame(self.tab_main, text=" 5. Thông số gửi kết bạn ")
        frame_cfg.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_cfg, text="Chỉ tiêu bạn/nick:").grid(row=0, column=0, padx=5, pady=5)
        self.ent_target = ttk.Entry(frame_cfg, width=6)
        self.ent_target.insert(0, "25")
        self.ent_target.grid(row=0, column=1, padx=5)

        ttk.Label(frame_cfg, text="Delay click (s):").grid(row=0, column=2, padx=10)
        self.ent_min_delay = ttk.Entry(frame_cfg, width=4)
        self.ent_min_delay.insert(0, "15")
        self.ent_min_delay.grid(row=0, column=3, padx=2)
        ttk.Label(frame_cfg, text="-").grid(row=0, column=4)
        self.ent_max_delay = ttk.Entry(frame_cfg, width=4)
        self.ent_max_delay.insert(0, "35")
        self.ent_max_delay.grid(row=0, column=5, padx=2)

        frame_btns = ttk.Frame(self.tab_main)
        frame_btns.pack(fill="x", padx=10, pady=5)



        self.btn_start = ttk.Button(frame_btns, text="▶ BẮT ĐẦU CHẠY", command=self.start_thread)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_stop = ttk.Button(frame_btns, text="⏹ DỪNG LẠI", command=self.stop_bot, state="disabled")
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=5)
        # Thanh tiến độ tổng quan %
        self.progress_bar = ttk.Progressbar(self.tab_main, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        frame_log = ttk.LabelFrame(self.tab_main, text=" Nhật ký hoạt động ")
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.txt_log = scrolledtext.ScrolledText(frame_log, height=5, state="disabled", bg="#fcfcfc")
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

    def _build_tab_data(self):
        frame_tools = ttk.LabelFrame(self.tab_data, text=" Công cụ Bảng dữ liệu & Báo cáo ")
        frame_tools.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_tools, text="Bạn bè từ:").pack(side="left", padx=5, pady=5)
        self.ent_min_friends = ttk.Entry(frame_tools, width=6)
        self.ent_min_friends.insert(0, "0")
        self.ent_min_friends.pack(side="left", padx=2)

        ttk.Label(frame_tools, text="đến:").pack(side="left", padx=5)
        self.ent_max_friends = ttk.Entry(frame_tools, width=6)
        self.ent_max_friends.insert(0, "5000")
        self.ent_max_friends.pack(side="left", padx=2)

        ttk.Button(frame_tools, text="🔍 Lọc", command=self.apply_filter).pack(side="left", padx=5)
        ttk.Button(frame_tools, text="🌐 Open Profile", command=self.open_selected_profile).pack(side="left", padx=3)
        ttk.Button(frame_tools, text="🔍 Check Live/Die", command=self.check_live_selected).pack(side="left", padx=3)
        ttk.Button(frame_tools, text="🔑 Get Token", command=self.get_token_selected).pack(side="left", padx=3)
        ttk.Button(frame_tools, text="🔐 Lấy mã 2FA", command=self.generate_2fa_dialog).pack(side="left", padx=3)
        ttk.Button(frame_tools, text="🔄 Nạp vào Bảng", command=self.reload_table_from_text).pack(side="left", padx=3)
        ttk.Button(frame_tools, text="📊 Xuất Báo Cáo", command=self.export_to_csv).pack(side="right", padx=5)

        frame_tree = ttk.Frame(self.tab_data)
        frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "name", "proxy", "sent_today", "current_friends", "status")
        self.tree = ttk.Treeview(frame_tree, columns=columns, show="headings", height=16)

        self.tree.heading("id", text="STT")
        self.tree.heading("name", text="Tên Nick")
        self.tree.heading("proxy", text="Proxy Đang Gán")
        self.tree.heading("sent_today", text="Đã gửi hôm nay")
        self.tree.heading("current_friends", text="Số bạn hiện có")
        self.tree.heading("status", text="Trạng thái")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=120)
        self.tree.column("proxy", width=180)
        self.tree.column("sent_today", width=110, anchor="center")
        self.tree.column("current_friends", width=110, anchor="center")
        self.tree.column("status", width=140, anchor="center")

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="🌐 Mở Trình Duyệt (Open Profile)", command=self.open_selected_profile)
        self.tree_menu.add_command(label="🔍 Kiểm tra Live/Die", command=self.check_live_selected)
        self.tree_menu.add_command(label="🔑 Trích xuất Access Token (EAAB)", command=self.get_token_selected)
        self.tree_menu.add_command(label="🔐 Tạo mã 2FA", command=self.generate_2fa_dialog)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="▶ BẮT ĐẦU CHẠY", command=self.start_thread)
        self.tree_menu.add_command(label="⏹ DỪNG LẠI (STOP)", command=self.stop_bot)

        def _show_popup(event):
            row_id = self.tree.identify_row(event.y)
            if row_id:
                if row_id not in self.tree.selection():
                    self.tree.selection_set(row_id)
                self.tree_menu.post(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", _show_popup)
    def log(self, text):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", f"{text}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def save_settings(self):
        data = {
            "accounts": self.txt_accounts.get("1.0", "end").strip(),
            "proxies": self.txt_proxies.get("1.0", "end").strip(),
            "targets": self.txt_targets.get("1.0", "end").strip(),
            "add_mode": self.add_mode.get(),
            "proxy_mode": self.proxy_mode.get(),
            "proxy_ratio": self.ent_proxy_ratio.get(),
            "threads": self.ent_threads.get(),
            "headless": self.chk_headless.get(),
            "warmup": self.chk_warmup.get(),
            "cancel_old": self.chk_cancel_old.get(),
            "target": self.ent_target.get(),
            "min_delay": self.ent_min_delay.get(),
            "max_delay": self.ent_max_delay.get()
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

            if "accounts" in data: self.txt_accounts.insert("1.0", data["accounts"])
            if "proxies" in data: self.txt_proxies.insert("1.0", data["proxies"])
            if "targets" in data: self.txt_targets.insert("1.0", data["targets"])
            if "add_mode" in data: self.add_mode.set(data["add_mode"])
            if "proxy_mode" in data: self.proxy_mode.set(data["proxy_mode"])
            if "proxy_ratio" in data: self.ent_proxy_ratio.delete(0, "end"); self.ent_proxy_ratio.insert(0, data["proxy_ratio"])
            if "threads" in data: self.ent_threads.delete(0, "end"); self.ent_threads.insert(0, data["threads"])
            if "headless" in data: self.chk_headless.set(data["headless"])
            if "warmup" in data: self.chk_warmup.set(data["warmup"])
            if "cancel_old" in data: self.chk_cancel_old.set(data["cancel_old"])
            if "target" in data: self.ent_target.delete(0, "end"); self.ent_target.insert(0, data["target"])
            if "min_delay" in data: self.ent_min_delay.delete(0, "end"); self.ent_min_delay.insert(0, data["min_delay"])
            if "max_delay" in data: self.ent_max_delay.delete(0, "end"); self.ent_max_delay.insert(0, data["max_delay"])
        except Exception:
            pass

    def on_close(self):
        try:
            self.is_running = False
            self.save_settings()
        except Exception:
            pass
        finally:
            self.root.destroy()
            os._exit(0)  # Ép tắt ngay lập tức toàn bộ tiến trình ngầm và giải phóng bộ nhớ

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
            
            assigned_proxy = "Không dùng"
            if proxy_lines:
                if self.proxy_mode.get() == "random":
                    assigned_proxy = random.choice(proxy_lines)
                else:
                    proxy_idx = (idx - 1) // ratio
                    assigned_proxy = proxy_lines[proxy_idx] if proxy_idx < len(proxy_lines) else proxy_lines[-1]

            self.tree.insert("", "end", iid=str(idx), values=(idx, acc_name, assigned_proxy, "0", "Chưa kiểm tra", "Sẵn sàng"))

    def update_tree_row(self, item_id, sent_today=None, current_friends=None, status=None):
        try:
            curr = list(self.tree.item(item_id, "values"))
            if sent_today is not None: 
                curr[3] = str(sent_today)
                # Tự động tính toán và đẩy thanh tiến độ %
                target_val = int(self.ent_target.get() or 25)
                self.progress_bar['value'] = min(100, int((int(sent_today) / target_val) * 100))
            if current_friends is not None: curr[4] = str(current_friends)
            if status is not None: curr[5] = str(status)
            self.tree.item(item_id, values=curr)
        except Exception:
            pass

    def apply_filter(self):
        try:
            min_f = int(self.ent_min_friends.get())
            max_f = int(self.ent_max_friends.get())
        except ValueError:
            return

        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            f_str = vals[4]
            if f_str.isdigit():
                f_count = int(f_str)
                if min_f <= f_count <= max_f:
                    self.tree.item(item, tags=())
                else:
                    self.tree.detach(item)

    def start_thread(self):
        self.save_settings()
        self.reload_table_from_text()
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_process, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.log("[!] Đang gửi lệnh dừng đến tất cả các luồng...")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def run_process(self):
        asyncio.run(self.main_worker())

    async def warm_up_feed(self, page, acc_name):
        self.log(f"[*] [{acc_name}] Đang tương tác đệm Bảng tin (30s)...")
        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)
            for _ in range(random.randint(3, 4)):
                if not self.is_running: break
                await page.mouse.wheel(0, random.randint(400, 800))
                await asyncio.sleep(random.randint(3, 6))

            like_btns = await page.locator('div[aria-label="Thích"], div[aria-label="Like"]').all()
            if like_btns:
                target_like = random.choice(like_btns[:2])
                if await target_like.is_visible():
                    await target_like.click()
                    await asyncio.sleep(2)
        except Exception:
            pass
    # ---> ĐOẠN CẦN CHÈN THÊM <---
    async def watch_facebook_reels(self, page, acc_name):
        """Tự động mở mục Reels, xem video ngẫu nhiên và like"""
        self.log(f"[*] [{acc_name}] Đang xem Reels Video...")
        try:
            await page.goto("https://www.facebook.com/reel/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            
            # Xem qua 2-3 video ngắn
            for i in range(random.randint(2, 3)):
                if not self.is_running: break
                watch_time = random.randint(8, 15)
                self.log(f"[*] [{acc_name}] Đang xem Reel video {i+1} ({watch_time}s)...")
                await asyncio.sleep(watch_time)

                # Xác suất 50% thả Like video
                if random.choice([True, False]):
                    like_reel_btn = page.locator('div[aria-label="Thích"], div[aria-label="Like"]').first
                    if await like_reel_btn.count() > 0 and await like_reel_btn.is_visible():
                        try:
                            await like_reel_btn.click()
                            await asyncio.sleep(1)
                        except Exception: pass
                
                # Cuộn phím mũi tên xuống để qua video tiếp theo
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(2)
        except Exception:
            pass

    async def view_facebook_stories(self, page, acc_name):
        """Tự động mở xem Story của bạn bè trên trang chủ"""
        self.log(f"[*] [{acc_name}] Đang xem Story...")
        try:
            await page.goto("https://www.facebook.com/stories/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            for _ in range(random.randint(2, 4)):
                if not self.is_running: break
                await asyncio.sleep(random.randint(5, 8))
                # Bấm phím mũi tên phải để sang story kế tiếp
                await page.keyboard.press("ArrowRight")
        except Exception:
            pass
    
    async def cancel_old_requests(self, page, acc_name):
        try:
            await page.goto("https://www.facebook.com/friends/requests/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            view_sent = page.locator('a:has-text("Xem lời mời đã gửi"), a:has-text("View sent requests")')
            if await view_sent.count() > 0 and await view_sent.first.is_visible():
                await view_sent.first.click()
                await asyncio.sleep(3)

            cancel_btns = await page.locator(CANCEL_REQUEST_SELECTORS).all()
            for c_btn in cancel_btns[:10]:
                if not self.is_running: break
                if await c_btn.is_visible():
                    try:
                        await c_btn.click()
                        await asyncio.sleep(2)
                    except Exception:
                        pass
        except Exception:
            pass

    async def get_current_friends_count(self, page):
        try:
            await page.goto("https://www.facebook.com/me/friends", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            page_text = await page.inner_text("body")
            match = re.search(r'([\d\.,]+)\s*(người bạn|friends|bạn bè)', page_text, re.IGNORECASE)
            if match:
                f_clean = match.group(1).replace('.', '').replace(',', '')
                return int(f_clean)
        except Exception:
            pass
        return "N/A"

    async def run_add_by_name(self, page, acc_name, idx, target_total, min_del, max_del):
        total_sent = 0
        shuffled_names = random.sample(SEARCH_KEYWORDS, len(SEARCH_KEYWORDS))
        for kw in shuffled_names:
            if total_sent >= target_total or not self.is_running: break
            limit_for_this_name = random.randint(3, 8)
            sent_this_name = 0

            search_url = f"https://www.facebook.com/search/people/?q={quote(kw)}"
            self.log(f"[*] [{acc_name}] Tìm tên: '{kw}' (Chỉ tiêu: {limit_for_this_name})")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            for _ in range(3):
                if sent_this_name >= limit_for_this_name or total_sent >= target_total or not self.is_running: break
                buttons = await page.locator(ADD_FRIEND_SELECTORS).all()
                for btn in buttons:
                    if not self.is_running: break
                    if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            await btn.click()
                            total_sent += 1
                            sent_this_name += 1
                            self.update_tree_row(str(idx), sent_today=total_sent)
                            delay = random.randint(min_del, max_del)
                            self.log(f"[+] [{acc_name}] Gửi ({total_sent}/{target_total}) - Delay {delay}s...")
                            await asyncio.sleep(delay)
                            if sent_this_name >= limit_for_this_name or total_sent >= target_total: break
                        except Exception:
                            continue
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(3)
        return total_sent

    async def run_add_by_group(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        total_sent = 0
        for group_input in targets:
            if total_sent >= target_total or not self.is_running: break
            group_url = group_input.strip()
            if not group_url.startswith("http"):
                group_url = f"https://www.facebook.com/groups/{group_url}"
            if not group_url.endswith("/"): group_url += "/"
            members_url = group_url + "members"

            self.log(f"[*] [{acc_name}] Đang vào Nhóm: {members_url}")
            await page.goto(members_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            for _ in range(5):
                if total_sent >= target_total or not self.is_running: break
                buttons = await page.locator(ADD_FRIEND_SELECTORS).all()
                for btn in buttons:
                    if not self.is_running: break
                    if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            await btn.click()
                            total_sent += 1
                            self.update_tree_row(str(idx), sent_today=total_sent)
                            delay = random.randint(min_del, max_del)
                            self.log(f"[+] [{acc_name}] (Nhóm) Đã gửi ({total_sent}/{target_total}) - Delay {delay}s...")
                            await asyncio.sleep(delay)
                            if total_sent >= target_total: break
                        except Exception:
                            continue
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(3)
        return total_sent

    async def run_add_by_uid(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        total_sent = 0
        for target in targets:
            if total_sent >= target_total or not self.is_running: break
            t = target.strip()
            profile_url = t if t.startswith("http") else f"https://www.facebook.com/{t}"
            self.log(f"[*] [{acc_name}] Truy cập Profile: {profile_url}")
            
            try:
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(3)
                btn = page.locator(ADD_FRIEND_SELECTORS).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    total_sent += 1
                    self.update_tree_row(str(idx), sent_today=total_sent)
                    delay = random.randint(min_del, max_del)
                    self.log(f"[+] [{acc_name}] (UID) Đã gửi ({total_sent}/{target_total}) - Delay {delay}s...")
                    await asyncio.sleep(delay)
            except Exception:
                pass
        return total_sent
    # ---> ĐOẠN CẦN CHÈN THÊM <---
    async def run_join_groups(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Tự động tìm kiếm nhóm theo từ khóa hoặc link và gửi yêu cầu tham gia"""
        total_joined = 0
        keywords = targets if targets else ["Bất động sản", "Việc làm", "Rao vặt", "Kinh doanh online"]
        
        JOIN_BTN_SELECTORS = (
            'div[role="button"]:has-text("Tham gia nhóm"), '
            'div[role="button"]:has-text("Tham gia"), '
            'div[role="button"]:has-text("Join group"), '
            'div[role="button"]:has-text("Join Group"), '
            'div[aria-label="Tham gia nhóm"], '
            'div[aria-label="Tham gia"]'
        )

        for kw in keywords:
            if total_joined >= target_total or not self.is_running: break
            
            # Nếu khách nhập thẳng Link Group
            if kw.startswith("http"):
                group_url = kw
            else:
                group_url = f"https://www.facebook.com/search/groups/?q={quote(kw)}"

            self.log(f"[*] [{acc_name}] Đang tìm nhóm: '{kw}'")
            try:
                await page.goto(group_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(4)

                for _ in range(3):
                    if total_joined >= target_total or not self.is_running: break
                    join_buttons = await page.locator(JOIN_BTN_SELECTORS).all()
                    
                    for btn in join_buttons:
                        if not self.is_running or total_joined >= target_total: break
                        if await btn.is_visible():
                            try:
                                await btn.scroll_into_view_if_needed()
                                await asyncio.sleep(1)
                                await btn.click()
                                total_joined += 1
                                self.update_tree_row(str(idx), sent_today=total_joined)
                                delay = random.randint(min_del, max_del)
                                self.log(f"[+] [{acc_name}] Đã bấm Tham gia nhóm ({total_joined}/{target_total}) - Delay {delay}s...")
                                await asyncio.sleep(delay)
                            except Exception:
                                continue
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(3)
            except Exception as e:
                self.log(f"[-] Lỗi tìm nhóm {kw}: {e}")
        return total_joined
    # ---> HẾT ĐOẠN CHÈN <---
    # ---> ĐOẠN CẦN CHÈN THÊM <---
    async def run_auto_post(self, page, acc_name, idx, targets):
        """Tự động đăng bài viết lên trang cá nhân Facebook"""
        content_to_post = "\n".join(targets) if targets else "Chào ngày mới mọi người! Chúc cả nhà một ngày tràn đầy năng lượng."
        self.log(f"[*] [{acc_name}] Đang chuẩn bị đăng bài lên trang cá nhân...")

        POST_BOX_SELECTORS = (
            'div[role="button"]:has-text("Bạn đang nghĩ gì?"), '
            'div[role="button"]:has-text("What\'s on your mind?"), '
            'div[aria-label="Tạo bài viết"], '
            'div[aria-label="Create a post"]'
        )
        
        SUBMIT_BTN_SELECTORS = (
            'div[role="button"]:has-text("Đăng"), '
            'div[role="button"]:has-text("Post"), '
            'div[aria-label="Đăng"], '
            'div[aria-label="Post"]'
        )

        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)

            # 1. Bấm mở khung đăng bài
            post_box = page.locator(POST_BOX_SELECTORS).first
            if await post_box.count() > 0 and await post_box.is_visible():
                await post_box.click()
                await asyncio.sleep(3)

                # 2. Nhập nội dung bài viết
                input_area = page.locator('div[role="textbox"][contenteditable="true"]').first
                if await input_area.count() > 0:
                    await input_area.fill(content_to_post)
                    await asyncio.sleep(2)

                    # 3. Bấm nút Đăng
                    post_btn = page.locator(SUBMIT_BTN_SELECTORS).first
                    if await post_btn.count() > 0 and await post_btn.is_visible():
                        await post_btn.click()
                        self.log(f"[✔] [{acc_name}] Đã đăng bài thành công lên trang cá nhân!")
                        self.update_tree_row(str(idx), sent_today="1", status="Đã đăng bài")
                        await asyncio.sleep(5)
                        return 1
            self.log(f"[-] [{acc_name}] Không tìm thấy khung soạn bài viết.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi khi đăng bài: {e}")
        return 0
    # ---> HẾT ĐOẠN CHÈN <---
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
            mode = self.add_mode.get()
            
            targets = [l.strip() for l in self.txt_targets.get("1.0", "end").splitlines() if l.strip()]

            try:
                browser = await playwright_instance.chromium.launch(headless=is_headless, proxy=proxy_cfg)
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                await context.add_cookies(cookies)
                page = await context.new_page()

                if self.chk_warmup.get(): await self.warm_up_feed(page, acc_name)
                if self.chk_watch_reels.get(): await self.watch_facebook_reels(page, acc_name)
                if self.chk_view_stories.get(): await self.view_facebook_stories(page, acc_name)
                if self.chk_cancel_old.get(): await self.cancel_old_requests(page, acc_name)

                cur_friends = await self.get_current_friends_count(page)
                self.update_tree_row(str(idx), current_friends=cur_friends)

                total_sent = 0
                if mode == "by_group":
                    total_sent = await self.run_add_by_group(page, acc_name, idx, targets, target_total, min_del, max_del)
                elif mode == "by_uid":
                    total_sent = await self.run_add_by_uid(page, acc_name, idx, targets, target_total, min_del, max_del)
                elif mode == "join_group":
                    total_sent = await self.run_join_groups(page, acc_name, idx, targets, target_total, min_del, max_del)
                elif mode == "auto_post":
                    total_sent = await self.run_auto_post(page, acc_name, idx, targets)
                else:
                    total_sent = await self.run_add_by_name(page, acc_name, idx, target_total, min_del, max_del)

                await context.close()
                await browser.close()
                self.update_tree_row(str(idx), sent_today=total_sent, status="Hoàn thành")
                self.log(f"[✔ XONG] Nick {acc_name} đã hoàn thành ({total_sent} lời mời).")

            except Exception as e:
                self.update_tree_row(str(idx), status="Lỗi")
                self.log(f"[-] Lỗi nick {acc_name}: {e}")

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
        acc_name = vals[1]
        proxy_str = vals[2]

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
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=profile_path,
                        headless=False,
                        proxy=proxy_cfg,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    if cookie_str:
                        await context.add_cookies(parse_cookies(cookie_str))
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto("https://www.facebook.com/")
                    while len(context.pages) > 0:
                        await asyncio.sleep(1)
            asyncio.run(run())

        threading.Thread(target=launch, daemon=True).start()
        # ---> ĐOẠN CẦN CHÈN THÊM <---
    def get_token_selected(self):
        """Trích xuất Access Token EAAB từ Cookie tài khoản"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn 1 dòng tài khoản để lấy Token!")
            return

        item = selected[0]
        acc_name = self.tree.item(item, "values")[1]
        
        # Tìm cookie của nick
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
                # Gửi request lấy token từ trang Ads Manager của Facebook
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
                        # Tự động sao chép vào Clipboard
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
            # Thuật toán TOTP chuẩn RFC 6238
            import struct, time
            clean_secret = key_2fa.replace(" ", "").upper()
            # Bổ sung padding nếu thiếu
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
    # ---> HẾT ĐOẠN CHÈN <---

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
        root.destroy()  # Đóng sạch cửa sổ kích hoạt cũ trước khi mở app chính
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