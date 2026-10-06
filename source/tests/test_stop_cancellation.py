"""Stop a real worker thread without requiring a Facebook connection."""
import asyncio
import contextvars
import queue
import threading
import time
from unittest import mock

import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app


def make_app():
    app = make_start_app()
    app.close_requested = False
    app.ui_queue = queue.Queue()
    app.post_ui = module.MainToolApp.post_ui.__get__(app)
    app._ui_run_context = contextvars.ContextVar("test_run_ui", default=None)
    return app


def drain(app):
    while not app.ui_queue.empty():
        app.ui_queue.get_nowait()()


def join_and_cleanup(app, timeout=1):
    thread = app.run_thread
    thread.join(timeout)
    stopped = not thread.is_alive()
    if not stopped:
        # Only the synthetic test loop: keep a failing regression from leaking.
        loop = app.worker_loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(lambda: [task.cancel() for task in asyncio.all_tasks(loop)])
        thread.join(2)
    assert not thread.is_alive(), "test worker cleanup timed out"
    drain(app)
    return stopped


def test_stop_cancels_root_outside_batch_and_restores_buttons():
    app = make_app()
    entered = threading.Event()
    cleaned = []

    async def worker():
        app.worker_loop = asyncio.get_running_loop()
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            cleaned.append(True)

    app.main_worker = worker
    app.start_thread()
    assert entered.wait(2)
    start = time.monotonic()
    app.stop_bot()
    assert app.stop_requested
    assert join_and_cleanup(app), "Stop did not cancel the root run task"
    assert time.monotonic() - start < 1
    assert cleaned == [True]
    assert app.run_status == "CANCELLED"
    assert not app.is_running
    assert app.worker_loop is None
    assert app.worker_tasks == []
    assert getattr(app, "worker_root_task", None) is None
    app.btn_start.config.assert_called_with(state="normal")
    app.btn_stop.config.assert_called_with(state="disabled")


def test_stop_is_idempotent_and_cleanup_finishes_before_enabling_start():
    app = make_app()
    entered, cleanup_entered, release = (threading.Event() for _ in range(3))
    cleanup_count = []

    async def worker():
        app.worker_loop = asyncio.get_running_loop()
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            cleanup_count.append(True)
            cleanup_entered.set()
            while not release.is_set():
                await asyncio.sleep(0.02)

    app.main_worker = worker
    app.start_thread()
    assert entered.wait(2)
    app.stop_bot()
    try:
        assert cleanup_entered.wait(0.5)
        app.stop_bot()
        app.stop_bot()
        drain(app)
        assert app.is_running
        assert app.btn_start.config.call_args.kwargs["state"] == "disabled"
    finally:
        release.set()
        stopped = join_and_cleanup(app)
    assert stopped
    assert cleanup_count == [True]
    app.stop_bot()
    assert app.run_status == "CANCELLED"


def test_stop_before_worker_loop_is_ready():
    app = make_app()
    entered, release = threading.Event(), threading.Event()
    main_started = []
    real_process = app.run_process

    def delayed_process():
        entered.set()
        release.wait(2)
        real_process()

    async def worker():
        main_started.append(True)

    app.run_process, app.main_worker = delayed_process, worker
    app.start_thread()
    assert entered.wait(2)
    app.stop_bot()
    release.set()
    assert join_and_cleanup(app)
    assert main_started == []
    assert app.run_status == "CANCELLED"


def test_old_run_stop_and_ui_callbacks_cannot_affect_new_run():
    app = make_app()
    entered = threading.Event()

    async def worker():
        app.worker_loop = asyncio.get_running_loop()
        entered.set()
        await asyncio.sleep(60)

    app.main_worker = worker
    app.start_thread()
    assert entered.wait(2)
    old_generation = getattr(app, "_run_generation", 0)
    stale = mock.Mock()
    token = app._ui_run_context.set(old_generation)
    app.post_ui(stale)
    app._ui_run_context.reset(token)
    old_ui = app.ui_queue.get_nowait()
    app.stop_bot()
    assert join_and_cleanup(app)
    entered.clear()
    app.start_thread()
    assert entered.wait(2)
    try:
        old_ui()
        app.worker_loop.call_soon_threadsafe(app._cancel_worker_tasks, old_generation)
        time.sleep(0.05)
        stale.assert_not_called()
        assert app.run_thread.is_alive()
        assert not app.stop_requested
    finally:
        app.stop_bot()
        assert join_and_cleanup(app)


@pytest.mark.parametrize("batch_size", ["1", "5"])
def test_stop_cancels_running_and_pending_accounts_without_new_batch(batch_size):
    app = make_app()
    app.ent_threads.get.return_value = "1"
    app.ent_batch_size.get.return_value = batch_size
    entered = threading.Event()
    started, cleanup = [], []

    async def account_worker(_p, index, *_args, **_kwargs):
        async with _args[-1]:
            if app.stop_requested:
                return
            started.append(index)
            entered.set()
            try:
                await asyncio.sleep(60)
            finally:
                cleanup.append(index)

    app.process_account_scoped = account_worker
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
        app.start_thread()
        assert entered.wait(2)
        app.stop_bot()
        assert join_and_cleanup(app)
    assert started == [1]
    assert cleanup == [1]
    assert app.worker_tasks == []
    assert app.run_status == "CANCELLED"


def test_stop_after_loop_closed_does_not_raise():
    app = make_app()
    app.is_running = True
    app.worker_loop = mock.Mock()
    app.worker_loop.is_running.return_value = True
    app.worker_loop.call_soon_threadsafe.side_effect = RuntimeError("Event loop is closed")
    app.stop_bot()
    assert app.stop_requested


def test_stop_never_calls_task_cancel_on_ui_thread():
    app = make_app()
    app.is_running = True
    app.worker_loop = mock.Mock()
    app.worker_loop.is_running.return_value = True
    app.worker_root_task = mock.Mock()
    app.worker_root_task.done.return_value = False
    app.stop_bot()
    app.worker_root_task.cancel.assert_not_called()
    app.worker_loop.call_soon_threadsafe.assert_called_once()


@pytest.mark.parametrize("stage", ["login", "create_page"])
def test_cancelled_account_is_not_an_error_and_does_not_increase_failed_counters(stage):
    app = make_app()
    app.mode_vars = {"create_page": mock.Mock()}
    app.mode_vars["create_page"].get.return_value = stage == "create_page"
    entered = threading.Event()
    resources = [mock.Mock(close=mock.AsyncMock()) for _ in range(3)]
    browser, context, page = resources
    app.create_browser_page = mock.AsyncMock(return_value=(browser, context, page))
    app.guard_facebook_checkpoint = mock.AsyncMock()
    app.get_current_friends_count = mock.AsyncMock(return_value=0)
    app.update_tree_row = mock.Mock()
    app.reset_create_page_account_results = mock.Mock()

    async def wait_for_stop(*_args, **_kwargs):
        entered.set()
        await asyncio.sleep(60)

    app.watch_facebook_checkpoint = wait_for_stop
    app.run_create_page = wait_for_stop
    app.authenticate_facebook_account = (wait_for_stop if stage == "login" else
                                         mock.AsyncMock(return_value=(module.LOGIN_SUCCESS, "verified")))

    async def worker():
        await app.process_account(None, 1, "11111", "c_user=11111;", "", asyncio.Semaphore(1))

    app.main_worker = worker
    app.start_thread()
    assert entered.wait(2)
    app.stop_bot()
    assert join_and_cleanup(app)
    state = app.account_states.get(1)
    assert state["status"] == ("UNKNOWN" if stage == "login" else "LIVE")
    assert state["page_failed_count"] == state["friend_failed_count"] == 0
    assert state["page_success_count"] == state["friend_success_count"] == 0
    assert all(task["status"] != "RUNNING" for task in state["tasks"].values())
    assert app.run_status == "CANCELLED"
    for resource in resources:
        resource.close.assert_awaited_once()

