"""Recipient/job verification, proxy isolation and durable credential-free history."""
import asyncio
import contextvars
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest

import client_app as app_module
from account_history import AccountHistoryStore


def make_app(history=None):
    app = app_module.MainToolApp.__new__(app_module.MainToolApp)
    app.account_states = app_module.AccountStateStore(history)
    app.account_states.sync([
        {"stt": 1, "account_id": "111111", "uid": "111111"},
        {"stt": 2, "account_id": "222222", "uid": "222222"},
    ])
    app.account_log_context = contextvars.ContextVar("targeted_account", default=None)
    app.post_ui = mock.Mock()
    app.log = mock.Mock()
    app.guard_facebook_checkpoint = mock.AsyncMock()
    app.update_tree_cell = mock.Mock()
    app.proxy_api_lock = asyncio.Lock()
    return app


def snapshot(controls, target="333333", connected=True):
    return {"connected": connected, "row": True,
            "links": [f"https://www.facebook.com/profile.php?id={target}"],
            "controls": controls}


def friend_resources(before, after, exception=None):
    scope = mock.Mock()
    scope.evaluate = mock.AsyncMock(side_effect=[before] + [after] * 8)
    handle = mock.Mock()
    handle.as_element.return_value = scope
    handle.dispose = mock.AsyncMock()
    button = mock.Mock()
    button.evaluate_handle = mock.AsyncMock(return_value=handle)
    button.click = mock.AsyncMock(side_effect=exception)
    page = mock.Mock(url="https://www.facebook.com/profile.php?id=333333")
    return page, button


@pytest.mark.parametrize("after", [snapshot([], connected=False), snapshot(["true"]),
                                   snapshot(["pending"], target="444444")])
def test_disappearance_or_wrong_recipient_is_not_success(after):
    app = make_app()
    page, button = friend_resources(snapshot(["Add Friend"]), after)
    with mock.patch.object(app_module.asyncio, "sleep", new=mock.AsyncMock()):
        result = asyncio.run(app.click_and_confirm_friend_request(page, button, "333333"))
    assert result.status == "FAILED"
    assert not result[0]
    button.click.assert_awaited_once()


def test_matching_recipient_pending_is_sent():
    app = make_app()
    page, button = friend_resources(snapshot(["Add Friend"]), snapshot(["outgoing_pending"]))
    result = asyncio.run(app.click_and_confirm_friend_request(page, button, "333333"))
    assert result.status == "SENT"
    assert result.target == "333333"


@pytest.mark.parametrize("control,status", [("friends", "ALREADY_FRIEND"), ("pending", "ALREADY_PENDING")])
def test_existing_relationship_is_not_clicked(control, status):
    app = make_app()
    page, button = friend_resources(snapshot([control]), snapshot([control]))
    result = asyncio.run(app.click_and_confirm_friend_request(page, button, "333333"))
    assert result.status == status
    assert not result[0]
    button.click.assert_not_awaited()


def test_friend_exception_is_task_error_not_account_die():
    app = make_app()
    app.account_states.update(1, status="LIVE")
    page, button = friend_resources(snapshot(["Add Friend"]), snapshot([]), TimeoutError("timeout"))
    outcome = asyncio.run(app.click_and_confirm_friend_request(page, button, "333333"))
    app.record_friend_outcome(1, outcome)
    state = app.account_states.get(1)
    assert outcome.status == "ERROR"
    assert state["status"] == "LIVE"
    assert state["tasks"]["FRIEND_REQUEST"]["status"] == "ERROR"
    assert "timeout" in state["current_action"]
    assert app.account_states.get(2)["tasks"] == {}


def test_failed_unverified_click_is_not_repeated_for_same_account():
    app = make_app()
    async def run():
        token = app.account_log_context.set(1)
        try:
            page, button = friend_resources(snapshot([]), snapshot([]))
            await app.click_and_confirm_friend_request(page, button, "333333")
            page2, button2 = friend_resources(snapshot([]), snapshot([]))
            outcome = await app.click_and_confirm_friend_request(page2, button2, "333333")
            button2.click.assert_not_awaited()
            assert outcome.status == "FAILED"
            assert app.account_states.get(2)["friend_attempts"] == set()
        finally:
            app.account_log_context.reset(token)
    with mock.patch.object(app_module.asyncio, "sleep", new=mock.AsyncMock()):
        asyncio.run(run())


@pytest.mark.parametrize("value", [":8080", "host:", "host:0", "host:65536", "host:80:user", "http://:8080", "host:80:user:"])
def test_proxy_rejects_missing_components(value):
    assert app_module.parse_proxy(value) is None


@pytest.mark.parametrize("value,server,password", [
    ("http://u:p%40ss%3A%2F%23%25@host:8080", "http://host:8080", "p@ss:/#%"),
    ("[2001:db8::1]:8080", "http://[2001:db8::1]:8080", None),
    ("socks5://u:p@ss@host:1080", "socks5://host:1080", "p@ss"),
    ("host:8080:u:p:@ss", "http://host:8080", "p:@ss"),
])
def test_proxy_preserves_ipv6_and_decodes_password(value, server, password):
    result = app_module.parse_proxy(value)
    assert result["server"] == server
    assert result.get("password") == password


@pytest.mark.parametrize("mode,expected,calls", [("account", "host:8080", 0), ("rotating_api", "rotated:9090", 1)])
def test_effective_proxy_obeys_selected_mode(mode, expected, calls):
    app = make_app()
    app.run_config = {"proxy_mode": mode, "proxy_api": "API"}
    with mock.patch.object(app_module, "fetch_proxy_from_api", return_value="rotated:9090") as fetch:
        result = asyncio.run(app.resolve_effective_proxy(1, "host:8080"))
    assert result == expected
    assert fetch.call_count == calls
    assert app.account_states.get(1)["effective_proxy"] == result
    assert app.account_states.get(1)["proxy"] == result
    callback = app.post_ui.call_args.args[0]
    app.tree = mock.Mock()
    app.tree.exists.return_value = True
    app.tree.item.return_value = list(range(10))
    app.refresh_account_state_row = mock.Mock()
    callback()
    assert app.tree.item.call_args.kwargs["values"][8] == expected


def test_proxy_resolution_isolated_between_accounts():
    app = make_app()
    app.run_config = {"proxy_mode": "account", "proxy_api": "unused"}
    async def run():
        return await asyncio.gather(app.resolve_effective_proxy(1, "a:8001"), app.resolve_effective_proxy(2, "b:8002"))
    assert asyncio.run(run()) == ["a:8001", "b:8002"]
    assert app.account_states.get(1)["effective_proxy"] == "a:8001"
    assert app.account_states.get(2)["effective_proxy"] == "b:8002"


@pytest.mark.parametrize("mode", ["account", "rotating_api"])
def test_empty_proxy_configuration_allows_direct_connection(mode):
    app = make_app()
    app.run_config = {"proxy_mode": mode, "proxy_api": "", "proxies": ""}
    result = asyncio.run(app.resolve_effective_proxy(1, ""))
    assert result == ""
    assert app.account_states.get(1)["effective_proxy"] == ""


def page_job():
    return {"owner_account_id": "111111", "owner_uid": "111111", "page_job_id": "job-A",
            "submitted": True, "page_name": "Page A", "prior_page_ids": {"555555"}}


def page_evidence():
    return {"page_type": "PAGE", "page_id": "999999", "name": "Page A", "canonical": ""}


@pytest.mark.parametrize("case", ["personal", "create", "unrelated", "canonical", "owner", "existing", "not_submitted"])
def test_page_rejects_unrelated_or_unproven_identity(case):
    job, evidence = page_job(), page_evidence()
    url, owner = "https://www.facebook.com/profile.php?id=999999", "111111"
    if case == "personal":
        evidence["page_type"] = "PROFILE"
    elif case == "create":
        url = "https://www.facebook.com/pages/creation/"
    elif case == "unrelated":
        evidence["name"] = "Page B"
    elif case == "canonical":
        evidence["canonical"] = "https://www.facebook.com/profile.php?id=888888"
    elif case == "owner":
        owner = "222222"
    elif case == "existing":
        job["prior_page_ids"].add("999999")
    elif case == "not_submitted":
        job["submitted"] = False
    assert not app_module.is_verified_page_identity(app_module.verify_page_job_evidence(url, evidence, job, owner))


def test_page_success_binds_owner_and_job():
    identity = app_module.verify_page_job_evidence("https://www.facebook.com/profile.php?id=999999", page_evidence(), page_job(), "111111")
    assert identity["verified"]
    assert identity["owner_account_id"] == "111111"
    assert identity["page_job_id"] == "job-A"


@pytest.mark.parametrize("requested,options,selected,expected", [
    ("Spa", ["Restaurant", " SPA "], True, True),
    ("Restaurant", ["Spa", "Restaurant"], True, True),
    ("Spa", ["Restaurant"], True, False),
    ("Spa", ["Spa"], False, False),
])
def test_category_matches_suggestion_and_verifies_selection(requested, options, selected, expected):
    app = make_app()
    page, category_input = mock.Mock(), mock.Mock()
    category_input.evaluate = mock.AsyncMock(return_value=selected)
    locators = []
    for text in options:
        locator = mock.Mock()
        locator.inner_text = mock.AsyncMock(return_value=text)
        locator.is_visible = mock.AsyncMock(return_value=True)
        locator.click = mock.AsyncMock()
        locator.wait_for = mock.AsyncMock()
        locators.append(locator)
    collection = mock.Mock()
    collection.first = locators[0]
    collection.count = mock.AsyncMock(return_value=len(locators))
    collection.nth.side_effect = lambda index: locators[index]
    page.locator.return_value = collection
    success, reason = asyncio.run(app.select_page_category(page, category_input, requested))
    assert success is expected
    for text, locator in zip(options, locators):
        assert locator.click.await_count == int(app_module.normalize_ui_text(text) == app_module.normalize_ui_text(requested))
    if not expected:
        assert reason.startswith("CATEGORY_")


def test_history_survives_reopen_refresh_and_reordering(tmp_path):
    path = tmp_path / "account_history.db"
    app = make_app(AccountHistoryStore(path))
    app.account_states.update(1, status="CHECKING")
    app.account_states.update(1, status="LIVE")
    app.account_states.append_log(1, "only account A")
    app.record_task_result(1, "CREATE_PAGE", "FAILED", "policy rejected")
    app.account_states.sync([])
    reopened = make_app(AccountHistoryStore(path))
    assert reopened.account_states.get(1)["status"] == "LIVE"
    assert reopened.account_states.get(1)["last_task_result"] == "FAILED"
    assert any("only account A" in item for item in reopened.account_states.get(1)["history_logs"])
    assert not any("only account A" in item for item in reopened.account_states.get(2)["history_logs"])
    reopened.account_states.sync([{"stt": 2, "account_id": "111111", "uid": "111111"}])
    assert reopened.account_states.get(2)["last_task_result"] == "FAILED"
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT first_seen_at,last_run_at,last_error FROM accounts WHERE account_id='111111'").fetchone()
        assert all(row)


def test_history_never_stores_plaintext_credentials(tmp_path):
    path = tmp_path / "account_history.db"
    history = AccountHistoryStore(path)
    state = {"uid": "111111", "status": "LIVE", "last_task_result": "ERROR",
             "password": 'M\u1eadt"khau\\secret', "2fa": "TWOFA_SECRET", "cookie": "c_user=111111; xs=COOKIE_SECRET;",
             "token": "EAA_TOKEN_SECRET", "proxy": "http://proxyuser:proxypass@host:8080"}
    state["raw_line"] = "|".join(state[key] for key in ("password", "2fa", "cookie", "token"))
    message = " ".join(state[key] for key in ("raw_line", "password", "2fa", "cookie", "token", "proxy"))
    state["current_action"] = message
    state["tasks"] = {"CREATE_PAGE": {"status": "ERROR", "detail": message, "outcomes": [{"password": state["password"], "technical_error": message, "proxy": state["proxy"]}]}}
    history.save(state, message=message)
    loaded = history.load(state)
    assert "[REDACTED]" in loaded["last_action"]
    content = path.read_bytes()
    for secret in (state["password"], "TWOFA_SECRET", "COOKIE_SECRET", "EAA_TOKEN_SECRET", "proxyuser", "proxypass"):
        assert secret.encode() not in content
    assert "password" not in loaded["tasks"]["CREATE_PAGE"]["outcomes"][0]


def test_concurrent_history_writes_and_duplicate_events(tmp_path):
    path = tmp_path / "account_history.db"
    history = AccountHistoryStore(path)
    def save(index):
        history.save({"uid": str(100000 + index), "status": "LIVE", "current_action": "verified"})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(save, range(40)))
    for _ in range(10):
        save(0)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 40
        assert db.execute("SELECT COUNT(*) FROM events WHERE account_id='100000'").fetchone()[0] == 1


def test_palette_complete_and_selection_readable():
    style, tree = mock.Mock(), mock.Mock()
    app_module.configure_account_table_style(style, tree)
    assert set(app_module.ACCOUNT_STATUS_PALETTE) == set(app_module.ACCOUNT_STATUSES)
    assert tree.tag_configure.call_count == len(app_module.ACCOUNT_STATUSES)
    style.map.assert_called_once_with("Account.Treeview", background=[("selected", "#285D69")], foreground=[("selected", "#FFFFFF")])
    for palette in app_module.ACCOUNT_STATUS_PALETTE.values():
        assert palette["background"] != palette["foreground"]


def test_refresh_during_run_preserves_worker_account_and_proxy():
    app = make_app()
    app.is_running = True
    app.tree = mock.Mock()
    app.account_states.set_proxy(1, "host:8080")
    app.reload_table_from_text()
    app.tree.delete.assert_not_called()
    assert app.account_states.get(1)["effective_proxy"] == "host:8080"


def test_selected_account_renders_persistent_history_only(tmp_path):
    first = make_app(AccountHistoryStore(tmp_path / "history.db"))
    first.account_states.append_log(1, "persistent-A")
    first.account_states.append_log(2, "persistent-B")
    app = make_app(AccountHistoryStore(tmp_path / "history.db"))
    app.txt_log = mock.Mock()
    app.lbl_log_scope = mock.Mock()
    app.selected_log_account = 1
    app.render_log_view()
    rendered = app.txt_log.insert.call_args.args[1]
    assert "persistent-A" in rendered
    assert "persistent-B" not in rendered
    assert "[HISTORY]" in rendered
    assert "[CURRENT RUN]" in rendered


def test_new_run_keeps_history_and_clears_only_task_results(tmp_path):
    app = make_app(AccountHistoryStore(tmp_path / "history.db"))
    app.record_task_result(1, "FRIEND_REQUEST", "ERROR", "old timeout")
    app.account_states.append_log(1, "previous-run")
    app.account_states.update(1, status="CHECKING")
    state = app.account_states.get(1)
    assert state["tasks"] == {}
    assert any("previous-run" in item for item in state["history_logs"])
    assert state["logs"] == []


def test_category_suggestions_absent_is_failed():
    app = make_app()
    page = mock.Mock()
    page.locator.return_value.first.wait_for = mock.AsyncMock(side_effect=TimeoutError("no suggestions"))
    success, reason = asyncio.run(app.select_page_category(page, mock.Mock(), "Spa"))
    assert not success
    assert reason == "CATEGORY_SUGGESTIONS_NOT_AVAILABLE"


def test_account_table_styles_work_in_both_real_tk_themes(tmp_path):
    root = app_module.tk.Tk()
    root.withdraw()
    try:
        with (mock.patch.object(app_module, "APP_DATA_DIR", str(tmp_path)),
              mock.patch.object(app_module.MainToolApp, "load_settings"),
              mock.patch.object(app_module, "check_for_updates"),
              mock.patch.object(app_module.threading, "Thread")):
            app = app_module.MainToolApp(root, "2027-01-01")
            for theme in ("Dark Charcoal (Mặc định)", "Cyberpunk Neon"):
                app.apply_theme(theme)
                for tree in (app.tree, app.account_state_tree):
                    assert tree.cget("style") == "Account.Treeview"
                    for status, palette in app_module.ACCOUNT_STATUS_PALETTE.items():
                        assert str(tree.tag_configure(status, "foreground")) == palette["foreground"]
                        assert str(tree.tag_configure(status, "background")) == palette["background"]
            assert "task" in app.account_state_tree.cget("columns")
            root.update_idletasks()
            app.close_requested = True
    finally:
        root.destroy()
