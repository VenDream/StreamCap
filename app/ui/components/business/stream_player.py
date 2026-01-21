import os
import urllib.parse

import flet as ft

from ....models.recording.recording_model import Recording


class StreamPlayer:
    """支持 M3U8/FLV 格式的流媒体播放器"""

    def __init__(self, app):
        self.app = app
        self._ = {}
        self.load_language()

    def load_language(self):
        language = self.app.language_manager.language
        for key in ("stream_player", "base", "video_quality"):
            self._.update(language.get(key, {}))

    async def preview_stream(self, recording: Recording):
        """
        预览直播流
        :param recording: 录制对象，包含直播信息
        """
        stream_url = recording.preview_url
        if not stream_url:
            await self.app.snack_bar.show_snack_bar(
                self._.get("cannot_get_preview_url", "无法获取预览地址")
            )
            return

        # 检测流类型
        stream_type = None
        if '.m3u8' in stream_url.lower() or 'm3u8' in stream_url.lower():
            stream_type = "m3u8"
        elif '.flv' in stream_url.lower() or 'flv' in stream_url.lower():
            stream_type = "flv"

        if not stream_type:
            await self.app.snack_bar.show_snack_bar(
                self._.get("unsupported_format", "无法识别流格式，仅支持 M3U8 和 FLV 格式")
            )
            return

        # 获取 API 端口和主机地址
        video_api_port = os.getenv("VIDEO_API_PORT", "6007")
        page_url = self.app.page.url
        if page_url:
            parsed = urllib.parse.urlparse(page_url)
            host = parsed.hostname or "localhost"
        else:
            host = "localhost"

        # Video API 服务始终使用 http
        # 构建播放器 URL
        encoded_stream_url = urllib.parse.quote(stream_url, safe='')
        player_url = (
            f"http://{host}:{video_api_port}/api/player"
            f"?stream_url={encoded_stream_url}&stream_type={stream_type}"
        )

        # 创建对话框
        def close_dialog(_):
            dialog.open = False
            self.app.dialog_area.update()

        async def open_in_new_tab(_):
            self.app.page.launch_url(player_url)

        async def copy_source(_):
            self.app.page.set_clipboard(stream_url)
            await self.app.snack_bar.show_snack_bar(
                self._.get("stream_url_copied", "流地址已复制")
            )

        async def open_room(_):
            if recording.url:
                self.app.page.launch_url(recording.url)

        # 创建 WebView 组件
        webview = ft.WebView(
            url=player_url,
            expand=True,
        )

        is_mobile = self.app.is_mobile

        # 获取页面尺寸，使用类似 vh/vw 的百分比计算
        page_width = self.app.page.width or 800
        page_height = self.app.page.height or 600

        if is_mobile:
            # 移动端：90vw, 70vh
            dialog_width = page_width * 0.9
            video_height = page_height * 0.55
            info_font_size = 12
        else:
            # 桌面端：80vw (max 1200), 65vh (max 650)
            dialog_width = min(page_width * 0.8, 1200)
            video_height = min(page_height * 0.65, 650)
            info_font_size = 13

        # 构建直播信息 - 移动端使用更紧凑的单行显示
        # 获取清晰度翻译
        quality_text = self._.get(recording.quality, recording.quality) if recording.quality else ""
        format_with_quality = f"{stream_type.upper()} - {quality_text}" if quality_text else stream_type.upper()

        if is_mobile:
            # 移动端：单行紧凑信息（主播 · 平台 · 格式-清晰度）
            info_parts = []
            if recording.streamer_name:
                info_parts.append(recording.streamer_name)
            if recording.platform:
                info_parts.append(recording.platform)
            info_parts.append(format_with_quality)

            info_text = " · ".join(info_parts)

            # 如果有直播标题，显示在第二行
            if recording.live_title:
                info_column = ft.Column(
                    controls=[
                        ft.Text(
                            info_text,
                            size=info_font_size,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            recording.live_title,
                            size=info_font_size - 1,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=2,
                )
            else:
                info_column = ft.Container(
                    content=ft.Text(
                        info_text,
                        size=info_font_size,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    padding=ft.padding.only(bottom=5),
                )
        else:
            # 桌面端：两列式布局
            left_column_items = []
            right_column_items = []
            label_width = 70  # 固定 label 宽度，适配英文

            if recording.streamer_name:
                left_column_items.append(
                    ft.Row([
                        ft.Container(
                            content=ft.Text(
                                self._.get("streamer_label", "主播："),
                                weight=ft.FontWeight.BOLD,
                                size=info_font_size,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            width=label_width,
                            alignment=ft.alignment.center_right,
                        ),
                        ft.Text(recording.streamer_name, size=info_font_size),
                    ], spacing=5)
                )

            if recording.platform:
                left_column_items.append(
                    ft.Row([
                        ft.Container(
                            content=ft.Text(
                                self._.get("platform_label", "平台："),
                                weight=ft.FontWeight.BOLD,
                                size=info_font_size,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            width=label_width,
                            alignment=ft.alignment.center_right,
                        ),
                        ft.Text(recording.platform, size=info_font_size),
                    ], spacing=5)
                )

            right_column_items.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(
                            self._.get("format_label", "格式："),
                            weight=ft.FontWeight.BOLD,
                            size=info_font_size,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                        width=label_width,
                        alignment=ft.alignment.center_right,
                    ),
                    ft.Text(format_with_quality, size=info_font_size),
                ], spacing=5)
            )

            if recording.live_title:
                right_column_items.append(
                    ft.Row([
                        ft.Container(
                            content=ft.Text(
                                self._.get("title_label", "标题："),
                                weight=ft.FontWeight.BOLD,
                                size=info_font_size,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            width=label_width,
                            alignment=ft.alignment.center_right,
                        ),
                        ft.Text(
                            recording.live_title,
                            size=info_font_size,
                            expand=True,
                            no_wrap=False,
                        ),
                    ], spacing=5, expand=True)
                )

            # 两列布局
            two_column_row = ft.Row(
                controls=[
                    ft.Column(controls=left_column_items, spacing=5, expand=True),
                    ft.Column(controls=right_column_items, spacing=5, expand=True),
                ],
                spacing=20,
            )

            info_column = two_column_row

        # 内容区域：信息 + 视频（居中）
        content = ft.Column(
            controls=[
                ft.Container(
                    content=info_column,
                    alignment=ft.alignment.center_left if is_mobile else ft.alignment.center,
                ),
                ft.Container(
                    content=webview,
                    width=dialog_width,
                    height=video_height,
                    border_radius=5,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    margin=ft.margin.only(top=20),
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

        # 按钮 - 移动端使用图标按钮节省空间
        if is_mobile:
            actions = [
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    tooltip=self._.get("open_live_room", "打开直播间"),
                    on_click=open_room,
                ) if recording.url else ft.Container(),
                ft.IconButton(
                    icon=ft.Icons.CONTENT_COPY,
                    tooltip=self._.get("copy_stream_url", "复制流地址"),
                    on_click=copy_source,
                ),
                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    tooltip=self._.get("open_in_new_tab", "新标签打开"),
                    on_click=open_in_new_tab,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    tooltip=self._.get("close", "关闭"),
                    on_click=close_dialog,
                ),
            ]
            # 过滤掉空容器
            actions = [a for a in actions if not isinstance(a, ft.Container)]
        else:
            actions = [
                ft.TextButton(
                    self._.get("copy_stream_url", "复制流地址"),
                    on_click=copy_source
                ),
                ft.TextButton(
                    self._.get("open_in_new_tab", "新标签打开"),
                    on_click=open_in_new_tab
                ),
                ft.TextButton(
                    self._.get("close", "关闭"),
                    on_click=close_dialog
                )
            ]
            if recording.url:
                actions.insert(
                    0,
                    ft.TextButton(
                        self._.get("open_live_room", "打开直播间"),
                        on_click=open_room
                    )
                )

        def on_dismiss(_):
            dialog.open = False
            self.app.dialog_area.update()

        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text(
                self._.get("preview_title", "直播预览"),
                size=16 if is_mobile else 20
            ),
            content=content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
            inset_padding=ft.padding.all(10) if is_mobile else ft.padding.all(24),
            on_dismiss=on_dismiss,
        )

        dialog.open = True
        self.app.dialog_area.content = dialog
        self.app.dialog_area.update()
