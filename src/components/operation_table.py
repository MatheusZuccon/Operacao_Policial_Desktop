import tkinter as tk
import ttkbootstrap as ttk
from typing import Callable, Optional
from src.utils.constants import COLORS, FONTS
from src.utils.helpers import format_datetime, format_operation_type


class OperationTable(tk.Frame):
    """
    Treeview-based table that displays police operations.
    Internal IDs are stored in a hidden iid-to-id map and never shown.
    """

    COLUMNS: tuple = ("number", "name", "type", "location", "created_at")
    COLUMN_CONFIG: dict = {
        "number":     {"text": "Nº Operação",        "width": 120, "anchor": tk.CENTER, "api_field": "operation_number"},
        "name":       {"text": "Nome da Operação",  "width": 240, "anchor": tk.W, "api_field": "name"},
        "type":       {"text": "Tipo",               "width": 150, "anchor": tk.W, "api_field": "operation_type"},
        "location":   {"text": "Localização",        "width": 180, "anchor": tk.W, "api_field": "location"},
        "created_at": {"text": "Data de Criação",    "width": 140, "anchor": tk.CENTER, "api_field": "created_at"},
    }

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[Optional[int]], None],
        on_double_click: Callable[[int], None],
        on_sort: Callable[[str, str], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg_content"], **kwargs)
        self._on_select = on_select
        self._on_double_click = on_double_click
        self._on_sort = on_sort
        self._id_map: dict[str, int] = {}  # iid → operation_id
        self._current_sort_col: Optional[str] = None
        self._current_sort_dir: str = "desc"
        self._build()

    def _build(self) -> None:
        # Treeview + scrollbars
        tree_frame = tk.Frame(self, bg=COLORS["bg_content"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure(
            "Operations.Treeview",
            font=FONTS["table_body"],
            rowheight=36,
            background=COLORS["bg_row_even"],
            fieldbackground=COLORS["bg_row_even"],
            foreground=COLORS["text_primary"],
            borderwidth=0,
        )
        style.configure(
            "Operations.Treeview.Heading",
            font=FONTS["table_header"],
            background=COLORS["bg_table_header"],
            foreground=COLORS["text_secondary"],
            relief=tk.FLAT,
            borderwidth=0,
        )
        style.map(
            "Operations.Treeview",
            background=[("selected", COLORS["bg_selected"])],
            foreground=[("selected", COLORS["text_primary"])],
        )
        style.layout("Operations.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            style="Operations.Treeview",
            selectmode="browse",
        )

        for col, cfg in self.COLUMN_CONFIG.items():
            self._tree.heading(col, text=cfg["text"], command=lambda c=col: self._on_header_click(c))
            self._tree.column(col, width=cfg["width"], anchor=cfg["anchor"], minwidth=80)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Alternating row colors
        self._tree.tag_configure("even", background=COLORS["bg_row_even"])
        self._tree.tag_configure("odd", background=COLORS["bg_row_odd"])

        # Events
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Double-1>", self._on_tree_double_click)

        # Empty state label (shown when no data)
        self._empty_label = tk.Label(
            self,
            text="Nenhuma operação encontrada.\nClique em '+ Nova Operação' para cadastrar.",
            font=FONTS["body_md"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_muted"],
            justify=tk.CENTER,
        )

    def _on_header_click(self, col: str) -> None:
        """Handle header click for sorting."""
        # Toggle direction if same column, otherwise default to desc
        if self._current_sort_col == col:
            self._current_sort_dir = "asc" if self._current_sort_dir == "desc" else "desc"
        else:
            self._current_sort_col = col
            self._current_sort_dir = "desc"
        
        # Update heading texts to show sort indicator
        for c, cfg in self.COLUMN_CONFIG.items():
            base_text = cfg["text"]
            if c == self._current_sort_col:
                indicator = "↑" if self._current_sort_dir == "asc" else "↓"
                self._tree.heading(c, text=f"{base_text} {indicator}")
            else:
                self._tree.heading(c, text=base_text)
        
        # Get the API field name
        api_field = self.COLUMN_CONFIG[col]["api_field"]
        # Notify parent to reload data
        self._on_sort(api_field, self._current_sort_dir)

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_data(self, operations: list[dict]) -> None:
        """Clear and re-populate the table with a fresh list of operations."""
        self._clear()
        if not operations:
            self._show_empty()
            return
        self._hide_empty()
        for idx, op in enumerate(operations):
            tag = "even" if idx % 2 == 0 else "odd"
            iid = self._tree.insert(
                "",
                tk.END,
                values=(
                    op.get("operation_number", "") or "—",
                    op.get("name", ""),
                    format_operation_type(op.get("operation_type", "")),
                    op.get("location", ""),
                    format_datetime(op.get("created_at", "")),
                ),
                tags=(tag,),
            )
            self._id_map[iid] = op["id"]

    def _clear(self) -> None:
        self._id_map.clear()
        for iid in self._tree.get_children():
            self._tree.delete(iid)

    # ── Selection ─────────────────────────────────────────────────────────────

    def get_selected_id(self) -> Optional[int]:
        """Return the operation ID of the currently selected row, or None."""
        selected = self._tree.selection()
        if not selected:
            return None
        return self._id_map.get(selected[0])

    def get_selected_name(self) -> Optional[str]:
        selected = self._tree.selection()
        if not selected:
            return None
        values = self._tree.item(selected[0], "values")
        return values[1] if values and len(values) > 1 else None

    def clear_selection(self) -> None:
        for iid in self._tree.selection():
            self._tree.selection_remove(iid)

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_tree_select(self, _event=None) -> None:
        self._on_select(self.get_selected_id())

    def _on_tree_double_click(self, _event=None) -> None:
        op_id = self.get_selected_id()
        if op_id is not None:
            self._on_double_click(op_id)

    # ── Empty State ───────────────────────────────────────────────────────────

    def _show_empty(self) -> None:
        self._empty_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _hide_empty(self) -> None:
        self._empty_label.place_forget()
