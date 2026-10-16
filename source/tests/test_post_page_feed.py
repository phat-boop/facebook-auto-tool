"""Configured post-Page Feed duration, countdown, and removal of Telegram inputs."""
import ast
import asyncio
import inspect
import json
from unittest import mock

from cryptography.fernet import Fernet
import pytest

import client_app as module
from facebook import page_creator
import test_core as core_tests
from test_core_feature_ui import build_preview
from test_run_snapshot_lifecycle import make_start_app


def test_post_page_feed_controls_default_to_800_900_without_telegram_row():
    root = module.tk.Tk()
    root.withdraw()
    try:
        app = build_preview(root)
        def labels(widget):
            values = [widget.cget("text")] if isinstance(widget, module.tk.Label) else []
            return values + [text for child in widget.winfo_children() for text in labels(child)]
        texts = labels(root)
        assert "Lướt Feed sau khi tạo Page:" in texts
        assert "Telegram Token:" not in texts and "Chat ID:" not in texts
        assert app.ent_min_page_delay.get() == "800"
        assert app.ent_max_page_delay.get() == "900"
        assert isinstance(app.ent_tele_token, module.tk.StringVar)
        assert isinstance(app.ent_tele_chatid, module.tk.StringVar)
    finally:
        root.destroy()


def test_post_page_feed_range_is_captured_once_and_sorted():
    app = make_start_app()
    app.ent_min_page_delay.get.return_value = "900"
    app.ent_max_page_delay.get.return_value = "800"
    snapshot = app.capture_run_config()
    app.ent_min_page_delay.get.side_effect = AssertionError("worker read UI")
    app.ent_max_page_delay.get.side_effect = AssertionError("worker read UI")
    assert (snapshot["min_page_delay"], snapshot["max_page_delay"]) == (800, 900)


def test_post_page_feed_range_survives_settings_restart(tmp_path):
    path = tmp_path / "settings.json"
    app = make_start_app()
    app.current_theme = next(iter(module.THEMES))
    app.ent_min_page_delay.get.return_value = "800"
    app.ent_max_page_delay.get.return_value = "900"
    recovered = make_start_app()
    recovered.cbo_theme, recovered.apply_theme = mock.Mock(), mock.Mock()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)), \
         mock.patch.object(module, "settings_cipher", return_value=Fernet(Fernet.generate_key())):
        module.MainToolApp.save_settings(app)
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["min_page_delay"] == "800" and saved["max_page_delay"] == "900"
        module.MainToolApp.load_settings(recovered)
    recovered.ent_min_page_delay.insert.assert_called_once_with(0, "800")
    recovered.ent_max_page_delay.insert.assert_called_once_with(0, "900")


def test_countdown_shows_exact_seconds_remaining():
    state = {"page_wait_remaining": 899, "next_page_at": "2026-10-15T10:20:30"}
    assert module.page_wait_label(state) == "899s → 10:20:30"
    assert module.page_wait_label({"page_wait_remaining": None}) == "-"


def test_feed_countdown_begins_only_after_profile_switch_and_navigation():
    fixture = core_tests.PageWaitTests()
    fixture.setUp()
    app, page = fixture.app, fixture.page
    events = []
    async def personal(*_args):
        assert app.account_states.get(1)["page_wait_remaining"] is None
        events.append("profile")
        return True
    async def navigate(*_args, **_kwargs):
        assert app.account_states.get(1)["page_wait_remaining"] is None
        events.append("feed")
    async def stop_after_first_scroll(*_args):
        assert app.account_states.get(1)["page_wait_remaining"] == 800
        assert app.account_states.get(2)["page_wait_remaining"] is None
        events.append("scroll")
        app.stop_requested, app.is_running = True, False
    app.ensure_personal_profile.side_effect = personal
    page.goto.side_effect = navigate
    app._smooth_human_scroll = mock.AsyncMock(side_effect=stop_after_first_scroll)
    with mock.patch.object(module.random, "randint", return_value=800), \
         mock.patch.object(module.random, "uniform", return_value=0):
        assert not asyncio.run(app.wait_between_page_jobs(page, object(), "A", 1, 800, 900))
    assert events == ["profile", "feed", "scroll"]
    assert app.account_states.get(1)["page_wait_remaining"] is None


@pytest.mark.parametrize("created,target,expected_waits", [(1, 5, 1), (2, 5, 1), (3, 5, 1), (5, 5, 0)])
def test_every_verified_page_wait_uses_the_exact_configured_range(created, target, expected_waits):
    production = ast.parse(inspect.getsource(page_creator.run_create_page))
    branch = next(node for node in ast.walk(production) if isinstance(node, ast.If)
                  and ast.unparse(node.test) == "created_count < effective_max_pages")
    harness = ast.parse("async def invoke(self, page, context, acc_name, idx, created_count, effective_max_pages, min_page_del, max_page_del):\n    for _ in range(1):\n        pass\n")
    harness.body[0].body[0].body = [branch]
    namespace = {}
    exec(compile(ast.fix_missing_locations(harness), "<production post-Page branch>", "exec"), namespace)
    app = mock.Mock(wait_between_page_jobs=mock.AsyncMock(return_value=True))
    asyncio.run(namespace["invoke"](app, "page", "context", "A", 1, created, target, 800, 900))
    assert app.wait_between_page_jobs.await_count == expected_waits
    if expected_waits:
        app.wait_between_page_jobs.assert_awaited_once_with("page", "context", "A", 1, 800, 900)
