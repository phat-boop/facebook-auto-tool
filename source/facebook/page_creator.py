import asyncio
import random
from datetime import datetime


import re
import unicodedata
from urllib.parse import urlparse
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import time
import uuid
from long_run import DuplicatePageResult
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

    if (
        not evidence
        or not job.get("submitted")
        or job.get("owner_account_id") != owner_account_id
    ):
        return empty

    canonical = evidence.get("canonical")

    identity = extract_facebook_page_identity([canonical, url])

    page_id = str(evidence.get("page_id") or "")

    page_type = str(evidence.get("page_type") or "").upper()

    if page_type != "PAGE":
        return empty

    if not page_id.isdigit() or len(page_id) < 5:
        return empty

    if not identity["url"]:
        return empty

    if identity["id"] and identity["id"] != page_id:
        return empty

    observed_name = normalize_ui_text(evidence.get("name"))
    expected_name = normalize_ui_text(job["page_name"])

    if not observed_name or observed_name != expected_name:
        return empty

    canonical = evidence.get("canonical")

    if (
        canonical
        and facebook_page_reference(canonical)
        != facebook_page_reference(url)
    ):
        return empty

    if (
        page_id == str(job.get("owner_uid") or "")
        or page_id in job.get("prior_page_ids", set())
    ):
        return empty

    return {
        **identity,
        "id": page_id,
        "owner_account_id": owner_account_id,
        "page_job_id": job["page_job_id"],
        "verified": True,
    }

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


CREATE_PAGE_BUTTON_PATTERN = re.compile(
    r"^(Tạo Trang|Create Page|Créer une Page|Crear página|Criar Página|"
    r"Seite erstellen|Buat Halaman|สร้างเพจ|Gumawa ng Page|ページを作成|페이지 만들기)$",
    re.IGNORECASE,
)


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


def is_invalid_facebook_account_url(url):
    normalized = str(url or "").casefold()
    return any(
        marker in normalized
        for marker in ("/login", "checkpoint", "challenge", "disabled", "suspended")
    )


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
                category_selected, category_reason = await self.select_page_category(
                    page,
                    cat_input,
                    category_name,)

                if not category_selected:
                    record_result(
                        build_create_page_result(
                            "FAILED",
                            acc_name,
                            page_name,
                            category_name,
                            reason=category_reason,
                            account_index=idx,
                            proxy=resolved_proxy,
                        )
                    )
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
                self.log(f"[PAGE][SUBMIT] [{acc_name}] name={page_name} category={category_name}")
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

            for _ in range(15):
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

            page_identity = {}
            for _ in range(3):
                page_identity = await self.verify_created_page(page, idx, current_page_job)
                self.log(f"[PAGE][VERIFY] [{acc_name}] {page_identity}")
                if is_verified_page_identity(page_identity):
                    break
                await asyncio.sleep(3.0)
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
