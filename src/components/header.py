import tkinter as tk
from src.utils.constants import COLORS, FONTS


class Header(tk.Frame):
    """Top navigation bar — dark background with app title and status dot."""

    HEIGHT: int = 58

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(
            parent,
            bg=COLORS["bg_header"],
            height=self.HEIGHT,
            **kwargs,
        )
        self.pack_propagate(False)
        self._build()

    def _build(self) -> None:
        # Left: badge icon + title
        left = tk.Frame(self, bg=COLORS["bg_header"])
        left.pack(side=tk.LEFT, padx=(20, 0), fill=tk.Y)

        badge = tk.Label(
            left,
            text="⚑",
            font=("Segoe UI", 22),
            bg=COLORS["btn_primary"],
            fg="#FFFFFF",
            width=3,
            relief=tk.FLAT,
        )
        badge.pack(side=tk.LEFT, padx=(0, 12), fill=tk.Y, ipady=6)

        title_frame = tk.Frame(left, bg=COLORS["bg_header"])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            title_frame,
            text="Police Operation Desktop",
            font=FONTS["app_title"],
            bg=COLORS["bg_header"],
            fg=COLORS["text_header"],
        ).pack(anchor=tk.W, pady=(14, 0))
        
        # Right: status indicator
        right = tk.Frame(self, bg=COLORS["bg_header"])
        right.pack(side=tk.RIGHT, padx=24, fill=tk.Y)

        status_frame = tk.Frame(right, bg=COLORS["bg_header"])
        status_frame.pack(side=tk.RIGHT, anchor=tk.CENTER)

        self._status_dot = tk.Label(
            status_frame,
            text="●",
            font=("Segoe UI", 12),
            bg=COLORS["bg_header"],
            fg=COLORS["text_success"],
        )
        self._status_dot.pack(side=tk.LEFT, padx=(0, 6))

        self._status_label = tk.Label(
            status_frame,
            text="API Online",
            font=FONTS["caption"],
            bg=COLORS["bg_header"],
            fg=COLORS["text_muted"],
        )
        self._status_label.pack(side=tk.LEFT)

        # Separator line at the bottom
        tk.Frame(self, bg=COLORS["sidebar_item_active"], height=2).pack(
            side=tk.BOTTOM, fill=tk.X
        )

    def set_status(self, online: bool) -> None:
        """Update the status indicator (call from the main thread only)."""
        if online:
            self._status_dot.configure(fg=COLORS["text_success"])
            self._status_label.configure(text="API Online")
        else:
            self._status_dot.configure(fg=COLORS["text_danger"])
            self._status_label.configure(text="API Offline")
