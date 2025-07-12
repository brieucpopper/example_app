import flet as ft

# List of top-level routes
TOP_LEVEL_ROUTES = ["/"]


def create_app_bar(page: ft.Page, title: str):
    """Create a consistent app bar for all views"""
    
    def go_back(e):
        # Only go back if there is more than one view in the stack
        if len(page.views) > 1:
            page.views.pop()
            # Always go to the new top view's route
            page.go(page.views[-1].route)

    # The back button should be visible only for detail/sub-views

    show_back = len(page.views) > 1 and (page.views[-1].route not in "/")
    back_button = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        icon_size=28,
        style=ft.ButtonStyle(padding=ft.padding.all(10)),
        visible=show_back,
        on_click=go_back,
    )
    
    # Create the title
    title_text = ft.Text(title, size=24, weight=ft.FontWeight.BOLD)
    
    # Create the container with the row
    return ft.Container(
        content=ft.Row(
            [back_button, title_text],
            alignment=ft.MainAxisAlignment.START,
        ),
        margin=ft.margin.only(bottom=20),
        padding=ft.padding.only(top=10),
    ) 