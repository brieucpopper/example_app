import flet as ft
from views.home import HomeView
from views.analysis import AnalysisView
from views.history import HistoryView
from views.settings import SettingsView
from models.settings import Settings
import re
import os
import json
import cv2
import pandas as pd
from datetime import datetime
import shutil
from PIL import Image


def main(page: ft.Page):
    page.title = "Jump Flet"
    page.window_width = 400
    page.window_height = 800
    page.fonts = {
        "RobotoSlab": "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab%5Bwght%5D.ttf"
    }
    page.theme = ft.Theme(font_family="RobotoSlab")

    settings = Settings()

    # Route to view factory
    def get_view_for_route(route):
        if route == "/":
            return HomeView()
        elif route == "/analysis":
            return AnalysisView(settings=settings)
        elif route == "/history":
            return HistoryView()
        elif route == "/settings":
            return SettingsView(settings)
        # /analysis/<id> detail route
        m = re.match(r"^/analysis/(.+)$", route)
        if m:
            return AnalysisView(detail_id=m.group(1), settings=settings)
        return None

    # Simple app bar; confirmation handled in view_pop
    def make_app_bar(route, title):
        def on_back(e):
            page.on_view_pop(None)  # Trigger the same logic
        return ft.AppBar(
            leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=on_back),
            title=ft.Text(title),
        )

    # ---------- AlertDialogs (pattern from docs) ----------

    exit_dialog = ft.AlertDialog(modal=True)

    def open_exit_dialog():
        exit_dialog.title = ft.Text("Exit App?")
        exit_dialog.content = ft.Text("Are you sure you want to exit?")
        exit_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda e: close_exit_dialog()),
            ft.TextButton("Exit", on_click=lambda e: page.window.destroy()),
        ]
        page.dialog = exit_dialog
        exit_dialog.open = True
        page.open(exit_dialog)  # helper triggers update

    def close_exit_dialog():
        exit_dialog.open = False
        page.update()
    
    def window_close():
        page.window_close()

    discard_dialog = ft.AlertDialog(modal=True)

    def open_discard_dialog():
        discard_dialog.title = ft.Text("Discard analysis?")
        discard_dialog.content = ft.Text("Data will be erased if you leave without confirming.")
        discard_dialog.actions = [
            ft.TextButton("Stay", on_click=lambda e: close_discard_dialog()),
            ft.TextButton("Leave", on_click=lambda e: _discard_and_go_home()),
        ]
        def _discard_and_go_home():
            close_discard_dialog()
            #call analysis.exit_view(save_to_history=False)
            page.views[-1].exit_view(save_to_history=False)
            #call back button
            page.views[-1].appbar.leading.on_click(None)
        page.dialog = discard_dialog
        discard_dialog.open = True
        page.open(discard_dialog)

    def close_discard_dialog():
        discard_dialog.open = False
        page.update()

    # Navigation rail
    routes_list = ["/", "/analysis", "/history", "/settings"]
    page.navigation_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=200,
        extended=False,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.HOME, label="Home"),
            ft.NavigationRailDestination(icon=ft.Icons.ANALYTICS, label="Analysis"),
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY, label="History"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS, label="Settings"),
        ],
        on_change=lambda e: page.go(routes_list[e.control.selected_index]),
    )

    # Route change handler
    def route_change(e):
        print(f"[NAV] route_change -> {e.route}")
        route = e.route or "/"
        # Always clear the stack for any top-level route
        if route in routes_list:
            page.views.clear()
            view = get_view_for_route(route)
            view.appbar = make_app_bar(route, view.__class__.__name__.replace('View',''))
            page.views.append(view)
            # Sync navigation rail
            if route in routes_list:
                page.navigation_rail.selected_index = routes_list.index(route)
            page.update()
            return
        # For detail/sub-routes, append a new view if not already on top
        if not (page.views and page.views[-1].route == route):
            view = get_view_for_route(route)
            view.appbar = make_app_bar(route, "Analysis Detail")
            page.views.append(view)
        page.update()

    # View pop handler (back gesture)
    def view_pop(e):
        print(f"[NAV] view_pop called. stack size={len(page.views)} top={(page.views[-1].route if page.views else 'None')}")
        # If current view is Analysis root and unconfirmed, ask confirmation
        if page.views:
            current_view = page.views[-1]
            if (
                isinstance(current_view, AnalysisView)
                and current_view.detail_id is None
                and not current_view.confirmed
                and current_view.frames_data
            ):
                open_discard_dialog()
                return  # wait for dialog

        _do_pop()

    def _do_pop():
        print(f"[NAV] _do_pop before. stack size={len(page.views)} routes={[v.route for v in page.views]}")
        if len(page.views) > 1:
            # Standard pop of secondary view
            page.views.pop()
            print(f"[NAV] popped. stack -> {[v.route for v in page.views]}")
            page.go(page.views[-1].route)
            return

        # Single top-level view remaining
        print("[NAV] single top level", page.views[0].route if page.views else None)
        if page.views and page.views[0].route != "/":
            # Any top-level route except Home navigates back to Home
            page.go("/")  # Let route_change handle rebuilding Home
            return
        
        # Already on Home – show exit confirmation
        open_exit_dialog()
        page.exit_dialog_open = True
        print("[NAV] exit dialog opened")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Start with home view if no route specified
    page.go(page.route or "/")

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
