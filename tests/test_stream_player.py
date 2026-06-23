import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import flet as ft

from app.ui.components.business.stream_player import StreamPlayer


class StreamPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_stream_falls_back_to_new_tab_when_webview_is_unavailable(self):
        launch_url = AsyncMock()
        app = SimpleNamespace(
            page=SimpleNamespace(
                url="http://127.0.0.1:6006",
                web=False,
                width=1280,
                height=720,
                launch_url=launch_url,
                set_clipboard=lambda *_args, **_kwargs: None,
            ),
            is_mobile=False,
            dialog_area=SimpleNamespace(content=None, update=lambda: None),
            snack_bar=SimpleNamespace(show_snack_bar=AsyncMock()),
            language_manager=SimpleNamespace(
                language={
                    "stream_player": {
                        "preview_title": "Live Preview",
                        "cannot_get_preview_url": "Cannot get preview URL",
                        "unsupported_format": "Unsupported format",
                        "stream_url_copied": "Stream URL copied",
                        "open_live_room": "Open Live Room",
                        "copy_stream_url": "Copy Stream URL",
                        "open_in_new_tab": "Open in New Tab",
                        "embedded_preview_unavailable": "Embedded preview unavailable",
                        "close": "Close",
                    },
                    "base": {},
                    "video_quality": {},
                }
            ),
        )
        player = StreamPlayer(app)
        recording = SimpleNamespace(
            preview_url="https://example.com/live.m3u8?token=abc",
            url="https://example.com/room",
            streamer_name="主播",
            platform="bilibili",
            quality="source",
            live_title="测试直播间",
        )
        expected_url = player._build_player_url(recording.preview_url, "m3u8")

        with patch.object(StreamPlayer, "_create_webview_control", return_value=None):
            await player.preview_stream(recording)

        launch_url.assert_awaited_once_with(expected_url, web_popup_window_name=ft.UrlTarget.BLANK)
        assert app.dialog_area.content is None
        app.snack_bar.show_snack_bar.assert_awaited_once_with("Embedded preview unavailable")

    def test_create_webview_control_uses_flet_webview_package_on_web(self):
        class FakeWebView:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        app = SimpleNamespace(page=SimpleNamespace(web=True, platform=None))
        player = StreamPlayer.__new__(StreamPlayer)
        player.app = app
        fake_module = SimpleNamespace(WebView=FakeWebView)
        player_url = "http://127.0.0.1:6007/api/player?stream_type=flv"

        with patch.dict("sys.modules", {"flet_webview": fake_module}):
            control = player._create_webview_control(player_url)

        assert isinstance(control, FakeWebView)
        assert control.kwargs == {"url": player_url, "expand": True}

    def test_build_player_base_url_uses_ipv4_loopback_for_localhost(self):
        app = SimpleNamespace(page=SimpleNamespace(url="http://localhost:6006"))
        player = StreamPlayer.__new__(StreamPlayer)
        player.app = app

        assert player._build_player_base_url() == "http://127.0.0.1:6007"

    async def test_copy_stream_url_uses_clipboard_service(self):
        class FakeClipboard:
            async def set(self, value):
                copied_values.append(value)

        copied_values = []
        launch_url = AsyncMock()
        app = SimpleNamespace(
            page=SimpleNamespace(
                url="http://localhost:6006",
                web=True,
                platform=None,
                width=1280,
                height=720,
                launch_url=launch_url,
            ),
            is_mobile=False,
            dialog_area=SimpleNamespace(content=None, update=lambda: None),
            snack_bar=SimpleNamespace(show_snack_bar=AsyncMock()),
            language_manager=SimpleNamespace(
                language={
                    "stream_player": {
                        "preview_title": "Live Preview",
                        "cannot_get_preview_url": "Cannot get preview URL",
                        "unsupported_format": "Unsupported format",
                        "stream_url_copied": "Stream URL copied",
                        "open_live_room": "Open Live Room",
                        "copy_stream_url": "Copy Stream URL",
                        "open_in_new_tab": "Open in New Tab",
                        "embedded_preview_unavailable": "Embedded preview unavailable",
                        "close": "Close",
                    },
                    "base": {},
                    "video_quality": {},
                }
            ),
        )
        recording = SimpleNamespace(
            preview_url="https://example.com/live.flv?token=abc",
            url="https://example.com/room",
            streamer_name="主播",
            platform="huya",
            quality="source",
            live_title="测试直播间",
        )
        player = StreamPlayer(app)

        with (
            patch.object(StreamPlayer, "_create_webview_control", return_value=ft.Text("player")),
            patch("app.ui.components.business.stream_player.ft.Clipboard", FakeClipboard),
        ):
            await player.preview_stream(recording)
            await app.dialog_area.content.actions[0].on_click(None)

        assert copied_values == [recording.preview_url]
        app.snack_bar.show_snack_bar.assert_awaited_once_with("Stream URL copied")


if __name__ == "__main__":
    unittest.main()
