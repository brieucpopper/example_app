import flet as ft
import os
from datetime import datetime
from PIL import Image
import pandas as pd
import cv2
import numpy as np
import shutil
from .components.app_bar import create_app_bar
import json

# Global state for analysis persistence (in-memory)
_GLOBAL_ANALYSIS_STATE = {
    "frames_data": [],
    "red_frame_index": -1,
    "green_frame_index": -1
}
_ANALYSIS_STATE_PATH = "storage/analysis_state.json"



def load_analysis_state():
    """Load analysis session from disk if present."""
    if os.path.exists(_ANALYSIS_STATE_PATH):
        with open(_ANALYSIS_STATE_PATH, "r") as f:
            try:
                data = json.load(f)
                return (
                    data.get("frames_data", []),
                    data.get("red_frame_index", -1),
                    data.get("green_frame_index", -1),
                )
            except Exception:
                return [], -1, -1
    return [], -1, -1

class AnalysisView(ft.View):
    def __init__(self, detail_id=None, settings=None):
        self.detail_id = detail_id
        route = f"/analysis/{detail_id}" if detail_id is not None else "/analysis"
        super().__init__(route=route)
        self.history_file = "storage/history.csv"
        self.model_path = f"./assets/model.onnx"  # works on android
        
        # --- App State ---
        self.frames_data = []  # list of frame dicts
        self.red_frame_index: int = -1
        self.green_frame_index: int = -1
        self.selected_frame_data = None
        self.confirmed: bool = True  # Set True after user presses "Confirm", set to false once adding vid
        self.current_video_path: str | None = None
        self.settings = settings
        self.fps = str(settings.get_fps()) if settings else "30.0"  # Default to 30 if no settings
        # Will be loaded in did_mount

        if not os.path.exists(self.model_path):
            self.model_path = "C:\\Users\\apo\\Documents\\example_app\\src\\assets\\model.onnx"

        # Initialize OpenCV DNN model
        if os.path.exists(self.model_path):
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
        else:
            self.net = None
            print(f"Warning: ONNX model not found at {self.model_path}")
        
        os.makedirs("storage/thumbnails", exist_ok=True)
        os.makedirs("storage/sessions", exist_ok=True)
        if not os.path.exists(self.history_file):
            pd.DataFrame(columns=["date", "filename", "width", "height", "thumbnail", "jump_time"]).to_csv(self.history_file, index=False)
        
        # --- UI Controls Initialization ---
        
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
        
        self.pick_files_dialog = ft.FilePicker(on_result=self.process_video)
        
        self.select_video_button = ft.Container(
            content=ft.ElevatedButton(
                "Select Video",
                icon=ft.Icons.VIDEO_LIBRARY,
                style=ft.ButtonStyle(
                    padding=ft.padding.all(20),
                    icon_size=24,
                ),
                on_click=lambda _: self.pick_files_dialog.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["mp4", "mov", "avi", "mkv"]
                )
            ),
            width=float("inf"),
        )
        
        self.progress_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Processing video..."),
                    ft.ProgressBar(width=400, value=0),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            visible=False,
            alignment=ft.alignment.center,
        )
        
        # Grid that shows all frames
        self.results_grid = ft.GridView(
            expand=1,
            runs_count=5,
            max_extent=150,
            child_aspect_ratio=1.0,
            spacing=5,
            run_spacing=5,
        )

        # ---------- Detail overlay (transparent) ----------
        self.overlay_image = ft.Image(fit=ft.ImageFit.CONTAIN)
        self.overlay_red_btn = ft.ElevatedButton("Set TAKEOFF (red)", icon=ft.Icons.FLAG, on_click=lambda e: self.set_red(self.selected_frame_data) if self.selected_frame_data else None)
        self.overlay_green_btn = ft.ElevatedButton("Set LANDING (green)", icon=ft.Icons.FLAG_OUTLINED, on_click=lambda e: self.set_green(self.selected_frame_data) if self.selected_frame_data else None)
        
        # Bigger close button with custom style
        self.overlay_close_btn = ft.IconButton(
            ft.Icons.CLOSE,
            icon_size=48,  # Much bigger icon
            style=ft.ButtonStyle(
                padding=ft.padding.all(20),  # More padding around the icon
                bgcolor={"": ft.Colors.with_opacity(0.5, ft.Colors.BLACK)},  # Semi-transparent background
                shape=ft.CircleBorder(),  # Circular button
            ),
            on_click=lambda e: self.close_detail()
        )

        # Navigation button style
        nav_button_style = ft.ButtonStyle(
            padding=ft.padding.all(20),
            bgcolor={"": ft.Colors.with_opacity(0.5, ft.Colors.BLACK)},
            shape=ft.CircleBorder(),
        )

        # Navigation buttons - single frame
        self.overlay_prev_btn = ft.IconButton(
            ft.Icons.ARROW_LEFT,
            icon_size=48,
            style=nav_button_style,
            on_click=lambda e: self.navigate_frame(-1)
        )

        self.overlay_next_btn = ft.IconButton(
            ft.Icons.ARROW_RIGHT,
            icon_size=48,
            style=nav_button_style,
            on_click=lambda e: self.navigate_frame(1)
        )

        # Navigation buttons - fast (fps/10 frames)
        self.overlay_fast_prev_btn = ft.IconButton(
            ft.Icons.FAST_REWIND,
            icon_size=48,
            style=nav_button_style,
            on_click=lambda e: self.navigate_frame(-max(1, int(float(self.fps)/10)))
        )

        self.overlay_fast_next_btn = ft.IconButton(
            ft.Icons.FAST_FORWARD,
            icon_size=48,
            style=nav_button_style,
            on_click=lambda e: self.navigate_frame(max(1, int(float(self.fps)/10)))
        )

        # Create columns for navigation buttons that will be positioned on either side of the image
        self.nav_left_col = ft.Column(
            [self.overlay_fast_prev_btn, self.overlay_prev_btn],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        self.nav_right_col = ft.Column(
            [self.overlay_fast_next_btn, self.overlay_next_btn],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Create a row with navigation buttons on either side
        self.nav_row = ft.Row(
            [self.nav_left_col, self.overlay_image, self.nav_right_col],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

        self.overlay_container = ft.Container(
            visible=False,
            bgcolor="#AA000000",  # semi-transparent black
            alignment=ft.alignment.center,
            content=ft.Column(
                [
                    ft.Row([self.overlay_close_btn], alignment=ft.MainAxisAlignment.END),  # Close button in top-right
                    self.nav_row,  # Navigation row with image
                    ft.Row([self.overlay_red_btn, self.overlay_green_btn], alignment=ft.MainAxisAlignment.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
                expand=True,
            ),
        )

        # Stack with only grid in normal layout
        self.results_stack = ft.Stack([
            self.results_grid,
        ])

        # Confirm button shown under the grid
        self.confirm_button = ft.ElevatedButton(
            f"Confirm ({self.fps} FPS)",
            icon=ft.Icons.CHECK,
            on_click=lambda _: self.exit_view(save_to_history=True),
            disabled=True,
        )
        
        # Layout: grid fills remaining space; Confirm pinned at bottom
        self.results_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=self.results_stack, expand=True),  # scrollable area for grid
                    self.confirm_button,
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            visible=False,
            expand=True,
        )
        
    def did_mount(self):
        """Called when the view is mounted to the page."""
        self.page.overlay.append(self.pick_files_dialog)
        # Load persisted state if any
        self.frames_data, self.red_frame_index, self.green_frame_index = load_analysis_state()
        self.controls.clear()
        if self.detail_id is not None:
            # If detail_id is provided, show the detail view directly
            try:
                frame_index = int(self.detail_id)
                if self.frames_data and 0 <= frame_index < len(self.frames_data):
                    frame_data = self.frames_data[frame_index]
                    red_btn = ft.ElevatedButton(
                        text="Set RED",
                        icon=ft.Icons.FLAG,
                        on_click=lambda _, fd=frame_data: self.set_red(fd),
                    )
                    green_btn = ft.ElevatedButton(
                        text="Set GREEN",
                        icon=ft.Icons.FLAG_OUTLINED,
                        on_click=lambda _, fd=frame_data: self.set_green(fd),
                    )
                    self.controls.append(
                        ft.Column(
                            [
                                ft.Text(f"Score: {frame_data['score']:.4f}", size=20),
                                ft.Image(
                                    src=frame_data["path"],
                                    fit=ft.ImageFit.CONTAIN,
                                    width=self.page.window_width * 0.9,
                                    height=self.page.window_height * 0.6,
                                ),
                                ft.Row([red_btn, green_btn], alignment=ft.MainAxisAlignment.CENTER),
                            ],
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True,
                        )
                    )
                else:
                    self.controls.append(ft.Text(f"Detail for frame {self.detail_id} not available."))
            except Exception as e:
                self.controls.append(ft.Text(f"Invalid detail id: {self.detail_id}"))
        else:
            self.controls.append(
                ft.Column(
                    [
                        # Removed: create_app_bar(self.page, "Analysis"),
                        self.success_container,
                        self.select_video_button,
                        self.progress_container,
                        self.results_container,
                    ],
                    expand=True,
                    spacing=20
                )
            )
        self.page.update()

    def will_unmount(self):
        """Called when the view is unmounted from the page."""
        self.page.overlay.remove(self.pick_files_dialog)
        self.page.update()

    def run_inference(self, img):
        self.confirmed = False
        if self.net is None:
            return 0.0 # Return a default float value
            
        img_resized = img.convert("RGB").resize((224, 224))
        img_array = np.array(img_resized).astype(np.float32)
        blob = cv2.dnn.blobFromImage(img_array, 1.0/255.0, (224, 224), swapRB=True)
        
        try:
            self.net.setInput(blob)
            output = self.net.forward()
            return float(output[0][0])
        except Exception as e:
            print(f"Inference error: {e}")
            return 0.0 # Return a default float value

    def show_success_message(self, width, height, jump_time: float,jump_height: float):
        """Show success message with analysis results.
        
        Args:
            width: Video width
            height: Video height
            jump_time: Time in seconds
        """
        ms = int(jump_time * 1000)  # Convert to milliseconds
        message = f"Video analyzed: {width}x{height}\nTime: {ms} ms | Height: {int(jump_height*100)} cm"
        self.success_container.content.controls[1].value = message
        self.success_container.visible = True
        self.update()
        
    def hide_success_message(self):
        self.success_container.visible = False
        self.update()

    def process_video(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return

        self.select_video_button.visible = False
        self.progress_container.visible = True
        self.results_container.visible = False
        self.success_container.visible = False
        self.frames_data.clear()
        self.red_frame_index = -1
        self.green_frame_index = -1
        self.confirmed = False
        self.current_video_path = None
        self.update()

        video_path = e.files[0].path
        self.current_video_path = video_path
        
        session_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        frames_dir = f"storage/sessions/{session_ts}"
        os.makedirs(frames_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Use a local list for processing, then assign to self.frames_data
        local_frames_data = []

        if frame_count > 0:
            for i in range(frame_count):
                ret, frame = cap.read()
                if not ret:
                    break
                
                self.progress_container.content.controls[1].value = i / frame_count
                self.update()

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                inference_value = self.run_inference(pil_img)
                
                frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
                cv2.imwrite(frame_path, frame)
                
                local_frames_data.append({"index": i, "path": frame_path, "score": inference_value})

        cap.release()
        
        self.frames_data = local_frames_data
        
        self.progress_container.visible = False
        self.select_video_button.visible = True

        if self.frames_data:
            # Determine initial red & green frames based on lowest/highest score
            sorted_by_score = sorted(self.frames_data, key=lambda x: x["score"])
            self.red_frame_index = sorted_by_score[0]["index"]
            self.green_frame_index = sorted_by_score[-1]["index"]

            self.display_results_grid()
        
        self.update()

    def display_results_grid(self):
        self.results_grid.controls.clear()
        for frame_data in sorted(self.frames_data, key=lambda x: x["index"]):
            idx = frame_data["index"]
            border_style = None
            if idx == self.red_frame_index:
                border_style = ft.border.all(3, ft.Colors.RED_400)
            elif idx == self.green_frame_index:
                border_style = ft.border.all(3, ft.Colors.GREEN_400)

            container = ft.Container(
                content=ft.Image(src=frame_data["path"]),
                border=border_style,
                border_radius=ft.border_radius.all(5),
                on_click=lambda _, fd=frame_data: self.open_detail(fd),
                tooltip=f"Frame {frame_data['index']}\nScore: {frame_data['score']:.4f}"
            )
            self.results_grid.controls.append(container)

        # Enable confirm button only if both frames selected and different
        self.confirm_button.disabled = (
            self.red_frame_index == -1
            or self.green_frame_index == -1
            or self.red_frame_index == self.green_frame_index
        )
        self.results_container.visible = True

    # ---------- Overlay helpers ----------
    def open_detail(self, frame_data):
        """Show transparent overlay with enlarged frame and buttons."""
        self.selected_frame_data = frame_data
        self.overlay_image.src = frame_data["path"]
        self.overlay_image.width = self.page.window_width * 0.9
        self.overlay_image.height = self.page.window_height * 0.6
        if self.overlay_container not in self.page.overlay:
            self.page.overlay.append(self.overlay_container)
        self.overlay_container.visible = True
        self.page.update()

    def close_detail(self):
        if self.overlay_container in self.page.overlay:
            self.page.overlay.remove(self.overlay_container)
        self.overlay_container.visible = False
        self.page.update()

    # Removed legacy toggle_highlight method

    # --- Frame assignment helpers ---
    def set_red(self, frame_data):
        self.red_frame_index = frame_data["index"]
        self.display_results_grid()
        self.update()
        self.close_detail()

    def set_green(self, frame_data):
        self.green_frame_index = frame_data["index"]
        self.display_results_grid()
        self.update()
        self.close_detail()

    # No longer needed with overlay approach
    def _navigate_back_to_grid(self):
        pass

    def navigate_frame(self, direction: int):
        """Navigate frames in the specified direction.
        
        Args:
            direction: Number of frames to move (positive for forward, negative for backward)
        """
        if not self.frames_data or not self.selected_frame_data:
            return
            
        # Get sorted list of frames by index
        sorted_frames = sorted(self.frames_data, key=lambda x: x["index"])
        current_idx = self.selected_frame_data["index"]
        
        # Find the current frame's position in the sorted list
        current_pos = 0
        for i, frame in enumerate(sorted_frames):
            if frame["index"] == current_idx:
                current_pos = i
                break
        
        # Calculate new position without wrapping
        new_pos = current_pos + direction
        
        # Clamp to valid range
        new_pos = max(0, min(new_pos, len(sorted_frames) - 1))
        
        # Only update if position changed
        if new_pos != current_pos:
            next_frame = sorted_frames[new_pos]
            self.selected_frame_data = next_frame
            self.overlay_image.src = next_frame["path"]
            self.overlay_image.width = self.page.window_width * 0.9
            self.overlay_image.height = self.page.window_height * 0.6
            self.page.update()
    def calculate_height(self, jump_time):
        """Calculate jump height using the formula: h = 1/8 * 9.81 * t^2"""
        return (1/8) * 9.81 * (jump_time ** 2)
    # --- Confirmation workflow ---
    def exit_view(self,save_to_history):
        self.close_detail()
        frame_count = abs(self.green_frame_index - self.red_frame_index)
        jump_time = frame_count * 1/float(self.fps)
        jump_height = self.calculate_height(jump_time)
        if save_to_history:
            self.save_video_to_history(self.current_video_path, jump_time, jump_height)
        self.confirmed = True
        self.confirm_button.disabled = True
        self.update()

    def save_video_to_history(self, video_path: str, jump_time: float, jump_height: float):
        """Persist analysed video metadata & time to history CSV."""
        if not os.path.exists(video_path):
            return

        # Select middle frame for thumbnail
        middle_idx = len(self.frames_data) // 2
        middle_frame_path = self.frames_data[middle_idx]["path"] if self.frames_data else None
        if middle_frame_path is None:
            return

        thumbnail_name = f"{os.path.splitext(os.path.basename(video_path))[0]}_{datetime.now().strftime('%H%M%S')}.jpg"
        thumbnail_path = os.path.join("storage/thumbnails", thumbnail_name)
        shutil.copyfile(middle_frame_path, thumbnail_path)

        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        df = pd.read_csv(self.history_file)
        new_row = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filename": os.path.basename(video_path),
            "width": width,
            "height": height,
            "thumbnail": thumbnail_name,
            "jump_time": jump_time,
            "jump_height": jump_height,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.history_file, index=False)

        self.show_success_message(width, height, jump_time, jump_height) 