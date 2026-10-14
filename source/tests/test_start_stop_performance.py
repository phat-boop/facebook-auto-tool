"""Bounded UI/log work and cancellation without live Facebook access."""
import asyncio
import contextvars
import queue
import sqlite3
import threading
import time
from unittest import mock

import pytest

import client_app as module
from test_stop_cancellation import make_app as make_stop_app, join_and_cleanup


def make_log_app(history=None):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.root = mock.Mock()
    app.account_states = module.AccountStateStore(history)
    app.account_states.sync([{"stt": index, "uid": str(index), "account_id": str(index)}
                             for index in (1, 2)])
    app.account_log_context = contextvars.ContextVar("performance_log", default=None)
    app._ui_run_context = contextvars.ContextVar("performance_ui", default=None)
    app.ui_queue = queue.Queue()
    app.close_requested = False
    app.global_logs = []
    app.global_log_lock = threading.RLock()
    app.selected_log_account = None
    app.refresh_account_state_row = mock.Mock()
    app.refresh_state_summary = mock.Mock()
    app.refresh_result_center_summary = mock.Mock()
    app.render_log_view = mock.Mock()
    return app


def test_debug_is_dropped_before_memory_ui_or_database():
    history = mock.Mock()
    history.load.return_value = None
    app = make_log_app(history)
    history.save.reset_mock()
    app.log("prefix [DEBUG] private diagnostic", account_index=1)
    app.log("[DEBUG] global diagnostic")
    app.account_states.append_log(2, "[DEBUG] direct call")
    assert app.account_states.get(1)["logs"] == []
    assert app.account_states.get(2)["logs"] == []
    assert app.global_logs == [] and app.ui_queue.empty()
    history.save.assert_not_called()


def test_only_important_logs_persist_even_with_debug_enabled(monkeypatch):
    monkeypatch.setattr(module, "ENABLE_DEBUG_LOG", True)
    history = mock.Mock()
    history.load.return_value = None
    app = make_log_app(history)
    history.save.reset_mock()
    for message in ("[DEBUG] enabled", "[*] progress", "[PAGE][WAIT] 100s",
                    "[✔] verified", "[-] failed", "[!] warning", "[ERROR] exception"):
        app.log(message, account_index=1)
    assert len(app.account_states.get(1)["logs"]) == 7
    assert history.save.call_count == 4
    assert all(call.args[2] == "LOG" for call in history.save.call_args_list)
    assert all("[DEBUG]" not in call.args[3] for call in history.save.call_args_list)
    app.account_states.update(1, status="LIVE")
    app.account_states.record_task(1, "FRIEND_REQUEST", "SUCCESS", "verified")
    assert history.save.call_args.args[2] == "TASK"


def test_debug_cannot_persist_later_through_current_action(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ENABLE_DEBUG_LOG", True)
    path = tmp_path / "history.db"
    store = module.AccountStateStore(module.AccountHistoryStore(path))
    store.sync([{"stt": 1, "uid": "11111", "account_id": "11111"}])
    store.append_log(1, "[*] [DEBUG] debug-only-diagnostic", current_action="debug-only-action")
    store.update(1, status="LIVE")
    with sqlite3.connect(path) as db:
        dump = "\n".join(db.iterdump())
    assert "debug-only-diagnostic" not in dump
    assert "debug-only-action" not in dump
    assert "[DEBUG]" in store.get(1)["logs"][0]


def test_log_limits_and_lightweight_snapshot_do_not_mix_accounts():
    app = make_log_app()
    for number in range(module.MAX_LOG_LINES + 40):
        app.log(f"account A {number}", account_index=1)
        app.log(f"global {number}")
    assert len(app.account_states.get(1)["logs"]) == module.MAX_LOG_LINES
    assert len(app.global_logs) == module.MAX_LOG_LINES
    assert app.account_states.get(2)["logs"] == []
    assert app.account_states.get(1, include_logs=False)["logs"] == []
    assert app.ui_queue.qsize() == 1


def test_ui_refresh_coalesces_rows_logs_and_summaries():
    app = make_log_app()
    app.selected_log_account = 1
    for number in range(1000):
        app.log(f"progress {number}", account_index=1 + number % 2)
    assert app.ui_queue.qsize() == 1
    app._drain_ui_queue()
    assert app.refresh_account_state_row.call_args_list == [mock.call(1), mock.call(2)]
    app.refresh_state_summary.assert_called_once()
    app.refresh_result_center_summary.assert_called_once()
    app.render_log_view.assert_called_once()
    app.root.after.assert_called_once_with(module.UI_POLL_INTERVAL_MS, app._drain_ui_queue)


def test_queue_drain_yields_to_tk_with_work_remaining(monkeypatch):
    app = make_log_app()
    monkeypatch.setattr(module, "UI_MAX_CALLBACKS", 3)
    monkeypatch.setattr(module, "UI_DRAIN_BUDGET_SECONDS", 10)
    callback = mock.Mock()
    for _ in range(10):
        app.post_ui(callback)
    app._drain_ui_queue()
    assert callback.call_count == 3 and app.ui_queue.qsize() == 7
    app.root.after.assert_called_once_with(module.UI_BUSY_INTERVAL_MS, app._drain_ui_queue)


def test_large_row_flush_requeues_remaining_rows_without_losing_updates(monkeypatch):
    app = make_log_app()
    monkeypatch.setattr(module, "UI_MAX_CALLBACKS", 1)
    app.request_ui_refresh(1)
    app.request_ui_refresh(2)
    app.ui_queue.get_nowait()()
    app.refresh_account_state_row.assert_called_once_with(1)
    assert app.ui_queue.qsize() == 1
    app.ui_queue.get_nowait()()
    assert app.refresh_account_state_row.call_args_list == [mock.call(1), mock.call(2)]
    assert app.ui_queue.empty()


def test_redundant_action_does_not_write_but_real_status_change_does():
    history = mock.Mock()
    history.load.return_value = None
    app = make_log_app(history)
    history.save.reset_mock()
    app.account_states.update(1, current_action="Chưa chạy")
    history.save.assert_not_called()
    app.account_states.update(1, status="LIVE")
    assert history.save.call_count == 1


def test_stale_refresh_cannot_block_the_next_generation():
    app = make_log_app()
    app._run_generation = 1
    app.request_ui_refresh(1)
    stale = app.ui_queue.get_nowait()
    app._run_generation = 2
    app.request_ui_refresh(2)
    stale()
    app.ui_queue.get_nowait()()
    app.refresh_account_state_row.assert_called_once_with(2)


def test_log_renderer_appends_only_new_lines_and_skips_identical_content():
    app = make_log_app()
    app.render_log_view = module.MainToolApp.render_log_view.__get__(app)
    app.txt_log, app.lbl_log_scope = mock.Mock(), mock.Mock()
    app.global_logs = ["line A"]
    app.render_log_view()
    app.render_log_view()
    app.txt_log.delete.assert_called_once()
    app.txt_log.insert.assert_called_once()
    app.global_logs.append("line B")
    app.render_log_view()
    assert app.txt_log.delete.call_count == 1
    app.txt_log.insert.assert_called_with("end", "line B\n")
    app.global_logs = ["trimmed line"]
    app.render_log_view()
    assert app.txt_log.delete.call_count == 2


def test_stop_updates_buttons_before_the_ui_queue_and_restores_text():
    app = make_stop_app()
    app.is_running = True
    app.btn_stop.cget.return_value = "original stop label"
    callback = mock.Mock()
    for _ in range(100):
        app.ui_queue.put(callback)
    start = time.perf_counter()
    app.stop_bot()
    assert time.perf_counter() - start < 0.2
    callback.assert_not_called()
    assert app.stop_requested
    app.btn_start.config.assert_called_with(state="disabled")
    app.btn_stop.config.assert_called_with(state="disabled", text="ĐANG DỪNG...")
    app.finish_run()
    assert mock.call(text="original stop label") in app.btn_stop.config.call_args_list
    assert app.worker_tasks == [] and app.worker_root_task is None and app.worker_loop is None


def test_stop_cancels_unlisted_child_before_root_cleanup_finishes():
    app = make_stop_app()
    entered, child_stopped, release = (threading.Event() for _ in range(3))

    async def child():
        entered.set()
        try:
            await asyncio.sleep(3600)
        finally:
            child_stopped.set()

    async def worker():
        asyncio.create_task(child())
        try:
            await asyncio.sleep(3600)
        finally:
            while not release.is_set():
                await asyncio.sleep(0.01)

    app.main_worker = worker
    app.start_thread()
    assert entered.wait(2)
    try:
        app.stop_bot()
        assert child_stopped.wait(1), "unlisted application child still running"
    finally:
        release.set()
        assert join_and_cleanup(app)


def test_all_browser_closes_start_without_waiting_for_a_hung_page():
    async def run():
        release, all_started = asyncio.Event(), asyncio.Event()
        started = []

        async def close(name):
            started.append(name)
            if len(started) == 3:
                all_started.set()
            await release.wait()

        resources = [mock.Mock(close=mock.AsyncMock()) for _ in range(3)]
        for resource, name in zip(resources, ("page", "context", "browser")):
            async def wait_close(name=name):
                await close(name)
            resource.close.side_effect = wait_close
        page, context, browser = resources
        task = asyncio.create_task(module.close_browser_resources(context, browser, page))
        try:
            await asyncio.wait_for(all_started.wait(), 0.5)
        finally:
            release.set()
            errors = await task
        assert errors == [] and set(started) == {"page", "context", "browser"}
        for resource in resources:
            resource.close.assert_awaited_once()
    asyncio.run(run())


def test_notification_http_is_cancellable_and_disposes_request():
    async def run():
        entered = asyncio.Event()
        request = mock.Mock(dispose=mock.AsyncMock())

        async def wait_post(*_args, **_kwargs):
            entered.set()
            await asyncio.sleep(3600)

        request.post = mock.AsyncMock(side_effect=wait_post)
        manager = mock.MagicMock()
        manager.__aenter__.return_value.request.new_context = mock.AsyncMock(return_value=request)
        with mock.patch.object(module, "async_playwright", return_value=manager):
            task = asyncio.create_task(module.send_telegram_alert_async("test-token", "test-chat", "message"))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        request.dispose.assert_awaited_once()
        manager.__aexit__.assert_awaited_once()
    asyncio.run(run())
