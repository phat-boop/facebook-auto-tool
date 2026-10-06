"""Phase 5: credential-safe table, exact clipboard data and isolated manual sessions."""
import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

import client_app as module
from test_account_normalization import make_import_app


def raw_account(uid, suffix):
    return f"{uid}|password-{suffix}|twofa-{suffix}|c_user={uid}; xs=session-{suffix}==;|token-{suffix}"


def management_app():
    app = make_import_app(raw_account("11111", "A") + "\n" + raw_account("22222", "B"))
    app.root = mock.Mock()
    app.reload_table_from_text()
    app.tree.selection = mock.Mock(return_value=("1", "2"))
    app.tree.selection_set = mock.Mock()
    app.tree.identify_row = mock.Mock(return_value="1")
    app.tree_menu = mock.Mock()
    return app


def test_management_schema_badges_masks_and_action_redaction():
    app = management_app()
    state = app.account_states.get(1)
    state.update(login_mode="COOKIE", status="LIVE", page_success_count=3,
                 page_failed_count=1, friend_success_count=7, friend_failed_count=2,
                 last_update="2026-10-03T10:20:30+00:00")
    state["current_action"] = " | ".join(state[key] for key in ("password", "2fa", "cookie", "token"))
    values = module.management_account_values(state)
    assert len(values) == len(module.ACCOUNT_MANAGEMENT_COLUMNS) == 13
    assert values[:9] == ("[✔]", 1, "11111", "********", "********", "YES", "YES", "COOKIE", "LIVE")
    assert values[10:12] == ("3 / 1", "7 / 2")
    assert values[12] != "-"
    for key in ("password", "2fa", "cookie", "token"):
        assert state[key] not in str(values)
    assert "session-A" not in str(values)
    state.update(cookie="", token="", password="", **{"2fa": ""})
    assert module.management_account_values(state, False)[:7] == ("[ ]", 1, "11111", "", "", "NO", "NO")


@pytest.mark.parametrize("mode,expected", [
    ("uid", "11111"), ("password", "password-A"), ("2fa", "twofa-A"),
    ("cookie", "c_user=11111; xs=session-A==;"), ("token", "token-A"),
    ("uid|pass", "11111|password-A"), ("uid|pass|2fa", "11111|password-A|twofa-A"),
    ("canonical", raw_account("11111", "A")), ("raw", raw_account("11111", "A")),
])
def test_right_click_copy_is_pinned_to_clicked_account(mode, expected):
    app = management_app()
    app.show_account_context_menu(SimpleNamespace(y=12, x_root=30, y_root=40))
    app.tree.selection_set.assert_called_once_with("1")
    app.tree_menu.tk_popup.assert_called_once_with(30, 40)
    app.tree_menu.grab_release.assert_called_once()
    app.tree.selection.return_value = ("2",)
    app.account_states.sync([dict(app.account_states.get(2), stt=1),
                             dict(app.account_states.get(1), stt=2)])
    app.copy_tree_data(mode, app._management_menu_account)
    app.root.clipboard_append.assert_called_once_with(expected)
    assert "password-A" not in str(app.log.call_args)


def test_copy_raw_preserves_original_import_while_canonical_is_normalized():
    raw = "FACEBOOK|11111|password-A|twofa-A|c_user=11111; xs=session-A==;|token-A"
    app = make_import_app(raw)
    app.root = mock.Mock()
    app.reload_table_from_text()
    state = app.management_account_for_item("1")
    app.copy_tree_data("raw", state)
    app.root.clipboard_append.assert_called_with(raw)
    app.copy_tree_data("canonical", state)
    app.root.clipboard_append.assert_called_with(raw_account("11111", "A"))


def test_stale_uid_row_cannot_copy_another_account_or_open_menu():
    app = management_app()
    values = list(app.tree.item("1", "values"))
    values[2] = "22222"
    app.tree.item("1", values=values)
    assert app.management_account_for_item("1") is None
    app.show_account_context_menu(SimpleNamespace(y=12, x_root=30, y_root=40))
    app.tree_menu.tk_popup.assert_not_called()
    app.tree.selection.return_value = ("1",)
    app.copy_tree_data("password")
    app.root.clipboard_append.assert_not_called()


def test_queued_row_update_preserves_checkbox_and_never_rewrites_badges():
    app = management_app()
    app.account_states.update(1, status="LIVE", current_action="creating")
    app.account_states.record_task(1, "CREATE_PAGE", "SUCCESS", "created", {"page_id": "99999"})
    before = app.tree.item("1", "values")
    app.update_tree_row("1", current_friends=40, sent_today=20, status="cookie secret")
    assert app.tree.item("1", "values") == before
    app.post_ui.call_args.args[0]()
    after = app.tree.item("1", "values")
    assert after[0] == "[✔]"
    assert after[5:9] == ("YES", "YES", "-", "LIVE")
    assert after[10] == "1 / 0"
    assert "cookie secret" not in str(after)
    assert app.tree.item("2", "values")[8] == "UNKNOWN"


@pytest.mark.parametrize("status", ["LIVE", "CHECKPOINT", "ERROR", "DIE"])
def test_running_tag_does_not_hide_checkpoint_error_or_die(status):
    app = management_app()
    app.account_states.record_task(1, "CREATE_PAGE", "RUNNING", "creating")
    app.account_states.update(1, status=status)
    app.refresh_management_account_row(1)
    assert app.tree.item("1", "tags") == ("RUNNING" if status == "LIVE" else status,)


def test_dark_palette_has_readable_contrast_and_distinct_statuses():
    def luminance(hex_color):
        rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    palettes = list(module.ACCOUNT_STATUS_PALETTE.values())
    table = module.ACCOUNT_TABLE_PALETTE
    palettes += [{"background": table[prefix + "background"], "foreground": table[prefix + "foreground"]}
                 for prefix in ("", "header_", "selected_")]
    for colors in palettes:
        bg, fg = luminance(colors["background"]), luminance(colors["foreground"])
        assert bg < .2
        assert (max(bg, fg) + .05) / (min(bg, fg) + .05) >= 4.5
    assert module.ACCOUNT_STATUS_PALETTE["CHECKING"] == table["RUNNING"]
    assert len({palette["background"] for palette in module.ACCOUNT_STATUS_PALETTE.values()}) == 6


def inspector_resources():
    page = mock.Mock(close=mock.AsyncMock(), goto=mock.AsyncMock())
    context = mock.Mock(close=mock.AsyncMock(), add_cookies=mock.AsyncMock(),
                        new_page=mock.AsyncMock(return_value=page), pages=[page])
    browser = mock.Mock(close=mock.AsyncMock(), new_context=mock.AsyncMock(return_value=context))
    browser.is_connected.return_value = False
    factory = mock.MagicMock()
    factory.__aenter__.return_value.chromium.launch = mock.AsyncMock(return_value=browser)
    return factory, browser, context, page


def test_manual_inspector_stays_open_until_user_closes_last_page():
    app = management_app()
    factory, browser, context, page = inspector_resources()
    browser.is_connected.return_value = True
    async def user_closes_window(_delay):
        for resource in (page, context, browser):
            resource.close.assert_not_awaited()
        context.pages = []
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None), \
         mock.patch.object(module.asyncio, "sleep", side_effect=user_closes_window) as sleep:
        asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    sleep.assert_awaited_once_with(.5)
    for resource in (page, context, browser):
        resource.close.assert_awaited_once()


def test_table_header_background_and_selection_use_local_style_only():
    root = module.tk.Tk()
    root.withdraw()
    try:
        style = module.ttk.Style(root)
        original_theme = style.theme_use()
        tree = module.ttk.Treeview(root, columns=module.ACCOUNT_MANAGEMENT_COLUMNS, show="headings")
        module.configure_account_table_style(style, tree)
        assert style.theme_use() == original_theme
        assert tuple(tree.cget("columns")) == module.ACCOUNT_MANAGEMENT_COLUMNS
        palette = module.ACCOUNT_TABLE_PALETTE
        assert style.lookup("Account.Treeview.Heading", "background") == palette["header_background"]
        assert style.lookup("Account.Treeview.Heading", "foreground") == palette["header_foreground"]
        assert style.lookup("Account.Treeview", "fieldbackground") == palette["background"]
        assert style.lookup("Account.Treeview", "rowheight") == 34
        assert style.lookup("Account.Treeview", "background", ("selected",)) == palette["selected_background"]
        assert style.lookup("Account.Treeview", "foreground", ("selected",)) == palette["selected_foreground"]
        assert "Account.Treeview.field" in str(style.layout("Account.Treeview"))
        assert "Account.Treeheading.border" in str(style.layout("Account.Treeview.Heading"))
    finally:
        root.destroy()


def test_inspectors_have_separate_cookie_proxy_locale_and_cleanup():
    app = management_app()
    a, b = app.account_states.get(1), app.account_states.get(2)
    a.update(effective_proxy="127.0.0.1:60001", locale="vi-VN")
    b.update(effective_proxy="127.0.0.1:60002", locale="ja-JP")
    ar, br = inspector_resources(), inspector_resources()
    worker = mock.Mock()
    app.create_browser_page = mock.AsyncMock(side_effect=AssertionError("worker factory reused"))
    async def run():
        await asyncio.gather(app.inspect_account_session(module.RunConfig(a)),
                             app.inspect_account_session(module.RunConfig(b)))
    with mock.patch.object(module, "async_playwright", side_effect=[ar[0], br[0]]) as drivers, \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        asyncio.run(run())
    assert drivers.call_count == 2
    for resources, account, port, locale in ((ar, a, 60001, "vi-VN"), (br, b, 60002, "ja-JP")):
        factory, browser, context, page = resources
        assert factory.__aenter__.return_value.chromium.launch.call_args.kwargs["proxy"]["server"].endswith(str(port))
        browser.new_context.assert_awaited_once_with(locale=locale)
        context.add_cookies.assert_awaited_once_with(module.parse_cookies(account["cookie"]))
        page.goto.assert_awaited_once_with("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
        for resource in (page, context, browser):
            resource.close.assert_awaited_once()
    app.create_browser_page.assert_not_awaited()
    worker.close.assert_not_called()
    assert app.account_states.get(1)["status"] == app.account_states.get(2)["status"] == "UNKNOWN"


@pytest.mark.parametrize("failure", ["init", "navigation", "cancel"])
def test_inspector_failures_and_cancel_cleanup(failure):
    app = management_app()
    factory, browser, context, page = inspector_resources()
    if failure == "init":
        browser.new_context.side_effect = RuntimeError("context init failed")
    else:
        page.goto.side_effect = asyncio.CancelledError() if failure == "cancel" else RuntimeError("network error")
    with mock.patch.object(module, "async_playwright", return_value=factory), \
         mock.patch.object(module, "get_installed_browser_path", return_value=None):
        with pytest.raises(asyncio.CancelledError if failure == "cancel" else RuntimeError):
            asyncio.run(app.inspect_account_session(app.account_states.get(1)))
    browser.close.assert_awaited_once()
    if failure != "init":
        page.close.assert_awaited_once()
        context.close.assert_awaited_once()


def test_invalid_inspector_proxy_never_falls_back_to_direct_ip():
    app = management_app()
    state = app.account_states.get(1)
    state["effective_proxy"] = "invalid proxy"
    with mock.patch.object(module, "async_playwright") as driver:
        with pytest.raises(ValueError):
            asyncio.run(app.inspect_account_session(state))
    driver.assert_not_called()


def test_inspector_worker_captures_snapshot_and_posts_error_to_ui_thread():
    app = management_app()
    state = app.account_states.get(1)
    app.inspect_account_session = mock.AsyncMock(side_effect=RuntimeError("password-A session-A=="))
    with mock.patch.object(module.threading, "Thread") as thread, \
         mock.patch.object(module.messagebox, "showerror") as message:
        app.open_account_inspector(state)
        state["cookie"] = "cookie-of-B"
        thread.call_args.kwargs["target"]()
        inspected = app.inspect_account_session.call_args.args[0]
        assert inspected["cookie"] == "c_user=11111; xs=session-A==;"
        assert inspected["uid"] == "11111"
        message.assert_not_called()
        app.post_ui.call_args.args[0]()
        assert "password-A" not in str(message.call_args)
        assert "session-A" not in str(message.call_args)


@pytest.mark.parametrize("history", [False, True])
def test_log_view_uses_stable_account_identity_after_reorder(history, tmp_path):
    app = management_app()
    app.account_states.history = module.AccountHistoryStore(tmp_path / "history.db")
    app.account_states.append_log(1, "A private password-A")
    app.account_states.append_log(2, "B-only-log")
    selected = app.account_states.get(1)
    app.account_states.sync([dict(app.account_states.get(2), stt=1),
                             dict(app.account_states.get(1), stt=2)])
    with mock.patch.object(module.tk, "Toplevel") as window, \
         mock.patch.object(module.scrolledtext, "ScrolledText") as textbox:
        app.show_management_account_logs(selected, history=history)
    text = textbox.return_value.insert.call_args.args[1]
    assert "A private" in text
    assert "B-only-log" not in text and "password-A" not in text
    window.return_value.title.assert_called_once_with(("Lịch sử" if history else "Nhật ký") + " - 11111")
    textbox.return_value.configure.assert_called_once_with(state="disabled")
