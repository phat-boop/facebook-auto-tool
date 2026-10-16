"""Per-account activity timers shared by Home, Management and Result Center."""
import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

import client_app as module
from test_feed_browser_runtime import support_page
from test_targeted_runtime import make_app


def countdown_app():
    history = mock.Mock(load=mock.Mock(return_value=None))
    app = make_app(history)
    app.is_running, app.stop_requested = True, False
    for index in (1, 2):
        app.account_states.update(index, status="LIVE", current_action="Ready")
    history.save.reset_mock()
    return app, history


def test_home_and_management_render_the_same_decreasing_countdown():
    app, history = countdown_app()
    app.account_state_tree = mock.Mock()
    app.account_state_tree.exists.return_value = True
    app.tree = mock.Mock()
    app.tree.exists.return_value = True
    app.tree.item.return_value = module.management_account_values(app.account_states.get(1))
    app.refresh_create_page_results_dialog = mock.Mock()
    app.refresh_state_summary = mock.Mock()
    for remaining in (130, 129, 0):
        app.account_states.set_activity_wait(1, remaining, "Lướt Feed đệm")
        app.refresh_account_state_row(1)
        state = app.account_states.get(1)
        expected = f"Lướt Feed đệm - còn {remaining}s ({remaining // 60:02d}:{remaining % 60:02d})"
        assert app.account_state_tree.item.call_args.kwargs["values"][-1] == expected
        updates = [call for call in app.tree.item.call_args_list if "values" in call.kwargs]
        assert updates[-1].kwargs["values"][9] == expected
        assert module.result_values(state)[9] == expected
        assert state["current_action"] == "Ready"
        assert app.account_states.get(2)["activity_wait_remaining"] is None
    history.save.assert_not_called()


@pytest.mark.parametrize("scroll,label", [(True, "Lướt Feed đệm"), (False, "Xem thông báo")])
def test_activity_ticks_every_second_in_its_account_context(scroll, label):
    app, history = countdown_app()
    clock = [0.0]
    snapshots = []
    real_sleep = asyncio.sleep

    async def sleep(delay):
        clock[0] += delay
        await real_sleep(0)

    def refresh(index):
        state = app.account_states.get(index)
        if state["activity_wait_remaining"] is not None:
            snapshots.append((index, state["activity_wait_remaining"], module.account_action_label(state)))
            if len(snapshots) == 3:
                app.stop_requested = True

    app.request_ui_refresh = mock.Mock(side_effect=refresh)
    app._smooth_human_scroll = mock.AsyncMock()

    async def wait_for_ticks(*_args):
        while not app.stop_requested:
            await real_sleep(0)

    app.guard_facebook_checkpoint = mock.AsyncMock(side_effect=wait_for_ticks)

    async def run():
        token = app.account_log_context.set(1)
        try:
            await app._wait_support_activity(support_page(), 130, scroll=scroll)
        finally:
            app.account_log_context.reset(token)

    with mock.patch.object(module, "time", SimpleNamespace(monotonic=lambda: clock[0])), \
         mock.patch.object(module.random, "uniform", return_value=0), \
         mock.patch.object(module.asyncio, "sleep", side_effect=sleep):
        asyncio.run(run())
    assert snapshots[:2] == [(1, 130, f"{label} - còn 130s (02:10)"),
                             (1, 129, f"{label} - còn 129s (02:09)")]
    assert snapshots[-1][1] < 129
    assert app.account_states.get(1)["activity_wait_remaining"] is None
    assert app.account_states.get(2)["activity_wait_remaining"] is None
    history.save.assert_not_called()


@pytest.mark.parametrize("ending", ["complete", "stop", "cancel", "error", "checkpoint"])
def test_countdown_cleanup_preserves_terminal_status_and_leaves_no_task(ending):
    app, _history = countdown_app()
    app.request_ui_refresh = mock.Mock()
    clock = [0.0]

    async def scroll(*_args):
        if ending == "complete":
            clock[0] = 130
        elif ending == "stop":
            app.stop_requested = True
        elif ending == "checkpoint":
            app.account_states.update(1, status="CHECKPOINT", current_action="Checkpoint stopped")
            raise module.FacebookCheckpointStopped()
        elif ending == "cancel":
            raise asyncio.CancelledError()
        else:
            raise RuntimeError("browser closed")

    app._smooth_human_scroll = mock.AsyncMock(side_effect=scroll)

    async def run():
        before = asyncio.all_tasks()
        token = app.account_log_context.set(1)
        try:
            if ending in {"complete", "stop"}:
                await app._wait_support_activity(support_page(), 130, scroll=True)
            else:
                error = {"checkpoint": module.FacebookCheckpointStopped,
                         "cancel": asyncio.CancelledError, "error": RuntimeError}[ending]
                with pytest.raises(error):
                    await app._wait_support_activity(support_page(), 130, scroll=True)
        finally:
            app.account_log_context.reset(token)
        assert asyncio.all_tasks() == before

    with mock.patch.object(module, "time", SimpleNamespace(monotonic=lambda: clock[0])), \
         mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        asyncio.run(run())
    state = app.account_states.get(1)
    assert state["activity_wait_remaining"] is None
    assert state["activity_wait_label"] == ""
    if ending == "checkpoint":
        assert module.account_action_label(state) == "Checkpoint stopped"
        assert state["status"] == "CHECKPOINT"


def test_concurrent_accounts_keep_their_own_activity_duration():
    app, history = countdown_app()
    app.request_ui_refresh = mock.Mock()

    async def run():
        both_started = asyncio.Event()
        seen = {}

        async def scroll(*_args):
            index = app.account_log_context.get()
            seen[index] = app.account_states.get(index)["activity_wait_remaining"]
            if len(seen) == 2:
                both_started.set()
            await both_started.wait()
            raise asyncio.CancelledError()

        app._smooth_human_scroll = mock.AsyncMock(side_effect=scroll)

        async def worker(index, duration):
            token = app.account_log_context.set(index)
            try:
                await app._wait_support_activity(support_page(), duration, scroll=True)
            finally:
                app.account_log_context.reset(token)

        await asyncio.gather(worker(1, 130), worker(2, 45), return_exceptions=True)
        assert seen == {1: 130, 2: 45}

    asyncio.run(run())
    assert all(app.account_states.get(index)["activity_wait_remaining"] is None for index in (1, 2))
    history.save.assert_not_called()
