"""Browser concurrency is separate from Page limits and login status."""
import asyncio
import contextvars
from unittest import mock

import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app, start_without_real_worker


def batch_app(page_workers=1, threads=5, batch_size=5, selected=None):
    app = make_start_app()
    app.txt_accounts.text = "\n".join(f"c_user={10000 + i}; xs=test;" for i in range(1, 6))
    app.txt_proxies.text = ""
    app.txt_targets.text = "Test Page|Local service"
    for name, value in (("threads", threads), ("batch_size", batch_size),
                        ("max_create_page_workers", page_workers), ("warmup_seconds", 1)):
        getattr(app, "ent_" + name).get.return_value = str(value)
    app.mode_vars = {"create_page": mock.Mock()}
    app.mode_vars["create_page"].get.return_value = True
    app.chk_warmup.get.return_value = True
    app.reset_create_page_account_results = mock.Mock()
    app.account_log_context = contextvars.ContextVar("batch_test_account", default=None)
    app.update_tree_row = mock.Mock()
    app.remove_processed_create_page_accounts_from_input = mock.Mock()
    app.guard_facebook_checkpoint = mock.AsyncMock()
    app.authenticate_facebook_account = mock.AsyncMock(return_value=(module.LOGIN_SUCCESS, "verified"))
    app.lbl_stat_running, app.lbl_stat_success, app.lbl_stat_failed = (mock.Mock() for _ in range(3))
    app.reload_table_from_text()
    if selected is not None:
        for item in app.tree.get_children():
            values = list(app.tree.item(item, "values"))
            values[0] = "[✔]" if int(item) in selected else "[ ]"
            app.tree.item(item, values=values)
    start_without_real_worker(app)
    return app


def attach_browsers(app):
    resources = {}

    async def create(_playwright, index, **_kwargs):
        browser, context, page = [mock.Mock(close=mock.AsyncMock()) for _ in range(3)]
        page.account_index = index
        resources[index] = (browser, context, page)
        return browser, context, page

    async def watch(*_args):
        await asyncio.Event().wait()

    app.create_browser_page = create
    app.watch_facebook_checkpoint = watch
    return resources


def assert_closed(resources):
    for account_resources in resources.values():
        for resource in account_resources:
            resource.close.assert_awaited_once()


@pytest.mark.parametrize("page_workers", [1, 3, 5])
def test_five_browsers_warm_up_together_while_page_limit_is_respected(page_workers):
    app = batch_app(page_workers)
    resources = attach_browsers(app)

    async def run():
        warmed, creating = set(), set()
        all_warming, release_warmup = asyncio.Event(), asyncio.Event()
        page_slots_full, release_pages = asyncio.Event(), asyncio.Event()
        max_creating = 0

        async def warmup(page, _name, _seconds):
            warmed.add(page.account_index)
            if len(warmed) == 5:
                all_warming.set()
            await release_warmup.wait()

        async def create_page(_app, page, *_args):
            nonlocal max_creating
            index = page.account_index
            creating.add(index)
            max_creating = max(max_creating, len(creating))
            if len(creating) == page_workers:
                page_slots_full.set()
            try:
                await release_pages.wait()
                await asyncio.sleep(0)
                return []
            finally:
                creating.remove(index)

        app.warm_up_feed = warmup
        with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()), \
             mock.patch.object(module, "_pc_run_create_page", side_effect=create_page):
            task = asyncio.create_task(app.main_worker())
            try:
                await asyncio.wait_for(all_warming.wait(), 2)
                assert warmed == {1, 2, 3, 4, 5}
                assert app.account_states.processing_count() == 5
                assert all(app.account_states.get(i)["status"] == "LIVE" for i in warmed)
                app.refresh_state_summary()
                app.lbl_stat_running.config.assert_called_with(text="5")
                release_warmup.set()
                await asyncio.wait_for(page_slots_full.wait(), 2)
                assert len(creating) == page_workers
                assert app.account_states.processing_count() == 5
                for index in warmed - creating:
                    assert "Chờ lượt tạo Page" in app.account_states.get(index)["current_action"]
                release_pages.set()
                await asyncio.wait_for(task, 3)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        assert max_creating == page_workers
        assert app.account_states.processing_count() == 0
        app.refresh_state_summary()
        app.lbl_stat_running.config.assert_called_with(text="0")
        assert not app.worker_tasks

    asyncio.run(run())
    assert_closed(resources)
    logs = [call.args[0] for call in app.log.call_args_list]
    assert any("5 tài khoản" in line and "5 luồng đồng thời" in line for line in logs)
    assert any(f"{page_workers} luồng tạo Page" in line for line in logs)


def test_stop_cancels_page_waiters_and_closes_all_five_owned_browsers():
    app = batch_app(page_workers=1)
    resources = attach_browsers(app)

    async def run():
        warmed = set()
        all_warmed, page_entered = asyncio.Event(), asyncio.Event()
        submitted = []

        async def warmup(page, *_args):
            warmed.add(page.account_index)
            if len(warmed) == 5:
                all_warmed.set()
            await all_warmed.wait()

        async def create_page(_app, page, *_args):
            submitted.append(page.account_index)
            page_entered.set()
            await asyncio.Event().wait()

        app.warm_up_feed = warmup
        with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()), \
             mock.patch.object(module, "_pc_run_create_page", side_effect=create_page):
            root = asyncio.create_task(app.main_worker())
            try:
                await asyncio.wait_for(page_entered.wait(), 2)
                await asyncio.sleep(0)
                assert app.account_states.processing_count() == 5
                app.stop_requested = True
                root.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(root, 2)
            finally:
                if not root.done():
                    root.cancel()
                    await asyncio.gather(root, return_exceptions=True)
        assert len(submitted) == 1
        assert app.account_states.processing_count() == 0
        assert not app.worker_tasks
        assert all(app.account_states.get(i)["status"] == "LIVE" for i in range(1, 6))
        assert all(app.account_states.get(i)["last_task_result"] == "SKIPPED" for i in range(1, 6))
        assert app.create_page_semaphore._value == 1

    asyncio.run(run())
    assert_closed(resources)


@pytest.mark.parametrize("selection", [{1}, {2, 4}])
def test_checked_subset_is_not_silently_expanded_to_the_whole_batch(selection):
    app = batch_app(selected=selection)
    app.process_account_scoped = mock.AsyncMock()
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
        asyncio.run(app.main_worker())
    assert {call.args[1] for call in app.process_account_scoped.call_args_list} == selection
    logs = [call.args[0] for call in app.log.call_args_list]
    assert any(f"{len(selection)}/5 tài khoản" in line and "dấu chọn" in line for line in logs)
    assert any("5 luồng đồng thời" in line for line in logs)
    assert all("Không được chọn" in app.account_states.get(i)["current_action"]
               for i in set(range(1, 6)) - selection)


def test_stop_clears_browser_queue_without_starting_remaining_accounts():
    app = batch_app(threads=2)
    resources = attach_browsers(app)

    async def run():
        entered = set()
        full = asyncio.Event()

        async def warmup(page, *_args):
            entered.add(page.account_index)
            if len(entered) == 2:
                full.set()
            await asyncio.Event().wait()

        app.warm_up_feed = warmup
        with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
            root = asyncio.create_task(app.main_worker())
            try:
                await asyncio.wait_for(full.wait(), 2)
                assert app.account_states.processing_count() == 2
                app.stop_requested = True
                root.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(root, 2)
            finally:
                if not root.done():
                    root.cancel()
                    await asyncio.gather(root, return_exceptions=True)
        assert app.account_states.processing_count() == 0
        assert len(resources) == 2
        for index in set(range(1, 6)) - entered:
            assert app.account_states.get(index)["status"] == "UNKNOWN"
            assert "Đã dừng khi chờ" in app.account_states.get(index)["current_action"]
        assert not app.worker_tasks

    asyncio.run(run())
    assert_closed(resources)


def test_manual_stt_filter_keeps_priority_over_checked_rows():
    app = batch_app(selected={1})
    values = dict(app.run_config)
    values["selected_indexes"] = "2,4-5"
    app.run_config = module.RunConfig(values)
    app.process_account_scoped = mock.AsyncMock()
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
        asyncio.run(app.main_worker())
    assert [call.args[1] for call in app.process_account_scoped.call_args_list] == [2, 4, 5]


@pytest.mark.parametrize("threads,batch_size,expected_batches,maximum", [(5, 5, 1, 5), (2, 5, 1, 2), (5, 2, 3, 2)])
def test_browser_workers_obey_threads_and_batch_size(threads, batch_size, expected_batches, maximum):
    app = batch_app(threads=threads, batch_size=batch_size)
    active = set()
    peak = 0
    seen = []

    async def worker(_p, index, _name, _cookie, _proxy, semaphore, **_kwargs):
        nonlocal peak
        async with app.account_worker_slot(index, semaphore):
            active.add(index)
            seen.append(index)
            peak = max(peak, len(active))
            try:
                await asyncio.sleep(0.01)
            finally:
                active.remove(index)

    app.process_account_scoped = worker
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
        asyncio.run(app.main_worker())
    assert seen == [1, 2, 3, 4, 5]
    assert peak == maximum
    assert app.account_states.processing_count() == 0
    logs = [call.args[0] for call in app.log.call_args_list]
    assert sum(line.startswith("[BẮT ĐẦU ĐỢT]") for line in logs) == expected_batches


def test_processing_flag_is_transient_and_not_the_same_as_login_status():
    history = mock.Mock()
    history.load.return_value = None
    store = module.AccountStateStore(history)
    records = [{"stt": i, "uid": str(i), "account_id": str(i)} for i in (1, 2)]
    store.sync(records)
    store.update(1, status="LIVE")
    store.update(2, status="CHECKING")
    history.save.reset_mock()
    assert store.processing_count() == 0
    store.set_processing(1, True)
    assert store.processing_count() == 1
    assert store.get(2)["is_processing"] is False
    store.set_processing(1, False)
    history.save.assert_not_called()
    assert store.processing_count() == 0
    store.set_processing(1, True)
    store.sync(records)
    assert store.processing_count() == 0
    assert store.get(1)["status"] == "LIVE"


@pytest.mark.parametrize("failure", ["proxy", "browser", "invalid", "checkpoint"])
def test_account_exit_clears_running_counter_without_touching_other_accounts(failure):
    app = batch_app()
    resources = attach_browsers(app)
    app.warm_up_feed = mock.AsyncMock()
    if failure == "proxy":
        app.resolve_effective_proxy = mock.AsyncMock(side_effect=ConnectionError("proxy failed"))
    elif failure == "browser":
        app.create_browser_page = mock.AsyncMock(side_effect=RuntimeError("launch failed"))
    else:
        result = module.LOGIN_INVALID if failure == "invalid" else module.LOGIN_CHECKPOINT
        app.authenticate_facebook_account.return_value = (result, "invalid session")
        app.record_create_page_account_result = mock.Mock()
    asyncio.run(app.process_account_scoped(None, 1, "10001", "c_user=10001; xs=test;", None,
                                          asyncio.Semaphore(5)))
    assert app.account_states.processing_count() == 0
    assert not app.account_states.get(1)["is_processing"]
    assert app.account_states.get(2)["status"] == "UNKNOWN"
    assert not app.account_states.get(2)["is_processing"]
    assert_closed(resources)
