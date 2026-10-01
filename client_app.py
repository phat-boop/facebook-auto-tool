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
from datetime import datetime
from tkinter import ttk, messagebox, scrolledtext, filedialog
from urllib.parse import quote, urlparse
from cryptography.fernet import Fernet, InvalidToken
from playwright.async_api import async_playwright
# ==================== CẤU HÌNH EVENT LOOP AN TOÀN CHO WINDOWS ====================
# ==================== CẤU HÌNH EVENT LOOP THEO CHUẨN HIỆN ĐẠI ====================
if sys.platform == 'win32':
    # Lấy policy hiện tại của hệ thống để kiểm tra trước
    current_policy = asyncio.get_event_loop_policy()
    if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
        # Chỉ thiết lập lại nếu hệ thống chưa dùng Proactor làm mặc định
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())




# ==================== THÔNG TIN PHIÊN BẢN & BẢO MẬT ====================
CURRENT_VERSION = "2.2.1"
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

ACCOUNT_STATUSES = {"UNKNOWN", "CHECKING", "LIVE", "DIE", "ERROR"}
ACCOUNT_STATUS_LABELS = {
    "UNKNOWN": "CHƯA KIỂM TRA",
    "CHECKING": "ĐANG KIỂM TRA",
    "LIVE": "LIVE",
    "DIE": "DIE",
    "ERROR": "ERROR",
}
ACCOUNT_STATUS_COLORS = {
    "UNKNOWN": "#94A3B8",
    "CHECKING": "#FACC15",
    "LIVE": "#22C55E",
    "DIE": "#EF4444",
    "ERROR": "#F97316",
}
LOGIN_SUCCESS = "SUCCESS"
LOGIN_INVALID = "INVALID"
LOGIN_TECHNICAL_ERROR = "TECHNICAL_ERROR"

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
        "STT", "Tài khoản / UID", "Trạng thái", "Page đã tạo",
        "Chỉ tiêu Page", "Kết quả / Lý do", "Thời gian", "Dữ liệu tài khoản gốc",
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
                record.get("account_id") or record.get("uid", ""),
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
    def __init__(self):
        self._lock = threading.RLock()
        self._states = {}

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
                        "current_action": "Chưa chạy",
                        "logs": [],
                        **account_payload,
                    }
                else:
                    existing["country"] = str(account.get("country") or "")
                    existing["locale"] = normalize_account_locale(account.get("locale"))
                    existing["timezone"] = normalize_account_timezone(account.get("timezone"))
                    existing.update(account_payload)
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
            if status is not None:
                normalized_status = str(status).upper()
                if normalized_status not in ACCOUNT_STATUSES:
                    raise ValueError(f"Trạng thái tài khoản không hợp lệ: {status}")
                state["status"] = normalized_status
            if current_action is not None:
                state["current_action"] = str(current_action)
            return self.get(index)

    def append_log(self, index, message, current_action=None):
        with self._lock:
            state = self._states.get(int(index))
            if state is None:
                return None
            state["logs"].append(str(message))
            if len(state["logs"]) > 5000:
                del state["logs"][:-4500]
            if current_action:
                state["current_action"] = str(current_action)
            return self.get(index)

    def set_failure(self, index, failure_kind, reason):
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
    ]
    csv_path = output_path("created_pages.csv")
    success_path = output_path("created_pages_success.txt")
    candidate_keys = page_identity_keys(record.get("page_url"), record.get("page_id"))
    if not candidate_keys:
        return False

    with RESULT_FILE_LOCK:
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
]


def save_create_page_outcome(record):
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


async def close_browser_resources(context=None, browser=None):
    """Close isolated resources on success, failure, or cancellation."""
    errors = []
    for resource in (context, browser):
        if resource is None:
            continue
        try:
            await resource.close()
        except Exception as exc:
            errors.append(exc)
    return errors


async def wait_for_locator_ready(locator, timeout=10000):
    """Wait for a visible, enabled action without clicking it."""
    await locator.wait_for(state="visible", timeout=timeout)
    for _ in range(10):
        aria_disabled = (await locator.get_attribute("aria-disabled") or "").casefold()
        disabled = await locator.get_attribute("disabled")
        if aria_disabled != "true" and disabled is None:
            return True
        await asyncio.sleep(0.25)
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


def build_windows_update_restart_script(process_id, temp_file, current_exe, error_log):
    """Build the updater script that replaces and starts a fresh PyInstaller app."""
    def batch_path(value):
        return os.path.abspath(str(value)).replace("%", "%%")

    temp_path = batch_path(temp_file)
    executable_path = batch_path(current_exe)
    executable_dir = batch_path(os.path.dirname(current_exe))
    error_log_path = batch_path(error_log)
    return f"""@echo off
setlocal
del /q "{error_log_path}" >nul 2>&1
taskkill /f /pid {int(process_id)} >nul 2>&1
timeout /t 3 /nobreak >nul
copy /y "{temp_path}" "{executable_path}" >nul
if errorlevel 1 goto replace_failed
del /q "{temp_path}" >nul 2>&1

rem Start a new top-level PyInstaller instance instead of inheriting the old archive context.
set "PYINSTALLER_RESET_ENVIRONMENT=1"
start "" /d "{executable_dir}" "{executable_path}"
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
                                        os.getpid(), temp_file, current_exe, restart_error_log
                                    )
                                    with open(updater_file, "w", encoding="utf-8") as f_bat:
                                        f_bat.write(bat_script)

                                    self.post_ui(lambda: lbl_progress.config(text="Tải xong! Đang khởi động lại ứng dụng..."))
                                    time.sleep(1.5)

                                    subprocess.Popen([updater_file], shell=True, cwd=APP_DATA_DIR)
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
    if not re.search(r'(?:^|;)\s*(?:c_user|xs|sessionid|sb|datr)\s*=', value):
        return ""
    return value


def parse_cookies(cookie_raw: str, default_domain: str = ".facebook.com"):
    """Tự động phân tách chuỗi cookie chuẩn định dạng Playwright"""
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
    if "://" in raw:
        try:
            parsed = urlparse(raw)
            if parsed.scheme not in {"http", "https", "socks4", "socks5"} or not parsed.hostname or not parsed.port:
                return None
            proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
            if parsed.username:
                proxy["username"] = parsed.username
            if parsed.password:
                proxy["password"] = parsed.password
            return proxy
        except ValueError:
            return None

    parts = raw.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        if port.isdigit() and 0 < int(port) <= 65535:
            return {"server": f"http://{host}:{port}", "username": username, "password": password}
    elif len(parts) == 2:
        host, port = parts
        if port.isdigit() and 0 < int(port) <= 65535:
            return {"server": f"http://{host}:{port}"}
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
    """Parse account fields without mutating or discarding the original line."""
    raw_value = str(raw_line or "").rstrip("\r\n")
    normalized_line = re.sub(r'^\s*\d+[\.\-]\s*', '', raw_value).strip()
    if not normalized_line:
        return None

    account_line, metadata = split_account_metadata(normalized_line)
    exact_fields = normalized_line.split("|")
    parts = [part.strip() for part in account_line.split("|")]
    recognized_indexes = set()
    uid = ""
    name = f"Nick_{idx}"
    password = ""
    fa2 = ""
    cookie = ""
    token = ""
    email = ""
    proxy = ""

    def is_cookie(value):
        return bool(normalize_cookie_input(value))

    prefix = parts[0].upper() if parts else ""
    if prefix == "COOKIE":
        recognized_indexes.add(0)
        cookie = parts[1] if len(parts) > 1 else ""
        if len(parts) > 1:
            recognized_indexes.add(1)
    elif prefix == "TOKEN":
        recognized_indexes.add(0)
        token = parts[1] if len(parts) > 1 else ""
        if len(parts) > 1:
            recognized_indexes.add(1)
    elif prefix == "FACEBOOK":
        recognized_indexes.add(0)
        uid = parts[1] if len(parts) > 1 else ""
        password = parts[2] if len(parts) > 2 else ""
        recognized_indexes.update(index for index in (1, 2) if index < len(parts))
        email = uid if "@" in uid else ""
    elif len(parts) == 1:
        value = parts[0]
        if is_cookie(value):
            cookie = value
            recognized_indexes.add(0)
        elif value.startswith(("EAAB", "EAAA")):
            token = value
            recognized_indexes.add(0)
        else:
            # Backward compatibility for raw, unclassified account input.
            cookie = value
    else:
        uid = parts[0] if parts else ""
        password = parts[1] if len(parts) > 1 else ""
        fa2 = parts[2] if len(parts) > 2 else ""
        recognized_indexes.update(index for index in (0, 1, 2) if index < len(parts))

        cookie_index = -1
        for field_index, value in enumerate(parts):
            if not value:
                continue
            if cookie_index < 0 and is_cookie(value):
                cookie = value
                cookie_index = field_index
                recognized_indexes.add(field_index)
            elif not token and value.startswith(("EAAB", "EAAA")):
                token = value
                recognized_indexes.add(field_index)
            elif not email and "@" in value and "." in value:
                email = value
                recognized_indexes.add(field_index)
            elif not proxy and parse_proxy(value):
                proxy = value
                recognized_indexes.add(field_index)

        # Lossless extended format: UID|PASSWORD|2FA|||COOKIE|TOKEN
        if cookie_index == 5 and len(parts) > 6 and parts[6]:
            token = parts[6]
            recognized_indexes.add(6)

    # Prefixes describe the import format; cookies anywhere in it take priority.
    cookie_fields = []
    for field_index, value in enumerate(parts):
        if is_cookie(value):
            cookie_fields.append(value)
            recognized_indexes.add(field_index)
    if cookie_fields:
        cookie = cookie_fields[0] if len(cookie_fields) == 1 else "; ".join(
            normalize_cookie_input(value).rstrip("; ") for value in cookie_fields
        )
    cookie_uid = re.search(r"(?:^|;)\s*c_user\s*=\s*(\d+)", normalize_cookie_input(cookie))
    if cookie_uid and (not uid or is_cookie(uid)):
        uid = cookie_uid.group(1)
    if prefix == "TOKEN" and not uid:
        uid = token[:15]

    account_type = "COOKIE" if cookie else ("TOKEN" if token else "RAW")
    if prefix == "FACEBOOK" and not cookie:
        account_type = "RAW"
    if uid:
        name = uid if prefix != "COOKIE" else f"FB_{uid}"
    elif token:
        name = f"Token_{token[:8]}"

    unknown_fields = [
        {"index": field_index, "value": value}
        for field_index, value in enumerate(parts)
        if field_index not in recognized_indexes and value
    ]
    result = {
        "type": account_type,
        "raw_line": raw_value,
        "source_line": normalized_line,
        "fields": exact_fields,
        "unknown_fields": unknown_fields,
        "uid": uid,
        "name": name,
        "pwd": password,
        "password": password,
        "2fa": fa2,
        "cookie": cookie,
        "token": token,
        "email": email,
        "proxy": proxy,
        "data": cookie or token or account_line,
    }
    result.update(metadata)
    return result


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
        fmt = self.format_mode.get()
        parsed_accounts = []

        # [THAY THẾ TOÀN BỘ VÒNG LẶP for line in lines BẰNG ĐOẠN AUTO-DETECT NÀY:]
        for idx, line in enumerate(lines, 1):
            explicit_prefixes = {
                "COOKIE|Cookie Facebook": "COOKIE|",
                "TOKEN|Token Facebook": "TOKEN|",
                "FACEBOOK|Email/UID|Password": "FACEBOOK|",
            }
            if fmt in explicit_prefixes:
                prefix = explicit_prefixes[fmt]
                normalized_line = line if line.upper().startswith(prefix) else prefix + line
                parsed = parse_any_account_line(normalized_line, idx)
                if parsed:
                    parsed_accounts.append({
                        "name": parsed["name"],
                        "uid": parsed["uid"],
                        "pwd": parsed["pwd"],
                        "2fa": parsed["2fa"],
                        "cookie": parsed["cookie"],
                        "proxy": parsed["proxy"] or "Không dùng",
                        "raw": normalized_line,
                    })
                continue

            uid, pwd, fa2, cookie, proxy, name = "", "", "", "", "Không dùng", ""
            
            # 1. Nếu dòng là Cookie trần (không có dấu | hoặc chứa c_user/sb/datr)
            if "|" not in line or ("c_user=" in line and fmt == "Chỉ Cookie (Tự nhận diện)"):
                cookie = line
                m = re.search(r'c_user=(\d+)', line)
                uid = m.group(1) if m else f"UID_{idx}"
                name = uid
            else:
                parts = line.split('|')
                # Tự động quét tìm phần tử là Cookie trong các cột
                for part in parts:
                    p = part.strip()
                    if "c_user=" in p or "sb=" in p or "datr=" in p:
                        cookie = p
                        m = re.search(r'c_user=(\d+)', p)
                        if m: uid = m.group(1)
                    elif p.isdigit() and len(p) >= 8 and not uid:
                        uid = p
                    elif len(p) in (16, 32) and p.isalnum() and not fa2 and not p.isdigit():
                        fa2 = p
                    elif ":" in p and any(char.isdigit() for char in p) and proxy == "Không dùng":
                        proxy = p

                # Nếu chọn theo định dạng mẫu cố định
                if fmt == "UID|Pass|2FA|Cookie":
                    uid = parts[0] if len(parts) > 0 else uid
                    pwd = parts[1] if len(parts) > 1 else ""
                    fa2 = parts[2] if len(parts) > 2 else fa2
                    cookie = parts[3] if len(parts) > 3 else cookie
                elif fmt == "Tên|Cookie":
                    name = parts[0] if len(parts) > 0 else (uid or f"Nick_{idx}")
                    cookie = parts[1] if len(parts) > 1 else cookie
                
                name = name or uid or f"Nick_{idx}"

            parsed_accounts.append({
                "name": name,
                "uid": uid,
                "pwd": pwd,
                "2fa": fa2,
                "cookie": cookie,
                "proxy": proxy,
                "raw": line
            })
# [KẾT THÚC THAY THẾ]

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
        self.root.geometry("1380x880")
        self.root.minsize(1280, 800)
        try:
            self.root.iconbitmap(resource_path("picture.ico"))
        except (tk.TclError, OSError):
            pass
        self.is_running = False
        self.stop_requested = False
        self.run_thread = None
        self.worker_loop = None
        self.worker_tasks = []
        self.proxy_api_lock = None
        self.run_config = {}
        self.ui_queue = queue.Queue()
        self.close_requested = False
        self.account_states = AccountStateStore()
        self.account_log_context = contextvars.ContextVar("account_log_context", default=None)
        self.global_logs = []
        self.global_log_lock = threading.RLock()
        self.selected_log_account = None
        self.current_batch = 1
        self.create_page_result_lock = threading.RLock()
        self.create_page_account_results = {"completed": {}, "die": {}}
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
                except (tk.TclError, RuntimeError):
                    pass
        except queue.Empty:
            pass
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
                resolved_proxies[account_index] = values[8] if len(values) > 8 else ""
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
        paned_left.add(card1, minsize=110, height=180)

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
        paned_left.add(card_log, minsize=100, height=180)

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
        paned_right.add(card2, minsize=190, height=215)

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
        for txt, val in [("Luân phiên", "round_robin"), ("Theo nhóm", "fixed_ratio"), ("Ngẫu nhiên", "random"), ("API xoay", "rotating_api")]:
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
        paned_right.add(card_reg, minsize=180, height=220)

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

        state_columns = ("stt", "account", "status", "action")
        self.account_state_tree = ttk.Treeview(card_reg, columns=state_columns, show="headings", selectmode="browse", height=5)
        self.account_state_tree.heading("stt", text="STT")
        self.account_state_tree.heading("account", text="Tài khoản")
        self.account_state_tree.heading("status", text="Trạng thái")
        self.account_state_tree.heading("action", text="Tác vụ hiện tại")
        self.account_state_tree.column("stt", width=40, anchor="center", stretch=False)
        self.account_state_tree.column("account", width=120, anchor="w")
        self.account_state_tree.column("status", width=105, anchor="center", stretch=False)
        self.account_state_tree.column("action", width=190, anchor="w")
        for status, color in ACCOUNT_STATUS_COLORS.items():
            self.account_state_tree.tag_configure(status, foreground=color)
        self.account_state_tree.pack(fill="both", expand=True)
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
        paned_right.add(card4, minsize=140, height=180)

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
        self.lbl_stat_success = make_stat_box(f_stats, "Thành công", "0", 2, "#10B981")
        self.lbl_stat_failed = make_stat_box(f_stats, "Thất bại", "0", 3, "#EF4444")
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

        columns = ("select", "id", "uid", "name", "password", "2fa", "cookie", "email", "proxy", "status")
        self.tree = ttk.Treeview(frame_tree, columns=columns, show="headings", selectmode="extended")
        self.tree.tag_configure("empty", foreground="#8EA3B5")
        self.tree.tag_configure("UNKNOWN", foreground="#94A3B8")
        self.tree.tag_configure("CHECKING", foreground="#FACC15")
        self.tree.tag_configure("LIVE", foreground="#4ADE80")
        self.tree.tag_configure("DIE", foreground="#F87171")
        self.tree.tag_configure("ERROR", foreground="#FB923C")

        self.tree.heading("select", text="[✔]")
        self.tree.heading("id", text="STT")
        self.tree.heading("uid", text="UID")
        self.tree.heading("name", text="Tên Nick")
        self.tree.heading("password", text="Password")
        self.tree.heading("2fa", text="2FA Key")
        self.tree.heading("cookie", text="Cookie")
        self.tree.heading("email", text="Email")
        self.tree.heading("proxy", text="Proxy")
        self.tree.heading("status", text="Trạng Thái")

        self.tree.column("select", width=45, anchor="center")
        self.tree.column("id", width=45, anchor="center")
        self.tree.column("uid", width=130, anchor="center")
        self.tree.column("name", width=120)
        self.tree.column("password", width=100, anchor="center")
        self.tree.column("2fa", width=110, anchor="center")
        self.tree.column("cookie", width=220)
        self.tree.column("email", width=140)
        self.tree.column("proxy", width=130, anchor="center")
        self.tree.column("status", width=110, anchor="center")

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
# [KẾT THÚC THAY THẾ]

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
        for result_type in ("completed", "die"):
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
                    f"DIE: {counts.get('die', 0)}"
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
                state["current_action"],
            ),
            tags=(state["status"],),
        )
        self.refresh_state_summary()

    def refresh_state_summary(self):
        summary = self.account_states.summary()
        total = sum(summary.values())
        if hasattr(self, "lbl_queue_info"):
            self.lbl_queue_info.config(
                text=(
                    f"Tổng: {total} • LIVE: {summary['LIVE']} • "
                    f"DIE: {summary['DIE']} • ERROR: {summary['ERROR']}"
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
                    f"DIE {summary['DIE']}  •  ERROR {summary['ERROR']}"
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
            lines = state["logs"] if state else []
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
            self.create_page_account_results = {"completed": {}, "die": {}}
        self.refresh_create_page_results_dialog()

    def record_create_page_account_result(
        self, index, result_type, reason="", created_count=0, target_count=0
    ):
        if result_type not in {"completed", "die"}:
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
            "uid": state.get("uid", ""),
            "raw_line": source_line,
            "created_count": int(created_count or 0),
            "target_count": int(target_count or 0),
            "reason": str(reason or ""),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        opposite = "die" if result_type == "completed" else "completed"
        with self.create_page_result_lock:
            self.create_page_account_results[opposite].pop(key, None)
            self.create_page_account_results[result_type][key] = record
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
                    vals[9] = " | ".join(msg_parts)
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
                writer.writerow(["STT", "UID", "Tên Nick", "Proxy", "Trạng thái", "Thời gian"])
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in items:
                    vals = list(self.tree.item(item, "values"))
                    writer.writerow([vals[1], vals[2], vals[3], vals[8], vals[9], now_str])
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo tại:\n{file_path}")
    def reload_table_from_text(self, checked_indexes=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        raw_acc_lines = [
            line for line in self.txt_accounts.get("1.0", "end").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        proxy_lines = [p.strip() for p in self.txt_proxies.get("1.0", "end").splitlines() if p.strip() and not p.startswith("#")]
        ratio = int(self.ent_proxy_ratio.get()) if self.ent_proxy_ratio.get().isdigit() else 20
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
            if assigned_proxy == "Không dùng" and proxy_lines:
                if self.proxy_mode.get() == "random":
                    assigned_proxy = random.choice(proxy_lines)
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

            # Điền đúng thứ tự 10 cột: Checkbox, STT, UID, Tên, Password, 2FA Key, Cookie, Email, Proxy, Status
            # Thêm cột đầu tiên là checkbox [✔] mặc định
            self.tree.insert("", "end", iid=str(idx), values=(
                "[✔]" if checked_indexes is None or idx in checked_indexes else "[ ]",
                idx, 
                parsed["uid"], 
                parsed["name"], 
                parsed["pwd"], 
                parsed["2fa"], 
                parsed["cookie"], 
                parsed["email"], 
                assigned_proxy, 
                "CHƯA KIỂM TRA"
            ), tags=("UNKNOWN",))

        self.account_states.sync(account_records)
        for index in self.account_states.indexes():
            item_id = str(index)
            state = self.account_states.get(index)
            if self.tree.exists(item_id) and state:
                values = list(self.tree.item(item_id, "values"))
                values[9] = ACCOUNT_STATUS_LABELS[state["status"]]
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
        if self.is_running or (self.run_thread and self.run_thread.is_alive()):
            self.log("[!] Tiến trình trước vẫn đang đóng. Vui lòng chờ hoàn tất.")
            return

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
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(text="● Đang chạy...", fg="#F59E0B")
        self.run_thread = threading.Thread(target=self.run_process, daemon=True)
        self.run_thread.start()

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
        was_stopped = self.stop_requested
        self.is_running = False
        self.run_thread = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        if hasattr(self, 'lbl_status_indicator'):
            self.lbl_status_indicator.config(
                text="● Đã dừng" if was_stopped else "● Hoàn thành",
                fg="#EF4444" if was_stopped else "#10B981",
            )
        self.stop_requested = False

    def run_process(self):
        """Khởi tạo vòng lặp sự kiện tương thích tuyệt đối với Windows và Playwright"""
        try:
            # Chạy trực tiếp worker chính, không gọi lại set_event_loop_policy để tránh xung đột luồng
            asyncio.run(self.main_worker())
        except Exception as e:
            self.log(f"[-] Lỗi hệ thống luồng chính [{type(e).__name__}]: {e}")
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

            # Test a real HTTPS route so a dead/auth-failed proxy cannot pass on about:blank.
            health_response = await page.goto(
                "https://www.facebook.com/robots.txt",
                wait_until="domcontentloaded",
                timeout=15000,
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
                    except Exception:
                        btn_count = 0

                    # =====================================
                    # CÒN NÚT ADD FRIEND
                    # =====================================
                    if btn_count > 0:
                        try:
                            btn = btns.first
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            confirmed, detail = await self.click_and_confirm_friend_request(page, btn)
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

        self.log(f"[✓] [{acc_name}] Hoàn thành. Tổng lời mời đã gửi: {sent}")
        return sent

    async def click_and_confirm_friend_request(self, page, button):
        """Click once and count only a request confirmed by Facebook's UI."""
        blocked_phrases = (
            "không thể gửi lời mời", "can't send friend request",
            "bạn đã gửi quá nhiều", "you've sent too many",
            "tạm thời bị chặn", "temporarily blocked",
        )
        before_count = await page.locator(FRIEND_REQUEST_SENT_SELECTORS).count()
        before_state = []
        for attribute in ("aria-label", "aria-pressed", "aria-disabled", "data-testid"):
            try:
                before_state.append(await button.get_attribute(attribute) or "")
            except Exception:
                before_state.append("")
        try:
            before_state.append(await button.inner_text(timeout=500) or "")
        except Exception:
            before_state.append("")
        before_state = tuple(before_state)
        await button.click(timeout=5000)

        stable_changed_polls = 0
        for _ in range(8):
            await asyncio.sleep(0.5)
            has_feedback_overlay = False
            alerts = page.locator('[role="alert"], [role="dialog"]')
            if await alerts.count() > 0:
                has_feedback_overlay = True
                try:
                    alert_text = (await alerts.last.inner_text(timeout=500)).casefold()
                    if any(phrase in alert_text for phrase in blocked_phrases):
                        return False, alert_text[:160]
                except Exception:
                    pass

            try:
                if await button.count() == 0 or not await button.is_visible():
                    if not has_feedback_overlay:
                        return True, "Facebook đã thay thế nút gửi lời mời"
                    continue

                current_state = []
                for attribute in ("aria-label", "aria-pressed", "aria-disabled", "data-testid"):
                    current_state.append(await button.get_attribute(attribute) or "")
                current_state.append(await button.inner_text(timeout=500) or "")
                current_state = tuple(current_state)
                if current_state != before_state and any(current_state):
                    stable_changed_polls += 1
                    if stable_changed_polls >= 2 and not has_feedback_overlay:
                        return True, "Facebook đã đổi trạng thái nút"
                else:
                    stable_changed_polls = 0
            except Exception:
                pass

            after_count = await page.locator(FRIEND_REQUEST_SENT_SELECTORS).count()
            if after_count > before_count:
                return True, "Facebook đã hiển thị trạng thái đã gửi"

        return False, "không thấy trạng thái xác nhận sau khi bấm"

    async def verify_facebook_session(self, page, context):
        """Distinguish a real logged-in session from login/checkpoint shells."""
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

    async def ensure_personal_profile(self, context, page, acc_name):
        """Clear Facebook's Page-profile selector cookie before another Page job."""
        cookies = await context.cookies("https://www.facebook.com/")
        if not any(cookie.get("name") == "i_user" for cookie in cookies):
            return True
        try:
            await context.clear_cookies(name="i_user")
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(2)
            remaining = await context.cookies("https://www.facebook.com/")
            is_personal = not any(cookie.get("name") == "i_user" for cookie in remaining)
            if not is_personal:
                self.log(f"[!] [{acc_name}] Chưa chuyển chắc chắn về hồ sơ cá nhân.")
            return is_personal
        except Exception as exc:
            self.log(f"[!] [{acc_name}] Không thể chuyển về hồ sơ cá nhân: {exc}")
            return False

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
        created_count = 0
        results = []

        def record_result(result):
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
                    if is_invalid_facebook_account_url(page.url):
                        reason = f"Session không hợp lệ trước Create Page: {page.url}"
                        set_page_flow_state("FAILED", reason)
                        self.set_account_failure(idx, "invalid_login", reason)
                        return results
                    set_page_flow_state("OPEN_CREATE_PAGE", page_name)
                    async def navigate_to_creation():
                        return await page.goto(
                            "https://www.facebook.com/pages/creation/",
                            wait_until="domcontentloaded",
                            timeout=45000,
                        )

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
                if "/pages/creation" not in cur_url:
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
                
                await name_input.fill(page_name)
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
                    await cat_input.fill(category_name)
                    
                    # Chờ 2.5s để Facebook gửi request tải danh sách gợi ý (Listbox)
                    await asyncio.sleep(2.5)

                    cat_option = page.locator('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]').first
                    try:
                        await cat_option.wait_for(state="visible", timeout=5000)
                        await cat_option.click()
                    except Exception:
                        # Phương án dự phòng bằng bàn phím
                        await page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                    await asyncio.sleep(1.5)
                else:
                    self.log(f"[!] [{acc_name}] Không tìm thấy ô nhập Hạng mục.")
                    record_result(build_create_page_result(
                        "ERROR", acc_name, page_name, category_name,
                        technical_error="Không tìm thấy combobox category.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
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
                    if not await wait_for_locator_ready(create_btn, timeout=10000):
                        record_result(build_create_page_result(
                            "ERROR", acc_name, page_name, category_name,
                            technical_error="Nút Submit không chuyển sang trạng thái khả dụng.",
                            retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                        ))
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
                    await create_btn.scroll_into_view_if_needed()
                    await create_btn.click()
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

                verified_page_identity = {"url": "", "id": ""}
                invalid_session_reason = ""
                for _ in range(10):
                    if not self.is_running or getattr(self, "stop_requested", False):
                        set_page_flow_state("CANCELLED", "Dừng trong khi xác minh")
                        return results
                    await asyncio.sleep(2)
                    cur_url = page.url.lower()
                    if is_invalid_facebook_account_url(cur_url):
                        invalid_session_reason = (
                            f"Tài khoản mất phiên đăng nhập sau khi gửi tạo Page: {page.url}"
                        )
                        self.log(f"[!] [{acc_name}] Bị Checkpoint ngay sau khi ấn Tạo!")
                        break

                    candidate_identity = await self.get_current_page_identity(page)
                    if is_verified_page_identity(candidate_identity):
                        verified_page_identity = candidate_identity
                        break

                    body_text = (await page.inner_text("body")).lower()
                    
                    if any(err in body_text for err in ["quá nhiều trang", "too many pages", "xảy ra lỗi", "went wrong"]):
                        self.log(f"[-] [{acc_name}] Bị chặn tạo: Đã tạo quá nhiều Trang / Lỗi server.")
                        if hasattr(self, 'take_error_snapshot'):
                            await self.take_error_snapshot(page, acc_name, "rate_limit_page")
                        break
                    
                if invalid_session_reason:
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason=invalid_session_reason,
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    self.set_account_failure(idx, "invalid_login", invalid_session_reason)
                    return results

                if not is_verified_page_identity(verified_page_identity):
                    self.log(
                        f"[-] [{acc_name}] Tạo trang thất bại hoặc chưa xác minh được Page URL/ID."
                    )
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="Không xác minh được Page URL/ID sau khi Submit.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

                # ======================================================
                # BƯỚC 6: BẤM "TIẾP" LIÊN TỤC CHO ĐẾN HÌNH 2 (GIAO DIỆN TRANG CHÍNH)
                # ======================================================
                self.log(f"[*] [{acc_name}] Đang bấm 'Tiếp/Xong' liên tục để chuyển sang Trang chính...")
                for _ in range(12):
                    if not self.is_running: break
                    cur_url = page.url.lower()
                    if "facebook.com/pages/creation" not in cur_url:
                        current_identity = await self.get_current_page_identity(page)
                        if is_verified_page_identity(current_identity):
                            self.log(f"[✔] [{acc_name}] Đã vào đến giao diện Trang chính!")
                            break

                    btn_selectors = (
                        'div[role="dialog"] button[type="submit"]:visible, '
                        'div[role="button"]:has-text("Tiếp"), div[role="button"]:has-text("Next"), '
                        'div[role="button"]:has-text("Xong"), div[role="button"]:has-text("Done"), '
                        'div[role="button"]:has-text("Hoàn tất"), '
                        'div[aria-label="Tiếp"], div[aria-label="Next"], '
                        'div[aria-label="Xong"], div[aria-label="Done"]'
                    )
                    wiz_btn = page.locator(btn_selectors).first
                    if await wiz_btn.count() > 0 and await wiz_btn.is_visible():
                        try:
                            await wiz_btn.click(timeout=3000)
                            await asyncio.sleep(3)
                        except Exception:
                            pass
                    else:
                        await asyncio.sleep(2)

                await page.keyboard.press("Escape")
                await asyncio.sleep(1)

                page_identity = await self.get_current_page_identity(page)
                if not is_verified_page_identity(page_identity):
                    page_identity = verified_page_identity
                if not is_verified_page_identity(page_identity):
                    self.log(
                        f"[-] [{acc_name}] Không xác minh được Page URL/ID sau khi tạo; "
                        "không ghi nhận thành công."
                    )
                    record_result(build_create_page_result(
                        "FAILED", acc_name, page_name, category_name,
                        reason="Page URL/ID không còn xác minh được sau wizard.",
                        retry_count=retry_count, account_index=idx, proxy=resolved_proxy,
                    ))
                    continue

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

                # ======================================================
                # BƯỚC 7: NUÔI NICK THEO CẤU HÌNH NGƯỜI DÙNG (NHẬP 0 SẼ BỎ QUA)
                # ======================================================
                if created_count < effective_max_pages and self.is_running:
                    surf_mins = self.run_config.get("feed_surf_min", 10)
                    watch_mins = self.run_config.get("watch_review_min", 5)

                    if surf_mins > 0:
                        await self.human_surf_feed(page, acc_name, duration_minutes=surf_mins)

                    if watch_mins > 0:
                        await self.human_watch_movie_reviews(page, acc_name, duration_minutes=watch_mins)

                    self.log(f"[*] [{acc_name}] Đang chuyển về tài khoản cá nhân...")
                    if not await self.ensure_personal_profile(context, page, acc_name):
                        self.log(
                            f"[!] [{acc_name}] Dừng tạo thêm Page để tránh thao tác nhầm bằng danh tính Page."
                        )
                        break
                    page_delay = (int(min_page_del) + int(max_page_del)) // 2
                    if page_delay > 0:
                        self.log(f"[*] [{acc_name}] Chờ {page_delay} giây trước Page tiếp theo...")
                        await asyncio.sleep(page_delay)

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
                    confirmed, detail = await self.click_and_confirm_friend_request(page, add_btn)
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
                btn = page.locator(ADD_FRIEND_SELECTORS).first
                if await btn.count() > 0 and await btn.is_visible():
                    confirmed, detail = await self.click_and_confirm_friend_request(page, btn)
                    append_csv_result(
                        "friend_actions.csv",
                        ["time", "account", "target", "method", "status", "detail"],
                        {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "account": acc_name,
                            "target": target,
                            "method": "uid",
                            "status": "sent" if confirmed else "not_confirmed",
                            "detail": detail,
                        },
                    )
                    if confirmed:
                        sent += 1
                        self.log(f"[✔] [{acc_name}] Facebook xác nhận đã gửi: {target}")
                        await asyncio.sleep(random.randint(min_del, max_del))
                    else:
                        self.log(f"[!] [{acc_name}] Không tính {target}: {detail}")
        except Exception as e:
            self.log(f"[-] [{acc_name}] Lỗi kết bạn UID: {e}")
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
            self.log(f"\n[🚀 LUỒNG BẮT ĐẦU] Nick {idx}: {acc_name} (Proxy: {assigned_proxy_str or 'None'})")
            self.log(
                f"[*] [{acc_name}] Context: locale={normalize_account_locale(account_locale)}; "
                f"country={account_country or 'N/A'}; timezone={account_timezone or 'AUTO'}"
            )

            cookies = parse_cookies(cookie_str)
            proxy_cfg = parse_proxy(assigned_proxy_str)
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
            # Tự động gọi SuiProxy lấy IP mới riêng cho từng nick
            if config.get("proxy_mode") == "rotating_api" and config.get("proxy_api"):
                self.log(f"[*] [{acc_name}] Đang gọi SuiProxy lấy IP mới...")
                async with self.proxy_api_lock:
                    fresh_proxy = await asyncio.to_thread(fetch_proxy_from_api, config["proxy_api"])
                if fresh_proxy:
                    assigned_proxy_str = fresh_proxy
                    proxy_cfg = parse_proxy(assigned_proxy_str)
                    if not proxy_cfg:
                        reason = f"[{acc_name}] API trả về proxy sai định dạng."
                        self.set_account_failure(idx, "proxy", reason)
                        self.update_tree_row(str(idx), status="ERROR")
                        return
                    self.log(f"[✔] [{acc_name}] Đã cấp IP SuiProxy mới: {assigned_proxy_str}")
                    await asyncio.sleep(2)
                else:
                    reason = f"[{acc_name}] API proxy không trả về IP; dừng để tránh dùng IP thật."
                    self.set_account_failure(idx, "proxy", reason)
                    self.update_tree_row(str(idx), status="ERROR")
                    return
            
            browser = None
            context = None
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

                # --- BẮT ĐẦU LOGIC ĐĂNG NHẬP CHUẨN XÁC ---
                is_valid_session = False
                
                # Nạp Cookie Facebook
                if cookies:
                    await context.add_cookies(cookies)
                    
                    self.log(f"[*] [{acc_name}] Đang mở trang chủ để kích hoạt Cookie...")
                    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
                    await asyncio.sleep(4)
                    
                    is_valid_session, session_detail = await self.verify_facebook_session(page, context)
                    if not is_valid_session:
                        reason = f"[{acc_name}] Phiên Cookie không hợp lệ: {session_detail}"
                        self.set_account_failure(idx, "invalid_cookie", reason)
                        self.update_tree_row(str(idx), status="DIE")
                        return
                    self.log(f"[✔] [{acc_name}] {session_detail}")

                # Đăng nhập Facebook bằng UID/email và mật khẩu
                elif account_type == "RAW" and login_user and login_password:
                    login_result, login_detail = await self.login_facebook_user_pass(
                        page, context, login_user, login_password
                    )
                    if login_result == LOGIN_TECHNICAL_ERROR:
                        reason = f"[{acc_name}] Lỗi kỹ thuật khi đăng nhập: {login_detail}"
                        self.set_account_failure(idx, "automation", reason)
                        self.update_tree_row(str(idx), status="ERROR")
                        return
                    is_valid_session = login_result == LOGIN_SUCCESS
                else:
                    reason = f"[{acc_name}] Thiếu dữ liệu đăng nhập hợp lệ."
                    self.set_account_failure(idx, "input", reason)
                    self.update_tree_row(str(idx), status="ERROR")
                    return
                
                # Chốt chặn: Nếu không đăng nhập thành công thì thoát luôn, không chạy tác vụ bên dưới
                if not is_valid_session:
                    reason = f"[{acc_name}] Đăng nhập không hợp lệ: {login_detail}"
                    self.set_account_failure(idx, "invalid_login", reason)
                    self.update_tree_row(str(idx), status="DIE")
                    return  
                # --- KẾT THÚC LOGIC ĐĂNG NHẬP ---

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
                # 1. Kết bạn theo tên
                if modes.get("by_name", False):
                    total_sent += (await self.run_add_by_name(page, acc_name, idx, targets_by_mode["by_name"], target_total, min_del, max_del)) or 0

                # 2. Thành viên nhóm
                if modes.get("by_group", False):
                    total_sent += (await self.run_add_by_group(page, acc_name, idx, targets_by_mode["by_group"], target_total, min_del, max_del)) or 0

                # 3. Theo UID / Profile
                if modes.get("by_uid", False):
                    total_sent += (await self.run_add_by_uid(page, acc_name, idx, targets_by_mode["by_uid"], target_total, min_del, max_del)) or 0

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

                self.set_account_state(
                    idx,
                    status="LIVE",
                    current_action=create_page_completion_action or "Hoàn thành",
                )
                self.update_tree_row(str(idx), sent_today=total_sent, status="LIVE")
                self.log(f"[✔ XONG] Nick {acc_name} đã hoàn thành ({total_sent} kết quả đã xác nhận).")

            except asyncio.CancelledError:
                current_state = self.account_states.get(idx)
                if current_state and current_state["status"] == "CHECKING":
                    self.set_account_state(idx, status="ERROR", current_action="Đã dừng khi đang kiểm tra")
                    self.update_tree_row(str(idx), status="ERROR")
                else:
                    self.set_account_state(idx, current_action="Đã dừng")
                self.log(f"[!] Đã dừng nick {acc_name} theo yêu cầu.")
                raise
            except Exception as e:
                reason = f"Lỗi nick {acc_name}: {e}"
                self.set_account_failure(idx, "automation", reason)
                self.update_tree_row(str(idx), status="ERROR")
                # Bắn cảnh báo về Telegram
                t_token = config.get("tele_token", "")
                t_id = config.get("tele_chatid", "")
                if t_token and t_id:
                    send_telegram_alert(t_token, t_id, f"⚠️ CẢNH BÁO: Nick [{acc_name}] gặp sự cố/checkpoint!\nChi tiết: {e}")
            
            finally:
                # --- SIÊU NĂNG LỰC: DÙ LỖI HAY KHÔNG CŨNG BẮT BUỘC ĐÓNG TRÌNH DUYỆT ĐỂ CHỐNG TREO RAM ---
                await close_browser_resources(context, browser)
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
            cookie_str = parsed.get("cookie", "")
            if parsed["type"] == "TOKEN":
                self.set_account_failure(
                    idx,
                    "input",
                    f"[{acc_name}] Token EAAB/EAAA không thể thay thế Cookie đăng nhập.",
                )
                continue
            has_raw_login = bool(
                parsed["type"] == "RAW"
                and parsed.get("uid")
                and (parsed.get("password") or parsed.get("pwd"))
            )
            if not cookie_str and not has_raw_login:
                self.set_account_failure(idx, "input", f"[{acc_name}] Thiếu dữ liệu đăng nhập.")
                continue

            assigned_proxy_str = resolve_account_proxy(
                parsed.get("proxy"), resolved_proxies, idx
            ) or None
            if (
                not assigned_proxy_str
                and config.get("proxy_mode") != "rotating_api"
                and proxy_lines
            ):
                # Compatibility for non-UI callers without a captured proxy map.
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
                "account_type": parsed["type"],
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
                self.log(
                    f"[KẾT THÚC ĐỢT] Đợt {batch_number}/{len(batches)} • "
                    f"LIVE: {batch_summary['LIVE']} • DIE: {batch_summary['DIE']} • "
                    f"ERROR: {batch_summary['ERROR']}"
                )

        if self.stop_requested:
            self.log("\n[!] Tiến trình đã dừng; các luồng đang chạy đã được đóng an toàn.")
            return

        final_summary = self.account_states.summary([job["idx"] for job in account_jobs])
        self.log(
            f"[KẾT THÚC ĐỢT CHẠY] LIVE: {final_summary['LIVE']} • "
            f"DIE: {final_summary['DIE']} • ERROR: {final_summary['ERROR']}"
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
        acc_name = vals[3] if len(vals) > 3 else vals[1]
        proxy_str = vals[8] if len(vals) > 8 else "Không dùng"

        parsed_account = self.get_parsed_account_for_item(item)
        cookie_str = parsed_account.get("cookie", "") if parsed_account else ""

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
