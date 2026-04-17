import flet as ft


class PopupColorItem(ft.PopupMenuItem):
    def __init__(self, color, name):
        super().__init__()
        self.content = ft.Row(
            controls=[
                ft.Icon(name=ft.Icons.COLOR_LENS_OUTLINED, color=color),
                ft.Text(name),
            ],
        )
        self.on_click = lambda e: self.seed_color_changed(e)
        self.data = color

    def seed_color_changed(self, e):
        page = e.page
        page.theme.color_scheme_seed = self.data
        page.theme.color_scheme = ft.ColorScheme(primary=self.data)
        page.update()
        self.save_theme_color(e)

    def save_theme_color(self, e):
        page = e.page
        app = page.data
        app.settings.user_config["theme_color"] = self.data
        page.run_task(app.config_manager.save_user_config, app.settings.user_config)


def _create_text_style(color: str, custom_font: str | None) -> ft.TextStyle:
    if custom_font:
        return ft.TextStyle(color=color, font_family=custom_font)
    return ft.TextStyle(color=color)


def _create_text_theme(color: str, custom_font: str | None) -> ft.TextTheme:
    return ft.TextTheme(
        body_medium=_create_text_style(color, custom_font),
        body_large=_create_text_style(color, custom_font),
        display_small=_create_text_style(color, custom_font),
        display_medium=_create_text_style(color, custom_font),
        display_large=_create_text_style(color, custom_font),
        headline_small=_create_text_style(color, custom_font),
        headline_medium=_create_text_style(color, custom_font),
        headline_large=_create_text_style(color, custom_font),
        title_small=_create_text_style(color, custom_font),
        title_medium=_create_text_style(color, custom_font),
        title_large=_create_text_style(color, custom_font),
        label_small=_create_text_style(color, custom_font),
        label_medium=_create_text_style(color, custom_font),
        label_large=_create_text_style(color, custom_font),
    )


def create_light_theme(custom_font: str | None) -> ft.Theme:
    """Define light colored theme"""
    theme_kwargs = {
        "text_theme": _create_text_theme(ft.Colors.BLACK, custom_font),
    }
    if custom_font:
        theme_kwargs["font_family"] = custom_font
    return ft.Theme(**theme_kwargs)


def create_dark_theme(custom_font: str | None) -> ft.Theme:
    """Define dark theme"""
    theme_kwargs = {
        "text_theme": _create_text_theme(ft.Colors.WHITE, custom_font),
    }
    if custom_font:
        theme_kwargs["font_family"] = custom_font
    return ft.Theme(**theme_kwargs)
