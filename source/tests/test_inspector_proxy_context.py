"""Part 2: inspector network identity, proxy response integrity and saved API settings."""
import asyncio
import json
from unittest import mock

from cryptography.fernet import Fernet
import pytest

import client_app as module
from test_account_management_ui import inspector_resources
from test_run_snapshot_lifecycle import make_start_app


def api_app(*, complete=True, resolved=None, errors=None):
    app = make_start_app()
    app.txt_proxies.text = ""
    app.proxy_mode.get.return_value = "rotating_api"
    app.ent_proxy_api.get.return_value = "https://example.invalid/proxy?key=API_SECRET"
    app.reload_table_from_text()
    values = dict(app.capture_run_config())
    values.update(proxy_snapshot_complete=complete,
                  resolved_proxies=resolved or {}, proxy_errors=errors or {})
    app.run_config = module.RunConfig(values)
    return app


@pytest.mark.parametrize("complete,resolved,errors", [
    (True, {}, {1: "API timeout API_SECRET"}),
    (False, {}, {}),
    (True, {}, {}),
    (True, {1: "invalid proxy"}, {}),
])
def test_api_inspector_fails_closed_before_browser_launch(complete, resolved, errors):
    app = api_app(complete=complete, resolved=resolved, errors=errors)
    resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=resources[0]) as driver, \
         mock.patch.object(module, "fetch_proxy_from_api") as sync_api, \
         mock.patch.object(module, "fetch_proxy_from_api_async") as async_api:
        with pytest.raises((ValueError, ConnectionError)) as error:
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    driver.assert_not_called()
    sync_api.assert_not_called()
    async_api.assert_not_called()
    assert "API_SECRET" not in str(error.value)
    assert app.account_states.get(1)["status"] == "UNKNOWN"


def test_inspector_resolves_network_by_uid_not_reused_stt():
    app = api_app(resolved={1: "127.0.0.1:62001", 2: "127.0.0.1:62002"})
    selected = app.account_states.get(1)
    selected.update(stt=2, proxy="", effective_proxy="")
    factory, browser, context, _page = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(app.inspect_account_session(selected))
    launch = factory.__aenter__.return_value.chromium.launch
    assert launch.call_args.kwargs["proxy"] == module.parse_proxy("127.0.0.1:62001")
    context.add_cookies.assert_awaited_once_with(module.parse_cookies(selected["cookie"]))
    browser.close.assert_awaited_once()


def test_inspector_cannot_borrow_proxy_from_another_uid():
    app = api_app(resolved={2: "127.0.0.1:62002"})
    factory, *_resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory) as driver:
        with pytest.raises((ValueError, ConnectionError)):
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    driver.assert_not_called()


def test_explicitly_required_inspector_proxy_rejects_empty_value():
    app = make_start_app()
    account = app.account_states.get(1)
    account.update(proxy="", effective_proxy="", proxy_required=True)
    factory, *_resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory) as driver:
        with pytest.raises(ValueError):
            asyncio.run(app.inspect_account_session(account))
    driver.assert_not_called()


def test_missing_snapshot_route_cannot_erase_the_accounts_proxy_requirement():
    app = make_start_app()
    values = dict(app.capture_run_config())
    values.update(proxy_mode="account", proxies="", resolved_proxies={})
    app.run_config = module.RunConfig(values)
    with mock.patch.object(module, "async_playwright", return_value=inspector_resources()[0]) as driver:
        with pytest.raises(ValueError):
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    driver.assert_not_called()


def open_snapshot(app, account, before_launch=None):
    app.inspect_account_session = mock.AsyncMock()
    with mock.patch.object(module.threading, "Thread") as thread:
        app.open_account_inspector(account)
        assert thread.called
        if before_launch:
            before_launch()
        thread.call_args.kwargs["target"]()
    return app.inspect_account_session.call_args.args[0]


def test_idle_refresh_invalidates_old_effective_proxy_only_for_that_uid():
    app = make_start_app()
    app.account_states.set_proxy(1, "127.0.0.1:60001")
    app.account_states.set_proxy(2, "127.0.0.1:60002")
    app.account_states.set_processing(2, True)
    accounts = [dict(app.account_states.get(1), proxy="127.0.0.1:61001"),
                app.account_states.get(2)]
    app.account_states.sync(accounts)
    a, b = app.account_states.get(1), app.account_states.get(2)
    assert a["proxy"] == "127.0.0.1:61001"
    assert not a.get("effective_proxy") or a["effective_proxy"] == a["proxy"]
    assert b["effective_proxy"] == "127.0.0.1:60002"


def test_idle_inspector_uses_edited_proxy_not_last_run_or_old_context_menu():
    app = make_start_app()
    app.run_config = app.capture_run_config()
    app.account_states.set_proxy(1, "127.0.0.1:60001")
    selected = app.account_states.get(1)
    app.txt_proxies.text = "127.0.0.1:61001\n127.0.0.1:61002"
    snapshot = open_snapshot(app, selected)
    factory, *_resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(module.MainToolApp.inspect_account_session(app, snapshot))
    assert factory.__aenter__.return_value.chromium.launch.call_args.kwargs["proxy"] == {
        "server": "http://127.0.0.1:61001",
    }
    assert app.run_config["resolved_proxies"][1] == "127.0.0.1:60001"


def test_active_inspector_uses_frozen_run_route_without_reading_tk():
    app = api_app(resolved={1: "socks5://user:pass@127.0.0.1:62001"})
    app.is_running = True
    account = app.account_states.get(1)
    for name in ("ent_proxy_api", "ent_proxy_ratio", "proxy_mode"):
        getattr(app, name).get.side_effect = AssertionError("inspector read active Tk config")
    app.txt_proxies.get = mock.Mock(side_effect=AssertionError("inspector read active proxy list"))
    snapshot = open_snapshot(app, account)
    assert snapshot["inspector_network"]["proxy"] == "socks5://user:pass@127.0.0.1:62001"
    assert snapshot["uid"] == account["uid"]


def test_inspector_worker_cannot_reresolve_or_change_captured_route():
    app = make_start_app()
    def edit_after_capture():
        app.txt_proxies.text = "127.0.0.1:63001"
        app.proxy_mode.get.side_effect = AssertionError("worker read mode")
        app.txt_proxies.get = mock.Mock(side_effect=AssertionError("worker read proxy widget"))
    snapshot = open_snapshot(app, app.account_states.get(1), edit_after_capture)
    with pytest.raises(TypeError):
        snapshot["inspector_network"]["proxy"] = "wrong:8000"
    factory, *_resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None), \
         mock.patch.object(module, "fetch_proxy_from_api") as sync_api, \
         mock.patch.object(module, "fetch_proxy_from_api_async") as async_api:
        asyncio.run(module.MainToolApp.inspect_account_session(app, snapshot))
    assert factory.__aenter__.return_value.chromium.launch.call_args.kwargs["proxy"]["server"].endswith(":60001")
    sync_api.assert_not_called()
    async_api.assert_not_called()


def test_idle_api_inspector_reuses_uid_route_after_reorder_without_fetching_again():
    app = api_app(resolved={1: "127.0.0.1:62001", 2: "127.0.0.1:62002"})
    account = app.account_states.get(1)
    app.txt_accounts.text = "c_user=22222; xs=B;\nc_user=11111; xs=A;"
    with mock.patch.object(module, "fetch_proxy_from_api") as sync_api, \
         mock.patch.object(module, "fetch_proxy_from_api_async") as async_api:
        snapshot = open_snapshot(app, account)
    assert snapshot["uid"] == "11111" and snapshot["stt"] == 2
    assert snapshot["inspector_network"]["proxy"] == "127.0.0.1:62001"
    sync_api.assert_not_called()
    async_api.assert_not_called()


def test_changed_api_configuration_rejects_previous_api_proxy():
    app = api_app(resolved={1: "127.0.0.1:62001"})
    app.ent_proxy_api.get.return_value = "NEW_API_SECRET"
    with mock.patch.object(module.threading, "Thread") as thread, \
         mock.patch.object(module.messagebox, "showerror") as error:
        app.open_account_inspector(app.account_states.get(1))
    thread.assert_not_called()
    error.assert_called_once()
    assert "NEW_API_SECRET" not in str(error.call_args)


def test_old_proxy_is_not_used_after_switching_to_explicit_direct_mode():
    app = make_start_app()
    app.account_states.set_proxy(1, "127.0.0.1:60001")
    account = app.account_states.get(1)
    app.txt_proxies.text = ""
    snapshot = open_snapshot(app, account)
    factory, *_resources = inspector_resources()
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(module.MainToolApp.inspect_account_session(app, snapshot))
    assert "proxy" not in factory.__aenter__.return_value.chromium.launch.call_args.kwargs


def test_inspector_checks_network_owner_again_immediately_before_launch():
    app = make_start_app()
    account = app.account_states.get(1)
    account["inspector_network"] = {"account_id": "22222", "proxy": "127.0.0.1:60002", "required": True}
    with mock.patch.object(module, "async_playwright") as driver:
        with pytest.raises(ValueError):
            asyncio.run(app.inspect_account_session(account))
    driver.assert_not_called()


@pytest.mark.parametrize("proxy", [
    "socks5://test-user:test-pass@127.0.0.1:60001",
    "http://test-user:p%40ss%3Dvalue@127.0.0.1:60002",
    "https://user:password@proxy.example:8443",
    "socks4://proxy.example:1080",
    "127.0.0.1:60003:user:pa:ss==",
    "user:password@proxy.example:8080",
    "socks5://user:password@[::1]:1080",
    "http://user:pass{value}@127.0.0.1:60004",
])
@pytest.mark.parametrize("container", ["plain", "json", "nested_json"])
def test_proxy_api_preserves_full_protocol_auth_and_address(proxy, container):
    body = {"plain": proxy, "json": json.dumps({"proxy": proxy}),
            "nested_json": json.dumps({"data": {"proxyHttp": proxy}})}[container]
    result = module.parse_proxy_api_response("\n " + body + " \n")
    assert result == proxy
    assert module.parse_proxy(result) == module.parse_proxy(proxy)


def test_unknown_text_response_is_not_silently_downgraded_to_unauthenticated_http():
    assert module.parse_proxy_api_response(
        "API failure; previous route was socks5://user:password@127.0.0.1:60001"
    ) == ""


def test_sync_and_async_proxy_api_keep_identical_authenticated_socks_route():
    proxy = "socks5://user:p%40ss@127.0.0.1:60001"
    response = mock.MagicMock()
    response.__enter__.return_value.read.return_value = proxy.encode()
    request = mock.Mock(get=mock.AsyncMock(return_value=mock.Mock(
        status=200, text=mock.AsyncMock(return_value=proxy),
    )))
    with mock.patch.object(module.urllib.request, "urlopen", return_value=response):
        assert module.fetch_proxy_from_api("https://example.invalid/proxy") == proxy
    assert asyncio.run(module.fetch_proxy_from_api_async("https://example.invalid/proxy", request)) == proxy


class EntryValue:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self, *_args):
        self.value = ""

    def insert(self, _index, value):
        self.value = str(value)


@pytest.mark.parametrize("api", ["API_KEY_SECRET", "https://example.invalid/proxy?api_key=API_KEY_SECRET", ""])
def test_proxy_api_settings_are_encrypted_and_restored_for_next_snapshot(tmp_path, api):
    path = tmp_path / "settings.json"
    cipher = Fernet(Fernet.generate_key())
    app = make_start_app()
    app.current_theme = next(iter(module.THEMES))
    app.ent_proxy_api = EntryValue(api)
    app.proxy_mode = EntryValue("rotating_api")
    recovered = make_start_app()
    recovered.ent_proxy_api = EntryValue("stale entry")
    recovered.proxy_mode = EntryValue("round_robin")
    recovered.cbo_theme, recovered.apply_theme = mock.Mock(), mock.Mock()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)), \
         mock.patch.object(module, "settings_cipher", return_value=cipher):
        module.MainToolApp.save_settings(app)
        saved_text = path.read_text(encoding="utf-8")
        saved = json.loads(saved_text)
        assert "proxy_api" in saved
        assert saved["proxy_mode"] == "rotating_api"
        assert "API_KEY_SECRET" not in saved_text
        if api:
            assert saved["proxy_api"] != api
            assert cipher.decrypt(saved["proxy_api"].encode()).decode() == api
        module.MainToolApp.load_settings(recovered)
    assert recovered.ent_proxy_api.get() == api
    assert recovered.proxy_mode.get() == "rotating_api"
    assert recovered.capture_run_config()["proxy_api"] == api


def test_old_settings_without_proxy_api_keep_blank_default(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"proxy_mode":"rotating_api"}', encoding="utf-8")
    app = make_start_app()
    app.ent_proxy_api = EntryValue()
    app.proxy_mode = EntryValue("round_robin")
    with mock.patch.object(module, "SETTINGS_FILE", str(path)):
        module.MainToolApp.load_settings(app)
    assert app.ent_proxy_api.get() == ""
    assert app.proxy_mode.get() == "rotating_api"
