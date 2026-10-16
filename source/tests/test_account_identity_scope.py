"""Part 1: stable selection, unique UID scheduling and isolated manual UID checks."""
import asyncio
import copy
import contextvars
import threading
from unittest import mock

import pytest

import client_app as module
from account_history import AccountHistoryStore
from test_account_normalization import TextBuffer, make_import_app
from test_run_snapshot_lifecycle import make_start_app, start_without_real_worker


def cookie(uid, value="synthetic-only"):
    return f"c_user={uid}; xs={value};"


def row(uid, index=1, value="synthetic-only"):
    record = module.import_account_record(cookie(uid, value))
    return {**record.to_account_dict(), "stt": index, "account_id": uid}


def check_rows(app, indexes):
    for item in app.tree.get_children():
        values = list(app.tree.item(item, "values"))
        values[0] = "[✔]" if int(item) in indexes else "[ ]"
        app.tree.item(item, values=values)


def checked_uids(app):
    return {str(app.tree.item(item, "values")[2]) for item in app.tree.get_children()
            if app.tree.item(item, "values")[0] == "[✔]"}


@pytest.mark.parametrize("selected", [set(), {1}, {2}, {1, 2}])
@pytest.mark.parametrize("refresh", ["focus", "proxy"])
def test_normal_refresh_never_changes_checked_account_identities(selected, refresh):
    app = make_start_app()
    check_rows(app, selected)
    expected = checked_uids(app)
    if refresh == "focus":
        app.auto_format_cookie_numbers()
    else:
        app.proxy_mode.get.return_value = "random"
        app.reload_table_from_text()
    assert checked_uids(app) == expected


def test_selection_follows_uid_through_reorder_and_start_snapshot():
    app = make_start_app()
    check_rows(app, {1})
    app.txt_accounts.text = cookie("22222") + "\n" + cookie("11111")
    config = start_without_real_worker(app)
    assert checked_uids(app) == {"11111"}
    assert config["checked_indexes"] == frozenset({2})
    assert app.run_account_indexes == {2}
    assert config["parsed_accounts"][2]["uid"] == "11111"


def test_replacing_selected_uid_does_not_select_a_different_account_at_same_stt():
    app = make_start_app()
    check_rows(app, {1})
    app.txt_accounts.text = cookie("33333") + "\n" + cookie("22222")
    with mock.patch.object(module.threading, "Thread") as worker:
        app.start_thread()
    worker.assert_not_called()
    assert checked_uids(app) == set()
    assert "Chưa chọn" in app.run_error


def test_new_uid_is_unchecked_until_explicitly_selected():
    app = make_start_app()
    check_rows(app, {1})
    app.txt_accounts.text += "\n" + cookie("33333")
    app.reload_table_from_text()
    assert checked_uids(app) == {"11111"}
    app.reload_table_from_text(checked_indexes={3})
    assert checked_uids(app) == {"33333"}


def test_first_import_remains_checked_and_manual_stt_override_still_works():
    app = make_import_app(cookie("11111") + "\n" + cookie("22222"))
    app.reload_table_from_text()
    assert checked_uids(app) == {"11111", "22222"}
    app = make_start_app()
    check_rows(app, set())
    app.txt_accounts.text = cookie("33333")
    app.ent_selected_indexes.get.return_value = "1"
    start_without_real_worker(app)
    assert app.run_account_indexes == {1}
    assert app.run_config["parsed_accounts"][1]["uid"] == "33333"


def test_delete_does_not_select_remaining_previously_unchecked_uid():
    app = make_start_app()
    check_rows(app, {1})
    app.tree.selection = lambda: ("1",)
    app.delete_selected_rows()
    assert app.account_states.get(1)["uid"] == "22222"
    assert checked_uids(app) == set()


@pytest.mark.parametrize("second", [row("11111", 2), row("11111", 2, "new-cookie")])
def test_sync_rejects_duplicate_uid_before_changing_state_or_history(tmp_path, second):
    history = AccountHistoryStore(tmp_path / "history.db")
    states = module.AccountStateStore(history)
    states.sync([row("11111"), row("22222", 2)])
    states.append_log(1, "[!] account A history")
    before = {index: states.get(index) for index in states.indexes()}
    with mock.patch.object(history, "save", wraps=history.save) as persist:
        with pytest.raises(ValueError, match="[Tt]rùng UID") as error:
            states.sync([row("11111"), second])
    persist.assert_not_called()
    assert {index: states.get(index) for index in states.indexes()} == before
    assert "xs=" not in str(error.value)
    assert "synthetic-only" not in str(error.value)


def test_sync_rejects_duplicate_stt_before_mutating_any_state():
    states = module.AccountStateStore()
    states.sync([row("11111"), row("22222", 2)])
    before = {index: states.get(index) for index in states.indexes()}
    with pytest.raises(ValueError, match="STT"):
        states.sync([row("11111"), row("22222", 1)])
    assert {index: states.get(index) for index in states.indexes()} == before


def test_duplicate_input_blocks_start_and_preserves_last_valid_table():
    app = make_start_app()
    before = copy.deepcopy(app.tree.rows)
    raw = cookie("11111", "first-secret") + "\n" + cookie("11111", "second-secret")
    app.txt_accounts.text = raw
    with mock.patch.object(module.threading, "Thread") as worker:
        app.start_thread()
    worker.assert_not_called()
    assert not app.is_running
    assert "trùng UID" in app.run_error
    assert app.tree.rows == before
    assert app.txt_accounts.text.strip() == raw
    assert "first-secret" not in app.run_error and "second-secret" not in app.run_error


def test_popup_rejects_duplicate_add_without_mutating_existing_input():
    app = make_import_app(cookie("11111"))
    app.reload_table_from_text()
    before = app.txt_accounts.text
    dialog = mock.Mock()
    dialog.txt_input = TextBuffer(cookie("11111", "replacement-cookie"))
    dialog.on_import_callback = app.add_accounts_to_table
    with mock.patch.object(module.messagebox, "showwarning") as warning, \
         mock.patch.object(module.messagebox, "showinfo") as success:
        module.ImportAccountDialog.process_import(dialog)
    assert app.txt_accounts.text == before
    assert app.account_states.get(1)["cookie"] == cookie("11111")
    success.assert_not_called()
    dialog.destroy.assert_not_called()
    warning.assert_called_once()


def test_worker_snapshot_rejects_duplicate_uid_before_opening_playwright():
    app = make_start_app()
    values = dict(app.capture_run_config())
    values["accounts"] = cookie("11111") + "\n" + cookie("11111", "other")
    values["parsed_accounts"] = {1: row("11111"), 2: row("11111", 2, "other")}
    app.run_config = module.RunConfig(values)
    app.is_running = True
    app.process_account_scoped = mock.AsyncMock()
    with mock.patch.object(module, "async_playwright") as browser:
        asyncio.run(app.main_worker())
    browser.assert_not_called()
    app.process_account_scoped.assert_not_awaited()
    assert app.run_status == "FAILED"


def checker_app():
    app = make_start_app()
    app.tree.selection = lambda: ("1",)
    app.close_requested = False
    app.account_log_context = contextvars.ContextVar("identity_check", default=None)
    app.request_ui_refresh = mock.Mock()
    app.update_tree_row = mock.Mock()
    app.selected_log_account = None
    app.refresh_account_state_row = mock.Mock()
    app.render_log_view = mock.Mock()
    app.queued_ui = []
    app.post_ui = app.queued_ui.append
    return app


def begin_check(app):
    with mock.patch.object(module.threading, "Thread") as thread:
        app.check_live_selected()
    assert thread.called
    return thread.call_args.kwargs["target"]


def complete_network(worker, error=None):
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.geturl.return_value = "https://example.invalid/fixture-picture"
    with mock.patch.object(module.urllib.request, "urlopen", return_value=response, side_effect=error) as request:
        worker()
    return request


def drain_ui(app):
    callbacks, app.queued_ui = app.queued_ui, []
    with mock.patch.object(module.messagebox, "showinfo"):
        for callback in callbacks:
            callback()


@pytest.mark.parametrize("active", ["running", "cleanup"])
def test_uid_check_is_blocked_during_run_or_worker_cleanup(active):
    app = checker_app()
    app.account_states.update(1, status="LIVE")
    app.account_states.record_task(1, "CREATE_PAGE", "RUNNING", "submitted")
    before = app.account_states.get(1)
    if active == "running":
        app.is_running = True
    else:
        app.run_thread = mock.Mock()
        app.run_thread.is_alive.return_value = True
    with mock.patch.object(module.threading, "Thread") as thread, \
         mock.patch.object(module.messagebox, "showwarning"):
        app.check_live_selected()
    thread.assert_not_called()
    assert app.account_states.get(1) == before


def test_idle_uid_check_preserves_tasks_counters_and_checkpoint_latch():
    app = checker_app()
    app.account_states.record_task(1, "FRIEND_REQUEST", "SUCCESS", "verified", {"target": "33333"})
    app.account_states.record_task(1, "CREATE_PAGE", "FAILED", "policy rejected")
    before = app.account_states.get(1)
    worker = begin_check(app)
    assert app.account_states.get(1)["tasks"] == before["tasks"]
    complete_network(worker)
    drain_ui(app)
    state = app.account_states.get(1)
    assert state["tasks"] == before["tasks"]
    assert state["friend_success_count"] == 1 and state["page_failed_count"] == 1
    app.account_states.update(1, status="CHECKPOINT", current_action="verification needed")
    complete_network(begin_check(app))
    drain_ui(app)
    assert app.account_states.get(1)["status"] == "CHECKPOINT"
    assert app.account_states.get(1)["checkpoint_stopped"]


@pytest.mark.parametrize("error,status", [(None, "UNKNOWN"), (TimeoutError("network timeout"), "ERROR")])
def test_uid_result_follows_identity_after_reorder_and_does_not_touch_other_uid(error, status):
    app = checker_app()
    worker = begin_check(app)
    app.txt_accounts.text = cookie("22222") + "\n" + cookie("11111")
    app.reload_table_from_text()
    complete_network(worker, error)
    drain_ui(app)
    a, b = app.account_states.get(2), app.account_states.get(1)
    assert a["uid"] == "11111" and a["status"] == status
    assert "UID" in a["current_action"]
    assert b["uid"] == "22222" and b["current_action"] == "Chưa chạy"
    assert b["status"] == "UNKNOWN"
    if app.log.call_args:
        assert app.log.call_args.kwargs.get("account_index") == 2


def test_removed_uid_drops_late_result_instead_of_updating_its_old_stt():
    app = checker_app()
    worker = begin_check(app)
    app.txt_accounts.text = cookie("22222")
    app.reload_table_from_text()
    complete_network(worker, TimeoutError("old request"))
    drain_ui(app)
    assert app.account_states.get(1)["uid"] == "22222"
    assert app.account_states.get(1)["status"] == "UNKNOWN"
    assert app.account_states.get(1)["current_action"] == "Chưa chạy"


def test_run_started_after_uid_check_drops_old_queued_results():
    app = checker_app()
    worker = begin_check(app)
    start_without_real_worker(app)
    app.account_states.update(1, status="LIVE")
    app.account_states.record_task(1, "CREATE_PAGE", "RUNNING", "new run")
    before = app.account_states.get(1)
    complete_network(worker, TimeoutError("old check"))
    drain_ui(app)
    assert app.account_states.get(1) == before


def test_new_uid_check_supersedes_old_results():
    app = checker_app()
    previous = begin_check(app)
    current = begin_check(app)
    complete_network(previous, TimeoutError("obsolete check"))
    drain_ui(app)
    assert app.account_states.get(1)["status"] != "ERROR"
    complete_network(current)
    drain_ui(app)
    assert app.account_states.get(1)["status"] == "UNKNOWN"


def test_checker_worker_never_reads_tk_or_writes_account_state_directly():
    app = checker_app()
    worker = begin_check(app)
    original_action = app.account_states.get(1)["current_action"]
    main_thread = threading.get_ident()
    get = app.account_states.get
    def ui_get(*args, **kwargs):
        assert threading.get_ident() == main_thread
        return get(*args, **kwargs)
    errors = []
    def run():
        try:
            complete_network(worker)
        except BaseException as error:
            errors.append(error)
    with mock.patch.object(app.account_states, "get", side_effect=ui_get), \
         mock.patch.object(app.tree, "get_children", side_effect=AssertionError("worker accessed Tk")), \
         mock.patch.object(app.account_states, "update", side_effect=AssertionError("worker wrote state")):
        thread = threading.Thread(target=run)
        thread.start()
        thread.join(3)
    assert not thread.is_alive() and not errors
    assert app.account_states.get(1)["current_action"] == original_action
    drain_ui(app)
    assert "UID có phản hồi" in app.account_states.get(1)["current_action"]


def test_close_cancels_manual_uid_requests_and_queued_results():
    app = checker_app()
    complete_network(begin_check(app))
    before = app.account_states.get(1)
    app.on_close()
    drain_ui(app)
    assert app.close_requested
    assert app._uid_check_cancel.is_set()
    assert app.account_states.get(1) == before
