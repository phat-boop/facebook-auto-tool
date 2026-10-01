"""Persistent account outcomes, without storing login credentials."""
import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit


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
    secrets = [str(state.get(key) or "") for key in ("raw_line", "source_line", "password", "pwd", "2fa", "cookie", "token")]
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
            """)

    def save(self, state, module="ACCOUNT", event_type="STATE", message=""):
        key = history_account_id(state)
        if not key:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = state.get("status", "UNKNOWN")
        action = redact_history_text(state.get("current_action"), state)
        def sanitize(value):
            if isinstance(value, dict):
                return {key: sanitize(item) for key, item in value.items()
                        if key not in {"password", "pwd", "2fa", "cookie", "token", "raw_line", "source_line"}}
            if isinstance(value, (list, tuple)):
                return [sanitize(item) for item in value]
            return redact_history_text(value, state) if isinstance(value, str) else value

        tasks = sanitize(state.get("tasks", {}))
        task_result = state.get("last_task_result", "PENDING")
        message = redact_history_text(message or action, state)
        error = next((task.get("detail", "") for task in tasks.values()
                      if task.get("status") in {"ERROR", "FAILED"}), action)
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute("""INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    last_status=excluded.last_status, last_task_result=excluded.last_task_result,
                    last_action=excluded.last_action, last_seen_at=excluded.last_seen_at,
                    last_run_at=COALESCE(excluded.last_run_at, accounts.last_run_at),
                    last_error=COALESCE(excluded.last_error, accounts.last_error),
                    last_checkpoint_at=COALESCE(excluded.last_checkpoint_at, accounts.last_checkpoint_at),
                    page_summary=excluded.page_summary, friend_summary=excluded.friend_summary,
                    proxy_label=excluded.proxy_label, tasks=excluded.tasks""", (
                key, status, task_result, action, now, now,
                now if status == "CHECKING" else None,
                error if status in {"DIE", "ERROR"} or task_result in {"FAILED", "ERROR"} else None,
                now if status == "CHECKPOINT" else None,
                json.dumps(tasks.get("CREATE_PAGE", {})), json.dumps(tasks.get("FRIEND_REQUEST", {})),
                safe_proxy_label(state.get("effective_proxy", state.get("proxy", ""))), json.dumps(tasks),
            ))
            result = tasks.get(module, {}).get("status", task_result) if module != "ACCOUNT" else status
            previous = db.execute("SELECT module,event_type,result,message FROM events WHERE account_id=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
            event = (module, event_type, result, message)
            if previous != event:
                db.execute("INSERT INTO events(account_id,timestamp,module,event_type,result,message) VALUES (?, ?, ?, ?, ?, ?)", (key, now, *event))

    def load(self, state):
        with self.lock, sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM accounts WHERE account_id=?", (history_account_id(state),)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["tasks"] = json.loads(result["tasks"] or "{}")
            result["logs"] = [f"[HISTORY] {event['timestamp']} [{event['module']}/{event['result']}] {event['message']}" for event in reversed(db.execute("SELECT * FROM events WHERE account_id=? ORDER BY id DESC LIMIT 500", (history_account_id(state),)).fetchall())]
            return result
