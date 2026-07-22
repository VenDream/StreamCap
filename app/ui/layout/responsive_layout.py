import flet as ft

from ...app_manager import App
from ...utils.logger import logger


def is_mobile_device(page: ft.Page) -> bool:
    viewport_width = page.width or getattr(page.window, "width", 0) or 0
    if viewport_width <= 0:
        return False
    return viewport_width < 768


def setup_responsive_layout(page: ft.Page, app: App) -> None:
    _ = app.language_manager.language.get("sidebar", {})
    is_mobile = is_mobile_device(page)

    if app.is_mobile == is_mobile and app.complete_page.content is not None:
        return

    if is_mobile:
        logger.info("mobile device detected, enable mobile layout")
        app.is_mobile = True
        app.left_navigation_menu.width = 0
        app.left_navigation_menu.visible = False

        app.bottom_navigation = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label=_["home"]),
                ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_ROUNDED, label=_["recordings"]),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label=_["settings"]),
                ft.NavigationBarDestination(icon=ft.Icons.DRIVE_FILE_MOVE, label=_["storage"]),
                ft.NavigationBarDestination(icon=ft.Icons.INFO, label=_["about"]),
            ],
            on_change=lambda e: page.go(
                f"/{['home', 'recordings', 'settings', 'storage', 'about'][e.control.selected_index]}"
            ),
        )

        app.content_area.expand = True

        layout = ft.Column(
            expand=True,
            spacing=0,
            controls=[app.content_area, app.bottom_navigation, app.dialog_area, app.snack_bar_area],
        )
    else:
        logger.info("desktop device detected, enable desktop layout")
        app.is_mobile = False
        app.left_navigation_menu.width = 192
        app.left_navigation_menu.visible = True
        layout = ft.Row(
            expand=True,
            controls=[
                app.left_navigation_menu,
                ft.VerticalDivider(width=1),
                app.content_area,
                app.dialog_area,
                app.snack_bar_area,
            ],
        )

    app.complete_page.content = layout
