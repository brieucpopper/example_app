import flet as ft
import os
import pandas as pd
from .components.app_bar import create_app_bar

class HistoryView(ft.View):
    def __init__(self):
        super().__init__(route="/history")
        self.history_file = "storage/history.csv"
        
    def update_history_list(self):
        history_items = []
        if os.path.exists(self.history_file):
            df = pd.read_csv(self.history_file)
            for _, row in df.iterrows():
                if 'jump_time' in row and not pd.isna(row['jump_time']):
                    # Convert seconds to milliseconds and format
                    ms = int(row['jump_time'] * 1000)
                    height = int(row['jump_height']*100)
                    delta_text = f"Time: {ms} ms | Height: {height} cm"
                else:
                    delta_text = "No data"
                history_items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Image(
                                    src=f"storage/thumbnails/{row['thumbnail']}",
                                    width=60,
                                    height=60,
                                    fit=ft.ImageFit.CONTAIN,
                                    border_radius=ft.border_radius.all(8),
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(row["filename"], size=16, weight=ft.FontWeight.W_500),
                                        ft.Text(f"Resolution: {row['width']}x{row['height']}", size=14),
                                        ft.Text(delta_text, size=14),
                                        ft.Text(row["date"], size=12, color=ft.Colors.GREY_400),
                                    ],
                                    spacing=4,
                                    expand=True,
                                ),
                            ],
                            spacing=15,
                        ),
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=10,
                        padding=15,
                        margin=ft.margin.only(bottom=10),
                    )
                )

        # Create a scrollable view with fixed height
        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        # Removed: create_app_bar(self.page, "History"),
                        ft.Container(
                            content=ft.ListView(
                                controls=history_items,
                                spacing=10,
                                padding=10,
                                expand=True,
                            ),
                            expand=True,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=10,
                            padding=10,
                        ),
                    ],
                    spacing=20,
                    expand=True,
                ),
                expand=True,
            )
        ]
        self.update()

    def did_mount(self):
        self.update_history_list() 