import tkinter as tk
import ttkbootstrap as ttk

from src.components.header import Header
from src.components.sidebar import Sidebar
from src.screens.operation_list_screen import OperationListScreen
from src.utils.constants import (
    APP_TITLE, APP_WIDTH, APP_HEIGHT,
    APP_MIN_WIDTH, APP_MIN_HEIGHT,
    SIDEBAR_WIDTH, COLORS,
)
from src.utils.helpers import center_window


class PoliceOperationApp:
    """
    Root application class.
    Sets up the ttkbootstrap Window, header, sidebar, and content area,
    then launches the OperationListScreen as the default view.
    """

    def __init__(self) -> None:
        # ── Root window ───────────────────────────────────────────────────────
        self.root = ttk.Window(
            title=APP_TITLE,
            themename="flatly",
        )
        self.root.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        center_window(self.root, APP_WIDTH, APP_HEIGHT)
        self.root.configure(bg=COLORS["bg_app"])

        # Make the window icon visible on the taskbar (Windows)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build()

    def _build(self) -> None:
        # ── Header (top) ──────────────────────────────────────────────────────
        self._header = Header(self.root)
        self._header.pack(fill=tk.X, side=tk.TOP)

        # ── Main row (sidebar + content) ──────────────────────────────────────
        main_row = tk.Frame(self.root, bg=COLORS["bg_app"])
        main_row.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self._sidebar = Sidebar(
            main_row,
            on_navigate=self._on_navigate,
        )
        self._sidebar.pack(fill=tk.Y, side=tk.LEFT)

        # Thin divider between sidebar and content
        tk.Frame(main_row, bg=COLORS["border"], width=1).pack(fill=tk.Y, side=tk.LEFT)

        # Content container
        self._content = tk.Frame(main_row, bg=COLORS["bg_app"])
        self._content.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Default screen: operations list
        self._list_screen = OperationListScreen(self._content)
        self._list_screen.pack(fill=tk.BOTH, expand=True)

    def _on_navigate(self, key: str) -> None:
        """Called by the sidebar when the user clicks a navigation item."""
        # Currently only one screen; extend here for future sections.
        if key == "operations":
            pass  # already showing

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = PoliceOperationApp()
    app.run()


if __name__ == "__main__":
    main()
