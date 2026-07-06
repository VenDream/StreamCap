import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.ui.views.settings_view import SettingsPage


class _StopAfterSecondGroupError(Exception):
    pass


class SettingsViewTests(unittest.TestCase):
    def test_create_push_settings_tab_accepts_current_flet_textfield_helper_api(self):
        page = SettingsPage.__new__(SettingsPage)
        page.app = SimpleNamespace(is_mobile=False)
        page._ = {
            "push_notifications": "push_notifications",
            "stream_start_notification_enabled": "stream_start_notification_enabled",
            "system_status_bar_notification_enabled": "system_status_bar_notification_enabled",
            "open_broadcast_push_enabled": "open_broadcast_push_enabled",
            "close_broadcast_push_enabled": "close_broadcast_push_enabled",
            "only_notify_no_record": "only_notify_no_record",
            "notify_loop_time": "notify_loop_time",
            "custom_push_settings": "custom_push_settings",
            "personalized_notification_content_behavior": "personalized_notification_content_behavior",
            "custom_push_title": "custom_push_title",
            "custom_push_title_variables_tip": "supported vars",
            "custom_open_broadcast_content": "custom_open_broadcast_content",
            "custom_close_broadcast_content": "custom_close_broadcast_content",
        }
        page.on_change = lambda *_args, **_kwargs: None
        page.get_config_value = lambda *_args, **_kwargs: ""
        page.create_setting_row = lambda label, control: (label, control)

        call_count = {"count": 0}

        def create_setting_group(*_args, **_kwargs):
            call_count["count"] += 1
            if call_count["count"] == 2:
                raise _StopAfterSecondGroupError

        page.create_setting_group = create_setting_group

        with self.assertRaises(_StopAfterSecondGroupError):  # noqa: PT027
            page.create_push_settings_tab()

    def test_language_change_updates_shared_settings_config_before_reload(self):
        page = SettingsPage.__new__(SettingsPage)
        page.user_config = {"language": "Chinese"}
        page.default_config = {}
        page.language_option = {"Chinese": "zh_CN", "English": "en"}
        page.default_language = "Chinese"
        page.language_code = "zh_CN"
        page.has_unsaved_changes = {"user_config": False}
        page.delay_handler = SimpleNamespace(start_task_timer=Mock())
        page.save_user_config_after_delay = Mock()
        page.load = Mock()
        page.app = SimpleNamespace(
            language_code="zh_CN",
            services=SimpleNamespace(settings_config=SimpleNamespace(language_code="zh_CN")),
            language_manager=SimpleNamespace(load=Mock(), notify_observers=Mock()),
        )
        page.page = SimpleNamespace(run_task=Mock())

        event = SimpleNamespace(control=SimpleNamespace(data="language"), data="English")

        asyncio.run(page.on_change(event))

        assert page.app.services.settings_config.language_code == "en"
        page.app.language_manager.load.assert_called_once_with()
        page.app.language_manager.notify_observers.assert_called_once_with()

    def test_restore_defaults_replaces_shared_settings_config_reference(self):
        page = SettingsPage.__new__(SettingsPage)
        old_config = {"language": "Chinese", "video_format": "FLV"}
        default_config = {"language": "English", "video_format": "TS"}
        settings_config = SimpleNamespace(user_config=old_config)

        def adopt_user_config(user_config):
            settings_config.user_config = user_config

        settings_config.adopt_user_config = Mock(side_effect=adopt_user_config)
        page.user_config = old_config
        page.default_config = default_config
        page.config_manager = SimpleNamespace(save_user_config=AsyncMock())
        page.load = Mock()
        page._ = {
            "confirm": "confirm",
            "query_restore_config_tip": "restore?",
            "cancel": "cancel",
            "sure": "sure",
            "success_restore_tip": "saved",
        }
        page.app = SimpleNamespace(
            services=SimpleNamespace(settings_config=settings_config),
            language_manager=SimpleNamespace(notify_observers=Mock()),
            snack_bar=SimpleNamespace(show_snack_bar=AsyncMock()),
            dialog_area=SimpleNamespace(content=None, update=Mock()),
        )
        page.page = SimpleNamespace(run_task=Mock())

        asyncio.run(page.restore_default_config(None))
        restore_dialog = page.app.dialog_area.content
        restore_dialog.update = Mock()
        asyncio.run(restore_dialog.actions[1].on_click(None))

        settings_config.adopt_user_config.assert_called_once_with(page.user_config)
        assert settings_config.user_config is page.user_config
        assert page.user_config == {"language": "Chinese", "video_format": "TS"}


if __name__ == "__main__":
    unittest.main()
