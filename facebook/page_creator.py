import asyncio
import random
from datetime import datetime


import re
import unicodedata
from urllib.parse import urlparse
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
    structural_failure="",
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
        "structural_failure": structural_failure,
    }

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

def parse_page_plan(value: str):
    """Parse `page name|category`; old one-column page names remain valid."""
    parts = [part.strip() for part in str(value or "").split("|", 1)]
    return {
        "name": parts[0] if parts and parts[0] else generate_random_person_name(),
        "category": parts[1] if len(parts) > 1 and parts[1] else "Blog cá nhân",
    }

def build_create_page_plans(targets, max_pages, name_generator=None):
    """Build the requested Page plans while preserving legacy auto-name behavior."""
    if name_generator is None:
        name_generator = generate_random_person_name

    requested = max(1, int(max_pages))
    plans = [
        str(target).strip()
        for target in (targets or [])
        if str(target or "").strip()
    ][:requested]

    while len(plans) < requested:
        plans.append(f"{name_generator()}|Blog cá nhân")

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

def build_page_context(
    account_id,
    page_name,
    category,
    proxy="",
    locale="AUTO",
    locale_normalizer=None,
):
    if locale_normalizer is None:
        locale_normalizer = lambda value: str(value or "AUTO")

    return {
        "owner_account_id": str(account_id or ""),
        "requested_page_name": str(page_name or ""),
        "requested_category": str(category or ""),
        "proxy": str(proxy or ""),
        "locale": locale_normalizer(locale),
        "page_id": "",
        "page_url": "",
        "creation_status": "PENDING",
        "verification_status": "PENDING",
        "created_at": "",
    }


def transition_page_context(
    page_context,
    state,
    page_identity=None,
    page_flow_states=None,
    identity_validator=None,
):
    normalized_state = str(state or "").upper()

    if page_flow_states is not None and normalized_state not in page_flow_states:
        raise ValueError(f"Create Page state không hợp lệ: {state}")

    if (
        normalized_state == "SUCCESS"
        and identity_validator is not None
        and not identity_validator(page_identity or {})
    ):
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


def is_page_policy_rejected(text):
    normalized = " ".join(str(text or "").casefold().split())
    return (
        "error occurred while creating the page" in normalized
        and "page policies" in normalized
    )


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


def page_identity_keys(page_url="", page_id=""):
    keys = set()
    clean_id = str(page_id or "").strip()
    clean_url = str(page_url or "").strip().rstrip("/").casefold()
    if clean_id:
        keys.add(f"id:{clean_id}")
    if clean_url:
        keys.add(f"url:{clean_url}")
    return keys


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
