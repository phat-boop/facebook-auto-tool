"""Phase 4: account-local result counters and durable, credential-free history."""
import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest

import client_app as module
from account_history import AccountHistoryStore, COUNTER_FIELDS


def records(order=("11111", "22222")):
    return [{**module.import_account_record(
        f"{uid}|PASSWORD_SECRET|TWOFA_SECRET|c_user={uid}; xs=COOKIE_SECRET==;|TOKEN_SECRET"
    ).to_account_dict(), "stt": index, "account_id": uid}
            for index, uid in enumerate(order, 1)]


def store(path=None, order=("11111", "22222")):
    states = module.AccountStateStore(AccountHistoryStore(path) if path else None)
    states.sync(records(order))
    return states


def page_result(states, index, status, job):
    states.record_task(index, "CREATE_PAGE", status, "Page outcome", {
        "page_job_id": job, "page_id": "99999" if status == "SUCCESS" else "",
        "status": status, "page_name": "Page " + job,
    })


def friend_result(states, index, status, target):
    states.record_task(index, "FRIEND_REQUEST", status, "Friend outcome", {
        "target": target, "result": "SENT" if status == "SUCCESS" else status,
    })


def app_with_store(states):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.account_states = states
    app.run_thread = None
    app.worker_loop = None
    app.worker_tasks = []
    app.is_running = True
    app.stop_requested = False
    app.run_error = None
    app.run_status = "RUNNING"
    app.run_account_indexes = set(states.indexes())
    app.root, app.btn_start, app.btn_stop, app.lbl_status_indicator = (mock.Mock() for _ in range(4))
    app.post_ui, app.log = mock.Mock(), mock.Mock()
    return app


def test_counters_are_account_local_and_update_at_result_time():
    states = store()
    page_result(states, 1, "SUCCESS", "job-A")
    page_result(states, 1, "FAILED", "job-B")
    friend_result(states, 1, "SUCCESS", "target-A")
    friend_result(states, 1, "ERROR", "target-B")
    assert [states.get(1)[key] for key in COUNTER_FIELDS] == [1, 1, 1, 1]
    assert [states.get(2)[key] for key in COUNTER_FIELDS] == [0, 0, 0, 0]
    page_result(states, 2, "SUCCESS", "job-C")
    assert states.get(1)["page_success_count"] == states.get(2)["page_success_count"] == 1


def test_duplicate_notifications_and_skipped_results_do_not_inflate_counters():
    states = store()
    page_result(states, 1, "SUCCESS", "job-A")
    page_result(states, 1, "SUCCESS", "job-A")
    friend_result(states, 1, "FAILED", "target-A")
    friend_result(states, 1, "ERROR", "target-A")
    friend_result(states, 1, "SKIPPED", "already-pending")
    states.record_task(1, "CREATE_PAGE", "RUNNING", "wait", preserve_outcomes=True)
    assert [states.get(1)[key] for key in COUNTER_FIELDS] == [1, 0, 0, 1]


def test_restart_keeps_login_mode_error_counters_and_task_results(tmp_path):
    path = tmp_path / "history.db"
    states = store(path)
    states.update(1, status="CHECKING")
    states.set_login_mode(1, "FALLBACK_LOGIN")
    states.update(1, status="LIVE", current_action="verified")
    page_result(states, 1, "SUCCESS", "job-A")
    friend_result(states, 1, "FAILED", "target-A")
    states.append_log(1, "persistent-account-A")
    reopened = store(path)
    state = reopened.get(1)
    assert state["status"] == "LIVE"
    assert state["login_mode"] == "FALLBACK_LOGIN"
    assert state["last_error"] == "Friend outcome"
    assert state["last_update"]
    assert [state[key] for key in COUNTER_FIELDS] == [1, 0, 0, 1]
    assert state["tasks"]["CREATE_PAGE"]["outcomes"][0]["page_job_id"] == "job-A"
    assert any("persistent-account-A" in log for log in state["history_logs"])
    assert not any("persistent-account-A" in log for log in reopened.get(2)["history_logs"])


@pytest.mark.parametrize("persistent", [False, True])
def test_refresh_and_reorder_bind_counters_to_uid_not_stt(tmp_path, persistent):
    states = store(tmp_path / "history.db" if persistent else None)
    page_result(states, 1, "SUCCESS", "job-A")
    friend_result(states, 2, "FAILED", "target-B")
    states.append_log(1, "A-only")
    states.sync(records(("22222", "11111")))
    assert states.get(1)["account_id"] == "22222"
    assert states.get(1)["friend_failed_count"] == 1
    assert states.get(1)["page_success_count"] == 0
    assert states.get(2)["account_id"] == "11111"
    assert states.get(2)["stt"] == 2
    assert states.get(2)["page_success_count"] == 1
    assert "A-only" in states.get(2)["logs"]
    assert "A-only" not in states.get(1)["logs"]
    states.sync(records(("22222", "11111")))
    assert states.get(2)["page_success_count"] == 1


def test_new_run_keeps_history_and_cumulative_counters(tmp_path):
    path = tmp_path / "history.db"
    states = store(path)
    page_result(states, 1, "SUCCESS", "old-job")
    states.append_log(1, "previous-run")
    states.set_login_mode(1, "COOKIE")
    states.update(1, status="CHECKING")
    state = states.get(1)
    assert state["tasks"] == {} and state["last_task_result"] == "PENDING"
    assert state["page_success_count"] == 1 and state["login_mode"] == "COOKIE"
    assert any("previous-run" in log for log in state["history_logs"])
    page_result(states, 1, "SUCCESS", "new-job")
    assert states.get(1)["page_success_count"] == 2
    with sqlite3.connect(path) as db:
        payloads = [json.loads(row[0]) for row in db.execute(
            "SELECT payload FROM events WHERE account_id='11111' AND payload IS NOT NULL")]
    assert any(any(item.get("page_job_id") == "old-job" for item in payload.get("outcomes", []))
               for payload in payloads)
    assert store(path).get(1)["page_success_count"] == 2


def test_live_account_failed_task_is_valid_and_run_is_not_green():
    states = store()
    states.update(1, status="LIVE")
    page_result(states, 1, "FAILED", "job-A")
    assert states.get(1)["status"] == "LIVE"
    assert states.get(1)["last_task_result"] == "FAILED"
    assert states.run_result({1}) == "COMPLETED_WITH_ERRORS"
    app = app_with_store(states)
    app.finish_run()
    assert app.run_status == "COMPLETED_WITH_ERRORS"
    assert app.lbl_status_indicator.config.call_args.kwargs["fg"] != "#10B981"
    assert "Hoàn thành" not in app.lbl_status_indicator.config.call_args.kwargs["text"]


def test_history_records_each_result_even_when_aggregate_task_remains_failed(tmp_path):
    path = tmp_path / "history.db"
    states = store(path)
    states.update(1, status="LIVE")
    page_result(states, 1, "FAILED", "failed-job")
    page_result(states, 1, "SUCCESS", "successful-job")
    assert states.get(1)["last_task_result"] == "FAILED"
    assert states.get(1)["page_success_count"] == states.get(1)["page_failed_count"] == 1
    with sqlite3.connect(path) as db:
        events = db.execute("SELECT result,payload FROM events WHERE account_id='11111' AND event_type='TASK' ORDER BY id").fetchall()
    assert [result for result, _payload in events] == ["FAILED", "SUCCESS"]
    assert all(len(json.loads(payload)["outcomes"]) == 1 for _result, payload in events)
    assert store(path).get(1)["last_task_result"] == "FAILED"


@pytest.mark.parametrize("status", ["DIE", "ERROR", "CHECKPOINT"])
def test_account_failure_also_produces_completed_with_errors(status):
    states = store()
    states.update(1, status=status, current_action="reason")
    assert states.run_result({1}) == "COMPLETED_WITH_ERRORS"
    assert states.run_result({2}) == "COMPLETED"


@pytest.mark.parametrize("cancelled,error,expected", [(False, None, "COMPLETED"),
                                                     (True, None, "CANCELLED"),
                                                     (False, "fatal worker error", "FAILED")])
def test_run_completion_states_are_separate_from_account_and_task(cancelled, error, expected):
    states = store()
    states.update(1, status="LIVE")
    app = app_with_store(states)
    app.stop_requested, app.run_error = cancelled, error
    app.finish_run()
    assert app.run_status == expected and app.run_status in module.RUN_STATUSES
    assert states.get(1)["status"] == "LIVE"
    app.finish_run()
    assert app.run_status == expected


def test_saved_run_error_survives_processed_account_removal():
    states = store()
    states.update(1, status="LIVE")
    page_result(states, 1, "FAILED", "job-A")
    app = app_with_store(states)
    app.run_status = states.run_result()
    states.sync([])
    app.finish_run()
    assert app.run_status == "COMPLETED_WITH_ERRORS"


def test_worker_sets_completed_with_errors_before_ui_removes_accounts():
    from test_run_snapshot_lifecycle import make_start_app, start_without_real_worker
    app = make_start_app()
    app.lbl_status_indicator = mock.Mock()
    start_without_real_worker(app)
    async def process(_p, index, *_args, **_kwargs):
        app.account_states.update(index, status="LIVE")
        page_result(app.account_states, index, "FAILED" if index == 1 else "SUCCESS", f"job-{index}")
    app.process_account_scoped = process
    with mock.patch.object(module, "async_playwright", return_value=mock.MagicMock()):
        asyncio.run(app.main_worker())
    assert app.run_status == "COMPLETED_WITH_ERRORS"
    app.finish_run()
    assert app.lbl_status_indicator.config.call_args.kwargs["fg"] != "#10B981"


def test_sqlite_migration_preserves_old_rows_and_events(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE accounts (
                account_id TEXT PRIMARY KEY,last_status TEXT,last_task_result TEXT,last_action TEXT,
                first_seen_at TEXT,last_seen_at TEXT,last_run_at TEXT,last_error TEXT,last_checkpoint_at TEXT,
                page_summary TEXT,friend_summary TEXT,proxy_label TEXT,tasks TEXT);
            CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT,account_id TEXT NOT NULL,
                timestamp TEXT,module TEXT,event_type TEXT,result TEXT,message TEXT);
            INSERT INTO accounts VALUES ('11111','LIVE','FAILED','old-action','first','seen',NULL,'old-error',NULL,'{}','{}','','{}');
            INSERT INTO events(account_id,timestamp,module,event_type,result,message)
                VALUES ('11111','old-time','ACCOUNT','LOG','LIVE','old-history');
        """)
    states = store(path)
    assert states.get(1)["status"] == "LIVE"
    assert any("old-history" in item for item in states.get(1)["history_logs"])
    page_result(states, 1, "SUCCESS", "new-job")
    reopened = store(path)
    assert reopened.get(1)["page_success_count"] == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT first_seen_at FROM accounts WHERE account_id='11111'").fetchone()[0] == "first"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_sqlite_does_not_store_credentials_in_errors_or_task_payload(tmp_path):
    path = tmp_path / "history.db"
    states = store(path)
    state = states.get(1)
    detail = "PASSWORD_SECRET TWOFA_SECRET COOKIE_SECRET== TOKEN_SECRET " + state["canonical_line"]
    outcome = {**state, "technical_error": detail, "nested": {"PASSWORD": "PASSWORD_SECRET", "twofa": "TWOFA_SECRET"}}
    states.record_task(1, "CREATE_PAGE", "ERROR", detail, outcome)
    states.update(1, status="ERROR", current_action=detail)
    states.set_login_mode(1, "COOKIE")
    with sqlite3.connect(path) as db:
        text = "\n".join(db.iterdump())
    content = path.read_bytes()
    for secret in ("PASSWORD_SECRET", "TWOFA_SECRET", "COOKIE_SECRET==", "TOKEN_SECRET", state["canonical_line"]):
        assert secret not in text and secret.encode() not in content
    loaded = AccountHistoryStore(path).load(state)
    assert loaded["login_mode"] == "COOKIE"
    assert "[REDACTED]" in loaded["last_error"]


def test_concurrent_results_are_atomic_and_account_isolated(tmp_path):
    path = tmp_path / "history.db"
    states = store(path)
    def result(number):
        index = 1 + number % 2
        page_result(states, index, "SUCCESS", f"job-{number}")
        friend_result(states, index, "FAILED", f"target-{number}")
        states.append_log(index, f"account-{index}-event-{number}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(result, range(40)))
    reopened = store(path)
    for index in (1, 2):
        assert [reopened.get(index)[key] for key in COUNTER_FIELDS] == [20, 0, 0, 20]
        assert not any(f"account-{3-index}-event" in log for log in reopened.get(index)["history_logs"])
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_ui_row_shows_account_counters_and_is_queued_at_result_time():
    states = store()
    app = app_with_store(states)
    app.account_state_tree = mock.Mock()
    app.account_state_tree.exists.return_value = True
    app.refresh_state_summary = mock.Mock()
    app.record_friend_outcome(1, module.FriendRequestOutcome("SENT", "target-A", "pending verified"))
    assert states.get(1)["friend_success_count"] == 1
    callback = app.post_ui.call_args.args[0]
    app.account_state_tree.item.assert_not_called()
    callback()
    values = app.account_state_tree.item.call_args.kwargs["values"]
    assert values[5:7] == ("0 / 0", "1 / 0")
    assert "PASSWORD_SECRET" not in str(values)


def test_finalizing_cancelled_task_does_not_count_a_failed_attempt():
    states = store()
    states.record_task(1, "CREATE_PAGE", "RUNNING", "starting")
    states.finalize_active_tasks(1, "SKIPPED", "stop requested")
    assert states.get(1)["page_failed_count"] == 0
    assert states.get(1)["tasks"]["CREATE_PAGE"]["status"] == "SKIPPED"
