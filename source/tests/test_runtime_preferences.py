"""User-configured Feed and notification options must survive restart."""
import json
from unittest import mock

from cryptography.fernet import Fernet
import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app


@pytest.mark.parametrize("warmup,notifications", [(False, False), (True, False), (False, True), (True, True)])
def test_support_preferences_round_trip(tmp_path, warmup, notifications):
    path = tmp_path / "settings.json"
    cipher = Fernet(Fernet.generate_key())
    app = make_start_app()
    app.current_theme = next(iter(module.THEMES))
    app.chk_warmup.get.return_value = warmup
    app.chk_check_notif.get.return_value = notifications
    app.ent_warmup_seconds.get.return_value = "47"
    app.ent_notification_seconds.get.return_value = "19"
    recovered = make_start_app()
    recovered.cbo_theme = mock.Mock()
    recovered.apply_theme = mock.Mock()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)), \
         mock.patch.object(module, "settings_cipher", return_value=cipher):
        module.MainToolApp.save_settings(app)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["warmup"] is warmup and data["check_notif"] is notifications
        assert data["warmup_seconds"] == "47" and data["notification_seconds"] == "19"
        assert not {"watch_reels", "view_stories", "cancel_old", "browse_web",
                    "interact_page", "chat_react", "feed_surf_min", "watch_review_min"} & data.keys()
        module.MainToolApp.load_settings(recovered)
    recovered.chk_warmup.set.assert_called_once_with(warmup)
    recovered.chk_check_notif.set.assert_called_once_with(notifications)
    recovered.ent_warmup_seconds.insert.assert_called_once_with(0, "47")
    recovered.ent_notification_seconds.insert.assert_called_once_with(0, "19")


def test_older_settings_without_optional_action_keys_keep_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{}', encoding='utf-8')
    app = make_start_app()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)):
        module.MainToolApp.load_settings(app)
    app.chk_warmup.set.assert_not_called()
    app.chk_check_notif.set.assert_not_called()
    app.ent_warmup_seconds.insert.assert_not_called()
    app.ent_notification_seconds.insert.assert_not_called()
