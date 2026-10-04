"""Disabled optional actions must remain disabled after restart."""
import json
from unittest import mock

from cryptography.fernet import Fernet
import pytest

import client_app as module
from test_run_snapshot_lifecycle import make_start_app


@pytest.mark.parametrize("reels,stories", [(False, False), (True, False), (False, True), (True, True)])
def test_optional_actions_round_trip_without_reenabling(tmp_path, reels, stories):
    path = tmp_path / "settings.json"
    cipher = Fernet(Fernet.generate_key())
    app = make_start_app()
    app.current_theme = next(iter(module.THEMES))
    app.chk_watch_reels.get.return_value = reels
    app.chk_view_stories.get.return_value = stories
    recovered = make_start_app()
    recovered.cbo_theme = mock.Mock()
    recovered.apply_theme = mock.Mock()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)), \
         mock.patch.object(module, "settings_cipher", return_value=cipher):
        module.MainToolApp.save_settings(app)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["watch_reels"] is reels
        assert data["view_stories"] is stories
        module.MainToolApp.load_settings(recovered)
    recovered.chk_watch_reels.set.assert_called_once_with(reels)
    recovered.chk_view_stories.set.assert_called_once_with(stories)


def test_older_settings_without_optional_action_keys_keep_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{}', encoding='utf-8')
    app = make_start_app()
    with mock.patch.object(module, "SETTINGS_FILE", str(path)):
        module.MainToolApp.load_settings(app)
    app.chk_watch_reels.set.assert_not_called()
    app.chk_view_stories.set.assert_not_called()
