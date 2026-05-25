import unittest
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
