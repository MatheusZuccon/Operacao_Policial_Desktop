import tkinter as tk
from typing import Callable
from src.utils.constants import COLORS, FONTS, SIDEBAR_WIDTH


class _NavItem(tk.Frame):
    """Single clickable item in the sidebar."""

    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        label: str,
        active: bool,
        on_click: Callable,
        **kwargs,
    ) -> None:
        bg = COLORS["sidebar_item_active"] if active else COLORS["bg_sidebar"]
        super().__init__(parent, bg=bg, cursor="hand2", **kwargs)

        self._active = active
        self._on_click = on_click
        self._default_bg = bg

        # Left accent bar (visible only when active)
        self._bar = tk.Frame(
            self,
            bg="#60A5FA" if active else COLORS["bg_sidebar"],
            width=4,
        )
        self._bar.pack(side=tk.LEFT, fill=tk.Y)

        # Icon
        tk.Label(
            self,
            text=icon,
            font=("Segoe UI", 14),
            bg=bg,
            fg="#FFFFFF" if active else COLORS["text_sidebar"],
            width=3,
        ).pack(side=tk.LEFT, padx=(10, 4), pady=14)

        # Label
        self._lbl = tk.Label(
            self,
            text=label,
            font=FONTS["sidebar_item"],
            bg=bg,
            fg="#FFFFFF" if active else COLORS["text_sidebar"],
            anchor=tk.W,
        )
        self._lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Bind click / hover to all children
        for widget in (self, self._lbl):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._hover_on)
            widget.bind("<Leave>", self._hover_off)

    def _click(self, _event=None) -> None:
        self._on_click()

    def _hover_on(self, _event=None) -> None:
        if not self._active:
            self.configure(bg=COLORS["sidebar_item_hover"])
            self._lbl.configure(bg=COLORS["sidebar_item_hover"])

    def _hover_off(self, _event=None) -> None:
        bg = COLORS["sidebar_item_active"] if self._active else COLORS["bg_sidebar"]
        self.configure(bg=bg)
        self._lbl.configure(bg=bg)

    def set_active(self, active: bool) -> None:
        self._active = active
        bg = COLORS["sidebar_item_active"] if active else COLORS["bg_sidebar"]
        self._default_bg = bg
        self.configure(bg=bg)
        self._lbl.configure(bg=bg)
        self._bar.configure(bg="#60A5FA" if active else COLORS["bg_sidebar"])


class Sidebar(tk.Frame):
    """Left-hand navigation sidebar."""

    def __init__(self, parent: tk.Widget, on_navigate: Callable, **kwargs) -> None:
        super().__init__(
            parent,
            bg=COLORS["bg_sidebar"],
            width=SIDEBAR_WIDTH,
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._items: dict[str, _NavItem] = {}
        self._active_key: str = "operations"
        self._build()

    def _build(self) -> None:
        # Brand section
        brand = tk.Frame(self, bg=COLORS["bg_sidebar"])
        brand.pack(fill=tk.X, pady=(20, 0))

        tk.Label(
            brand,
            text="MENU PRINCIPAL",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_sidebar"],
            fg=COLORS["text_muted"],
        ).pack(anchor=tk.W, padx=20, pady=(0, 8))

        # Separator
        tk.Frame(self, bg=COLORS["sidebar_divider"], height=1).pack(fill=tk.X, padx=16, pady=(0, 8))

        # Nav items
        nav_items = [
            ("operations", "📋", "Operações"),
        ]

        for key, icon, label in nav_items:
            item = _NavItem(
                self,
                icon=icon,
                label=label,
                active=(key == self._active_key),
                on_click=lambda k=key: self._navigate(k),
            )
            item.pack(fill=tk.X)
            self._items[key] = item

        # Separator
        tk.Frame(self, bg=COLORS["sidebar_divider"], height=1).pack(fill=tk.X, padx=16, pady=16)

        # Info section at bottom
        info_frame = tk.Frame(self, bg=COLORS["bg_sidebar"])
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=16)

        tk.Frame(self, bg=COLORS["sidebar_divider"], height=1).pack(
            side=tk.BOTTOM, fill=tk.X, padx=16
        )

        tk.Label(
            info_frame,
            text="Police Operation API",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_sidebar"],
            fg=COLORS["text_muted"],
        ).pack(anchor=tk.W)

        tk.Label(
            info_frame,
            text="v1.0.0 — Desktop Client",
            font=("Segoe UI", 8),
            bg=COLORS["bg_sidebar"],
            fg=COLORS["sidebar_divider"],
        ).pack(anchor=tk.W)

    def _navigate(self, key: str) -> None:
        for k, item in self._items.items():
            item.set_active(k == key)
        self._active_key = key
        self._on_navigate(key)
