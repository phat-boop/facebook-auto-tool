"""Phase 7: process ownership, module-local pause and commit-before-publication."""
import asyncio
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import pytest

import client_app as module
from account_history import AccountHistoryStore
from long_run import DuplicatePageResult, ModuleCircuitBreaker, SingleInstanceLock


def make_app(tmp_path):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.account_states = module.AccountStateStore(AccountHistoryStore(tmp_path / "history.db"))
    app.account_states.sync([
        {**module.import_account_record(f"{uid}|PASSWORD_SECRET||c_user={uid}; xs=SECRET;|").to_account_dict(),
         "stt": index, "account_id": uid}
        for index, uid in enumerate(("11111", "22222", "33333", "44444"), 1)
    ])
    for index in app.account_states.indexes():
        app.account_states.update(index, status="LIVE")
    app.post_ui = mock.Mock()
    app.log = mock.Mock()
    app.is_running = True
    app.stop_requested = False
    app.module_breaker = ModuleCircuitBreaker()
    return app


def result(index=1, job="job-A", page_id="99999", status="SUCCESS", structural=""):
    owner = ("11111", "22222", "33333", "44444")[index - 1]
    value = module.build_create_page_result(
        status, owner, "Page A", "Spa", account_index=index,
        page_id=page_id if status == "SUCCESS" else "",
        page_url=f"https://www.facebook.com/profile.php?id={page_id}" if status == "SUCCESS" else "",
        reason="layout missing" if structural else "", structural_failure=structural,
    )
    value.update(owner_account_id=owner, page_job_id=job)
    return value


@pytest.fixture
def exports():
    with mock.patch.object(module, "save_created_page_success", return_value=True) as success, \
            mock.patch.object(module, "save_create_page_outcome") as outcome, \
            mock.patch.object(module, "append_create_page_account_log") as log:
        yield success, outcome, log


def test_single_instance_rejects_second_owner_and_releases(tmp_path):
    first, second = (SingleInstanceLock(tmp_path / "production.lock") for _ in range(2))
    try:
        assert first.acquire()
        assert first.acquire()
        assert not second.acquire()
        first.release()
        assert second.acquire()
    finally:
        first.release()
        second.release()


def test_process_exit_releases_lock_even_without_cleanup(tmp_path):
    path = tmp_path / "production.lock"
    child = subprocess.Popen(
        [sys.executable, "-B", "-c",
         "import sys; from long_run import SingleInstanceLock; "
         "lock=SingleInstanceLock(sys.argv[1]); print(lock.acquire(), flush=True); sys.stdin.read()", str(path)],
        cwd=Path(module.__file__).parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    second = SingleInstanceLock(path)
    try:
        assert child.stdout.readline().strip() == "True"
        assert not second.acquire()
        child.terminate()
        child.wait(timeout=10)
        assert second.acquire()
    finally:
        second.release()
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)


def test_source_start_does_not_take_production_lock():
    with mock.patch.object(module.sys, "frozen", False, create=True), \
            mock.patch.object(module, "run_application", return_value=0) as launch, \
            mock.patch.object(module, "SingleInstanceLock") as lock:
        assert module.main() == 0
        launch.assert_called_once_with()
        lock.assert_not_called()


def test_second_production_instance_shows_message_and_exits():
    with mock.patch.object(module.sys, "frozen", True, create=True), \
            mock.patch.object(module, "SingleInstanceLock") as lock, \
            mock.patch.object(module.tk, "Tk") as root, \
            mock.patch.object(module.messagebox, "showinfo") as notice, \
            mock.patch.object(module, "run_application") as launch:
        lock.return_value.acquire.return_value = False
        assert module.main() == 0
        launch.assert_not_called()
        notice.assert_called_once_with("Ứng dụng đang chạy", "Ứng dụng đang chạy", parent=root.return_value)
        root.return_value.destroy.assert_called_once_with()
        lock.return_value.release.assert_called_once_with()


@pytest.mark.parametrize("exception", [RuntimeError("startup error"), SystemExit(0)])
def test_production_lock_released_on_startup_exit(exception):
    with mock.patch.object(module.sys, "frozen", True, create=True), \
            mock.patch.object(module, "SingleInstanceLock") as lock, \
            mock.patch.object(module, "run_application", side_effect=exception):
        lock.return_value.acquire.return_value = True
        with pytest.raises(type(exception)):
            module.main()
        lock.return_value.release.assert_called_once_with()


def test_lock_failure_is_fail_closed(tmp_path):
    lock = SingleInstanceLock(tmp_path / "missing" / "production.lock")
    with pytest.raises(OSError):
        lock.acquire()
    assert lock.handle is None


def test_three_distinct_accounts_trip_only_affected_module():
    breaker = ModuleCircuitBreaker()
    failure = {"status": "ERROR", "structural_failure": "CREATE_SUBMIT_MISSING"}
    for _ in range(4):
        assert not breaker.observe("CREATE_PAGE", "A", failure)
    assert not breaker.observe("CREATE_PAGE", "B", failure)
    assert breaker.observe("CREATE_PAGE", "C", failure)
    assert "MODULE_PAUSED / structural failure" in breaker.paused_reason("CREATE_PAGE")
    assert not breaker.paused_reason("FRIEND_REQUEST")
    assert not breaker.observe("CREATE_PAGE", "D", failure)
    breaker.reset()
    assert not breaker.paused_reason("CREATE_PAGE")


@pytest.mark.parametrize("status", ["DIE", "CHECKPOINT", "ERROR"])
def test_account_failure_never_trips_structural_breaker(status):
    breaker = ModuleCircuitBreaker()
    for uid in range(10):
        assert not breaker.observe("CREATE_PAGE", uid,
                                   {"status": "ERROR", "structural_failure": "CATEGORY_INPUT_MISSING"}, status)
    assert not breaker.paused_reason("CREATE_PAGE")


@pytest.mark.parametrize("failure", [
    {"status": "FAILED", "reason": "policy rejected"},
    {"status": "ERROR", "technical_error": "proxy timeout"},
    {"status": "ERROR", "technical_error": "browser closed"},
    {"status": "ERROR", "structural_failure": "UNKNOWN_LAYOUT"},
])
def test_policy_network_and_unknown_errors_do_not_pause_module(failure):
    breaker = ModuleCircuitBreaker()
    for uid in range(10):
        assert not breaker.observe("CREATE_PAGE", uid, failure)
    assert not breaker.paused_reason("CREATE_PAGE")


def test_nonconsecutive_or_different_structural_failures_reset_streak():
    breaker = ModuleCircuitBreaker()
    missing = {"status": "ERROR", "structural_failure": "CREATE_SUBMIT_MISSING"}
    assert not breaker.observe("CREATE_PAGE", "A", missing)
    assert not breaker.observe("CREATE_PAGE", "B", missing)
    assert not breaker.observe("CREATE_PAGE", "success", {"status": "SUCCESS"})
    assert not breaker.observe("CREATE_PAGE", "C", missing)
    assert not breaker.observe("CREATE_PAGE", "D", {**missing, "structural_failure": "CATEGORY_INPUT_MISSING"})
    assert not breaker.observe("CREATE_PAGE", "E", missing)
    assert not breaker.paused_reason("CREATE_PAGE")


def test_concurrent_structural_failures_trip_once():
    breaker = ModuleCircuitBreaker()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda uid: breaker.observe("CREATE_PAGE", uid,
                       {"status": "ERROR", "structural_failure": "PAGE_NAME_INPUT_MISSING"}), range(20)))
    assert sum(results) == 1
    assert breaker.paused_reason("CREATE_PAGE")


def test_paused_create_page_skips_browser_but_not_friend_module(tmp_path, exports):
    app = make_app(tmp_path)
    for index in (1, 2, 3):
        assert app.publish_create_page_result(index, result(index, status="ERROR", structural="CATEGORY_INPUT_MISSING"))
    page, context = mock.Mock(), mock.Mock()
    assert asyncio.run(app.run_create_page(page, context, "44444", 4, ["Page|Spa"], 1, 1, 2)) == []
    assert not page.mock_calls
    assert app.account_states.get(4)["tasks"]["CREATE_PAGE"]["status"] == "SKIPPED"
    assert app.account_states.get(4)["status"] == "LIVE"
    assert not app.skip_paused_module(4, "FRIEND_REQUEST")
    assert "MODULE_PAUSED" in app.account_states.get(4)["current_action"]


@pytest.mark.parametrize("has_main", [True, False])
def test_real_create_flow_pauses_for_missing_layout_not_blank_page(tmp_path, exports, has_main):
    app = make_app(tmp_path)
    app.guard_facebook_checkpoint = mock.AsyncMock()
    app.take_error_snapshot = mock.AsyncMock()
    page = mock.Mock(url="https://www.facebook.com/pages/creation/", frames=[])
    page.goto = mock.AsyncMock()
    page.reload = mock.AsyncMock()
    page.title = mock.AsyncMock(return_value="Create a Page")
    missing = mock.Mock()
    missing.count = mock.AsyncMock(return_value=0)
    missing.first.wait_for = mock.AsyncMock(side_effect=TimeoutError("input missing"))
    main = mock.Mock()
    main.count = mock.AsyncMock(return_value=int(has_main))
    page.locator.side_effect = lambda selector: main if selector == 'div[role="main"]' else missing
    with mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        for index in (1, 2, 3, 4):
            asyncio.run(app.run_create_page(page, mock.Mock(), str(index), index, ["Page|Spa"], 1, 1, 2))
    assert page.goto.await_count == (3 if has_main else 4)
    assert bool(app.module_breaker.paused_reason("CREATE_PAGE")) == has_main
    assert app.account_states.get(4)["tasks"]["CREATE_PAGE"]["status"] == ("SKIPPED" if has_main else "ERROR")


def test_create_navigation_error_does_not_trip_breaker_or_mark_die(tmp_path, exports):
    app = make_app(tmp_path)
    app.guard_facebook_checkpoint = mock.AsyncMock()
    page = mock.Mock(url="https://www.facebook.com/pages/creation/")
    page.goto = mock.AsyncMock(side_effect=TimeoutError("proxy network timeout"))
    with mock.patch.object(module.asyncio, "sleep", new=mock.AsyncMock()):
        for index in (1, 2, 3, 4):
            asyncio.run(app.run_create_page(page, mock.Mock(), str(index), index, ["Page|Spa"], 1, 1, 2))
    assert not app.module_breaker.paused_reason("CREATE_PAGE")
    for index in (1, 2, 3, 4):
        state = app.account_states.get(index)
        assert state["status"] == "LIVE"
        assert state["tasks"]["CREATE_PAGE"]["status"] == "ERROR"


def test_success_is_durable_before_ui_or_export(tmp_path, exports):
    app = make_app(tmp_path)
    events = []
    history = app.account_states.history
    original_save = history.save

    def save(state, *args, **kwargs):
        if args[:2] == ("CREATE_PAGE", "TASK"):
            assert app.account_states.get(1)["page_success_count"] == 0
        original_save(state, *args, **kwargs)
        events.append("commit")

    def export(value):
        assert history.load(app.account_states.get(1))["page_success_count"] == 1
        assert app.account_states.get(1)["page_success_count"] == 1
        events.append("export")

    exports[0].side_effect = export
    with mock.patch.object(history, "save", side_effect=save):
        assert app.publish_create_page_result(1, result())
    assert events.index("commit") < events.index("export")
    assert app.account_states.get(2)["page_success_count"] == 0


def test_sqlite_failure_does_not_publish_success_or_increment_or_export(tmp_path, exports):
    app = make_app(tmp_path)
    before = app.account_states.get(1)
    with mock.patch.object(app.account_states.history, "save", side_effect=sqlite3.OperationalError("disk full")):
        with pytest.raises(sqlite3.OperationalError):
            app.publish_create_page_result(1, result())
    assert app.account_states.get(1) == before
    assert not app.post_ui.called
    assert not any(export.called for export in exports)


def test_checkpoint_race_does_not_publish_or_export(tmp_path, exports):
    app = make_app(tmp_path)
    app.account_states.update(1, status="CHECKPOINT")
    assert not app.publish_create_page_result(1, result())
    assert app.account_states.get(1)["page_success_count"] == 0
    assert not any(export.called for export in exports)


@pytest.mark.parametrize("field,value", [("owner_account_id", "22222"), ("page_job_id", "")])
def test_invalid_owner_job_binding_cannot_commit_success(tmp_path, exports, field, value):
    app = make_app(tmp_path)
    page = result()
    page[field] = value
    with pytest.raises(ValueError):
        app.publish_create_page_result(1, page)
    assert app.account_states.get(1)["page_success_count"] == 0
    assert not any(export.called for export in exports)


def test_identity_missing_cannot_commit_success(tmp_path, exports):
    app = make_app(tmp_path)
    page = {**result(), "page_id": "", "page_url": ""}
    with pytest.raises(ValueError):
        app.publish_create_page_result(1, page)
    assert app.account_states.get(1)["page_success_count"] == 0


def test_sqlite_duplicate_protection_survives_restart_without_csv(tmp_path, exports):
    app = make_app(tmp_path)
    app.publish_create_page_result(1, result())
    restarted = make_app(tmp_path)
    assert restarted.account_states.get(1)["page_success_count"] == 1
    for index, job in ((1, "job-new"), (2, "job-other-account")):
        with pytest.raises(DuplicatePageResult):
            restarted.publish_create_page_result(index, result(index, job))
    assert restarted.account_states.get(1)["page_success_count"] == 1
    assert restarted.account_states.get(2)["page_success_count"] == 0
    assert exports[0].call_count == 1


def test_id_or_url_alone_blocks_duplicate(tmp_path, exports):
    app = make_app(tmp_path)
    app.publish_create_page_result(1, result())
    for candidate in ({**result(2, "job-B"), "page_url": "https://www.facebook.com/another-page"},
                      {**result(2, "job-C"), "page_id": "88888"}):
        with pytest.raises(DuplicatePageResult):
            app.publish_create_page_result(2, candidate)
    assert app.account_states.get(2)["page_success_count"] == 0


def test_repeat_notification_is_idempotent_and_distinct_pages_count(tmp_path, exports):
    app = make_app(tmp_path)
    app.publish_create_page_result(1, result())
    app.publish_create_page_result(1, result())
    assert app.account_states.get(1)["page_success_count"] == 1
    app.publish_create_page_result(1, result(job="job-B", page_id="88888"))
    assert app.account_states.get(1)["page_success_count"] == 2


def test_concurrent_claim_of_same_page_commits_only_one_owner(tmp_path, exports):
    app = make_app(tmp_path)

    def publish(index):
        try:
            return app.publish_create_page_result(index, result(index, f"job-{index}"))
        except DuplicatePageResult:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        committed = list(pool.map(publish, (1, 2, 3, 4)))
    assert sum(committed) == 1
    assert sum(app.account_states.get(index)["page_success_count"] for index in (1, 2, 3, 4)) == 1
    assert exports[0].call_count == 1


def test_duplicate_claim_is_atomic_across_independent_sqlite_connections(tmp_path):
    first, second = make_app(tmp_path), make_app(tmp_path)

    def publish(item):
        app, index = item
        try:
            return app.account_states.record_task(index, "CREATE_PAGE", "SUCCESS", "verified", result(index, f"job-{index}"))
        except DuplicatePageResult:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        committed = list(pool.map(publish, ((first, 1), (second, 2))))
    assert sum(committed) == 1
    with sqlite3.connect(first.account_states.history.path) as db:
        assert db.execute("SELECT sum(page_success_count) FROM accounts").fetchone()[0] == 1


def test_database_transaction_rolls_back_identity_if_account_write_fails(tmp_path, exports):
    app = make_app(tmp_path)
    with sqlite3.connect(app.account_states.history.path) as db:
        db.execute("CREATE TRIGGER reject_save BEFORE INSERT ON accounts BEGIN SELECT RAISE(ABORT, 'rejected'); END")
    with pytest.raises(sqlite3.IntegrityError):
        app.publish_create_page_result(1, result())
    with sqlite3.connect(app.account_states.history.path) as db:
        assert db.execute("SELECT count(*) FROM page_identities").fetchone()[0] == 0
    assert app.account_states.get(1)["page_success_count"] == 0
    assert not any(export.called for export in exports)


@pytest.mark.parametrize("export_index", [0, 1, 2])
def test_export_error_does_not_undo_verified_durable_success(tmp_path, exports, export_index):
    app = make_app(tmp_path)
    exports[export_index].side_effect = OSError("export disk error")
    assert app.publish_create_page_result(1, result())
    state = app.account_states.get(1)
    assert state["page_success_count"] == 1
    assert state["tasks"]["CREATE_PAGE"]["status"] == "SUCCESS"
    assert app.account_states.history.load(state)["page_success_count"] == 1
    assert any("EXPORT_ERROR" in call.args[0] for call in app.log.call_args_list)
    with pytest.raises(DuplicatePageResult):
        app.publish_create_page_result(2, result(2, "job-B"))


def test_bootstrap_preserves_legacy_exclusions_without_fabricating_success(tmp_path, exports):
    app = make_app(tmp_path)
    history = app.account_states.history
    assert not history.page_identity_bootstrapped()
    history.bootstrap_page_identities({"id:99999"})
    history.bootstrap_page_identities({"id:88888"})
    assert history.page_identity_bootstrapped()
    with pytest.raises(DuplicatePageResult):
        app.publish_create_page_result(1, result())
    assert app.account_states.get(1)["page_success_count"] == 0
    assert app.publish_create_page_result(1, result(job="job-B", page_id="88888"))


def test_bootstrap_preserves_existing_sqlite_history_when_csv_missing(tmp_path, exports):
    app = make_app(tmp_path)
    page = result()
    page.pop("owner_account_id")
    app.account_states.record_task(1, "CREATE_PAGE", "SUCCESS", "legacy verified page", page)
    app.account_states.history.bootstrap_page_identities(set())
    restarted = make_app(tmp_path)
    with pytest.raises(DuplicatePageResult):
        restarted.publish_create_page_result(1, result(job="new-job"))
    assert restarted.account_states.get(1)["page_success_count"] == 1


def test_credential_redaction_cannot_change_verified_identity(tmp_path, exports):
    app = make_app(tmp_path)
    accounts = []
    for index in (1, 2):
        uid = ("11111", "22222")[index - 1]
        accounts.append({**module.import_account_record(
            f"{uid}|11111||c_user={uid}; xs=SECRET;|"
        ).to_account_dict(), "stt": index, "account_id": uid})
    app.account_states.sync(accounts)
    assert app.publish_create_page_result(1, result())
    with pytest.raises(DuplicatePageResult):
        app.publish_create_page_result(2, result(2, "job-B"))
    assert app.account_states.get(1)["page_success_count"] == 1
