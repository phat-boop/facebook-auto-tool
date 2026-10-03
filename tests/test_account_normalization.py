"""Phase 1 import compatibility and positional runtime account contract."""
import asyncio
import json
from dataclasses import FrozenInstanceError
from unittest import mock

import pytest
from cryptography.fernet import Fernet

import client_app as app_module


COOKIE = "c_user=123456789; xs=abc=def==;"


class TextBuffer:
    def __init__(self, text=""):
        self.text = text

    def get(self, *_args):
        return self.text

    def delete(self, *_args):
        self.text = ""

    def insert(self, _index, text):
        self.text = text + self.text


class AccountTree:
    def __init__(self):
        self.rows = {}

    def get_children(self):
        return tuple(self.rows)

    def insert(self, _parent, _where, iid, values, tags):
        self.rows[iid] = {"values": values, "tags": tags}

    def delete(self, item):
        del self.rows[item]

    def exists(self, item):
        return item in self.rows

    def item(self, item, option=None, **updates):
        self.rows[item].update(updates)
        return self.rows[item][option] if option else self.rows[item]


def make_import_app(text=""):
    app = app_module.MainToolApp.__new__(app_module.MainToolApp)
    app.txt_accounts = TextBuffer(text)
    app.txt_proxies = TextBuffer()
    app.txt_targets = TextBuffer()
    app.tree = AccountTree()
    app.account_states = app_module.AccountStateStore()
    app._account_import_records = {}
    app.is_running = False
    app.stop_requested = False
    app.refresh_account_state_table = mock.Mock()
    app.log = mock.Mock()
    app.post_ui = mock.Mock()
    app.ent_proxy_ratio = mock.Mock()
    app.ent_proxy_ratio.get.return_value = "20"
    app.proxy_mode = mock.Mock()
    app.proxy_mode.get.return_value = "account"
    return app


@pytest.mark.parametrize("twofa,token", [("", ""), ("2FA", ""),
                                        ("", "TOKEN"), ("2FA", "TOKEN")])
def test_canonical_positions_and_optional_slots(twofa, token):
    raw = f"12345|Pass|{twofa}|{COOKIE}|{token}"
    with mock.patch.object(app_module, "parse_legacy_account_line", side_effect=AssertionError("heuristic")):
        record = app_module.import_account_record(raw)
    assert isinstance(record, app_module.AccountRecord)
    assert (record.uid, record.password, record.twofa, record.cookie, record.token) == (
        "12345", "Pass", twofa, COOKIE, token)
    assert record.raw_line == raw
    assert record.canonical_line == raw
    assert len(record.canonical_line.split("|")) == 5
    assert app_module.serialize_account_line(record) == raw


@pytest.mark.parametrize("password", ["A" * 16, "B" * 32, "EAABpassword",
                                    "p@example.com", "not_c_user=secret", " spaced password "])
def test_canonical_password_is_never_reclassified(password):
    raw = f"12345|{password}|ACTUAL_2FA|{COOKIE}|opaque-token"
    record = app_module.import_account_record(raw)
    assert record.password == password
    assert record.twofa == "ACTUAL_2FA"
    assert record.token == "opaque-token"
    assert record.canonical_line == raw


@pytest.mark.parametrize("raw,uid,password,twofa,token,proxy", [
    (COOKIE, "123456789", "", "", "", ""),
    (f"COOKIE|{COOKIE}", "123456789", "", "", "", ""),
    (f"Name|{COOKIE}", "123456789", "", "", "", ""),
    (f"FACEBOOK|12345|Pass|{COOKIE}|EAABtoken", "12345", "Pass", "", "EAABtoken", ""),
    (f"FACEBOOK|12345|Pass|2FA|{COOKIE}|EAABtoken", "12345", "Pass", "2FA", "EAABtoken", ""),
    (f"FACEBOOK|12345|Pass|{COOKIE}|TOKEN", "12345", "Pass", "", "TOKEN", ""),
    (f"FACEBOOK|12345|Pass|2FA|{COOKIE}|TOKEN", "12345", "Pass", "2FA", "TOKEN", ""),
    (f"TOKEN|EAABtoken|{COOKIE}", "123456789", "", "", "EAABtoken", ""),
    (f"12345|Pass|2FA|{COOKIE}", "12345", "Pass", "2FA", "", ""),
    (f"12345|{'A' * 16}|2FA|||{COOKIE}|TOKEN", "12345", "A" * 16, "2FA", "TOKEN", ""),
    (f"12345|Pass|2FA|{COOKIE}|127.0.0.1:60001", "12345", "Pass", "2FA", "", "127.0.0.1:60001"),
    (f"12345|Pass|2FA|{COOKIE}|EAABtoken|127.0.0.1:60002", "12345", "Pass", "2FA", "EAABtoken", "127.0.0.1:60002"),
    (f"12345|Pass|2FA|{COOKIE}|email@example.com|127.0.0.1:60003", "12345", "Pass", "2FA", "", "127.0.0.1:60003"),
    (f"12345|Pass|2FA|EAABtoken|{COOKIE}|unused", "12345", "Pass", "2FA", "EAABtoken", ""),
    (f"12345|c_user=password|2FA|||{COOKIE}|TOKEN", "12345", "c_user=password", "2FA", "TOKEN", ""),
    (f"12345|Pass|EAABtoken|{COOKIE}", "12345", "Pass", "", "EAABtoken", ""),
    (f"12345|Pass|{'EAAB' + 'X' * 12}|{COOKIE}", "12345", "Pass", "", "EAAB" + "X" * 12, ""),
    (f"12345|Pass|email@example.com|{COOKIE}", "12345", "Pass", "", "", ""),
])
def test_legacy_import_normalizes_without_losing_credentials(raw, uid, password, twofa, token, proxy):
    record = app_module.import_account_record(raw)
    assert record is not None
    assert (record.uid, record.password, record.twofa, record.cookie, record.token, record.proxy) == (
        uid, password, twofa, COOKIE, token, proxy)
    assert record.raw_line == raw
    assert record.canonical_line == f"{uid}|{password}|{twofa}|{COOKIE}|{token}"
    assert len(record.canonical_line.split("|")) == 5
    assert app_module.parse_canonical_account_line(record.canonical_line).canonical_line == record.canonical_line


@pytest.mark.parametrize("payload", [
    [{"name": "c_user", "value": "123456789"}, {"name": "xs", "value": "abc=def=="}],
    {"cookies": {"c_user": "123456789", "xs": "abc=def=="}},
])
def test_json_cookie_import_is_normalized_with_equals_intact(payload):
    raw = json.dumps(payload)
    record = app_module.import_account_record(raw)
    assert record.raw_line == raw
    assert record.uid == "123456789"
    assert "xs=abc=def==" in record.cookie
    assert len(record.canonical_line.split("|")) == 5
    cookies = app_module.parse_cookies(record.cookie)
    assert next(cookie["value"] for cookie in cookies if cookie["name"] == "xs") == "abc=def=="


def test_long_cookie_containing_dots_is_not_also_a_token():
    raw = json.dumps({"c_user": "123456789", "xs": "abc.def==", "datr": "x" * 60})
    record = app_module.import_account_record(raw)
    assert record.token == ""
    assert "xs=abc.def==" in record.cookie


@pytest.mark.parametrize("cookie", ["not_c_user=12345", "prefix_c_user=12345",
                                   "c_user_extra=12345", "value=not_c_user=12345",
                                   '{"not_c_user":"12345"}', "invalid JSON {"])
def test_cookie_false_detection_is_rejected(cookie):
    assert app_module.import_account_record(f"12345|Pass||{cookie}|") is None
    assert app_module.parse_canonical_account_line(f"12345|Pass||{cookie}|") is None


@pytest.mark.parametrize("raw", [f"COOKIE|{COOKIE}", f"12345|Pass|2FA|||{COOKIE}|TOKEN",
                                f"12345|Pass|2FA|{COOKIE}", "", "12345|Pass|2FA||"])
def test_runtime_canonical_parser_rejects_noncanonical_data(raw):
    with mock.patch.object(app_module, "parse_legacy_account_line", side_effect=AssertionError("legacy in runtime")):
        assert app_module.parse_canonical_account_line(raw) is None
        assert app_module.runtime_account_record({"raw_line": raw}) is None
        with pytest.raises(ValueError, match="normalized"):
            app_module.serialize_account_line({"raw_line": raw})


def test_original_fields_and_whitespace_survive_import_and_refresh():
    raw = f"  7. 12345|Pass|2FA|||{COOKIE}|EAABtoken|email@example.com|127.0.0.1:60001|unused  "
    app = make_import_app(raw)
    app.reload_table_from_text()
    first = app.account_states.get(1)
    assert first["raw_line"] == raw
    assert first["import_fields"][3:5] == ["", ""]
    assert first["import_fields"][-1] == "unused"
    assert first["fields"] == ["12345", "Pass", "2FA", COOKIE, "EAABtoken"]
    assert app.txt_accounts.text.rstrip("\n") == first["canonical_line"]
    with mock.patch.object(app_module, "parse_legacy_account_line", side_effect=AssertionError("reimport")):
        app.reload_table_from_text()
    second = app.account_states.get(1)
    assert second["raw_line"] == raw
    assert second["proxy"] == "127.0.0.1:60001"
    assert second["email"] == "email@example.com"
    assert second["account_record"] is first["account_record"]
    with pytest.raises(FrozenInstanceError):
        second["account_record"].password = "changed"


def test_multiple_accounts_keep_separate_raw_proxy_and_fields():
    raw_a = f"12345|{'A' * 16}|TWOFA|||{COOKIE}|TOKEN|127.0.0.1:60001"
    raw_b = "67890|PassB||c_user=67890; xs=other=token;|TOKEN_B|127.0.0.1:60002"
    app = make_import_app(raw_a + "\n" + raw_b)
    app.reload_table_from_text()
    app.reload_table_from_text()
    a, b = app.account_states.get(1), app.account_states.get(2)
    assert a["raw_line"] == raw_a and b["raw_line"] == raw_b
    assert a["password"] == "A" * 16 and b["password"] == "PassB"
    assert a["proxy"] == "127.0.0.1:60001" and b["proxy"] == "127.0.0.1:60002"
    assert len(a["fields"]) == len(b["fields"]) == 5
    assert len(app.txt_accounts.text.strip().splitlines()) == 2


def test_import_dialog_keeps_raw_and_token_in_callback():
    raw = f" 12345|Pass|2FA|||{COOKIE}|TOKEN "
    dialog = mock.Mock()
    dialog.txt_input = TextBuffer(raw)
    with mock.patch.object(app_module.messagebox, "showinfo"):
        app_module.ImportAccountDialog.process_import(dialog)
    account = dialog.on_import_callback.call_args.args[0][0]
    assert account["raw_line"] == raw
    assert account["token"] == "TOKEN"
    assert len(account["canonical_line"].split("|")) == 5


def test_runtime_selected_account_uses_record_not_textbox():
    raw = f"12345|Pass|2FA|||{COOKIE}|TOKEN"
    app = make_import_app(raw)
    app.reload_table_from_text()
    app.txt_accounts.text = "unimported garbage"
    with mock.patch.object(app_module, "parse_any_account_line", side_effect=AssertionError("runtime heuristic")):
        account = app.get_parsed_account_for_item("1")
    assert account["uid"] == "12345" and account["token"] == "TOKEN"
    assert account["raw_line"] == raw


def test_worker_only_consumes_canonical_model_and_rejects_legacy_fallback():
    raw = f"12345|{'A' * 16}|2FA|||{COOKIE}|TOKEN|127.0.0.1:60001"
    app = make_import_app(raw)
    app.reload_table_from_text()
    app.run_config = {
        "accounts": app.txt_accounts.text, "parsed_accounts": {1: app.account_states.get(1)},
        "proxy_mode": "account", "threads": 1, "batch_size": 5, "modes": {},
        "options": {}, "targets": "", "resolved_proxies": {},
    }
    app.process_account_scoped = mock.AsyncMock()
    factory = mock.MagicMock()
    with mock.patch.object(app_module, "async_playwright", return_value=factory), \
         mock.patch.object(app_module, "parse_any_account_line", side_effect=AssertionError("heuristic")), \
         mock.patch.object(app_module, "parse_legacy_account_line", side_effect=AssertionError("legacy")):
        asyncio.run(app.main_worker())
        args, kwargs = app.process_account_scoped.call_args
        assert args[3] == COOKIE
        assert args[4] == "127.0.0.1:60001"
        assert kwargs["login_user"] == "12345" and kwargs["login_password"] == "A" * 16
        app.process_account_scoped.reset_mock()
        app.run_config["accounts"] = raw
        app.run_config["parsed_accounts"] = {}
        asyncio.run(app.main_worker())
        app.process_account_scoped.assert_not_called()


def test_import_provenance_survives_encrypted_settings_round_trip(tmp_path):
    raw = f" 12345|Pass|2FA|||{COOKIE}|TOKEN|127.0.0.1:60001|unknown "
    app = make_import_app(raw)
    app.reload_table_from_text()
    app.current_theme = next(iter(app_module.THEMES))
    app.mode_vars = {}
    names = ("ent_threads ent_batch_size ent_target ent_page_target ent_max_create_page_workers "
             "ent_min_page_delay ent_max_page_delay ent_min_delay ent_max_delay ent_feed_surf_min "
             "ent_watch_review_min ent_tele_token ent_tele_chatid chk_headless chk_warmup "
             "chk_cancel_old chk_browse_web chk_interact_page chk_check_notif chk_chat_react").split()
    for name in names:
        setattr(app, name, mock.Mock())
        getattr(app, name).get.return_value = "1"
    saved_path = tmp_path / "settings.json"
    cipher = Fernet(Fernet.generate_key())
    with mock.patch.object(app_module, "SETTINGS_FILE", str(saved_path)), \
         mock.patch.object(app_module, "settings_cipher", return_value=cipher):
        app.save_settings()
        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert raw not in data["account_import_records"]
        recovered = make_import_app()
        recovered.cbo_theme = mock.Mock()
        recovered.apply_theme = mock.Mock()
        for name in names:
            setattr(recovered, name, mock.Mock())
        recovered.load_settings()
    assert recovered.account_states.get(1)["raw_line"] == raw
    assert recovered.account_states.get(1)["token"] == "TOKEN"
    assert recovered.account_states.get(1)["proxy"] == "127.0.0.1:60001"
    assert recovered.account_states.get(1)["import_fields"][-1] == "unknown"


def test_start_normalizes_new_input_even_if_old_state_exists():
    app = make_import_app(f"11111|OldPass||c_user=11111;|")
    app.reload_table_from_text()
    app.txt_accounts.text = f"22222|{'B' * 32}|2FA|||c_user=22222;|TOKEN"
    app.run_thread = None
    app.save_settings = mock.Mock()
    app.capture_run_config = mock.Mock(side_effect=lambda: {
        "modes": {}, "threads": 1, "headless": True,
        "parsed_accounts": {1: app.account_states.get(1)},
    })
    app.ent_threads = mock.Mock()
    app.ent_threads.get.return_value = "1"
    app.btn_start, app.btn_stop = mock.Mock(), mock.Mock()
    with mock.patch.object(app_module.threading, "Thread"):
        app.start_thread()
    assert app.run_config["parsed_accounts"][1]["uid"] == "22222"
    assert app.run_config["parsed_accounts"][1]["password"] == "B" * 32
    assert len(app.txt_accounts.text.strip().split("|")) == 5
