import unittest
from types import SimpleNamespace
from unittest.mock import patch

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


class StubSettingsPage:
    def __init__(self, app):
        self.app = app
        self.language_code = "zh_CN"
        self.user_config = {
            "theme_mode": "light",
            "is_grid_view": True,
            "last_update_check": 0,
        }


class StubLanguageManager:
    def __init__(self, app):
        self.app = app


class StubComponent:
    def __init__(self, app):
        self.app = app


class StubInstallationManager(StubComponent):
    async def check_env(self):
        return None


class StubRecordingManager(StubComponent):
    async def check_free_space(self):
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


class AppInitializationTests(unittest.TestCase):
    def test_app_sets_is_mobile_before_recordings_page_init(self):
        page = DummyPage()

        with (
            patch("app.app_manager.SettingsPage", StubSettingsPage),
            patch("app.app_manager.LanguageManager", StubLanguageManager),
            patch("app.app_manager.AboutPage", StubComponent),
            patch("app.app_manager.RecordingsPage", StubRecordingsPage),
            patch("app.app_manager.HomePage", StubComponent),
            patch("app.app_manager.StoragePage", StubComponent),
            patch("app.app_manager.NavigationSidebar", StubComponent),
            patch("app.app_manager.LeftNavigationMenu", StubComponent),
            patch("app.app_manager.ShowSnackBar", StubComponent),
            patch("app.app_manager.RecordingCardManager", StubComponent),
            patch("app.app_manager.RecordingManager", StubRecordingManager),
            patch("app.app_manager.InstallationManager", StubInstallationManager),
            patch("app.app_manager.UpdateChecker", StubUpdateChecker),
            patch("app.app_manager.utils.get_startup_info", return_value=None),
            patch.object(App, "start_video_api_service", return_value=None),
        ):
            app = App(page)

        assert app.is_mobile is False


if __name__ == "__main__":
    unittest.main()
