import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import flet as ft

from app.app_manager import App


class DummyPage:
    def __init__(self):
        self.web = True
        self.theme_mode = ft.ThemeMode.LIGHT
        self.pubsub = SimpleNamespace()
        self._tasks = []

    def run_task(self, func, *args, **kwargs):
        self._tasks.append((func, args, kwargs))


class StubSettingsConfig:
    def __init__(self):
        self.language_code = "en"
        self.user_config = {}
        self.cookies_config = {}
        self.accounts_config = {}

    def adopt_user_config(self, user_config):
        self.user_config = dict(user_config)

    def adopt_cookies_config(self, cookies_config):
        self.cookies_config = dict(cookies_config)

    def adopt_accounts_config(self, accounts_config):
        self.accounts_config = dict(accounts_config)


class StubSettingsPage:
    def __init__(self, app):
        self.app = app
        self.language_code = "zh_CN"
        self.user_config = {
            "theme_mode": "light",
            "is_grid_view": True,
            "last_update_check": 0,
        }
        self.cookies_config = {"bilibili": "cookie"}
        self.accounts_config = {"douyin": {"username": "tester"}}


class StubComponent:
    def __init__(self, app):
        self.app = app


class StubInstallationManager(StubComponent):
    async def check_env(self):
        return None


class StubUpdateChecker:
    def __init__(self, app):
        self.app = app
        self.update_config = {"auto_check": False, "check_interval": 0}


class StubRecordingsPage:
    def __init__(self, app):
        if not hasattr(app, "is_mobile"):
            raise AttributeError("App missing is_mobile before RecordingsPage init")
        self.app = app


class StubServices:
    def __init__(self):
        self.settings_config = StubSettingsConfig()
        self.config_manager = SimpleNamespace(save_user_config=AsyncMock())
        self.process_manager = SimpleNamespace(cleanup=AsyncMock())
        self.language_manager = SimpleNamespace(language={}, add_observer=lambda *_args, **_kwargs: None)
        self.recording_manager = SimpleNamespace(check_free_space=AsyncMock())
        self.subprocess_start_up_info = None
        self.tray_manager = None
        self.recording_enabled = True
        self.registered_bridge = None

    def register_ui_bridge(self, bridge):
        self.registered_bridge = bridge

    def unregister_ui_bridge(self, bridge):
        if self.registered_bridge is bridge:
            self.registered_bridge = None


class AppInitializationTests(unittest.TestCase):
    def test_app_accepts_services_and_sets_is_mobile_before_recordings_page_init(self):
        page = DummyPage()
        services = StubServices()

        with (
            patch("app.app_manager.SettingsPage", StubSettingsPage),
            patch("app.app_manager.AboutPage", StubComponent),
            patch("app.app_manager.RecordingsPage", StubRecordingsPage),
            patch("app.app_manager.HomePage", StubComponent),
            patch("app.app_manager.StoragePage", StubComponent),
            patch("app.app_manager.NavigationSidebar", StubComponent),
            patch("app.app_manager.LeftNavigationMenu", StubComponent),
            patch("app.app_manager.ShowSnackBar", StubComponent),
            patch("app.app_manager.RecordingCardManager", StubComponent),
            patch("app.app_manager.InstallationManager", StubInstallationManager),
            patch("app.app_manager.UpdateChecker", StubUpdateChecker),
            patch.object(App, "start_video_api_service", return_value=None) as start_video_api_service,
        ):
            app = App(page, services=services)

        assert app.record_manager is services.recording_manager
        assert services.registered_bridge is app
        assert app.is_mobile is False
        assert services.settings_config.language_code == "zh_CN"
        assert services.settings_config.cookies_config == {"bilibili": "cookie"}
        assert services.settings_config.accounts_config == {"douyin": {"username": "tester"}}
        start_video_api_service.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
