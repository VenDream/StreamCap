import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import flet as ft

from app.ui.layout.responsive_layout import is_mobile_device, setup_responsive_layout
from app.ui.views.recordings_view import RecordingsPage
from main import handle_page_resize


class ResponsiveLayoutTests(unittest.IsolatedAsyncioTestCase):
    def test_is_mobile_device_uses_window_width_when_page_width_is_unavailable(self):
        page = SimpleNamespace(width=0, window=SimpleNamespace(width=1280))

        assert is_mobile_device(page) is False

    def test_handle_page_resize_runs_registered_page_resize_handler(self):
        page = SimpleNamespace(
            width=1280,
            window=SimpleNamespace(width=1280),
            run_task=Mock(),
            update=Mock(),
        )
        resize_handler = AsyncMock()
        app = SimpleNamespace(page_resize_handler=resize_handler)
        event = SimpleNamespace()

        with patch("main.setup_responsive_layout") as responsive_layout:
            on_resize = handle_page_resize(page, app)
            on_resize(event)

        responsive_layout.assert_called_once_with(page, app)
        page.run_task.assert_called_once_with(resize_handler, event)
        page.update.assert_called_once_with()

    async def test_recordings_page_load_registers_grid_resize_handler_without_overwriting_page_handler(self):
        original_resize_handler = Mock()
        page = SimpleNamespace(
            on_resize=original_resize_handler,
            on_keyboard_event=None,
            pubsub=SimpleNamespace(subscribe_topic=lambda *_args, **_kwargs: None),
        )
        app = SimpleNamespace(
            page=page,
            content_area=SimpleNamespace(controls=[], update=Mock()),
            settings=SimpleNamespace(user_config={"is_grid_view": True}),
            language_manager=SimpleNamespace(language={}, add_observer=lambda *_args, **_kwargs: None),
            page_resize_handler=None,
        )

        with patch.object(RecordingsPage, "init", lambda self: None):
            recordings_page = RecordingsPage(app)

        recordings_page.recording_card_area = SimpleNamespace(content=SimpleNamespace(controls=[object()]))
        recordings_page.create_recordings_title_area = Mock(return_value=object())
        recordings_page.create_filter_area = Mock(return_value=object())
        recordings_page.create_recordings_content_area = Mock(return_value=object())
        recordings_page.apply_filter = AsyncMock()
        recordings_page.add_record_cards = AsyncMock()
        recordings_page.recalculate_grid_columns = AsyncMock()
        recordings_page.update_grid_layout = AsyncMock()

        await recordings_page.load()

        assert page.on_resize is original_resize_handler
        assert app.page_resize_handler is recordings_page.update_grid_layout

    def test_layout_switch_keeps_mounted_root_control(self):
        page = SimpleNamespace(width=500, window=SimpleNamespace(width=500), go=lambda *_args: None)
        root = ft.Container(expand=True)
        navigation = ft.Container(width=192, visible=True)
        app = SimpleNamespace(
            language_manager=SimpleNamespace(
                language={
                    "sidebar": {
                        "home": "Home",
                        "recordings": "Recordings",
                        "settings": "Settings",
                        "storage": "Storage",
                        "about": "About",
                    }
                }
            ),
            left_navigation_menu=navigation,
            content_area=ft.Column(),
            dialog_area=ft.Container(),
            snack_bar_area=ft.Container(),
            complete_page=root,
            is_mobile=False,
        )

        setup_responsive_layout(page, app)

        assert app.complete_page is root
        assert isinstance(root.content, ft.Column)
        assert navigation.visible is False

        page.width = 1200
        setup_responsive_layout(page, app)

        assert app.complete_page is root
        assert isinstance(root.content, ft.Row)
        assert navigation.visible is True
        assert navigation.width == 192


if __name__ == "__main__":
    unittest.main()
