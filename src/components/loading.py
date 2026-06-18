import tkinter as tk
import ttkbootstrap as ttk
from src.utils.constants import COLORS, FONTS


class LoadingOverlay:
    def __init__(self, parent: tk.Widget) -> None:
        self._parent = parent
        self._top: tk.Toplevel | None = None

    def show(self, message: str = "Carregando…") -> None:
        if self._top is not None:
            return

        root = self._parent.winfo_toplevel()
        self._top = tk.Toplevel(root)
        self._top.transient(root)
        self._top.grab_set()
        self._top.overrideredirect(True)
        self._top.configure(bg=COLORS["bg_content"])

        # Size and position
        w, h = 300, 130
        root.update_idletasks()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()
        x = rx + (rw - w) // 2
        y = ry + (rh - h) // 2
        self._top.geometry(f"{w}x{h}+{x}+{y}")

        # Border frame
        border = tk.Frame(self._top, bg=COLORS["border"], bd=1)
        border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner = tk.Frame(border, bg=COLORS["bg_content"], padx=24, pady=20)
        inner.pack(fill=tk.BOTH, expand=True)

        # Icon + label
        tk.Label(
            inner,
            text="⏳",
            font=("Segoe UI", 22),
            bg=COLORS["bg_content"],
            fg=COLORS["btn_primary"],
        ).pack()

        self._msg_var = tk.StringVar(value=message)
        tk.Label(
            inner,
            textvariable=self._msg_var,
            font=FONTS["body_md"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_secondary"],
        ).pack(pady=(6, 10))

        self._pb = ttk.Progressbar(
            inner,
            mode="indeterminate",
            bootstyle="primary",
            length=220,
        )
        self._pb.pack()
        self._pb.start(12)

        self._top.update()

    def update_message(self, message: str) -> None:
        if self._top and hasattr(self, "_msg_var"):
            self._msg_var.set(message)

    def hide(self) -> None:
        if self._top is None:
            return
        try:
            self._pb.stop()
            self._top.grab_release()
            self._top.destroy()
        except tk.TclError:
            pass
        finally:
            self._top = None
