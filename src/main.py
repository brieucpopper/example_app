import flet as ft
import os
from datetime import datetime
from PIL import Image
import pandas as pd
import json
import cv2
import numpy as np

class Settings:
    def __init__(self):
        self.config_file = "storage/settings.json"
        self._load_settings()

    def _load_settings(self):
        os.makedirs("storage", exist_ok=True)
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                self.settings = json.load(f)
        else:
            self.settings = {"default_fps": 30.0}
            self._save_settings()

    def _save_settings(self):
        with open(self.config_file, "w") as f:
            json.dump(self.settings, f)

    def get_fps(self):
        return self.settings.get("default_fps", 30.0)

    def set_fps(self, value):
        self.settings["default_fps"] = value
        self._save_settings()

class SettingsView(ft.View):
    def __init__(self, settings, route="/settings"):
        super().__init__(route=route)
        self.settings = settings
        self.fps_field = ft.TextField(
            label="Default FPS",
            value=str(self.settings.get_fps()),
            width=200,
            on_submit=self.save_settings
        )
        self.controls = [
            ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                on_click=lambda _: self.page.go("/")
                            ),
                            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row([ft.Text("Default FPS:"), self.fps_field]),
                ],
                spacing=20,
            )
        ]

    def save_settings(self, e):
        try:
            fps = float(self.fps_field.value)
            self.settings.set_fps(fps)
            self.fps_field.error_text = None
        except ValueError:
            self.fps_field.error_text = "Please enter a valid number"
        self.update()

class AnalysisView(ft.View):
    def __init__(self, route="/analysis"):
        super().__init__(route=route)
        self.history_file = "storage/history.csv"
        self.model_path = "storage/model.onnx"
        
        # Initialize OpenCV DNN model
        if os.path.exists(self.model_path):
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
        else:
            self.net = None
            print(f"Warning: ONNX model not found at {self.model_path}")
        
        os.makedirs("storage/thumbnails", exist_ok=True)
        if not os.path.exists(self.history_file):
            pd.DataFrame(columns=["date", "filename", "width", "height", "thumbnail", "inference_value"]).to_csv(self.history_file, index=False)
        
        self.pick_files_dialog = ft.FilePicker(
            on_result=self.process_image
        )
        
        # Success message container
        self.success_container = ft.Container(
            visible=False,
            bgcolor=ft.Colors.GREEN_100,
            border_radius=10,
            padding=10,
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                    ft.Text("", color=ft.Colors.GREEN_900, size=16, weight=ft.FontWeight.W_500),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=ft.Colors.GREEN_900,
                        on_click=lambda _: self.hide_success_message()
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        
        self.controls = [
            ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                on_click=lambda _: self.page.go("/")
                            ),
                            ft.Text("Analysis", size=30, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    self.success_container,
                    ft.ElevatedButton(
                        "Select Image",
                        icon=ft.Icons.IMAGE,
                        on_click=lambda _: self.pick_files_dialog.pick_files(
                            allow_multiple=False,
                            allowed_extensions=["png", "jpg", "jpeg"]
                        )
                    ),
                    self.pick_files_dialog,
                ],
                spacing=20,
            )
        ]

    def run_inference(self, img):
        if self.net is None:
            return 'no net'
            
        # Preprocess image - assuming model expects (1, 3, 224, 224) input
        img_resized = img.convert("RGB").resize((224, 224))
        img_array = np.array(img_resized).astype(np.float32)
        
        # Convert to blob for OpenCV DNN
        blob = cv2.dnn.blobFromImage(img_array, 1.0/255.0, (224, 224), swapRB=True)
        
        # Run inference
        try:
            self.net.setInput(blob)
            output = self.net.forward()
            return float(output[0][0])  # Assuming single output value
        except Exception as e:
            print(f"Inference error: {e}")
            # return string version of the error
            return str(e)

    def show_success_message(self, width, height, inference_value=None):
        message = f"Image analyzed successfully: {width}x{height}"
        if inference_value is not None:
            message += f"\nInference value: {inference_value}"
        self.success_container.content.controls[1].value = message
        self.success_container.visible = True
        self.update()
        
    def hide_success_message(self):
        self.success_container.visible = False
        self.update()

    def process_image(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return

        file_path = e.files[0].path
        with Image.open(file_path) as img:
            width, height = img.size
            
            # Run inference
            inference_value = self.run_inference(img)
            
            # Create thumbnail
            thumbnail_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            thumbnail_path = f"storage/thumbnails/{thumbnail_name}"
            img.thumbnail((100, 100))
            img.save(thumbnail_path)

            # Save to history
            df = pd.read_csv(self.history_file)
            new_row = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "filename": os.path.basename(file_path),
                "width": width,
                "height": height,
                "thumbnail": thumbnail_name,
                "inference_value": inference_value if inference_value is not None else "N/A"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(self.history_file, index=False)

            # Show success message
            self.show_success_message(width, height, inference_value)

class HistoryView(ft.View):
    def __init__(self, route="/history"):
        super().__init__(route=route)
        self.history_file = "storage/history.csv"
        self.update_history_list()

    def update_history_list(self):
        history_items = []
        if os.path.exists(self.history_file):
            df = pd.read_csv(self.history_file)
            for _, row in df.iterrows():
                inference_text = f"Inference: {row['inference_value']}" if row['inference_value'] != "N/A" else "No inference"
                history_items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Image(
                                    src=f"storage/thumbnails/{row['thumbnail']}",
                                    width=50,
                                    height=50,
                                    fit=ft.ImageFit.CONTAIN,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(row["filename"]),
                                        ft.Text(f"Resolution: {row['width']}x{row['height']}"),
                                        ft.Text(inference_text),
                                        ft.Text(row["date"], size=12),
                                    ],
                                ),
                            ],
                        ),
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=10,
                        padding=10,
                        margin=ft.margin.only(bottom=10),
                    )
                )

        self.controls = [
            ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                on_click=lambda _: self.page.go("/")
                            ),
                            ft.Text("History", size=30, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.ListView(
                        controls=history_items,
                        spacing=10,
                        height=400,
                        width=400,
                    ),
                ],
                spacing=20,
            )
        ]

class HomeView(ft.View):
    def __init__(self, route="/"):
        super().__init__(route=route)
        self.controls = [
            ft.Column(
                controls=[
                    ft.Text("Jump Analysis", size=40, weight=ft.FontWeight.BOLD),
                    ft.Text("Welcome to Jump Analysis!", size=20),
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
                                        width=400,
                                        on_click=lambda _: self.page.go("/settings")
                                    ),
                                    margin=ft.margin.only(top=10),
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
                                        width=400,
                                        on_click=lambda _: self.page.go("/analysis")
                                    ),
                                    margin=ft.margin.only(top=10),
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
                                        width=400,
                                        on_click=lambda _: self.page.go("/history")
                                    ),
                                    margin=ft.margin.only(top=10),
                                ),
                            ],
                            spacing=10,
                        ),
                        margin=ft.margin.only(top=20),
                    ),
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ]

def main(page: ft.Page):
    page.title = "Jump Analysis"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 800
    page.window_height = 600
    
    # Initialize settings
    settings = Settings()
    
    # Initialize views
    home_view = HomeView()
    settings_view = SettingsView(settings)
    analysis_view = AnalysisView()
    history_view = HistoryView()

    def route_change(route):
        page.views.clear()
        
        if page.route == "/":
            page.views.append(home_view)
            page.navigation_rail.selected_index = 0
        elif page.route == "/settings":
            page.views.append(settings_view)
            page.navigation_rail.selected_index = 1
        elif page.route == "/analysis":
            page.views.append(analysis_view)
            page.navigation_rail.selected_index = 2
        elif page.route == "/history":
            history_view.update_history_list()  # Refresh history when navigating to it
            page.views.append(history_view)
            page.navigation_rail.selected_index = 3
        
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        top_view.visible = True
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Navigation rail
    page.navigation_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=400,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME,
                selected_icon=ft.Icons.HOME,
                label="Home",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ANALYTICS,
                selected_icon=ft.Icons.ANALYTICS,
                label="Analysis",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HISTORY,
                selected_icon=ft.Icons.HISTORY,
                label="History",
            ),
        ],
        on_change=lambda e: page.go(
            ["/", "/settings", "/analysis", "/history"][e.control.selected_index]
        ),
    )

    # Go to initial route
    page.go("/")

ft.app(target=main)
