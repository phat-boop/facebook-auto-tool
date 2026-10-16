"""Regressions for the confirmed audit failures; no Facebook traffic."""
import asyncio
import json
from pathlib import Path
import subprocess
import os
import contextvars
import threading
from unittest import mock

import playwright
import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app, start_without_real_worker


def uncheck_all(app):
    for row in app.tree.get_children():
        values = list(app.tree.item(row, "values"))
        values[0] = "[ ]"
        app.tree.item(row, values=values)


def test_unchecked_all_does_not_start_any_account():
    app = make_start_app()
    uncheck_all(app)
    with mock.patch.object(module.threading, "Thread") as thread:
        app.start_thread()
    thread.assert_not_called()
    assert not app.is_running
    assert app.run_config["checked_indexes"] == frozenset()
    assert "Chưa chọn" in app.run_error
    app.btn_start.config.assert_called_with(state="normal")


def test_manual_selection_can_override_empty_checkboxes():
    app = make_start_app()
    uncheck_all(app)
    app.ent_selected_indexes.get.return_value = "2"
    start_without_real_worker(app)
    assert app.run_account_indexes == {2}


@pytest.mark.parametrize("manual", ["invalid", "99"])
def test_invalid_or_missing_stt_does_not_run_all_accounts(manual):
    app = make_start_app()
    app.ent_selected_indexes.get.return_value = manual
    with mock.patch.object(module.threading, "Thread") as thread:
        app.start_thread()
    thread.assert_not_called()
    assert not app.is_running


def test_worker_also_rejects_explicit_empty_selection():
    app = make_start_app()
    values = dict(app.capture_run_config())
    values["checked_indexes"] = set()
    app.run_config = module.RunConfig(values)
    app.is_running = True
    with mock.patch.object(module, "async_playwright") as browser:
        asyncio.run(app.main_worker())
    browser.assert_not_called()
    assert app.run_status == "FAILED"


def dom_page_evidence(kind="profile", page_id="333333"):
    # Playwright ships this JS runtime, so tests need no extra Node installation.
    node = Path(playwright.__file__).parent / "driver" / ("node.exe" if os.name == "nt" else "node")
    setup = """
const kind = __KIND__, id = __PAGE_ID__;
global.location = {search: '?id=333333', pathname: '/profile.php'};
global.document = {
    cookie: kind === 'page-cookie' ? 'i_user=' + id : '',
    querySelector: selector => {
        if (kind === 'data' && selector === '[data-page-id]')
            return {getAttribute: () => id};
        if (kind === 'deep-link' && selector === 'meta[property="al:android:url"]')
            return {content: 'fb://page/' + id};
        return null;
    },
    querySelectorAll: () => [{innerText: 'Audit Page', getClientRects: () => [{}]}]
};
process.stdout.write(JSON.stringify((__EVIDENCE__)()));
""".replace("__KIND__", json.dumps(kind)).replace("__PAGE_ID__", json.dumps(page_id)).replace("__EVIDENCE__", module.PAGE_CREATION_EVIDENCE)
    result = subprocess.run([str(node), "-e", setup], capture_output=True, text=True, timeout=10, check=True)
    return json.loads(result.stdout)


def verify_dom_page(evidence, **job_changes):
    job = {"submitted": True, "owner_account_id": "111111", "owner_uid": "111111",
           "page_name": "Audit Page", "page_job_id": "audit-job", "prior_page_ids": set()}
    job.update(job_changes)
    return module.verify_page_job_evidence("https://www.facebook.com/profile.php?id=333333",
                                         evidence, job, "111111")


def test_personal_profile_url_and_matching_name_are_not_page_success():
    evidence = dom_page_evidence()
    assert evidence["page_id"] == "333333"
    assert evidence["page_type"] == ""
    assert not module.is_verified_page_identity(verify_dom_page(evidence))


@pytest.mark.parametrize("kind", ["data", "deep-link", "page-cookie"])
def test_page_specific_identity_still_requires_owner_job_and_matching_url(kind):
    evidence = dom_page_evidence(kind)
    assert verify_dom_page(evidence)["verified"]
    assert not module.is_verified_page_identity(verify_dom_page(evidence, submitted=False))
    assert not module.is_verified_page_identity(verify_dom_page(evidence, owner_account_id="222222"))
    assert not module.is_verified_page_identity(verify_dom_page(dom_page_evidence(kind, "444444")))


@pytest.mark.parametrize("login_result", [module.LOGIN_SUCCESS, module.LOGIN_INVALID, module.LOGIN_TECHNICAL_ERROR])
def test_imported_cookie_cannot_be_overridden_by_saved_profile(tmp_path, login_result):
    from test_cookie_session import make_app as cookie_app, UID
    app, _context, _page, _events = cookie_app(tmp_path)
    app.root = mock.Mock(spec=module.tk.Tk)
    context = mock.Mock(add_cookies=mock.AsyncMock())
    page = mock.Mock(goto=mock.AsyncMock(return_value=mock.Mock(status=200)))
    app.dismiss_floating_overlays = mock.AsyncMock()
    app.verify_facebook_session = mock.AsyncMock(return_value=(login_result, "fixture result"))
    fresh = f"c_user={UID}; xs=FRESH_INPUT;"
    old = f"c_user={UID}; xs=OLD_CACHED_SESSION;"
    with mock.patch.object(module.os.path, "isfile", return_value=True), \
         mock.patch("builtins.open", mock.mock_open(read_data=json.dumps({"cookie": old}))) as opened, \
         mock.patch.object(module, "unprotect_setting", side_effect=lambda value: value), \
         mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        result, _detail = asyncio.run(app.authenticate_facebook_account(1, page, context, fresh, UID, ""))
    assert result == login_result
    loaded = {cookie["name"]: cookie["value"] for cookie in context.add_cookies.call_args.args[0]}
    assert loaded["xs"] == "FRESH_INPUT"
    opened.assert_not_called()
    assert app.account_states.get(1)["login_mode"] == "COOKIE"


def friend_loop_app():
    from test_targeted_runtime import make_app
    app = make_app()
    app.is_running, app.stop_requested = True, False
    page = mock.Mock(goto=mock.AsyncMock())
    button = mock.Mock(scroll_into_view_if_needed=mock.AsyncMock())
    collection = mock.Mock(first=button, count=mock.AsyncMock(return_value=1))
    page.locator.return_value = collection
    page.mouse.wheel = mock.AsyncMock()
    app.click_and_confirm_friend_request = mock.AsyncMock()
    return app, page, button, collection


@pytest.mark.parametrize("stage", ["locator", "scroll", "unconfirmed"])
def test_friend_loop_stops_after_six_consecutive_failures(stage):
    app, page, button, collection = friend_loop_app()
    if stage == "locator":
        collection.count.side_effect = RuntimeError("stale selector")
        operation = collection.count
    elif stage == "scroll":
        button.scroll_into_view_if_needed.side_effect = RuntimeError("stale button")
        operation = button.scroll_into_view_if_needed
    else:
        app.click_and_confirm_friend_request.return_value = module.FriendRequestOutcome("FAILED", "333333", "unconfirmed")
        operation = app.click_and_confirm_friend_request
    with mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        assert asyncio.run(app.run_add_by_name(page, "111111", 1, ["Target A", "Target B"], 2, 0, 0)) == 0
    assert operation.await_count == 6
    page.goto.assert_awaited_once()
    assert app.account_states.get(1)["status"] != "DIE"


def test_friend_verified_success_resets_failure_streak():
    app, page, _button, _collection = friend_loop_app()
    failed = module.FriendRequestOutcome("FAILED", "333333", "unconfirmed")
    app.click_and_confirm_friend_request.side_effect = [
        failed, failed, failed, module.FriendRequestOutcome("SENT", "444444", "verified"),
        failed, failed, failed, module.FriendRequestOutcome("SENT", "555555", "verified"),
    ]
    with mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        assert asyncio.run(app.run_add_by_name(page, "111111", 1, ["Target A"], 2, 0, 0)) == 2
    assert app.click_and_confirm_friend_request.await_count == 8
    assert app.account_states.get(1)["friend_success_count"] == 2
    assert app.account_states.get(2)["friend_success_count"] == 0


@pytest.mark.parametrize("requested", ["Spa", "Nhà hàng", "Local service"])
def test_category_never_falls_back_to_an_unrelated_suggestion(requested):
    from test_targeted_runtime import make_app
    app = make_app()
    option = mock.Mock(inner_text=mock.AsyncMock(return_value="Personal blog"),
                       is_visible=mock.AsyncMock(return_value=True), click=mock.AsyncMock(),
                       wait_for=mock.AsyncMock())
    options = mock.Mock(first=option, count=mock.AsyncMock(return_value=1))
    options.nth.return_value = option
    page = mock.Mock()
    page.locator.return_value = options
    page.keyboard.type = mock.AsyncMock()
    field = mock.Mock(evaluate=mock.AsyncMock(return_value=True))
    with mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        success, reason = asyncio.run(app.select_page_category(page, field, requested))
    assert not success and reason == "CATEGORY_NOT_FOUND"
    option.click.assert_not_awaited()
    page.keyboard.type.assert_not_awaited()


def test_equivalent_translated_blog_category_is_still_allowed():
    from test_targeted_runtime import make_app
    app = make_app()
    async def click_option(_page, locator):
        await locator.click()
    app.human_click = mock.AsyncMock(side_effect=click_option)
    option = mock.Mock(inner_text=mock.AsyncMock(return_value="Personal blog"),
                       is_visible=mock.AsyncMock(return_value=True), click=mock.AsyncMock(),
                       wait_for=mock.AsyncMock())
    options = mock.Mock(first=option, count=mock.AsyncMock(return_value=1))
    options.nth.return_value = option
    page = mock.Mock()
    page.locator.return_value = options
    field = mock.Mock(evaluate=mock.AsyncMock(return_value=True))
    assert asyncio.run(app.select_page_category(page, field, "Blog cá nhân")) == (True, "")
    app.human_click.assert_awaited_once_with(page, option)
    option.click.assert_awaited_once()
    field.evaluate.assert_awaited_once()
    assert field.evaluate.call_args.args[1] == "Personal blog"


def proxy_factory():
    request = mock.Mock(dispose=mock.AsyncMock(), get=mock.AsyncMock())
    factory = mock.MagicMock()
    factory.__aenter__.return_value.request.new_context = mock.AsyncMock(return_value=request)
    return factory, request


def enable_proxy_api(app):
    app.proxy_mode.get.return_value = "rotating_api"
    app.ent_proxy_api.get.return_value = "https://example.invalid/api?api_key=SECRET_FIXTURE"
    app.account_log_context = contextvars.ContextVar("proxy_preflight_account", default=None)


def test_proxy_snapshot_does_not_make_network_calls_on_tk_thread():
    app = make_start_app()
    enable_proxy_api(app)
    with mock.patch.object(module, "fetch_proxy_from_api") as sync_fetch, \
         mock.patch.object(module, "fetch_proxy_from_api_async") as async_fetch:
        config = start_without_real_worker(app)
    sync_fetch.assert_not_called()
    async_fetch.assert_not_called()
    assert not config["proxy_snapshot_complete"]


def test_proxy_preparation_is_complete_before_accounts_run_without_tk_reads():
    app = make_start_app()
    enable_proxy_api(app)
    start_without_real_worker(app)
    factory, request = proxy_factory()
    events = []

    async def fetch(_api, _request):
        proxy = f"127.0.0.1:{62001 + len(events)}"
        events.append(proxy)
        return proxy

    async def account_worker(_p, index, _name, _cookie, proxy, *_args, **_kwargs):
        assert len(events) == 2
        assert app.run_config["proxy_snapshot_complete"]
        assert proxy == app.run_config["resolved_proxies"][index]

    app.process_account_scoped = mock.AsyncMock(side_effect=account_worker)
    for name, widget in vars(app).items():
        if name.startswith(("ent_", "chk_")) or name == "proxy_mode":
            widget.get.side_effect = AssertionError("worker read Tk")
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "fetch_proxy_from_api_async", side_effect=fetch) as fetcher:
        asyncio.run(app.main_worker())
    assert fetcher.await_count == app.process_account_scoped.await_count == 2
    assert app.run_config["resolved_proxies"][1] != app.run_config["resolved_proxies"][2]
    request.dispose.assert_awaited_once()


def test_proxy_timeout_never_opens_browser_or_marks_die():
    app = make_start_app()
    enable_proxy_api(app)
    start_without_real_worker(app)
    factory, request = proxy_factory()
    request.get.side_effect = TimeoutError("secret URL SECRET_FIXTURE")
    app.create_browser_page = mock.AsyncMock()
    app.update_tree_row = mock.Mock()
    with mock.patch.object(module, "async_playwright", return_value=factory):
        asyncio.run(app.main_worker())
    app.create_browser_page.assert_not_awaited()
    assert all(app.account_states.get(i)["status"] == "ERROR" for i in (1, 2))
    assert "SECRET_FIXTURE" not in str(dict(app.run_config["proxy_errors"]))
    request.dispose.assert_awaited_once()


def test_stop_cancels_waiting_proxy_preparation_and_restores_start():
    from test_stop_cancellation import make_app, join_and_cleanup
    app = make_app()
    enable_proxy_api(app)
    factory, request = proxy_factory()
    entered = threading.Event()

    async def wait_for_api(*_args, **_kwargs):
        entered.set()
        await asyncio.Event().wait()

    request.get.side_effect = wait_for_api
    app.create_browser_page = mock.AsyncMock()
    with mock.patch.object(module, "async_playwright", return_value=factory):
        app.start_thread()
        assert entered.wait(2)
        app.stop_bot()
        assert join_and_cleanup(app, timeout=2)
    request.dispose.assert_awaited_once()
    app.create_browser_page.assert_not_awaited()
    assert app.run_status == "CANCELLED"
    assert app.worker_loop is None and app.worker_root_task is None and app.worker_tasks == []


@pytest.mark.parametrize("body,expected", [
    ('{"proxyHttp":"127.0.0.1:60001"}', "127.0.0.1:60001"),
    ('{"data":{"ip":"127.0.0.1","port":60002}}', "127.0.0.1:60002"),
    ('{"data":{"proxy":"127.0.0.1:60003:user:pass"}}', "127.0.0.1:60003:user:pass"),
    ('{"data":"127.0.0.1:60004"}', "127.0.0.1:60004"),
    ("127.0.0.1:60005", "127.0.0.1:60005"),
])
def test_async_proxy_api_keeps_existing_response_formats(body, expected):
    request = mock.Mock(get=mock.AsyncMock(return_value=mock.Mock(status=200, text=mock.AsyncMock(return_value=body))))
    assert asyncio.run(module.fetch_proxy_from_api_async("API_KEY", request)) == expected
    assert module.parse_proxy_api_response(body) == expected
    assert request.get.call_args.kwargs["timeout"] == 15000
