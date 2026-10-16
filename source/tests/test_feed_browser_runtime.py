"""Regressions for authenticated Feed timeouts and manual inspector closure."""
import asyncio
from unittest import mock

import pytest
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

import client_app as module
from test_account_management_ui import inspector_resources, management_app
from test_cookie_session import make_app, run_account


CLOSED = "Target page, context or browser has been closed"


def support_app():
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.is_running, app.stop_requested = True, False
    app.log = mock.Mock()
    app.guard_facebook_checkpoint = mock.AsyncMock()
    app.verify_facebook_session = mock.AsyncMock(return_value=(module.LOGIN_SUCCESS, "verified"))
    return app


def support_page(url="https://www.facebook.com/"):
    page = mock.Mock(url=url, goto=mock.AsyncMock(), context=object())
    page.is_closed.return_value = False
    return page


@pytest.mark.parametrize("host", ["www.facebook.com", "web.facebook.com", "m.facebook.com"])
def test_warmup_does_not_reload_the_already_authenticated_home(host):
    app, page = support_app(), support_page(f"https://{host}/")
    app._wait_support_activity = mock.AsyncMock()
    asyncio.run(app.warm_up_feed(page, "test", 130))
    page.goto.assert_not_awaited()
    app._wait_support_activity.assert_awaited_once_with(page, 130, scroll=True)


@pytest.mark.parametrize("url", ["about:blank", "https://example.com/", "https://www.facebook.com/me"])
def test_warmup_still_navigates_when_not_on_facebook_home(url):
    app, page = support_app(), support_page(url)
    app._wait_support_activity = mock.AsyncMock()
    asyncio.run(app.warm_up_feed(page, "test", 30))
    page.goto.assert_awaited_once_with("https://www.facebook.com/", wait_until="domcontentloaded", timeout=25000)


def test_real_worker_with_valid_cookie_does_not_fail_on_a_second_home_navigation(tmp_path):
    app, context, page, events = make_app(tmp_path)
    app.run_config["options"] = {"warmup": True}
    app.run_config["warmup_seconds"] = 130
    app._wait_support_activity = mock.AsyncMock()
    original_goto = page.goto

    async def first_navigation_only(*args, **kwargs):
        if any(event[0] == "goto" for event in events):
            raise PlaywrightTimeoutError("Page.goto: Timeout 25000ms exceeded")
        return await original_goto(*args, **kwargs)

    page.goto = first_navigation_only
    state = run_account(app)
    assert state["status"] == "LIVE"
    assert len([event for event in events if event[0] == "goto"]) == 1
    app._wait_support_activity.assert_awaited_once_with(page, 130, scroll=True)
    context.close.assert_awaited_once()


def test_feed_navigation_timeout_can_continue_only_with_verified_session():
    app, page = support_app(), support_page("https://www.facebook.com/me")
    page.goto.side_effect = PlaywrightTimeoutError("DOMContentLoaded timeout")
    app._wait_support_activity = mock.AsyncMock()
    asyncio.run(app.warm_up_feed(page, "test", 30))
    app.verify_facebook_session.assert_awaited_once_with(page, page.context)
    app._wait_support_activity.assert_awaited_once()
    assert page.goto.await_count == 1


@pytest.mark.parametrize("result", [module.LOGIN_INVALID, module.LOGIN_TECHNICAL_ERROR, module.LOGIN_CHECKPOINT])
def test_feed_timeout_does_not_ignore_invalid_unverified_or_checkpoint_session(result):
    app, page = support_app(), support_page("https://www.facebook.com/me")
    page.goto.side_effect = PlaywrightTimeoutError("navigation timeout")
    app.verify_facebook_session.return_value = (result, "not verified")
    app._wait_support_activity = mock.AsyncMock()
    expected = module.FacebookCheckpointStopped if result == module.LOGIN_CHECKPOINT else RuntimeError
    with pytest.raises(expected):
        asyncio.run(app.warm_up_feed(page, "test", 30))
    app._wait_support_activity.assert_not_awaited()


def test_slow_optional_scroll_does_not_abort_a_verified_live_session():
    app, page = support_app(), support_page()
    app._smooth_human_scroll = mock.AsyncMock(side_effect=TimeoutError())
    pauses = []

    async def stop_after_pause(delay):
        pauses.append(delay)
        app.stop_requested = True

    with mock.patch.object(module.asyncio, "sleep", side_effect=stop_after_pause):
        asyncio.run(app._wait_support_activity(page, 130, scroll=True))
    app.verify_facebook_session.assert_awaited_once_with(page, page.context)
    assert pauses
    assert any("[!]" in call.args[0] for call in app.log.call_args_list)


def test_scroll_timeout_with_unverified_session_remains_error():
    app, page = support_app(), support_page()
    app._smooth_human_scroll = mock.AsyncMock(side_effect=TimeoutError())
    app.verify_facebook_session.return_value = (module.LOGIN_TECHNICAL_ERROR, "blank page")
    with pytest.raises(RuntimeError, match="blank page"):
        asyncio.run(app._wait_support_activity(page, 130, scroll=True))


def test_stop_cancellation_is_not_swallowed_by_feed_timeout_handling():
    app, page = support_app(), support_page()
    app._smooth_human_scroll = mock.AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(app._wait_support_activity(page, 130, scroll=True))
    app.verify_facebook_session.assert_not_awaited()


def test_manually_closed_inspector_during_goto_is_not_an_error():
    app = management_app()
    factory, browser, context, page = inspector_resources()
    page.is_closed.return_value = True
    page.goto.side_effect = PlaywrightError(CLOSED)
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    for resource in (page, context, browser):
        resource.close.assert_awaited_once()
    assert app.account_states.get(1)["status"] == "UNKNOWN"


def test_inspector_crash_is_not_hidden_as_manual_close():
    app = management_app()
    factory, browser, context, page = inspector_resources()
    page.is_closed.return_value = True

    async def crash_during_navigation(*_args, **_kwargs):
        callbacks = {call.args[0]: call.args[1] for call in page.on.call_args_list}
        if "crash" in callbacks:
            callbacks["crash"](page)
        raise PlaywrightError(CLOSED)

    page.goto.side_effect = crash_during_navigation
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        with pytest.raises(PlaywrightError):
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    browser.close.assert_awaited_once()


def test_inspector_navigation_abort_waits_for_the_actual_close_event():
    app = management_app()
    factory, browser, context, page = inspector_resources()
    browser.is_connected.return_value = True
    page.is_closed.return_value = False

    async def close_after_navigation_rejects(*_args, **_kwargs):
        callbacks = {call.args[0]: call.args[1] for call in page.on.call_args_list}
        def deliver_close():
            page.is_closed.return_value = True
            callbacks["close"](page)
        asyncio.get_running_loop().call_soon(deliver_close)
        raise PlaywrightError("Page.goto: net::ERR_ABORTED; maybe frame was detached?")

    page.goto.side_effect = close_after_navigation_rejects
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    browser.close.assert_awaited_once()


def test_inspector_navigation_abort_is_still_error_when_window_stays_open():
    app = management_app()
    factory, browser, context, page = inspector_resources()
    browser.is_connected.return_value = True
    page.is_closed.return_value = False
    page.goto.side_effect = PlaywrightError("Page.goto: net::ERR_ABORTED")
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        with pytest.raises(PlaywrightError, match="ERR_ABORTED"):
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    browser.close.assert_awaited_once()


def test_cleanup_ignores_already_closed_resource_race_but_keeps_real_errors():
    page = mock.Mock(close=mock.AsyncMock(side_effect=PlaywrightError(CLOSED)))
    context = mock.Mock(close=mock.AsyncMock(side_effect=PlaywrightError(CLOSED)))
    browser = mock.Mock(close=mock.AsyncMock(side_effect=RuntimeError("real cleanup error")))
    errors = asyncio.run(module.close_browser_resources(context, browser, page))
    assert len(errors) == 1 and str(errors[0]) == "real cleanup error"
    for resource in (page, context, browser):
        resource.close.assert_awaited_once()
