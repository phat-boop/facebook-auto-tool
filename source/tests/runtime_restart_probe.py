"""Isolated onefile restart probe; never launches the licensed application."""
import ast
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    source_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "client_app.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names = {"get_update_restart_environment", "build_windows_update_restart_script"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"os": os, "base64": base64}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_path), "exec"), namespace)
    root = Path(sys.executable).resolve().parent
    marker = root / "restart_phase.json"
    error_log = root / "restart_error.log"
    if marker.exists():
        marker.write_text(json.dumps({
            "phase": "restarted", "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable, "pid": os.getpid(), "parent_pid": os.getppid(),
        }), encoding="utf-8")
        time.sleep(12)
        return
    marker.write_text(json.dumps({"phase": "old_instance", "pid": os.getpid()}), encoding="utf-8")
    updater = root / "updater.bat"
    updater.write_text(namespace["build_windows_update_restart_script"](
        os.getpid(), str(root / "update_temp.exe"), sys.executable, str(error_log),
        parent_process_id=os.getppid(),
    ), encoding="utf-8")
    process = subprocess.Popen(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(updater)],
        cwd=root, env=namespace["get_update_restart_environment"](),
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    (root / "helper_pid.txt").write_text(str(process.pid), encoding="ascii")


if __name__ == "__main__":
    main()
