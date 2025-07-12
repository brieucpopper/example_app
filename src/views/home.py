import flet as ft

class HomeView(ft.View):
    def __init__(self):
        super().__init__(route="/")
        
    def did_mount(self):
        self.controls = [
            ft.Column(
                controls=[
                    ft.Text("Welcome to Jump Analysis!", size=18),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Quick Start:", size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(
                                    content=ft.ElevatedButton(
                                        content=ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.SETTINGS),
                                                ft.Text("Settings", size=16),
                                                ft.Text(" - Configure default FPS", size=14, color=ft.Colors.GREY_400),
                                            ],
                                        ),
                                        width=None,
                                        style=ft.ButtonStyle(
                                            padding=ft.padding.all(20),
                                            icon_size=24,
                                        ),
                                        on_click=lambda _: self.page.go("/settings")
                                    ),
                                    margin=ft.margin.only(top=10),
                                    width=float("inf"),
                                ),
                                ft.Container(
                                    content=ft.ElevatedButton(
                                        content=ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.ANALYTICS),
                                                ft.Text("Analysis", size=16),
                                                ft.Text(" - Analyze image resolution", size=14, color=ft.Colors.GREY_400),
                                            ],
                                        ),
                                        width=None,
                                        style=ft.ButtonStyle(
                                            padding=ft.padding.all(20),
                                            icon_size=24,
                                        ),
                                        on_click=lambda _: self.page.go("/analysis")
                                    ),
                                    margin=ft.margin.only(top=10),
                                    width=float("inf"),
                                ),
                                ft.Container(
                                    content=ft.ElevatedButton(
                                        content=ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.HISTORY),
                                                ft.Text("History", size=16),
                                                ft.Text(" - View previous analyses", size=14, color=ft.Colors.GREY_400),
                                            ],
                                        ),
                                        width=None,
                                        style=ft.ButtonStyle(
                                            padding=ft.padding.all(20),
                                            icon_size=24,
                                        ),
                                        on_click=lambda _: self.page.go("/history")
                                    ),
                                    margin=ft.margin.only(top=10),
                                    width=float("inf"),
                                ),
                            ],
                            spacing=10,
                        ),
                        margin=ft.margin.only(top=20),
                        padding=ft.padding.all(10),
                    ),
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=float("inf"),
            )
        ]
        self.update() 