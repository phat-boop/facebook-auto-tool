"""Phase 3: fresh immutable snapshots and isolated browser ownership."""
import asyncio
import ast
import inspect
import threading
from unittest import mock

import pytest

import client_app as module
from test_account_normalization import make_import_app


def account(uid):
    return f"{uid}|Pass||c_user={uid}; xs=value;|"


def make_start_app():
    app = make_import_app(account("11111") + "\n" + account("22222"))
    app.root = mock.Mock()
    app.root.winfo_screenwidth.return_value = 1920
    app.root.winfo_screenheight.return_value = 1080
    entries = {
        "threads": "2", "batch_size": "5", "proxy_ratio": "1",
        "selected_indexes": "", "proxy_api": "", "target": "1",
        "min_delay": "0", "max_delay": "0", "page_target": "1",
        "max_create_page_workers": "2", "min_page_delay": "0", "max_page_delay": "0",
        "feed_surf_min": "0", "watch_review_min": "0", "tele_token": "", "tele_chatid": "",
    }
    for name, value in entries.items():
        widget = mock.Mock()
        widget.get.return_value = value
        setattr(app, "ent_" + name, widget)
    for name in ("headless warmup watch_reels view_stories check_notif chat_react interact_page "
                 "cancel_old browse_web").split():
        widget = mock.Mock()
        widget.get.return_value = name == "headless"
        setattr(app, "chk_" + name, widget)
    app.mode_vars = {}
    app.run_thread = None
    app.worker_loop = None
    app.worker_tasks = []
    app.run_error = None
    app.btn_start, app.btn_stop = mock.Mock(), mock.Mock()
    app.save_settings = mock.Mock()
    app.proxy_mode.get.return_value = "round_robin"
    app.txt_proxies.text = "127.0.0.1:60001\n127.0.0.1:60002"
    app.reload_table_from_text()
    return app


def start_without_real_worker(app):
    with mock.patch.object(module.threading, "Thread") as factory:
        factory.return_value.is_alive.return_value = False
        app.start_thread()
        assert app.is_running, app.run_error
        factory.return_value.start.assert_called_once()
    return app.run_config


def test_edits_before_start_are_synced_before_running():
    app = make_start_app()
    app.txt_accounts.text = account("33333") + "\n" + account("44444")
    app.txt_proxies.text = "127.0.0.1:61001\n127.0.0.1:61002"
    original_reload = app.reload_table_from_text
    original_capture = app.capture_run_config
    events = []
    def reload(**kwargs):
        assert not app.is_running
        events.append("reload")
        original_reload(**kwargs)
    def capture():
        assert not app.is_running
        events.append("capture")
        return original_capture()
    app.reload_table_from_text, app.capture_run_config = reload, capture
    config = start_without_real_worker(app)
    assert events == ["reload", "capture"]
    assert config["parsed_accounts"][1]["uid"] == "33333"
    assert config["parsed_accounts"][2]["uid"] == "44444"
    assert dict(config["resolved_proxies"]) == {1: "127.0.0.1:61001", 2: "127.0.0.1:61002"}
    assert app.account_states.get(1)["proxy"] == "127.0.0.1:61001"


def test_snapshot_is_recursively_immutable_and_detached():
    app = make_start_app()
    config = start_without_real_worker(app)
    with pytest.raises(TypeError):
        config["threads"] = 99
    with pytest.raises(TypeError):
        config["parsed_accounts"][1]["uid"] = "wrong"
    with pytest.raises(TypeError):
        config["options"]["warmup"] = True
    with pytest.raises(TypeError):
        config["resolved_proxies"][1] = "wrong:8000"
    app.account_states.set_proxy(1, "changed:8000")
    app.txt_accounts.text = account("55555")
    assert config["parsed_accounts"][1]["uid"] == "11111"
    assert config["resolved_proxies"][1] == "127.0.0.1:60001"
    assert isinstance(config["checked_indexes"], frozenset)


@pytest.mark.parametrize("raw", ["", "# comment", "invalid account"])
def test_invalid_input_never_starts_thread_and_restores_buttons(raw):
    app = make_start_app()
    app.txt_accounts.text = raw
    with mock.patch.object(module.threading, "Thread") as factory:
        app.start_thread()
    factory.assert_not_called()
    assert not app.is_running
    app.btn_start.config.assert_called_with(state="normal")
    app.btn_stop.config.assert_called_with(state="disabled")


def test_worker_uses_snapshot_without_tk_or_proxy_reselection():
    app = make_start_app()
    config = start_without_real_worker(app)
    app.process_account_scoped = mock.AsyncMock()
    worker_errors = []
    def run():
        try:
            asyncio.run(app.main_worker())
        except BaseException as exc:
            worker_errors.append(exc)
    # Every widget access would fail from the real worker thread.
    for name, widget in vars(app).items():
        if name.startswith(("txt_", "ent_", "chk_")) or name in {"root", "tree", "proxy_mode"}:
            if isinstance(widget, mock.Mock):
                widget.get.side_effect = AssertionError("worker read Tk")
                widget.winfo_screenwidth.side_effect = AssertionError("worker read screen")
                widget.winfo_screenheight.side_effect = AssertionError("worker read screen")
            else:
                widget.get = mock.Mock(side_effect=AssertionError("worker read Tk"))
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()), \
         mock.patch.object(module.random, "choice", side_effect=AssertionError("reselected proxy")):
        thread = threading.Thread(target=run)
        thread.start()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert worker_errors == []
    calls = app.process_account_scoped.call_args_list
    assert len(calls) == 2
    assert [(call.args[1], call.args[4]) for call in calls] == [
        (1, config["resolved_proxies"][1]), (2, config["resolved_proxies"][2])]


def test_rotating_api_is_resolved_before_running_not_again_in_worker():
    app = make_start_app()
    app.proxy_mode.get.return_value = "rotating_api"
    app.ent_proxy_api.get.return_value = "https://proxy.example/api"
    def fetch(_url):
        assert not app.is_running
        return next(proxies)
    proxies = iter(["127.0.0.1:62001", "127.0.0.1:62002"])
    with mock.patch.object(module, "fetch_proxy_from_api", side_effect=fetch) as fetcher:
        config = start_without_real_worker(app)
        fetcher.assert_called()
        assert fetcher.call_count == 2
        fetcher.side_effect = AssertionError("proxy resolved twice")
        async def resolve():
            return await asyncio.gather(app.resolve_effective_proxy(1, "old:8000"),
                                        app.resolve_effective_proxy(2, "old:8000"))
        assert asyncio.run(resolve()) == [config["resolved_proxies"][1], config["resolved_proxies"][2]]


def test_failed_proxy_capture_cannot_fallback_to_machine_ip():
    app = make_start_app()
    app.proxy_mode.get.return_value = "rotating_api"
    app.ent_proxy_api.get.return_value = "API"
    with mock.patch.object(module, "fetch_proxy_from_api", side_effect=TimeoutError("proxy timeout")):
        start_without_real_worker(app)
    async def resolve():
        with pytest.raises(ConnectionError, match="proxy timeout"):
            await app.resolve_effective_proxy(1, None)
    asyncio.run(resolve())


class Resource:
    def __init__(self):
        self.close = mock.AsyncMock()


def browser_resources():
    browser, context, page = Resource(), Resource(), Resource()
    browser.new_context = mock.AsyncMock(return_value=context)
    context.new_page = mock.AsyncMock(return_value=page)
    context.add_init_script = mock.AsyncMock()
    page.goto = mock.AsyncMock(return_value=mock.Mock(status=200))
    launcher = mock.Mock()
    launcher.chromium.launch = mock.AsyncMock(return_value=browser)
    return launcher, browser, context, page


def browser_app():
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.run_config = module.RunConfig({"threads": 2, "screen_width": 1920, "screen_height": 1080})
    app.log = mock.Mock()
    return app


@pytest.mark.parametrize("stage,expected", [("context", (1, 0, 0)), ("page", (1, 1, 0)),
                                           ("script", (1, 1, 1)), ("health", (1, 1, 1))])
@pytest.mark.parametrize("error", [RuntimeError("init failure"), asyncio.CancelledError()])
def test_browser_initialization_failure_or_cancel_closes_owned_resources(stage, expected, error):
    launcher, browser, context, page = browser_resources()
    operation = {"context": browser.new_context, "page": context.new_page,
                 "script": context.add_init_script, "health": page.goto}[stage]
    operation.side_effect = error
    async def run():
        with pytest.raises(asyncio.CancelledError if isinstance(error, asyncio.CancelledError) else RuntimeError):
            await browser_app().create_browser_page(launcher, 1)
    with mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(run())
    assert (browser.close.await_count, context.close.await_count, page.close.await_count) == expected


def test_cancel_actual_init_task_cleans_resources():
    launcher, browser, context, page = browser_resources()
    async def run():
        entered = asyncio.Event()
        async def navigate(*_args, **_kwargs):
            entered.set()
            await asyncio.Event().wait()
        page.goto.side_effect = navigate
        task = asyncio.create_task(browser_app().create_browser_page(launcher, 1))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    with mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(run())
    for resource in (page, context, browser):
        resource.close.assert_awaited_once()


def test_hung_close_that_delays_cancellation_does_not_block_other_resources():
    page, context, browser = Resource(), Resource(), Resource()
    async def run():
        release = asyncio.Event()
        async def stubborn_close():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await release.wait()
        page.close.side_effect = stubborn_close
        errors = await asyncio.wait_for(module.close_browser_resources(context, browser, page, 0.02), 0.5)
        assert len(errors) == 1 and isinstance(errors[0], TimeoutError)
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
        release.set()
        await asyncio.sleep(0)
    asyncio.run(run())


def test_cancellation_during_cleanup_still_closes_remaining_resources():
    page, context, browser = Resource(), Resource(), Resource()
    async def run():
        entered = asyncio.Event()
        async def hang():
            entered.set()
            await asyncio.Event().wait()
        page.close.side_effect = hang
        task = asyncio.create_task(module.close_browser_resources(context, browser, page, 0.02))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()
    asyncio.run(run())


def test_two_browser_sessions_do_not_close_each_other():
    app = browser_app()
    a, ab, ac, ap = browser_resources()
    b, bb, bc, bp = browser_resources()
    ap.goto.side_effect = RuntimeError("A failed")
    async def run():
        failed, live = await asyncio.gather(app.create_browser_page(a, 1),
                                          app.create_browser_page(b, 2), return_exceptions=True)
        assert isinstance(failed, RuntimeError)
        assert live == (bb, bc, bp)
        for resource in (bb, bc, bp):
            resource.close.assert_not_awaited()
        await module.close_browser_resources(bc, bb, bp)
    with mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(run())
    for resource in (ab, ac, ap, bb, bc, bp):
        resource.close.assert_awaited_once()


def test_manual_profile_navigation_failure_uses_bounded_cleanup(tmp_path):
    app = make_start_app()
    app.tree.selection = lambda: ("1",)
    browser, context, page = Resource(), Resource(), Resource()
    context.pages = [page]
    context.add_cookies = mock.AsyncMock()
    context.new_page = mock.AsyncMock(return_value=page)
    browser.new_context = mock.AsyncMock(return_value=context)
    page.goto = mock.AsyncMock(side_effect=RuntimeError("navigation failed"))
    factory = mock.MagicMock()
    factory.__aenter__.return_value.chromium.launch = mock.AsyncMock(return_value=browser)
    with mock.patch.object(module, "APP_DATA_DIR", str(tmp_path)), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None), \
         mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "close_browser_resources", wraps=module.close_browser_resources) as cleanup, \
         mock.patch.object(module.threading, "Thread") as thread:
        app.open_selected_profile()
        thread.call_args.kwargs["target"]()
        cleanup.assert_awaited_once_with(context, browser, page)
    for resource in (page, context, browser):
        resource.close.assert_awaited_once()


@pytest.mark.parametrize("outcome", ["SUCCESS", "FAILED", "ERROR", "CHECKPOINT", "STOP", "CANCEL"])
def test_account_exit_paths_cleanup_only_own_browser(tmp_path, outcome):
    from test_cookie_session import make_app, COOKIE, UID
    app, context, page, _events = make_app(tmp_path)
    browser = app.create_browser_page.return_value[0]
    other_browser = Resource()
    second = module.import_account_record(account("22222"))
    app.account_states.sync([{**module.import_account_record(account(UID)).to_account_dict(), "stt": 1, "account_id": UID},
                             {**second.to_account_dict(), "stt": 2, "account_id": "22222"}])
    app.run_config = module.RunConfig({"modes": {}, "options": {}, "targets": ""})
    if outcome == "FAILED":
        app.authenticate_facebook_account = mock.AsyncMock(return_value=(module.LOGIN_INVALID, "invalid"))
    elif outcome == "ERROR":
        app.authenticate_facebook_account = mock.AsyncMock(side_effect=RuntimeError("browser error"))
    elif outcome == "CHECKPOINT":
        app.authenticate_facebook_account = mock.AsyncMock(return_value=(module.LOGIN_CHECKPOINT, "checkpoint"))
    elif outcome in {"CANCEL", "STOP"}:
        async def cancel(*_args):
            if outcome == "STOP":
                app.stop_requested, app.is_running = True, False
            raise asyncio.CancelledError()
        app.authenticate_facebook_account = cancel
    else:
        app.authenticate_facebook_account = mock.AsyncMock(return_value=(module.LOGIN_SUCCESS, "valid"))
    async def run():
        try:
            await app.process_account_scoped(object(), 1, UID, COOKIE, None, asyncio.Semaphore(1))
        except asyncio.CancelledError:
            assert outcome in {"CANCEL", "STOP"}
    with mock.patch.object(module, "output_path", side_effect=lambda name: str(tmp_path / name)):
        asyncio.run(run())
    for resource in (browser, context, page):
        resource.close.assert_awaited_once()
    other_browser.close.assert_not_awaited()
    assert app.account_states.get(2)["status"] == "UNKNOWN"


def test_async_worker_methods_do_not_call_tk_directly():
    tree = ast.parse(inspect.getsource(module))
    violations = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = ast.unparse(node.func.value)
            if owner.startswith(("self.txt_", "self.ent_", "self.chk_", "self.root", "self.tree", "self.proxy_mode")):
                # Queued callbacks are UI work, not worker-thread accesses.
                nested = [n for n in ast.walk(function) if isinstance(n, ast.FunctionDef) and node in ast.walk(n)]
                if not nested:
                    violations.append((function.name, node.lineno, owner))
    assert violations == []
