import asyncio
from facebook.page_creator import build_create_page_result
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
from datetime import datetime, timedelta, timezone
import math
from tkinter import ttk, messagebox, scrolledtext, filedialog
from urllib.parse import quote, urlparse
from urllib.parse import unquote, urljoin
import copy
import ipaddress
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from types import MappingProxyType
from account_history import AccountHistoryStore, COUNTER_FIELDS, history_account_id, redact_history_text, safe_proxy_label
from result_center import (
    RESULT_COLUMNS, RESULT_HEADERS, RESULT_TABS, SUMMARY_KEYS, report_record,
    result_matches, result_summary, result_values, write_result_csv, write_result_workbook,
)
from long_run import DuplicatePageResult, ModuleCircuitBreaker, SingleInstanceLock, app_circuit_breaker
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
CURRENT_VERSION = "2.3.3"
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
CORE_AUTOMATION_MODES = ("create_page", "by_name", "by_group", "by_uid")

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
    "UNKNOWN": {"background": "#28323C", "foreground": "#E2C891"},
    "CHECKING": {"background": "#153F60", "foreground": "#8EDB56"},
    "LIVE": {"background": "#164535", "foreground": "#8FBDFC"},
    "CHECKPOINT": {"background": "#8F702E", "foreground": "#FFFFFF"},
    "DIE": {"background": "#57252C", "foreground": "#FFB5BF"},
    "ERROR": {"background": "#623B1D", "foreground": "#FFD1BC"},
}

TASK_RESULTS = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "ERROR", "SKIPPED"}
RUN_STATUSES = {"RUNNING", "COMPLETED", "COMPLETED_WITH_ERRORS", "CANCELLED", "FAILED"}
ACCOUNT_TABLE_PALETTE = {
    "background": "#19232C", "foreground": "#2BF33C",
    "header_background": "#24323D", "header_foreground": "#14AACF",
    "selected_background": "#285D69", "selected_foreground": "#FFFFFF",
    "RUNNING": ACCOUNT_STATUS_PALETTE["CHECKING"],
}
ACCOUNT_MANAGEMENT_COLUMNS = (
    "select", "id", "uid", "password", "2fa", "cookie", "token", "login_mode",
    "status", "action", "page", "friend", "last_update",
)


def configure_account_table_style(style, *trees):
    palette = ACCOUNT_TABLE_PALETTE
    if isinstance(style, ttk.Style) and "clam" in style.theme_names():
        # Clone only table elements: native Windows borders can ignore dark backgrounds.
        for element in ("Treeview.field", "Treeheading.cell", "Treeheading.border"):
            name = "Account." + element
            if name not in style.element_names():
                style.element_create(name, "from", "clam", element)
        style.layout("Account.Treeview", [("Account.Treeview.field", {"sticky": "nswe", "border": 1,
            "children": [("Treeview.padding", {"sticky": "nswe", "children": [("Treeview.treearea", {"sticky": "nswe"})]})]})])
        style.layout("Account.Treeview.Heading", [("Account.Treeheading.cell", {"sticky": "nswe"}),
            ("Account.Treeheading.border", {"sticky": "nswe", "children": [("Treeheading.padding", {"sticky": "nswe", "children": [
                ("Treeheading.image", {"side": "right", "sticky": ""}),
                ("Treeheading.text", {"sticky": "we"})]})]})])
    style.configure("Account.Treeview", rowheight=34, foreground=palette["foreground"], background=palette["background"], fieldbackground=palette["background"], font=("Segoe UI", 11))
    style.configure("Account.Treeview.Heading", background=palette["header_background"], foreground=palette["header_foreground"], font=("Segoe UI", 11, "bold"), padding=(8, 7))
    style.map("Account.Treeview", background=[("selected", palette["selected_background"])], foreground=[("selected", palette["selected_foreground"])])
    for tree in trees:
        tree.configure(style="Account.Treeview")
        for status, palette in ACCOUNT_STATUS_PALETTE.items():
            tree.tag_configure(status, **palette)


def management_account_values(state, checked=True):
    timestamp = str(state.get("last_update") or "")
    try:
        timestamp = datetime.fromisoformat(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S") if timestamp else "-"
    except ValueError:
        timestamp = "-"
    return (
        "[✔]" if checked else "[ ]", state["stt"], state.get("uid", ""),
        "********" if state.get("password") else "", "********" if state.get("2fa") else "",
        "YES" if state.get("cookie") else "NO", "YES" if state.get("token") else "NO",
        state.get("login_mode") or "-", state.get("status", "UNKNOWN"),
        redact_history_text(state.get("current_action", ""), state),
        f"{state.get('page_success_count', 0)} / {state.get('page_failed_count', 0)}",
        f"{state.get('friend_success_count', 0)} / {state.get('friend_failed_count', 0)}", timestamp,
    )


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
LOGIN_CHECKPOINT = "CHECKPOINT"

FACEBOOK_LOGIN_FORM_SELECTOR = 'input[name="email"], input[name="pass"], form[action*="login"]'
FACEBOOK_AUTHENTICATED_SELECTOR = (
    'a[href*="/logout.php"], form[action*="/logout"], '
    '[data-testid="blue_bar_profile_link"], '
    '[role="navigation"] a[href*="/messages"], [role="banner"] a[href*="/messages"], '
    '[role="navigation"] a[href*="/settings"], [role="banner"] a[href*="/settings"], '
    '[role="banner"] [role="button"][aria-label="Your profile" i], '
    '[role="navigation"] [role="button"][aria-label="Your profile" i], '
    '[role="banner"] [role="button"][aria-label="Trang cá nhân của bạn" i], '
    '[role="navigation"] [role="button"][aria-label="Trang cá nhân của bạn" i]'
)
FACEBOOK_2FA_INPUT_SELECTOR = (
    'input[id="approvals_code"], input[name="approvals_code"], input[autocomplete="one-time-code"]'
)
FACEBOOK_2FA_SUBMIT_SELECTOR = (
    'button[id="checkpointSubmitButton"], '
    'form:has(input[name="approvals_code"]) button[type="submit"], '
    'form:has(input[autocomplete="one-time-code"]) button[type="submit"]'
)


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


def write_create_page_results_xlsx(file_path, categorized_records, result_rows=None):
    """Preserve the A-I account report and optionally include the realtime result schema."""
    write_result_workbook(file_path, categorized_records, result_rows)


class AccountStateStore:
    def __init__(self, history=None):
        self._lock = threading.RLock()
        self._states = {}
        self.history = history

    def _persist(self, state, module="ACCOUNT", event_type="STATE", message="", task_event=None):
        state["last_update"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        if self.history is not None:
            self.history.save(state, module, event_type, message, task_event=task_event)

    def sync(self, accounts):
        with self._lock:
            previous = {history_account_id(state): state for state in self._states.values()}
            active_indexes = set()
            for account in accounts:
                index = int(account["stt"])
                active_indexes.add(index)
                account_id = str(account.get("account_id") or f"Tài khoản {index}")
                account_payload = {
                    "account_record": account.get("account_record"),
                    "canonical_line": str(account.get("canonical_line") or ""),
                    "import_fields": list(account.get("import_fields") or []),
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
                existing = previous.get(history_account_id({**account_payload, "account_id": account_id}))
                if existing is None:
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
                        "last_error": "",
                        "last_update": "",
                        "_counter_events": set(),
                        **{field: 0 for field in COUNTER_FIELDS},
                        **account_payload,
                    }
                    saved = self.history.load(self._states[index]) if self.history else None
                    if saved:
                        self._states[index].update(
                            status=saved["last_status"], current_action=saved["last_action"],
                            tasks=saved["tasks"], last_task_result=saved["last_task_result"],
                            history_logs=saved["logs"],
                            last_error=saved.get("last_error") or "",
                            last_update=saved.get("last_update") or saved.get("last_seen_at") or "",
                            **{field: int(saved.get(field) or 0) for field in COUNTER_FIELDS},
                        )
                        if saved.get("login_mode"):
                            self._states[index]["login_mode"] = saved["login_mode"]
                else:
                    self._states[index] = existing
                    existing["stt"] = index
                    existing["account_id"] = account_id
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
            snapshot.pop("_counter_events", None)
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
                state["_counter_events"] = set()
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
            if status in {"DIE", "ERROR", "CHECKPOINT"}:
                state["last_error"] = state["current_action"]
            self._persist(state)
            return self.get(index)

    def set_proxy(self, index, proxy):
        with self._lock:
            state = self._states[int(index)]
            state["proxy"] = state["effective_proxy"] = str(proxy or "")
            self._persist(state, event_type="PROXY", message=safe_proxy_label(proxy))

    def set_login_mode(self, index, mode):
        if mode not in {"COOKIE", "FALLBACK_LOGIN"}:
            raise ValueError("Invalid login mode.")
        with self._lock:
            state = self._states.get(int(index))
            if state is not None:
                state["login_mode"] = mode
                self._persist(state, event_type="LOGIN_MODE", message=f"Login mode: {mode}")

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
                    if status == "ERROR":
                        state["last_error"] = reason
                    self._count_task_result(state, module, status, reason)
                    state["last_task_result"] = task_result_status(state["tasks"])
                    self._persist(state, module, "TASK", reason, {"status": status, "detail": reason})

    def record_task(self, index, module, status, detail="", outcome=None, preserve_outcomes=False):
        if status not in TASK_RESULTS:
            raise ValueError(f"Task result không hợp lệ: {status}")
        with self._lock:
            state = self._states.get(int(index))
            if state is None or state.get("checkpoint_stopped"):
                return False
            state = dict(state)
            state["tasks"] = copy.deepcopy(state.get("tasks", {}))
            state["_counter_events"] = set(state.get("_counter_events", set()))
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
            self._count_task_result(state, module, status, detail, outcome)
            if status in {"FAILED", "ERROR"}:
                state["last_error"] = str(detail)
            if task["status"] in {"FAILED", "ERROR"}:
                state["current_action"] = f"{module} {task['status']}: {task['detail']}"
            self._persist(state, module, "TASK", detail, {
                "status": status, "detail": detail,
                "outcomes": [outcome] if outcome is not None else [],
            })
            self._states[int(index)] = state
            return True

    def _count_task_result(self, state, module, status, detail, outcome=None):
        prefix = {"CREATE_PAGE": "page", "FRIEND_REQUEST": "friend"}.get(module)
        if prefix is None or status not in {"SUCCESS", "FAILED", "ERROR"}:
            return
        # Outcome identity avoids counting a repeated notification as another result.
        identity = None
        if isinstance(outcome, dict):
            identity = (outcome.get("page_job_id") or outcome.get("page_id")
                        or outcome.get("page_url") or outcome.get("target"))
        if not identity:
            identity = json.dumps(outcome, sort_keys=True, default=str) if outcome is not None else str(detail)
        key = (module, "SUCCESS" if status == "SUCCESS" else "FAILED", identity)
        counted = state.setdefault("_counter_events", set())
        if key not in counted:
            counted.add(key)
            field = f"{prefix}_{'success' if status == 'SUCCESS' else 'failed'}_count"
            state[field] = state.get(field, 0) + 1

    def run_result(self, indexes=None):
        with self._lock:
            selected = set(indexes) if indexes is not None else set(self._states)
            for index, state in self._states.items():
                if index not in selected:
                    continue
                if state["status"] in {"DIE", "ERROR", "CHECKPOINT", "CHECKING"}:
                    return "COMPLETED_WITH_ERRORS"
                if any(task["status"] in {"FAILED", "ERROR", "RUNNING", "PENDING"}
                       for task in state.get("tasks", {}).values()):
                    return "COMPLETED_WITH_ERRORS"
            return "COMPLETED"

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


@dataclass(frozen=True, repr=False)
class RunConfig(Mapping):
    """Detached, recursively immutable values captured on the UI thread."""
    data: Mapping

    def __post_init__(self):
        def freeze(value):
            if isinstance(value, Mapping):
                return MappingProxyType({key: freeze(item) for key, item in value.items()})
            if isinstance(value, (list, tuple)):
                return tuple(freeze(item) for item in value)
            if isinstance(value, (set, frozenset)):
                return frozenset(freeze(item) for item in value)
            return value
        object.__setattr__(self, "data", freeze(self.data))

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


def consume_cleanup_result(task):
    if not task.cancelled():
        task.exception()


async def close_browser_resources(context=None, browser=None, page=None, close_timeout=5):
    """Bound each close independently; cancellation cannot skip remaining resources."""
    async def close_all():
        errors = []
        for resource in (page, context, browser):
            if resource is None:
                continue
            try:
                task = asyncio.ensure_future(resource.close())
                done, _ = await asyncio.wait({task}, timeout=close_timeout)
                if not done:
                    task.cancel()
                    task.add_done_callback(consume_cleanup_result)
                    errors.append(TimeoutError("Browser resource close timed out"))
                    continue
                task.result()
            except asyncio.CancelledError:
                errors.append(RuntimeError("Browser resource close was cancelled"))
            except Exception as exc:
                errors.append(exc)
        return errors

    cleanup = asyncio.create_task(close_all())
    cancelled = False
    while True:
        try:
            errors = await asyncio.shield(cleanup)
            break
        except asyncio.CancelledError:
            if cleanup.cancelled():
                raise
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError()
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

@dataclass(frozen=True, repr=False)
class AccountRecord:
    uid: str
    password: str
    twofa: str
    cookie: str
    token: str
    raw_line: str
    proxy: str = ""
    email: str = ""
    locale: str = "AUTO"
    country: str = ""
    timezone: str = ""
    import_fields: tuple = ()

    def __post_init__(self):
        if not self.uid.strip() or not normalize_cookie_input(self.cookie):
            raise ValueError("Account requires a UID and a recognized cookie.")
        if any("|" in value or "\n" in value or "\r" in value
               for value in (self.uid, self.password, self.twofa, self.cookie, self.token)):
            raise ValueError("Account fields cannot contain the canonical separator or newlines.")

    @property
    def canonical_line(self):
        return "|".join((self.uid, self.password, self.twofa, self.cookie, self.token))

    def to_account_dict(self):
        return {
            "account_record": self, "canonical_line": self.canonical_line,
            "raw_line": self.raw_line, "source_line": self.canonical_line,
            "fields": self.canonical_line.split("|"),
            "import_fields": list(self.import_fields), "unknown_fields": [],
            "type": "COOKIE", "uid": self.uid, "name": self.uid,
            "password": self.password, "pwd": self.password, "2fa": self.twofa,
            "cookie": self.cookie, "data": self.cookie, "token": self.token,
            "proxy": self.proxy, "email": self.email, "locale": self.locale,
            "country": self.country, "timezone": self.timezone,
        }


def parse_canonical_account_line(line):
    """Read exactly five positional slots; never infer password, 2FA or token."""
    raw = str(line or "")
    fields = normalize_account_source_line(raw).split("|")
    if (len(fields) != 5 or not fields[0].strip()
            or fields[0].upper() in {"FACEBOOK", "COOKIE", "TOKEN"}):
        return None
    cookie = normalize_cookie_input(fields[3])
    if not cookie:
        return None
    try:
        return AccountRecord(fields[0].strip(), fields[1], fields[2], cookie,
                             fields[4], raw, import_fields=tuple(fields))
    except ValueError:
        return None


def parse_legacy_account_line(raw_line: str, idx: int = 1):
    """Compatibility detection for IMPORT only; callers normalize the result."""
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
            start_index = 3
            if len(fields) > 4 and normalize_cookie_input(fields[4]):
                two_factor = fields[3]
                start_index = 4
        elif prefix == "TOKEN":
            token = fields[1] if len(fields) > 1 else ""

    # Known UID/password layouts take precedence over length-based detection.
    if prefix not in {"FACEBOOK", "COOKIE", "TOKEN"} and len(fields) >= 3:
        cookie_indexes = [i for i, field in enumerate(fields)
                          if i >= 2 and normalize_cookie_input(field)]
        if fields[0].isdigit() and len(fields[0]) >= 5 and cookie_indexes and cookie_indexes[0] >= 2:
            uid, password = fields[0], normalized_line.split("|")[1]
            start_index = 2
            if (cookie_indexes[0] >= 3 and not fields[2].startswith(("EAAB", "EAAA"))
                    and "@" not in fields[2] and not parse_proxy(fields[2])):
                two_factor = fields[2]
                start_index = 3

    # Preserve recognized tokens before considering an opaque positional token.
    if not token:
        token = next((field for field in fields[start_index:]
                      if not normalize_cookie_input(field) and (
                          field.startswith(("EAAB", "EAAA"))
                          or len(field) > 50 and "." in field and "@" not in field)), "")
    if not token and uid:
        cookie_index = next((i for i in range(start_index, len(fields))
                             if normalize_cookie_input(fields[i])), -1)
        positional_token = cookie_index in {2, 3} or (
            cookie_index == 5 and not fields[3] and not fields[4]
        ) or (prefix == "FACEBOOK" and cookie_index == 4)
        if positional_token and cookie_index + 1 < len(fields):
            candidate = fields[cookie_index + 1]
            if candidate and "@" not in candidate and not parse_proxy(candidate):
                token = candidate

    # Tự động quét và phân loại từng trường dữ liệu dựa vào đặc thù nhận diện
    for index, field in enumerate(fields):
        if index < start_index or not field:
            continue
        norm_cookie = normalize_cookie_input(field)
        if norm_cookie and not cookie:
            cookie = field
            continue
        if token and field == token:
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



def import_account_record(raw_line, idx=1):
    """Import canonical or supported legacy data, retaining original provenance."""
    canonical = parse_canonical_account_line(raw_line)
    if canonical and not parse_proxy(canonical.token):
        return canonical
    parsed = parse_legacy_account_line(raw_line, idx)
    if not parsed:
        return None
    try:
        return AccountRecord(
            parsed["uid"], parsed["password"], parsed["2fa"],
            normalize_cookie_input(parsed["cookie"]), parsed["token"], str(raw_line),
            proxy=parsed["proxy"], email=parsed["email"],
            import_fields=tuple(normalize_account_source_line(raw_line).split("|")),
        )
    except ValueError:
        return None


def parse_any_account_line(raw_line: str, idx: int = 1):
    """Compatibility entry point for import; returns canonical account data."""
    record = import_account_record(raw_line, idx)
    return record.to_account_dict() if record else None


def runtime_account_record(account):
    """Accept only a normalized model or its canonical serialization at runtime."""
    if isinstance(account, AccountRecord):
        return account
    account = account or {}
    record = account.get("account_record")
    if isinstance(record, AccountRecord):
        return record
    return parse_canonical_account_line(account.get("canonical_line", ""))


def serialize_account_line(account):
    """Serialize the internal model without changing the cookie-only UI view."""
    record = runtime_account_record(account)
    if record is None:
        raise ValueError("Account must be normalized before serialization.")
    return record.canonical_line


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
    """Cookie import dialog with internal provenance for full account inputs."""
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

        tk.Label(frame_top, text="COOKIE FACEBOOK", font=("Segoe UI", 13, "bold"), bg="#131C2E", fg="#38BDF8").pack(anchor="w")

        # Khung nhập dữ liệu
        frame_txt = tk.Frame(self, bg="#131C2E", padx=10, pady=10, highlightbackground="#1E293B", highlightthickness=1)
        frame_txt.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(frame_txt, text="Cookie (mỗi dòng một tài khoản):", font=("Segoe UI", 12), bg="#131C2E", fg="#94A3B8").pack(anchor="w", pady=(0, 5))
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
        raw_data = self.txt_input.get("1.0", "end")
        if not raw_data.strip():
            messagebox.showwarning("Thông báo", "Vui lòng nhập ít nhất 1 dòng dữ liệu!", parent=self)
            return

        lines = [line for line in raw_data.splitlines() if line.strip()]
        parsed_accounts = []

        for idx, line in enumerate(lines, 1):
            parsed = parse_any_account_line(line, idx)
            if parsed:
                parsed_accounts.append(parsed)

        self.on_import_callback(parsed_accounts)
        messagebox.showinfo("Thành công", f"Đã nạp thành công {len(parsed_accounts)} tài khoản vào bảng!", parent=self)
        self.destroy()
# [ĐOẠN TRƯỚC:]
class MainToolApp:
    def auto_format_cookie_numbers(self, event=None):
        """Refresh cookie input and account-table numbering."""
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
        self.run_status = None
        self.run_account_indexes = None
        self.run_thread = None
        self.worker_loop = None
        self.worker_tasks = []
        self.worker_root_task = None
        self._run_generation = 0
        self._finished_run_generation = None
        self._cancel_requested_generation = None
        self._ui_run_context = contextvars.ContextVar("ui_run_context", default=None)
        self.proxy_api_lock = None
        self.run_config = {}
        self._account_import_records = {}
        self.ui_queue = queue.Queue()
        self.close_requested = False
        history = AccountHistoryStore(output_path("account_history.db"))
        if not history.page_identity_bootstrapped():
            identities = set()
            csv_path = output_path("created_pages.csv")
            if os.path.exists(csv_path):
                with open(csv_path, newline="", encoding="utf-8-sig") as stream:
                    for record in csv.DictReader(stream):
                        identities.update(page_identity_keys(record.get("page_url"), record.get("page_id")))
            history.bootstrap_page_identities(identities)
        self.account_states = AccountStateStore(history)
        self.module_breaker = ModuleCircuitBreaker()
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
            context = getattr(self, "_ui_run_context", None)
            generation = context.get() if context is not None else None
            if generation is None:
                self.ui_queue.put(callback)
            else:
                def current_run_callback():
                    if generation == getattr(self, "_run_generation", 0):
                        callback()
                self.ui_queue.put(current_run_callback)

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

    @staticmethod
    def activity_duration_seconds(value, label):
        try:
            seconds = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: thời gian phải là số nguyên từ 0 đến 86400 giây.") from exc
        if not 0 <= seconds <= 86400:
            raise ValueError(f"{label}: thời gian phải từ 0 đến 86400 giây.")
        return seconds

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

        values = {
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
            "warmup_seconds": self.activity_duration_seconds(self.ent_warmup_seconds.get(), "Feed đệm"),
            "notification_seconds": self.activity_duration_seconds(self.ent_notification_seconds.get(), "Thông báo"),
            "tele_token": self.ent_tele_token.get().strip(),
            "tele_chatid": self.ent_tele_chatid.get().strip(),
            "screen_width": self.root.winfo_screenwidth(),
            "screen_height": self.root.winfo_screenheight(),
            "modes": {key: bool(value.get()) for key, value in self.mode_vars.items()
                      if key in CORE_AUTOMATION_MODES},
            "options": {
                "warmup": bool(self.chk_warmup.get()),
                "check_notif": bool(self.chk_check_notif.get()),
            },
        }
        values["auto_headless"] = values["threads"] > 12 and not values["headless"]
        if values["auto_headless"]:
            values["headless"] = True
        # Bind proxies once before starting workers; preserve per-account API failures.
        selected = self.parse_range_string(values["selected_indexes"]) or checked_indexes
        proxy_errors = {}
        for index, account in parsed_accounts.items():
            if selected and index not in selected:
                continue
            proxy = resolve_account_proxy(account.get("proxy"), resolved_proxies, index)
            if values["proxy_mode"] == "rotating_api" and values["proxy_api"]:
                try:
                    proxy = fetch_proxy_from_api(values["proxy_api"])
                    if not proxy or not parse_proxy(proxy):
                        raise ValueError("API proxy không trả về proxy hợp lệ.")
                except Exception as exc:
                    proxy_errors[index] = f"{type(exc).__name__}: {exc}"
                    proxy = ""
            resolved_proxies[index] = proxy
        values["proxy_errors"] = proxy_errors
        values["proxy_snapshot_complete"] = True
        return RunConfig(values)

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
        tk.Label(f1_head, text="👤 1. HÀNG ĐỢI TÀI KHOẢN FACEBOOK", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f1_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_accounts_file).pack(side="right")

        tk.Label(card1, text="Cookie Facebook (mỗi dòng một tài khoản):", font=("Segoe UI", 12), fg="#64748B", bg="#131C2E").pack(anchor="w")
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
        paned_left.add(card3, minsize=245, height=280)

        f3_targets = tk.Frame(card3, bg="#131C2E")
        f3_targets.pack(side="bottom", fill="x")
        tk.Label(f3_targets, text="Đích kết bạn / Cấu hình Page:", font=("Segoe UI", 12), fg="#64748B", bg="#131C2E").pack(anchor="w", pady=(2, 1))
        self.txt_targets = scrolledtext.ScrolledText(f3_targets, height=2, bg="#070B14", fg="#E2E8F0", font=("Consolas", 11), insertbackground="#38BDF8", relief="solid", bd=1)
        self.txt_targets.pack(fill="x")

        f3_head = tk.Frame(card3, bg="#131C2E")
        f3_head.pack(fill="x", pady=(0, 2))
        tk.Label(f3_head, text="⚡ 3. CHỨC NĂNG TỰ ĐỘNG", font=("Segoe UI", 13, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        
        def toggle_all(val):
            for v in self.mode_vars.values(): v.set(val)

        f3_actions = tk.Frame(card3, bg="#131C2E")
        f3_actions.pack(fill="x", pady=(2, 4))
        tk.Button(f3_actions, text="Bỏ chọn hết", font=("Segoe UI", 11), bg="#1E293B", fg="#94A3B8", relief="flat", cursor="hand2", command=lambda: toggle_all(False)).pack(side="right", padx=2)
        tk.Button(f3_actions, text="Chọn tất cả", font=("Segoe UI", 11), bg="#1E293B", fg="#38BDF8", relief="flat", cursor="hand2", command=lambda: toggle_all(True)).pack(side="right", padx=2)
        f_modes_scroll = tk.Frame(card3, bg="#131C2E")
        f_modes_scroll.pack(fill="both", expand=True)
        self.modes_canvas = tk.Canvas(f_modes_scroll, bg="#131C2E", height=135, highlightthickness=0)
        modes_scrollbar = ttk.Scrollbar(f_modes_scroll, orient="vertical", command=self.modes_canvas.yview)
        modes_scrollbar.pack(side="right", fill="y")
        self.modes_canvas.pack(side="left", fill="both", expand=True)
        self.modes_canvas.configure(yscrollcommand=modes_scrollbar.set)
        f_modes_grid = tk.Frame(self.modes_canvas, bg="#131C2E")
        modes_window = self.modes_canvas.create_window((0, 0), window=f_modes_grid, anchor="nw")
        f_modes_grid.bind("<Configure>", lambda _event: self.modes_canvas.configure(scrollregion=self.modes_canvas.bbox("all")))
        mode_buttons = []

        def resize_modes(event):
            self.modes_canvas.itemconfigure(modes_window, width=event.width)
            columns = 2 if mode_buttons and event.width >= 2 * max(button.winfo_reqwidth() for button in mode_buttons) + 12 else 1
            for index, button in enumerate(mode_buttons):
                row, column = divmod(index, columns)
                button.grid_configure(row=row, column=column)

        self.modes_canvas.bind("<Configure>", resize_modes)

        def scroll_modes(event):
            self.modes_canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

        self.modes_canvas.bind("<MouseWheel>", scroll_modes)

        self.mode_vars = {}
        all_modes = [
            ("🚩 Tạo Page", "create_page"),
            ("🔍 Kết bạn theo tên", "by_name"),
            ("👥 Kết bạn trong nhóm", "by_group"),
            ("📇 Kết bạn theo UID", "by_uid"),
        ]

        for i, (text, val) in enumerate(all_modes):
            var = tk.BooleanVar(value=True if val == "by_name" else False)
            self.mode_vars[val] = var
            button = tk.Checkbutton(
                f_modes_grid, text=text, variable=var,
                font=("Segoe UI", 13), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14",
                activebackground="#131C2E", activeforeground="#38BDF8", cursor="hand2"
            )
            button.grid(row=i, column=0, sticky="w", padx=2, pady=2)
            button.bind("<MouseWheel>", scroll_modes)
            mode_buttons.append(button)

        # Log Card
        card_log = tk.Frame(paned_left, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_left.add(card_log, minsize=80, height=140)

        f_log_head = tk.Frame(card_log, bg="#131C2E")
        f_log_head.pack(fill="x", pady=(0, 2))
        self.lbl_log_scope = tk.Label(f_log_head, text="📜 NHẬT KÝ TỔNG", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E")
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
        self.txt_log = scrolledtext.ScrolledText(card_log, bg="#070B14", fg="#00FF66", font=("Consolas", 11), insertbackground="#38BDF8", relief="solid", bd=1, state="disabled")
        self.txt_log.pack(fill="both", expand=True)

        # ==================== CỘT PHẢI (THIẾT KẾ ĐẦY ĐỦ, CHUYÊN NGHIỆP) ====================
        paned_right = tk.PanedWindow(paned_main, orient="vertical", bg="#0A0E1A", bd=0, sashwidth=5, sashrelief="ridge")
        paned_main.add(paned_right, minsize=500)

        # R1: Card Danh sách Proxy
        card2 = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card2, minsize=190, height=210)

        f2_head = tk.Frame(card2, bg="#131C2E")
        f2_head.pack(fill="x", pady=(0, 2))
        tk.Label(f2_head, text="🌐 2. DANH SÁCH PROXY", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Button(f2_head, text="📁 Nhập từ file .txt", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#F8FAFC", relief="flat", padx=8, pady=1, cursor="hand2", command=self.import_proxies_file).pack(side="right")

        tk.Label(card2, text="Nhập danh sách Proxy (IP:Port hoặc IP:Port:User:Pass):", font=("Segoe UI", 8), fg="#64748B", bg="#131C2E").pack(anchor="w")
        self.txt_proxies = scrolledtext.ScrolledText(card2, height=3, bg="#070B14", fg="#E2E8F0", font=("Consolas", 11), insertbackground="#38BDF8", relief="solid", bd=1)

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
        self.txt_proxies.pack(fill="both", expand=True, pady=2)

        # R2: Trạng thái tài khoản và điều hướng theo đợt
        card_reg = tk.Frame(paned_right, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        paned_right.add(card_reg, minsize=105, height=190)

        f_reg_head = tk.Frame(card_reg, bg="#131C2E")
        f_reg_head.pack(fill="x", pady=(0, 3))
        tk.Label(f_reg_head, text="⇄ 4. TRẠNG THÁI TÀI KHOẢN", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        tk.Label(f_reg_head, text="Số tài khoản/đợt:", font=("Segoe UI", 10), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(12, 2))
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

        state_columns = ("stt", "account", "status", "task", "next_page", "pages", "friends", "action")
        self.account_state_tree = ttk.Treeview(card_reg, columns=state_columns, show="headings", selectmode="browse", height=5)
        self.account_state_tree.heading("stt", text="STT")
        self.account_state_tree.heading("account", text="Tài khoản")
        self.account_state_tree.heading("status", text="Trạng thái")
        self.account_state_tree.heading("task", text="Kết quả tác vụ")
        self.account_state_tree.heading("next_page", text="Page tiếp / Còn lại")
        self.account_state_tree.heading("pages", text="Page OK / Lỗi")
        self.account_state_tree.heading("friends", text="Bạn OK / Lỗi")
        self.account_state_tree.heading("action", text="Tác vụ hiện tại")
        self.account_state_tree.column("stt", width=40, anchor="center", stretch=False)
        self.account_state_tree.column("account", width=120, anchor="w")
        self.account_state_tree.column("status", width=105, anchor="center", stretch=False)
        self.account_state_tree.column("task", width=100, anchor="center", stretch=False)
        self.account_state_tree.column("next_page", width=155, anchor="center", stretch=False)
        self.account_state_tree.column("pages", width=105, anchor="center", stretch=False)
        self.account_state_tree.column("friends", width=105, anchor="center", stretch=False)
        self.account_state_tree.column("action", width=190, anchor="w")
        configure_account_table_style(self.style, self.account_state_tree)
        state_scroll = ttk.Scrollbar(card_reg, orient="horizontal", command=self.account_state_tree.xview)
        state_scroll.pack(side="bottom", fill="x")
        self.account_state_tree.configure(xscrollcommand=state_scroll.set)
        self.account_state_tree.bind("<<TreeviewSelect>>", self.on_account_state_selected)

        self.lbl_queue_info = tk.Label(
            card_reg,
            text="Tổng: 0 • LIVE: 0 • DIE: 0 • ERROR: 0",
            font=("Segoe UI", 10),
            fg="#CBD5E1",
            bg="#131C2E",
            anchor="w",
        )
        self.lbl_queue_info.pack(side="bottom", fill="x", pady=(3, 0))
        self.account_state_tree.pack(fill="both", expand=True)

        # Settings can scroll; run controls stay visible below them.
        f_bottom_right = tk.Frame(paned_right, bg="#0A0E1A")
        paned_right.add(f_bottom_right, minsize=205, height=360)
        f_run_controls = tk.Frame(f_bottom_right, bg="#0A0E1A")
        f_run_controls.pack(side="bottom", fill="x")
        f_settings_scroll = tk.Frame(f_bottom_right, bg="#131C2E")
        f_settings_scroll.pack(fill="both", expand=True, pady=(0, 4))
        self.settings_canvas = tk.Canvas(f_settings_scroll, bg="#131C2E", highlightthickness=0)
        settings_scroll = ttk.Scrollbar(f_settings_scroll, orient="vertical", command=self.settings_canvas.yview)
        settings_scroll.pack(side="right", fill="y")
        self.settings_canvas.pack(side="left", fill="both", expand=True)
        self.settings_canvas.configure(yscrollcommand=settings_scroll.set)
        f_settings = tk.Frame(self.settings_canvas, bg="#131C2E")
        settings_window = self.settings_canvas.create_window((0, 0), window=f_settings, anchor="nw")
        f_settings.bind("<Configure>", lambda _event: self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox("all")))
        self.settings_canvas.bind("<Configure>", lambda event: self.settings_canvas.itemconfigure(settings_window, width=event.width))

        card4 = tk.Frame(f_settings, bg="#131C2E", padx=12, pady=8)
        card4.pack(fill="x")
        tk.Label(card4, text="🛡️ 5. HIỆU NĂNG & ĐIỀU TIẾT", font=("Segoe UI", 13, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 4))

        f4_sys = tk.Frame(card4, bg="#131C2E")
        f4_sys.pack(fill="x", pady=2)
        tk.Label(f4_sys, text="Trình duyệt đồng thời:", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_threads = tk.Spinbox(f4_sys, from_=1, to=20, width=3, font=("Segoe UI", 12, "bold"), bg="#070B14", fg="#38BDF8", justify="center", relief="solid", bd=1)
        self.ent_threads.delete(0, "end")
        self.ent_threads.insert(0, "6")
        self.ent_threads.pack(side="left", padx=4)

        self.chk_headless = tk.BooleanVar(value=False)
        self.chk_warmup = tk.BooleanVar(value=True)
        self.chk_check_notif = tk.BooleanVar(value=True)
        tk.Checkbutton(f4_sys, text="Chạy ẩn", variable=self.chk_headless, font=("Segoe UI", 13), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left", padx=8)

        for label, variable, attribute, default in (
            ("Lướt Feed đệm", self.chk_warmup, "ent_warmup_seconds", "30"),
            ("Xem thông báo", self.chk_check_notif, "ent_notification_seconds", "3"),
        ):
            row = tk.Frame(card4, bg="#131C2E")
            row.pack(fill="x", pady=3)
            tk.Checkbutton(row, text=label, variable=variable, font=("Segoe UI", 13), fg="#E2E8F0", bg="#131C2E", selectcolor="#070B14", cursor="hand2").pack(side="left")
            entry = tk.Spinbox(row, from_=0, to=86400, width=5, font=("Segoe UI", 13), bg="#070B14", fg="#38BDF8", justify="center", relief="solid", bd=1)
            entry.delete(0, "end")
            entry.insert(0, default)
            entry.pack(side="left", padx=8)
            setattr(self, attribute, entry)
            tk.Label(row, text="giây", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")

        f4_tele = tk.Frame(card4, bg="#131C2E")
        f4_tele.pack(fill="x", pady=(2, 0))
        tk.Label(f4_tele, text="Telegram Token:", font=("Segoe UI", 10), fg="#94A3B8", bg="#131C2E").pack(side="left")
        self.ent_tele_token = tk.Entry(f4_tele, width=16, font=("Segoe UI", 10), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_tele_token.pack(side="left", padx=2)

        tk.Label(f4_tele, text="Chat ID:", font=("Segoe UI", 10), fg="#94A3B8", bg="#131C2E").pack(side="left", padx=(4, 2))
        self.ent_tele_chatid = tk.Entry(f4_tele, width=10, font=("Segoe UI", 10), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_tele_chatid.pack(side="left")

        card5 = tk.Frame(f_settings, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=12, pady=8)
        card5.pack(fill="x", pady=(0, 4))

        tk.Label(card5, text="⚙️ 6. THÔNG SỐ PAGE & KẾT BẠN", font=("Segoe UI", 13, "bold"), fg="#38BDF8", bg="#131C2E").pack(anchor="w", pady=(0, 4))

        f5_cfg = tk.Frame(card5, bg="#131C2E")
        f5_cfg.pack(fill="x", pady=3)
        tk.Label(f5_cfg, text="Bạn/nick:", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_target = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_target.insert(0, "25")
        self.ent_target.pack(side="left", padx=4)

        tk.Label(f5_cfg, text="Delay kết bạn (s):", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(12, 2))
        self.ent_min_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_min_delay.insert(0, "25")
        self.ent_min_delay.pack(side="left", padx=2)
        tk.Label(f5_cfg, text="-", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_delay = tk.Entry(f5_cfg, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_max_delay.insert(0, "35")
        self.ent_max_delay.pack(side="left", padx=2)

        f5_page = tk.Frame(card5, bg="#131C2E")
        f5_page.pack(fill="x", pady=3)
        tk.Label(f5_page, text="Page/nick:", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_page_target = tk.Entry(f5_page, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_page_target.insert(0, "5")
        self.ent_page_target.pack(side="left", padx=2)

        tk.Label(f5_page, text="Delay Page (s):", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left", padx=(12, 2))
        self.ent_min_page_delay = tk.Entry(f5_page, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_min_page_delay.insert(0, "60")
        self.ent_min_page_delay.pack(side="left", padx=2)
        tk.Label(f5_page, text="-", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_page_delay = tk.Entry(f5_page, width=4, font=("Segoe UI", 12), bg="#070B14", fg="#FFFFFF", relief="solid", bd=1)
        self.ent_max_page_delay.insert(0, "120")
        self.ent_max_page_delay.pack(side="left", padx=2)

        f5_workers = tk.Frame(card5, bg="#131C2E")
        f5_workers.pack(fill="x", pady=3)
        tk.Label(f5_workers, text="Luồng tạo Page:", font=("Segoe UI", 12), fg="#E2E8F0", bg="#131C2E").pack(side="left")
        self.ent_max_create_page_workers = tk.Entry(f5_workers, width=3, font=("Segoe UI", 12), bg="#070B14", fg="#38BDF8", relief="solid", bd=1)
        self.ent_max_create_page_workers.insert(0, "3")
        self.ent_max_create_page_workers.pack(side="left", padx=2)

        def scroll_settings(event):
            self.settings_canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

        def bind_settings_scroll(widget):
            widget.bind("<MouseWheel>", scroll_settings)
            for child in widget.winfo_children():
                bind_settings_scroll(child)

        self.settings_canvas.bind("<MouseWheel>", scroll_settings)
        bind_settings_scroll(f_settings)
        # Ô nhập STT rải rác hoặc dải số (ví dụ: 1, 3, 5-8)
        f_filter_idx = tk.Frame(f_run_controls, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, padx=6, pady=3)
        f_filter_idx.pack(fill="x", pady=(0, 4))
        tk.Label(f_filter_idx, text="🎯 Chọn STT chạy:", font=("Segoe UI", 11, "bold"), fg="#38BDF8", bg="#131C2E").pack(side="left")
        self.ent_selected_indexes = tk.Entry(f_filter_idx, font=("Consolas", 11), bg="#070B14", fg="#00FF66", relief="solid", bd=1)
        self.ent_selected_indexes.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(f_filter_idx, text="(VD: 1, 3, 5-9)", font=("Segoe UI", 7), fg="#64748B", bg="#131C2E").pack(side="right")

        f_action_btns = tk.Frame(f_run_controls, bg="#0A0E1A")
        f_action_btns.pack(fill="x", pady=(0, 4))
        self.btn_start = tk.Button(f_action_btns, text="▶ BẮT ĐẦU CHẠY", font=("Segoe UI", 13, "bold"), bg="#10B981", fg="#FFFFFF", relief="flat", cursor="hand2", command=self.start_thread)
        self.btn_start.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.btn_stop = tk.Button(f_action_btns, text="⏹ DỪNG LẠI", font=("Segoe UI", 13, "bold"), bg="#EF4444", fg="#FFFFFF", relief="flat", cursor="hand2", state="disabled", command=self.stop_bot)
        self.btn_stop.pack(side="right", fill="both", expand=True, padx=(4, 0))

        f_stats = tk.Frame(f_run_controls, bg="#0A0E1A")
        f_stats.pack(fill="both", expand=True)
        for i in range(4): f_stats.columnconfigure(i, weight=1)

        def make_stat_box(parent, title, val, col_idx, color):
            bx = tk.Frame(parent, bg="#131C2E", highlightbackground="#1E293B", highlightthickness=1, pady=3)
            bx.grid(row=0, column=col_idx, sticky="nsew", padx=2)
            lbl_v = tk.Label(bx, text=val, font=("Segoe UI", 13, "bold"), fg=color, bg="#131C2E")
            lbl_v.pack(expand=True)
            tk.Label(bx, text=title, font=("Segoe UI", 10), fg="#94A3B8", bg="#131C2E").pack(pady=(0, 1))
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

        columns = ACCOUNT_MANAGEMENT_COLUMNS
        self.tree = ttk.Treeview(frame_tree, columns=columns, show="headings", selectmode="extended")
        self.tree.tag_configure("empty", foreground="#8EA3B5")
        configure_account_table_style(self.style, self.tree)
        self.tree.tag_configure("RUNNING", **ACCOUNT_TABLE_PALETTE["RUNNING"])

        headings = ("[✔]", "STT", "UID", "PASSWORD", "2FA", "COOKIE", "TOKEN", "LOGIN MODE",
                    "STATUS", "ACTION", "PAGE", "FRIEND", "LAST UPDATE")
        widths = (45, 45, 140, 110, 95, 85, 85, 150, 115, 300, 95, 95, 170)
        for column, title, width in zip(columns, headings, widths):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=width, anchor="w" if column == "action" else "center", stretch=column == "action")

        # Context Menu
        self.tree_menu = tk.Menu(self.tree, tearoff=0, bg="#131C2E", fg="#FFFFFF")
        self._management_menu_account = None
        for label, mode in (
            ("Copy UID", "uid"), ("Copy Password", "password"), ("Copy 2FA", "2fa"),
            ("Copy Cookie", "cookie"), ("Copy Token", "token"),
            ("Copy UID|Password", "uid|pass"), ("Copy UID|Password|2FA", "uid|pass|2fa"),
            ("Copy canonical line", "canonical"), ("Copy raw line", "raw"),
        ):
            self.tree_menu.add_command(label=label, command=lambda mode=mode: self.copy_tree_data(mode, self._management_menu_account))
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Mở Chrome kiểm tra", command=lambda: self.open_account_inspector(self._management_menu_account))
        self.tree_menu.add_command(label="Xem log", command=lambda: self.show_management_account_logs(self._management_menu_account))
        self.tree_menu.add_command(label="Xem lịch sử", command=lambda: self.show_management_account_logs(self._management_menu_account, history=True))

        self.tree.bind("<Button-3>", self.show_account_context_menu)
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

    def management_account_for_item(self, item):
        values = self.tree.item(item, "values")
        if len(values) < 3 or not str(values[1]).isdigit():
            return None
        state = self.account_states.get(int(values[1]))
        return state if state and str(state.get("uid", "")) == str(values[2]) else None

    def show_account_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        self._management_menu_account = self.management_account_for_item(item) if item else None
        if self._management_menu_account is None:
            return
        self.tree.selection_set(item)
        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

    def copy_tree_data(self, mode, account=None):
        accounts = [account] if account is not None else [
            self.management_account_for_item(item) for item in self.tree.selection()
        ]
        result = []
        for parsed in accounts:
            if not parsed: continue
            
            if mode == "uid":
                result.append(parsed["uid"])
            elif mode == "password":
                result.append(parsed["password"])
            elif mode in {"2fa", "cookie", "token"}:
                result.append(parsed.get(mode, ""))
            elif mode == "uid|pass":
                result.append(f"{parsed['uid']}|{parsed['password']}")
            elif mode == "uid|pass|2fa":
                result.append(f"{parsed['uid']}|{parsed['password']}|{parsed['2fa']}")
            elif mode == "raw":
                result.append(parsed["raw_line"])
            elif mode == "canonical":
                record = runtime_account_record(parsed)
                if record is not None:
                    result.append(record.canonical_line)
                
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(result))
            self.log(f"[+] Đã copy {len(result)} dòng (Chế độ: {mode})")

    def show_management_account_logs(self, account, history=False):
        if account is None:
            return
        key = history_account_id(account)
        current = next((self.account_states.get(index) for index in self.account_states.indexes()
                        if history_account_id(self.account_states.get(index)) == key), account)
        if history:
            saved = self.account_states.history.load(account) if self.account_states.history else None
            lines = saved["logs"] if saved else current.get("history_logs", [])
        else:
            lines = current.get("logs", [])
        palette = ACCOUNT_TABLE_PALETTE
        window = tk.Toplevel(self.root)
        window.title(f"{'Lịch sử' if history else 'Nhật ký'} - {account.get('uid', '')}")
        window.geometry("900x520")
        text = scrolledtext.ScrolledText(window, wrap="word", bg=palette["background"], fg=palette["foreground"],
                                        insertbackground=palette["foreground"], font=("Consolas", 10))
        text.pack(fill="both", expand=True)
        text.insert("1.0", "\n".join(redact_history_text(line, account) for line in lines))
        text.configure(state="disabled")

    def refresh_management_account_row(self, index):
        if not hasattr(self, "tree") or not self.tree.exists(str(index)):
            return
        state = self.account_states.get(index)
        if state is None:
            return
        previous = self.tree.item(str(index), "values")
        tag = state["status"]
        if tag == "LIVE" and task_result_status(state.get("tasks", {})) == "RUNNING":
            tag = "RUNNING"
        self.tree.item(str(index), values=management_account_values(state, bool(previous and previous[0] == "[✔]")), tags=(tag,))

    def open_create_page_results_dialog(self):
        window = getattr(self, "create_page_results_window", None)
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            self.refresh_create_page_results_dialog()
            return
        palette = ACCOUNT_TABLE_PALETTE
        window = tk.Toplevel(self.root)
        self.create_page_results_window = window
        window.title("Create Page - Result Center")
        width = max(960, min(1500, self.root.winfo_screenwidth() - 80))
        height = max(500, min(760, self.root.winfo_screenheight() - 100))
        window.geometry(f"{width}x{height}")
        window.minsize(960, 500)
        window.configure(bg=palette["background"])
        header = tk.Frame(window, bg=palette["header_background"], padx=14, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="CREATE PAGE · RESULT CENTER", font=("Segoe UI", 13, "bold"),
                 bg=palette["header_background"], fg=palette["header_foreground"]).pack(anchor="w")
        summary = tk.Frame(header, bg=palette["header_background"])
        summary.pack(fill="x", pady=(10, 0))
        self.result_center_summary_labels = {}
        for position, key in enumerate(SUMMARY_KEYS):
            summary.grid_columnconfigure(position, weight=1)
            color_key = {"RUNNING": "CHECKING", "PAGE SUCCESS": "LIVE", "PAGE FAILED": "ERROR"}.get(key, key)
            colors = ACCOUNT_STATUS_PALETTE.get(color_key, palette)
            block = tk.Frame(summary, bg=colors["background"], padx=5, pady=5)
            block.grid(row=0, column=position, sticky="nsew", padx=2)
            tk.Label(block, text=key, font=("Segoe UI", 8, "bold"),
                     bg=colors["background"], fg=colors["foreground"]).pack()
            label = tk.Label(block, text="0", font=("Segoe UI", 16, "bold"),
                             bg=colors["background"], fg=colors["foreground"])
            label.pack()
            self.result_center_summary_labels[key] = label
                # Ép riêng Notebook Result Center dùng element của theme clam
        # để Windows không tự vẽ nền tab màu trắng.
        if "ResultNotebook.tab" not in self.style.element_names():
            self.style.element_create("ResultNotebook.tab", "from", "clam", "Notebook.tab")
            self.style.element_create("ResultNotebook.padding", "from", "clam", "Notebook.padding")
            self.style.element_create("ResultNotebook.focus", "from", "clam", "Notebook.focus")
            self.style.element_create("ResultNotebook.label", "from", "clam", "Notebook.label")
            self.style.element_create("ResultNotebook.client", "from", "clam", "Notebook.client")

        self.style.layout("Result.TNotebook", [
            ("ResultNotebook.client", {"sticky": "nswe"})
        ])

        self.style.layout("Result.TNotebook.Tab", [
            ("ResultNotebook.tab", {
                "sticky": "nswe",
                "children": [
                    ("ResultNotebook.padding", {
                        "side": "top",
                        "sticky": "nswe",
                        "children": [
                            ("ResultNotebook.focus", {
                                "side": "top",
                                "sticky": "nswe",
                                "children": [
                                    ("ResultNotebook.label", {"side": "top", "sticky": ""})
                                ]
                            })
                        ]
                    })
                ]
            })
        ])

        self.style.configure(
            "Result.TNotebook",
            background="#19232C",
            borderwidth=0
        )

        self.style.configure(
            "Result.TNotebook.Tab",
            background="#24323D",
            foreground="#D7E3F0",
            font=("Segoe UI", 9, "bold"),
            padding=(16, 9),
            borderwidth=0,
            lightcolor="#24323D",
            darkcolor="#24323D",
            bordercolor="#19232C"
        )

        self.style.map(
            "Result.TNotebook.Tab",
            background=[
                ("selected", "#0EA5E9"),
                ("active", "#334155")
            ],
            foreground=[
                ("selected", "#FFFFFF"),
                ("active", "#FFFFFF")
            ]
        )
        notebook = ttk.Notebook(window, style="Result.TNotebook")
        notebook.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        self.create_page_results_notebook = notebook
        self.create_page_result_trees = {}
        widths = (55, 150, 120, 150, 125, 120, 140, 140, 120, 300, 220, 150, 300, 170)
        for key, title in RESULT_TABS:
            frame = tk.Frame(notebook, bg=palette["background"])
            notebook.add(frame, text=title)
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            tree = ttk.Treeview(frame, columns=RESULT_COLUMNS, show="headings", selectmode="browse")
            configure_account_table_style(self.style, tree)
            tree.tag_configure("RUNNING", **palette["RUNNING"])
            tree.tag_configure("TASK_FAILED", **ACCOUNT_STATUS_PALETTE["ERROR"])
            for column, heading, column_width in zip(RESULT_COLUMNS, RESULT_HEADERS, widths):
                tree.heading(column, text=heading)
                tree.column(column, width=column_width, minwidth=column_width,
                            anchor="w" if column in {"action", "reason", "page_name"} else "center",
                            stretch=column in {"action", "reason"})
            vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vertical.grid(row=0, column=1, sticky="ns")
            horizontal.grid(row=1, column=0, sticky="ew")
            tree.bind("<Button-3>", lambda event, tree=tree: self.show_result_center_context_menu(event, tree))
            self.create_page_result_trees[key] = tree
        self.result_center_menu = tk.Menu(window, tearoff=0, bg=palette["header_background"], fg=palette["foreground"])
        self._result_center_menu_account = None
        self._result_center_menu_values = ()
        self._result_center_menu_page_url = ""
        for label, mode in (("Copy UID", "uid"), ("Copy canonical account", "canonical"),
                            ("Copy Page ID", "page_id"), ("Copy Page URL", "page_url"),
                            ("Copy reason", "reason"), ("Copy result row", "row")):
            self.result_center_menu.add_command(label=label, command=lambda mode=mode: self.copy_result_center_data(mode))
        self.result_center_menu.add_separator()
        self.result_center_menu.add_command(label="Mở Chrome kiểm tra",
            command=lambda: self.open_account_inspector(self._result_center_menu_account))
        self.result_center_menu.add_command(label="Xem log account",
            command=lambda: self.show_management_account_logs(self._result_center_menu_account))
        footer = tk.Frame(window, bg=palette["background"], padx=12, pady=10)
        footer.pack(fill="x")

        self.lbl_create_page_result_summary = tk.Label(
            footer, text="", font=("Segoe UI", 9),
            bg=palette["background"], fg=palette["foreground"]
        )
        self.lbl_create_page_result_summary.pack(side="left")

        tk.Button(
            footer, text="Xuất Excel",
            command=self.export_create_page_results_excel,
            bg="#16A34A", fg="#FFFFFF",
            activebackground="#15803D", activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padx=14, pady=6, relief="flat", bd=0, cursor="hand2"
        ).pack(side="right", padx=4)

        tk.Button(
            footer, text="Xuất CSV",
            command=self.export_result_center_csv,
            bg="#2563EB", fg="#FFFFFF",
            activebackground="#1D4ED8", activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padx=14, pady=6, relief="flat", bd=0, cursor="hand2"
        ).pack(side="right", padx=4)

        notebook.bind("<<NotebookTabChanged>>", lambda _event: self.update_result_center_footer())

        def close():
            window.destroy()
            self.create_page_results_window = None
            self.create_page_result_trees = {}
            self.result_center_summary_labels = {}
            self._result_center_menu_account = None
        window.protocol("WM_DELETE_WINDOW", close)
        self.refresh_create_page_results_dialog()

    def result_center_accounts(self):
        # Project the existing live store and its SQLite history, including removed input rows.
        states = [self.account_states.get(index) for index in self.account_states.indexes()]
        accounts = {history_account_id(state): state for state in states if state is not None}
        config = getattr(self, "run_config", {})
        legacy = {}
        if hasattr(self, "create_page_result_lock"):
            with self.create_page_result_lock:
                for category, records in self.create_page_account_results.items():
                    for record in records.values():
                        legacy[history_account_id(record)] = (category, record)
        for index, source in config.get("parsed_accounts", {}).items():
            key = history_account_id(source)
            if key in accounts:
                continue
            saved = self.account_states.history.load(source, include_logs=False) if self.account_states.history else None
            if saved:
                accounts[key] = {**source, "stt": int(index), "status": saved["last_status"],
                    "current_action": saved["last_action"], "last_task_result": saved["last_task_result"],
                    "last_error": saved.get("last_error"), "last_update": saved.get("last_update"),
                    "login_mode": saved.get("login_mode"), "tasks": saved["tasks"],
                    **{field: int(saved.get(field) or 0) for field in COUNTER_FIELDS}}
            elif key in legacy:
                category, record = legacy[key]
                accounts[key] = {**source, "stt": int(index),
                    "status": {"completed": "LIVE", "die": "DIE", "checkpoint": "CHECKPOINT"}[category],
                    "page_success_count": record["created_count"], "last_error": record["reason"],
                    "current_action": record["reason"], "last_update": record["time"],
                    "last_task_result": "SUCCESS" if category == "completed" else "SKIPPED"}
        return sorted(accounts.values(), key=lambda state: (int(state["stt"]), history_account_id(state)))

    @staticmethod
    def result_center_item_id(account):
        return "result_" + hashlib.sha256(history_account_id(account).encode()).hexdigest()

    def result_center_active_tab(self):
        notebook = self.create_page_results_notebook
        return RESULT_TABS[notebook.index(notebook.select())][0]

    def update_result_center_footer(self):
        window = getattr(self, "create_page_results_window", None)
        if window is None or not window.winfo_exists():
            return
        tree = self.create_page_result_trees.get(self.result_center_active_tab())
        if tree is not None:
            self.lbl_create_page_result_summary.config(text=f"{len(tree.get_children())} tài khoản")

    def refresh_create_page_results_dialog(self, index=None):
        window = getattr(self, "create_page_results_window", None)
        if window is None or not window.winfo_exists():
            return
        accounts = self.result_center_accounts()
        changed = self.account_states.get(index) if index is not None else None
        rows = [changed] if changed else accounts
        for key, tree in self.create_page_result_trees.items():
            if index is None or changed is None:
                visible = {self.result_center_item_id(state) for state in rows if result_matches(state, key)}
                for item in tree.get_children():
                    if item not in visible:
                        tree.delete(item)
            for state in rows:
                item = self.result_center_item_id(state)
                if not result_matches(state, key):
                    if tree.exists(item):
                        tree.delete(item)
                    continue
                values = result_values(state)
                tag = state["status"]
                if tag not in {"DIE", "ERROR", "CHECKPOINT", "CHECKING"}:
                    if values[8] in {"FAILED", "ERROR"}:
                        tag = "TASK_FAILED"
                    elif values[8] == "RUNNING":
                        tag = "RUNNING"
                if tree.exists(item):
                    tree.item(item, values=values, tags=(tag,))
                else:
                    tree.insert("", "end", iid=item, values=values, tags=(tag,))
        for key, value in result_summary(accounts).items():
            self.result_center_summary_labels[key].config(text=str(value))
        self.update_result_center_footer()

    def show_result_center_context_menu(self, event, tree):
        item = tree.identify_row(event.y)
        account = next((state for state in self.result_center_accounts()
                        if self.result_center_item_id(state) == item), None)
        self._result_center_menu_account = None
        if account is None:
            return
        values = tuple(tree.item(item, "values"))
        if len(values) != len(RESULT_COLUMNS) or str(account.get("uid") or account.get("account_id")) != str(values[1]):
            return
        self._result_center_menu_account = account
        self._result_center_menu_values = values
        outcomes = account.get("tasks", {}).get("CREATE_PAGE", {}).get("outcomes", [])
        self._result_center_menu_page_url = next((str(outcome.get("page_url") or "") for outcome in reversed(outcomes)
            if isinstance(outcome, dict) and str(outcome.get("page_id") or "") == str(values[11])
            and redact_history_text(outcome.get("page_name"), account) == str(values[10])), "")
        tree.selection_set(item)
        try:
            self.result_center_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.result_center_menu.grab_release()

    def copy_result_center_data(self, mode):
        account = self._result_center_menu_account
        if account is None:
            return
        values = self._result_center_menu_values
        if mode == "canonical":
            self.copy_tree_data("canonical", account)
            return
        data = {"uid": values[1], "page_id": values[11], "page_url": self._result_center_menu_page_url,
                "reason": values[12], "row": "\t".join(map(str, values))}[mode]
        self.root.clipboard_clear()
        self.root.clipboard_append(str(data))

    def export_create_page_results_excel(self, result_type=None):
        self.export_result_center("xlsx", result_type)

    def export_result_center_csv(self):
        self.export_result_center("csv")

    def export_result_center(self, extension, result_type=None):
        key = result_type or self.result_center_active_tab()
        accounts = [state for state in self.result_center_accounts() if result_matches(state, key)]
        if not accounts:
            messagebox.showwarning("Xuất kết quả", "Danh sách được chọn đang trống.")
            return
        rows = [result_values(state) for state in accounts]
        target = int(getattr(self, "run_config", {}).get("page_target") or 0)
        records = [report_record(state, target) for state in accounts]
        parent = getattr(self, "create_page_results_window", None)
        path = filedialog.asksaveasfilename(parent=parent, title="Xuất kết quả",
            defaultextension=f".{extension}", initialfile=f"results_{key}_{datetime.now():%Y%m%d_%H%M%S}.{extension}",
            filetypes=[("Excel Workbook" if extension == "xlsx" else "CSV", f"*.{extension}")])
        if not path:
            return
        try:
            if extension == "xlsx":
                write_create_page_results_xlsx(path, {key: records}, result_rows=rows)
            else:
                write_result_csv(path, rows)
        except Exception as exc:
            messagebox.showerror("Xuất kết quả thất bại", str(exc), parent=parent)
            return
        messagebox.showinfo("Xuất kết quả thành công", f"Đã lưu báo cáo tại:\n{path}", parent=parent)

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
                "\n".join(normalize_account_source_line(line) for line in remaining_lines) + "\n",
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
        self.refresh_create_page_results_dialog()
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
                    f"{state['page_success_count']} / {state['page_failed_count']}",
                    f"{state['friend_success_count']} / {state['friend_failed_count']}",
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
        self.refresh_management_account_row(index)
        self.refresh_create_page_results_dialog(index)
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
                f"{state['page_success_count']} / {state['page_failed_count']}",
                f"{state['friend_success_count']} / {state['friend_failed_count']}",
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
        committed = self.account_states.record_task(index, module, status, detail, outcome, preserve_outcomes)
        self.post_ui(lambda idx=int(index): self.refresh_account_state_row(idx))
        return committed

    def skip_paused_module(self, index, module):
        reason = app_circuit_breaker(self).paused_reason(module)
        if not reason:
            return False
        self.record_task_result(index, module, "SKIPPED", reason, preserve_outcomes=True)
        self.set_account_state(index, current_action=f"{module}: {reason}")
        return True

    def publish_create_page_result(self, index, result):
        status = str(result.get("status") or "ERROR").upper()
        state = self.account_states.get(index) or {}
        if status == "SUCCESS":
            if (result.get("owner_account_id") != state.get("account_id")
                    or not result.get("page_job_id")
                    or not page_identity_keys(result.get("page_url"), result.get("page_id"))):
                raise ValueError("Verified Page result lacks matching owner/job/identity.")
        detail = str(result.get("reason") or result.get("technical_error")
                     or result.get("page_url") or result.get("page_id") or result.get("page_name") or "")
        # Commit the result and counter before publishing SUCCESS or writing exports.
        if not self.record_task_result(index, "CREATE_PAGE", status, detail, result):
            return False
        if app_circuit_breaker(self).observe("CREATE_PAGE", state.get("account_id"), result, state.get("status")):
            self.log(app_circuit_breaker(self).paused_reason("CREATE_PAGE"), account_index=index)
        self.set_account_state(index, current_action=f"Create Page [{status}]: {detail[:140]}")
        for exporter in ((save_created_page_success,) if status == "SUCCESS" else ()) + (save_create_page_outcome,):
            try:
                exporter(result)
            except Exception as exc:
                self.log(f"[EXPORT_ERROR] Kết quả đã lưu; không xuất được {getattr(exporter, '__name__', 'result')}: {exc}", account_index=index)
        try:
            append_create_page_account_log(index, result.get("account_id", state.get("account_id", "")),
                                           f"[{status}][PAGE_FLOW] {result.get('page_name', '')} | {detail}")
        except Exception as exc:
            self.log(f"[EXPORT_ERROR] Không xuất được log Create Page: {exc}", account_index=index)
        return True

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
        if config.get("proxy_snapshot_complete", False):
            error = config.get("proxy_errors", {}).get(index)
            if error:
                raise ConnectionError(error)
            effective_proxy = config.get("resolved_proxies", {}).get(index, "")
        elif mode == "rotating_api" and proxy_api:
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
            "cookie": state.get("cookie", ""),
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
        return {record[field] for record in records for field in ("raw_line", "cookie")
                if record.get(field)}

    def get_targets_for_mode(self, targets, mode, known_modes=None):
        """Lọc target theo prefix mode, vẫn hỗ trợ danh sách cũ không có prefix."""
        available_modes = known_modes if known_modes is not None else self.mode_vars
        return filter_targets_for_mode(targets, mode, available_modes)

    def update_tree_row(self, item_id, current_friends=None, sent_today=None, status=None):
        """Render management cells from account state, never positional credential cells."""
        def _update():
            if str(item_id).isdigit():
                self.refresh_management_account_row(int(item_id))
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
        source_lines = self._normalize_account_input()
        for account in account_list:
            record = runtime_account_record(account)
            if record is None:
                record = import_account_record(account.get("raw", ""), len(source_lines) + 1)
            if record is not None:
                source_lines.append(record.cookie)
                self._account_import_records[len(source_lines)] = record
        self.txt_accounts.delete("1.0", "end")
        if source_lines:
            self.txt_accounts.insert("1.0", "\n".join(source_lines) + "\n")
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
        remaining_records = [
            getattr(self, "_account_import_records", {}).get(index)
            for index in range(1, len(source_lines) + 1) if index not in selected_indexes
        ]
        self._account_import_records = {
            index: record for index, record in enumerate(remaining_records, 1) if record is not None
        }

        self.txt_accounts.delete("1.0", "end")
        if remaining_lines:
            self.txt_accounts.insert("1.0", "\n".join(remaining_lines) + "\n")

        self.reload_table_from_text()
        if hasattr(self, 'lbl_stat_total'):
            self.lbl_stat_total.config(text=str(len(self.tree.get_children())))
        if hasattr(self, 'lbl_acc_count'):
            self.lbl_acc_count.config(text=f"Tổng: {len(self.tree.get_children())} nick")

    
    # [BẮT ĐẦU THAY THẾ save_settings VÀ load_settings:]
    def save_settings(self):
        modes_saved = {k: v.get() for k, v in self.mode_vars.items()
                       if k in CORE_AUTOMATION_MODES} if hasattr(self, 'mode_vars') else {}
        data = {
            "selected_theme": self.current_theme,
            "accounts": protect_setting(self.txt_accounts.get("1.0", "end").strip()),
            "account_import_records": protect_setting(json.dumps({
                str(index): asdict(record)
                for index, record in getattr(self, "_account_import_records", {}).items()
            }, ensure_ascii=False)),
            "proxies": protect_setting(self.txt_proxies.get("1.0", "end").strip()),
            "targets": self.txt_targets.get("1.0", "end").strip(),
            "selected_modes": modes_saved,
            "proxy_mode": self.proxy_mode.get(),
            "proxy_ratio": self.ent_proxy_ratio.get(),
            "threads": self.ent_threads.get(),
            "batch_size": self.ent_batch_size.get(),
            "headless": self.chk_headless.get(),
            "warmup": self.chk_warmup.get(),
            "warmup_seconds": self.ent_warmup_seconds.get(),
            "notification_seconds": self.ent_notification_seconds.get(),
            "target": self.ent_target.get(),
            "page_target": self.ent_page_target.get() if hasattr(self, 'ent_page_target') else "5",
            "max_create_page_workers": self.ent_max_create_page_workers.get() if hasattr(self, 'ent_max_create_page_workers') else "3",
            "min_page_delay": self.ent_min_page_delay.get() if hasattr(self, 'ent_min_page_delay') else "60",
            "max_page_delay": self.ent_max_page_delay.get() if hasattr(self, 'ent_max_page_delay') else "120",
            "min_delay": self.ent_min_delay.get(),

            "max_delay": self.ent_max_delay.get(),
            "check_notif": self.chk_check_notif.get(),
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
            if "account_import_records" in data:
                saved_records = json.loads(unprotect_setting(data["account_import_records"]))
                self._account_import_records = {}
                for index, payload in saved_records.items():
                    payload["import_fields"] = tuple(payload.get("import_fields", ()))
                    record = AccountRecord(**payload)
                    if parse_canonical_account_line(record.canonical_line):
                        self._account_import_records[int(index)] = record
            if "proxies" in data: self.txt_proxies.insert("1.0", unprotect_setting(data["proxies"]))
            if "targets" in data: self.txt_targets.insert("1.0", data["targets"])
            if "selected_modes" in data and hasattr(self, 'mode_vars'):
                for k, val in data["selected_modes"].items():
                    if k in CORE_AUTOMATION_MODES and k in self.mode_vars:
                        self.mode_vars[k].set(val)
            if "proxy_mode" in data: self.proxy_mode.set(data["proxy_mode"])
            if "proxy_ratio" in data: self.ent_proxy_ratio.delete(0, "end"); self.ent_proxy_ratio.insert(0, data["proxy_ratio"])
            if "threads" in data: self.ent_threads.delete(0, "end"); self.ent_threads.insert(0, data["threads"])
            if "batch_size" in data: self.ent_batch_size.delete(0, "end"); self.ent_batch_size.insert(0, data["batch_size"])
            if "headless" in data: self.chk_headless.set(data["headless"])
            if "warmup" in data: self.chk_warmup.set(data["warmup"])
            for key, entry in (("warmup_seconds", self.ent_warmup_seconds),
                               ("notification_seconds", self.ent_notification_seconds)):
                if key in data:
                    entry.delete(0, "end")
                    entry.insert(0, data[key])
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
            if "min_delay" in data: self.ent_min_delay.delete(0, "end"); self.ent_min_delay.insert(0, data["min_delay"])
            if "max_delay" in data: self.ent_max_delay.delete(0, "end"); self.ent_max_delay.insert(0, data["max_delay"])
            if "check_notif" in data: self.chk_check_notif.set(data["check_notif"])
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
                lines = [line.rstrip("\r\n") for line in f if line.strip() and not line.lstrip().startswith("#")]
            self._account_import_records = {}
            self.txt_accounts.delete("1.0", "end")
            self.txt_accounts.insert("1.0", "\n".join(lines) + "\n")
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
                    state = self.management_account_for_item(item)
                    if state:
                        writer.writerow([state["stt"], state["uid"], state["password"], state["2fa"],
                                         state["status"], redact_history_text(state["current_action"], state), now_str])
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo tại:\n{file_path}")
    def _normalize_account_input(self):
        """Show cookies only, retaining normalized models and original input internally."""
        text = self.txt_accounts.get("1.0", "end")
        lines = [line for line in text.splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        previous = getattr(self, "_account_import_records", {})
        remaining = list(previous.items())
        records = {}
        display_lines = []
        for index, line in enumerate(lines, 1):
            normalized = normalize_account_source_line(line)
            match = next(((key, record) for key, record in remaining
                          if key == index and normalized in (record.cookie, record.canonical_line)), None)
            if match is None:
                match = next(((key, record) for key, record in remaining
                              if normalized in (record.cookie, record.canonical_line)), None)
            if match:
                remaining.remove(match)
                record = match[1]
            else:
                record = import_account_record(line, index)
            if record is not None:
                records[index] = record
                display_lines.append(record.cookie)
            else:
                display_lines.append(line)
        self._account_import_records = records
        cookie_text = "\n".join(display_lines)
        if text.rstrip("\r\n") != cookie_text:
            self.txt_accounts.delete("1.0", "end")
            if display_lines:
                self.txt_accounts.insert("1.0", cookie_text + "\n")
        return display_lines

    def reload_table_from_text(self, checked_indexes=None, normalize_before_run=False):
        if getattr(self, "is_running", False) and not normalize_before_run:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        raw_acc_lines = self._normalize_account_input()
        proxy_lines = [p.strip() for p in self.txt_proxies.get("1.0", "end").splitlines() if p.strip() and not p.startswith("#")]
        ratio = int(self.ent_proxy_ratio.get()) if self.ent_proxy_ratio.get().isdigit() else 20
        proxy_signature = (self.proxy_mode.get(), tuple(proxy_lines), ratio)
        if getattr(self, "_preview_proxy_signature", None) != proxy_signature:
            self._preview_proxy_assignments = {}
            self._preview_proxy_signature = proxy_signature
        account_records = []

        for idx, line in enumerate(raw_acc_lines, 1):
            record = self._account_import_records.get(idx)
            if record is None:
                continue
            parsed = record.to_account_dict()
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

            self.tree.insert("", "end", iid=str(idx), values=management_account_values(
                {**parsed, "stt": idx, "status": "UNKNOWN", "current_action": "Chưa chạy"},
                checked_indexes is None or idx in checked_indexes,
            ), tags=("UNKNOWN",))

        self.account_states.sync(account_records)
        for index in self.account_states.indexes():
            item_id = str(index)
            self.refresh_management_account_row(index)
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

        self._run_generation = getattr(self, "_run_generation", 0) + 1
        self._finished_run_generation = None
        self._cancel_requested_generation = None
        self.worker_root_task = None
        self.worker_tasks = []
        self.worker_loop = None
        self.is_running = False
        self.stop_requested = False
        self.run_error = None
        self.run_status = None
        self.run_account_indexes = None
        try:
            if not any(line.strip() and not line.lstrip().startswith("#")
                       for line in self.txt_accounts.get("1.0", "end").splitlines()):
                raise ValueError("Không có tài khoản để chạy.")
            checked_indexes = {
                int(self.tree.item(item, "values")[1])
                for item in self.tree.get_children()
                if str(self.tree.item(item, "values")[0]) == "[✔]"
                and str(self.tree.item(item, "values")[1]).isdigit()
            }
            self.reload_table_from_text(checked_indexes=checked_indexes or None)
            if not self.account_states.indexes():
                raise ValueError("Không có tài khoản hợp lệ để chạy.")
            self.run_config = self.capture_run_config()
            selected = self.parse_range_string(self.run_config.get("selected_indexes", "")) or self.run_config.get("checked_indexes", set())
            self.run_account_indexes = set(selected) if selected else set(self.account_states.indexes())
            self.save_settings()
        except Exception as exc:
            self.run_error = f"Không chuẩn bị được lượt chạy: {type(exc).__name__}: {exc}"
            self.log(f"[ERROR] {self.run_error}")
            self.finish_run()
            return
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
        if self.run_config.get("auto_headless", False):
            self.log("[i] Trên 12 trình duyệt: tự động bật chế độ chạy ẩn để giảm RAM và tránh tràn màn hình.")
        self.stop_requested = False
        self.run_error = None
        self.is_running = True
        app_circuit_breaker(self).reset()
        self.run_status = "RUNNING"
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
        if self.stop_requested:
            return
        self.stop_requested = True
        generation = getattr(self, "_run_generation", 0)
        self.log("[!] Đang gửi lệnh dừng đến tất cả các luồng...")
        def mark_stopping():
            if generation != getattr(self, "_run_generation", 0):
                return
            self.btn_stop.config(state="disabled")
            if hasattr(self, 'lbl_status_indicator'):
                self.lbl_status_indicator.config(text="● Đang dừng...", fg="#F59E0B")
        self.post_ui(mark_stopping)
        loop = self.worker_loop
        if loop and loop.is_running():
            try:
                loop.call_soon_threadsafe(self._cancel_worker_tasks, generation)
            except RuntimeError:
                # The worker may finish and close its loop during this request.
                pass

    def _cancel_worker_tasks(self, generation=None):
        current = getattr(self, "_run_generation", 0)
        if generation is not None and generation != current:
            return
        if getattr(self, "_cancel_requested_generation", None) == current:
            return
        self._cancel_requested_generation = current
        root = getattr(self, "worker_root_task", None)
        if root is not None and not root.done():
            # Cancelling gather's owner propagates once to all account tasks.
            root.cancel()
            return
        for task in list(self.worker_tasks):
            if not task.done():
                task.cancel()

    def finish_run(self, generation=None):
        current = getattr(self, "_run_generation", 0)
        if generation is not None and generation != current:
            return
        if getattr(self, "_finished_run_generation", None) == current:
            return
        if self.run_thread and self.run_thread.is_alive():
            self.root.after(100, lambda: self.finish_run(current))
            return
        was_stopped = self.stop_requested
        if getattr(self, "run_error", None):
            self.run_status = "FAILED"
        elif was_stopped:
            self.run_status = "CANCELLED"
        elif getattr(self, "run_status", None) not in RUN_STATUSES - {"RUNNING"}:
            self.run_status = (self.account_states.run_result(getattr(self, "run_account_indexes", None))
                               if hasattr(self, "account_states") else "COMPLETED")
        self.is_running = False
        self.stop_requested = False
        self.run_thread = None
        self.worker_loop = None
        self.worker_tasks = []
        self.worker_root_task = None
        self._finished_run_generation = current

        # Khôi phục trạng thái nút Bắt đầu để người dùng có thể chạy lại ngay
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        
        if hasattr(self, 'lbl_status_indicator'):
            text, color = {
                "FAILED": ("● Lỗi (Sẵn sàng chạy lại)", "#EF4444"),
                "CANCELLED": ("● Đã dừng (Sẵn sàng chạy lại)", "#F59E0B"),
                "COMPLETED_WITH_ERRORS": ("● Kết thúc có lỗi", "#F59E0B"),
                "COMPLETED": ("● Hoàn thành", "#10B981"),
            }[self.run_status]
            self.lbl_status_indicator.config(
                text=text, fg=color,
            )

    def run_process(self):
        """Khởi tạo vòng lặp sự kiện tương thích tuyệt đối với Windows và Playwright"""
        generation = getattr(self, "_run_generation", 0)
        ui_context = getattr(self, "_ui_run_context", None)
        if ui_context is None:
            ui_context = self._ui_run_context = contextvars.ContextVar("ui_run_context", default=None)
        token = ui_context.set(generation)

        async def current_run():
            self.worker_loop = asyncio.get_running_loop()
            self.worker_root_task = asyncio.current_task()
            if self.stop_requested:
                raise asyncio.CancelledError()
            await self.main_worker()

        try:
            # Chạy trực tiếp worker chính, không gọi lại set_event_loop_policy để tránh xung đột luồng
            asyncio.run(current_run())
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
            self.worker_root_task = None
            try:
                self.post_ui(self.finish_run)
            finally:
                ui_context.reset(token)


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


    async def login_facebook_user_pass(self, page, context, username, password, expected_uid=None, twofa=None):
        """Đăng nhập Facebook bằng tài khoản và mật khẩu đã được parse."""
        if not username or not password:
            return LOGIN_TECHNICAL_ERROR, "Thiếu tài khoản hoặc mật khẩu"

        self.log(f"[*] Đang đăng nhập Facebook cho tài khoản: {username}...")
        try:
            log_context = getattr(self, "account_log_context", None)
            index = log_context.get() if log_context is not None else None
            state = self.account_states.get(index) if index is not None else None
            if expected_uid is None:
                expected_uid = (state or {}).get("uid") or username
            if twofa is None:
                twofa = (state or {}).get("2fa", "")
            await context.clear_cookies()
            response = await page.goto("https://www.facebook.com/login/", wait_until="domcontentloaded", timeout=40000)
            status = getattr(response, "status", None)
            if isinstance(status, int) and status >= 400:
                return LOGIN_TECHNICAL_ERROR, f"Login navigation HTTP {status}"
            await page.locator('input[name="email"]').fill(username)
            await page.locator('input[name="pass"]').fill(password)

            login_btn = page.locator('button[name="login"], button[type="submit"]').first
            if await login_btn.count() == 0:
                # New login forms use a role button rather than a native button.
                candidates = page.locator(
                    'form:has(input[name="email"]):has(input[name="pass"]) [role="button"]:visible'
                )
                if await candidates.count() != 1:
                    self.log(f"[-] [{username}] Không xác định được nút đăng nhập Facebook duy nhất.")
                    return LOGIN_TECHNICAL_ERROR, "Không xác định được nút đăng nhập Facebook duy nhất"
                login_btn = candidates.first

            await login_btn.click()
            await page.wait_for_timeout(5000)
            
            code_input = page.locator(FACEBOOK_2FA_INPUT_SELECTOR).first
            if await code_input.count() > 0 and await code_input.is_visible():
                if not twofa:
                    return LOGIN_CHECKPOINT, "Cần mã 2FA nhưng không có trong dữ liệu"
                self.log(f"[*] [{username}] Đang giải mã 2FA...")
                await code_input.fill(generate_totp_code(twofa))
                submit_2fa = page.locator(FACEBOOK_2FA_SUBMIT_SELECTOR).first
                if await submit_2fa.count() == 0 or not await submit_2fa.is_visible():
                    return LOGIN_TECHNICAL_ERROR, "Không tìm thấy nút xác nhận 2FA"
                await submit_2fa.click()
                await page.wait_for_timeout(5000)

            session_result, session_detail = await self.verify_facebook_session(page, context, expected_uid)
            if session_result != LOGIN_SUCCESS:
                self.log(f"[-] [{username}] Đăng nhập Facebook chưa hợp lệ: {session_detail}.")
                return session_result, session_detail

            self.log(f"[✔] [{username}] {session_detail}.")
            return LOGIN_SUCCESS, session_detail
        except FacebookCheckpointStopped:
            return LOGIN_CHECKPOINT, "Facebook yêu cầu xác minh tài khoản"
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

    async def _wait_support_activity(self, page, duration_seconds, scroll=False):
        deadline = time.monotonic() + duration_seconds
        while self.is_running and not getattr(self, "stop_requested", False):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            await self.guard_facebook_checkpoint(page)
            if page.is_closed():
                raise RuntimeError("Profile đã đóng trong lúc chờ")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            if scroll:
                try:
                    await asyncio.wait_for(page.mouse.wheel(0, 500), timeout=min(5, remaining))
                except asyncio.TimeoutError:
                    if time.monotonic() >= deadline:
                        return
                    raise
            await asyncio.sleep(min(5 if scroll else 1, max(0, deadline - time.monotonic())))

    async def warm_up_feed(self, page, acc_name, duration_seconds=30):
        """Browse the Feed for the configured duration, without reactions."""
        duration = self.activity_duration_seconds(duration_seconds, "Feed đệm")
        if duration == 0 or not self.is_running or getattr(self, "stop_requested", False):
            return
        self.log(f"[*] [{acc_name}] Lướt Feed đệm trong {duration} giây...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=25000)
        await self._wait_support_activity(page, duration, scroll=True)

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
        """ # Gọi luôn ở đây để không sợ thiếu thư viện ở đầu file
   
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

        context = None
        page = None
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

            self.log(f"[*] Đã mở Slot {slot} (Luồng {idx}) tại Tọa độ: {pos_x}x{pos_y}")
            return browser, context, page
        except BaseException as e:
            await close_browser_resources(context, browser, page)
            if not isinstance(e, Exception):
                raise
            raise RuntimeError(f"Trình duyệt mở được nhưng Page không phản hồi (Khả năng do Proxy): {e}") from e

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

    async def check_notifications(self, page, acc_name, duration_seconds=3):
        """Keep the notification panel open for the configured duration."""
        duration = self.activity_duration_seconds(duration_seconds, "Thông báo")
        if duration == 0 or not self.is_running or getattr(self, "stop_requested", False):
            return
        self.log(f"[*] [{acc_name}] Xem thông báo trong {duration} giây...")
        notif_btn = page.locator('div[aria-label*="Thông báo"], div[aria-label*="Notifications"]').first
        if await notif_btn.count() == 0:
            self.log(f"[-] [{acc_name}] Không tìm thấy nút thông báo; bỏ qua.")
            return
        await notif_btn.click(timeout=5000)
        await self._wait_support_activity(page, duration)

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

    async def verify_facebook_session(self, page, context, expected_uid=None):
        """Require matching cookie identity and visible authenticated UI evidence."""
        try:
            await self.guard_facebook_checkpoint(page)
            parsed = urlparse(str(page.url or ""))
            host = (parsed.hostname or "").casefold()
            path = parsed.path.casefold()
            if (parsed.scheme not in {"http", "https"}
                    or host != "facebook.com" and not host.endswith(".facebook.com")):
                return LOGIN_TECHNICAL_ERROR, "Chưa tải được trang Facebook hợp lệ"
            if re.match(r'^/(?:checkpoint|challenge|two_factor)(?:/|$|\.)', path):
                return LOGIN_CHECKPOINT, "Facebook yêu cầu xác minh tài khoản"
            if re.match(r'^/(?:disabled|suspended)(?:/|$|\.)', path):
                return LOGIN_INVALID, f"Phiên không hợp lệ: {path}"
            code_fields = page.locator(FACEBOOK_2FA_INPUT_SELECTOR)
            for index in range(await code_fields.count()):
                if await code_fields.nth(index).is_visible():
                    return LOGIN_CHECKPOINT, "Facebook đang yêu cầu mã xác minh 2FA"
            if re.match(r'^/login(?:/|$|\.)', path):
                return LOGIN_INVALID, f"Phiên không hợp lệ: {path}"

            if expected_uid is None:
                log_context = getattr(self, "account_log_context", None)
                index = log_context.get() if log_context is not None else None
                state = self.account_states.get(index) if index is not None else None
                expected_uid = (state or {}).get("uid", "")
            cookies = await context.cookies("https://www.facebook.com/")
            cookie_uids = {str(cookie.get("value") or "") for cookie in cookies
                           if cookie.get("name") == "c_user"}
            if len(cookie_uids) != 1 or not next(iter(cookie_uids), "").isdigit():
                return LOGIN_INVALID, "Cookie thiếu c_user hợp lệ hoặc có UID mâu thuẫn"
            expected_uid = str(expected_uid or "")
            if expected_uid.isdigit() and cookie_uids != {expected_uid}:
                return LOGIN_INVALID, "c_user không khớp UID tài khoản cần đăng nhập"

            login_fields = page.locator(FACEBOOK_LOGIN_FORM_SELECTOR)
            for index in range(await login_fields.count()):
                if await login_fields.nth(index).is_visible():
                    return LOGIN_INVALID, "Facebook đang hiển thị biểu mẫu đăng nhập"

            authenticated = page.locator(FACEBOOK_AUTHENTICATED_SELECTOR)
            for index in range(await authenticated.count()):
                if await authenticated.nth(index).is_visible():
                    return LOGIN_SUCCESS, "Phiên Facebook hợp lệ, có bằng chứng đăng nhập"
            return LOGIN_TECHNICAL_ERROR, "Không có bằng chứng đăng nhập; trang có thể rỗng hoặc DOM chưa sẵn sàng"
        except FacebookCheckpointStopped:
            return LOGIN_CHECKPOINT, "Facebook yêu cầu xác minh tài khoản"
        except Exception as exc:
            return LOGIN_TECHNICAL_ERROR, f"Session verification {type(exc).__name__}: {exc}"

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
        if self.skip_paused_module(idx, "CREATE_PAGE"):
            return []
        await self.guard_facebook_checkpoint(page, idx)
        created_count = 0
        results = []
        current_page_job = None

        def record_result(result):
            owner = (self.account_states.get(idx) or {}).get("account_id", acc_name)
            job = current_page_job["page_job_id"] if current_page_job else ""
            if result.get("status") == "SUCCESS":
                if result.get("owner_account_id") != owner or result.get("page_job_id") != job:
                    raise ValueError("Verified Page owner/job does not match current job.")
            else:
                result.update(owner_account_id=owner, page_job_id=job)
            if not self.publish_create_page_result(idx, result):
                return None
            results.append(result)
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
            if self.skip_paused_module(idx, "CREATE_PAGE"):
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
                            structural_failure="PAGE_NAME_INPUT_MISSING" if name_count_retry == 0 and await page.locator('div[role="main"]').count() > 0 else "",
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
                        structural_failure="CATEGORY_INPUT_MISSING" if await cat_elements.count() == 0 else "",
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
                        structural_failure="CREATE_SUBMIT_MISSING" if await create_btn.count() == 0 else "",
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
                    if self.skip_paused_module(idx, "CREATE_PAGE"):
                        return results
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
                try:
                    if record_result(page_record) is None:
                        return results
                except DuplicatePageResult:
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        page_url=page_identity["url"], page_id=page_identity["id"],
                        reason="Page URL/ID đã tồn tại trong kết quả SQLite.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.log(f"[FAILED] [{acc_name}] Bỏ qua Page trùng URL/ID.")
                    continue

                created_count += 1
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
    
    async def authenticate_facebook_account(self, index, page, context, cookie_str, username, password):
        """Restore and verify cookies only; never submit password, 2FA or token."""
        self.account_states.set_login_mode(index, "COOKIE")
        state = self.account_states.get(index) or {}
        expected_uid = state.get("uid") or username
        try:
            cookies = parse_cookies(cookie_str)
            if not cookies:
                return LOGIN_TECHNICAL_ERROR, "Không đọc được dữ liệu Cookie để khôi phục phiên"
            await context.add_cookies(cookies)
            self.log("[LOGIN][COOKIE] Khôi phục Cookie và xác minh phiên Facebook")
            response = await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
            status = getattr(response, "status", None)
            if isinstance(status, int) and status >= 400:
                return LOGIN_TECHNICAL_ERROR, f"Cookie navigation HTTP {status}"
            await asyncio.sleep(4)
            result, detail = await self.verify_facebook_session(page, context, expected_uid)
            if result == LOGIN_INVALID:
                return result, f"{detail}; Cookie không hợp lệ/hết hạn, cần thay Cookie mới"
            return result, detail
        except FacebookCheckpointStopped:
            return LOGIN_CHECKPOINT, "Facebook yêu cầu xác minh tài khoản"
        except Exception as exc:
            return LOGIN_TECHNICAL_ERROR, f"Cookie login {type(exc).__name__}: {exc}"

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
            if not self.is_running or self.stop_requested: return

            config = self.run_config
            modes = {mode: bool(config.get("modes", {}).get(mode)) for mode in CORE_AUTOMATION_MODES}
            options = config.get("options", {})

            self.set_account_state(idx, status="CHECKING", current_action="Khởi tạo tài khoản")
            self.update_tree_row(str(idx), status="ĐANG KIỂM TRA")
            self.log(f"\n[🚀 LUỒNG BẮT ĐẦU] Nick {idx}: {acc_name}")
            self.log(
                f"[*] [{acc_name}] Context: locale={normalize_account_locale(account_locale)}; "
                f"country={account_country or 'N/A'}; timezone={account_timezone or 'AUTO'}"
            )

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
                login_result, login_detail = await self.authenticate_facebook_account(
                    idx, page, context, cookie_str, login_user, login_password
                )
                if login_result == LOGIN_CHECKPOINT:
                    self.stop_checkpoint_account(idx)
                    self.update_tree_row(str(idx), status="CHECKPOINT")
                    return
                if login_result != LOGIN_SUCCESS:
                    failure_kind = "invalid_login" if login_result == LOGIN_INVALID else "automation"
                    self.set_account_failure(idx, failure_kind, f"[{acc_name}] {login_detail}")
                    self.update_tree_row(str(idx), status="DIE" if login_result == LOGIN_INVALID else "ERROR")
                    return
                self.log(f"[LOGIN][SUCCESS] {login_detail}")

                await self.guard_facebook_checkpoint(page, idx)
                self.set_account_state(idx, status="LIVE", current_action="Đăng nhập Facebook hợp lệ")
                self.update_tree_row(str(idx), status="LIVE")
                checkpoint_watcher = asyncio.create_task(
                    self.watch_facebook_checkpoint(page, idx, asyncio.current_task())
                )

                if options.get("warmup"):
                    self.set_account_state(idx, current_action="Đang lướt Feed đệm")
                    await self.warm_up_feed(page, acc_name, config.get("warmup_seconds", 30))
                if options.get("check_notif"):
                    self.set_account_state(idx, current_action="Đang xem thông báo")
                    await self.check_notifications(page, acc_name, config.get("notification_seconds", 3))

                total_sent = 0
                created_pages = []
                create_page_completion_action = ""
                friend_enabled = any(modes.get(mode) for mode in ("by_name", "by_group", "by_uid"))
                if friend_enabled:
                    cur_friends = await self.get_current_friends_count(page)
                    self.update_tree_row(str(idx), current_friends=cur_friends)
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
                user_cancelled = self.stop_requested
                interrupted = bool(not user_cancelled and current_state
                                   and current_state["status"] in {"CHECKPOINT", "ERROR"})
                self.finalize_active_account_tasks(
                    idx, "ERROR" if interrupted else "SKIPPED",
                    current_state["current_action"] if interrupted else "Đã dừng theo yêu cầu",
                )
                if interrupted:
                    return
                if current_state and current_state["status"] == "CHECKING":
                    self.set_account_state(idx, status="UNKNOWN", current_action="Đã dừng khi đang kiểm tra")
                    self.update_tree_row(str(idx), status="CHƯA KIỂM TRA")
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
                try:
                    if checkpoint_watcher is not None:
                        checkpoint_watcher.cancel()
                        await asyncio.wait({checkpoint_watcher}, timeout=1)
                        checkpoint_watcher.add_done_callback(consume_cleanup_result)
                finally:
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
        modes = {mode: bool(config.get("modes", {}).get(mode)) for mode in CORE_AUTOMATION_MODES}
        if modes.get("create_page", False):
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
                self.run_status = "FAILED"
                self.log(f"[FAILED][CREATE_PAGE][PRE-FLIGHT] {validation_error}")
                for index in target_indexes or range(1, len(raw_acc_lines) + 1):
                    self.set_account_state(
                        index,
                        current_action=f"Create Page FAILED: {validation_error}",
                    )
                return
        batch_size = config.get("batch_size", 5)
        resolved_proxies = config.get("resolved_proxies", {})
        semaphore = asyncio.Semaphore(threads_count)
        account_jobs = []
        for idx, line in enumerate(raw_acc_lines, 1):
            if target_indexes and idx not in target_indexes:
                continue
            parsed = parsed_accounts.get(idx) or parsed_accounts.get(str(idx))
            record = runtime_account_record(parsed)
            if record is None or normalize_account_source_line(line) not in (record.cookie, record.canonical_line):
                record = parse_canonical_account_line(line)
            if record is None:
                continue
            parsed = record.to_account_dict()

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
            account_jobs.append({
                "idx": idx,
                "acc_name": acc_name,
                "cookie_str": cookie_str,
                "assigned_proxy_str": assigned_proxy_str,
                "account_type": "COOKIE",
                "login_user": parsed.get("uid", ""),
                "login_password": "",
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
                    if self.stop_requested:
                        break
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
            self.run_status = "CANCELLED"
            self.log("\n[!] Tiến trình đã dừng; các luồng đang chạy đã được đóng an toàn.")
            return

        final_summary = self.account_states.summary([job["idx"] for job in account_jobs])
        self.run_account_indexes = {job["idx"] for job in account_jobs}
        self.run_status = self.account_states.run_result(self.run_account_indexes)
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
            send_telegram_alert(t_token, t_id, "THÔNG BÁO: " + (
                "Đợt chạy kết thúc có lỗi; kiểm tra nhật ký tài khoản."
                if self.run_status == "COMPLETED_WITH_ERRORS"
                else "Toàn bộ dàn nick đã hoàn thành tất cả tiến trình!"
            ))

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
        record = runtime_account_record(self.account_states.get(account_index))
        return record.to_account_dict() if record else None


    def open_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chú ý", "Vui lòng chọn 1 dòng tài khoản để mở Profile!")
            return

        self.open_account_inspector(self.management_account_for_item(selected[0]))

    def open_account_inspector(self, account):
        if account is None:
            return
        snapshot = RunConfig(account)
        def launch():
            try:
                asyncio.run(self.inspect_account_session(snapshot))
            except Exception as exc:
                error = redact_history_text(f"{type(exc).__name__}: {exc}", snapshot)
                self.post_ui(lambda: messagebox.showerror("Chrome kiểm tra", error))
        threading.Thread(target=launch, daemon=True).start()

    async def inspect_account_session(self, account):
        """Manual inspection owns its driver, browser and ephemeral account context."""
        proxy = str(account.get("effective_proxy") or account.get("proxy") or "")
        proxy = "" if proxy == "Không dùng" else proxy
        proxy_cfg = parse_proxy(proxy)
        if proxy and not proxy_cfg:
            raise ValueError("Proxy không hợp lệ; không mở bằng IP thật.")
        browser = context = page = None
        async with async_playwright() as p:
            try:
                launch_options = {"headless": False}
                browser_exe = get_installed_browser_path()
                if browser_exe:
                    launch_options["executable_path"] = browser_exe
                if proxy_cfg:
                    launch_options["proxy"] = proxy_cfg
                browser = await p.chromium.launch(**launch_options)
                context_options = {}
                locale = browser_locale_options(account.get("locale", "AUTO"))["locale"]
                if locale:
                    context_options["locale"] = locale
                zone = normalize_account_timezone(account.get("timezone", ""))
                if zone:
                    context_options["timezone_id"] = zone
                context = await browser.new_context(**context_options)
                await context.add_cookies(parse_cookies(account.get("cookie", "")))
                page = await context.new_page()
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
                while browser.is_connected() and context.pages:
                    await asyncio.sleep(0.5)
            finally:
                await close_browser_resources(context, browser, page)


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

def run_application():
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

def main():
    if not getattr(sys, "frozen", False):
        return run_application()
    lock = SingleInstanceLock(output_path("production.lock"))
    try:
        if not lock.acquire():
            root = tk.Tk()
            root.withdraw()
            try:
                messagebox.showinfo("Ứng dụng đang chạy", "Ứng dụng đang chạy", parent=root)
            finally:
                root.destroy()
            return 0
        return run_application()
    finally:
        lock.release()

if __name__ == "__main__":
    sys.exit(main() or 0)
