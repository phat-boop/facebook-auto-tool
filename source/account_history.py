"""Persistent account outcomes, without storing login credentials."""
import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from long_run import DuplicatePageResult

COUNTER_FIELDS = (
    "page_success_count", "page_failed_count", "friend_success_count", "friend_failed_count",
)
SECRET_FIELDS = {
    "password", "pwd", "twofa", "2fa", "cookie", "token", "raw_line", "source_line",
    "canonical_line", "fields", "import_fields", "unknown_fields", "account_record",
}

def history_account_id(state):
    value = str(state.get("uid") or state.get("account_id") or "")
    if any(char in value for char in "|=;") or value.startswith("EAA"):
        return "account:" + hashlib.sha256(value.encode()).hexdigest()
    return value


def safe_proxy_label(value):
    value = str(value or "")
    if not value:
        return ""
    try:
        if "://" in value or "@" in value:
            parsed = urlsplit(value if "://" in value else "http://" + value)
            host = parsed.hostname or ""
            if ":" in host:
                host = "[" + host + "]"
            return f"{parsed.scheme}://{host}:{parsed.port}" if host and parsed.port else "INVALID_PROXY"
        match = re.match(r'^(\[[^\]]+\]|[^:]+):(\d+)', value)
        return match.group(0) if match else "INVALID_PROXY"
    except ValueError:
        return "INVALID_PROXY"


def redact_history_text(text, state):
    value = str(text or "")
    secrets = [str(state.get(key) or "") for key in ("raw_line", "source_line", "canonical_line", "password", "pwd", "twofa", "2fa", "cookie", "token")]
    for cookie in str(state.get("cookie") or "").split(";"):
        name, separator, cookie_value = cookie.strip().partition("=")
        if separator and name != "c_user":
            secrets.append(cookie_value)
    proxy = str(state.get("proxy") or "")
    if proxy:
        value = value.replace(proxy, safe_proxy_label(proxy))
        legacy = re.fullmatch(r'(?:\[[^\]]+\]|[^:\s]+):\d+:([^:]*):(.*)', proxy)
        if legacy:
            secrets.extend(legacy.groups())
        else:
            try:
                parsed = urlsplit(proxy if "://" in proxy else "http://" + proxy)
                secrets.extend(unquote(item) for item in (parsed.username, parsed.password) if item)
            except ValueError:
                value = value.replace(proxy, "INVALID_PROXY")
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            value = value.replace(secret, "[REDACTED]")
    value = re.sub(r'\b(?:c_user|xs|sb|datr|fr|sessionid|access_token|token|password|2fa)\s*=\s*[^;\s]+', '[REDACTED]', value, flags=re.I)
    value = re.sub(r'\bEAA[A-Za-z0-9_]+', '[REDACTED]', value)
    value = re.sub(r'(?i)(https?|socks[45])://[^\s/@]+@', r'\1://', value)
    return value


class AccountHistoryStore:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.lock, sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY, last_status TEXT, last_task_result TEXT,
                    last_action TEXT, first_seen_at TEXT, last_seen_at TEXT,
                    last_run_at TEXT, last_error TEXT, last_checkpoint_at TEXT,
                    page_summary TEXT, friend_summary TEXT, proxy_label TEXT, tasks TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL,
                    timestamp TEXT, module TEXT, event_type TEXT, result TEXT, message TEXT
                );
                CREATE INDEX IF NOT EXISTS events_account ON events(account_id, id);
                CREATE TABLE IF NOT EXISTS page_identities (
                    identity_key TEXT PRIMARY KEY, account_id TEXT NOT NULL, job_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS history_metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            db.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in db.execute("PRAGMA table_info(accounts)")}
            additions = {"login_mode": "TEXT", "last_update": "TEXT",
                         **{field: "INTEGER NOT NULL DEFAULT 0" for field in COUNTER_FIELDS}}
            for column, definition in additions.items():
                if column not in columns:
                    db.execute(f"ALTER TABLE accounts ADD COLUMN {column} {definition}")
            if "payload" not in {row[1] for row in db.execute("PRAGMA table_info(events)")}:
                db.execute("ALTER TABLE events ADD COLUMN payload TEXT")

    def save(self, state, module="ACCOUNT", event_type="STATE", message="", task_event=None):
        key = history_account_id(state)
        if not key:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = state.get("status", "UNKNOWN")
        action = redact_history_text(state.get("current_action"), state)
        def sanitize(value):
            if isinstance(value, dict):
                return {key: sanitize(item) for key, item in value.items()
                        if str(key).casefold() not in SECRET_FIELDS}
            if isinstance(value, (list, tuple, set, frozenset)):
                return [sanitize(item) for item in value]
            if isinstance(value, str):
                return redact_history_text(value, state)
            return value if value is None or isinstance(value, (bool, int, float)) else "[UNSUPPORTED]"

        tasks = sanitize(state.get("tasks", {}))
        task_result = state.get("last_task_result", "PENDING")
        message = redact_history_text(message or action, state)
        error = next((task.get("detail", "") for task in tasks.values()
                      if task.get("status") in {"ERROR", "FAILED"}), action)
        last_error = redact_history_text(state.get("last_error") or error, state)
        login_mode = state.get("login_mode")
        login_mode = login_mode if login_mode in {"COOKIE", "FALLBACK_LOGIN"} else None
        counters = [max(0, int(state.get(field) or 0)) for field in COUNTER_FIELDS]
        event_task = sanitize(task_event) if task_event is not None else tasks.get(module, {})
        identity_event = task_event if task_event is not None else state.get("tasks", {}).get(module, {})
        # Events keep one outcome each; avoid copying all earlier outcomes into every event.
        payload = json.dumps({**event_task, "outcomes": event_task.get("outcomes", [])[-1:]}) if event_type == "TASK" else None
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if module == "CREATE_PAGE" and event_type == "TASK" and identity_event.get("status") == "SUCCESS":
                # Identity checks use verified business fields, not redacted display text.
                for page in identity_event.get("outcomes", []):
                    if not isinstance(page, dict) or not page.get("owner_account_id") or not page.get("page_job_id"):
                        continue  # Generic/legacy task events are not verified Page claims.
                    if str(page["owner_account_id"]) != str(state.get("account_id") or key):
                        raise ValueError("Page owner does not match account.")
                    keys = page_result_identity_keys(page)
                    if not keys:
                        raise ValueError("Verified Page result has no identity.")
                    previous_count = db.execute("SELECT page_success_count FROM accounts WHERE account_id=?", (key,)).fetchone()
                    for identity in keys:
                        existing = db.execute("SELECT account_id,job_id FROM page_identities WHERE identity_key=?", (identity,)).fetchone()
                        if existing and (existing != (key, page["page_job_id"]) or not previous_count or counters[0] != previous_count[0]):
                            raise DuplicatePageResult("Page URL/ID đã tồn tại trong kết quả SQLite.")
                    db.executemany("INSERT OR IGNORE INTO page_identities VALUES (?, ?, ?)",
                                   ((identity, key, page["page_job_id"]) for identity in keys))
            db.execute("""INSERT INTO accounts (
                    account_id,last_status,last_task_result,last_action,first_seen_at,last_seen_at,
                    last_run_at,last_error,last_checkpoint_at,page_summary,friend_summary,proxy_label,tasks,
                    login_mode,last_update,page_success_count,page_failed_count,friend_success_count,friend_failed_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    last_status=excluded.last_status, last_task_result=excluded.last_task_result,
                    last_action=excluded.last_action, last_seen_at=excluded.last_seen_at,
                    last_run_at=COALESCE(excluded.last_run_at, accounts.last_run_at),
                    last_error=COALESCE(excluded.last_error, accounts.last_error),
                    last_checkpoint_at=COALESCE(excluded.last_checkpoint_at, accounts.last_checkpoint_at),
                    page_summary=excluded.page_summary, friend_summary=excluded.friend_summary,
                    proxy_label=excluded.proxy_label, tasks=excluded.tasks,
                    login_mode=COALESCE(excluded.login_mode, accounts.login_mode), last_update=excluded.last_update,
                    page_success_count=excluded.page_success_count, page_failed_count=excluded.page_failed_count,
                    friend_success_count=excluded.friend_success_count, friend_failed_count=excluded.friend_failed_count""", (
                key, status, task_result, action, now, now,
                now if status == "CHECKING" else None,
                last_error if state.get("last_error") or status in {"DIE", "ERROR", "CHECKPOINT"} or task_result in {"FAILED", "ERROR"} else None,
                now if status == "CHECKPOINT" else None,
                json.dumps(tasks.get("CREATE_PAGE", {})), json.dumps(tasks.get("FRIEND_REQUEST", {})),
                safe_proxy_label(state.get("effective_proxy", state.get("proxy", ""))), json.dumps(tasks),
                login_mode, now, *counters,
            ))
            result = event_task.get("status", task_result) if module != "ACCOUNT" else status
            previous = db.execute("SELECT module,event_type,result,message,payload FROM events WHERE account_id=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
            event = (module, event_type, result, message, payload)
            if previous != event:
                db.execute("INSERT INTO events(account_id,timestamp,module,event_type,result,message,payload) VALUES (?, ?, ?, ?, ?, ?, ?)", (key, now, *event))

    def page_identity_bootstrapped(self):
        with self.lock, sqlite3.connect(self.path) as db:
            return db.execute("SELECT 1 FROM history_metadata WHERE name='legacy_page_identities'").fetchone() is not None

    def bootstrap_page_identities(self, identities):
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM history_metadata WHERE name='legacy_page_identities'").fetchone():
                return
            identities = set(identities)
            for (summary,) in db.execute("SELECT page_summary FROM accounts"):
                for page in json.loads(summary or "{}").get("outcomes", []):
                    if isinstance(page, dict) and page.get("status") == "SUCCESS":
                        identities.update(page_result_identity_keys(page))
            db.executemany("INSERT OR IGNORE INTO page_identities VALUES (?, '', '')", ((key,) for key in identities))
            db.execute("INSERT INTO history_metadata VALUES ('legacy_page_identities', '1')")

    def load(self, state, include_logs=True):
        with self.lock, sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM accounts WHERE account_id=?", (history_account_id(state),)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["tasks"] = json.loads(result["tasks"] or "{}")
            result["logs"] = [f"[HISTORY] {event['timestamp']} [{event['module']}/{event['result']}] {event['message']}" for event in reversed(db.execute("SELECT * FROM events WHERE account_id=? ORDER BY id DESC LIMIT 500", (history_account_id(state),)).fetchall())] if include_logs else []
            return result


def page_result_identity_keys(page):
    keys = set()
    if page.get("page_id"):
        keys.add("id:" + str(page["page_id"]).strip())
    if page.get("page_url"):
        keys.add("url:" + str(page["page_url"]).strip().rstrip("/").casefold())
    return keys
