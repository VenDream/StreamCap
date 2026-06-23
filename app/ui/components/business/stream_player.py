import os
import urllib.parse

import flet as ft

from ....models.recording.recording_model import Recording
from ....utils.logger import logger


class StreamPlayer:
    SUPPORTED_WEBVIEW_PLATFORMS = {"android", "ios", "macos"}
    LOCAL_VIDEO_API_HOSTS = {"localhost", "0.0.0.0", "::", "::1"}

    def __init__(self, app):
        self.app = app
        self._ = {}
        self.load_language()

    def load_language(self):
        language = self.app.language_manager.language
        for key in ("stream_player", "base", "video_quality"):
            self._.update(language.get(key, {}))

    @staticmethod
    def _detect_stream_type(stream_url: str) -> str | None:
        lowered = stream_url.lower()
        if ".m3u8" in lowered or "m3u8" in lowered:
            return "m3u8"
        if ".flv" in lowered or "flv" in lowered:
            return "flv"
        return None

    def _build_player_base_url(self) -> str:
        video_api_external_url = os.getenv("VIDEO_API_EXTERNAL_URL", "").rstrip("/")
        if video_api_external_url:
            return video_api_external_url

        video_api_port = os.getenv("VIDEO_API_PORT", "6007")
        page_url = self.app.page.url
        if page_url:
            parsed = urllib.parse.urlparse(page_url)
            host = parsed.hostname or "localhost"
            if host in self.LOCAL_VIDEO_API_HOSTS:
                host = "127.0.0.1"
            return f"http://{host}:{video_api_port}"

        return f"http://localhost:{video_api_port}"

    def _build_player_url(self, stream_url: str, stream_type: str) -> str:
        encoded_stream_url = urllib.parse.quote(stream_url, safe="")
        return f"{self._build_player_base_url()}/api/player?stream_url={encoded_stream_url}&stream_type={stream_type}"

    def _is_embedded_webview_supported(self) -> bool:
        page = getattr(self.app, "page", None)
        if getattr(page, "web", False):
            return True

        platform = getattr(page, "platform", None)
        platform_value = getattr(platform, "value", platform)
        return platform_value in self.SUPPORTED_WEBVIEW_PLATFORMS

    @staticmethod
    def _get_webview_class():
        try:
            from flet_webview import WebView

            return WebView
        except ImportError:
            return getattr(ft, "WebView", None)

    def _create_webview_control(self, player_url: str):
        if not self._is_embedded_webview_supported():
            return None

        webview_cls = self._get_webview_class()
        if webview_cls is None:
            return None

        try:
            return webview_cls(url=player_url, expand=True)
        except Exception as e:
            logger.debug(f"Create WebView failed, fallback to browser preview: {e}")
            return None

    async def preview_stream(self, recording: Recording):
        stream_url = recording.preview_url
        if not stream_url:
            await self.app.snack_bar.show_snack_bar(self._["cannot_get_preview_url"])
            return

        stream_type = self._detect_stream_type(stream_url)
        if not stream_type:
            await self.app.snack_bar.show_snack_bar(self._["unsupported_format"])
            return

        player_url = self._build_player_url(stream_url, stream_type)
        webview = self._create_webview_control(player_url)

        if webview is None:
            await self.app.page.launch_url(player_url, web_popup_window_name=ft.UrlTarget.BLANK)
            await self.app.snack_bar.show_snack_bar(self._["embedded_preview_unavailable"])
            return

        def close_dialog(_):
            dialog.open = False
            self.app.dialog_area.update()

        async def copy_stream_url(_):
            await ft.Clipboard().set(stream_url)
            await self.app.snack_bar.show_snack_bar(self._["stream_url_copied"])

        async def open_in_new_tab(_):
            await self.app.page.launch_url(player_url, web_popup_window_name=ft.UrlTarget.BLANK)

        async def open_live_room(_):
            if recording.url:
                await self.app.page.launch_url(recording.url, web_popup_window_name=ft.UrlTarget.BLANK)

        is_mobile = self.app.is_mobile
        page_width = self.app.page.width or 800
        page_height = self.app.page.height or 600
        dialog_width = page_width * 0.92 if is_mobile else min(page_width * 0.82, 1200)
        player_height = page_height * 0.52 if is_mobile else min(page_height * 0.65, 680)
        quality_text = self._.get(recording.quality, recording.quality) if recording.quality else ""
        meta_parts = [
            part
            for part in [
                recording.streamer_name,
                recording.platform,
                f"{stream_type.upper()} {quality_text}".strip(),
            ]
            if part
        ]

        info_controls = [
            ft.Text(
                " · ".join(meta_parts),
                size=12 if is_mobile else 13,
                max_lines=1 if is_mobile else 2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        ]
        if recording.live_title:
            info_controls.append(
                ft.Text(
                    recording.live_title,
                    size=11 if is_mobile else 12,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color=ft.Colors.GREY_600,
                )
            )

        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text(self._["preview_title"]),
            content=ft.Container(
                width=dialog_width,
                content=ft.Column(
                    [
                        ft.Column(info_controls, spacing=4, tight=True),
                        ft.Container(
                            content=webview,
                            width=dialog_width,
                            height=player_height,
                            border_radius=8,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        ),
                    ],
                    spacing=10,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton(self._["copy_stream_url"], on_click=copy_stream_url),
                ft.TextButton(self._["open_live_room"], on_click=open_live_room),
                ft.TextButton(self._["open_in_new_tab"], on_click=open_in_new_tab),
                ft.TextButton(self._["close"], on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dialog.open = True
        self.app.dialog_area.content = dialog
        self.app.dialog_area.update()
