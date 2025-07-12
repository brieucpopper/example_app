import flet as ft
from .components.app_bar import create_app_bar

class SettingsView(ft.View):
    def __init__(self, settings):
        super().__init__(route="/settings")
        self.settings = settings
        self.fps_field = ft.TextField(
            label="FPS",
            value=str(self.settings.get_fps()),
            width=float("inf"),
            height=60,
            text_size=16,
            on_submit=self.save_settings
        )

    def did_mount(self):
        self.controls = [
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Default FPS:", size=16, weight=ft.FontWeight.W_500),
                                self.fps_field,
                            ],
                            spacing=10,
                        ),
                        padding=ft.padding.all(20),
                        
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=10,
                        width=float("inf"),
                    ),
                ],
                spacing=20,
                width=float("inf"),
            )
        ]
        self.update()

    def save_settings(self, e):
        try:
            fps = float(self.fps_field.value)
            self.settings.set_fps(fps)
            self.fps_field.error_text = None
        except ValueError:
            self.fps_field.error_text = "Please enter a valid number"
        self.update() 