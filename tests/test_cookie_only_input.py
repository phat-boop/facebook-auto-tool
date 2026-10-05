"""Cookie-only input, retained provenance, and runtime account binding."""
import asyncio
import json
import threading
from unittest import mock

import pytest

import client_app as module
from test_account_normalization import make_import_app
from test_run_snapshot_lifecycle import make_start_app, start_without_real_worker
from test_cookie_session import make_app, run_account


COOKIE_A = "c_user=11111; xs=a=b==;"
COOKIE_B = "c_user=22222; xs=b=token;"
RAW_A = f"11111|PasswordA|TWOFA_A|||{COOKIE_A}|TOKEN_A|127.0.0.1:60001|unused"
RAW_B = f"22222|PasswordB||{COOKIE_B}|TOKEN_B|127.0.0.1:60002"


@pytest.mark.parametrize("raw", [COOKIE_A, f"COOKIE|{COOKIE_A}", RAW_A,
                               f"11111|PasswordA|TWOFA_A|{COOKIE_A}|TOKEN_A"])
def test_import_displays_only_cookie_and_keeps_original_record(raw):
    app = make_import_app(raw)
    app.reload_table_from_text()
    state = app.account_states.get(1)
    assert app.txt_accounts.text.rstrip("\n") == COOKIE_A
    assert "|" not in app.txt_accounts.text
    assert state["raw_line"] == raw
    assert state["cookie"] == COOKIE_A
    before = state["account_record"]
    with mock.patch.object(module, "import_account_record", side_effect=AssertionError("reimport")):
        app.reload_table_from_text()
    assert app.account_states.get(1)["account_record"] is before
    assert app.account_states.get(1)["raw_line"] == raw


def test_cookie_rows_reorder_without_mixing_metadata_or_proxy():
    app = make_import_app(RAW_A + "\n" + RAW_B)
    app.reload_table_from_text()
    app.txt_accounts.text = COOKIE_B + "\n" + COOKIE_A
    with mock.patch.object(module, "import_account_record", side_effect=AssertionError("reimport")):
        app.reload_table_from_text()
    b, a = app.account_states.get(1), app.account_states.get(2)
    assert (b["uid"], b["raw_line"], b["proxy"]) == ("22222", RAW_B, "127.0.0.1:60002")
    assert (a["uid"], a["raw_line"], a["proxy"]) == ("11111", RAW_A, "127.0.0.1:60001")
    assert b["password"] == "PasswordB" and a["password"] == "PasswordA"


def test_replacing_cookie_uses_new_data_not_cached_cookie():
    app = make_import_app(RAW_A)
    app.reload_table_from_text()
    updated = "c_user=11111; xs=new=value==;"
    app.txt_accounts.text = updated
    app.reload_table_from_text()
    assert app.account_states.get(1)["cookie"] == updated
    assert app.account_states.get(1)["raw_line"] == updated
    assert app.txt_accounts.text.strip() == updated


def test_dialog_callback_appends_only_cookies_with_original_metadata():
    app = make_import_app(RAW_A)
    imported = module.import_account_record(RAW_B).to_account_dict()
    app.add_accounts_to_table([imported])
    assert app.txt_accounts.text.strip().splitlines() == [COOKIE_A, COOKIE_B]
    assert app.account_states.get(2)["raw_line"] == RAW_B
    assert app.account_states.get(2)["proxy"] == "127.0.0.1:60002"


def test_import_file_converts_full_lines_to_cookie_only(tmp_path):
    path = tmp_path / "accounts.txt"
    path.write_text(RAW_A + "\n" + RAW_B, encoding="utf-8")
    app = make_import_app()
    with mock.patch.object(module.filedialog, "askopenfilename", return_value=str(path)):
        app.import_accounts_file()
    assert app.txt_accounts.text.strip().splitlines() == [COOKIE_A, COOKIE_B]
    assert app.account_states.get(1)["raw_line"] == RAW_A
    assert app.account_states.get(2)["raw_line"] == RAW_B


def test_json_cookie_display_preserves_equals_and_original_json():
    raw = json.dumps({"c_user": "11111", "xs": "a=b=="})
    app = make_import_app(raw)
    app.reload_table_from_text()
    state = app.account_states.get(1)
    assert state["raw_line"] == raw
    assert app.txt_accounts.text.strip() == "c_user=11111; xs=a=b=="
    assert next(c["value"] for c in module.parse_cookies(state["cookie"]) if c["name"] == "xs") == "a=b=="


def test_cookie_input_snapshot_runs_models_without_password_twofa_or_token():
    app = make_start_app()
    app.txt_accounts.text = RAW_A + "\n" + RAW_B
    config = start_without_real_worker(app)
    assert config["accounts"].splitlines() == [COOKIE_A, COOKIE_B]
    app.process_account_scoped = mock.AsyncMock()
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()), \
         mock.patch.object(module, "parse_legacy_account_line", side_effect=AssertionError("runtime heuristic")):
        asyncio.run(app.main_worker())
    calls = app.process_account_scoped.call_args_list
    assert len(calls) == 2
    for call, uid, cookie, proxy in zip(calls, ("11111", "22222"), (COOKIE_A, COOKIE_B),
                                      ("127.0.0.1:60001", "127.0.0.1:60002")):
        assert call.args[3:5] == (cookie, proxy)
        assert call.kwargs["login_user"] == uid
        assert call.kwargs["login_password"] == ""
        assert "two_factor" not in call.kwargs and "token" not in call.kwargs


def test_processed_cookie_is_removed_without_removing_other_account():
    app = make_import_app(RAW_A + "\n" + RAW_B)
    app.reload_table_from_text()
    app.create_page_result_lock = threading.Lock()
    app.create_page_account_results = {"completed": {}, "die": {}, "checkpoint": {}}
    app.save_settings = mock.Mock()
    app.record_create_page_account_result(1, "completed", created_count=1, target_count=1)
    app.remove_processed_create_page_accounts_from_input()
    assert app.txt_accounts.text.strip() == COOKIE_B
    assert app.account_states.get(1)["uid"] == "22222"
    assert app.account_states.get(1)["raw_line"] == RAW_B
    assert app.account_states.get(1)["proxy"] == "127.0.0.1:60002"
    app.save_settings.assert_called_once()


def test_cookie_without_password_logs_in_only_after_session_verified(tmp_path):
    app, context, page, events = make_app(tmp_path)
    record = module.import_account_record("c_user=123456789; xs=abc=def;")
    app.account_states.sync([{**record.to_account_dict(), "stt": 1, "account_id": record.uid}])
    app.login_facebook_user_pass = mock.AsyncMock(side_effect=AssertionError("password login"))
    state = run_account(app, password="")
    assert state["status"] == "LIVE" and state["login_mode"] == "COOKIE"
    assert state["password"] == "" and state["token"] == ""
    assert events[0][0] == "restore"
    assert not any(event[0] == "fill" for event in events)
    app.login_facebook_user_pass.assert_not_awaited()
