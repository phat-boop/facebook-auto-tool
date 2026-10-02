import asyncio
import base64
import contextvars
import csv
import json
import os
import queue
import random
import webbrowser
import re
import subprocess
import sys
import struct
import threading
import hashlib
import winreg
import hmac
import time
import tkinter as tk
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import math
from tkinter import ttk, messagebox, scrolledtext, filedialog
from urllib.parse import quote, urlparse
from urllib.parse import unquote, urljoin
import copy
import ipaddress
import unicodedata
import uuid
from account_history import AccountHistoryStore, safe_proxy_label
from cryptography.fernet import Fernet, InvalidToken
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
# ==================== CẤU HÌNH EVENT LOOP AN TOÀN CHO WINDOWS ====================
# ==================== CẤU HÌNH EVENT LOOP THEO CHUẨN HIỆN ĐẠI ====================
if sys.platform == 'win32':
    # Lấy policy hiện tại của hệ thống để kiểm tra trước
    current_policy = asyncio.get_event_loop_policy()
    if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
        # Chỉ thiết lập lại nếu hệ thống chưa dùng Proactor làm mặc định
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())




# ==================== THÔNG TIN PHIÊN BẢN & BẢO MẬT ====================
CURRENT_VERSION = "2.3.0"
VERSION_CHECK_URL = "https://raw.githubusercontent.com/phat-boop/facebook-auto-tool/refs/heads/main/version.json"

SECRET_SALT = b"FB_TOOL_SECRET_SALT_2026"
LICENSE_API_URL = "https://facebook-tool-license.dangphat-license.workers.dev"
APP_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "FacebookAutoTool",
)
os.makedirs(APP_DATA_DIR, exist_ok=True)
LICENSE_FILE = os.path.join(APP_DATA_DIR, "license.lic")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

def output_path(filename: str) -> str:
    return os.path.join(APP_DATA_DIR, filename)

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

SEARCH_KEYWORDS = [
    "Bảo", "Trâm", "Thư", "Phong", "Hoàng", "Lan Anh", "Diệu", "Mai", "Kiệt", "Huy", 
    "Huyền", "Ngọc", "Quỳnh", "Thanh", "Tùng", "Hà", "Linh", "Duy", "Phương", "Hải", 
    "Nam", "Hạnh", "Thảo", "Vân", "Hương", "Nhung", "Bình", "Cường", "Đức", "Hùng", 
    "Tuấn", "Minh", "Quang", "Thành", "Trung", "Vũ", "Xuân", "Yến", "Anh", "Bích", 
    "Châu", "Diễm", "Giang", "Hiếu", "Hoài", "Hồng", "Khánh", "Kiều", "Lan", "Ngân", 
    "Như", "Trang", "Trinh", "Tú", "Tuệ"
]

HO_VIET = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
DEM_VIET = ["Văn", "Thị", "Đức", "Ngọc", "Thanh", "Minh", "Hữu", "Gia", "Bảo", "Anh", "Quang", "Phương", "Khánh", "Hải", "Tuấn", "Hoài"]
TEN_VIET = [
    "Anh", "Bảo", "Bình", "Châu", "Cường", "Dũng", "Dương", "Duy", "Đạt", "Đức", "Giang", "Hà", "Hải", "Hiếu", "Hoa",
    "Hoàng", "Hùng", "Huy", "Huyền", "Hương", "Khánh", "Khoa", "Kiên", "Kiệt", "Lam", "Lan", "Linh", "Long", "Mai",
    "Minh", "Nam", "Nga", "Ngân", "Ngọc", "Nhung", "Phong", "Phúc", "Phương", "Quân", "Quang", "Quyên", "Quỳnh", "Sơn",
    "Tâm", "Thái", "Thắng", "Thanh", "Thảo", "Thịnh", "Thu", "Thuận", "Thư", "Thương", "Tiến", "Toàn", "Trang", "Trí",
    "Trinh", "Trúc", "Trung", "Tú", "Tuấn", "Tùng", "Uyên", "Vân", "Việt", "Vinh", "Vũ", "Vy", "Yến"
]
HAU_TO_PAGE = ["", " - Blog Cá Nhân", " Cuộc Sống", " Chia Sẻ", " Daily", " Góc Nhỏ", " Kỷ Niệm"]

def generate_random_person_name():
    """Tự động kết hợp ngẫu nhiên tạo ra hơn 500+ tên người Việt Nam thực tế"""
    ho = random.choice(HO_VIET)
    dem = random.choice(DEM_VIET)
    ten = random.choice(TEN_VIET)
    hau_to = random.choice(HAU_TO_PAGE)
    return f"{ho} {dem} {ten}{hau_to}".strip()

ADD_FRIEND_SELECTORS = (
    '[role="main"] [role="button"][data-testid*="add_friend" i], '
    '[role="main"] button[name*="add_friend" i], '
    '[role="main"] [role="button"][data-action*="add_friend" i], '
    'div[role="button"]:has-text("Thêm bạn bè"), '
    'div[role="button"]:has-text("Add friend"), '
    'div[role="button"]:has-text("Add Friend"), '
    'div[role="button"]:has-text("เพิ่มเป็นเพื่อน"), '
    'div[role="button"]:has-text("Tambahkan Teman"), '
    'div[role="button"]:has-text("Magdagdag ng kaibigan"), '
    'div[role="button"]:has-text("友達を追加"), '
    'div[role="button"]:has-text("친구 추가"), '
    'div[aria-label="Thêm bạn bè"], '
    'div[aria-label="Add friend"], '
    'div[aria-label="Add Friend"], '
    'div[aria-label="เพิ่มเป็นเพื่อน"], '
    'div[aria-label="Tambahkan Teman"], '
    'div[aria-label="Magdagdag ng kaibigan"], '
    'div[aria-label="友達を追加"], '
    'div[aria-label="친구 추가"]'
)

FRIEND_REQUEST_SENT_SELECTORS = (
    'div[role="button"]:has-text("Hủy lời mời"), '
    'div[role="button"]:has-text("Hủy yêu cầu"), '
    'div[role="button"]:has-text("Cancel request"), '
    'div[role="button"]:has-text("Request sent"), '
    'div[aria-label="Hủy lời mời"], '
    'div[aria-label="Hủy yêu cầu"], '
    'div[aria-label="Cancel request"], '
    'div[aria-label="Request sent"]'
)

RESULT_FILE_LOCK = threading.Lock()

ACCOUNT_STATUSES = {"UNKNOWN", "CHECKING", "LIVE", "DIE", "ERROR", "CHECKPOINT"}
ACCOUNT_STATUS_LABELS = {
    "UNKNOWN": "CHƯA KIỂM TRA",
    "CHECKING": "ĐANG KIỂM TRA",
    "LIVE": "LIVE",
    "DIE": "DIE",
    "ERROR": "ERROR",
    "CHECKPOINT": "CHECKPOINT",
}
ACCOUNT_STATUS_COLORS = {
    "UNKNOWN": "#94A3B8",
    "CHECKING": "#FACC15",
    "LIVE": "#22C55E",
    "DIE": "#EF4444",
    "ERROR": "#F97316",
    "CHECKPOINT": "#C084FC",
}
ACCOUNT_STATUS_PALETTE = {
    "UNKNOWN": {"background": "#28323C", "foreground": "#E7EDF2"},
    "CHECKING": {"background": "#594418", "foreground": "#FFF3C4"},
    "LIVE": {"background": "#164535", "foreground": "#D5FBE5"},
    "CHECKPOINT": {"background": "#49315D", "foreground": "#F0DEFF"},
    "DIE": {"background": "#57252C", "foreground": "#FFE1E5"},
    "ERROR": {"background": "#623B1D", "foreground": "#FFE9CD"},
}
TASK_RESULTS = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "ERROR", "SKIPPED"}


def configure_account_table_style(style, *trees):
    style.configure("Account.Treeview", rowheight=30, foreground="#E7EDF2", background="#19232C", fieldbackground="#19232C", font=("Segoe UI", 9))
    style.map("Account.Treeview", background=[("selected", "#285D69")], foreground=[("selected", "#FFFFFF")])
    for tree in trees:
        tree.configure(style="Account.Treeview")
        for status, palette in ACCOUNT_STATUS_PALETTE.items():
            tree.tag_configure(status, **palette)


def task_result_status(tasks):
    values = {task.get("status", "PENDING") for task in tasks.values()}
    return next((status for status in ("ERROR", "FAILED", "RUNNING", "PENDING", "SUCCESS", "SKIPPED") if status in values), "PENDING")


def page_wait_label(state):
    remaining = state.get("page_wait_remaining")
    if remaining is None:
        return "-"
    minutes, seconds = divmod(max(0, int(remaining)), 60)
    return f"{minutes:02d}:{seconds:02d} → {state['next_page_at'][11:19]}"


class FriendRequestOutcome(tuple):
    def __new__(cls, status, target, detail):
        result = super().__new__(cls, (status == "SENT", detail))
        result.status, result.target = status, target
        return result


def friend_profile_reference(value):
    value = str(value or "").strip()
    if value.isdigit():
        return value
    parsed = urlparse(urljoin("https://www.facebook.com/", value))
    if parsed.hostname not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        return ""
    path = parsed.path.strip("/")
    if path == "profile.php":
        match = re.search(r'(?:^|&)id=(\d+)(?:&|$)', parsed.query)
        return match.group(1) if match else ""
    if not path or "/" in path or path in {"friends", "search", "groups", "checkpoint", "login", "pages", "settings"}:
        return ""
    return path.casefold()


def classify_friend_controls(controls):
    for value in controls:
        text = " ".join(str(value or "").casefold().split())
        if text in {"pending", "outgoing_pending", "request_sent", "cancel request", "hủy lời mời", "hủy yêu cầu", "ยกเลิกคำขอ", "batalkan permintaan", "友達リクエストをキャンセル", "요청 취소"}:
            return "ALREADY_PENDING"
        if text in {"friends", "friend", "bạn bè", "เพื่อน", "teman", "友達", "친구"}:
            return "ALREADY_FRIEND"
    return "UNKNOWN"


FRIEND_SCOPE_SNAPSHOT = r"""root => ({
    connected: root.isConnected,
    row: Boolean(root.closest('[role="row"], [role="listitem"]')),
    links: Array.from(root.querySelectorAll('a[href]')).map(a => a.href),
    controls: Array.from(root.querySelectorAll('button,[role="button"]')).flatMap(el =>
        [el.getAttribute('data-friendship-status'), el.getAttribute('aria-label'), el.innerText])
})"""


def normalize_ui_text(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def page_creation_notice_matches(text, page_name):
    name = re.escape(normalize_ui_text(page_name))
    if not name:
        return False
    text = normalize_ui_text(text)
    return any(re.search(pattern, text) for pattern in (
        rf"(?<!\w){name}\s+was created(?:[.!]|$|\s+now\b)",
        rf"success!\s+you['’]ve created\s+{name}(?:[.!]|$)",
        rf"(?<!\w){name}\s+đã được tạo(?:[.!]|$)",
        rf"(?:thành công[!:]?\s*)bạn đã tạo\s+{name}(?:[.!]|$)",
    ))


PAGE_CREATION_EVIDENCE = r"""() => {
    const data = document.querySelector('[data-page-id]');
    const deepLink = document.querySelector('meta[property="al:android:url"]');
    const match = (deepLink?.content || '').match(/^fb:\/\/page\/(\d+)/);
    const pageId = data?.getAttribute('data-page-id') || match?.[1] || '';
    const heading = Array.from(document.querySelectorAll('h1'))
        .find(el => el.getClientRects().length > 0);
    return {page_id: pageId, page_type: pageId ? 'PAGE' : '', name: heading?.innerText || '',
        canonical: document.querySelector('link[rel="canonical"]')?.href || ''};
}"""


def verify_page_job_evidence(url, evidence, job, owner_account_id):
    empty = {"url": "", "id": ""}
    if not evidence or not job.get("submitted") or job.get("owner_account_id") != owner_account_id:
        return empty
    identity = extract_facebook_page_identity([url])
    page_id = str(evidence.get("page_id") or "")
    if evidence.get("page_type") != "PAGE" or not page_id.isdigit() or len(page_id) < 5:
        return empty
    if not identity["url"] or (identity["id"] and identity["id"] != page_id):
        return empty
    if normalize_ui_text(evidence.get("name")) != normalize_ui_text(job["page_name"]):
        return empty
    canonical = evidence.get("canonical")
    if canonical and facebook_page_reference(canonical) != facebook_page_reference(url):
        return empty
    if page_id == str(job.get("owner_uid") or "") or page_id in job.get("prior_page_ids", set()):
        return empty
    return {**identity, "id": page_id, "owner_account_id": owner_account_id,
            "page_job_id": job["page_job_id"], "verified": True}
LOGIN_SUCCESS = "SUCCESS"
LOGIN_INVALID = "INVALID"
LOGIN_TECHNICAL_ERROR = "TECHNICAL_ERROR"


class FacebookCheckpointStopped(asyncio.CancelledError):
    """Unwind account automation without being swallowed by action retries."""


async def detect_facebook_account_state(page):
    parsed = urlparse(str(getattr(page, "url", "") or ""))
    host = (parsed.hostname or "").casefold()
    if host != "facebook.com" and not host.endswith(".facebook.com"):
        return "UNKNOWN"
    path = parsed.path.casefold()
    if re.match(r'^/(?:checkpoint|challenge)(?:/|$|\.)', path):
        return "CHECKPOINT"
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return "UNKNOWN"
    try:
        checkpoint_form = await evaluate(r"""() => Array.from(document.forms).some(form => {
        const url = new URL(form.action, location.href);
        return (url.hostname === 'facebook.com' || url.hostname.endsWith('.facebook.com'))
            && /^\/(checkpoint|challenge)(\/|$|\.)/i.test(url.pathname)
            && form.getClientRects().length > 0;
    })""")
    except Exception as exc:
        # A navigation can destroy the old DOM between monitor polls.
        if "execution context was destroyed" in str(exc).casefold():
            return "UNKNOWN"
        raise
    if checkpoint_form:
        return "CHECKPOINT"
    return "UNKNOWN"


def is_page_policy_rejected(text):
    normalized = " ".join(str(text or "").casefold().split())
    return (
        "error occurred while creating the page" in normalized
        and "page policies" in normalized
    )


def save_checkpoint_account(raw_line):
    path = output_path("checkpoint_accounts.txt")
    with RESULT_FILE_LOCK:
        existing = set()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                existing = set(handle.read().splitlines())
        if raw_line and raw_line not in existing:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(raw_line + "\n")

PAGE_FLOW_STATES = {
    "PENDING", "VALIDATING", "SESSION_CHECK", "OPEN_CREATE_PAGE",
    "FILL_PAGE_NAME", "SELECT_CATEGORY", "SUBMITTING", "VERIFYING",
    "SUCCESS", "FAILED", "ERROR", "CANCELLED",
}
PAGE_ACCESS_STATUSES = {"ASSIGNED", "INVITED", "PENDING", "FAILED", "ERROR"}


def split_account_batches(items, batch_size):
    size = max(1, int(batch_size))
    values = list(items)
    return [values[index:index + size] for index in range(0, len(values), size)]


def effective_account_worker_count(
    requested_threads, modes, max_create_page_workers=3, max_bm_workers=None
):
    requested = max(1, int(requested_threads))
    limits = [requested]
    if (modes or {}).get("create_page", False):
        limits.append(max(1, int(max_create_page_workers)))
    if (modes or {}).get("add_page_admin", False):
        bm_limit = max_create_page_workers if max_bm_workers is None else max_bm_workers
        limits.append(max(1, int(bm_limit)))
    return min(limits)


def account_status_for_failure(failure_kind):
    return "DIE" if failure_kind in {"invalid_cookie", "invalid_login"} else "ERROR"


def normalize_account_source_line(raw_line):
    """Normalize only the UI number prefix so account data remains byte-for-byte intact."""
    return re.sub(r'^\s*\d+[\.\-]\s*', '', str(raw_line or "").rstrip("\r\n")).strip()


def account_display_name(account, index):
    """Return a stable label for parsed input and older account-state snapshots."""
    account = account or {}
    return str(
        account.get("name")
        or account.get("account_id")
        or account.get("uid")
        or f"Nick_{index}"
    )


def is_invalid_facebook_account_url(url):
    normalized = str(url or "").casefold()
    return any(
        marker in normalized
        for marker in ("/login", "checkpoint", "challenge", "disabled", "suspended")
    )


def keep_unprocessed_account_lines(lines, processed_source_lines):
    processed = {
        normalize_account_source_line(line)
        for line in (processed_source_lines or [])
        if normalize_account_source_line(line)
    }
    return [
        line for line in (lines or [])
        if normalize_account_source_line(line) not in processed
    ]


def write_create_page_results_xlsx(file_path, categorized_records):
    """Write LIVE/DIE account results to a styled Excel workbook."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        raise RuntimeError("Thiếu thư viện openpyxl để xuất Excel.") from exc

    workbook = Workbook()
    workbook.remove(workbook.active)
    headers = (
        "STT", "UID", "Mật khẩu (Pass)", "Trạng thái", "Page đã tạo",
        "Chỉ tiêu Page", "Kết quả / Lý do", "Thời gian", "Dữ liệu gốc",
    )
    sheet_specs = (
        ("LIVE", categorized_records.get("completed", []), "16A34A"),
        ("DIE", categorized_records.get("die", []), "DC2626"),
    )
    result_key_by_sheet = {"LIVE": "completed", "DIE": "die"}
    for sheet_name, records, accent in sheet_specs:
        if result_key_by_sheet[sheet_name] not in categorized_records:
            continue
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)
        for record in records:
            sheet.append((
                record.get("stt", ""),
                record.get("uid") or record.get("account_id", ""),
                record.get("password") or record.get("pwd", ""),
                sheet_name,
                int(record.get("created_count") or 0),
                int(record.get("target_count") or 0),
                (
                    "Đã tạo đủ Page"
                    if sheet_name == "LIVE"
                    else record.get("reason") or "Tài khoản không còn đăng nhập hợp lệ"
                ),
                record.get("time", ""),
                record.get("raw_line", ""),
            ))

        header_fill = PatternFill("solid", fgColor=accent)
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:H{max(1, sheet.max_row)}"
        sheet.row_dimensions[1].height = 26
        widths = (8, 24, 12, 14, 14, 48, 22, 58)
        for column_index, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(column_index)].width = width

    if not workbook.sheetnames:
        raise ValueError("Không có danh sách LIVE/DIE để xuất Excel.")
    workbook.save(file_path)


class AccountStateStore:
    def __init__(self, history=None):
        self._lock = threading.RLock()
        self._states = {}
        self.history = history

    def _persist(self, state, module="ACCOUNT", event_type="STATE", message=""):
        if self.history is not None:
            self.history.save(state, module, event_type, message)

    def sync(self, accounts):
        with self._lock:
            active_indexes = set()
            for account in accounts:
                index = int(account["stt"])
                active_indexes.add(index)
                account_id = str(account.get("account_id") or f"Tài khoản {index}")
                account_payload = {
                    "raw_line": str(account.get("raw_line") or ""),
                    "source_line": str(account.get("source_line") or ""),
                    "name": account_display_name(account, index),
                    "fields": list(account.get("fields") or []),
                    "unknown_fields": list(account.get("unknown_fields") or []),
                    "uid": str(account.get("uid") or ""),
                    "password": str(account.get("password") or account.get("pwd") or ""),
                    "pwd": str(account.get("pwd") or account.get("password") or ""),
                    "2fa": str(account.get("2fa") or ""),
                    "cookie": str(account.get("cookie") or ""),
                    "token": str(account.get("token") or ""),
                    "email": str(account.get("email") or ""),
                    "proxy": str(account.get("proxy") or ""),
                    "type": str(account.get("type") or ""),
                }
                existing = self._states.get(index)
                if existing is None or existing["account_id"] != account_id:
                    self._states[index] = {
                        "stt": index,
                        "account_id": account_id,
                        "country": str(account.get("country") or ""),
                        "locale": normalize_account_locale(account.get("locale")),
                        "timezone": normalize_account_timezone(account.get("timezone")),
                        "status": "UNKNOWN",
                        "checkpoint_stopped": False,
                        "current_action": "Chưa chạy",
                        "logs": [],
                        "history_logs": [],
                        "tasks": {},
                        "last_task_result": "PENDING",
                        "page_wait_remaining": None,
                        "next_page_at": "",
                        **account_payload,
                    }
                    saved = self.history.load(self._states[index]) if self.history else None
                    if saved:
                        self._states[index].update(
                            status=saved["last_status"], current_action=saved["last_action"],
                            tasks=saved["tasks"], last_task_result=saved["last_task_result"],
                            history_logs=saved["logs"],
                        )
                else:
                    existing["country"] = str(account.get("country") or "")
                    existing["locale"] = normalize_account_locale(account.get("locale"))
                    existing["timezone"] = normalize_account_timezone(account.get("timezone"))
                    existing.update(account_payload)
                self._persist(self._states[index], event_type="SEEN")
            for index in list(self._states):
                if index not in active_indexes:
                    del self._states[index]

    def indexes(self):
        with self._lock:
            return sorted(self._states)

    def get(self, index):
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return None
            snapshot = dict(state)
            snapshot["logs"] = list(state["logs"])
            snapshot["history_logs"] = list(state.get("history_logs", []))
            snapshot["tasks"] = copy.deepcopy(state.get("tasks", {}))
            snapshot["friend_attempts"] = set(state.get("friend_attempts", set()))
            snapshot["fields"] = list(state.get("fields") or [])
            snapshot["unknown_fields"] = [
                dict(field) for field in state.get("unknown_fields") or []
            ]
            return snapshot

    def update(self, index, status=None, current_action=None):
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return None
            if status == "CHECKING":
                state["page_wait_remaining"] = None
                state["next_page_at"] = ""
                if self.history:
                    saved = self.history.load(state)
                    state["history_logs"] = saved["logs"] if saved else []
                    state["logs"] = []
                state["checkpoint_stopped"] = False
                state["tasks"] = {}
                state["friend_attempts"] = set()
                state["last_task_result"] = "PENDING"
            if state.get("checkpoint_stopped") and status != "CHECKPOINT":
                return self.get(index)
            if status is not None:
                normalized_status = str(status).upper()
                if normalized_status not in ACCOUNT_STATUSES:
                    raise ValueError(f"Trạng thái tài khoản không hợp lệ: {status}")
                state["status"] = normalized_status
                if normalized_status == "CHECKPOINT":
                    state["checkpoint_stopped"] = True
            if current_action is not None:
                state["current_action"] = str(current_action)
            self._persist(state)
            return self.get(index)

    def set_proxy(self, index, proxy):
        with self._lock:
            state = self._states[int(index)]
            state["proxy"] = state["effective_proxy"] = str(proxy or "")
            self._persist(state, event_type="PROXY", message=safe_proxy_label(proxy))

    def mark_friend_attempt(self, index, target):
        with self._lock:
            self._states[int(index)].setdefault("friend_attempts", set()).add(target)

    def set_page_wait(self, index, remaining=None, next_page_at=""):
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return
            if remaining is not None and state["status"] in {"CHECKPOINT", "DIE", "ERROR"}:
                return
            state["page_wait_remaining"] = remaining
            state["next_page_at"] = next_page_at

    def finalize_active_tasks(self, index, status, reason):
        if status not in {"SKIPPED", "ERROR"}:
            raise ValueError("Kết quả dừng tác vụ phải là SKIPPED hoặc ERROR")
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return
            state["page_wait_remaining"] = None
            state["next_page_at"] = ""
            for module, task in state.get("tasks", {}).items():
                if task["status"] in {"PENDING", "RUNNING"}:
                    task.update(status=status, detail=reason)
                    state["last_task_result"] = task_result_status(state["tasks"])
                    self._persist(state, module, "TASK", reason)

    def record_task(self, index, module, status, detail="", outcome=None, preserve_outcomes=False):
        if status not in TASK_RESULTS:
            raise ValueError(f"Task result không hợp lệ: {status}")
        with self._lock:
            state = self._states.get(int(index))
            if state is None or state.get("checkpoint_stopped"):
                return
            task = state.setdefault("tasks", {}).setdefault(module, {"status": "PENDING", "detail": "", "outcomes": []})
            if status == "RUNNING":
                if not preserve_outcomes:
                    task.update(status=status, detail=detail, outcomes=[])
                elif task["status"] not in {"FAILED", "ERROR"}:
                    task.update(status=status, detail=detail)
            else:
                if outcome is not None:
                    task["outcomes"].append(copy.deepcopy(outcome))
                if (task["status"] not in {"FAILED", "ERROR"} or status == "ERROR") and not (status == "SKIPPED" and task["status"] == "SUCCESS"):
                    task.update(status=status, detail=detail)
            state["last_task_result"] = task_result_status(state["tasks"])
            if task["status"] in {"FAILED", "ERROR"}:
                state["current_action"] = f"{module} {task['status']}: {task['detail']}"
            self._persist(state, module, "TASK", detail)

    def task_summary(self, indexes=None):
        with self._lock:
            selected = set(indexes) if indexes is not None else set(self._states)
            counts = {status: 0 for status in TASK_RESULTS}
            for index, state in self._states.items():
                if index in selected:
                    for task in state.get("tasks", {}).values():
                        counts[task["status"]] += 1
            return counts

    def append_log(self, index, message, current_action=None):
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return None
            state["logs"].append(str(message))
            if len(state["logs"]) > 5000:
                del state["logs"][:-4500]
            if current_action and not state.get("checkpoint_stopped"):
                state["current_action"] = str(current_action)
            self._persist(state, event_type="LOG", message=message)
            return self.get(index)

    def set_failure(self, index, failure_kind, reason):
        state = self.get(index)
        if state and state.get("checkpoint_stopped"):
            return "CHECKPOINT"
        status = account_status_for_failure(failure_kind)
        self.update(index, status=status, current_action=str(reason))
        self.append_log(index, f"[-] {reason}")
        return status

    def summary(self, indexes=None):
        with self._lock:
            selected = set(indexes) if indexes is not None else set(self._states)
            counts = {status: 0 for status in ACCOUNT_STATUSES}
            for index, state in self._states.items():
                if index in selected:
                    counts[state["status"]] += 1
            return counts

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

FRIEND_STATE_SELECTORS = (
    '[role="button"][data-friendship-status], button[data-friendship-status], '
    '[role="button"][aria-label="Friends"], [role="button"][aria-label="Bạn bè"], '
    '[role="button"][aria-label="เพื่อน"], [role="button"][aria-label="Teman"], '
    '[role="button"][aria-label="友達"], [role="button"][aria-label="친구"]'
)

CREATE_PAGE_BUTTON_PATTERN = re.compile(
    r"^(Tạo Trang|Create Page|Créer une Page|Crear página|Criar Página|"
    r"Seite erstellen|Buat Halaman|สร้างเพจ|Gumawa ng Page|ページを作成|페이지 만들기)$",
    re.IGNORECASE,
)
ADD_PAGE_ADMIN_BUTTON_PATTERN = re.compile(
    r"^(Thêm mới|Add new|เพิ่มใหม่|Tambahkan baru|Magdagdag ng bago|新しく追加|새로 추가)$",
    re.IGNORECASE,
)
NEXT_BUTTON_PATTERN = re.compile(
    r"^(Tiếp|Next|ถัดไป|Berikutnya|Susunod|次へ|다음)$",
    re.IGNORECASE,
)
PAGE_SETUP_FINISH_PATTERN = re.compile(r"^(Done|Finish|Xong|Hoàn tất)$", re.IGNORECASE)
PAGE_SETUP_SKIP_PATTERN = re.compile(r"^(Skip|Bỏ qua)$", re.IGNORECASE)
PAGE_SETUP_FIELDS_SELECTOR = (
    'input[type="tel"]:visible, input[type="url"]:visible, '
    'input[autocomplete="tel"]:visible, input[autocomplete="url"]:visible, '
    'input[autocomplete="street-address"]:visible, '
    'input[aria-label*="phone" i]:visible, input[aria-label*="website" i]:visible, '
    'input[placeholder="Phone number" i]:visible, input[placeholder="Website" i]:visible, '
    'input[placeholder="Address" i]:visible, input[placeholder="City/town" i]:visible, '
    'input[placeholder="Số điện thoại" i]:visible, input[placeholder="Địa chỉ" i]:visible, '
    'div[role="dialog"]:has(input):visible'
)
PAGE_BLANK_MARGIN_POINT = r"""() => {
    const width = document.documentElement.clientWidth;
    const height = document.documentElement.clientHeight;
    if (width < 40 || height < 40) return null;
    if (Array.from(document.querySelectorAll('[role="dialog"]')).some(el => el.getClientRects().length > 0)) return null;
    const excluded = 'a,button,input,textarea,select,label,form,header,nav,aside,' +
        'img,video,canvas,[contenteditable="true"],[onclick],[aria-haspopup],' +
        '[tabindex]:not([tabindex="-1"]),[role="button"],[role="link"],' +
        '[role="textbox"],[role="combobox"],[role="checkbox"],[role="radio"],' +
        '[role="switch"],[role="slider"],[role="tab"],[role="menuitem"],' +
        '[role="banner"],[role="navigation"],[role="dialog"],[role="menu"],' +
        '[role="listbox"],[role="alert"],[role="status"]';
    const points = [[width - 20, height / 2], [width - 20, height * 0.75],
        [width * 0.75, height - 20], [width / 2, height - 20], [20, height * 0.75]];
    for (const [x, y] of points) {
        const target = document.elementFromPoint(x, y);
        if (!target || target.closest(excluded) || getComputedStyle(target).cursor === 'pointer') continue;
        if (Array.from(target.childNodes).some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim())) continue;
        return {x: Math.round(x), y: Math.round(y)};
    }
    return null;
}"""
GIVE_ACCESS_BUTTON_PATTERN = re.compile(
    r"^(Cấp quyền truy cập|Give access|ให้สิทธิ์การเข้าถึง|Berikan akses|"
    r"Magbigay ng access|アクセスを許可|액세스 권한 부여)$",
    re.IGNORECASE,
)

ACCOUNT_METADATA_PATTERN = re.compile(
    r"^(locale|language|country|timezone)\s*=\s*(.*?)\s*$",
    re.IGNORECASE,
)


def normalize_account_locale(value):
    locale = str(value or "AUTO").strip()
    if not locale or locale.casefold() == "auto":
        return "AUTO"
    if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z]{2}|-[A-Za-z]{4})?", locale):
        return "AUTO"
    pieces = locale.split("-")
    return pieces[0].lower() + (f"-{pieces[1].upper()}" if len(pieces) > 1 else "")


def normalize_account_timezone(value):
    timezone = str(value or "").strip()
    if not timezone:
        return ""
    return timezone if re.fullmatch(r"[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+", timezone) else ""


def split_account_metadata(raw_line):
    """Remove optional account metadata tokens without inferring them from the proxy."""
    metadata = {"locale": "AUTO", "country": "", "timezone": ""}
    account_parts = []
    for part in str(raw_line or "").split("|"):
        match = ACCOUNT_METADATA_PATTERN.fullmatch(part.strip())
        if not match:
            account_parts.append(part)
            continue
        key, value = match.group(1).casefold(), match.group(2).strip()
        if key in {"locale", "language"}:
            metadata["locale"] = normalize_account_locale(value)
        elif key == "country":
            metadata["country"] = value
        elif key == "timezone":
            metadata["timezone"] = normalize_account_timezone(value)
    return "|".join(account_parts), metadata


def browser_locale_options(locale):
    """Return browser locale settings; AUTO leaves Facebook/browser language untouched."""
    normalized = normalize_account_locale(locale)
    if normalized == "AUTO":
        return {"locale": None, "accept_language": None, "lang_arg": None}
    language = normalized.split("-", 1)[0]
    return {
        "locale": normalized,
        "accept_language": f"{normalized},{language};q=0.9,en-US;q=0.7,en;q=0.6",
        "lang_arg": normalized,
    }


def resolve_account_proxy(account_proxy, resolved_proxies, account_index):
    """Use the proxy captured for this account; never borrow another account's proxy."""
    inline_proxy = str(account_proxy or "").strip()
    if inline_proxy:
        return inline_proxy
    resolved = str((resolved_proxies or {}).get(int(account_index), "") or "").strip()
    return "" if resolved in {"", "Không dùng"} else resolved


def facebook_page_reference(url):
    """Extract a Page reference from Page and Page-settings URLs."""
    parsed = urlparse(str(url or "").strip())
    if (parsed.hostname or "").casefold() not in {
        "facebook.com", "www.facebook.com", "m.facebook.com"
    }:
        return ""
    query_id = re.search(r"(?:^|&)id=(\d+)(?:&|$)", parsed.query)
    if query_id:
        return query_id.group(1)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts or parts[0].casefold() in {"pages", "settings", "login"}:
        return ""
    return parts[0].casefold()


def page_reference_matches(expected_url, current_url):
    expected = facebook_page_reference(expected_url)
    current = facebook_page_reference(current_url)
    return bool(expected and current and expected == current)


async def locator_matches_account_target(locator, target):
    """Verify a search result against the user-provided UID/name, independent of UI language."""
    expected = str(target or "").strip().casefold()
    if not expected:
        return False
    evidence = []
    for attribute in ("href", "data-id", "data-testid", "aria-label"):
        try:
            evidence.append(await locator.get_attribute(attribute) or "")
        except Exception:
            pass
    try:
        target_link = locator.locator('a[href]').first
        if await target_link.count() > 0:
            evidence.append(await target_link.get_attribute("href") or "")
    except Exception:
        pass
    try:
        evidence.append(await locator.inner_text(timeout=1000) or "")
    except Exception:
        pass
    combined = " ".join(evidence).casefold()
    if expected.isdigit():
        return re.search(rf"(?<!\d){re.escape(expected)}(?!\d)", combined) is not None
    return expected in combined

def version_tuple(version):
    """Chuyển chuỗi version thành tuple số để so sánh đúng thứ tự."""
    parts = re.findall(r"\d+", str(version))
    return tuple(int(part) for part in parts) if parts else (0,)


def parse_page_plan(value: str):
    """Parse `page name|category`; old one-column page names remain valid."""
    parts = [part.strip() for part in str(value or "").split("|", 1)]
    return {
        "name": parts[0] if parts and parts[0] else generate_random_person_name(),
        "category": parts[1] if len(parts) > 1 and parts[1] else "Blog cá nhân",
    }


def build_create_page_plans(targets, max_pages):
    """Build the requested Page plans while preserving legacy auto-name behavior."""
    requested = max(1, int(max_pages))
    plans = [
        str(target).strip()
        for target in (targets or [])
        if str(target or "").strip()
    ][:requested]
    while len(plans) < requested:
        plans.append(f"{generate_random_person_name()}|Blog cá nhân")
    return plans


def validate_create_page_targets(targets, max_pages):
    """Validate explicit Page plans before any browser is launched."""
    requested = max(1, int(max_pages))
    clean_targets = [str(target or "") for target in (targets or []) if str(target or "").strip()]
    if not clean_targets:
        return False, "Chưa có cấu hình Page hợp lệ."
    for position, target in enumerate(clean_targets[:requested], 1):
        parts = target.split("|", 1)
        page_name = parts[0].strip() if parts else ""
        category = parse_page_plan(target)["category"]
        if not page_name:
            return False, f"Page #{position} thiếu page_name."
        if not category:
            return False, f"Page #{position} thiếu category."
    return True, ""


def filter_targets_for_mode(targets, mode, known_modes):
    """Return targets for one mode without discarding legacy unscoped entries."""
    available_modes = known_modes.keys() if hasattr(known_modes, "keys") else known_modes
    normalized_modes = {
        str(available_mode).strip().casefold()
        for available_mode in (available_modes or [])
    }
    requested_mode = str(mode or "").strip().casefold()
    scoped_targets = []
    unscoped_targets = []

    for target in targets or []:
        raw_target = str(target or "").strip()
        if not raw_target:
            continue
        prefix, separator, value = raw_target.partition(":")
        normalized_prefix = prefix.strip().casefold()
        if separator and normalized_prefix in normalized_modes:
            if normalized_prefix == requested_mode and value.strip():
                scoped_targets.append(value.strip())
            continue
        unscoped_targets.append(raw_target)

    return scoped_targets if scoped_targets else unscoped_targets


def build_create_page_result(
    status,
    account_id,
    page_name,
    category,
    page_url="",
    page_id="",
    reason="",
    technical_error="",
    retry_count=0,
    account_index=None,
    proxy="",
    flow_state="",
):
    return {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "account_index": account_index,
        "account": account_id,
        "account_id": account_id,
        "page_name": page_name,
        "category": category,
        "page_url": page_url,
        "page_id": page_id,
        "proxy": proxy,
        "status": str(status).upper(),
        "reason": reason,
        "technical_error": technical_error,
        "retry_count": int(retry_count),
        "flow_state": str(flow_state or status).upper(),
    }


def build_page_context(account_id, page_name, category, proxy="", locale="AUTO"):
    return {
        "owner_account_id": str(account_id or ""),
        "requested_page_name": str(page_name or ""),
        "requested_category": str(category or ""),
        "proxy": str(proxy or ""),
        "locale": normalize_account_locale(locale),
        "page_id": "",
        "page_url": "",
        "creation_status": "PENDING",
        "verification_status": "PENDING",
        "created_at": "",
    }


def transition_page_context(page_context, state, page_identity=None):
    normalized_state = str(state or "").upper()
    if normalized_state not in PAGE_FLOW_STATES:
        raise ValueError(f"Create Page state không hợp lệ: {state}")
    if normalized_state == "SUCCESS" and not is_verified_page_identity(page_identity or {}):
        raise ValueError("Không thể chuyển SUCCESS khi chưa có Page URL/ID hợp lệ.")
    page_context["creation_status"] = normalized_state
    if normalized_state == "VERIFYING":
        page_context["verification_status"] = "VERIFYING"
    elif normalized_state == "SUCCESS":
        identity = page_identity or {}
        page_context["page_url"] = str(identity.get("url") or "")
        page_context["page_id"] = str(identity.get("id") or "")
        page_context["verification_status"] = "VERIFIED"
        page_context["created_at"] = datetime.now().isoformat(timespec="seconds")
    elif normalized_state in {"FAILED", "ERROR", "CANCELLED"}:
        page_context["verification_status"] = "NOT_VERIFIED"
    return page_context


def classify_page_access_feedback(text):
    normalized = str(text or "").casefold()
    marker_groups = (
        ("ASSIGNED", ("has facebook access", "đã có quyền truy cập", "ได้รับสิทธิ์", "アクセス権", "액세스 권한")),
        ("INVITED", ("invitation sent", "đã gửi lời mời", "ส่งคำเชิญแล้ว", "undangan dikirim", "招待を送信", "초대를 보냈")),
        ("PENDING", ("pending", "đang chờ", "รอดำเนินการ", "menunggu", "保留中", "대기 중")),
    )
    for status, markers in marker_groups:
        if any(marker in normalized for marker in markers):
            return status
    return "FAILED"


def build_page_access_result(account_id, page_url, target_user, status, reason=""):
    normalized_status = str(status or "").upper()
    if normalized_status not in PAGE_ACCESS_STATUSES:
        raise ValueError(f"Trạng thái Page Access không hợp lệ: {status}")
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "account_id": str(account_id or ""),
        "page_id": facebook_page_reference(page_url),
        "page_url": str(page_url or ""),
        "business_id": "",
        "target_user": str(target_user or ""),
        "assignment_status": normalized_status,
        "reason": str(reason or ""),
    }


PAGE_ACCESS_RESULT_FIELDS = [
    "timestamp", "account_id", "business_id", "page_id", "page_url",
    "target_user", "assignment_status", "reason",
]


def save_page_access_result(result):
    append_csv_result("page_admin_jobs.csv", PAGE_ACCESS_RESULT_FIELDS, result)


def page_identity_keys(page_url="", page_id=""):
    keys = set()
    clean_id = str(page_id or "").strip()
    clean_url = str(page_url or "").strip().rstrip("/").casefold()
    if clean_id:
        keys.add(f"id:{clean_id}")
    if clean_url:
        keys.add(f"url:{clean_url}")
    return keys


def save_created_page_success(record):
    """Atomically de-duplicate and write both Create Page success outputs."""
    fieldnames = [
        "time", "timestamp", "account_index", "account", "account_id",
        "page_name", "category", "page_url", "page_id", "proxy", "status",
        "reason", "technical_error", "retry_count", "flow_state",
        "owner_account_id", "page_job_id",
    ]
    csv_path = output_path("created_pages.csv")
    success_path = output_path("created_pages_success.txt")
    candidate_keys = page_identity_keys(record.get("page_url"), record.get("page_id"))
    if not candidate_keys:
        return False

    with RESULT_FILE_LOCK:
        upgrade_page_result_header(csv_path, fieldnames)
        existing_keys = set()
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            with open(csv_path, "r", newline="", encoding="utf-8-sig") as handle:
                for existing in csv.DictReader(handle):
                    existing_keys.update(page_identity_keys(
                        existing.get("page_url"), existing.get("page_id")
                    ))
        if candidate_keys & existing_keys:
            return False

        has_content = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        with open(csv_path, "a", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            if not has_content:
                writer.writeheader()
            writer.writerow(record)
        with open(success_path, "a", encoding="utf-8") as handle:
            handle.write(
                f"{record['account_id']} | {record['page_name']} | "
                f"{record['page_url'] or record['page_id']} | {record['time']}\n"
            )
    return True


CREATE_PAGE_RESULT_FIELDS = [
    "time", "timestamp", "account_index", "account", "account_id",
    "page_name", "category", "page_url", "page_id", "proxy", "status",
    "reason", "technical_error", "retry_count", "flow_state",
    "owner_account_id", "page_job_id",
]


def upgrade_page_result_header(path, fieldnames):
    if not os.path.exists(path) or not os.path.getsize(path):
        return
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames == fieldnames:
            return
        rows = list(reader)
    temporary = path + ".schema.tmp"
    try:
        with open(temporary, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def save_create_page_outcome(record):
    with RESULT_FILE_LOCK:
        upgrade_page_result_header(output_path("create_page_results.csv"), CREATE_PAGE_RESULT_FIELDS)
        append_csv_result("create_page_results.csv", CREATE_PAGE_RESULT_FIELDS, record)


def append_create_page_account_log(account_index, account_id, message):
    safe_account = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(account_id or account_index))
    filename = f"create_page_{int(account_index)}_{safe_account[:48]}.log"
    with RESULT_FILE_LOCK:
        with open(output_path(filename), "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")


def is_transient_create_page_error(exc):
    text = f"{type(exc).__name__}: {exc}".casefold()
    return isinstance(exc, (TimeoutError, OSError, ConnectionError)) or any(
        marker in text for marker in (
            "timeout", "timed out", "connection", "network", "navigation",
            "net::err_", "temporarily unavailable",
        )
    )


async def retry_create_page_operation(operation, max_attempts=3, base_delay=1.0):
    """Retry transient pre-submit operations with bounded exponential backoff."""
    last_error = None
    for attempt in range(1, max(1, int(max_attempts)) + 1):
        try:
            return await operation(), attempt - 1
        except Exception as exc:
            last_error = exc
            try:
                setattr(exc, "create_page_retry_count", attempt - 1)
            except Exception:
                pass
            if attempt >= max_attempts or not is_transient_create_page_error(exc):
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
    raise last_error


async def close_browser_resources(context=None, browser=None, page=None, close_timeout=5):
    """Close isolated resources on success, failure, or cancellation."""
    errors = []
    for resource in (page, context, browser):
        if resource is None:
            continue
        try:
            await asyncio.wait_for(resource.close(), timeout=close_timeout)
        except Exception as exc:
            errors.append(exc)
    return errors


async def wait_for_locator_ready(locator, timeout=15000):
    """Chờ phần tử hiển thị và sẵn sàng tương tác, kết hợp kiểm tra is_enabled() chuẩn xác."""
    await locator.wait_for(state="visible", timeout=timeout)
    deadline = time.monotonic() + (timeout / 1000.0)
    while time.monotonic() < deadline:
        try:
            aria_disabled = (await locator.get_attribute("aria-disabled") or "").casefold()
            disabled = await locator.get_attribute("disabled")
            enabled = await locator.is_enabled()
            if aria_disabled != "true" and disabled is None and enabled:
                return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False


def select_page_admin_job(targets, account_index: int, account_name: str):
    """Select an account-specific Page/admin mapping while preserving legacy input."""
    legacy_job = None
    has_scoped_jobs = False
    account_keys = {str(account_index), str(account_name or "").strip().casefold()}
    for raw_target in targets or []:
        parts = [part.strip() for part in str(raw_target).split("|")]
        if len(parts) >= 3:
            has_scoped_jobs = True
            owner = parts[0].casefold()
            if owner in account_keys or owner in {"*", "all", "tất cả", "tat ca"}:
                return {"page": parts[1], "admin": parts[2]}
        elif len(parts) == 2 and all(parts):
            legacy_job = {"page": parts[0], "admin": parts[1]}

    # Backward compatibility: two separate lines used to mean URL then admin.
    if legacy_job:
        return legacy_job
    if has_scoped_jobs:
        return None
    clean_targets = [str(item).strip() for item in (targets or []) if str(item).strip()]
    if len(clean_targets) >= 2:
        return {"page": clean_targets[0], "admin": clean_targets[1]}
    return None


def extract_facebook_page_identity(urls):
    """Return a stable Page URL/ID from current or canonical Facebook URLs."""
    for raw_url in urls or []:
        url = str(raw_url or "").strip()
        if not url:
            continue
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")
        if host not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
            continue
        if path in {"", "/", "/pages", "/pages/creation"} or path.startswith("/pages/creation/"):
            continue
        first_segment = path.strip("/").split("/", 1)[0].casefold()
        if first_segment in {
            "bookmarks", "events", "friends", "gaming", "groups", "home.php",
            "login", "manage", "marketplace", "messages", "notifications",
            "pages", "search", "settings", "watch",
        }:
            continue
        query_id = re.search(r"(?:^|&)id=(\d+)(?:&|$)", parsed.query)
        path_id = re.search(r"/(?:profile\.php/)?(\d{5,})(?:/|$)", path)
        page_id = (query_id or path_id).group(1) if (query_id or path_id) else ""
        clean_url = f"https://www.facebook.com{path}"
        if query_id and path.endswith("profile.php"):
            clean_url += f"?id={page_id}"
        return {"url": clean_url, "id": page_id}
    return {"url": "", "id": ""}


def is_verified_page_identity(identity):
    """Return True only when Facebook supplied a stable Page URL or Page ID."""
    return bool(
        identity
        and (
            str(identity.get("url", "")).strip()
            or str(identity.get("id", "")).strip()
        )
    )


def append_csv_result(filename: str, fieldnames, row):
    """Append one durable result row without interleaving concurrent workers."""
    path = output_path(filename)
    with RESULT_FILE_LOCK:
        has_content = os.path.exists(path) and os.path.getsize(path) > 0
        with open(path, "a", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            if not has_content:
                writer.writeheader()
            writer.writerow(row)

def is_trusted_update_url(download_url: str) -> bool:
    parsed = urlparse(download_url)
    trusted_hosts = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
    return (
        parsed.scheme == "https"
        and parsed.hostname in trusted_hosts
        and parsed.path.lower().endswith(".exe")
    )


def get_self_update_target(executable=None, frozen=None):
    target = os.path.abspath(executable or sys.executable)
    is_frozen = getattr(sys, "frozen", False) if frozen is None else bool(frozen)
    if not is_frozen:
        return None
    if os.path.basename(target).casefold() in {"python.exe", "pythonw.exe", "py.exe"}:
        return None
    return target


def get_update_restart_environment(environment=None):
    source = os.environ if environment is None else environment
    clean = {
        key: value for key, value in source.items()
        if not key.upper().startswith("_PYI_") and key.upper() != "_MEIPASS2"
    }
    clean["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return clean


def build_windows_update_restart_script(process_id, temp_file, current_exe, error_log, parent_process_id=0):
    """Build the updater script that replaces and starts a fresh PyInstaller app."""
    def batch_path(value):
        return os.path.abspath(str(value)).replace("%", "%%")

    temp_path = batch_path(temp_file)
    executable_path = batch_path(current_exe)
    error_log_path = batch_path(error_log)
    def encoded_command(script):
        return base64.b64encode(script.encode("utf-16le")).decode("ascii")

    ps_executable = os.path.abspath(current_exe).replace("'", "''")
    wait_command = encoded_command(f"""
$ErrorActionPreference = 'Stop'
try {{
    $oldProcesses = @(Get-Process -Id {int(process_id)} -ErrorAction SilentlyContinue)
    $parent = Get-Process -Id {int(parent_process_id)} -ErrorAction SilentlyContinue
    if ($parent -and $parent.Path -eq '{ps_executable}') {{ $oldProcesses += $parent }}
    foreach ($oldProcess in $oldProcesses) {{
        if (-not $oldProcess.WaitForExit(60000)) {{ throw 'Old instance is still running.' }}
    }}
    exit 0
}} catch {{ exit 1 }}
""")
    restart_command = encoded_command(f"""
$ErrorActionPreference = 'Stop'
try {{
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = '{ps_executable}'
    $info.WorkingDirectory = [IO.Path]::GetDirectoryName($info.FileName)
    $info.UseShellExecute = $false
    foreach ($key in @($info.EnvironmentVariables.Keys)) {{
        if ($key.StartsWith('_PYI_', [StringComparison]::OrdinalIgnoreCase) -or $key -eq '_MEIPASS2') {{
            $info.EnvironmentVariables.Remove($key)
        }}
    }}
    $info.EnvironmentVariables['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    $newProcess = [Diagnostics.Process]::Start($info)
    if ($null -eq $newProcess) {{ throw 'Restart did not create a process.' }}
    if ($newProcess.WaitForExit(10000) -and $newProcess.ExitCode -ne 0) {{
        throw 'Restarted application exited with an error.'
    }}
    exit 0
}} catch {{ exit 1 }}
""")
    return f"""@echo off
setlocal
del /q "{error_log_path}" >nul 2>&1
powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {wait_command}
if errorlevel 1 goto replace_failed
copy /y "{temp_path}" "{executable_path}" >nul
if errorlevel 1 goto replace_failed
del /q "{temp_path}" >nul 2>&1

rem Start a new top-level PyInstaller instance instead of inheriting the old archive context.
set "PYINSTALLER_RESET_ENVIRONMENT=1"
for /f "tokens=1 delims==" %%V in ('set _PYI_ 2^>nul') do set "%%V="
set "_MEIPASS2="
powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {restart_command}
if errorlevel 1 goto restart_failed
goto cleanup

:replace_failed
>"{error_log_path}" echo Khong the thay the file EXE. Vui long thu cap nhat lai.
set "UPDATE_FAILURE_MESSAGE=Khong the thay the file cap nhat. Vui long thu lai."
goto notify_failure

:restart_failed
>"{error_log_path}" echo EXE moi da duoc thay thanh cong nhung khong the tu khoi dong.
set "UPDATE_FAILURE_MESSAGE=EXE moi da duoc cai dat nhung khong the tu khoi dong. Vui long mo lai ung dung thu cong."

:notify_failure
start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('%UPDATE_FAILURE_MESSAGE%', 'Cap nhat phan mem')"

:cleanup
del /q "{temp_path}" >nul 2>&1
endlocal
del /q "%~f0" >nul 2>&1
"""


def check_for_updates(self, manual=False):
    """Kiểm tra bản mới và hiển thị cửa sổ cập nhật tùy chỉnh có thanh tiến trình"""
    try:
        req = urllib.request.Request(VERSION_CHECK_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                latest_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url", "")
                expected_sha256 = str(data.get("sha256", "")).strip().lower()
                changelog = data.get("changelog", "Nâng cấp tính năng và cải thiện hiệu suất hệ thống.")
                is_mandatory = data.get("mandatory", True)  # True nếu bắt buộc cập nhật

                if version_tuple(latest_version) > version_tuple(CURRENT_VERSION):
                    if not is_trusted_update_url(download_url):
                        self.log("[-] Bỏ qua bản cập nhật vì đường dẫn tải xuống không thuộc nguồn tin cậy.")
                        return
                    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
                        self.log("[-] Bỏ qua bản cập nhật vì thiếu hoặc sai mã SHA-256.")
                        return

                    self_update_target = get_self_update_target()
                    effective_mandatory = bool(is_mandatory and self_update_target)

                    def show_update_dialog():
                        # Tạo cửa sổ Toplevel đồng bộ màu với app
                        dlg = tk.Toplevel(self.root)
                        dlg.title("Thông báo cập nhật phần mềm")
                        dlg.geometry("520x460")
                        dlg.minsize(460, 380)
                        dlg.resizable(True, True)
                        dlg.configure(bg="#131C2E")
                        dlg.transient(self.root)
                        dlg.grab_set()

                        if effective_mandatory:
                            dlg.protocol("WM_DELETE_WINDOW", lambda: None)

                        # Tiêu đề
                        tk.Label(dlg, text="🚀 THÔNG BÁO CẬP NHẬT PHẦN MỀM", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E").pack(pady=(15, 5))

                        info_text = f"Đã có phiên bản mới: v{latest_version} (Bản hiện tại: v{CURRENT_VERSION})\nBản cập nhật này giúp nâng cao hiệu suất và tính bảo mật."
                        tk.Label(dlg, text=info_text, font=("Segoe UI", 9), fg="#E2E8F0", bg="#131C2E", justify="center").pack(pady=5)

                        # Footer được giữ cố định ở đáy để changelog không thể che các nút.
                        f_footer = tk.Frame(dlg, bg="#131C2E")
                        f_footer.pack(side="bottom", fill="x", padx=20, pady=(5, 15))

                        # Thanh Progressbar tải xuống (Ẩn lúc đầu)
                        progress_var = tk.DoubleVar(value=0)
                        p_bar = ttk.Progressbar(f_footer, orient="horizontal", mode="determinate", variable=progress_var)
                        
                        lbl_progress = tk.Label(f_footer, text="", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E")

                        # Nút bấm hành động
                        f_btn = tk.Frame(f_footer, bg="#131C2E")
                        f_btn.pack(side="bottom", fill="x")
                        action_columns = 1 + int(not effective_mandatory) + int(bool(self_update_target))
                        for column in range(action_columns):
                            f_btn.columnconfigure(column, weight=1, uniform="update_actions")

                        # Khung changelog chỉ sử dụng phần không gian còn lại phía trên footer.
                        f_log = tk.Frame(dlg, bg="#070B14", highlightbackground="#1E293B", highlightthickness=1)
                        f_log.pack(side="top", fill="both", expand=True, padx=20, pady=10)

                        txt_changelog = scrolledtext.ScrolledText(
                            f_log,
                            height=10,
                            bg="#070B14",
                            fg="#00FF66",
                            font=("Consolas", 8),
                            relief="flat",
                            wrap="word",
                        )
                        txt_changelog.pack(fill="both", expand=True, padx=5, pady=5)
                        txt_changelog.insert("1.0", f"Nội dung thay đổi:\n{changelog}")
                        txt_changelog.config(state="disabled")

                        btn_cancel = None
                        btn_update = None

                        def start_download():
                            if get_self_update_target() is None:
                                messagebox.showinfo(
                                    "Cập nhật thủ công",
                                    "Chế độ chạy source không hỗ trợ tự cập nhật. Vui lòng dùng TẢI THỦ CÔNG.",
                                    parent=dlg,
                                )
                                return
                            btn_update.config(state="disabled")
                            btn_download.config(state="disabled")
                            if btn_cancel is not None:
                                btn_cancel.config(state="disabled")
                            
                            p_bar.pack(side="top", fill="x", pady=(0, 5))
                            lbl_progress.pack(side="top", pady=(0, 5))
                            lbl_progress.config(text="Đang kết nối tải xuống tệp cập nhật...")

                            def download_worker():
                                try:
                                    temp_file = output_path("update_temp.exe")
                                    req_dl = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                                    with urllib.request.urlopen(req_dl, timeout=60) as dl_resp:
                                        total_size = int(dl_resp.headers.get('Content-Length', 0))
                                        downloaded = 0
                                        chunk_size = 8192

                                        with open(temp_file, "wb") as f_out:
                                            while True:
                                                chunk = dl_resp.read(chunk_size)
                                                if not chunk:
                                                    break
                                                f_out.write(chunk)
                                                downloaded += len(chunk)
                                                if total_size > 0:
                                                    percent = (downloaded / total_size) * 100
                                                    self.post_ui(lambda p=percent, d=downloaded, t=total_size: [
                                                        progress_var.set(p),
                                                        lbl_progress.config(
                                                            text=f"Đang tải: {d//1024} KB / {t//1024} KB ({p:.1f}%)"
                                                        ),
                                                    ])

                                    # Kiểm tra SHA256 và định dạng
                                    with open(temp_file, "rb") as f_chk:
                                        update_bytes = f_chk.read()
                                        if update_bytes[:2] != b"MZ" or hashlib.sha256(update_bytes).hexdigest() != expected_sha256:
                                            os.remove(temp_file)
                                            raise ValueError("Mã xác thực SHA-256 hoặc định dạng tệp không hợp lệ!")

                                    # Kiểm tra lại target ngay trước khi tạo updater/thay EXE.
                                    current_exe = get_self_update_target()
                                    if current_exe is None:
                                        os.remove(temp_file)
                                        raise RuntimeError("Target tự cập nhật không an toàn hoặc ứng dụng đang chạy source.")
                                    updater_file = output_path("updater.bat")
                                    restart_error_log = output_path("update_restart_error.log")
                                    bat_script = build_windows_update_restart_script(
                                        os.getpid(), temp_file, current_exe, restart_error_log,
                                        parent_process_id=os.getppid(),
                                    )
                                    with open(updater_file, "w", encoding="utf-8") as f_bat:
                                        f_bat.write(bat_script)

                                    self.post_ui(lambda: lbl_progress.config(text="Tải xong! Đang khởi động lại ứng dụng..."))
                                    time.sleep(1.5)

                                    subprocess.Popen(
                                        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", updater_file],
                                        cwd=APP_DATA_DIR, env=get_update_restart_environment(),
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                    )
                                    self.post_ui(self.root.destroy)

                                except Exception as err:
                                    self.post_ui(lambda e=err: [
                                        messagebox.showerror("Lỗi cập nhật", f"Không thể hoàn tất cập nhật:\n{e}", parent=dlg),
                                        dlg.destroy()
                                    ])

                            threading.Thread(target=download_worker, daemon=True).start()

                        next_column = 0
                        if not effective_mandatory:
                            btn_cancel = tk.Button(f_btn, text="ĐỂ SAU", font=("Segoe UI", 9), bg="#1E293B", fg="#E2E8F0", relief="flat", padx=15, pady=8, cursor="hand2", command=dlg.destroy)
                            btn_cancel.grid(row=0, column=next_column, sticky="ew", padx=(0, 5))
                            next_column += 1
                        btn_download = tk.Button(f_btn, text="TẢI THỦ CÔNG", font=("Segoe UI", 9), bg="#2563EB", fg="#FFFFFF", relief="flat", padx=15, pady=8, cursor="hand2", command=lambda: webbrowser.open(download_url))
                        btn_download.grid(row=0, column=next_column, sticky="ew", padx=5)
                        next_column += 1
                        if self_update_target:
                            btn_update = tk.Button(f_btn, text="CẬP NHẬT NGAY", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", padx=15, pady=8, cursor="hand2", command=start_download)
                            btn_update.grid(row=0, column=next_column, sticky="ew", padx=(5, 0))

                    self.post_ui(show_update_dialog)
                elif manual and version_tuple(latest_version) == version_tuple(CURRENT_VERSION):
                    self.post_ui(lambda: messagebox.showinfo(
                        "Kiểm tra cập nhật",
                        f"Bạn đang sử dụng phiên bản mới nhất\n\nPhiên bản hiện tại: v{CURRENT_VERSION}",
                        parent=self.root,
                    ))
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
    """Xác thực license online bằng Cloudflare Worker API."""
    try:
        clean_key = key_str.strip().upper()
        if not re.fullmatch(r"[A-Z2-7]{4}(?:-[A-Z2-7]{4}){3}", clean_key):
            return False, "Định dạng Key không hợp lệ!"

        if "YOUR-WORKER" in LICENSE_API_URL:
            return False, "Chưa cấu hình License API trên client."

        payload = json.dumps({"key": clean_key, "hwid": get_hwid()}).encode("utf-8")
        request = urllib.request.Request(
            f"{LICENSE_API_URL.rstrip('/')}/validate",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "FacebookAutoTool"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("valid"):
            return True, str(result.get("expires", ""))
        return False, str(result.get("message", "Key không hợp lệ hoặc đã hết hạn."))
    except (urllib.error.URLError, TimeoutError):
        return False, "Không thể kết nối máy chủ bản quyền."
    except (ValueError, json.JSONDecodeError, OSError):
        return False, "Phản hồi từ máy chủ bản quyền không hợp lệ."

def load_saved_license():
    """Đọc license an toàn; file hỏng hoặc không đọc được sẽ coi như chưa kích hoạt."""
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as license_file:
            return license_file.read().strip()
    except (OSError, UnicodeError):
        return ""

def settings_cipher():
    key_material = hashlib.sha256(
        SECRET_SALT + get_hwid().encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))

def protect_setting(value):
    if not value:
        return value
    return settings_cipher().encrypt(str(value).encode("utf-8")).decode("ascii")

def unprotect_setting(value):
    if not value:
        return value
    try:
        return settings_cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError, UnicodeError):
        # Backward compatibility for settings saved before encryption.
        return value

# [ĐOẠN TRƯỚC GIỮ NGUYÊN:]
# [THAY THẾ TOÀN BỘ HÀM parse_cookies]:
def normalize_cookie_input(value: str):
    """Normalize login cookies without changing the stored account input."""
    value = str(value or "").strip()
    value = re.sub(r'^Cookie\s*:\s*', '', value, flags=re.IGNORECASE)
    if value.startswith(('[', '{')):
        try:
            payload = json.loads(value)
        except (ValueError, TypeError):
            return ""
        if isinstance(payload, dict):
            payload = payload.get("cookies", payload)
        if isinstance(payload, dict):
            if "name" in payload and "value" in payload:
                payload = [payload]
            else:
                payload = [{"name": key, "value": val} for key, val in payload.items()]
        if not isinstance(payload, list):
            return ""
        pairs = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            val = item.get("value")
            if isinstance(name, str) and isinstance(val, (str, int)):
                pairs.append(f"{name.strip()}={val}")
        value = "; ".join(pairs)
    if not re.search(r'(?:^|;)\s*\b(?:c_user|xs|sessionid|sb|datr)\b\s*=', value):
        return ""
    return value


def parse_cookies(cookie_raw: str, default_domain: str = ".facebook.com"):
    clean_cookie = re.sub(r'^\d+[\.\-\s\|]+', '', cookie_raw.strip()).strip()
    if "|" in clean_cookie:
        clean_cookie = "; ".join(
            normalized.rstrip("; ") for field in clean_cookie.split("|")
            if (normalized := normalize_cookie_input(field))
        )
    else:
        clean_cookie = normalize_cookie_input(clean_cookie) or clean_cookie
    
    domain_val = default_domain

    cookies_list = []
    pairs = clean_cookie.split(';')
    for pair in pairs:
        if '=' in pair:
            name, value = pair.strip().split('=', 1)
            name_clean = name.strip()
            val_clean = value.strip()
            if name_clean:
                cookies_list.append({
                    "name": name_clean,
                    "value": val_clean,
                    "domain": domain_val,
                    "path": "/",
                    "sameSite": "Lax"
                })
    return cookies_list

def parse_proxy(proxy_raw: str):
    if not proxy_raw or not proxy_raw.strip():
        return None
    raw = proxy_raw.strip()
    scheme = "http"
    username = password = None
    if "://" in raw or ("@" in raw and not re.match(r'^[^:@]+:\d+:', raw)):
        try:
            parsed = urlparse(raw if "://" in raw else "http://" + raw)
            if parsed.scheme not in {"http", "https", "socks4", "socks5"} or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                return None
            scheme, host, port = parsed.scheme, parsed.hostname, parsed.port
            if parsed.username is not None:
                username, password = unquote(parsed.username), unquote(parsed.password or "")
        except ValueError:
            return None
    else:
        match = re.fullmatch(r'(\[[^\]]+\]|[^:\s]+):(\d+)(?::([^:]*):(.*))?', raw)
        if not match:
            return None
        host, port, username, password = match.groups()
        host = host.strip("[]")
        port = int(port)
        if username is not None:
            username, password = unquote(username), unquote(password or "")
    if not host or port is None or not 0 < port <= 65535:
        return None
    if username is not None and (not username or not password):
        return None
    if ":" in host:
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            return None
        host = f"[{host}]"
    elif not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host):
        return None
    proxy = {"server": f"{scheme}://{host}:{port}"}
    if username is not None:
        proxy.update(username=username, password=password)
    return proxy

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

def fetch_proxy_from_api(api_input: str) -> str:
    """Tự động nhận diện Key hoặc Link API SuiProxy/TMProxy để lấy IP:Port mới nhất"""
    raw_val = api_input.strip()
    if not raw_val:
        return ""

    # 1. Nếu khách chỉ dán Key SuiProxy (không có http) -> Tự ghép link chuẩn
    if not raw_val.startswith("http"):
        request_url = f"https://api.suiproxy.com/api/proxy/get-new-proxy?api_key={raw_val}"
        api_key_header = raw_val
    else:
        request_url = raw_val
        # Trích xuất key từ link nếu có tham số api_key
        m_key = re.search(r'api_key=([^&]+)', raw_val)
        api_key_header = m_key.group(1) if m_key else ""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    if api_key_header:
        headers['X-API-KEY'] = api_key_header

    try:
        req = urllib.request.Request(request_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode('utf-8', errors='ignore').strip()
            
            # Xử lý phản hồi JSON chuẩn SuiProxy
            if "{" in data and "}" in data:
                res_json = json.loads(data)

                # Trường hợp SuiProxy: trả về trực tiếp proxyHttp / proxy
                for k in ["proxyHttp", "proxy", "http", "https", "ip_port"]:
                    if k in res_json and isinstance(res_json[k], str) and ":" in res_json[k]:
                        return res_json[k].strip()

                # Trường hợp bọc trong object "data"
                if "data" in res_json:
                    d = res_json["data"]
                    if isinstance(d, dict):
                        for k in ["proxyHttp", "proxy", "http", "https", "ip_port"]:
                            if k in d and isinstance(d[k], str) and ":" in d[k]:
                                return d[k].strip()
                        if "ip" in d and "port" in d:
                            return f"{d['ip']}:{d['port']}"
                    elif isinstance(d, str) and ":" in d:
                        return d.strip()

            # Trường hợp trả về text thuần IP:Port
            ip_port_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5})', data)
            if ip_port_match:
                return ip_port_match.group(1)
    except Exception:
        pass
    return ""
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

def generate_totp_code(secret_key: str) -> str:
    """Tạo mã TOTP hiện tại từ secret Base32."""
    

    clean_secret = re.sub(r"\s+", "", secret_key).upper()
    padding = "=" * ((8 - len(clean_secret) % 8) % 8)
    key_bytes = base64.b32decode(clean_secret + padding, casefold=True)
    time_bytes = struct.pack(">Q", int(time.time() // 30))
    digest = hmac.new(key_bytes, time_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    ) % 1000000
    return f"{code:06d}"

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

def parse_any_account_line(raw_line: str, idx: int = 1):
    """Parse account lines flexibly, auto-detecting UID, Password, Cookie, Token, and trimming extra trailing metadata."""
    raw_value = str(raw_line or "").rstrip("\r\n")
    normalized_line = re.sub(r"^\s*\d+[\.\-\s]+", "", raw_value).strip()
    if not normalized_line or normalized_line.startswith("#"):
        return None

    fields = [field.strip() for field in normalized_line.split("|")]
    if not fields:
        return None

    uid = ""
    password = ""
    two_factor = ""
    cookie = ""
    token = ""
    email = ""
    proxy = ""
    prefix = fields[0].upper()
    start_index = 0
    if prefix in {"FACEBOOK", "COOKIE", "TOKEN"}:
        start_index = 1
        if prefix == "FACEBOOK":
            uid = fields[1] if len(fields) > 1 else ""
            password = fields[2] if len(fields) > 2 else ""
        elif prefix == "TOKEN":
            token = fields[1] if len(fields) > 1 else ""

    # Tự động quét và phân loại từng trường dữ liệu dựa vào đặc thù nhận diện
    for index, field in enumerate(fields):
        if index < start_index or not field:
            continue
        norm_cookie = normalize_cookie_input(field)
        if norm_cookie and not cookie:
            cookie = field
            continue
        if not token and (field.startswith(("EAAB", "EAAA")) or len(field) > 50 and "." in field and not "@" in field):
            token = field
            continue
        if not email and "@" in field and "." in field:
            email = field
            continue
        if not proxy and parse_proxy(field):
            proxy = field
            continue
        if not two_factor and (len(field) in (16, 32) and field.isalnum() and not field.isdigit()):
            two_factor = field
            continue
        if not uid and (field.isdigit() and len(field) >= 5):
            uid = field
            continue
        if uid and not password and field != cookie and field != token:
            password = field

    # Fallback trích xuất UID từ chuỗi Cookie nếu chưa tìm thấy UID ở các cột đầu
    cookie_val = normalize_cookie_input(cookie)
    if cookie_val:
        cookie_uid_match = re.search(r'(?:^|;)\s*c_user\s*=\s*(\d+)', cookie_val)
        if cookie_uid_match and not uid:
            uid = cookie_uid_match.group(1)

    # Nếu vẫn không có UID, gán nhãn mặc định theo STT
    if not uid:
        uid = f"UID_{idx}"

    if not cookie:
        return None

    account_type = "COOKIE"
    return {
        "type": account_type,
        "raw_line": raw_value,
        "source_line": normalized_line,
        "fields": fields,
        "unknown_fields": [],
        "uid": uid,
        "name": uid,
        "pwd": password,
        "password": password,
        "2fa": two_factor,
        "cookie": cookie,
        "token": token,
        "email": email or (uid if "@" in uid else ""),
        "proxy": proxy,
        "data": cookie or token or normalized_line,
        "locale": "AUTO",
        "country": "",
        "timezone": "",
    }



def serialize_account_line(account):
    """Return the exact user-provided account line for lossless UI refresh/export."""
    return str((account or {}).get("raw_line", ""))


def serialize_account_lines(accounts):
    return "\n".join(serialize_account_line(account) for account in accounts)

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
        "bg": "#10151B",
        "card": "#1A222B",
        "primary": "#43BEB2",
        "text": "#E7EDF2",
        "muted": "#A9B6C2",
        "border": "#32404C",
        "entry_bg": "#0D1319",
        "entry_fg": "#F5F8FA",
        "log_bg": "#0B1015",
        "log_fg": "#79D5CB"
    },
    "Cyberpunk Neon": {
        "bg": "#0D1117",
        "card": "#161B22",
        "primary": "#00F0FF",
        "text": "#F0F6FC",
        "muted": "#9BA9B7",
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
        "muted": "#9CAECC",
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
        "muted": "#52606D",
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
            "COOKIE|Cookie Facebook",
            "TOKEN|Token Facebook",
            "FACEBOOK|Email/UID|Password",
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
        parsed_accounts = []

        for idx, line in enumerate(lines, 1):
            parsed = parse_any_account_line(line, idx)
            if parsed:
                parsed_accounts.append({
                    "name": parsed["name"],
                    "uid": parsed["uid"],
                    "pwd": parsed["pwd"],
                    "2fa": parsed["2fa"],
                    "cookie": parsed["cookie"],
                    "proxy": parsed["proxy"] or "Không dùng",
                    "raw": line,
                })

        self.on_import_callback(parsed_accounts)
        messagebox.showinfo("Thành công", f"Đã nạp thành công {len(parsed_accounts)} tài khoản vào bảng!", parent=self)
        self.destroy()
# [ĐOẠN TRƯỚC:]
class MainToolApp:
    def auto_format_cookie_numbers(self, event=None):
        """Refresh the numbered table without rewriting the raw account input."""
        raw_text = self.txt_accounts.get("1.0", "end")
        if not raw_text.strip():
            return
        account_count = sum(
            1 for line in raw_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {account_count} nick")
        self.reload_table_from_text()

    def __init__(self, root, expire_date):
        self.root = root
        self.expire_date = expire_date
        self.root.title(f"Facebook Workspace Pro v{CURRENT_VERSION} - ĐẶNG PHÁT - Hạn dùng: {expire_date}")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1380, max(1000, round(screen_width * 0.90)))
        window_height = min(880, max(620, round(screen_height * 0.88)))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(1000, 620)
        try:
            self.root.iconbitmap(resource_path("picture.ico"))
        except (tk.TclError, OSError):
            pass
        self.is_running = False
        self.stop_requested = False
        self.run_error = None
        self.run_thread = None
        self.worker_loop = None
        self.worker_tasks = []
        self.proxy_api_lock = None
        self.run_config = {}
        self.ui_queue = queue.Queue()
        self.close_requested = False
        self.account_states = AccountStateStore(AccountHistoryStore(output_path("account_history.db")))
        self.account_log_context = contextvars.ContextVar("account_log_context", default=None)
        self.global_logs = []
        self.global_log_lock = threading.RLock()
        self.selected_log_account = None
        self.current_batch = 1
        self.create_page_result_lock = threading.RLock()
        self.create_page_account_results = {"completed": {}, "die": {}, "checkpoint": {}}
        self.create_page_results_window = None
        self.create_page_result_trees = {}

        self.theme_name = "Dark Charcoal (Mặc định)"
        self.current_theme = self.theme_name
        self.T = THEMES[self.theme_name]
        self.style = ttk.Style()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self._drain_ui_queue)

        self._build_layout()
        self.apply_theme(self.theme_name)
        self.load_settings()
        self._start_clock()

        threading.Thread(
            target=lambda: check_for_updates(self),
            daemon=True
            ).start()

    def post_ui(self, callback):
        """Schedule a UI callback without calling Tkinter from a worker thread."""
        if not self.close_requested:
            self.ui_queue.put(callback)

    def _drain_ui_queue(self):
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                try:
                    callback()
                except Exception as exc:
                    # A failed row refresh must not discard the later finish_run callback.
                    with self.global_log_lock:
                        self.global_logs.append(f"[UI ERROR] {type(exc).__name__}: {exc}")
        except queue.Empty:
            pass
        finally:
            if not self.close_requested:
                self.root.after(50, self._drain_ui_queue)

    @staticmethod
    def _bounded_int(value, default, minimum=0, maximum=100000):
        try:
            parsed = int(str(value).strip())
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, parsed))

    def capture_run_config(self):
        """Read every Tk value once on the UI thread before automation starts."""
        checked_indexes = set()
        resolved_proxies = {}
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and str(values[1]).isdigit():
                account_index = int(values[1])
                state = self.account_states.get(account_index)
                resolved_proxies[account_index] = (
                    state.get("proxy", "") if state else ""
                )
                if values[0] == "[✔]":
                    checked_indexes.add(account_index)

        min_delay = self._bounded_int(self.ent_min_delay.get(), 25, 0, 86400)
        max_delay = self._bounded_int(self.ent_max_delay.get(), 35, 0, 86400)
        min_page_delay = self._bounded_int(self.ent_min_page_delay.get(), 60, 0, 86400)
        max_page_delay = self._bounded_int(self.ent_max_page_delay.get(), 120, 0, 86400)
        parsed_accounts = {
            index: self.account_states.get(index)
            for index in self.account_states.indexes()
        }

        return {
            "accounts": self.txt_accounts.get("1.0", "end").strip(),
            "proxies": self.txt_proxies.get("1.0", "end").strip(),
            "targets": self.txt_targets.get("1.0", "end").strip(),
            "selected_indexes": self.ent_selected_indexes.get().strip(),
            "checked_indexes": checked_indexes,
            "resolved_proxies": resolved_proxies,
            "parsed_accounts": parsed_accounts,
            "threads": self._bounded_int(self.ent_threads.get(), 6, 1, 20),
            "batch_size": self._bounded_int(self.ent_batch_size.get(), 5, 1, 10000),
            "proxy_ratio": self._bounded_int(self.ent_proxy_ratio.get(), 20, 1, 10000),
            "proxy_mode": self.proxy_mode.get(),
            "proxy_api": self.ent_proxy_api.get().strip(),
            "headless": bool(self.chk_headless.get()),
            "target": self._bounded_int(self.ent_target.get(), 25, 1, 10000),
            "min_delay": min(min_delay, max_delay),
            "max_delay": max(min_delay, max_delay),
            "page_target": self._bounded_int(self.ent_page_target.get(), 5, 1, 100),
            "max_create_page_workers": self._bounded_int(
                self.ent_max_create_page_workers.get(), 3, 1, 10
            ),
            "min_page_delay": min(min_page_delay, max_page_delay),
            "max_page_delay": max(min_page_delay, max_page_delay),
            "feed_surf_min": self._bounded_int(self.ent_feed_surf_min.get(), 10, 0, 1440),
            "watch_review_min": self._bounded_int(self.ent_watch_review_min.get(), 5, 0, 1440),
            "tele_token": self.ent_tele_token.get().strip(),
            "tele_chatid": self.ent_tele_chatid.get().strip(),
            "screen_width": self.root.winfo_screenwidth(),
            "screen_height": self.root.winfo_screenheight(),
            "modes": {key: bool(value.get()) for key, value in self.mode_vars.items()},
            "options": {
                "browse_web": bool(self.chk_browse_web.get()),
                "warmup": bool(self.chk_warmup.get()),
                "watch_reels": bool(self.chk_watch_reels.get()),
                "view_stories": bool(self.chk_view_stories.get()),
                "check_notif": bool(self.chk_check_notif.get()),
                "chat_react": bool(self.chk_chat_react.get()),
                "interact_page": bool(self.chk_interact_page.get()),
                "cancel_old": bool(self.chk_cancel_old.get()),
            },
        }

    def _build_layout(self):
        self.root.configure(bg="#0B1117")

        # 1. HEADER
        self.header_bg = "#101820"
        self.header_muted = "#8EA3B5"
        self.header_active = "#19C3B1"
        self.header_tab_bg = "#1B2A35"
        self.frame_header = tk.Frame(self.root, bg=self.header_bg, height=68, padx=18, pady=9, highlightbackground="#263844", highlightthickness=1)
        self.frame_header.pack(fill="x", side="top")

        f_title = tk.Frame(self.frame_header, bg=self.header_bg)
        f_title.pack(side="left", padx=(0, 24))
        logo_badge = tk.Frame(f_title, bg="#17333A", width=46, height=46, highlightbackground="#28535A", highlightthickness=1)
        logo_badge.pack(side="left", padx=(0, 10))
        logo_badge.pack_propagate(False)
        try:
            self.logo_image = tk.PhotoImage(file=resource_path(os.path.join("assets", "facebook_tool_logo_64.png")))
            self.lbl_logo = tk.Label(logo_badge, image=self.logo_image, bg="#17333A")
        except (tk.TclError, OSError):
            self.logo_image = None
            self.lbl_logo = tk.Label(logo_badge, text="F", font=("Segoe UI", 17, "bold"), fg=self.header_active, bg="#17333A")
        self.lbl_logo.pack(expand=True)
        
        f_text = tk.Frame(f_title, bg=self.header_bg)
        f_text.pack(side="left")
        self.lbl_app_name = tk.Label(f_text, text="Facebook Workspace Pro", font=("Segoe UI", 12, "bold"), fg="#F4FAFC", bg=self.header_bg)
        self.lbl_app_name.pack(anchor="w")
        self.lbl_app_sub = tk.Label(f_text, text=f"PRO WORKSPACE  •  v{CURRENT_VERSION}  •  ĐẶNG PHÁT", font=("Segoe UI", 8), fg=self.header_muted, bg=self.header_bg)
        self.lbl_app_sub.pack(anchor="w")

        f_tabs = tk.Frame(self.frame_header, bg=self.header_bg)
        f_tabs.pack(side="left", padx=8)

        self.btn_tab_main = tk.Button(f_tabs, text="⌂  TRANG CHỦ", font=("Segoe UI", 9, "bold"), bg=self.header_active, fg="#071417", activebackground="#28D8C5", activeforeground="#071417", relief="flat", padx=15, pady=7, cursor="hand2", command=lambda: self.switch_tab(0))
        self.btn_tab_main.pack(side="left", padx=(0, 5))

        self.btn_tab_data = tk.Button(f_tabs, text="▦  THỐNG KÊ & QUẢN LÝ", font=("Segoe UI", 9, "bold"), bg=self.header_tab_bg, fg=self.header_muted, activebackground="#28414C", activeforeground="#F4FAFC", relief="flat", padx=15, pady=7, cursor="hand2", command=lambda: self.switch_tab(1))
        self.btn_tab_data.pack(side="left")

        f_right = tk.Frame(self.frame_header, bg=self.header_bg)
        f_right.pack(side="right", padx=(12, 0))

        tk.Button(
            f_right,
            text="⬆ Kiểm tra Update",
            font=("Segoe UI", 8, "bold"),
            bg="#10B981",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=lambda: threading.Thread(
                target=lambda: check_for_updates(self, manual=True),
                daemon=True,
            ).start(),
        ).pack(side="left", padx=5)

        tk.Label(f_right, text="THEME", font=("Segoe UI", 8, "bold"), fg=self.header_muted, bg=self.header_bg).pack(side="left", padx=(0, 7))
        self.cbo_theme = ttk.Combobox(f_right, values=list(THEMES.keys()), state="readonly", width=19)
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
            self.btn_tab_main.config(bg=self.header_active, fg="#071417")
            self.btn_tab_data.config(bg=self.header_tab_bg, fg=self.header_muted)
        else:
            self.tab1_view.pack_forget()
            self.tab2_view.pack(fill="both", expand=True)
            self.btn_tab_data.config(bg=self.header_active, fg="#071417")
            self.btn_tab_main.config(bg=self.header_tab_bg, fg=self.header_muted)

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
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background=t["card"], foreground=t["primary"])
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), background=t["card"], foreground=t["text"], fieldbackground=t["card"], borderwidth=0)
        self.style.map("Treeview", background=[("selected", t["primary"])], foreground=[("selected", "#FFFFFF")])
        configure_account_table_style(self.style, self.account_state_tree, self.tree)

        # Style Progressbar
        self.style.configure("Horizontal.TProgressbar", troughcolor=t["border"], background=t["primary"], bordercolor=t["card"])

        # Recolor legacy hard-coded neutral surfaces while preserving semantic
        # green/red/orange action and status colors.
        color_map = {
            "#0a0e1a": t["bg"], "#0b0f19": t["bg"], "#0b1117": t["bg"],
            "#131c2e": t["card"], "#101820": t["card"],
            "#070b14": t["entry_bg"], "#1e293b": t["border"],
            "#0254f8": t["card"], "#38bdf8": t["primary"],
            "#e2e8f0": t["text"], "#f8fafc": t["text"],
            "#94a3b8": t.get("muted", t["text"]),
            "#64748b": t.get("muted", t["text"]),
        }

        def recolor_widget(widget):
            for option in (
                "background", "foreground", "activebackground", "activeforeground",
                "highlightbackground", "insertbackground", "selectcolor",
            ):
                try:
                    current = str(widget.cget(option)).casefold()
                    if current in color_map:
                        widget.configure(**{option: color_map[current]})
                except (tk.TclError, KeyError):
                    pass
            for child in widget.winfo_children():
                recolor_widget(child)

        recolor_widget(self.root)

        # Cập nhật màu các ô ScrolledText
        for txt in [self.txt_accounts, self.txt_proxies, self.txt_targets]:
            txt.configure(bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["primary"], relief="solid", bd=1)
        
        self.txt_log.configure(bg=t["log_bg"], fg=t["log_fg"], relief="solid", bd=1)
        if hasattr(self, "lbl_tree_empty"):
            self.lbl_tree_empty.configure(bg=t["bg"], fg=t["text"])

    # [BẮT ĐẦU THAY THẾ TOÀN BỘ _build_tab_main VÀ _build_tab_data:]
    # [BẮT ĐẦU THAY THẾ _build_tab_main:]
    def _build_tab_main(self):
        paned_main = tk.PanedWindow(self.tab_main, orient="horizontal", bg="#0A0E1A", bd=0, sashwidth=6, sashrelief="ridge")
        paned_main.pack(fill="both", expand=True, padx=10, pady=8)

        # ==================== CỘT TRÁI (GIỮ NGUYÊN BỐ CỤC ĐẸP) ====================
        paned_left = tk.PanedWindow(paned_main, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=5, sashrelief="ridge")
        paned_main.add(paned_left, minsize=380)

        # 1. Cookie / Token Card (Auto Detect)
        card1 = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card1, minsize=90, height=160)

        f1_head = tk.Frame(card1, bg="#131C2E")
        f1_head.pack(fill="x", pady=(0, 2))
        tk.Label(f1_head, text="👤 1. HÀNG ĐỢI TÀI KHOẢN FACEBOOK", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f1_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_accounts_file).pack(side="right")

        tk.Label(card1, text="Dán Cookie hoặc User|Pass; hỗ trợ xếp hàng 50–100 tài khoản:", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w")
        self.txt_accounts = scrolledtext.ScrolledText(card1, bg="#070B14", fg="#E2E8F0", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_accounts.pack(fill="both", expand=True, pady=2)
        
        # Tự động thêm STT 1, 2, 3 khi rời chuột hoặc sau khi dán dữ liệu
        self.txt_accounts.bind("<FocusOut>", self.auto_format_cookie_numbers)

        f1_bot = tk.Frame(card1, bg="#131C2E")
        f1_bot.pack(fill="x")
        self.lbl_acc_count = tk.Label(f1_bot, text="Tổng: 0 nick   👥 0", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E")
        self.lbl_acc_count.pack(side="left")
        tk.Button(f1_bot, text="🗑 Xóa tất cả", font=("Segoe UI", 8), bg="#131C2E", fg="#F87171", relief="flat", cursor="hand2", command=lambda: [self.txt_accounts.delete("1.0", "end"), self.reload_table_from_text()]).pack(side="right")

        # 3. Chức năng tự động Card
        card3 = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card3, minsize=140, height=280)

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
            ("🔍 Kết bạn theo tên", "by_name"),
            ("👥 Kết bạn trong nhóm", "by_group"),
            ("📇 Kết bạn theo UID", "by_uid"),
            ("🚩 Tạo Fanpage", "create_page"),
            ("🚀 Đăng bài Fanpage", "post_page"),
            ("👑 Thêm Admin Page", "add_page_admin"),
            ("🏷️ Đổi tên Fanpage", "update_page_name"),
            ("👍 Mời bạn Like Page", "invite_like_page"),
            ("➕ Tham gia nhóm", "join_group"),
            ("📝 Đăng bài Facebook", "auto_post"),
            ("ℹ️ Cập nhật tiểu sử", "change_bio"),
            ("🖼️ Thay Avatar/Bìa", "change_avatar"),
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
        paned_left.add(card_log, minsize=80, height=140)

        f_log_head = tk.Frame(card_log, bg="#131C2E")
        f_log_head.pack(fill="x", pady=(0, 2))
        self.lbl_log_scope = tk.Label(f_log_head, text="📜 NHẬT KÝ TỔNG", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E")
        self.lbl_log_scope.pack(side="left")
        tk.Button(
            f_log_head,
            text="Log tổng",
            font=("Segoe UI", 7, "bold"),
            bg="#1E293B",
            fg="#CBD5E1",
            relief="flat",
            cursor="hand2",
            command=self.show_global_log,
        ).pack(side="right")
        self.txt_log = scrolledtext.ScrolledText(card_log, bg="#070B14", fg="#00FF66", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1, state="disabled")
        self.txt_log.pack(fill="both", expand=True)

        # ==================== CỘT PHẢI (THIẾT KẾ ĐẦY ĐỦ, CHUYÊN NGHIỆP) ====================
        paned_right = tk.PanedWindow(paned_main, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=5, sashrelief="ridge")
        paned_main.add(paned_right, minsize=420)

        # R1: Card Danh sách Proxy
        card2 = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card2, minsize=150, height=190)

        f2_head = tk.Frame(card2, bg="#131C2E")
        f2_head.pack(fill="x", pady=(0, 2))
        tk.Label(f2_head, text="🌐 2. DANH SÁCH PROXY", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f2_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_proxies_file).pack(side="right")

        tk.Label(card2, text="Nhập danh sách Proxy (IP:Port hoặc IP:Port:User:Pass):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w")
        self.txt_proxies = scrolledtext.ScrolledText(card2, height=4, bg="#070B14", fg="#E2E8F0", font=("Consolas", 9), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_proxies.pack(fill="x", pady=2)

        f2_cfg = tk.Frame(card2, bg="#131C2E")
        f2_cfg.pack(fill="x")
        self.proxy_mode = tk.StringVar(value="round_robin")
        for txt, val in [("Luân phiên", "round_robin"), ("Theo nhóm", "fixed_ratio"), ("Ngẫu nhiên", "random"), ("Riêng/account", "account"), ("API xoay", "rotating_api")]:
            tk.Radiobutton(
                f2_cfg,
                text=txt,
                variable=self.proxy_mode,
                value=val,
                font=("Segoe UI", 8),
                fg="#E2E8F0",
                bg="#131C2E",
                selectcolor="#070B14",
                cursor="hand2",
                command=self.reload_table_from_text,
            ).pack(side="left", padx=4)

        tk.Label(f2_cfg, text="Số nick/Proxy:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(8, 2))
        self.ent_proxy_ratio = tk.Entry(f2_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_proxy_ratio.insert(0, "20")
        self.ent_proxy_ratio.pack(side="left")


        f2_api = tk.Frame(card2, bg="#131C2E")
        f2_api.pack(fill="x", pady=(2, 0))
        tk.Label(f2_api, text="API Key / Link SuiProxy:", font=("Segoe UI", 8), fg="#38BDF8", bg="#131C2E").pack(side="left")
        self.ent_proxy_api = tk.Entry(f2_api, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_proxy_api.pack(side="left", fill="x", expand=True, padx=4)

        f2_bot = tk.Frame(card2, bg="#131C2E")
        f2_bot.pack(fill="x", pady=(2, 0))
        self.lbl_proxy_count = tk.Label(f2_bot, text="Tổng: 0 proxy", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E")
        self.lbl_proxy_count.pack(side="left")
        tk.Button(f2_bot, text="🗑 Xóa tất cả", font=("Segoe UI", 8), bg="#131C2E", fg="#F87171", relief="flat", cursor="hand2", command=lambda: self.txt_proxies.delete("1.0", "end")).pack(side="right")

        # R2: Trạng thái tài khoản và điều hướng theo đợt
        card_reg = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card_reg, minsize=135, height=190)

        f_reg_head = tk.Frame(card_reg, bg="#131C2E")
        f_reg_head.pack(fill="x", pady=(0, 3))
        tk.Label(f_reg_head, text="⇄ 4. TRẠNG THÁI TÀI KHOẢN", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Label(f_reg_head, text="Số tài khoản/đợt:", font=("Segoe UI", 8), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(12, 2))
        self.ent_batch_size = tk.Entry(f_reg_head, width=4, font=("Segoe UI", 8, "bold"), bg="#070B14", fg="#38BDF8", justify="center", relief="solid", bd=1)
        self.ent_batch_size.insert(0, "5")
        self.ent_batch_size.pack(side="left")
        self.ent_batch_size.bind("<FocusOut>", lambda _event: self.refresh_account_state_table(reset_batch=True))

        f_batch_nav = tk.Frame(card_reg, bg="#131C2E")
        f_batch_nav.pack(fill="x", pady=(0, 3))
        tk.Button(f_batch_nav, text="◀ Đợt trước", font=("Segoe UI", 7, "bold"), bg="#1E293B", fg="#E2E8F0", relief="flat", cursor="hand2", command=lambda: self.change_batch(-1)).pack(side="left")
        self.lbl_batch_info = tk.Label(f_batch_nav, text="Đợt 0 / 0", font=("Segoe UI", 8, "bold"), fg="#FACC15", bg="#131C2E")
        self.lbl_batch_info.pack(side="left", expand=True)
        tk.Button(f_batch_nav, text="Đợt sau ▶", font=("Segoe UI", 7, "bold"), bg="#1E293B", fg="#E2E8F0", relief="flat", cursor="hand2", command=lambda: self.change_batch(1)).pack(side="right")

        state_columns = ("stt", "account", "status", "task", "next_page", "action")
        self.account_state_tree = ttk.Treeview(card_reg, columns=state_columns, show="headings", selectmode="browse", height=5)
        self.account_state_tree.heading("stt", text="STT")
        self.account_state_tree.heading("account", text="Tài khoản")
        self.account_state_tree.heading("status", text="Trạng thái")
        self.account_state_tree.heading("task", text="Kết quả tác vụ")
        self.account_state_tree.heading("next_page", text="Page tiếp / Còn lại")
        self.account_state_tree.heading("action", text="Tác vụ hiện tại")
        self.account_state_tree.column("stt", width=40, anchor="center", stretch=False)
        self.account_state_tree.column("account", width=120, anchor="w")
        self.account_state_tree.column("status", width=105, anchor="center", stretch=False)
        self.account_state_tree.column("task", width=100, anchor="center", stretch=False)
        self.account_state_tree.column("next_page", width=155, anchor="center", stretch=False)
        self.account_state_tree.column("action", width=190, anchor="w")
        configure_account_table_style(self.style, self.account_state_tree)
        self.account_state_tree.pack(fill="both", expand=True)
        state_scroll = ttk.Scrollbar(card_reg, orient="horizontal", command=self.account_state_tree.xview)
        state_scroll.pack(fill="x")
        self.account_state_tree.configure(xscrollcommand=state_scroll.set)
        self.account_state_tree.bind("<<TreeviewSelect>>", self.on_account_state_selected)

        self.lbl_queue_info = tk.Label(
            card_reg,
            text="Tổng: 0 • LIVE: 0 • DIE: 0 • ERROR: 0",
            font=("Segoe UI", 7),
            fg="#CBD5E1",
            bg="#131C2E",
            anchor="w",
        )
        self.lbl_queue_info.pack(fill="x", pady=(3, 0))

        # R3: Card Nuôi Nick Chống Checkpoint
        card4 = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card4, minsize=115, height=155)

        tk.Label(card4, text="🛡️ 5. HIỆU NĂNG & ĐIỀU TIẾT", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 2))

        f4_sys = tk.Frame(card4, bg="#131C2E")
        f4_sys.pack(fill="x", pady=2)
        tk.Label(f4_sys, text="Trình duyệt đồng thời (1–20):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_threads = tk.Entry(f4_sys, width=4, font=("Segoe UI", 8, "bold"), bg="#070B14", fg="#38BDF8", justify="center", relief="solid", bd=1)
        self.ent_threads.insert(0, "6")
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
        paned_right.add(f_bottom_right, minsize=120, height=145)

        card5 = tk.Frame(f_bottom_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=6)
        card5.pack(fill="x", pady=(0, 4))

        tk.Label(card5, text="⚙️ 6. THÔNG SỐ GỬI KẾT BẠN & TƯƠNG TÁC", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 2))

        f5_cfg = tk.Frame(card5, bg="#131C2E")
        f5_cfg.pack(fill="x", expand=True)
        tk.Label(f5_cfg, text="Chỉ tiêu bạn/nick:", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_target = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_target.insert(0, "25")
        self.ent_target.pack(side="left", padx=4)

        tk.Label(f5_cfg, text="Số Page/nick:", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(10, 2))
        self.ent_page_target = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_page_target.insert(0, "5")
        self.ent_page_target.pack(side="left", padx=2)

        tk.Label(f5_cfg, text="Delay Page (s):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(10, 2))
        self.ent_min_page_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_min_page_delay.insert(0, "60")
        self.ent_min_page_delay.pack(side="left", padx=2)
        tk.Label(f5_cfg, text="-", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_page_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_max_page_delay.insert(0, "120")
        self.ent_max_page_delay.pack(side="left", padx=2)

        tk.Label(f5_cfg, text="Delay click (s):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(15, 2))
        self.ent_min_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_min_delay.insert(0, "25")
        self.ent_min_delay.pack(side="left", padx=2)
        tk.Label(f5_cfg, text="-", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_max_delay.insert(0, "35")
        self.ent_max_delay.pack(side="left", padx=2)

        # Thêm cấu hình số phút ngâm giữa các lần tạo Page
        f5_page_warmup = tk.Frame(card5, bg="#131C2E")
        f5_page_warmup.pack(fill="x", expand=True, pady=(2, 0))

        tk.Label(f5_page_warmup, text="Lướt Feed đệm (phút):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_feed_surf_min = tk.Entry(f5_page_warmup, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_feed_surf_min.insert(0, "10")
        self.ent_feed_surf_min.pack(side="left", padx=2)

        tk.Label(f5_page_warmup, text="Xem Review đệm (phút):", font=("Segoe UI", 8), fg="#E2E8F0", bg="#0254F8").pack(side="left", padx=(10, 2))
        self.ent_watch_review_min = tk.Entry(f5_page_warmup, width=4, font=("Segoe UI", 8), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_watch_review_min.insert(0, "5")
        self.ent_watch_review_min.pack(side="left", padx=2)
        tk.Label(f5_page_warmup, text="Luồng Page/BM:", font=("Segoe UI", 8), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(10, 2))
        self.ent_max_create_page_workers = tk.Entry(f5_page_warmup, width=3, font=("Segoe UI", 8), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_max_create_page_workers.insert(0, "3")
        self.ent_max_create_page_workers.pack(side="left", padx=2)
        # Ô nhập STT rải rác hoặc dải số (ví dụ: 1, 3, 5-8)
        f_filter_idx = tk.Frame(f_bottom_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=6, pady=3)
        f_filter_idx.pack(fill="x", pady=(0, 4))
        tk.Label(f_filter_idx, text="🎯 Chọn STT chạy:", font=("Segoe UI", 8, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        self.ent_selected_indexes = tk.Entry(f_filter_idx, font=("Consolas", 9), bg="#070B14", fg="#00FF66", relief="solid", bd=1)
        self.ent_selected_indexes.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(f_filter_idx, text="(VD: 1, 3, 5-9)", font=("Segoe UI", 7), fg="#64748B", bg="#131C2E").pack(side="right")

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
        self.lbl_stat_success = make_stat_box(f_stats, "Account LIVE", "0", 2, "#10B981")
        self.lbl_stat_failed = make_stat_box(f_stats, "Account lỗi", "0", 3, "#EF4444")
# [KẾT THÚC THAY THẾ]

    def _build_tab_data(self):
        # PanedWindow dọc cho Tab 2 (Kéo dãn thanh công cụ / Bảng dữ liệu)
        paned_data = tk.PanedWindow(self.tab_data, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=4, sashrelief="ridge")
        paned_data.pack(fill="both", expand=True, padx=8, pady=6)

        # 1. Khu điều khiển quản lý: chia hàng để dễ quét và không dồn nút.
        frame_ribbon = tk.Frame(
            paned_data, bg="#131C2E", padx=12, pady=8,
            highlightbackground="#26384A", highlightthickness=1,
        )
        paned_data.add(frame_ribbon, minsize=84, height=92)

        ribbon_head = tk.Frame(frame_ribbon, bg="#131C2E")
        ribbon_head.pack(fill="x", pady=(0, 7))
        tk.Label(
            ribbon_head, text="QUẢN LÝ TÀI KHOẢN", font=("Segoe UI", 10, "bold"),
            fg="#F8FAFC", bg="#131C2E",
        ).pack(side="left")
        self.lbl_management_summary = tk.Label(
            ribbon_head, text="Tổng 0  •  LIVE 0  •  DIE 0  •  ERROR 0",
            font=("Segoe UI", 8, "bold"), fg="#94A3B8", bg="#131C2E",
        )
        self.lbl_management_summary.pack(side="right")

        ribbon_actions = tk.Frame(frame_ribbon, bg="#131C2E")
        ribbon_actions.pack(fill="x")

        def make_btn(parent, text, cmd, color="#0369A1"):
            return tk.Button(
                parent, text=text, font=("Segoe UI", 8, "bold"),
                bg=color, fg="#FFFFFF", activebackground=color,
                activeforeground="#FFFFFF", relief="flat", padx=9, pady=5,
                cursor="hand2", command=cmd,
            )

        make_btn(ribbon_actions, "➕ Nhập tài khoản", self.open_import_dialog).pack(side="left", padx=(0, 4))
        make_btn(ribbon_actions, "🌐 Mở profile", self.open_selected_profile).pack(side="left", padx=2)
        make_btn(ribbon_actions, "🔍 Kiểm tra LIVE/DIE", self.check_live_selected).pack(side="left", padx=2)
        make_btn(ribbon_actions, "🔑 Lấy token", self.get_token_selected).pack(side="left", padx=2)
        make_btn(ribbon_actions, "🔐 Lấy mã 2FA", self.generate_2fa_dialog).pack(side="left", padx=2)
        make_btn(
            ribbon_actions,
            "📋 Kết quả tạo Page",
            self.open_create_page_results_dialog,
            color="#7C3AED",
        ).pack(side="left", padx=2)
        make_btn(ribbon_actions, "🗑 Xóa chọn", self.delete_selected_rows, color="#B91C1C").pack(side="left", padx=2)

        f_search = tk.Frame(ribbon_actions, bg="#131C2E")
        f_search.pack(side="right")
        self.ent_search_tree = tk.Entry(
            f_search, width=20, font=("Segoe UI", 9), bg="#070B14", fg="#FFFFFF",
            insertbackground="#FFFFFF", relief="solid", bd=1,
        )
        self.ent_search_tree.pack(side="left", ipady=3, padx=(0, 5))

        def filter_table(event=None):
            kw = self.ent_search_tree.get().strip().lower()
            for item in self.tree.get_children():
                vals = [str(v).lower() for v in self.tree.item(item, "values")]
                if not kw or any(kw in v for v in vals):
                    self.tree.reattach(item, "", "end")
                else:
                    self.tree.detach(item)
        self.ent_search_tree.bind("<KeyRelease>", filter_table)

        make_btn(f_search, "Xuất CSV", self.export_to_csv, color="#047857").pack(side="left")

        # 2. Bảng dữ liệu trung tâm Dark Theme
        frame_tree = tk.Frame(paned_data, bg="#0A0E1A")
        paned_data.add(frame_tree, minsize=200)

        columns = ("select", "id", "uid", "password", "2fa", "status", "action")
        self.tree = ttk.Treeview(frame_tree, columns=columns, show="headings", selectmode="extended")
        self.tree.tag_configure("empty", foreground="#8EA3B5")
        configure_account_table_style(self.style, self.tree)

        self.tree.heading("select", text="[✔]")
        self.tree.heading("id", text="STT")
        self.tree.heading("uid", text="UID")
        self.tree.heading("password", text="PASSWORD")
        self.tree.heading("2fa", text="2FA")
        self.tree.heading("status", text="STATUS")
        self.tree.heading("action", text="ACTION")

        self.tree.column("select", width=45, anchor="center")
        self.tree.column("id", width=45, anchor="center")
        self.tree.column("uid", width=130, anchor="center")
        self.tree.column("password", width=120, anchor="center")
        self.tree.column("2fa", width=100, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("action", width=250, anchor="w")

        # Context Menu
        self.tree_menu = tk.Menu(self.tree, tearoff=0, bg="#131C2E", fg="#FFFFFF")
        self.tree_menu.add_command(label="Copy UID", command=lambda: self.copy_tree_data("uid"))
        self.tree_menu.add_command(label="Copy Password", command=lambda: self.copy_tree_data("password"))
        self.tree_menu.add_command(label="Copy UID | Password", command=lambda: self.copy_tree_data("uid|pass"))
        self.tree_menu.add_command(label="Copy UID | Password | 2FA", command=lambda: self.copy_tree_data("uid|pass|2fa"))
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Copy dòng gốc", command=lambda: self.copy_tree_data("raw"))

        def show_context_menu(event):
            item = self.tree.identify_row(event.y)
            if item:
                if item not in self.tree.selection():
                    self.tree.selection_set(item)
                self.tree_menu.tk_popup(event.x_root, event.y_root)

        self.tree.bind("<Button-3>", show_context_menu)
        self.tree.bind("<Control-c>", lambda e: self.copy_tree_data("raw"))

        def toggle_row_check(event):
            region = self.tree.identify("region", event.x, event.y)
            if region == "cell":
                col = self.tree.identify_column(event.x)
                if col == "#1":  # Bấm trúng cột Checkbox đầu tiên
                    item = self.tree.identify_row(event.y)
                    if item:
                        vals = list(self.tree.item(item, "values"))
                        vals[0] = "[ ]" if vals[0] == "[✔]" else "[✔]"
                        self.tree.item(item, values=vals)

        self.tree.bind("<ButtonRelease-1>", toggle_row_check)

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.lbl_tree_empty = tk.Label(
            frame_tree,
            text="Chưa có tài khoản\nNhập dữ liệu ở trang chủ để bắt đầu",
            font=("Segoe UI", 10),
            fg="#8EA3B5",
            bg="#0B1117",
            justify="center",
        )
        self.lbl_tree_empty.place(relx=0.5, rely=0.5, anchor="center")

        # 3. Thanh trạng thái dưới đáy
        self.lbl_footer_status = tk.Label(self.tab_data, text="Tổng số nick: 0 | Sẵn sàng hoạt động.", font=("Segoe UI", 9), fg="#94A3B8", bg="#131C2E", anchor="w", padx=10, pady=4)
        self.lbl_footer_status.pack(fill="x", side="bottom")

    def copy_tree_data(self, mode):
        selected = self.tree.selection()
        if not selected:
            return
        result = []
        for item in selected:
            vals = self.tree.item(item, "values")
            stt = int(vals[1])
            parsed = self.account_states.get(stt)
            if not parsed: continue
            
            if mode == "uid":
                result.append(parsed["uid"])
            elif mode == "password":
                result.append(parsed["password"])
            elif mode == "uid|pass":
                result.append(f"{parsed['uid']}|{parsed['password']}")
            elif mode == "uid|pass|2fa":
                result.append(f"{parsed['uid']}|{parsed['password']}|{parsed['2fa']}")
            elif mode == "raw":
                result.append(parsed["raw_line"])
                
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(result))
            self.log(f"[+] Đã copy {len(result)} dòng (Chế độ: {mode})")
    def open_create_page_results_dialog(self):
        window = self.create_page_results_window
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            self.refresh_create_page_results_dialog()
            return

        window = tk.Toplevel(self.root)
        self.create_page_results_window = window
        window.title("Kết quả tạo Page theo tài khoản")
        window.geometry("1080x620")
        window.minsize(820, 480)
        window.configure(bg="#0B1117")

        header = tk.Frame(window, bg="#101820", padx=16, pady=12)
        header.pack(fill="x")
        header_text = tk.Frame(header, bg="#101820")
        header_text.pack(side="left")
        tk.Label(
            header_text, text="KẾT QUẢ CREATE PAGE", font=("Segoe UI", 13, "bold"),
            fg="#F8FAFC", bg="#101820",
        ).pack(anchor="w")
        tk.Label(
            header_text,
            text="Theo dõi tài khoản đã hoàn tất và tài khoản ngừng do mất phiên đăng nhập",
            font=("Segoe UI", 8), fg="#94A3B8", bg="#101820",
        ).pack(anchor="w", pady=(2, 0))

        summary = tk.Frame(header, bg="#101820")
        summary.pack(side="right")
        self.lbl_create_page_live_count = tk.Label(
            summary, text="LIVE  0", font=("Segoe UI", 10, "bold"),
            fg="#4ADE80", bg="#17332A", padx=12, pady=7,
        )
        self.lbl_create_page_live_count.pack(side="left", padx=4)
        self.lbl_create_page_die_count = tk.Label(
            summary, text="DIE  0", font=("Segoe UI", 10, "bold"),
            fg="#F87171", bg="#3B1D24", padx=12, pady=7,
        )
        self.lbl_create_page_die_count.pack(side="left", padx=4)

        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        self.create_page_results_notebook = notebook
        self.create_page_result_trees = {}

        for result_type, title in (
            ("completed", "LIVE - ĐÃ TẠO XONG PAGE"),
            ("die", "DIE - ĐÃ DỪNG"),
            ("checkpoint", "CHECKPOINT - CẦN XÁC MINH"),
        ):
            frame = tk.Frame(notebook, bg="#0B1117")
            notebook.add(frame, text=title)
            columns = ("stt", "account", "pages", "detail", "time")
            tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
            tree.heading("stt", text="STT")
            tree.heading("account", text="Tài khoản / UID")
            tree.heading("pages", text="Số Page")
            tree.heading("detail", text="Kết quả / Lý do")
            tree.heading("time", text="Thời gian")
            tree.column("stt", width=55, anchor="center", stretch=False)
            tree.column("account", width=180)
            tree.column("pages", width=90, anchor="center", stretch=False)
            tree.column("detail", width=430)
            tree.column("time", width=145, anchor="center", stretch=False)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self.create_page_result_trees[result_type] = tree

        footer = tk.Frame(window, bg="#0B1117", padx=12, pady=10)
        footer.pack(fill="x", side="bottom")
        self.lbl_create_page_result_summary = tk.Label(
            footer, text="", font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0", bg="#0B1117",
        )
        self.lbl_create_page_result_summary.pack(side="left")
        tk.Button(
            footer, text="XUẤT TẤT CẢ", command=lambda: self.export_create_page_results_excel(),
            font=("Segoe UI", 8, "bold"), bg="#0369A1", fg="#FFFFFF",
            relief="flat", padx=12, pady=6, cursor="hand2",
        ).pack(side="right", padx=(5, 0))
        tk.Button(
            footer, text="XUẤT DIE", command=lambda: self.export_create_page_results_excel("die"),
            font=("Segoe UI", 8, "bold"), bg="#B91C1C", fg="#FFFFFF",
            relief="flat", padx=12, pady=6, cursor="hand2",
        ).pack(side="right", padx=(5, 0))
        tk.Button(
            footer, text="XUẤT LIVE", command=lambda: self.export_create_page_results_excel("completed"),
            font=("Segoe UI", 8, "bold"), bg="#047857", fg="#FFFFFF",
            relief="flat", padx=12, pady=6, cursor="hand2",
        ).pack(side="right", padx=(5, 0))
        tk.Button(
            footer, text="ĐÓNG", command=window.destroy,
            font=("Segoe UI", 9, "bold"), bg="#1E293B", fg="#FFFFFF",
            relief="flat", padx=14, pady=5, cursor="hand2",
        ).pack(side="right", padx=(10, 0))
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        self.refresh_create_page_results_dialog()

    def refresh_create_page_results_dialog(self):
        window = getattr(self, "create_page_results_window", None)
        if window is None or not window.winfo_exists():
            return
        counts = {}
        for result_type in ("completed", "die", "checkpoint"):
            tree = self.create_page_result_trees.get(result_type)
            if tree is None:
                continue
            for item in tree.get_children():
                tree.delete(item)
            records = self.get_create_page_account_results(result_type)
            counts[result_type] = len(records)
            for position, record in enumerate(records, 1):
                pages = f"{record['created_count']}/{record['target_count']}"
                if result_type == "die" and not record["target_count"]:
                    pages = str(record["created_count"])
                detail = (
                    "Đã tạo đủ Page"
                    if result_type == "completed"
                    else record["reason"] or "Tài khoản không còn đăng nhập hợp lệ"
                )
                tree.insert(
                    "", "end", iid=f"{result_type}_{position}",
                    values=(
                        record["stt"], record["account_id"] or record["uid"],
                        pages, detail, record["time"],
                    ),
                )
        if hasattr(self, "lbl_create_page_result_summary"):
            self.lbl_create_page_result_summary.config(
                text=(
                    f"LIVE đã tạo xong: {counts.get('completed', 0)}   |   "
                    f"DIE: {counts.get('die', 0)}   |   CHECKPOINT: {counts.get('checkpoint', 0)}"
                )
            )
        if hasattr(self, "lbl_create_page_live_count"):
            self.lbl_create_page_live_count.config(
                text=f"LIVE  {counts.get('completed', 0)}"
            )
        if hasattr(self, "lbl_create_page_die_count"):
            self.lbl_create_page_die_count.config(text=f"DIE  {counts.get('die', 0)}")

    def export_create_page_results_excel(self, result_type=None):
        result_types = (result_type,) if result_type else ("completed", "die")
        categorized_records = {
            key: self.get_create_page_account_results(key)
            for key in result_types
        }
        if not any(categorized_records.values()):
            messagebox.showwarning("Xuất Excel", "Danh sách được chọn đang trống.")
            return
        suffix = {None: "LIVE_DIE", "completed": "LIVE", "die": "DIE"}[result_type]
        file_path = filedialog.asksaveasfilename(
            parent=self.create_page_results_window,
            title=f"Xuất danh sách {suffix}",
            defaultextension=".xlsx",
            initialfile=f"create_page_{suffix}_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not file_path:
            return
        try:
            write_create_page_results_xlsx(file_path, categorized_records)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Xuất Excel thất bại", str(exc), parent=self.create_page_results_window)
            return
        messagebox.showinfo(
            "Xuất Excel thành công",
            f"Đã lưu báo cáo tại:\n{file_path}",
            parent=self.create_page_results_window,
        )

    def remove_processed_create_page_accounts_from_input(self):
        processed_sources = self.get_processed_create_page_sources()
        if not processed_sources:
            return
        current_lines = [
            line for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        remaining_lines = keep_unprocessed_account_lines(current_lines, processed_sources)
        removed_count = len(current_lines) - len(remaining_lines)
        if removed_count <= 0:
            return
        self.txt_accounts.delete("1.0", "end")
        if remaining_lines:
            self.txt_accounts.insert(
                "1.0",
                "\n".join(
                    f"{index}. {normalize_account_source_line(line)}"
                    for index, line in enumerate(remaining_lines, 1)
                ) + "\n",
            )
        self.reload_table_from_text()
        self.save_settings()
        self.log(
            f"[i] Đã chuyển {removed_count} tài khoản đã hoàn tất/DIE khỏi danh sách chờ."
        )



    def update_footer_count(self):
        total = len(self.tree.get_children())
        self.lbl_footer_status.config(text=f"Tổng số nick: {total} | Sẵn sàng hoạt động.")

    def get_batch_size(self):
        if not hasattr(self, "ent_batch_size"):
            return 5
        return self._bounded_int(self.ent_batch_size.get(), 5, 1, 10000)

    def refresh_account_state_table(self, reset_batch=False):
        if not hasattr(self, "account_state_tree"):
            return
        batches = split_account_batches(self.account_states.indexes(), self.get_batch_size())
        if reset_batch:
            self.current_batch = 1
        total_batches = len(batches)
        if total_batches == 0:
            self.current_batch = 1
            visible_indexes = []
        else:
            self.current_batch = max(1, min(self.current_batch, total_batches))
            visible_indexes = batches[self.current_batch - 1]

        selected_index = self.selected_log_account
        for item in self.account_state_tree.get_children():
            self.account_state_tree.delete(item)
        for index in visible_indexes:
            state = self.account_states.get(index)
            if state is None:
                continue
            item_id = f"account_state_{index}"
            self.account_state_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    state["stt"],
                    state["account_id"],
                    ACCOUNT_STATUS_LABELS[state["status"]],
                    state["last_task_result"],
                    page_wait_label(state),
                    state["current_action"],
                ),
                tags=(state["status"],),
            )
            if selected_index == index:
                self.account_state_tree.selection_set(item_id)

        self.lbl_batch_info.config(
            text=f"Đợt {self.current_batch if total_batches else 0} / {total_batches}"
        )
        self.refresh_state_summary()

    def refresh_account_state_row(self, index):
        if not hasattr(self, "account_state_tree"):
            return
        item_id = f"account_state_{int(index)}"
        if not self.account_state_tree.exists(item_id):
            self.refresh_state_summary()
            return
        state = self.account_states.get(index)
        if state is None:
            return
        self.account_state_tree.item(
            item_id,
            values=(
                state["stt"],
                state["account_id"],
                ACCOUNT_STATUS_LABELS[state["status"]],
                state["last_task_result"],
                page_wait_label(state),
                state["current_action"],
            ),
            tags=(state["status"],),
        )
        self.refresh_state_summary()

    def refresh_state_summary(self):
        summary = self.account_states.summary()
        total = sum(summary.values())
        task_summary = self.account_states.task_summary()
        task_totals = {status: task_summary[status]
                       for status in ("SUCCESS", "FAILED", "ERROR", "SKIPPED")}
        if hasattr(self, "lbl_queue_info"):
            self.lbl_queue_info.config(
                text=(
                    f"Tổng: {total} • LIVE: {summary['LIVE']} • "
                    f"DIE: {summary['DIE']} • ERROR: {summary['ERROR']} • CHECKPOINT: {summary['CHECKPOINT']}\n"
                    + "Task: " + " • ".join(f"{key}: {value}" for key, value in task_totals.items())
                )
            )
        if hasattr(self, "lbl_stat_running"):
            self.lbl_stat_running.config(text=str(summary["CHECKING"]))
            self.lbl_stat_success.config(text=str(summary["LIVE"]))
            self.lbl_stat_failed.config(text=str(summary["DIE"] + summary["ERROR"]))
        if hasattr(self, "lbl_management_summary"):
            self.lbl_management_summary.config(
                text=(
                    f"Tổng {total}  •  LIVE {summary['LIVE']}  •  "
                    f"DIE {summary['DIE']}  •  ERROR {summary['ERROR']}  •  CHECKPOINT {summary['CHECKPOINT']}"
                )
            )

    def change_batch(self, offset):
        total_batches = len(split_account_batches(self.account_states.indexes(), self.get_batch_size()))
        if total_batches == 0:
            return
        self.current_batch = max(1, min(total_batches, self.current_batch + int(offset)))
        self.refresh_account_state_table()

    def show_batch(self, batch_number):
        self.current_batch = max(1, int(batch_number))
        self.refresh_account_state_table()

    def on_account_state_selected(self, _event=None):
        selection = self.account_state_tree.selection()
        if not selection:
            return
        match = re.fullmatch(r"account_state_(\d+)", selection[0])
        if not match:
            return
        self.selected_log_account = int(match.group(1))
        self.render_log_view()

    def show_global_log(self):
        self.selected_log_account = None
        if hasattr(self, "account_state_tree"):
            selection = self.account_state_tree.selection()
            if selection:
                self.account_state_tree.selection_remove(*selection)
        self.render_log_view()

    def render_log_view(self):
        if not hasattr(self, "txt_log"):
            return
        if self.selected_log_account is None:
            with self.global_log_lock:
                lines = list(self.global_logs)
            title = "📜 NHẬT KÝ TỔNG"
        else:
            state = self.account_states.get(self.selected_log_account)
            lines = (state["history_logs"] + ["[CURRENT RUN]"] + state["logs"]) if state else []
            account_label = state["account_id"] if state else str(self.selected_log_account)
            title = f"📜 NHẬT KÝ: {account_label}"

        self.lbl_log_scope.config(text=title)
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        if lines:
            self.txt_log.insert("1.0", "\n".join(lines) + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def set_account_state(self, index, status=None, current_action=None):
        self.account_states.update(index, status=status, current_action=current_action)
        self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))

    def record_task_result(self, index, module, status, detail="", outcome=None, preserve_outcomes=False):
        self.account_states.record_task(index, module, status, detail, outcome, preserve_outcomes)
        self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))

    def finalize_active_account_tasks(self, index, status, reason):
        self.account_states.finalize_active_tasks(index, status, reason)
        self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))

    async def resolve_effective_proxy(self, index, assigned_proxy):
        config = self.run_config
        mode = config.get("proxy_mode", "round_robin")
        effective_proxy = str(assigned_proxy or "")
        proxy_api = str(config.get("proxy_api") or "").strip()
        proxy_list_configured = bool(str(config.get("proxies") or "").strip())
        has_proxy_source = bool(effective_proxy or proxy_api or proxy_list_configured)
        if mode == "rotating_api" and proxy_api:
            async with self.proxy_api_lock:
                effective_proxy = await asyncio.to_thread(fetch_proxy_from_api, proxy_api)
            if not effective_proxy:
                raise ConnectionError("API proxy không trả về proxy hợp lệ.")
        elif mode == "rotating_api" and has_proxy_source:
            if not proxy_api:
                raise ValueError("API xoay chưa được cấu hình; không dùng IP thật.")
        required = bool(config.get("proxy_required", False)) or (
            mode in {"account", "rotating_api"} and has_proxy_source
        )
        if (required and not effective_proxy) or (effective_proxy and not parse_proxy(effective_proxy)):
            raise ValueError("Thiếu proxy bắt buộc hoặc proxy sai định dạng; không dùng IP thật.")
        self.account_states.set_proxy(index, effective_proxy)
        def update_proxy():
            if hasattr(self, "tree") and self.tree.exists(str(index)):
                values = list(self.tree.item(str(index), "values"))
                values[8] = effective_proxy or "Không dùng"
                self.tree.item(str(index), values=values)
            self.refresh_account_state_row(index)
        self.post_ui(update_proxy)
        return effective_proxy

    def stop_checkpoint_account(self, index):
        state = self.account_states.get(index)
        if state is None or state.get("checkpoint_stopped"):
            return
        self.set_account_state(
            index, status="CHECKPOINT",
            current_action="Đã dừng - Facebook Checkpoint",
        )
        self.log("[CHECKPOINT] Facebook yêu cầu xác minh tài khoản.", account_index=index)
        self.log("[CHECKPOINT] Dừng toàn bộ tác vụ của account này.", account_index=index)
        raw_line = state.get("raw_line", "")
        try:
            save_checkpoint_account(raw_line)
        except OSError as exc:
            self.log(f"[ERROR] Không lưu được danh sách checkpoint: {exc}", account_index=index)
        if hasattr(self, "create_page_result_lock"):
            self.record_create_page_account_result(
                index, "checkpoint", reason="Đã dừng - Facebook Checkpoint"
            )

    async def guard_facebook_checkpoint(self, page, index=None):
        if index is None:
            log_context = getattr(self, "account_log_context", None)
            index = log_context.get() if log_context is not None else None
        state = self.account_states.get(index) if index is not None else None
        if (state and state.get("checkpoint_stopped")) or await detect_facebook_account_state(page) == "CHECKPOINT":
            if index is not None:
                self.stop_checkpoint_account(index)
            raise FacebookCheckpointStopped()

    async def watch_facebook_checkpoint(self, page, index, worker):
        try:
            while not worker.done():
                is_closed = getattr(page, "is_closed", None)
                if callable(is_closed) and is_closed() is True:
                    self.set_account_failure(index, "automation", "Profile/trình duyệt đã được đóng thủ công; dừng worker của tài khoản.")
                    worker.cancel()
                    return
                await self.guard_facebook_checkpoint(page, index)
                await asyncio.sleep(2.5)
        except FacebookCheckpointStopped:
            worker.cancel()
        except Exception as exc:
            self.set_account_failure(index, "automation", f"Lỗi theo dõi phiên Facebook: {exc}")
            worker.cancel()

    def set_account_failure(self, index, failure_kind, reason):
        status = self.account_states.set_failure(index, failure_kind, reason)
        if (
            status == "DIE"
            and getattr(self, "run_config", {}).get("modes", {}).get("create_page", False)
        ):
            self.record_create_page_account_result(index, "die", reason=reason)
        self.post_ui(lambda idx=int(index): [
            self.refresh_account_state_row(idx),
            self.render_log_view() if self.selected_log_account == idx else None,
        ])
        return status

    def reset_create_page_account_results(self):
        with self.create_page_result_lock:
            self.create_page_account_results = {"completed": {}, "die": {}, "checkpoint": {}}
        self.refresh_create_page_results_dialog()

    def record_create_page_account_result(
        self, index, result_type, reason="", created_count=0, target_count=0
    ):
        if result_type not in {"completed", "die", "checkpoint"}:
            raise ValueError(f"Loại kết quả Create Page không hợp lệ: {result_type}")
        state = self.account_states.get(index)
        if state is None:
            return
        source_line = normalize_account_source_line(
            state.get("source_line") or state.get("raw_line")
        )
        key = source_line or state.get("uid") or state.get("account_id") or str(index)
        record = {
            "stt": state.get("stt", index),
            "account_id": state.get("account_id", ""),
            "uid": state.get("uid", "") or state.get("account_id", ""),
            "password": state.get("password") or state.get("pwd", ""),
            "raw_line": (state.get("raw_line") or source_line) if result_type == "checkpoint" else source_line,
            "created_count": int(created_count or 0),
            "target_count": int(target_count or 0),
            "reason": str(reason or ""),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        opposite = "die" if result_type == "completed" else "completed"
        with self.create_page_result_lock:
            self.create_page_account_results[opposite].pop(key, None)
            if result_type == "checkpoint":
                self.create_page_account_results["die"].pop(key, None)
            self.create_page_account_results.setdefault(result_type, {})[key] = record
        self.post_ui(self.refresh_create_page_results_dialog)

    def get_create_page_account_results(self, result_type):
        with self.create_page_result_lock:
            return [
                dict(record)
                for record in self.create_page_account_results.get(result_type, {}).values()
            ]

    def get_processed_create_page_sources(self):
        with self.create_page_result_lock:
            records = [
                *self.create_page_account_results["completed"].values(),
                *self.create_page_account_results["die"].values(),
            ]
        return {record["raw_line"] for record in records if record.get("raw_line")}

    def get_targets_for_mode(self, targets, mode, known_modes=None):
        """Lọc target theo prefix mode, vẫn hỗ trợ danh sách cũ không có prefix."""
        available_modes = known_modes if known_modes is not None else self.mode_vars
        return filter_targets_for_mode(targets, mode, available_modes)

    def update_tree_row(self, item_id, current_friends=None, sent_today=None, status=None):
        """Cập nhật dữ liệu hàng trong bảng Treeview chính xác vào cột Trạng Thái (Index 8)"""
        def _update():
            if self.tree.exists(item_id):
                vals = list(self.tree.item(item_id, "values"))
                msg_parts = []
                account_state = None
                if str(item_id).isdigit():
                    account_state = self.account_states.get(int(item_id))
                if account_state:
                    msg_parts.append(ACCOUNT_STATUS_LABELS[account_state["status"]])
                # Gom các thông tin phụ vào chung cột Status để không đè lên Cookie/Email/Proxy
                if current_friends is not None:
                    msg_parts.append(f"Bạn bè: {current_friends}")
                if sent_today is not None:
                    msg_parts.append(f"Đã gửi: {sent_today}")
                if status is not None and not account_state:
                    msg_parts.append(status)
                
                if msg_parts:
                    vals[5] = " | ".join(msg_parts)
                row_status = account_state["status"] if account_state else "UNKNOWN"
                self.tree.item(item_id, values=vals, tags=(row_status,))
        self.post_ui(_update)

    def log(self, text, account_index=None):
        """Route log vào đúng tài khoản hiện tại hoặc nhật ký tổng."""
        resolved_index = account_index
        if resolved_index is None:
            resolved_index = self.account_log_context.get()
        message = str(text)

        if resolved_index is not None and self.account_states.get(resolved_index) is not None:
            current_action = None
            stripped = message.lstrip()
            if stripped.startswith(("[*]", "[🚀]", "[⏳]")):
                current_action = re.sub(r"^\[[^\]]+\]\s*", "", stripped)
                current_action = re.sub(r"^\[[^\]]+\]\s*", "", current_action)[:160]
            self.account_states.append_log(resolved_index, message, current_action=current_action)
            self.post_ui(lambda idx=int(resolved_index): [
                self.refresh_account_state_row(idx),
                self.render_log_view() if self.selected_log_account == idx else None,
            ])
            return

        with self.global_log_lock:
            self.global_logs.append(message)
            if len(self.global_logs) > 5000:
                del self.global_logs[:-4500]
        self.post_ui(lambda: self.render_log_view() if self.selected_log_account is None else None)


    async def take_error_snapshot(self, page, acc_name, reason):
        """
        Chụp ảnh màn hình toàn trang khi có lỗi để phục vụ quá trình debug.
        """
        try:
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", str(acc_name))
            file_name = f"{safe_name}_{reason}.png"
            
            # Lưu ảnh vào thư mục cấu hình qua output_path
            await page.screenshot(path=output_path(file_name), full_page=True)
            self.log(f"[DEBUG] Đã lưu screenshot: {file_name}")
            screenshots = sorted(
                (
                    os.path.join(APP_DATA_DIR, name)
                    for name in os.listdir(APP_DATA_DIR)
                    if name.lower().endswith(".png")
                ),
                key=os.path.getmtime,
            )
            for old_file in screenshots[:-100]:
                try:
                    os.remove(old_file)
                except OSError:
                    pass
            
        except Exception as e:
            self.log(f"[DEBUG] Screenshot lỗi: {e}")
    
    def open_import_dialog(self):
        ImportAccountDialog(self.root, self.add_accounts_to_table)

    def add_accounts_to_table(self, account_list):
        source_lines = [
            line.strip()
            for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        source_lines.extend(
            acc.get("raw", "").strip()
            for acc in account_list
            if acc.get("raw", "").strip()
        )

        self.txt_accounts.delete("1.0", "end")
        numbered_lines = [
            f"{index}. {re.sub(r'^\\d+[.\\-\\s]+', '', line)}"
            for index, line in enumerate(source_lines, start=1)
        ]
        if numbered_lines:
            self.txt_accounts.insert("1.0", "\n".join(numbered_lines) + "\n")
        self.reload_table_from_text()
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {len(self.tree.get_children())} nick")

    def delete_selected_rows(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn dòng cần xóa!")
            return

        selected_indexes = {
            int(self.tree.item(item, "values")[1])
            for item in selected
            if self.tree.item(item, "values")
            and str(self.tree.item(item, "values")[1]).isdigit()
        }
        source_lines = [
            line.strip()
            for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        remaining_lines = [
            line for index, line in enumerate(source_lines, start=1)
            if index not in selected_indexes
        ]

        self.txt_accounts.delete("1.0", "end")
        if remaining_lines:
            numbered_lines = [
                f"{index}. {re.sub(r'^\\d+[.\\-\\s]+', '', line)}"
                for index, line in enumerate(remaining_lines, start=1)
            ]
            self.txt_accounts.insert("1.0", "\n".join(numbered_lines) + "\n")

        self.reload_table_from_text()
        if hasattr(self, 'lbl_stat_total'):
            self.lbl_stat_total.config(text=str(len(self.tree.get_children())))
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {len(self.tree.get_children())} nick")

    
    # [BẮT ĐẦU THAY THẾ save_settings VÀ load_settings:]
    def save_settings(self):
        modes_saved = {k: v.get() for k, v in self.mode_vars.items()} if hasattr(self, 'mode_vars') else {}
        data = {
            "selected_theme": self.current_theme,
            "accounts": protect_setting(self.txt_accounts.get("1.0", "end").strip()),
            "proxies": protect_setting(self.txt_proxies.get("1.0", "end").strip()),
            "targets": self.txt_targets.get("1.0", "end").strip(),
            "selected_modes": modes_saved,
            "proxy_mode": self.proxy_mode.get(),
            "proxy_ratio": self.ent_proxy_ratio.get(),
            "threads": self.ent_threads.get(),
            "batch_size": self.ent_batch_size.get(),
            "headless": self.chk_headless.get(),
            "warmup": self.chk_warmup.get(),
            "cancel_old": self.chk_cancel_old.get(),
            "target": self.ent_target.get(),
            "page_target": self.ent_page_target.get() if hasattr(self, 'ent_page_target') else "5",
            "max_create_page_workers": self.ent_max_create_page_workers.get() if hasattr(self, 'ent_max_create_page_workers') else "3",
            "min_page_delay": self.ent_min_page_delay.get() if hasattr(self, 'ent_min_page_delay') else "60",
            "max_page_delay": self.ent_max_page_delay.get() if hasattr(self, 'ent_max_page_delay') else "120",
            "min_delay": self.ent_min_delay.get(),

            "feed_surf_min": self.ent_feed_surf_min.get() if hasattr(self, 'ent_feed_surf_min') else "10",
            "watch_review_min": self.ent_watch_review_min.get() if hasattr(self, 'ent_watch_review_min') else "5",
            "max_delay": self.ent_max_delay.get(),
            "browse_web": self.chk_browse_web.get(),
            "interact_page": self.chk_interact_page.get(),
            "check_notif": self.chk_check_notif.get(),
            "chat_react": self.chk_chat_react.get(),
            "tele_token": protect_setting(self.ent_tele_token.get().strip()),
            "tele_chatid": self.ent_tele_chatid.get().strip(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.log(f"[-] Không thể lưu settings: {e}")

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "selected_theme" in data and data["selected_theme"] in THEMES:
                self.cbo_theme.set(data["selected_theme"])
                self.apply_theme(data["selected_theme"])
            if "accounts" in data: self.txt_accounts.insert("1.0", unprotect_setting(data["accounts"]))
            if "proxies" in data: self.txt_proxies.insert("1.0", unprotect_setting(data["proxies"]))
            if "targets" in data: self.txt_targets.insert("1.0", data["targets"])
            if "selected_modes" in data and hasattr(self, 'mode_vars'):
                for k, val in data["selected_modes"].items():
                    if k in self.mode_vars:
                        self.mode_vars[k].set(val)
            if "proxy_mode" in data: self.proxy_mode.set(data["proxy_mode"])
            if "proxy_ratio" in data: self.ent_proxy_ratio.delete(0, "end"); self.ent_proxy_ratio.insert(0, data["proxy_ratio"])
            if "threads" in data: self.ent_threads.delete(0, "end"); self.ent_threads.insert(0, data["threads"])
            if "batch_size" in data: self.ent_batch_size.delete(0, "end"); self.ent_batch_size.insert(0, data["batch_size"])
            if "headless" in data: self.chk_headless.set(data["headless"])
            if "warmup" in data: self.chk_warmup.set(data["warmup"])
            if "cancel_old" in data: self.chk_cancel_old.set(data["cancel_old"])
            if "target" in data: self.ent_target.delete(0, "end"); self.ent_target.insert(0, data["target"])
            if "page_target" in data and hasattr(self, 'ent_page_target'):
                self.ent_page_target.delete(0, "end")
                self.ent_page_target.insert(0, data["page_target"])
            if "max_create_page_workers" in data and hasattr(self, 'ent_max_create_page_workers'):
                self.ent_max_create_page_workers.delete(0, "end")
                self.ent_max_create_page_workers.insert(0, data["max_create_page_workers"])

            if "min_page_delay" in data and hasattr(self, 'ent_min_page_delay'):
                self.ent_min_page_delay.delete(0, "end")
                self.ent_min_page_delay.insert(0, data["min_page_delay"])
            if "max_page_delay" in data and hasattr(self, 'ent_max_page_delay'):
                self.ent_max_page_delay.delete(0, "end")
                self.ent_max_page_delay.insert(0, data["max_page_delay"])
            if "feed_surf_min" in data and hasattr(self, 'ent_feed_surf_min'):
                self.ent_feed_surf_min.delete(0, "end"); self.ent_feed_surf_min.insert(0, data["feed_surf_min"])
            if "watch_review_min" in data and hasattr(self, 'ent_watch_review_min'):
                self.ent_watch_review_min.delete(0, "end"); self.ent_watch_review_min.insert(0, data["watch_review_min"])
            if "min_delay" in data: self.ent_min_delay.delete(0, "end"); self.ent_min_delay.insert(0, data["min_delay"])
            if "max_delay" in data: self.ent_max_delay.delete(0, "end"); self.ent_max_delay.insert(0, data["max_delay"])
            if "browse_web" in data: self.chk_browse_web.set(data["browse_web"])
            if "interact_page" in data: self.chk_interact_page.set(data["interact_page"])
            if "check_notif" in data: self.chk_check_notif.set(data["check_notif"])
            if "chat_react" in data: self.chk_chat_react.set(data["chat_react"])
            if "tele_token" in data: self.ent_tele_token.delete(0, "end"); self.ent_tele_token.insert(0, unprotect_setting(data["tele_token"]))
            if "tele_chatid" in data: self.ent_tele_chatid.delete(0, "end"); self.ent_tele_chatid.insert(0, data["tele_chatid"])
            
            self.reload_table_from_text()
        except Exception as e:
            self.log(f"[-] Không thể tải settings: {e}")
# [KẾT THÚC THAY THẾ]


    def on_close(self):
        if self.close_requested:
            return
        try:
            self.save_settings()
        except Exception:
            pass

        if self.is_running or (self.run_thread and self.run_thread.is_alive()):
            self.stop_bot()
            self.log("[!] Đang đóng trình duyệt và hoàn tất dữ liệu trước khi thoát...")
            deadline = time.monotonic() + 15

            def wait_for_worker():
                if self.run_thread and self.run_thread.is_alive() and time.monotonic() < deadline:
                    self.root.after(100, wait_for_worker)
                    return
                self.close_requested = True
                self.root.destroy()

            self.root.after(100, wait_for_worker)
            return

        self.close_requested = True
        self.root.destroy()

    def import_accounts_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text & CSV", "*.txt *.csv"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [re.sub(r'^\d+[\.\-\s]+', '', line.strip()) for line in f if line.strip() and not line.startswith("#")]
            
            # Tự động thêm STT 1. 2. 3... cho từng dòng nạp từ file
            numbered_lines = [f"{idx}. {line}" for idx, line in enumerate(lines, 1)]
            self.txt_accounts.delete("1.0", "end")
            self.txt_accounts.insert("1.0", "\n".join(numbered_lines) + "\n")
            self.reload_table_from_text()
            if hasattr(self, 'lbl_acc_count'):
                self.lbl_acc_count.config(text=f"Tổng: {len(lines)} nick")

    def import_proxies_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text & CSV", "*.txt *.csv"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                proxy_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

            self.txt_proxies.delete("1.0", "end")
            self.txt_proxies.insert("1.0", "\n".join(proxy_lines) + "\n")
            self.reload_table_from_text()

    def export_to_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Cảnh báo", "Bảng dữ liệu đang trống!")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV File", "*.csv")])
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["STT", "UID", "PASSWORD", "2FA", "STATUS", "ACTION", "TIME"])
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in items:
                    vals = list(self.tree.item(item, "values"))
                    writer.writerow([vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], now_str])
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo tại:\n{file_path}")
    def reload_table_from_text(self, checked_indexes=None):
        if getattr(self, "is_running", False):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        raw_acc_lines = [
            line for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        proxy_lines = [p.strip() for p in self.txt_proxies.get("1.0", "end").splitlines() if p.strip() and not p.startswith("#")]
        ratio = int(self.ent_proxy_ratio.get()) if self.ent_proxy_ratio.get().isdigit() else 20
        proxy_signature = (self.proxy_mode.get(), tuple(proxy_lines), ratio)
        if getattr(self, "_preview_proxy_signature", None) != proxy_signature:
            self._preview_proxy_assignments = {}
            self._preview_proxy_signature = proxy_signature
        account_records = []

        for idx, line in enumerate(raw_acc_lines, 1):
            parsed = parse_any_account_line(line, idx)
            if not parsed:
                continue
            account_record = dict(parsed)
            account_record.update({
                "stt": idx,
                "account_id": parsed["uid"] or parsed["name"] or f"Tài khoản {idx}",
                "country": parsed.get("country", ""),
                "locale": parsed.get("locale", "AUTO"),
                "timezone": parsed.get("timezone", ""),
                "proxy": "",
            })
            account_records.append(account_record)

            assigned_proxy = parsed["proxy"] or "Không dùng"
            if assigned_proxy == "Không dùng" and proxy_lines and self.proxy_mode.get() not in {"account", "rotating_api"}:
                if self.proxy_mode.get() == "random":
                    key = (idx, line)
                    if key not in self._preview_proxy_assignments:
                        self._preview_proxy_assignments[key] = random.choice(proxy_lines)
                    assigned_proxy = self._preview_proxy_assignments[key]
                elif self.proxy_mode.get() == "round_robin":
                    assigned_proxy = proxy_lines[(idx - 1) % len(proxy_lines)]
                else:
                    try:
                        ratio = max(1, int(self.ent_proxy_ratio.get().strip()))
                    except Exception:
                        ratio = 1

                    proxy_idx = (idx - 1) // ratio
                    assigned_proxy = proxy_lines[proxy_idx] if proxy_idx < len(proxy_lines) else proxy_lines[-1]

            account_records[-1]["proxy"] = "" if assigned_proxy == "Không dùng" else assigned_proxy

            self.tree.insert("", "end", iid=str(idx), values=(
                "[✔]" if checked_indexes is None or idx in checked_indexes else "[ ]",
                idx, 
                parsed["uid"], 
                parsed["password"], 
                parsed["2fa"], 
                "CHƯA KIỂM TRA",
                "Chưa chạy"
            ), tags=("UNKNOWN",))

        self.account_states.sync(account_records)
        for index in self.account_states.indexes():
            item_id = str(index)
            state = self.account_states.get(index)
            if self.tree.exists(item_id) and state:
                values = list(self.tree.item(item_id, "values"))
                values[5] = ACCOUNT_STATUS_LABELS[state["status"]]
                values[6] = state["current_action"]
                self.tree.item(item_id, values=values, tags=(state["status"],))
        self.refresh_account_state_table(reset_batch=True)
        
        if hasattr(self, 'lbl_stat_total'):
            self.lbl_stat_total.config(text=str(len(self.tree.get_children())))
        if hasattr(self, 'lbl_proxy_count'):
            valid_proxy_count = sum(1 for proxy in proxy_lines if parse_proxy(proxy))
            self.lbl_proxy_count.config(text=f"Tổng: {len(proxy_lines)} proxy • Hợp lệ: {valid_proxy_count}")
        if hasattr(self, "lbl_tree_empty"):
            if self.tree.get_children():
                self.lbl_tree_empty.place_forget()
            else:
                self.lbl_tree_empty.place(relx=0.5, rely=0.5, anchor="center")

    def start_thread(self):
        if self.run_thread and self.run_thread.is_alive():
            self.log("[!] Tiến trình trước vẫn đang dọn dẹp. Vui lòng thử lại sau 2 giây.")
            return

        self.is_running = True
        self.stop_requested = False
        self.run_error = None
        self.save_settings()
        checked_indexes = {
            int(self.tree.item(item, "values")[1])
            for item in self.tree.get_children()
            if str(self.tree.item(item, "values")[0]) == "[✔]"
            and str(self.tree.item(item, "values")[1]).isdigit()
        }
        self.reload_table_from_text(checked_indexes=checked_indexes)
        self.run_config = self.capture_run_config()
        if self.run_config.get("modes", {}).get("create_page", False):
            self.reset_create_page_account_results()
        try:
            requested_threads = int(self.ent_threads.get().strip())
        except ValueError:
            requested_threads = self.run_config["threads"]
        if requested_threads > 20:
            messagebox.showinfo(
                "Điều tiết hàng đợi",
                "Ứng dụng sẽ nhận toàn bộ danh sách tài khoản nhưng chỉ mở tối đa 20 trình duyệt đồng thời "
                "để tránh cạn RAM và nghẽn proxy.",
            )
        if self.run_config["threads"] > 12 and not self.run_config["headless"]:
            self.run_config["headless"] = True
            self.log("[i] Trên 12 trình duyệt: tự động bật chế độ chạy ẩn để giảm RAM và tránh tràn màn hình.")
        self.stop_requested = False
        self.run_error = None
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(text="● Đang chạy...", fg="#F59E0B")
        try:
            self.run_thread = threading.Thread(target=self.run_process, daemon=True)
            self.run_thread.start()
        except Exception as exc:
            self.run_error = f"Không khởi động được luồng: {type(exc).__name__}: {exc}"
            self.log(f"[ERROR] {self.run_error}")
            self.finish_run()

    def stop_bot(self):
        if not self.is_running and not (self.run_thread and self.run_thread.is_alive()):
            return
        self.is_running = False
        self.stop_requested = True
        self.log("[!] Đang gửi lệnh dừng đến tất cả các luồng...")
        def mark_stopping():
            self.btn_stop.config(state="disabled")
            if hasattr(self, 'lbl_status_indicator'):
                self.lbl_status_indicator.config(text="● Đang dừng...", fg="#F59E0B")
        self.post_ui(mark_stopping)
        loop = self.worker_loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._cancel_worker_tasks)

    def _cancel_worker_tasks(self):
        for task in list(self.worker_tasks):
            if not task.done():
                task.cancel()

    def finish_run(self):
        if self.run_thread and self.run_thread.is_alive():
            self.root.after(100, self.finish_run)
            return
        was_stopped = self.stop_requested
        self.is_running = False
        self.stop_requested = False
        self.run_thread = None
        self.worker_loop = None
        self.worker_tasks = []

        # Khôi phục trạng thái nút Bắt đầu để người dùng có thể chạy lại ngay
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(
                text=("● Lỗi (Sẵn sàng chạy lại)" if getattr(self, "run_error", None)
                      else "● Đã dừng (Sẵn sàng chạy lại)" if was_stopped else "● Hoàn thành"),
                fg=("#EF4444" if getattr(self, "run_error", None)
                    else "#F59E0B" if was_stopped else "#10B981"),
            )

    def run_process(self):
        """Khởi tạo vòng lặp sự kiện tương thích tuyệt đối với Windows và Playwright"""
        try:
            # Chạy trực tiếp worker chính, không gọi lại set_event_loop_policy để tránh xung đột luồng
            asyncio.run(self.main_worker())
        except asyncio.CancelledError:
            self.stop_requested = True
            self.log("[!] Luồng chính đã nhận lệnh dừng.")
        except Exception as e:
            self.run_error = f"{type(e).__name__}: {e}"
            self.log(f"[-] Lỗi hệ thống luồng chính [{type(e).__name__}]: {e}")
            if hasattr(self, "account_states"):
                for index in self.account_states.indexes():
                    self.finalize_active_account_tasks(index, "ERROR", self.run_error)
        finally:
            self.worker_loop = None
            self.worker_tasks = []
            self.post_ui(self.finish_run)


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
                    self.log(f"[✔] [{acc_name}] Đổi mật khẩu thành công.")
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
            # In thông tin chẩn đoán trạng thái trang thực tế
            self.log(f"[DEBUG] [{acc_name}] URL={page.url}")
            self.log(f"[DEBUG] [{acc_name}] Title={await page.title()}")
            self.log(f"[DEBUG] [{acc_name}] Inputs={await page.locator('input').count()}")
            self.log(f"[DEBUG] [{acc_name}] Textareas={await page.locator('textarea').count()}")
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
            secret_key = ""
            candidates = re.findall(r'(?<![A-Z2-7])(?:[A-Z2-7]{4}\s*){4,8}(?![A-Z2-7])', body_text.upper())
            for candidate in candidates:
                clean_candidate = re.sub(r"\s+", "", candidate)
                if not 16 <= len(clean_candidate) <= 32:
                    continue
                try:
                    padding = "=" * ((8 - len(clean_candidate) % 8) % 8)
                    base64.b32decode(clean_candidate + padding, casefold=True)
                    secret_key = clean_candidate
                    break
                except Exception:
                    continue

            if secret_key:
                code_input = page.locator(
                    'input[inputmode="numeric"], '
                    'input[autocomplete="one-time-code"], '
                    'input[aria-label*="mã"], '
                    'input[aria-label*="code"]'
                ).first
                if await code_input.count() == 0 or not await code_input.is_visible():
                    self.log(f"[-] [{acc_name}] Không tìm thấy ô nhập mã xác nhận 2FA.")
                    return 0

                await code_input.fill(generate_totp_code(secret_key))
                confirm_btn = page.locator(
                    'div[role="button"]:has-text("Tiếp"), '
                    'div[role="button"]:has-text("Continue"), '
                    'div[role="button"]:has-text("Xác nhận"), '
                    'div[role="button"]:has-text("Confirm"), '
                    'div[role="button"]:has-text("Bật"), '
                    'div[role="button"]:has-text("Turn on"), '
                    'button[type="submit"]'
                ).first
                if await confirm_btn.count() == 0 or not await confirm_btn.is_visible():
                    self.log(f"[-] [{acc_name}] Không tìm thấy nút xác nhận 2FA.")
                    return 0

                await confirm_btn.click()
                await asyncio.sleep(5)
                result_text = (await page.inner_text("body")).lower()
                success_markers = (
                    "đã bật xác thực hai yếu tố",
                    "two-factor authentication is on",
                    "two-factor authentication is enabled",
                    "xác thực hai yếu tố đã bật",
                )
                if not any(marker in result_text for marker in success_markers):
                    self.log(f"[-] [{acc_name}] Chưa xác nhận được 2FA đã bật.")
                    return 0

                with open(output_path("2fa_keys_saved.txt"), "a", encoding="utf-8") as f:
                    f.write(f"{acc_name}|{secret_key}\n")
                self.log(f"[✔] [{acc_name}] Bật 2FA và lưu Secret Key thành công.")
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
        await self.guard_facebook_checkpoint(page, idx)
        """Tự động cấp quyền Quản trị viên / Biên tập viên cho Fanpage Profile"""
        def finish(status, reason):
            result = build_page_access_result(
                acc_name, page_url, target_uid_or_name, status, reason
            )
            save_page_access_result(result)
            self.set_account_state(
                idx,
                current_action=f"Page Access [{result['assignment_status']}]: {reason}",
            )
            self.log(
                f"[PAGE_ACCESS][{result['assignment_status']}] [{acc_name}] "
                f"page_id={result['page_id'] or 'N/A'} target={target_uid_or_name} | {reason}"
            )
            return result

        if not page_url or not target_uid_or_name:
            return finish("FAILED", "Thiếu Link Page hoặc UID/Tên cần thêm quyền.")
        self.log(f"[PAGE_ACCESS][START] [{acc_name}] page={page_url} target={target_uid_or_name}")
        try:
            settings_url = page_url.rstrip('/') + "/settings/?tab=profile_access"
            await page.goto(settings_url, wait_until="domcontentloaded", timeout=40000)
            await self.guard_facebook_checkpoint(page, idx)
            await asyncio.sleep(4)
            if not page_reference_matches(page_url, page.url):
                return finish(
                    "FAILED",
                    "Trang cài đặt không khớp Page được giao; đã dừng để tránh ghép nhầm.",
                )

            # Bấm Thêm người mới (Add new)
            add_btn = page.locator(
                'div[role="main"] button[data-testid*="profile_access" i][data-testid*="add" i], '
                'div[role="main"] [role="button"][data-action*="profile_access" i][data-action*="add" i]'
            ).first
            if await add_btn.count() == 0:
                add_btn = page.get_by_role(
                    "button", name=ADD_PAGE_ADMIN_BUTTON_PATTERN
                ).first
            if await add_btn.count() > 0 and await add_btn.is_visible():
                await add_btn.click()
                await asyncio.sleep(2)
                
                next_btn = page.locator(
                    'div[role="dialog"] button[type="submit"]:visible'
                ).first
                if await next_btn.count() == 0:
                    next_btn = page.get_by_role("button", name=NEXT_BUTTON_PATTERN).first
                if await next_btn.count() > 0: await next_btn.click()
                await asyncio.sleep(2)

                # Tìm và chọn UID/Tên cần phân quyền
                search_input = page.locator(
                    'div[role="dialog"] input[type="search"], '
                    'div[role="dialog"] input[role="combobox"], '
                    'div[role="dialog"] input[type="text"]'
                ).first
                if await search_input.count() > 0:
                    await search_input.fill(target_uid_or_name)
                    await asyncio.sleep(3)
                    
                    user_res = page.locator('div[role="listbox"] div[role="option"]').first
                    if await user_res.count() == 0:
                        user_res = page.get_by_text(target_uid_or_name, exact=True).first
                    target_verified = (
                        await user_res.count() > 0
                        and await locator_matches_account_target(user_res, target_uid_or_name)
                    )
                    if target_verified:
                        await user_res.click()
                        await asyncio.sleep(2)

                        give_access = page.locator(
                            'div[role="dialog"] button[type="submit"]:visible'
                        ).first
                        if await give_access.count() == 0:
                            give_access = page.get_by_role(
                                "button", name=GIVE_ACCESS_BUTTON_PATTERN
                            ).first
                        if await give_access.count() > 0:
                            await give_access.click()
                            await self.guard_facebook_checkpoint(page, idx)
                            await asyncio.sleep(3)
                            password_prompt = page.locator('input[type="password"]:visible')
                            if await password_prompt.count() > 0:
                                return finish(
                                    "PENDING",
                                    "Facebook yêu cầu xác nhận mật khẩu; chưa xác minh cấp quyền.",
                                )

                            action_completed = False
                            try:
                                action_completed = (
                                    await give_access.count() == 0
                                    or not await give_access.is_visible()
                                )
                            except Exception:
                                action_completed = False

                            if str(target_uid_or_name).isdigit():
                                escaped_target = re.escape(str(target_uid_or_name))
                                target_evidence = page.locator(
                                    f'a[href*="id={escaped_target}"], '
                                    f'a[href*="/{escaped_target}"]'
                                ).first
                            else:
                                target_evidence = page.get_by_text(
                                    target_uid_or_name, exact=True
                                ).first
                            target_still_verified = (
                                await target_evidence.count() > 0
                                and await locator_matches_account_target(
                                    target_evidence, target_uid_or_name
                                )
                            )
                            page_still_matches = page_reference_matches(page_url, page.url)
                            result_text = ""
                            feedback = page.locator('[role="alert"], [role="status"], [role="dialog"]')
                            if await feedback.count() > 0:
                                try:
                                    result_text = (await feedback.last.inner_text(timeout=1500)).casefold()
                                except Exception:
                                    result_text = ""
                            assignment_status = classify_page_access_feedback(result_text)
                            await self.guard_facebook_checkpoint(page, idx)
                            confirmed = bool(
                                page_still_matches
                                and target_still_verified
                                and assignment_status in {"ASSIGNED", "INVITED", "PENDING"}
                            )
                            if confirmed:
                                return finish(
                                    assignment_status,
                                    "Đã xác minh đúng Page, đúng target và trạng thái phản hồi.",
                                )
                            return finish(
                                "FAILED",
                                "Đã click cấp quyền nhưng chưa xác minh được Page/target/trạng thái.",
                            )
                    else:
                        return finish(
                            "FAILED",
                            f"Kết quả tìm kiếm không khớp target '{target_uid_or_name}'.",
                        )
            return finish("FAILED", "Không tìm thấy mục quản lý quyền Page.")
        except Exception as e:
            return finish("ERROR", f"{type(e).__name__}: {e}")

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

                image_attached = False
                # Đính kèm ảnh nếu người dùng đã cung cấp đường dẫn
                if image_path:
                    if not os.path.isfile(image_path):
                        self.log(f"[-] [{acc_name}] File ảnh không tồn tại: {image_path}")
                        return 0
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    if await file_input.count() == 0:
                        self.log(f"[-] [{acc_name}] Không tìm thấy ô tải ảnh lên.")
                        return 0
                    await file_input.set_input_files(image_path)
                    image_attached = True
                    await asyncio.sleep(4)

                await page.keyboard.press("Enter")
                await asyncio.sleep(4)
                result_label = "kèm ảnh" if image_attached else ""
                self.log(f"[✔] [{acc_name}] Đã bình luận {result_label} thành công!".replace("  ", " "))
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
                with open(output_path("group_members_scraped.txt"), "a", encoding="utf-8") as f:
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
                    with open(output_path("contacts_scraped.txt"), "a", encoding="utf-8") as f:
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
        fb_pwd = self.run_config.get("reg_pass", "").strip() or "FbAuto@2026Secure"
        
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
            try:
                await re_email.wait_for(state="visible", timeout=4000)
                await re_email.fill(email)
            except Exception:
                pass # Bỏ qua nếu giao diện IP đó không yêu cầu xác nhận

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
                
                with open(output_path("reg_facebook_success.txt"), "a", encoding="utf-8") as f:
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
        pwd = self.run_config.get("reg_pass", "").strip() or "TikTok@2026Secure"
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
                    with open(output_path("reg_tiktok_pending.txt"), "a", encoding="utf-8") as f:
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
        pwd = self.run_config.get("reg_pass", "").strip() or "Insta@2026Secure"
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
                    with open(output_path("reg_instagram_success.txt"), "a", encoding="utf-8") as f:
                        f.write(f"{uname}|{email}|{pwd}|{proxy_str}\n")
                    self.log(f"[✔] [{acc_name}] Tạo Instagram thành công: {uname}")
                    return 1
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi Reg Instagram: {e}")
        return 0
# [KẾT THÚC DÁN HÀM REG]


    async def login_facebook_user_pass(self, page, context, username, password):
        """Đăng nhập Facebook bằng tài khoản và mật khẩu đã được parse."""
        if not username or not password:
            return LOGIN_TECHNICAL_ERROR, "Thiếu tài khoản hoặc mật khẩu"

        self.log(f"[*] Đang đăng nhập Facebook cho tài khoản: {username}...")
        try:
            await page.goto("https://www.facebook.com/login/", wait_until="domcontentloaded", timeout=40000)
            await page.locator('input[name="email"]').fill(username)
            await page.locator('input[name="pass"]').fill(password)

            login_btn = page.locator('button[name="login"], button[type="submit"]').first
            if await login_btn.count() == 0:
                self.log(f"[-] [{username}] Không tìm thấy nút đăng nhập Facebook.")
                return LOGIN_TECHNICAL_ERROR, "Không tìm thấy nút đăng nhập Facebook"

            await login_btn.click()
            await page.wait_for_timeout(5000)
            
            if "checkpoint" in page.url or "two_factor" in page.url or "id=1501092823525282" in page.url:
                state = self.account_states.get(int(self.account_log_context.get())) if getattr(self, 'account_log_context', None) else None
                fa2 = state.get("2fa", "") if state else ""
                if not fa2:
                    return LOGIN_INVALID, "Cần mã 2FA nhưng không có trong dữ liệu"
                self.log(f"[*] [{username}] Đang giải mã 2FA...")
                code_input = page.locator('input[id="approvals_code"], input[name="approvals_code"]').first
                if await code_input.count() > 0:
                    await code_input.fill(generate_totp_code(fa2))
                    submit_2fa = page.locator('button[id="checkpointSubmitButton"]').first
                    if await submit_2fa.count() > 0:
                        await submit_2fa.click()
                        await page.wait_for_timeout(5000)
                        for _ in range(4):
                            cont_btn = page.locator('button[id="checkpointSubmitButton"]').first
                            if await cont_btn.count() > 0 and await cont_btn.is_visible():
                                await cont_btn.click()
                                await page.wait_for_timeout(3000)

            is_valid_session, session_detail = await self.verify_facebook_session(page, context)
            if not is_valid_session:
                self.log(f"[-] [{username}] Đăng nhập Facebook chưa hợp lệ: {session_detail}.")
                return LOGIN_INVALID, session_detail

            self.log(f"[✔] [{username}] {session_detail}.")
            return LOGIN_SUCCESS, session_detail
        except Exception as e:
            self.log(f"[-] [{username}] Lỗi đăng nhập Facebook: {e}")
            return LOGIN_TECHNICAL_ERROR, f"{type(e).__name__}: {e}"

    async def login_tiktok_user_pass(self, page, username, password):
        """Tự động đăng nhập TikTok bằng Username/Email và Password"""
        self.log(f"[*] Đang đăng nhập TikTok cho tài khoản: {username}...")
        try:
            await page.goto("https://www.tiktok.com/login/phone-or-email/email", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            # Điền tài khoản/email
            user_input = page.locator('input[name="username"], input[placeholder*="Email hoặc TikTok ID"], input[placeholder*="Email or username"]').first
            pass_input = page.locator('input[type="password"]').first

            if await user_input.count() > 0 and await pass_input.count() > 0:
                await user_input.fill(username)
                await asyncio.sleep(1)
                await pass_input.fill(password)
                await asyncio.sleep(1)

                login_btn = page.locator('button[type="submit"], button:has-text("Đăng nhập"), button:has-text("Log in")').first
                if await login_btn.count() > 0:
                    await login_btn.click()
                    await asyncio.sleep(6)

                    # Kiểm tra xem có dính Captcha kéo trượt hình không
                    captcha_box = page.locator('div[class*="captcha"], div[id*="captcha"]')
                    if await captcha_box.count() > 0 and await captcha_box.is_visible():
                        self.log(f"[!] [{username}] Xuất hiện Captcha kéo hình, vui lòng kéo thủ công hoặc đợi giải mã...")
                        await asyncio.sleep(10)

                    self.log(f"[✔] [{username}] Đăng nhập TikTok hoàn tất!")
                    return True
            else:
                self.log(f"[-] [{username}] Không tìm thấy khung điền tài khoản/mật khẩu TikTok.")
        except Exception as e:
            self.log(f"[-] [{username}] Lỗi đăng nhập TikTok: {e}")
        return False
    
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

    async def warm_up_feed(self, page, acc_name):
        """Lướt Newfeed kết hợp Health Check, Soft Timeout và Telemetry Metrics"""
        session_start = time.monotonic()
        stats = {"scrolls": 0, "likes": 0, "errors": 0, "stuck_count": 0}
        
        try:
            scroll_cycles = random.randint(6, 10)
            self.log(f"[*] [{acc_name}] Khởi động ngâm Feed ({scroll_cycles} chu kỳ)...")
            
            for step in range(scroll_cycles):
                cycle_start = time.monotonic()
                
                # 1. Health Check & Soft Timeout (Giới hạn tối đa ngâm 5 phút = 300s)
                if not self.is_running or page.is_closed(): break
                if (time.monotonic() - session_start) > 300:
                    self.log(f"[WARN] [{acc_name}] Ngâm Feed vượt quá 5 phút. Buộc kết thúc để chạy việc khác.")
                    break

                # 2. Ghi nhận vị trí cũ để check stuck
                old_y = await page.evaluate("window.scrollY")
                
                # 3. Lăn chuột phần cứng
                scroll_distance = random.randint(450, 800)
                chunks = random.randint(5, 10)
                for _ in range(chunks):
                    await page.mouse.wheel(0, scroll_distance // chunks)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                stats["scrolls"] += 1
                
                # 4. Kiểm tra có bị kẹt (không cuộn được nữa) không
                await asyncio.sleep(random.uniform(1.0, 2.0))
                new_y = await page.evaluate("window.scrollY")
                if old_y == new_y:
                    stats["stuck_count"] += 1
                    if stats["stuck_count"] >= 3:
                        self.log(f"[DEBUG] [{acc_name}] Feed không thể cuộn thêm (chạm đáy hoặc popup chắn). Kết thúc lướt.")
                        break
                else:
                    stats["stuck_count"] = 0 # Reset nếu vẫn cuộn được

                # Dừng đọc bài
                await asyncio.sleep(random.randint(4, 10))

                # 5. Tương tác Thích an toàn qua Helper (Tỷ lệ 35%)
                if random.random() < 0.35:
                    like_selector = 'div[role="button"][aria-label*="thích" i], div[role="button"][aria-label*="like" i]'
                    success = await self.safe_action_click(page, like_selector, acc_name, action_name="Thích bài viết")
                    if success:
                        stats["likes"] += 1
                        await asyncio.sleep(random.randint(3, 5))

                elapsed = time.monotonic() - cycle_start
                self.log(f"[DEBUG] [{acc_name}] Cycle {step+1}/{scroll_cycles} xong trong {elapsed:.2f}s (Cuộn {scroll_distance}px).")

        except Exception as e:
            stats["errors"] += 1
            self.log(f"[-] [{acc_name}] Lỗi lướt feed: {e}")
            await self.take_error_snapshot(page, acc_name, "warm_up_feed")
        
        # Thống kê cuối phiên
        self.log(f"[SUMMARY] [{acc_name}] Ngâm Feed hoàn tất: Cuộn={stats['scrolls']} lần, Thích={stats['likes']} bài, Lỗi={stats['errors']}.")

    async def create_browser_page(
        self,
        playwright_instance,
        idx,
        proxy_cfg=None,
        is_headless=False,
        account_locale="AUTO",
        account_timezone="",
    ):
        """
        Khởi tạo Browser + Context + Page.
        Tính năng: Tự động chia khung Grid, Retry khởi tạo, Health check.
        """
        import math  # Gọi luôn ở đây để không sợ thiếu thư viện ở đầu file
   
        # ==================================================
        # TÍNH TOÁN LƯỚI THÔNG MINH THEO SỐ LƯỢNG LUỒNG & ĐỘ PHÂN GIẢI
        # ==================================================
        config = self.run_config
        t_count = config.get("threads", 3)
        screen_w = config.get("screen_width", 1920)
        screen_h = config.get("screen_height", 1080)

        # Tự động phân chia lưới dựa vào số lượng luồng thực tế đang chạy
        if t_count <= 4:
            cols, rows = 2, 2  # Lưới 2x2 (4 cửa sổ)
        elif t_count <= 8:
            cols, rows = 4, 2  # Lưới 4x2 (8 cửa sổ)
        else:
            cols, rows = 4, 4  # Lưới 4x4 (16 cửa sổ)

                # ==================================================
        # ÉP KÍCH THƯỚC CỬA SỔ NHỎ GỌN CỐ ĐỊNH (VD: Rộng 450, Cao 750)
        # ==================================================
        win_w = 450  # Chiều rộng cửa sổ nhỏ gọn
        win_h = 450  # Chiều cao cửa sổ nhỏ gọn

        cols = max(1, screen_w // win_w)  # Tự động xếp thành nhiều cột nếu mở nhiều luồng

        slot = (idx - 1) % t_count
        pos_x = (slot % cols) * win_w
        pos_y = (slot // cols) * win_h

        # ==================================================
        # 2. CHUẨN BỊ THAM SỐ LAUNCH & ẨN DANH
        # ==================================================
        browser_exe = get_installed_browser_path()
        locale_options = browser_locale_options(account_locale)
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-popup-blocking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--no-default-browser-check",
            "--no-first-run",
            "--enable-translate",
            f"--window-position={pos_x},{pos_y}",
            f"--window-size={win_w},{win_h}",
        ]
        if locale_options["lang_arg"]:
            launch_args.append(f"--lang={locale_options['lang_arg']}")

        launch_kwargs = {
            "headless": is_headless,
            "args": launch_args,
        }
        if proxy_cfg: launch_kwargs["proxy"] = proxy_cfg
        if browser_exe: launch_kwargs["executable_path"] = browser_exe

        # ==================================================
        # 3. LAUNCH RETRY & HEALTH CHECK
        # ==================================================
        browser = None
        for attempt in range(1, 4):
            try:
                browser = await playwright_instance.chromium.launch(**launch_kwargs)
                break
            except Exception as e:
                self.log(f"[!] Lỗi khởi tạo Chrome lần {attempt}: {e}")
                await asyncio.sleep(2)

        if not browser:
            raise RuntimeError("Thất bại hoàn toàn khi mở trình duyệt Chromium.")

        try:
            # Dùng no_viewport=True để Facebook nhận diện đây là cửa sổ thật
            context_options = {"no_viewport": True, "ignore_https_errors": False}
            if locale_options["locale"]:
                context_options["locale"] = locale_options["locale"]
                context_options["extra_http_headers"] = {
                    "Accept-Language": locale_options["accept_language"]
                }
            normalized_timezone = normalize_account_timezone(account_timezone)
            if normalized_timezone:
                context_options["timezone_id"] = normalized_timezone
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                delete navigator.__proto__.webdriver;
                window.chrome = {
                    app: { isInstalled: false },
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)

            # Test a real HTTPS route so a dead/auth-failed proxy cannot pass on about:blank.
            health_response = await page.goto(
                "https://www.facebook.com/robots.txt",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            if health_response is None:
                raise RuntimeError("Không nhận được phản hồi HTTPS từ Facebook")
            if health_response.status == 407 or health_response.status >= 500:
                raise RuntimeError(f"Proxy trả về HTTP {health_response.status}")

        except Exception as e:
            try: await context.close()
            except: pass
            try: await browser.close()
            except: pass
            raise RuntimeError(f"Trình duyệt mở được nhưng Page không phản hồi (Khả năng do Proxy): {e}")

        self.log(f"[*] Đã mở Slot {slot} (Luồng {idx}) tại Tọa độ: {pos_x}x{pos_y}")
        return browser, context, page

    async def wait_between_page_jobs(self, page, context, acc_name, index, min_delay, max_delay):
        """Browse without reactions during the one configured inter-Page delay."""
        if not self.is_running or getattr(self, "stop_requested", False):
            return False
        lower, upper = sorted((max(0, int(min_delay)), max(0, int(max_delay))))
        delay = random.randint(lower, upper)
        deadline = time.monotonic() + delay
        next_page_at = (datetime.now() + timedelta(seconds=delay)).isoformat(timespec="seconds")
        timer = None

        def update_countdown():
            remaining = max(0, math.ceil(deadline - time.monotonic()))
            self.account_states.set_page_wait(index, remaining, next_page_at)
            self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))

        async def countdown():
            while self.is_running and not getattr(self, "stop_requested", False):
                update_countdown()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return
                await asyncio.sleep(min(1, remaining))

        try:
            update_countdown()
            self.record_task_result(index, "CREATE_PAGE", "RUNNING", "Chờ Page tiếp", preserve_outcomes=True)
            self.log(f"[PAGE][WAIT] [{acc_name}] Delay {delay}s; Page tiếp lúc {next_page_at[11:19]}.")
            timer = asyncio.create_task(countdown())
            if not await self.ensure_personal_profile(context, page, acc_name):
                raise RuntimeError("Không xác minh được danh tính cá nhân trước khi chờ Page tiếp")
            if not self.is_running or getattr(self, "stop_requested", False):
                self.finalize_active_account_tasks(index, "SKIPPED", "Đã dừng theo yêu cầu")
                return False
            remaining = deadline - time.monotonic()
            if remaining > 0:
                self.set_account_state(index, current_action="Đang lướt Feed; chờ Page tiếp")
                await asyncio.wait_for(
                    page.goto("https://www.facebook.com/", wait_until="domcontentloaded",
                              timeout=max(1, int(min(15, remaining) * 1000))),
                    timeout=remaining,
                )
            while self.is_running and not getattr(self, "stop_requested", False):
                await self.guard_facebook_checkpoint(page, index)
                is_closed = getattr(page, "is_closed", None)
                if callable(is_closed) and is_closed() is True:
                    raise RuntimeError("Profile đã được đóng trong lúc chờ Page tiếp")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True
                await asyncio.wait_for(page.mouse.wheel(0, 500), timeout=min(15, remaining))
                await asyncio.sleep(min(5, max(0, deadline - time.monotonic())))
            self.finalize_active_account_tasks(index, "SKIPPED", "Đã dừng theo yêu cầu")
            return False
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            reason = f"Lỗi chờ Page tiếp: {type(exc).__name__}: {exc}"
            self.set_account_failure(index, "automation", reason)
            self.finalize_active_account_tasks(index, "ERROR", reason)
            return False
        finally:
            if timer is not None:
                timer.cancel()
                await asyncio.gather(timer, return_exceptions=True)
            self.account_states.set_page_wait(index)
            self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))

    async def human_surf_feed(self, page, acc_name, duration_minutes=10):
        """Lướt Bảng tin như người thật trong khoảng thời gian chỉ định"""
        self.log(f"[*] [{acc_name}] Bắt đầu lướt Newfeed trong {duration_minutes} phút...")
        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(4)
        except Exception:
            pass

        end_time = time.monotonic() + (duration_minutes * 60)
        while time.monotonic() < end_time and self.is_running:
            if page.is_closed(): break
            
            # 1. TỶ LỆ 20% CUỘN NGƯỢC LÊN (Đọc lại bài vừa trôi qua)
            if random.random() < 0.20:
                up_dist = random.randint(150, 300)
                up_steps = random.randint(8, 14)
                for _ in range(up_steps):
                    await page.mouse.wheel(0, -(up_dist // up_steps))
                    await asyncio.sleep(random.uniform(0.015, 0.03))
                await asyncio.sleep(random.uniform(2.0, 4.0))

            # 2. CUỘN XUỐNG MƯỢT CÓ QUÁN TÍNH
            scroll_dist = random.randint(350, 650)
            steps = random.randint(14, 24)
            for _ in range(steps):
                await page.mouse.wheel(0, scroll_dist // steps)
                await asyncio.sleep(random.uniform(0.015, 0.035))

            # 3. DỪNG ĐỌC BÀI TỰ NHIÊN
            read_time = random.uniform(6.0, 12.0) if random.random() < 0.3 else random.uniform(1.5, 3.5)
            await asyncio.sleep(read_time)

            # 4. TỶ LỆ 10% TƯƠNG TÁC THẢ LIKE
            if random.random() < 0.10:
                like_btn = page.locator('div[role="button"][aria-label*="thích" i], div[role="button"][aria-label*="like" i]').first
                if await like_btn.count() > 0 and await like_btn.is_visible():
                    try:
                        await like_btn.click(timeout=2000)
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                    except Exception:
                        pass

    async def human_watch_movie_reviews(self, page, acc_name, duration_minutes=5):
        """Mở Facebook Watch tìm và xem Review Phim trong khoảng thời gian chỉ định"""
        self.log(f"[*] [{acc_name}] Bắt đầu xem Video Review Phim trong {duration_minutes} phút...")
        search_url = "https://www.facebook.com/watch/search/?q=review%20phim"
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(5)
            video_card = page.locator('div[role="article"] a, a[href*="/watch/"], a[href*="/videos/"]').first
            if await video_card.count() > 0:
                await video_card.click()
                await asyncio.sleep(4)
        except Exception as e:
            self.log(f"[DEBUG] [{acc_name}] Lỗi nạp Watch Review Phim: {e}")

        end_time = time.monotonic() + (duration_minutes * 60)
        while time.monotonic() < end_time and self.is_running:
            if page.is_closed(): break
            stay_time = random.randint(30, 60)
            await asyncio.sleep(stay_time)
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(3)
    async def browse_external_web(self, page, acc_name):
        """Lướt báo/web ngoài tạo lịch sử tự nhiên"""
        try:
            self.log(f"[*] [{acc_name}] Lướt báo đọc tin tức 15s...")
            await page.goto("https://vnexpress.net/", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(5)
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(5)
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi lướt web ngoài: {e}")

    async def watch_facebook_reels(self, page, acc_name, count=5):
        """Xem và lướt Video Reels Facebook tự động như người thật"""
        try:
            self.log(f"[*] [{acc_name}] Bắt đầu lướt xem {count} video Reels...")
            await page.goto("https://www.facebook.com/reel", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(3.0, 5.0))

            for r_idx in range(count):
                if not self.is_running or page.is_closed():
                    break

                # Xem video từ 7 đến 16 giây
                watch_time = random.randint(7, 16)
                self.log(f"[*] [{acc_name}] Đang xem Reel {r_idx + 1}/{count} ({watch_time}s)...")
                await asyncio.sleep(watch_time)

                # Tỷ lệ 15% thả tim video
                if random.random() < 0.15:
                    like_btn = page.locator('div[aria-label*="Thích" i], div[aria-label*="Like" i]').first
                    if await like_btn.count() > 0 and await like_btn.is_visible():
                        try:
                            await like_btn.click(timeout=2000)
                            await asyncio.sleep(1)
                        except Exception:
                            pass

                # Chuyển Reel kế tiếp bằng phím mũi tên xuống kết hợp lăn chuột
                await page.keyboard.press("ArrowDown")
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(random.uniform(1.5, 3.0))

            self.log(f"[✔] [{acc_name}] Đã xem xong các video Reels.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi xem Reels: {e}")

    async def view_facebook_stories(self, page, acc_name):
        """Xem Story Facebook bạn bè"""
        try:
            self.log(f"[*] [{acc_name}] Xem Story bạn bè...")
            await page.goto("https://www.facebook.com/stories", wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(random.randint(5, 10))
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi xem Story: {e}")

    async def check_notifications(self, page, acc_name):
        """Mở xem thông báo"""
        try:
            self.log(f"[*] [{acc_name}] Kiểm tra bảng tin thông báo...")
            notif_btn = page.locator('div[aria-label*="Thông báo"], div[aria-label*="Notifications"]').first
            if await notif_btn.count() > 0:
                await notif_btn.click()
                await asyncio.sleep(3)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi kiểm tra thông báo: {e}")

    async def react_messenger(self, page, acc_name):
        """Thả cảm xúc Messenger"""
        try:
            self.log(f"[*] [{acc_name}] Kiểm tra tin nhắn Messenger...")
            msg_btn = page.locator('div[aria-label*="Messenger"]').first
            if await msg_btn.count() > 0:
                await msg_btn.click()
                await asyncio.sleep(3)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi mở Messenger: {e}")

    async def interact_fanpage(self, page, acc_name):
        """Tương tác Fanpage"""
        try:
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(2)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi tương tác Fanpage: {e}")

    async def cancel_old_requests(self, page, acc_name):
        """Hủy các lời mời kết bạn gửi đi đã quá lâu"""
        try:
            self.log(f"[*] [{acc_name}] Đang kiểm tra lời mời kết bạn cũ...")
            await page.goto("https://www.facebook.com/friends/requests", wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi kiểm tra lời mời cũ: {e}")

    async def get_current_friends_count(self, page):
        """Lấy số lượng bạn bè hiện tại"""
        try:
            await page.goto("https://www.facebook.com/me/friends", wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
            body_text = await page.inner_text("body")
            m = re.search(r'(\d+[\d\.,]*)\s+người bạn', body_text)
            if m:
                return m.group(1)
        except Exception as e:
            self.log(f"[-] Không thể lấy số lượng bạn bè: {e}")
        return "Chưa rõ"

    async def run_add_by_name(
        self,
        page,
        acc_name,
        idx,
        targets=None,
        target_total=25,
        min_del=15,
        max_del=35,
    ):
        """
        Tìm người theo tên/từ khóa rồi gửi lời mời kết bạn.
        Logic:
        - Luôn click nút Add Friend đầu tiên còn tồn tại (.first).
        - Sau mỗi click lấy lại locator mới.
        - Khi hết nút Add Friend thì scroll xuống nạp thêm.
        - Scroll quá 5 lần không có dữ liệu => chuyển từ khóa khác.
        """
        search_names = (
            [x.strip() for x in targets if x.strip()]
            if targets and any(x.strip() for x in targets)
            else SEARCH_KEYWORDS
        )

        sent = 0

        for keyword in search_names:
            if not self.is_running or sent >= target_total:
                break

            keyword = keyword.strip()
            if not keyword:
                continue

            search_url = f"https://www.facebook.com/search/people/?q={quote(keyword)}"
            self.log(f"[*] [{acc_name}] Đang tìm kiếm: '{keyword}'")

            try:
                await page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=35000,
                )
                await asyncio.sleep(random.uniform(3, 5))

                # Số lần liên tiếp scroll nhưng không có dữ liệu mới
                no_new_data_count = 0

                while self.is_running and sent < target_total:
                    try:
                        btns = page.locator(ADD_FRIEND_SELECTORS)
                        btn_count = await btns.count()
                    except Exception as exc:
                        self.record_task_result(idx, "FRIEND_REQUEST", "ERROR", str(exc))
                        btn_count = 0

                    # =====================================
                    # CÒN NÚT ADD FRIEND
                    # =====================================
                    if btn_count > 0:
                        try:
                            btn = btns.first
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            outcome = await self.click_and_confirm_friend_request(page, btn)
                            self.record_friend_outcome(idx, outcome)
                            confirmed, detail = outcome
                            if confirmed:
                                sent += 1
                                no_new_data_count = 0
                                self.log(
                                    f"[✔] [{acc_name}] Đã xác nhận gửi {sent}/{target_total} (Từ khóa: {keyword})"
                                )
                                await asyncio.sleep(random.randint(min_del, max_del))
                            else:
                                self.log(f"[!] [{acc_name}] Không tính lượt kết bạn: {detail}")
                                no_new_data_count += 1
                                await page.evaluate("window.scrollBy(0, 350)")
                                await asyncio.sleep(2)
                                if no_new_data_count > 5:
                                    self.log(
                                        f"[-] [{acc_name}] Không thể xác nhận thêm lời mời cho '{keyword}'."
                                    )
                                    break

                        except Exception as click_err:
                            self.record_task_result(idx, "FRIEND_REQUEST", "ERROR", str(click_err))
                            self.log(f"[!] [{acc_name}] Nút bị che hoặc lỗi: {click_err}")
                            # Cuộn nhẹ để nút lỗi trôi qua
                            await page.evaluate("window.scrollBy(0, 350)")
                            await asyncio.sleep(2)

                    # =====================================
                    # HẾT NÚT HOẶC MÀN HÌNH CHƯA TẢI KỊP
                    # =====================================
                    else:
                        no_new_data_count += 1
                        if no_new_data_count > 5:
                            self.log(f"[-] [{acc_name}] Không còn kết quả mới cho '{keyword}'. Chuyển từ khóa.")
                            break

                        self.log(f"[*] [{acc_name}] Đang cuộn màn hình nạp thêm bạn bè...")
                        await page.evaluate("window.scrollBy(0, 800)")
                        await asyncio.sleep(random.uniform(2.5, 4.0))

            except Exception as e:
                self.log(f"[-] [{acc_name}] Lỗi khi tìm '{keyword}': {e}")
                self.record_task_result(idx, "FRIEND_REQUEST", "ERROR", str(e))

        self.log(f"[FRIEND][SUMMARY] [{acc_name}] Lời mời đã xác minh: {sent}")
        return sent

    async def click_and_confirm_friend_request(self, page, button, target=None):
        """Bind evidence to the recipient's action group, never the whole page."""
        await self.guard_facebook_checkpoint(page)
        expected = friend_profile_reference(target) if target else ""
        handle = None
        try:
            handle = await button.evaluate_handle(r"""button => {
                let root = button.closest('[role="row"], [role="listitem"]');
                if (root) return root;
                root = button.parentElement;
                for (let i = 0; root && i < 5; i++, root = root.parentElement) {
                    if (root.querySelector('a[href]')) return root;
                }
                return button.parentElement;
            }""")
            scope = handle.as_element()
            if scope is None:
                return FriendRequestOutcome("FAILED", expected, "Không xác định được vùng thao tác của người nhận.")
            before = await scope.evaluate(FRIEND_SCOPE_SNAPSHOT)
            references = {ref for link in before["links"] if (ref := friend_profile_reference(link))}
            current_profile = friend_profile_reference(page.url)
            if expected:
                if current_profile != expected or (references and references != {expected}):
                    return FriendRequestOutcome("FAILED", expected, "Profile/UID không khớp người nhận.")
            elif len(references) == 1:
                expected = next(iter(references))
            else:
                return FriendRequestOutcome("FAILED", "", "Không xác minh được UID/profile người nhận.")
            status = classify_friend_controls(before["controls"])
            if status in {"ALREADY_PENDING", "ALREADY_FRIEND"}:
                return FriendRequestOutcome(status, expected, "Đã có trạng thái trước khi gửi; bỏ qua.")
            context = getattr(self, "account_log_context", None)
            index = context.get() if context is not None else None
            if index is not None:
                state = self.account_states.get(index)
                attempts = state.get("friend_attempts", set()) if state else set()
                if expected in attempts:
                    return FriendRequestOutcome("FAILED", expected, "Đã thao tác người nhận này trong đợt; không gửi lại khi chưa xác minh.")
                self.account_states.mark_friend_attempt(index, expected)
            await button.click(timeout=5000)
            for _ in range(8):
                await self.guard_facebook_checkpoint(page)
                after = await scope.evaluate(FRIEND_SCOPE_SNAPSHOT)
                after_references = {ref for link in after["links"] if (ref := friend_profile_reference(link))}
                if (target and friend_profile_reference(page.url) != expected) or (after_references and after_references != {expected}):
                    return FriendRequestOutcome("FAILED", expected, "Người nhận thay đổi sau khi click.")
                if after["connected"] and (not before["row"] or after_references == {expected}):
                    if classify_friend_controls(after["controls"]) == "ALREADY_PENDING":
                        return FriendRequestOutcome("SENT", expected, "Đã xác minh pending của đúng người nhận.")
                await asyncio.sleep(0.5)
            return FriendRequestOutcome("FAILED", expected, "Không có bằng chứng pending của đúng người nhận.")
        except Exception as exc:
            return FriendRequestOutcome("ERROR", expected, f"{type(exc).__name__}: {exc}")
        finally:
            if handle is not None:
                try:
                    await handle.dispose()
                except Exception as exc:
                    self.log(f"[FRIEND][CLEANUP] {type(exc).__name__}: {exc}")

    def record_friend_outcome(self, index, outcome):
        status = {"SENT": "SUCCESS", "ALREADY_PENDING": "SKIPPED", "ALREADY_FRIEND": "SKIPPED", "FAILED": "FAILED", "ERROR": "ERROR"}[outcome.status]
        self.record_task_result(index, "FRIEND_REQUEST", status, outcome[1], {
            "target": outcome.target, "result": outcome.status, "detail": outcome[1],
        })

    async def verify_facebook_session(self, page, context):
        """Distinguish a real logged-in session from login/checkpoint shells."""
        await self.guard_facebook_checkpoint(page)
        current_url = page.url.lower()
        if any(marker in current_url for marker in (
            "/login", "checkpoint", "challenge", "disabled", "suspended"
        )):
            return False, "Login / Checkpoint"

        cookies = await context.cookies("https://www.facebook.com/")
        cookie_names = {cookie.get("name") for cookie in cookies}
        if "c_user" not in cookie_names:
            return False, "Cookie thiếu c_user"

        login_fields = page.locator(
            'input[name="email"], input[name="pass"], form[action*="login"]'
        )
        if await login_fields.count() > 0:
            for index in range(await login_fields.count()):
                try:
                    if await login_fields.nth(index).is_visible():
                        return False, "Facebook đang hiển thị biểu mẫu đăng nhập"
                except Exception:
                    continue
        return True, "Phiên Facebook hợp lệ"

    async def get_current_page_identity(self, page):
        candidates = [page.url]
        for selector in ('link[rel="canonical"]', 'meta[property="og:url"]'):
            locator = page.locator(selector).first
            if await locator.count() > 0:
                attribute = "href" if selector.startswith("link") else "content"
                value = await locator.get_attribute(attribute)
                if value:
                    candidates.insert(0, value)
        return extract_facebook_page_identity(candidates)

    async def verify_created_page(self, page, index, job):
        await self.guard_facebook_checkpoint(page, index)
        state = self.account_states.get(index) or {}
        evidence = await page.evaluate(PAGE_CREATION_EVIDENCE)
        return verify_page_job_evidence(page.url, evidence, job, state.get("account_id", ""))

    async def page_setup_transition_detected(self, page, page_name, body_text, alerts):
        # A setup form/toast permits onboarding, never a SUCCESS record on its own.
        if await page.locator(PAGE_SETUP_FIELDS_SELECTOR).count() > 0:
            return True
        return any(page_creation_notice_matches(text, page_name) for text in [body_text, *alerts])

    async def get_page_setup_button(self, page):
        # Facebook also renders this wizard inline, outside role="dialog".
        for pattern in (PAGE_SETUP_FINISH_PATTERN, NEXT_BUTTON_PATTERN, PAGE_SETUP_SKIP_PATTERN):
            buttons = page.get_by_role("button", name=pattern)
            for index in range(await buttons.count()):
                button = buttons.nth(index)
                if (await button.is_visible() and await button.is_enabled()
                        and (await button.get_attribute("aria-disabled") or "").casefold() != "true"):
                    return button
        buttons = page.locator('div[role="dialog"] button[type="submit"]:visible')
        if await buttons.count() == 1 and await buttons.first.is_enabled():
            return buttons.first
        return None

    async def click_page_blank_margin(self, page, acc_name, index):
        if not self.is_running or getattr(self, "stop_requested", False):
            return False
        try:
            await self.guard_facebook_checkpoint(page, index)
            point = await page.evaluate(PAGE_BLANK_MARGIN_POINT)
            if not isinstance(point, dict):
                self.log(f"[PAGE][FOCUS] [{acc_name}] Không có vùng rìa trống an toàn; bỏ qua click.")
                return False
            if not self.is_running or getattr(self, "stop_requested", False):
                return False
            await asyncio.wait_for(page.mouse.click(point["x"], point["y"]), timeout=3)
            return True
        except Exception as exc:
            self.log(f"[PAGE][FOCUS] [{acc_name}] Bỏ qua click vùng trống: {type(exc).__name__}: {exc}")
            return False

    async def select_page_category(self, page, category_input, requested_category):
        options = page.locator('div[role="listbox"] [role="option"], ul[role="listbox"] li, [role="option"]')
        try:
            await options.first.wait_for(state="visible", timeout=5000)
        except (TimeoutError, PlaywrightTimeoutError):
            return False, "CATEGORY_SUGGESTIONS_NOT_AVAILABLE"
        
        # Mở rộng danh sách từ khóa tương đương cho đa ngôn ngữ
        req_norm = normalize_ui_text(requested_category)
        aliases = {req_norm}
        if req_norm == normalize_ui_text("Blog cá nhân"):
            aliases.update(normalize_ui_text(x) for x in ["Personal blog", "Blog personnel", "Blog personal", "Blog pessoal", "Persönlicher Blog", "บล็อกส่วนตัว", "Blog Pribadi", "ブログ(個人)", "개인 블로그"])
            
        for index in range(await options.count()):
            option = options.nth(index)
            if await option.is_visible():
                opt_text = await option.inner_text()
                if normalize_ui_text(opt_text) in aliases:
                    await option.click()
                    selected = await category_input.evaluate(r"""async (input, matched_text) => {
                        const normalize = text => (text || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
                        const deadline = Date.now() + 3000;
                        while (Date.now() < deadline && input.isConnected) {
                            const root = input.parentElement.parentElement;
                            const selected = Array.from(root.querySelectorAll('[aria-selected="true"], [data-selected-category], span'))
                            .some(el => !el.closest('[role="listbox"]') && el.getClientRects().length > 0
                                && normalize(el.textContent) === normalize(matched_text)
                                && (el.matches('[aria-selected="true"],[data-selected-category]')
                                    || el.parentElement.querySelector('button,[role="button"]')));
                            if (selected) return true;
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }
                        return false;
                    }""", opt_text)
                    return bool(selected), "" if selected else "CATEGORY_SELECTION_NOT_VERIFIED"
        return False, "CATEGORY_NOT_FOUND"
    async def ensure_personal_profile(self, context, page, acc_name):
        """Chuyển đổi danh tính từ Fanpage về lại tài khoản cá nhân trên giao diện."""
        cookies = await context.cookies("https://www.facebook.com/")
        has_page_cookie = any(cookie.get("name") == "i_user" for cookie in cookies)
        
        try:
            # 1. Thao tác chuyển profile trên giao diện UI
            profile_btn = page.locator(
                'div[role="navigation"] [aria-label*="Trang cá nhân của bạn" i], '
                'div[role="navigation"] [aria-label*="Your profile" i], '
                'div[role="banner"] [aria-label*="Trang cá nhân của bạn" i], '
                'div[role="banner"] [aria-label*="Your profile" i], '
                'div[aria-label*="Tài khoản" i][role="button"], '
                'div[aria-label*="Account" i][role="button"]'
            ).first

            if await profile_btn.count() > 0 and await profile_btn.is_visible():
                await self.human_click(page, profile_btn)
                await asyncio.sleep(2.0)

                # Tìm nút chuyển sang trang cá nhân chính
                switch_btn = page.locator(
                    'div[role="dialog"] div[role="button"][aria-label*="chuyển sang" i], '
                    'div[role="dialog"] div[role="button"][aria-label*="switch to" i], '
                    'div[role="dialog"] [data-nocookies="true"], '
                    'div[role="menu"] div[role="menuitem"]:has-text("Chuyển sang"), '
                    'div[role="menu"] div[role="menuitem"]:has-text("Switch to")'
                ).first

                if await switch_btn.count() > 0 and await switch_btn.is_visible():
                    await self.human_click(page, switch_btn)
                    await asyncio.sleep(4.0)

            # 2. Xóa triệt để cookie i_user và làm sạch storage
            try:
                await context.clear_cookies(name="i_user")
                await page.evaluate("() => { try { localStorage.removeItem('active_profile'); } catch(e){} }")
            except Exception:
                pass
            
            # 3. Reload về trang chủ kiểm tra trạng thái
            await page.goto("https://www.facebook.com/me", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3.0)

            updated_cookies = await context.cookies("https://www.facebook.com/")
            is_personal = not any(cookie.get("name") == "i_user" for cookie in updated_cookies)
            if is_personal:
                self.log(f"[✔] [{acc_name}] Đã chuyển về tài khoản cá nhân thành công.")
            else:
                self.log(f"[!] [{acc_name}] Cảnh báo: Vẫn còn giữ cookie quyền Page.")
            return is_personal

        except Exception as exc:
            self.log(f"[!] [{acc_name}] Lỗi khi chuyển về hồ sơ cá nhân: {exc}")
            # Phương án dự phòng: cố gắng xóa cookie và về lại trang chủ
            try:
                await context.clear_cookies(name="i_user")
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
                fallback_cookies = await context.cookies("https://www.facebook.com/")
                return not any(cookie.get("name") == "i_user" for cookie in fallback_cookies)
            except Exception:
                return False

    async def get_system_notifications(self, page):
        """Tự động đọc mọi thông báo nổi, toast, alert hệ thống theo chuẩn ARIA."""
        messages = []
        try:
            notifs = page.locator('[role="alert"], [role="status"]')
            count = await notifs.count()
            for i in range(count):
                el = notifs.nth(i)
                if await el.is_visible():
                    txt = (await el.inner_text()).strip()
                    if txt:
                        messages.append(txt)
        except Exception:
            pass
        return messages

    async def dismiss_floating_overlays(self, page):
        """Tự động đóng mọi popup, toast, dialog nổi cản trở trên màn hình."""
        try:
            await page.keyboard.press("Escape")
            close_btns = page.locator(
                '[aria-label="Đóng" i], [aria-label="Close" i], '
                '[role="status"] [role="button"], [role="alert"] [role="button"], '
                '[role="status"] button, [role="alert"] button'
            )
            for i in range(await close_btns.count()):
                btn = close_btns.nth(i)
                if await btn.is_visible():
                    await btn.click(timeout=800)
        except Exception:
            pass            
    async def human_type(self, page, locator, text: str, error_rate=0.03):
        """Gõ từng ký tự với độ trễ biến thiên, mô phỏng gõ nhầm và sửa lại."""
        await locator.click()
        await asyncio.sleep(random.uniform(0.3, 0.6))
        for char in text:
            if random.random() < error_rate:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await page.keyboard.press(wrong_char)
                await asyncio.sleep(random.uniform(0.12, 0.22))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.08, 0.16))
            await page.keyboard.type(char, delay=random.randint(55, 140))
            if char == " " and random.random() < 0.35:
                await asyncio.sleep(random.uniform(0.25, 0.5))

    async def human_click(self, page, locator):
        """Di chuyển chuột có quỹ đạo mềm và click lệch tâm tự nhiên."""
        box = await locator.bounding_box()
        if not box:
            await locator.click()
            return
        target_x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
        target_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)
        await page.mouse.move(target_x, target_y, steps=random.randint(6, 12))
        await asyncio.sleep(random.uniform(0.12, 0.28))
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.12))
        await page.mouse.up()
    async def safe_action_click(self, page, selector, acc_name, action_name="Click", retries=3):
        """
        Click an toàn khi DOM thay đổi, tự động retry khi bị Stale Element.
        """
        for attempt in range(1, retries + 1):
            try:
                locator = page.locator(selector)
                count = await locator.count()

                if count == 0:
                    return False

                target = locator.first
                await target.scroll_into_view_if_needed(timeout=3000)

                if not await target.is_visible(timeout=2000):
                    return False

                await target.click(timeout=3000)
                self.log(f"[DEBUG] [{acc_name}] {action_name} OK (attempt {attempt})")
                return True

            except Exception as e:
                err_msg = str(e).lower()
                if "detached" in err_msg or "not attached" in err_msg or "timeout" in err_msg:
                    self.log(f"[DEBUG] [{acc_name}] {action_name} retry {attempt}/{retries}: DOM thay đổi...")
                else:
                    self.log(f"[DEBUG] [{acc_name}] {action_name} retry {attempt}/{retries}: {type(e).__name__}")
                
                await asyncio.sleep(random.uniform(1.0, 1.5))

        return False
    async def run_create_page(
        self,
        page,
        context,
        acc_name,
        idx,
        targets=None,
        max_pages=5,
        min_page_del=60,
        max_page_del=120,
        resolved_proxy="",
    ):
        """
        Tạo Fanpage: Tích hợp check Checkpoint, đa tầng Selector, xử lý Stale Element (DOM refresh), 
        kiểm tra iframe, focus trước khi gõ và chụp ảnh debug.
        """
        await self.guard_facebook_checkpoint(page, idx)
        created_count = 0
        results = []
        current_page_job = None

        def record_result(result):
            result["owner_account_id"] = (self.account_states.get(idx) or {}).get("account_id", acc_name)
            result["page_job_id"] = current_page_job["page_job_id"] if current_page_job else ""
            results.append(result)
            result_status = str(result.get("status") or "ERROR").upper()
            detail = (
                result.get("reason")
                or result.get("technical_error")
                or result.get("page_url")
                or result.get("page_id")
                or result.get("page_name")
            )
            self.set_account_state(
                idx,
                current_action=f"Create Page [{result_status}]: {str(detail)[:140]}",
            )
            self.record_task_result(idx, "CREATE_PAGE", result_status, str(detail), result)
            try:
                save_create_page_outcome(result)
                append_create_page_account_log(
                    idx,
                    acc_name,
                    f"[{result['status']}][PAGE_FLOW] "
                    f"{result['page_name']} | {result['reason'] or result['technical_error'] or result['page_url'] or result['page_id']}",
                )
            except OSError as exc:
                self.log(f"[ERROR] [{acc_name}] Không ghi được kết quả Create Page: {exc}")
            return result

        planned_targets = build_create_page_plans(targets, max_pages)
        valid_targets, validation_error = validate_create_page_targets(
            planned_targets, max_pages
        )
        if not valid_targets:
            record_result(build_create_page_result(
                "FAILED", acc_name, "", "", reason=validation_error,
                account_index=idx, proxy=resolved_proxy,
            ))
            self.log(f"[FAILED] [{acc_name}] {validation_error}")
            return results

        effective_max_pages = len(planned_targets)

        self.log(
            f"[*] [{acc_name}] Bắt đầu tiến trình tạo {effective_max_pages} Fanpage "
            f"theo {len(planned_targets)} cấu hình hợp lệ..."
        )

        for p_idx in range(effective_max_pages):
            if not self.is_running or created_count >= effective_max_pages:
                break

            page_plan = parse_page_plan(planned_targets[p_idx])
            page_name = page_plan["name"]
            category_name = page_plan["category"]
            retry_count = 0
            page_context = build_page_context(
                acc_name, page_name, category_name,
                proxy=resolved_proxy,
                locale=self.account_states.get(idx).get("locale", "AUTO")
                if self.account_states.get(idx) else "AUTO",
            )
            owner_state = self.account_states.get(idx) or {}
            current_page_job = {
                "owner_account_id": owner_state.get("account_id", acc_name),
                "owner_uid": owner_state.get("uid") or owner_state.get("account_id"),
                "page_job_id": uuid.uuid4().hex, "page_name": page_name,
                "prior_page_ids": {result["page_id"] for result in results if result.get("page_id")},
                "submitted": False,
            }

            def set_page_flow_state(state, detail=""):
                transition_page_context(page_context, state)
                action = f"Create Page [{state}]"
                if detail:
                    action += f": {detail}"
                self.set_account_state(idx, current_action=action)
                self.log(f"[PAGE][{state}] [{acc_name}] {detail}".rstrip())

            set_page_flow_state("PENDING", f"{page_name} ({p_idx + 1}/{effective_max_pages})")
            set_page_flow_state("VALIDATING", f"category={category_name}")

            try:
                # ======================================================
                # BƯỚC 1: TRUY CẬP VÀ ĐỢI REACT LOAD XONG
                # ======================================================
                try:
                    set_page_flow_state("SESSION_CHECK")
                    await self.guard_facebook_checkpoint(page, idx)
                    if is_invalid_facebook_account_url(page.url):
                        reason = f"Session không hợp lệ trước Create Page: {page.url}"
                        set_page_flow_state("FAILED", reason)
                        self.set_account_failure(idx, "invalid_login", reason)
                        return results
                    set_page_flow_state("OPEN_CREATE_PAGE", page_name)
                    async def navigate_to_creation():
                        response = await page.goto(
                            "https://www.facebook.com/pages/creation/",
                            wait_until="domcontentloaded",
                            timeout=45000,
                        )
                        await self.guard_facebook_checkpoint(page, idx)
                        return response

                    _response, retry_count = await retry_create_page_operation(
                        navigate_to_creation, max_attempts=3, base_delay=1.0
                    )
                except Exception as e:
                    retry_count = getattr(e, "create_page_retry_count", retry_count)
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error=f"{type(e).__name__}: {e}",
                        retry_count=retry_count,
                        account_index=idx,
                        proxy=resolved_proxy,
                    ))
                    self.log(f"[ERROR] [{acc_name}] Lỗi tải trang tạo Page: {e}")
                    continue
                await asyncio.sleep(3)

                cur_url = page.url.lower()
                self.log(
                    f"[DEBUG] URL={page.url}"
                )

                self.log(
                    f"[DEBUG] Title={await page.title()}"
                )

                self.log(
                    f"[DEBUG] Inputs={await page.locator('input').count()}"
                )

                self.log(
                    f"[DEBUG] Textareas={await page.locator('textarea').count()}"
                )
                self.log(
                    f"[DEBUG] Frames={len(page.frames)}"
                )
                if is_invalid_facebook_account_url(cur_url):
                    reason = "Session invalid/checkpoint khi mở trang tạo Page."
                    self.log(f"[!] [{acc_name}] Tài khoản không còn phiên đăng nhập hợp lệ!")
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason=reason,
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.set_account_failure(idx, "invalid_login", reason)
                    return results
                if not re.search(r'/pages/creat', cur_url):
                    self.log(
                        f"[-] [{acc_name}] Facebook đã chuyển khỏi trang tạo Page ({page.url}). "
                        "Tài khoản có thể chưa được cấp quyền tạo Trang hoặc giao diện đã thay đổi."
                    )
                    await self.take_error_snapshot(page, acc_name, "create_page_redirect")
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason=f"Facebook chuyển khỏi trang tạo Page: {page.url}",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    break

                # ======================================================
                # BƯỚC 2: TÌM FORM TÊN TRANG (XỬ LÝ LỖI STALE ELEMENT VÀ IFRAME)
                # ======================================================
                # Đã gỡ bỏ form input[type="text"] chung chung để tránh bắt nhầm ô Search
                name_selectors = (
                    'div[role="main"] input[type="text"]:not([role="combobox"]):not([type="search"]), '
                    'label:has-text("Tên trang") input, '
                    'label:has-text("Page name") input, '
                    'label:has-text("Nom de la Page") input, '
                    'label:has-text("Nombre de la página") input, '
                    'label:has-text("Nome da Página") input, '
                    'input[aria-label*="tên trang" i], '
                    'input[aria-label*="page name" i], '
                    'input[aria-label*="nom de la page" i], '
                    'input[aria-label*="nombre de la página" i], '
                    'input[aria-label*="nome da página" i]'
                )
                
                # Check số lượng match để debug
                name_count = await page.locator(name_selectors).count()
                self.log(f"[DEBUG] [{acc_name}] Tìm thấy {name_count} phần tử khớp selector tên trang.")
                
                name_input = page.locator(name_selectors).first
                
                try:
                    await name_input.wait_for(state="visible", timeout=15000)
                except Exception:
                    self.log(f"[!] [{acc_name}] Form tải chậm hoặc lỗi DOM. Chụp ảnh debug và F5...")
                    
                    # Chụp ảnh thực trạng giao diện trước khi reload
                    if hasattr(self, 'take_error_snapshot'):
                        await self.take_error_snapshot(page, acc_name, "create_page_timeout_1")
                    
                    # Kiểm tra iframes đề phòng form bị nhúng ngầm
                    for i, frame in enumerate(page.frames):
                        self.log(f"[DEBUG] [{acc_name}] Frame {i}: {frame.url}")
                    
                    await page.reload(wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(3)
                    
                    # [QUAN TRỌNG NHẤT]: Re-assign (khai báo lại) locator sau khi reload (Khắc phục lỗi Copilot chỉ ra)
                    name_input = page.locator(name_selectors).first
                    name_count_retry = await page.locator(name_selectors).count()
                    self.log(f"[DEBUG] [{acc_name}] Sau F5, tìm thấy {name_count_retry} phần tử khớp.")
                    
                    try:
                        await name_input.wait_for(state="visible", timeout=15000)
                    except Exception:
                        self.log(f"[-] [{acc_name}] Vẫn không load được form. Bỏ qua lượt này.")
                        if hasattr(self, 'take_error_snapshot'):
                            await self.take_error_snapshot(page, acc_name, "create_page_fail_2")
                        record_result(build_create_page_result(
                            "ERROR", acc_name, page_name, category_name,
                            technical_error="Form tạo Page không xuất hiện sau retry.",
                            retry_count=retry_count + 1,
                            account_index=idx, proxy=resolved_proxy,
                        ))
                        continue

                # ======================================================
                # BƯỚC 3: GÕ TÊN TRANG (THÊM LỆNH FOCUS TRƯỚC KHI GÕ)
                # ======================================================
                set_page_flow_state("FILL_PAGE_NAME", page_name)
                await name_input.scroll_into_view_if_needed()
                await name_input.click(timeout=3000)
                
                # Ép trỏ chuột phải nháy đúng vào ô này trước khi gõ
                try:
                    await name_input.focus()
                except Exception:
                    self.log(f"[!] [{acc_name}] Lỗi focus ô tên trang. Chụp ảnh debug...")
                    if hasattr(self, 'take_error_snapshot'):
                        await self.take_error_snapshot(page, acc_name, "create_page_focus_fail")
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error="Không focus được ô page_name.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue
                
                await self.human_type(page, name_input, page_name)
                await asyncio.sleep(1)
                # Tự động bắt lỗi tên không hợp lệ từ Facebook và tự sửa
                await asyncio.sleep(1.0)
                err_notice = page.locator('div[role="alert"], div:has-text("không hợp lệ"), div:has-text("đề xuất")')
                if await err_notice.count() > 0 and await err_notice.first.is_visible():
                    self.log(f"[!] [{acc_name}] Tên '{page_name}' bị Facebook từ chối. Đang tự động đổi sang tên thuần...")
                    
                    # Lọc lấy tên thuần (bỏ các từ nối, hậu tố)
                    clean_name = page_name.split(" -")[0].split(" Official")[0].split(" Review")[0].strip()
                    
                    await name_input.fill(clean_name)
                    await asyncio.sleep(1)

                # ======================================================
                # ======================================================
                # BƯỚC 4: ĐIỀN HẠNG MỤC (CHỐNG NHẦM THANH TÌM KIẾM FACEBOOK)
                # ======================================================
                cat_selectors = (
                    'div[role="main"] input[role="combobox"], '
                    'label:has-text("Hạng mục") input, '
                    'label:has-text("Category") input, '
                    'label:has-text("Catégorie") input, '
                    'label:has-text("Categoría") input, '
                    'label:has-text("Categoria") input, '
                    'input[aria-label*="hạng mục" i], '
                    'input[aria-label*="category" i], '
                    'input[aria-label*="catégorie" i], '
                    'input[aria-label*="categoría" i], '
                    'input[aria-label*="categoria" i], '
                    'div[role="main"] input[role="combobox"], '
                    'input[role="combobox"]:not([aria-label*="kiếm" i]):not([aria-label*="search" i])'
                )

                cat_input = None
                cat_elements = page.locator(cat_selectors)
                
                # Quét từng phần tử tìm được để loại trừ dứt điểm thanh Search ở Header
                for i in range(await cat_elements.count()):
                    el = cat_elements.nth(i)
                    aria_label = (await el.get_attribute("aria-label") or "").lower()
                    if "tìm kiếm" in aria_label or "search" in aria_label:
                        continue  # Bỏ qua nếu là thanh tìm kiếm của Facebook
                    if await el.is_visible():
                        cat_input = el
                        break

                if cat_input:
                    set_page_flow_state("SELECT_CATEGORY", category_name)
                    await cat_input.scroll_into_view_if_needed()
                    await cat_input.click()
                    await cat_input.focus()
                    
                    # Gõ mô phỏng người dùng để kích hoạt dropdown gợi ý
                    await self.human_type(page, cat_input, category_name)
                    await asyncio.sleep(2.0)

                    # Sử dụng phím mũi tên xuống + Enter để chọn gợi ý chắc chắn
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.5)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(1.5)

                    # Kiểm tra xem hạng mục đã được chọn thành công hay chưa
                    has_selected_tag = await page.locator(
                        'div[role="main"] [aria-label*="xóa" i], '
                        'div[role="main"] [aria-label*="remove" i], '
                        'div[role="main"] span:has-text("' + category_name + '")'
                    ).count() > 0

                    if not has_selected_tag:
                        # Thử phương án dự phòng gọi select_page_category nếu phím Enter chưa bắt được
                        category_selected, category_reason = await self.select_page_category(page, cat_input, category_name)
                        if not category_selected:
                            record_result(build_create_page_result(
                                "FAILED", acc_name, page_name, category_name,
                                reason=category_reason, account_index=idx, proxy=resolved_proxy,
                            ))
                            continue
                else:
                    self.log(f"[!] [{acc_name}] Không tìm thấy ô nhập Hạng mục.")
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="CATEGORY_INPUT_NOT_FOUND", account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                # ======================================================
                # BƯỚC 5: BẤM TẠO VÀ CHỜ KẾT QUẢ TỪ SERVER
                # ======================================================
                create_btn = page.locator(
                    'div[role="main"] form button[type="submit"]:visible, '
                    'div[role="main"] button[type="submit"]:visible'
                ).first
                if await create_btn.count() == 0:
                    create_btn = page.get_by_role(
                        "button", name=CREATE_PAGE_BUTTON_PATTERN
                    ).first
                
                if await create_btn.count() == 0 or not await create_btn.is_visible():
                    self.log(f"[-] [{acc_name}] Không tìm thấy nút Tạo Trang.")
                    if hasattr(self, 'take_error_snapshot'):
                        await self.take_error_snapshot(page, acc_name, "no_create_btn")
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error="Không tìm thấy nút Submit tạo Page.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                try:
                    # Chờ tối đa 15 giây cho Facebook đồng bộ dữ liệu Tên và Hạng mục
                    if not await wait_for_locator_ready(create_btn, timeout=15000):
                        # Quét thông báo lỗi chi tiết trên form để chỉ rõ nguyên nhân
                        form_alerts = await page.locator(
                            'div[role="main"] div[role="alert"], '
                            'div[role="main"] [aria-invalid="true"], '
                            'div[role="main"] span:has-text("hợp lệ"), '
                            'div[role="main"] span:has-text("valid")'
                        ).all_inner_texts()
                        
                        detail_msg = "Nút Tạo Trang bị khóa: "
                        if form_alerts:
                            detail_msg += "; ".join(txt.strip() for txt in form_alerts if txt.strip())
                        else:
                            detail_msg += f"Tên '{page_name}' hoặc Hạng mục '{category_name}' chưa được Facebook chấp thuận."

                        self.log(f"[-] [{acc_name}] {detail_msg}")
                        record_result(build_create_page_result(
                            "FAILED", acc_name, page_name, category_name,
                            reason=detail_msg,
                            retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                        ))
                        if hasattr(self, 'take_error_snapshot'):
                            await self.take_error_snapshot(page, acc_name, "submit_disabled")
                        continue
                except Exception as e:
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error=f"Không chờ được nút Submit: {type(e).__name__}: {e}",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                try:
                    if not self.is_running or getattr(self, "stop_requested", False):
                        set_page_flow_state("CANCELLED", "Dừng trước khi Submit")
                        return results
                    set_page_flow_state("SUBMITTING", page_name)
                    before_identity = await self.get_current_page_identity(page)
                    if before_identity.get("id"):
                        current_page_job["prior_page_ids"].add(before_identity["id"])
                    await create_btn.scroll_into_view_if_needed()
                    await self.human_click(page, create_btn)
                    current_page_job["submitted"] = True
                    await self.guard_facebook_checkpoint(page, idx)
                except Exception as e:
                    self.log(f"[!] [{acc_name}] Lỗi click nút Tạo Trang. Chụp ảnh debug...")
                    if hasattr(self, 'take_error_snapshot'):
                        await self.take_error_snapshot(page, acc_name, "create_page_create_btn_click_fail")
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error=f"Submit failed: {type(e).__name__}: {e}",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                set_page_flow_state("VERIFYING", page_name)

                invalid_session_reason = ""
                policy_rejected = False
                rate_limited = False
                submission_accepted = False

                for _ in range(8):
                    if not self.is_running or getattr(self, "stop_requested", False):
                        set_page_flow_state("CANCELLED", "Dừng trong khi gửi tạo Page")
                        return results
                    await asyncio.sleep(2)
                    await self.guard_facebook_checkpoint(page, idx)

                    cur_url = page.url.lower()
                    if is_invalid_facebook_account_url(cur_url):
                        invalid_session_reason = f"Tài khoản mất phiên đăng nhập sau khi gửi tạo Page: {page.url}"
                        break

                    # 1. Tự động đọc mọi thông báo hệ thống xuất hiện trên màn hình qua ARIA
                    system_alerts = await self.get_system_notifications(page)
                    combined_alerts = " ".join(system_alerts).lower()
                    body_text = (await page.inner_text("body")).lower()

                    if is_page_policy_rejected(body_text) or "page policies" in combined_alerts or "chính sách" in combined_alerts:
                        policy_rejected = True
                        break

                    if any(err in f"{combined_alerts} {body_text}" for err in ["quá nhiều trang", "too many pages", "limit", "giới hạn"]):
                        rate_limited = True
                        break

                    # 2. Nhận diện cấu trúc Onboarding xuất hiện (form chi tiết hoặc URL đã điều hướng)
                    has_onboarding_form = await self.page_setup_transition_detected(
                        page, page_name, body_text, system_alerts
                    )

                    if has_onboarding_form or "profile.php?id=" in cur_url or "facebook.com/pages/creation" not in cur_url:
                        submission_accepted = True
                        # Do not dismiss the setup dialog itself with Escape.
                        break

                if invalid_session_reason:
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason=invalid_session_reason,
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.set_account_failure(idx, "invalid_login", invalid_session_reason)
                    return results

                if policy_rejected:
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="PAGE_POLICY_REJECTED",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.log(f"[-] [{acc_name}] Facebook từ chối tạo Page theo chính sách.")
                    continue

                if rate_limited:
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="Bị giới hạn tạo Trang gần đây (Rate limited)",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.log(f"[-] [{acc_name}] Bị giới hạn tạo Trang gần đây.")
                    break

                if not submission_accepted:
                    self.log(f"[-] [{acc_name}] Không phát hiện bước tiếp theo hoặc thông báo xác nhận.")
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="Không xuất hiện giao diện thiết lập sau khi bấm Tạo.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                await self.click_page_blank_margin(page, acc_name, idx)

                # ======================================================
                # BƯỚC 6: XỬ LÝ WIZARD THIẾT LẬP (MÔ PHỎNG NGƯỜI THẬT TỪNG BƯỚC)
                # ======================================================
                self.log(f"[*] [{acc_name}] Bắt đầu hoàn thiện các bước thiết lập Page (Bio, Tiếp, Xong)...")
                
                # 6.1. Điền Tiểu sử (Bio) ngẫu nhiên nếu có form
                bio_samples = [
                    "Chào mừng mọi người đến với kênh của mình! ✨",
                    "Nơi chia sẻ những khoảnh khắc và trải nghiệm thú vị mỗi ngày.",
                    "Trang cá nhân cập nhật tin tức và kiến thức hữu ích 🌿",
                    "Góc nhỏ lưu giữ kỷ niệm và kết nối những người bạn mới.",
                    "Học hỏi, chia sẻ và lan tỏa năng lượng tích cực 🌟"
                ]
                bio_input = page.locator('div[role="dialog"] textarea, textarea[aria-label*="tiểu sử" i], textarea[aria-label*="bio" i]').first
                if await bio_input.count() > 0 and await bio_input.is_visible():
                    try:
                        chosen_bio = random.choice(bio_samples)
                        await self.human_type(page, bio_input, chosen_bio)
                        await asyncio.sleep(random.uniform(1.2, 2.0))
                    except Exception:
                        pass

                # 6.2. Vòng lặp duyệt qua các bước Next / Done có nhịp dừng và cuộn trang
                wizard_step = 1
                for _ in range(15):
                    if not self.is_running or getattr(self, "stop_requested", False):
                        break
                    await self.guard_facebook_checkpoint(page, idx)

                    # Nếu đã điều hướng khỏi màn hình tạo trang và tới Page chính
                    cur_url = page.url.lower()
                    if "facebook.com/pages/creation" not in cur_url:
                        break

                    # Mô phỏng người đọc: thi thoảng cuộn nhẹ chuột trong dialog
                    if random.random() < 0.4:
                        await page.mouse.wheel(0, random.randint(120, 250))
                        await asyncio.sleep(random.uniform(0.6, 1.2))

                    # Ưu tiên tìm nút Xong/Done trước, sau đó tới Tiếp/Next/Bỏ qua
                    wiz_btn = await self.get_page_setup_button(page)
                    if wiz_btn is not None:
                        await wiz_btn.scroll_into_view_if_needed(timeout=5000)
                        if not await wait_for_locator_ready(wiz_btn, timeout=5000):
                            await asyncio.sleep(1)
                            continue
                        btn_name = (await wiz_btn.inner_text()).strip()
                        self.log(f"[*] [{acc_name}] [Bước {wizard_step}] Bấm '{btn_name}'...")
                        await self.human_click(page, wiz_btn)
                        wizard_step += 1
                        # Giữ nhịp dừng tự nhiên từ 3.5s đến 6s cho mỗi bước chuyển
                        await asyncio.sleep(random.uniform(3.5, 6.0))
                    else:
                        await asyncio.sleep(2.0)

                await self.click_page_blank_margin(page, acc_name, idx)

                # Đóng các popup chào mừng/giới thiệu nếu còn sót lại
                await page.keyboard.press("Escape")
                await asyncio.sleep(1.5)

                page_identity = await self.verify_created_page(page, idx, current_page_job)
                if not is_verified_page_identity(page_identity):
                    self.log(
                        f"[-] [{acc_name}] Không xác minh được Page URL/ID sau khi tạo; "
                        "không ghi nhận thành công."
                    )
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="Facebook đã chuyển sang thiết lập Page nhưng chưa xác minh được Page URL/ID; dừng tạo tiếp để tránh trùng Page.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    break

                if not self.is_running or getattr(self, "stop_requested", False):
                    set_page_flow_state("CANCELLED", "Không ghi success sau lệnh Stop")
                    return results
                transition_page_context(page_context, "SUCCESS", page_identity)
                page_record = build_create_page_result(
                    "SUCCESS", acc_name, page_name, category_name,
                    page_url=page_identity["url"], page_id=page_identity["id"],
                    retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    flow_state=page_context["creation_status"],
                )
                page_record.update(owner_account_id=page_identity["owner_account_id"],
                                   page_job_id=page_identity["page_job_id"])
                await self.guard_facebook_checkpoint(page, idx)
                if not save_created_page_success(page_record):
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        page_url=page_identity["url"], page_id=page_identity["id"],
                        reason="Page URL/ID đã tồn tại trong file kết quả.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.log(f"[FAILED] [{acc_name}] Bỏ qua Page trùng URL/ID.")
                    continue

                created_count += 1
                record_result(page_record)
                self.set_account_state(
                    idx,
                    current_action=f"Create Page [SUCCESS]: {created_count}/{effective_max_pages}",
                )
                self.log(f"[PAGE][SUCCESS] [{acc_name}] page_id={page_identity['id'] or 'N/A'} page_url={page_identity['url']}")

                if created_count < effective_max_pages:
                    if not await self.wait_between_page_jobs(
                        page, context, acc_name, idx, min_page_del, max_page_del
                    ):
                        break

            except Exception as e:
                self.log(f"[-] [{acc_name}] Lỗi vòng lặp tạo Page: {e}")
                record_result(build_create_page_result(
                    "ERROR", acc_name, page_name, category_name,
                    technical_error=f"{type(e).__name__}: {e}",
                    retry_count=retry_count,
                    account_index=idx,
                    proxy=resolved_proxy,
                ))
                if hasattr(self, 'take_error_snapshot'):
                    await self.take_error_snapshot(page, acc_name, "create_page_fatal")

        return results

    async def run_add_by_group(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Kết bạn theo danh sách thành viên nhóm"""
        if not targets:
            self.log(f"[-] [{acc_name}] Thiếu Link nhóm ở ô danh sách mục tiêu!")
            return 0
        self.log(f"[*] [{acc_name}] Bắt đầu kết bạn từ nhóm: {targets[0]}...")
        sent = 0
        try:
            group_members_url = targets[0].rstrip('/') + "/members"
            await page.goto(group_members_url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            for _ in range(target_total):
                if not self.is_running: break
                add_btn = page.locator(ADD_FRIEND_SELECTORS).first
                if await add_btn.count() > 0 and await add_btn.is_visible():
                    outcome = await self.click_and_confirm_friend_request(page, add_btn)
                    self.record_friend_outcome(idx, outcome)
                    confirmed, detail = outcome
                    if confirmed:
                        sent += 1
                        self.log(f"[✔] [{acc_name}] Đã xác nhận kết bạn nhóm {sent}/{target_total}")
                        await asyncio.sleep(random.randint(min_del, max_del))
                    else:
                        self.log(f"[!] [{acc_name}] Không tính lượt kết bạn nhóm: {detail}")
                        await page.evaluate("window.scrollBy(0, 500)")
                        await asyncio.sleep(2)
                else:
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(2)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi kết bạn nhóm: {e}")
            self.record_task_result(idx, "FRIEND_REQUEST", "ERROR", str(e))
        return sent

    async def run_add_by_uid(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Kết bạn theo danh sách UID / Link Profile"""
        if not targets:
            self.log(f"[-] [{acc_name}] Thiếu danh sách UID ở ô mục tiêu!")
            return 0
        sent = 0
        try:
            for target in targets[:target_total]:
                if not self.is_running: break
                profile_url = target if target.startswith("http") else f"https://www.facebook.com/{target}"
                self.log(f"[*] [{acc_name}] Mở profile: {profile_url}...")
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                btn = page.locator(ADD_FRIEND_SELECTORS + ", " + CANCEL_REQUEST_SELECTORS + ", " + FRIEND_STATE_SELECTORS).first
                if await btn.count() > 0 and await btn.is_visible():
                    outcome = await self.click_and_confirm_friend_request(page, btn, target=target)
                    self.record_friend_outcome(idx, outcome)
                    confirmed, detail = outcome
                    append_csv_result(
                        "friend_actions.csv",
                        ["time", "account", "target", "method", "status", "detail"],
                        {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "account": acc_name,
                            "target": target,
                            "method": "uid",
                            "status": outcome.status,
                            "detail": detail,
                        },
                    )
                    if confirmed:
                        sent += 1
                        self.log(f"[✔] [{acc_name}] Facebook xác nhận đã gửi: {target}")
                        await asyncio.sleep(random.randint(min_del, max_del))
                    else:
                        self.log(f"[!] [{acc_name}] Không tính {target}: {detail}")
                else:
                    self.record_task_result(idx, "FRIEND_REQUEST", "FAILED", f"Không xác định được trạng thái kết bạn của {target}.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi kết bạn UID: {e}")
            self.record_task_result(idx, "FRIEND_REQUEST", "ERROR", str(e))
        return sent

    async def run_join_groups(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Tham gia nhóm theo Link hoặc ID"""
        if not targets: return
        for g in targets[:target_total]:
            if not self.is_running: break
            try:
                g_url = g if g.startswith("http") else f"https://www.facebook.com/groups/{g}"
                await page.goto(g_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                join_btn = page.locator('div[role="button"]:has-text("Tham gia nhóm"), div[role="button"]:has-text("Join group")').first
                if await join_btn.count() > 0 and await join_btn.is_visible():
                    await join_btn.click()
                    self.log(f"[✔] [{acc_name}] Đã gửi yêu cầu tham gia nhóm: {g}")
                    await asyncio.sleep(random.randint(min_del, max_del))
            except Exception as e:
                self.log(f"[-] [{acc_name}] Lỗi tham gia nhóm '{g}': {e}")

    async def run_auto_post(self, page, acc_name, idx, targets):
        """Tự động đăng bài lên tường cá nhân"""
        post_content = targets[0] if targets else "Chúc mọi người một ngày mới tràn đầy năng lượng! ✨"
        posted_count = 0
        try:
            self.log(f"[*] [{acc_name}] Đang đăng bài lên tường cá nhân...")
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            post_box = page.locator('div[role="button"]:has-text("Bạn đang nghĩ gì thế?"), div[role="button"]:has-text("What\'s on your mind?")').first
            if await post_box.count() > 0:
                await post_box.click()
                await asyncio.sleep(2)
                txt_input = page.locator('div[role="textbox"][contenteditable="true"]').first
                if await txt_input.count() > 0:
                    await txt_input.fill(spin_text(post_content))
                    await asyncio.sleep(2)
                    send_btn = page.locator('div[role="button"]:has-text("Đăng"), div[role="button"]:has-text("Post")').first
                    if await send_btn.count() > 0:
                        await send_btn.click()
                        await asyncio.sleep(5)
                        posted_count = 1
                        self.log(f"[✔] [{acc_name}] Đã đăng bài thành công!")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi đăng bài: {e}")
        return posted_count

    async def run_auto_inbox(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Tự động gửi tin nhắn cho danh sách UID"""
        if not targets: 
            return 0
        msg_content = targets[1] if len(targets) > 1 else "Chào {bạn|anh|chị}, kết nối cùng nhau nhé!"
        uid_list = [targets[0]] if len(targets) == 1 else targets[:-1]
        sent_count = 0
        for u in uid_list[:target_total]:
            if not self.is_running: break
            try:
                m_url = f"https://www.facebook.com/messages/t/{u}"
                await page.goto(m_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(4)
                input_msg = page.locator('div[role="textbox"][contenteditable="true"]').first
                if await input_msg.count() > 0:
                    await input_msg.fill(spin_text(msg_content))
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    sent_count += 1
                    self.log(f"[✔] [{acc_name}] Đã gửi tin nhắn cho UID: {u}")
                    await asyncio.sleep(random.randint(min_del, max_del))
            except Exception as e:
                self.log(f"[-] [{acc_name}] Lỗi gửi tin nhắn tới UID {u}: {e}")
        return sent_count

    async def run_seed_group(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Seeding tương tác bài viết trong nhóm"""
        if not targets: 
            return 0
        sent_count = 0
        try:
            await page.goto(targets[0], wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            for _ in range(target_total):
                if not self.is_running: break
                like_btns = page.locator('div[aria-label="Thích"], div[aria-label="Like"]').first
                if await like_btns.count() > 0 and await like_btns.is_visible():
                    await like_btns.click()
                    sent_count += 1
                    self.log(f"[✔] [{acc_name}] Thả like bài viết nhóm ({sent_count}/{target_total})")
                    await asyncio.sleep(random.randint(min_del, max_del))
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(2)
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi seeding bài viết nhóm: {e}")
        return sent_count
    async def run_change_bio(self, page, acc_name, idx, targets):
        """Cập nhật tiểu sử Bio"""
        bio_txt = targets[0] if targets else "Sống tích cực mỗi ngày ✨ | Kết bạn làm quen nhé!"
        try:
            await page.goto("https://www.facebook.com/me", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            edit_bio = page.locator('div[role="button"]:has-text("Thêm tiểu sử"), div[role="button"]:has-text("Chỉnh sửa tiểu sử")').first
            if await edit_bio.count() > 0:
                await edit_bio.click()
                await asyncio.sleep(2)
                t_input = page.locator('textarea').first
                if await t_input.count() > 0:
                    await t_input.fill(bio_txt)
                    await asyncio.sleep(1)
                    save_btn = page.locator('div[role="button"]:has-text("Lưu"), div[role="button"]:has-text("Save")').first
                    if await save_btn.count() > 0:
                        await save_btn.click()
                        self.log(f"[✔] [{acc_name}] Đã cập nhật Bio mới thành công!")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi cập nhật Bio: {e}")

    async def run_change_avatar(self, page, acc_name, idx, targets):
        """Cập nhật ảnh đại diện từ file đường dẫn"""
        if not targets or not os.path.exists(targets[0]):
            self.log(f"[-] [{acc_name}] Đường dẫn ảnh không tồn tại: {targets}")
            return
        try:
            await page.goto("https://www.facebook.com/me", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            f_input = page.locator('input[type="file"][accept*="image"]').first
            if await f_input.count() == 0:
                self.log(f"[-] [{acc_name}] Không tìm thấy ô tải avatar lên.")
                return
            await f_input.set_input_files(targets[0])
            await asyncio.sleep(5)
            save_btn = page.locator('div[role="button"]:has-text("Lưu"), div[role="button"]:has-text("Save")').first
            if await save_btn.count() == 0:
                self.log(f"[-] [{acc_name}] Không tìm thấy nút lưu avatar.")
                return
            await save_btn.click()
            self.log(f"[✔] [{acc_name}] Đã cập nhật Avatar mới!")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi cập nhật Avatar: {e}")

    async def run_invite_friends_to_group(self, page, acc_name, idx, targets, target_total, min_del, max_del):
        """Mời bạn bè vào nhóm"""
        if not targets: 
            return 0
        invited_count = 0
        try:
            await page.goto(targets[0], wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            inv_btn = page.locator('div[role="button"]:has-text("Mời"), div[role="button"]:has-text("Invite")').first
            if await inv_btn.count() > 0:
                await inv_btn.click()
                await asyncio.sleep(3)
                select_all = page.locator('div[role="checkbox"]:has-text("Chọn tất cả")').first
                if await select_all.count() > 0: 
                    await select_all.click()
                send_inv = page.locator('div[role="button"]:has-text("Gửi lời mời")').first
                if await send_inv.count() > 0:
                    await send_inv.click()
                    invited_count = 1
                    self.log(f"[✔] [{acc_name}] Đã gửi lời mời bạn bè vào nhóm!")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi mời bạn vào nhóm: {e}")
        return invited_count

    async def run_scrape_uid_post(self, page, acc_name, idx, targets):
        """Quét UID tương tác bài viết"""
        if not targets: return
        try:
            await page.goto(targets[0], wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            links = await page.eval_on_selector_all('a[href*="/user/"], a[href*="id="]', 'els => els.map(e => e.href)')
            uids = set()
            for l in links:
                m = re.search(r'id=(\d+)', l) or re.search(r'user/(\d+)', l)
                if m: uids.add(m.group(1))
            if uids:
                with open(output_path("scraped_post_uids.txt"), "a", encoding="utf-8") as f:
                    for u in uids: f.write(f"{u}\n")
                self.log(f"[✔] [{acc_name}] Đã quét được {len(uids)} UID tương tác.")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi quét UID bài viết: {e}")

    async def run_post_page(self, page, acc_name, idx, targets):
        """Đăng bài lên Fanpage"""
        if not targets: return
        page_url = targets[0]
        content = targets[1] if len(targets) > 1 else "Bài viết mới trên Fanpage ✨"
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4)
            box = page.locator('div[role="button"]:has-text("Bạn đang nghĩ gì?"), div[role="button"]:has-text("Tạo bài viết")').first
            if await box.count() > 0:
                await box.click()
                await asyncio.sleep(2)
                inp = page.locator('div[role="textbox"][contenteditable="true"]').first
                if await inp.count() > 0:
                    await inp.fill(spin_text(content))
                    await asyncio.sleep(2)
                    p_btn = page.locator('div[role="button"]:has-text("Đăng"), div[role="button"]:has-text("Post")').first
                    if await p_btn.count() > 0:
                        await p_btn.click()
                        self.log(f"[✔] [{acc_name}] Đã đăng bài lên Page thành công!")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi đăng bài lên Page: {e}")

    async def run_seed_live(self, page, acc_name, idx, targets):
        """Bão Seeding Livestream Facebook"""
        if not targets: return
        live_url = targets[0]
        cmt = targets[1] if len(targets) > 1 else "{Tuyệt vời|Chào shop|Đã like live} {ạ|nhé|nha} ❤️"
        try:
            await page.goto(live_url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(5)
            for _ in range(5):
                if not self.is_running: break
                c_box = page.locator('div[role="textbox"][contenteditable="true"]').first
                if await c_box.count() > 0:
                    await c_box.fill(spin_text(cmt))
                    await page.keyboard.press("Enter")
                    self.log(f"[✔] [{acc_name}] Đã gửi bình luận Live Stream!")
                    await asyncio.sleep(random.randint(10, 20))
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi seeding livestream: {e}")
    
    async def process_account_scoped(self, *args, **kwargs):
        account_index = int(args[1])
        context_token = self.account_log_context.set(account_index)
        try:
            return await self.process_account(*args, **kwargs)
        finally:
            self.account_log_context.reset(context_token)

    async def process_account(
        self,
        playwright_instance,
        idx,
        acc_name,
        cookie_str,
        assigned_proxy_str,
        semaphore,
        account_type="",
        login_user="",
        login_password="",
        account_country="",
        account_locale="AUTO",
        account_timezone="",
    ):
        async with semaphore:
            if not self.is_running: return

            config = self.run_config
            modes = config.get("modes", {})
            options = config.get("options", {})

            self.set_account_state(idx, status="CHECKING", current_action="Khởi tạo tài khoản")
            self.update_tree_row(str(idx), status="ĐANG KIỂM TRA")
            self.log(f"\n[🚀 LUỒNG BẮT ĐẦU] Nick {idx}: {acc_name}")
            self.log(
                f"[*] [{acc_name}] Context: locale={normalize_account_locale(account_locale)}; "
                f"country={account_country or 'N/A'}; timezone={account_timezone or 'AUTO'}"
            )

            cookies = parse_cookies(cookie_str)
            try:
                assigned_proxy_str = await self.resolve_effective_proxy(idx, assigned_proxy_str)
            except Exception as exc:
                self.set_account_failure(idx, "proxy", f"Lỗi proxy: {exc}")
                self.update_tree_row(str(idx), status="ERROR")
                return
            proxy_cfg = parse_proxy(assigned_proxy_str)
            self.log(f"[*] [{acc_name}] Proxy thực tế: {safe_proxy_label(assigned_proxy_str) or 'Không dùng'}")
            is_headless = config.get("headless", False)

            if assigned_proxy_str and not proxy_cfg:
                reason = f"[{acc_name}] Proxy sai định dạng, dừng để tránh chạy nhầm IP thật."
                self.set_account_failure(idx, "proxy", reason)
                self.update_tree_row(str(idx), status="ERROR")
                return

            target_total = config.get("target", 25)
            min_del = config.get("min_delay", 25)
            max_del = config.get("max_delay", 35)
            
            
            targets = [line.strip() for line in config.get("targets", "").splitlines() if line.strip()]
            targets_by_mode = {
                mode: self.get_targets_for_mode(targets, mode, modes)
                for mode in modes
            }
            
            browser = None
            context = None
            page = None
            checkpoint_watcher = None
            try:
                self.set_account_state(idx, status="CHECKING", current_action="Mở trình duyệt và kiểm tra đăng nhập")
                # Gọi Helper khởi tạo trình duyệt siêu cấp (GPM Layout, Anti-Detect)
                browser, context, page = await self.create_browser_page(
                    playwright_instance,
                    idx,
                    proxy_cfg=proxy_cfg,
                    is_headless=is_headless,
                    account_locale=account_locale,
                    account_timezone=account_timezone,
                )
                checkpoint_watcher = asyncio.create_task(
                    self.watch_facebook_checkpoint(page, idx, asyncio.current_task())
                )
                await self.guard_facebook_checkpoint(page, idx)

                # --- BẮT ĐẦU LOGIC ĐĂNG NHẬP CHUẨN XÁC ---
                is_valid_session = False
                
                # Yêu cầu tool: Luôn đăng nhập bằng Cookie
                if not cookies:
                    self.set_account_failure(idx, "invalid_cookie", f"[{acc_name}] Thiếu Cookie.")
                    self.update_tree_row(str(idx), status="DIE")
                    return

                await context.add_cookies(cookies)
                self.log(f"[*] [{acc_name}] Đang mở trang chủ để nạp phiên Cookie...")
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
                await self.guard_facebook_checkpoint(page, idx)
                await asyncio.sleep(4)

                is_valid_session, session_detail = await self.verify_facebook_session(page, context)
                if not is_valid_session:
                    self.log(f"[!] [{acc_name}] Cookie không hợp lệ: {session_detail}. Fallback đăng nhập UID/PASSWORD...")
                    login_result, login_detail = await self.login_facebook_user_pass(
                        page, context, login_user, login_password
                    )
                    await self.guard_facebook_checkpoint(page, idx)
                    if login_result != LOGIN_SUCCESS:
                        reason = f"[{acc_name}] Đăng nhập UID/PASS thất bại: {login_detail}"
                        self.set_account_failure(idx, "invalid_login", reason)
                        self.update_tree_row(str(idx), status="DIE")
                        return
                    self.log(f"[✔] [{acc_name}] Đăng nhập bằng UID/PASSWORD + 2FA thành công!")
                else:
                    self.log(f"[✔] [{acc_name}] Đăng nhập bằng Cookie thành công: {session_detail}")  
                # --- KẾT THÚC LOGIC ĐĂNG NHẬP ---

                await self.guard_facebook_checkpoint(page, idx)
                self.set_account_state(idx, status="LIVE", current_action="Đăng nhập Facebook hợp lệ")
                self.update_tree_row(str(idx), status="LIVE")

                if options.get("browse_web"): await self.browse_external_web(page, acc_name)
                if options.get("warmup"): await self.warm_up_feed(page, acc_name)
                if options.get("watch_reels"): await self.watch_facebook_reels(page, acc_name)
                if options.get("view_stories"): await self.view_facebook_stories(page, acc_name)
                if options.get("check_notif"): await self.check_notifications(page, acc_name)
                if options.get("chat_react"): await self.react_messenger(page, acc_name)
                if options.get("interact_page"): await self.interact_fanpage(page, acc_name)
                if options.get("cancel_old"): await self.cancel_old_requests(page, acc_name)

                cur_friends = await self.get_current_friends_count(page)
                self.update_tree_row(str(idx), current_friends=cur_friends)

                total_sent = 0
                created_pages = []
                create_page_completion_action = ""
                friend_enabled = any(modes.get(mode) for mode in ("by_name", "by_group", "by_uid"))
                if friend_enabled:
                    self.record_task_result(idx, "FRIEND_REQUEST", "RUNNING", "Đang kết bạn")
                # 1. Kết bạn theo tên
                if modes.get("by_name", False):
                    total_sent += (await self.run_add_by_name(page, acc_name, idx, targets_by_mode["by_name"], target_total, min_del, max_del)) or 0

                # 2. Thành viên nhóm
                if modes.get("by_group", False):
                    total_sent += (await self.run_add_by_group(page, acc_name, idx, targets_by_mode["by_group"], target_total, min_del, max_del)) or 0

                # 3. Theo UID / Profile
                if modes.get("by_uid", False):
                    total_sent += (await self.run_add_by_uid(page, acc_name, idx, targets_by_mode["by_uid"], target_total, min_del, max_del)) or 0

                if friend_enabled:
                    friend_task = self.account_states.get(idx)["tasks"].get("FRIEND_REQUEST", {})
                    if friend_task.get("status") == "RUNNING":
                        self.record_task_result(idx, "FRIEND_REQUEST", "FAILED", "Không có lời mời nào được xác minh")

                # 4. Tham gia nhóm (Join)
                if modes.get("join_group", False):
                    await self.run_join_groups(page, acc_name, idx, targets_by_mode["join_group"], target_total, min_del, max_del)

                # 5. Tự động đăng bài
                if modes.get("auto_post", False):
                    total_sent += (await self.run_auto_post(page, acc_name, idx, targets_by_mode["auto_post"])) or 0

                # 6. Tự động gửi tin nhắn
                if modes.get("auto_inbox", False):
                    total_sent += (await self.run_auto_inbox(page, acc_name, idx, targets_by_mode["auto_inbox"], target_total, min_del, max_del)) or 0

                # 7. Seeding bài viết nhóm
                if modes.get("seed_group", False):
                    total_sent += (await self.run_seed_group(page, acc_name, idx, targets_by_mode["seed_group"], target_total, min_del, max_del)) or 0

                # 8. Cập nhật Bio
                if modes.get("change_bio", False):
                    await self.run_change_bio(page, acc_name, idx, targets_by_mode["change_bio"])

                # 9. Thay đổi Avatar/Ảnh bìa
                if modes.get("change_avatar", False):
                    await self.run_change_avatar(page, acc_name, idx, targets_by_mode["change_avatar"])

                # 10. Mời bạn vào nhóm
                if modes.get("invite_group", False):
                    total_sent += (await self.run_invite_friends_to_group(page, acc_name, idx, targets_by_mode["invite_group"], target_total, min_del, max_del)) or 0

                # 11. Quét UID tương tác
                if modes.get("scrape_uid", False):
                    await self.run_scrape_uid_post(page, acc_name, idx, targets_by_mode["scrape_uid"])
                
                # 12. Tạo Fanpage
                if modes.get("create_page", False):
                    self.record_task_result(idx, "CREATE_PAGE", "RUNNING", "Đang tạo Page")
                    page_target_num = config.get("page_target", 5)
                    p_min_del = config.get("min_page_delay", 60)
                    p_max_del = config.get("max_page_delay", 120)
                    
                    create_page_results = await self.run_create_page(
                        page, context, acc_name, idx, targets_by_mode["create_page"],
                        max_pages=page_target_num, 
                        min_page_del=p_min_del, 
                        max_page_del=p_max_del,
                        resolved_proxy=assigned_proxy_str or "",
                    )
                    created_pages = [
                        result for result in create_page_results
                        if result.get("status") == "SUCCESS"
                    ]
                    page_task = self.account_states.get(idx)["tasks"].get("CREATE_PAGE", {})
                    if page_task.get("status") == "RUNNING":
                        self.record_task_result(idx, "CREATE_PAGE", "FAILED", "Không có Page nào được xác minh")
                    page_metrics = {
                        status: sum(
                            1 for result in create_page_results
                            if result.get("status") == status
                        )
                        for status in ("SUCCESS", "FAILED", "ERROR")
                    }
                    self.log(
                        f"[PAGE][SUMMARY] [{acc_name}] requested={page_target_num} "
                        f"success={page_metrics['SUCCESS']} failed={page_metrics['FAILED']} "
                        f"error={page_metrics['ERROR']}"
                    )
                    total_sent += len(created_pages)
                    current_state = self.account_states.get(idx)
                    if current_state and current_state["status"] == "ERROR":
                        return
                    if current_state and current_state["status"] == "DIE":
                        self.record_create_page_account_result(
                            idx,
                            "die",
                            reason=current_state["current_action"],
                            created_count=len(created_pages),
                            target_count=page_target_num,
                        )
                        self.update_tree_row(str(idx), status="DIE")
                        self.log(
                            f"[DIE] [{acc_name}] Dừng riêng tài khoản này; "
                            "các tài khoản khác tiếp tục chạy."
                        )
                        return
                    if len(created_pages) >= page_target_num:
                        create_page_completion_action = (
                            f"Đã tạo xong {len(created_pages)}/{page_target_num} Page"
                        )
                        self.record_create_page_account_result(
                            idx,
                            "completed",
                            created_count=len(created_pages),
                            target_count=page_target_num,
                        )
                    else:
                        create_page_completion_action = (
                            f"Chưa hoàn tất Create Page: {len(created_pages)}/{page_target_num}"
                        )
                # 13. Đăng bài lên Fanpage
                if modes.get("post_page", False):
                    await self.run_post_page(page, acc_name, idx, targets_by_mode["post_page"])

                # 14. Seeding Livestream
                if modes.get("seed_live", False):
                    await self.run_seed_live(page, acc_name, idx, targets_by_mode["seed_live"])

                # 15. Đổi mật khẩu
                if modes.get("change_pass", False):
                    password_targets = targets_by_mode["change_pass"]
                    new_pwd = password_targets[0].strip() if password_targets else ""
                    if not login_password or not new_pwd:
                        self.log(
                            f"[-] [{acc_name}] Bỏ qua đổi mật khẩu vì thiếu mật khẩu hiện tại hoặc mật khẩu mới."
                        )
                    else:
                        await self.run_change_password(page, acc_name, idx, login_password, new_pwd)

                # 16. Bật 2FA
                if modes.get("enable_2fa", False):
                    await self.run_enable_2fa(page, acc_name, idx)

                # 17. Đăng xuất thiết bị cũ
                if modes.get("logout_sessions", False):
                    await self.run_logout_other_sessions(page, acc_name, idx)

                # 18. Thêm Admin Fanpage
                if modes.get("add_page_admin", False):
                    admin_targets = targets_by_mode["add_page_admin"]
                    admin_job = select_page_admin_job(admin_targets, idx, acc_name)
                    if not admin_job:
                        self.log(
                            f"[-] [{acc_name}] Thiếu cấu hình ghép Page. Dùng: "
                            "STT tài khoản|URL Page hoặc AUTO|UID admin"
                        )
                    else:
                        target_page = admin_job["page"]
                        if target_page.casefold() == "auto":
                            target_page = next(
                                (record["page_url"] for record in reversed(created_pages) if record["page_url"]),
                                "",
                            )
                        if not target_page:
                            self.log(
                                f"[-] [{acc_name}] Không có URL Page để ghép; xem created_pages.csv."
                            )
                        else:
                            page_access_result = await self.run_add_page_admin(
                                page, acc_name, idx, target_page, admin_job["admin"]
                            )
                            self.log(
                                f"[PAGE_ACCESS][SUMMARY] [{acc_name}] "
                                f"status={page_access_result['assignment_status']}"
                            )

                # 19. Đổi tên Fanpage
                if modes.get("update_page_name", False):
                    page_name_targets = targets_by_mode["update_page_name"]
                    if len(page_name_targets) < 2:
                        self.log(f"[-] [{acc_name}] Thiếu URL Page hoặc tên mới; không thực hiện đổi tên.")
                    else:
                        await self.run_update_page_info(
                            page, acc_name, idx, page_name_targets[0], page_name_targets[1]
                        )

                # 20. Mời like Page
                if modes.get("invite_like_page", False):
                    like_targets = targets_by_mode["invite_like_page"]
                    if not like_targets:
                        self.log(f"[-] [{acc_name}] Thiếu URL Page; không thực hiện mời like.")
                    else:
                        await self.run_invite_friends_like_page(page, acc_name, idx, like_targets[0])

                # 21. Nhắn tin người comment
                if modes.get("inbox_commenters", False):
                    commenter_targets = targets_by_mode["inbox_commenters"]
                    post_link = commenter_targets[0] if len(commenter_targets) > 0 else "https://www.facebook.com/"
                    msg_txt = commenter_targets[1] if len(commenter_targets) > 1 else "Chào {bạn|anh|chị}, em tư vấn ạ!"
                    await self.run_inbox_post_commenters(page, acc_name, idx, post_link, msg_txt)

                # 22. Đăng bài group đã vào
                if modes.get("post_joined_groups", False):
                    post_targets = targets_by_mode["post_joined_groups"]
                    post_content = post_targets[0] if post_targets else "Nội dung bài viết mẫu {chất lượng|uy tín}!"
                    await self.run_post_joined_groups(page, acc_name, idx, post_content)

                # 23. Bình luận kèm ảnh
                if modes.get("comment_with_image", False):
                    image_targets = targets_by_mode["comment_with_image"]
                    post_link = image_targets[0] if len(image_targets) > 0 else "https://www.facebook.com/"
                    cmt_text = image_targets[1] if len(image_targets) > 1 else "{Tư vấn|Quan tâm} ạ!"
                    img_path = image_targets[2] if len(image_targets) > 2 else ""
                    await self.run_comment_with_image(page, acc_name, idx, post_link, cmt_text, img_path)

                # 24. Quét member nhóm
                if modes.get("scrape_group_members", False):
                    group_targets = targets_by_mode["scrape_group_members"]
                    group_link = group_targets[0] if group_targets else "https://www.facebook.com/groups/feed"
                    await self.run_scrape_group_members(page, acc_name, idx, group_link, max_members=target_total)

                # 25. Quét SĐT/Email
                if modes.get("scrape_contacts", False):
                    await self.run_scrape_contact_info(page, acc_name, idx, targets_by_mode["scrape_contacts"])

                await self.guard_facebook_checkpoint(page, idx)
                task_state = self.account_states.get(idx)
                task_failures = [f"{module} {task['status']}: {task['detail']}"
                                 for module, task in task_state.get("tasks", {}).items()
                                 if task["status"] in {"FAILED", "ERROR"}]
                self.set_account_state(
                    idx, status="LIVE",
                    current_action="; ".join(task_failures) or create_page_completion_action or "Hoàn thành",
                )
                self.update_tree_row(str(idx), sent_today=total_sent, status="LIVE")
                self.log(f"[ACCOUNT][SUMMARY] {acc_name}: LIVE; TASK={task_state['last_task_result']}; {total_sent} kết quả đã xác nhận.")

            except FacebookCheckpointStopped:
                self.finalize_active_account_tasks(idx, "ERROR", "Dừng do Facebook Checkpoint")
                return
            except asyncio.CancelledError:
                current_state = self.account_states.get(idx)
                interrupted = bool(current_state and current_state["status"] in {"CHECKPOINT", "ERROR"})
                self.finalize_active_account_tasks(
                    idx, "ERROR" if interrupted else "SKIPPED",
                    current_state["current_action"] if interrupted else "Đã dừng theo yêu cầu",
                )
                if current_state and current_state["status"] in {"CHECKPOINT", "ERROR"}:
                    return
                if current_state and current_state["status"] == "CHECKING":
                    self.set_account_state(idx, status="ERROR", current_action="Đã dừng khi đang kiểm tra")
                    self.update_tree_row(str(idx), status="ERROR")
                else:
                    self.set_account_state(idx, current_action="Đã dừng")
                self.log(f"[!] Đã dừng nick {acc_name} theo yêu cầu.")
                raise
            except Exception as e:
                reason = f"Lỗi nick {acc_name}: {e}"
                self.finalize_active_account_tasks(idx, "ERROR", reason)
                self.set_account_failure(idx, "automation", reason)
                self.update_tree_row(str(idx), status="ERROR")
                # Bắn cảnh báo về Telegram
                t_token = config.get("tele_token", "")
                t_id = config.get("tele_chatid", "")
                if t_token and t_id:
                    send_telegram_alert(t_token, t_id, f"⚠️ CẢNH BÁO: Nick [{acc_name}] gặp sự cố/checkpoint!\nChi tiết: {e}")
            
            finally:
                # --- SIÊU NĂNG LỰC: DÙ LỖI HAY KHÔNG CŨNG BẮT BUỘC ĐÓNG TRÌNH DUYỆT ĐỂ CHỐNG TREO RAM ---
                if checkpoint_watcher is not None:
                    checkpoint_watcher.cancel()
                    await asyncio.gather(checkpoint_watcher, return_exceptions=True)
                cleanup_errors = await close_browser_resources(context, browser, page)
                if cleanup_errors:
                    self.log(f"[ERROR] [{acc_name}] Lỗi đóng browser/profile: {cleanup_errors[0]}")
    def parse_range_string(self, range_str: str) -> set:
        """Tự động phân tách chuỗi số phức hợp dạng '1, 3, 5-9' thành danh sách STT"""
        selected = set()
        if not range_str:
            return selected
        parts = range_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                sub = part.split('-', 1)
                if sub[0].strip().isdigit() and sub[1].strip().isdigit():
                    selected.update(range(int(sub[0].strip()), int(sub[1].strip()) + 1))
            elif part.isdigit():
                selected.add(int(part))
        return selected

    # [TÌM ĐẾN main_worker VÀ THAY THẾ TOÀN BỘ:]
    async def main_worker(self):
        config = self.run_config
        self.worker_loop = asyncio.get_running_loop()
        self.proxy_api_lock = asyncio.Lock()
        raw_acc_lines = [
            line
            for line in config.get("accounts", "").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        proxy_lines = [
            line.strip()
            for line in config.get("proxies", "").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        if not raw_acc_lines:
            self.log("[-] Không có tài khoản/cookie nào để chạy!")
            self.stop_bot()
            return

        parsed_accounts = config.get("parsed_accounts", {})
        # 1. ƯU TIÊN 1: LẤY THEO CÚ PHÁP Ô NHẬP (VD: 1, 3, 5-9)
        manual_syntax = config.get("selected_indexes", "")
        target_indexes = self.parse_range_string(manual_syntax)

        # 2. ƯU TIÊN 2: NẾU Ô CÚ PHÁP TRỐNG, LẤY CÁC DÒNG CÓ DẤU [✔] TRONG BẢNG TREEVIEW
        if not target_indexes:
            target_indexes = set(config.get("checked_indexes", set()))

        threads_count = config.get("threads", 3)
        modes = config.get("modes", {})
        if modes.get("create_page", False) or modes.get("add_page_admin", False):
            max_create_workers = max(1, int(config.get("max_create_page_workers", 3)))
            threads_count = effective_account_worker_count(
                threads_count, modes, max_create_workers
            )
        if modes.get("create_page", False):
            raw_targets = [
                line.strip() for line in config.get("targets", "").splitlines()
                if line.strip()
            ]
            create_targets = self.get_targets_for_mode(raw_targets, "create_page", modes)
            planned_targets = build_create_page_plans(
                create_targets, config.get("page_target", 5)
            )
            valid_targets, validation_error = validate_create_page_targets(
                planned_targets, config.get("page_target", 5)
            )
            if not valid_targets:
                self.log(f"[FAILED][CREATE_PAGE][PRE-FLIGHT] {validation_error}")
                for index in target_indexes or range(1, len(raw_acc_lines) + 1):
                    self.set_account_state(
                        index,
                        current_action=f"Create Page FAILED: {validation_error}",
                    )
                return
        batch_size = config.get("batch_size", 5)
        ratio = config.get("proxy_ratio", 20)
        resolved_proxies = config.get("resolved_proxies", {})
        semaphore = asyncio.Semaphore(threads_count)
        account_jobs = []
        for idx, line in enumerate(raw_acc_lines, 1):
            if target_indexes and idx not in target_indexes:
                continue
            parsed = parsed_accounts.get(idx) or parsed_accounts.get(str(idx))
            if not parsed:
                parsed = parse_any_account_line(line, idx)
            if not parsed:
                continue

            acc_name = account_display_name(parsed, idx)
            cookie_str = (parsed.get("cookie") or "").strip()

            # Yêu cầu cốt lõi: Bắt buộc phải có Cookie để chạy tài khoản
            if not cookie_str:
                self.set_account_failure(
                    idx,
                    "input",
                    f"[{acc_name}] Thiếu chuỗi Cookie hợp lệ (Tool chạy hoàn toàn bằng Cookie).",
                )
                continue

            assigned_proxy_str = resolve_account_proxy(
                parsed.get("proxy"), resolved_proxies, idx
            ) or None
            if (
                not assigned_proxy_str
                and config.get("proxy_mode") not in {"account", "rotating_api"}
                and proxy_lines
            ):
                if config.get("proxy_mode") in {"round_robin", "random"}:
                    assigned_proxy_str = proxy_lines[(idx - 1) % len(proxy_lines)]
                else:
                    proxy_index = (idx - 1) // ratio
                    assigned_proxy_str = proxy_lines[proxy_index] if proxy_index < len(proxy_lines) else proxy_lines[-1]

            account_jobs.append({
                "idx": idx,
                "acc_name": acc_name,
                "cookie_str": cookie_str,
                "assigned_proxy_str": assigned_proxy_str,
                "account_type": "COOKIE",
                "login_user": parsed.get("uid", ""),
                "login_password": parsed.get("password") or parsed.get("pwd", ""),
                "two_factor": parsed.get("2fa", ""),
                "token": parsed.get("token", ""),
                "raw_line": parsed.get("raw_line", line),
                "country": parsed.get("country", ""),
                "locale": parsed.get("locale", "AUTO"),
                "timezone": parsed.get("timezone", ""),
            })

        batches = split_account_batches(account_jobs, batch_size)
        self.log(
            f"[BẮT ĐẦU ĐỢT CHẠY] {len(account_jobs)} tài khoản • "
            f"{len(batches)} đợt • {threads_count} luồng đồng thời"
        )
        unexpected_errors = []

        async with async_playwright() as p:
            for batch_number, batch_jobs in enumerate(batches, start=1):
                if self.stop_requested:
                    break
                self.post_ui(lambda number=batch_number: self.show_batch(number))
                batch_indexes = [job["idx"] for job in batch_jobs]
                self.log(f"[BẮT ĐẦU ĐỢT] Đợt {batch_number}/{len(batches)} • {len(batch_jobs)} tài khoản")

                tasks = []
                for job in batch_jobs:
                    tasks.append(asyncio.create_task(self.process_account_scoped(
                        p,
                        job["idx"],
                        job["acc_name"],
                        job["cookie_str"],
                        job["assigned_proxy_str"],
                        semaphore,
                        account_type=job["account_type"],
                        login_user=job["login_user"],
                        login_password=job["login_password"],
                        account_country=job["country"],
                        account_locale=job["locale"],
                        account_timezone=job["timezone"],
                    )))

                self.worker_tasks = tasks
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                for job, result in zip(batch_jobs, task_results):
                    if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                        unexpected_errors.append(result)
                        self.set_account_failure(
                            job["idx"],
                            "automation",
                            f"Lỗi worker chưa xử lý: {type(result).__name__}: {result}",
                        )
                self.worker_tasks = []

                batch_summary = self.account_states.summary(batch_indexes)
                batch_tasks = self.account_states.task_summary(batch_indexes)
                self.log(
                    f"[KẾT THÚC ĐỢT] Đợt {batch_number}/{len(batches)} • "
                    f"LIVE: {batch_summary['LIVE']} • DIE: {batch_summary['DIE']} • "
                    f"ERROR: {batch_summary['ERROR']} • CHECKPOINT: {batch_summary['CHECKPOINT']} • TASK: {batch_tasks}"
                )

        if self.stop_requested:
            self.log("\n[!] Tiến trình đã dừng; các luồng đang chạy đã được đóng an toàn.")
            return

        final_summary = self.account_states.summary([job["idx"] for job in account_jobs])
        self.log(
            f"[KẾT THÚC ĐỢT CHẠY] LIVE: {final_summary['LIVE']} • "
            f"DIE: {final_summary['DIE']} • ERROR: {final_summary['ERROR']} • CHECKPOINT: {final_summary['CHECKPOINT']} • "
            f"TASK: {self.account_states.task_summary([job['idx'] for job in account_jobs])}"
        )
        if modes.get("create_page", False):
            self.post_ui(self.remove_processed_create_page_accounts_from_input)
        t_token = config.get("tele_token", "")
        t_id = config.get("tele_chatid", "")
        if t_token and t_id:
            send_telegram_alert(t_token, t_id, "🎉 THÔNG BÁO: Toàn bộ dàn nick đã hoàn thành tất cả tiến trình!")

    def check_live_selected(self):
        selected = self.tree.selection() or self.tree.get_children()
        if not selected:
            messagebox.showwarning("Chú ý", "Bảng đang trống!")
            return

        selected_accounts = [
            (item, str(self.tree.item(item, "values")[2]).strip())
            for item in selected
        ]
        for item, _uid in selected_accounts:
            if str(item).isdigit():
                self.set_account_state(int(item), status="CHECKING", current_action="Kiểm tra UID")
                self.update_tree_row(item, status="ĐANG KIỂM TRA")

        def worker():
            for item, uid in selected_accounts:
                account_index = int(item) if str(item).isdigit() else None
                if uid and uid.isdigit():
                    try:
                        url = f"https://graph.facebook.com/{uid}/picture?type=normal"
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            response_url = resp.geturl()
                        action = "UID có phản hồi; cần đăng nhập để xác nhận LIVE/DIE"
                        if "static.xx.fbcdn.net" in response_url:
                            action = "UID không xác định; cần đăng nhập để kết luận"
                        if account_index is not None:
                            self.set_account_state(account_index, status="UNKNOWN", current_action=action)
                            self.log(f"[*] [{uid}] {action}", account_index=account_index)
                        status_live = "CHƯA KIỂM TRA"
                    except Exception as error:
                        if account_index is not None:
                            self.set_account_failure(
                                account_index,
                                "network",
                                f"Không thể kiểm tra UID do lỗi mạng: {error}",
                            )
                        status_live = "ERROR"
                else:
                    if account_index is not None:
                        self.set_account_failure(account_index, "input", "Không có UID hợp lệ để kiểm tra.")
                    status_live = "ERROR"

                self.update_tree_row(item, status=status_live)
            self.post_ui(lambda: messagebox.showinfo("Hoàn tất", "Đã kiểm tra xong tình trạng Live/Die."))

        threading.Thread(target=worker, daemon=True).start()

    def get_parsed_account_for_item(self, item_id):
        values = self.tree.item(item_id, "values")
        if not values or not str(values[1]).isdigit():
            return None

        account_index = int(values[1])
        source_lines = [
            line.strip()
            for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if account_index < 1 or account_index > len(source_lines):
            return None
        return parse_any_account_line(source_lines[account_index - 1], account_index)


    def open_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn 1 dòng tài khoản để mở Profile!")
            return

        item = selected[0]
        vals = self.tree.item(item, "values")
        
        stt = int(vals[1])
        parsed_account = self.account_states.get(stt)
        if not parsed_account: return
        acc_name = parsed_account.get("name", str(stt))
        proxy_str = parsed_account.get("proxy", "Không dùng")
        cookie_str = parsed_account.get("cookie", "")

        profiles_dir = os.path.join(APP_DATA_DIR, "browser_profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        profile_path = os.path.join(profiles_dir, f"profile_{acc_name}")

        def launch():
            # Khởi tạo chính sách vòng lặp sự kiện bất đồng bộ an toàn chống gạch ngang cảnh báo
            if sys.platform == 'win32':
                try:
                    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except AttributeError:
                    pass

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
                    
                    # Giải pháp gia cố: Ép giải phóng tệp Lock dù người dùng tắt trình duyệt bằng bất cứ cách nào
                    try:
                        if cookie_str:
                            await context.add_cookies(parse_cookies(cookie_str))
                        page = context.pages[0] if context.pages else await context.new_page()
                        await page.goto("https://facebook.com")
                        
                        # Vòng lặp giữ trình duyệt sống cho đến khi người dùng tắt thủ công cửa sổ cuối cùng
                        while len(context.pages) > 0:
                            await asyncio.sleep(1)
                    except Exception:
                        pass
                    finally:
                        # Buộc phải đóng đóng đóng context để nhả file khóa
                        await context.close()
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
        acc_name = vals[3] if len(vals) > 3 else vals[1]

        parsed_account = self.get_parsed_account_for_item(item)
        cookie_str = parsed_account.get("cookie", "") if parsed_account else ""

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
                        def show_success():
                            self.root.clipboard_clear()
                            self.root.clipboard_append(token)
                            messagebox.showinfo("Thành công", f"Đã lấy được Token EAAB (Copy tự động):\n\n{token[:45]}...")
                        self.post_ui(show_success)
                    else:
                        self.post_ui(lambda: messagebox.showwarning("Thông báo", "Cookie không hợp lệ/Không có Token EAAB."))
            except Exception as e:
                self.post_ui(lambda err=e: messagebox.showerror("Lỗi", f"Không thể lấy Token: {err}"))

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
        saved_key = load_saved_license()
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
        k = load_saved_license()
        _, exp = verify_license(k)
        app = MainToolApp(main_root, exp)
        main_root.mainloop()
        sys.exit(0)

    app = LicenseCheckDialog(root, launch_main)
    root.mainloop()

if __name__ == "__main__":
    main()
