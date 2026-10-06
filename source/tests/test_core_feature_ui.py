"""Real Tk layout checks for the simplified automation surface."""
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import font, ttk

import pytest

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import client_app as module


def build_preview(root):
    app = module.MainToolApp.__new__(module.MainToolApp)
    app.root = root
    app.style = ttk.Style(root)
    tk.Frame(root, height=64, bg="#131C2E").pack(side="top", fill="x")
    tk.Frame(root, height=28, bg="#131C2E").pack(side="bottom", fill="x")
    app.tab_main = tk.Frame(root)
    app.tab_main.pack(fill="both", expand=True)
    app._build_tab_main()
    return app


def assert_layout(size):
    root = tk.Tk()
    try:
        root.title("FacebookTool layout test - no automation")
        root.geometry(size)
        app = build_preview(root)
        root.update()
        assert set(app.mode_vars) == set(module.CORE_AUTOMATION_MODES)
        assert not hasattr(app, "chk_view_stories")
        assert not hasattr(app, "chk_watch_reels")
        for control in (app.btn_start, app.btn_stop, app.txt_targets, app.ent_selected_indexes):
            assert control.winfo_ismapped()
            assert control.winfo_width() > 30 and control.winfo_height() >= 20
            assert control.winfo_rooty() >= root.winfo_rooty()
            assert control.winfo_rooty() + control.winfo_height() <= root.winfo_rooty() + root.winfo_height()
        for control in (app.ent_warmup_seconds, app.ent_notification_seconds, app.ent_target,
                        app.ent_page_target, app.ent_min_delay, app.ent_max_delay,
                        app.ent_min_page_delay, app.ent_max_page_delay):
            assert control.winfo_width() >= control.winfo_reqwidth()
        assert font.Font(root=root, font=app.ent_warmup_seconds.cget("font")).actual("size") >= 13
        assert font.Font(root=root, font=app.btn_start.cget("font")).actual("size") >= 13
        assert app.ent_warmup_seconds.get() == "30"
        assert app.ent_notification_seconds.get() == "3"
        assert app.txt_proxies.winfo_height() >= 20
        assert app.lbl_proxy_count.winfo_height() >= app.lbl_proxy_count.winfo_reqheight()
        # Scrolling settings never scrolls or hides the run buttons.
        button_y = app.btn_start.winfo_rooty()
        app.settings_canvas.yview_moveto(1)
        root.update()
        assert app.btn_start.winfo_rooty() == button_y
    finally:
        root.destroy()


@pytest.mark.parametrize("size", ["1000x620", "1366x768", "1920x1080"])
def test_core_ui_controls_fit_and_removed_options_are_absent(size):
    # Each GUI check owns one Tcl interpreter, isolated from other Tk tests.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), size],
                            cwd=Path(module.__file__).parent, capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    assert_layout(sys.argv[1])
