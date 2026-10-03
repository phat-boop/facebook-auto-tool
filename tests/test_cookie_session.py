"""Cookie-first login, affirmative session evidence and failure classification."""
import asyncio
import contextvars
from unittest import mock

import pytest

import client_app as module


UID = "123456789"
COOKIE = f"c_user={UID}; xs=abc=def;"


class LoginLocator:
    def __init__(self, page, kind, visible=True):
        self.page, self.kind, self.visible = page, kind, visible

    @property
    def first(self):
        return self

    def nth(self, _index):
        return self

    async def count(self):
        return int(self.visible)

    async def is_visible(self):
        if self.page.visibility_error:
            raise self.page.visibility_error
        return self.visible

    async def fill(self, value):
        self.page.events.append(("fill", self.kind, value))

    async def click(self):
        self.page.events.append(("click", self.kind))
        if self.kind == "password-submit":
            if self.page.password_error:
                raise self.page.password_error
            mode = self.page.password_mode
            if mode == "valid":
                self.page.sign_in()
            elif mode == "invalid":
                self.page.url = "https://www.facebook.com/login/"
                self.page.login_form = True
            elif mode in {"twofa", "twofa-invalid"}:
                self.page.url = "https://www.facebook.com/checkpoint/"
                self.page.code_visible = True
            elif mode == "mismatch":
                self.page.sign_in("999999999")
            else:
                self.page.url = "https://www.facebook.com/checkpoint/"
        elif self.kind == "twofa-submit":
            if self.page.password_mode == "twofa":
                self.page.sign_in()


class LoginContext:
    def __init__(self, events):
        self.events = events
        self.values = []
        self.cookie_error = None
        self.restore_error = None
        self.close = mock.AsyncMock()

    async def add_cookies(self, cookies):
        self.events.append(("restore", cookies))
        if self.restore_error:
            raise self.restore_error
        self.values = list(cookies)

    async def clear_cookies(self):
        self.events.append(("clear-cookie",))
        self.values = []

    async def cookies(self, _url):
        if self.cookie_error:
            raise self.cookie_error
        return self.values


class LoginPage:
    def __init__(self, context, cookie_mode="valid", password_mode="valid"):
        self.context = context
        self.events = context.events
        self.cookie_mode, self.password_mode = cookie_mode, password_mode
        self.url = "https://www.facebook.com/"
        self.authenticated = False
        self.login_form = False
        self.code_visible = False
        self.navigation_error = self.password_error = self.dom_error = self.visibility_error = None
        self.http_status = 200
        self.close = mock.AsyncMock()

    def sign_in(self, uid=UID):
        self.url = "https://www.facebook.com/"
        self.authenticated = True
        self.login_form = self.code_visible = False
        self.context.values = [{"name": "c_user", "value": uid}]

    async def goto(self, url, **_kwargs):
        self.events.append(("goto", url))
        if self.navigation_error:
            raise self.navigation_error
        self.url = url
        if url.endswith("/login/"):
            self.authenticated = False
            self.login_form = True
        elif self.cookie_mode == "valid":
            self.sign_in()
        elif self.cookie_mode == "invalid":
            self.url = "https://www.facebook.com/login/"
            self.login_form = True
        elif self.cookie_mode == "login-form":
            self.login_form = True
        elif self.cookie_mode == "mismatch":
            self.sign_in("999999999")
        elif self.cookie_mode == "missing-cookie":
            self.authenticated = True
            self.context.values = []
        elif self.cookie_mode == "twofa-login-wall":
            self.url = "https://www.facebook.com/login/approvals/"
            self.code_visible = True
        elif self.cookie_mode in {"checkpoint", "challenge", "disabled", "suspended", "two_factor"}:
            self.url = f"https://www.facebook.com/{self.cookie_mode}/"
        return mock.Mock(status=self.http_status)

    def locator(self, selector):
        if self.dom_error:
            raise self.dom_error
        if selector == module.FACEBOOK_LOGIN_FORM_SELECTOR:
            return LoginLocator(self, "login-form", self.login_form)
        if selector == module.FACEBOOK_AUTHENTICATED_SELECTOR:
            return LoginLocator(self, "authenticated", self.authenticated)
        if selector == module.FACEBOOK_2FA_INPUT_SELECTOR:
            return LoginLocator(self, "twofa-code", self.code_visible)
        if selector == module.FACEBOOK_2FA_SUBMIT_SELECTOR:
            return LoginLocator(self, "twofa-submit", self.code_visible)
        if selector == 'button[name="login"], button[type="submit"]':
            return LoginLocator(self, "password-submit")
        return LoginLocator(self, selector)

    async def evaluate(self, _script):
        return False

    async def wait_for_timeout(self, _milliseconds):
        await asyncio.sleep(0)


def make_app(tmp_path, cookie_mode="valid", password_mode="valid", twofa=""):
    app = module.MainToolApp.__new__(module.MainToolApp)
    record = module.import_account_record(f"{UID}|Password|{twofa}|{COOKIE}|EAAA_NOT_FOR_BROWSER")
    app.account_states = module.AccountStateStore()
    app.account_states.sync([{**record.to_account_dict(), "stt": 1, "account_id": UID}])
    app.account_log_context = contextvars.ContextVar("phase2_account", default=None)
    app.run_config = {"modes": {}, "options": {}, "targets": "", "headless": True}
    app.is_running, app.stop_requested = True, False
    app.log = mock.Mock()
    app.post_ui = mock.Mock()
    app.update_tree_row = mock.Mock()
    app.selected_log_account = None
    app.refresh_account_state_row = mock.Mock()
    app.render_log_view = mock.Mock()
    app.get_current_friends_count = mock.AsyncMock(return_value=0)
    app.watch_facebook_checkpoint = mock.AsyncMock()
    events = []
    context = LoginContext(events)
    page = LoginPage(context, cookie_mode, password_mode)
    browser = mock.Mock(close=mock.AsyncMock())
    app.create_browser_page = mock.AsyncMock(return_value=(browser, context, page))
    return app, context, page, events


def run_account(app, username=UID, password="Password", proxy=None):
    async def run():
        await app.process_account_scoped(object(), 1, UID, COOKIE, proxy, asyncio.Semaphore(1),
                                         login_user=username, login_password=password)
    # Preserve real scheduling/yields while skipping fixed four-second waits.
    original_sleep = asyncio.sleep
    async def fast_sleep(_seconds):
        await original_sleep(0)
    with mock.patch.object(module.asyncio, "sleep", side_effect=fast_sleep):
        asyncio.run(run())
    return app.account_states.get(1)


@pytest.fixture(autouse=True)
def private_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "output_path", lambda name: str(tmp_path / name))


def test_valid_cookie_is_first_and_never_uses_password_or_token(tmp_path):
    app, context, page, events = make_app(tmp_path)
    app.login_facebook_user_pass = mock.AsyncMock(side_effect=AssertionError("fallback for valid cookie"))
    state = run_account(app)
    assert state["status"] == "LIVE" and state["login_mode"] == "COOKIE"
    app.login_facebook_user_pass.assert_not_awaited()
    assert events[0][0] == "restore" and events[1] == ("goto", "https://www.facebook.com/")
    assert not any("EAAA_NOT_FOR_BROWSER" in str(event) for event in events)
    assert not any(event[0] == "fill" for event in events)
    context.close.assert_awaited_once()
    page.close.assert_awaited_once()


@pytest.mark.parametrize("cookie_mode", ["invalid", "login-form", "missing-cookie", "mismatch"])
def test_confirmed_invalid_cookie_falls_back_and_verifies_same_uid(tmp_path, cookie_mode):
    app, context, page, events = make_app(tmp_path, cookie_mode)
    state = run_account(app)
    assert state["status"] == "LIVE" and state["login_mode"] == "FALLBACK_LOGIN"
    assert next(event for event in events if event[0] == "fill" and event[1] == 'input[name="email"]')[2] == UID
    assert next(event for event in events if event[0] == "fill" and event[1] == 'input[name="pass"]')[2] == "Password"
    assert events.index(("clear-cookie",)) > 0
    assert context.values == [{"name": "c_user", "value": UID}]


@pytest.mark.parametrize("error", [TimeoutError("navigation timeout"), OSError("DNS failure"),
                                   RuntimeError("proxy connection failed"), RuntimeError("browser crashed")])
def test_cookie_technical_error_does_not_fallback_or_die(tmp_path, error):
    app, context, page, _events = make_app(tmp_path)
    page.navigation_error = error
    app.login_facebook_user_pass = mock.AsyncMock()
    state = run_account(app)
    assert state["status"] == "ERROR" and state["login_mode"] == "COOKIE"
    assert str(error) in state["current_action"]
    app.login_facebook_user_pass.assert_not_awaited()
    app.watch_facebook_checkpoint.assert_not_called()


@pytest.mark.parametrize("kind", ["restore", "cookies", "dom", "visibility"])
def test_cookie_verification_exceptions_never_become_live_or_fallback(tmp_path, kind):
    app, context, page, _events = make_app(tmp_path)
    error = RuntimeError("temporary DOM/network error")
    if kind == "restore":
        context.restore_error = error
    elif kind == "cookies":
        context.cookie_error = error
    elif kind == "dom":
        page.dom_error = error
    else:
        page.visibility_error = error
    app.login_facebook_user_pass = mock.AsyncMock()
    state = run_account(app)
    assert state["status"] == "ERROR"
    app.login_facebook_user_pass.assert_not_awaited()


@pytest.mark.parametrize("status", [403, 407, 429, 500, 502, 503])
def test_http_network_or_proxy_failure_does_not_trigger_password(tmp_path, status):
    app, context, page, _events = make_app(tmp_path)
    page.http_status = status
    app.login_facebook_user_pass = mock.AsyncMock()
    assert run_account(app)["status"] == "ERROR"
    app.login_facebook_user_pass.assert_not_awaited()


def test_blank_page_with_stale_cookie_is_error_without_password_attempt(tmp_path):
    app, context, page, _events = make_app(tmp_path, "blank")
    app.login_facebook_user_pass = mock.AsyncMock()
    state = run_account(app)
    assert state["status"] == "ERROR" and state["login_mode"] == "COOKIE"
    assert "bằng chứng" in state["current_action"]
    app.login_facebook_user_pass.assert_not_awaited()


def test_uid_mismatch_cannot_be_live_without_a_verified_fallback(tmp_path):
    app, context, page, _events = make_app(tmp_path, "mismatch")
    state = run_account(app, password="")
    assert state["status"] == "DIE" and "khớp UID" in state["current_action"]
    assert not any(event[0] == "fill" for event in page.events)


@pytest.mark.parametrize("password_mode,expected", [("invalid", "DIE"), ("mismatch", "DIE"),
                                                   ("checkpoint", "CHECKPOINT")])
def test_fallback_result_classification(tmp_path, password_mode, expected):
    app, context, page, _events = make_app(tmp_path, "invalid", password_mode)
    state = run_account(app)
    assert state["status"] == expected and state["login_mode"] == "FALLBACK_LOGIN"
    app.watch_facebook_checkpoint.assert_not_called()


@pytest.mark.parametrize("error", [TimeoutError("password navigation timeout"), OSError("network DNS"),
                                   RuntimeError("proxy failure"), RuntimeError("browser closed")])
def test_fallback_technical_error_is_error_not_die(tmp_path, error):
    app, context, page, _events = make_app(tmp_path, "invalid")
    page.password_error = error
    state = run_account(app)
    assert state["status"] == "ERROR" and state["login_mode"] == "FALLBACK_LOGIN"
    assert str(error) in state["current_action"]


@pytest.mark.parametrize("mode,expected", [("checkpoint", "CHECKPOINT"), ("challenge", "CHECKPOINT"),
                                          ("disabled", "DIE"), ("suspended", "DIE"),
                                          ("two_factor", "CHECKPOINT"), ("twofa-login-wall", "CHECKPOINT")])
def test_terminal_cookie_account_state_never_tries_password(tmp_path, mode, expected):
    app, context, page, _events = make_app(tmp_path, mode)
    app.login_facebook_user_pass = mock.AsyncMock()
    state = run_account(app)
    assert state["status"] == expected and state["login_mode"] == "COOKIE"
    app.login_facebook_user_pass.assert_not_awaited()
    app.watch_facebook_checkpoint.assert_not_called()


def test_password_twofa_uses_same_account_seed_and_verifies_session(tmp_path):
    seed = "JBSWY3DPEHPK3PXP"
    app, context, page, events = make_app(tmp_path, "invalid", "twofa", twofa=seed)
    with mock.patch.object(module, "generate_totp_code", return_value="123456") as totp:
        state = run_account(app)
    totp.assert_called_once_with(seed)
    assert ("fill", "twofa-code", "123456") in events
    assert state["status"] == "LIVE" and state["login_mode"] == "FALLBACK_LOGIN"
    app.watch_facebook_checkpoint.assert_called_once()


@pytest.mark.parametrize("seed,mode", [("", "twofa"), ("JBSWY3DPEHPK3PXP", "twofa-invalid")])
def test_unresolved_twofa_remains_checkpoint_not_live_or_die(tmp_path, seed, mode):
    app, context, page, _events = make_app(tmp_path, "invalid", mode, twofa=seed)
    state = run_account(app)
    assert state["status"] == "CHECKPOINT" and state["login_mode"] == "FALLBACK_LOGIN"
    app.watch_facebook_checkpoint.assert_not_called()


@pytest.mark.parametrize("url", ["about:blank", "chrome-error://chromewebdata/", "https://example.com/",
                                 "https://facebook.com.evil.test/", "https://example.com/checkpoint/"])
def test_verifier_rejects_non_facebook_page_even_with_cookie_and_ui(tmp_path, url):
    app, context, page, _events = make_app(tmp_path)
    page.sign_in()
    page.url = url
    result, _detail = asyncio.run(app.verify_facebook_session(page, context, UID))
    assert result == module.LOGIN_TECHNICAL_ERROR


def test_hidden_positive_evidence_is_not_enough(tmp_path):
    app, context, page, _events = make_app(tmp_path)
    page.sign_in()
    original_locator = page.locator
    hidden = LoginLocator(page, "authenticated", visible=False)
    hidden.count = mock.AsyncMock(return_value=1)
    page.locator = lambda selector: hidden if selector == module.FACEBOOK_AUTHENTICATED_SELECTOR else original_locator(selector)
    result, _detail = asyncio.run(app.verify_facebook_session(page, context, UID))
    assert result == module.LOGIN_TECHNICAL_ERROR


def test_login_form_blocks_live_despite_cookie_and_positive_evidence(tmp_path):
    app, context, page, _events = make_app(tmp_path)
    page.sign_in()
    page.login_form = True
    result, _detail = asyncio.run(app.verify_facebook_session(page, context, UID))
    assert result == module.LOGIN_INVALID


def test_login_mode_and_twofa_context_are_isolated_between_accounts(tmp_path):
    app, context, page, _events = make_app(tmp_path, "invalid", "twofa", twofa="JBSWY3DPEHPK3PXP")
    other = module.import_account_record("987654321|OtherPass|OTHER_2FA|c_user=987654321;|OTHER_TOKEN")
    first = app.account_states.get(1)
    app.account_states.sync([first, {**other.to_account_dict(), "stt": 2, "account_id": other.uid}])
    with mock.patch.object(module, "generate_totp_code", return_value="123456") as totp:
        state = run_account(app)
    assert state["login_mode"] == "FALLBACK_LOGIN"
    assert "login_mode" not in app.account_states.get(2)
    assert app.account_states.get(2)["status"] == "UNKNOWN"
    totp.assert_called_once_with("JBSWY3DPEHPK3PXP")
