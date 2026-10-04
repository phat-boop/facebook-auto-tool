"""Core-only dispatch, configurable durations, and removal of stale options."""
import asyncio
import inspect
import json
from unittest import mock

import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app
import test_core as core_tests


REMOVED_OPTIONS = ("watch_reels", "view_stories", "cancel_old", "browse_web",
                   "interact_page", "chat_react")
REMOVED_MODES = ("post_page", "add_page_admin", "update_page_name", "invite_like_page",
                 "join_group", "auto_post", "auto_inbox", "seed_group", "change_bio",
                 "change_avatar", "invite_group", "scrape_uid", "seed_live", "change_pass",
                 "enable_2fa", "logout_sessions", "inbox_commenters", "post_joined_groups",
                 "comment_with_image", "scrape_group_members", "scrape_contacts")


def test_older_settings_do_not_restore_removed_automation(tmp_path):
    path = tmp_path / "settings.json"
    data = {key: True for key in REMOVED_OPTIONS}
    data.update(selected_modes={key: True for key in REMOVED_MODES}, watch_review_min="60")
    path.write_text(json.dumps(data), encoding="utf-8")
    app = make_start_app()
    app.mode_vars = {name: mock.Mock() for name in module.CORE_AUTOMATION_MODES}
    with mock.patch.object(module, "SETTINGS_FILE", str(path)):
        module.MainToolApp.load_settings(app)
    for variable in app.mode_vars.values():
        variable.set.assert_not_called()
    app.ent_warmup_seconds.insert.assert_not_called()
    app.ent_notification_seconds.insert.assert_not_called()
    for option in REMOVED_OPTIONS:
        assert not hasattr(app, "chk_" + option)


def test_snapshot_contains_only_core_modes_and_configured_durations(tmp_path):
    app = make_start_app()
    app.ent_warmup_seconds.get.return_value = "127"
    app.ent_notification_seconds.get.return_value = "23"
    app.mode_vars = {name: mock.Mock(get=mock.Mock(return_value=True))
                     for name in module.CORE_AUTOMATION_MODES + REMOVED_MODES}
    snapshot = app.capture_run_config()
    assert set(snapshot["modes"]) == set(module.CORE_AUTOMATION_MODES)
    assert set(snapshot["options"]) == {"warmup", "check_notif"}
    assert snapshot["warmup_seconds"] == 127 and snapshot["notification_seconds"] == 23
    app.ent_warmup_seconds.get.side_effect = AssertionError("worker read Tk")
    assert snapshot["warmup_seconds"] == 127
    app.ent_warmup_seconds.get.side_effect = None
    app.current_theme = next(iter(module.THEMES))
    path = tmp_path / "settings.json"
    with mock.patch.object(module, "SETTINGS_FILE", str(path)):
        module.MainToolApp.save_settings(app)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert set(saved["selected_modes"]) == set(module.CORE_AUTOMATION_MODES)


@pytest.mark.parametrize("value", ["", "abc", "1.5", "-1", "86401"])
def test_invalid_support_duration_is_rejected(value):
    app = make_start_app()
    app.ent_warmup_seconds.get.return_value = value
    with pytest.raises(ValueError, match="Feed"):
        app.capture_run_config()


@pytest.mark.parametrize("value", ["0", "1", "86400"])
def test_valid_support_duration(value):
    assert module.MainToolApp.activity_duration_seconds(value, "Feed") == int(value)


@pytest.mark.parametrize("action,duration,scroll", [("warm_up_feed", 47, True), ("check_notifications", 19, False)])
def test_support_action_uses_exact_user_duration(action, duration, scroll):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.is_running, app.stop_requested = True, False
    app.log = mock.Mock()
    app._wait_support_activity = mock.AsyncMock()
    page = mock.Mock()
    page.goto = mock.AsyncMock()
    button = page.locator.return_value.first
    button.count = mock.AsyncMock(return_value=1)
    button.click = mock.AsyncMock()
    asyncio.run(getattr(app, action)(page, "A", duration))
    if scroll:
        app._wait_support_activity.assert_awaited_once_with(page, duration, scroll=True)
    else:
        app._wait_support_activity.assert_awaited_once_with(page, duration)


@pytest.mark.parametrize("action", ["warm_up_feed", "check_notifications"])
def test_zero_duration_disables_support_action(action):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.is_running, app.stop_requested = True, False
    page = mock.Mock()
    asyncio.run(getattr(app, action)(page, "A", 0))
    assert not page.mock_calls


@pytest.mark.parametrize("scroll", [False, True])
def test_support_wait_is_bounded_and_observes_stop(scroll):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.is_running, app.stop_requested = True, False
    app.guard_facebook_checkpoint = mock.AsyncMock()
    page = mock.Mock()
    page.is_closed.return_value = False
    page.mouse.wheel = mock.AsyncMock()
    clock = [0.0]
    async def advance(delay):
        clock[0] += delay
    with mock.patch.object(module.time, "monotonic", side_effect=lambda: clock[0]), \
         mock.patch.object(module.asyncio, "sleep", side_effect=advance):
        asyncio.run(app._wait_support_activity(page, 17, scroll=scroll))
    assert clock[0] == 17
    app.stop_requested = True
    app.guard_facebook_checkpoint.reset_mock()
    asyncio.run(app._wait_support_activity(page, 999, scroll=scroll))
    app.guard_facebook_checkpoint.assert_not_awaited()
    assert not page.locator.called


def test_worker_ignores_removed_modes_and_options_even_in_stale_config():
    harness = core_tests.CheckpointRuntimeTests(methodName="test_technical_errors_stay_error")
    harness.setUp()
    try:
        app = harness.app
        app.run_config = {"modes": {mode: True for mode in REMOVED_MODES},
                          "options": {option: True for option in REMOVED_OPTIONS}}
        resources = harness.resources("https://www.facebook.com/")
        app.authenticate_facebook_account = mock.AsyncMock(return_value=(module.LOGIN_SUCCESS, "verified"))
        asyncio.run(harness.run_worker(1, resources))
        assert app.account_states.get(1)["status"] == "LIVE"
        app.run_create_page.assert_not_awaited()
        app.run_add_by_uid.assert_not_awaited()
        app.run_add_page_admin.assert_not_awaited()
        for resource in resources:
            resource.close.assert_awaited_once()
        source = inspect.getsource(module.MainToolApp.process_account)
        for name in REMOVED_MODES + REMOVED_OPTIONS:
            assert f'get("{name}"' not in source
    finally:
        harness.doCleanups()
