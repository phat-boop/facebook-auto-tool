"""Process ownership and conservative, module-local structural circuit breakers."""
import errno
import os
import threading


class DuplicatePageResult(ValueError):
    pass


class SingleInstanceLock:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def acquire(self):
        if self.handle is not None:
            return True
        handle = open(self.path, "a+b")
        try:
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                return False
            raise
        except BaseException:
            handle.close()
            raise
        self.handle = handle
        return True

    def release(self):
        handle, self.handle = self.handle, None
        if handle is None:
            return
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


STRUCTURAL_FAILURES = frozenset({
    "PAGE_NAME_INPUT_MISSING", "CATEGORY_INPUT_MISSING", "CREATE_SUBMIT_MISSING",
})


class ModuleCircuitBreaker:
    def __init__(self, threshold=3):
        self.threshold = max(2, int(threshold))
        self.lock = threading.RLock()
        self.modules = {}

    def reset(self):
        with self.lock:
            self.modules.clear()

    def paused_reason(self, module):
        with self.lock:
            return self.modules.get(module, {}).get("paused", "")

    def observe(self, module, account_id, result, account_status="LIVE"):
        with self.lock:
            state = self.modules.setdefault(module, {"signature": "", "accounts": set(), "paused": ""})
            if state["paused"]:
                return False
            code = result.get("structural_failure", "")
            eligible = (code in STRUCTURAL_FAILURES and result.get("status") in {"FAILED", "ERROR"}
                        and account_status not in {"DIE", "CHECKPOINT", "ERROR"})
            if not eligible:
                state.update(signature="", accounts=set())
                return False
            if code != state["signature"]:
                state.update(signature=code, accounts=set())
            state["accounts"].add(str(account_id))
            if len(state["accounts"]) >= self.threshold:
                state["paused"] = f"MODULE_PAUSED / structural failure: {code} ({len(state['accounts'])} accounts)"
                return True
            return False


_BREAKER_INIT_LOCK = threading.Lock()


def app_circuit_breaker(app):
    with _BREAKER_INIT_LOCK:
        if not hasattr(app, "module_breaker"):
            app.module_breaker = ModuleCircuitBreaker()
        return app.module_breaker
