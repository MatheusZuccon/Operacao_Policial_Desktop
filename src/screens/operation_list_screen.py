import threading
import tkinter as tk
import ttkbootstrap as ttk
from typing import Optional

from src.services.operation_api_service import (
    OperationApiService,
    ApiConnectionError,
    ApiTimeoutError,
    ApiNotFoundError,
    ApiServerError,
)
from src.components.loading import LoadingOverlay
from src.components.operation_table import OperationTable
from src.components import dialogs
from src.models import OperationModel
from src.utils.constants import COLORS, FONTS
from src.screens.operation_form_screen import OperationFormScreen
from src.screens.operation_details_screen import OperationDetailsScreen
from src.screens.report_screen import ReportService


class OperationListScreen(tk.Frame):
    """
    Main content screen — shows the operations table and all action buttons.
    Manages the full CRUD lifecycle by opening modal Toplevels for
    create, edit, and view operations.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=COLORS["bg_app"], **kwargs)
        self._service = OperationApiService()
        self._report_svc: Optional[ReportService] = None
        self._selected_id: Optional[int] = None

        self._page = 1
        self._page_size = 20
        self._total_pages = 1
        self._sort_by = "created_at"
        self._sort_dir = "desc"

        self._build()
        self._loading = LoadingOverlay(self)
        self.after(100, self._load_operations)  # Initial load after render

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Page header ───────────────────────────────────────────────────────
        self._build_page_header()

        # ── Toolbar ───────────────────────────────────────────────────────────
        self._build_toolbar()

        # ── Table ─────────────────────────────────────────────────────────────
        self._build_table()

        # ── Pagination (bottom, above actions) ────────────────────────────────
        self._build_pagination()

        # ── Action buttons ────────────────────────────────────────────────────
        self._build_action_bar()

        # ── Status bar ────────────────────────────────────────────────────────
        self._build_status_bar()

    def _build_page_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["bg_content"], pady=16, padx=24)
        header.pack(fill=tk.X)

        left = tk.Frame(header, bg=COLORS["bg_content"])
        left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            left,
            text="Operações Policiais",
            font=FONTS["heading_lg"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_primary"],
        ).pack(anchor=tk.W)

        tk.Label(
            left,
            text="Gerencie todas as operações do sistema",
            font=FONTS["body_sm"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_muted"],
        ).pack(anchor=tk.W, pady=(2, 0))

        # Right: New Operation button (always enabled)
        right = tk.Frame(header, bg=COLORS["bg_content"])
        right.pack(side=tk.RIGHT, anchor=tk.CENTER)

        self._btn_new = ttk.Button(
            right,
            text="  ➕  Nova Operação",
            command=self._open_create_form,
            bootstyle="primary",
            width=20,
        )
        self._btn_new.pack()

        # Separator
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill=tk.X)

    def _build_toolbar(self) -> None:
        toolbar = tk.Frame(self, bg=COLORS["bg_content"], padx=20, pady=10)
        toolbar.pack(fill=tk.X)

        # Search label
        tk.Label(
            toolbar,
            text="Buscar:",
            font=FONTS["heading_sm"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_primary"],
        ).pack(side=tk.LEFT, padx=(0, 6))

        # Search Entry
        self._search_var = tk.StringVar(value="")
        self._search_entry = ttk.Entry(
            toolbar,
            textvariable=self._search_var,
            font=FONTS["body_md"],
            width=30,
        )
        self._search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        # Search button
        ttk.Button(
            toolbar,
            text="🔍  Pesquisar",
            command=self._on_search,
            bootstyle="primary-outline",
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 6))

        # Clear filter button
        ttk.Button(
            toolbar,
            text="Limpar",
            command=self._on_clear_filter,
            bootstyle="secondary-outline",
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Refresh button
        ttk.Button(
            toolbar,
            text="🔄  Atualizar",
            command=self._load_operations,
            bootstyle="secondary",
            width=12,
        ).pack(side=tk.LEFT)

        # Counter label (right-aligned)
        self._count_var = tk.StringVar(value="")
        tk.Label(
            toolbar,
            textvariable=self._count_var,
            font=FONTS["caption"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_muted"],
        ).pack(side=tk.RIGHT, padx=4)

        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=0)

    def _build_table(self) -> None:
        table_frame = tk.Frame(self, bg=COLORS["bg_content"], padx=20, pady=12)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self._table = OperationTable(
            table_frame,
            on_select=self._on_selection_change,
            on_double_click=self._open_details,
            on_sort=self._on_sort,
        )
        self._table.pack(fill=tk.BOTH, expand=True)
    
    def _on_sort(self, sort_by: str, sort_dir: str) -> None:
        """Handle sort event from table: update state and reload."""
        self._sort_by = sort_by
        self._sort_dir = sort_dir
        self._page = 1  # Reset to first page on sort change
        self._load_operations()

    def _build_pagination(self) -> None:
        self._pagination_frame = tk.Frame(self, bg=COLORS["bg_content"], padx=20, pady=10)
        self._pagination_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Separator above pagination
        tk.Frame(self._pagination_frame, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 10))

        center_frame = tk.Frame(self._pagination_frame, bg=COLORS["bg_content"])
        center_frame.pack(anchor=tk.CENTER)

        self._btn_prev = ttk.Button(
            center_frame,
            text="◀  Anterior",
            command=self._prev_page,
            bootstyle="secondary-outline",
            width=12,
            state=tk.DISABLED,
        )
        self._btn_prev.pack(side=tk.LEFT, padx=10)

        self._page_label_var = tk.StringVar(value="Página 1 de 1")
        self._page_label = tk.Label(
            center_frame,
            textvariable=self._page_label_var,
            font=FONTS["label_bold"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_primary"],
        )
        self._page_label.pack(side=tk.LEFT, padx=20)

        self._btn_next = ttk.Button(
            center_frame,
            text="Próxima  ▶",
            command=self._next_page,
            bootstyle="secondary-outline",
            width=12,
            state=tk.DISABLED,
        )
        self._btn_next.pack(side=tk.LEFT, padx=10)

    def _prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load_operations()

    def _next_page(self) -> None:
        if self._page < self._total_pages:
            self._page += 1
            self._load_operations()

    def _on_search(self) -> None:
        self._page = 1
        self._load_operations()

    def _on_clear_filter(self) -> None:
        self._search_var.set("")
        self._page = 1
        self._load_operations()

    def _build_action_bar(self) -> None:
        action_frame = tk.Frame(
            self,
            bg=COLORS["bg_content"],
            padx=20,
            pady=14,
        )
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Frame(action_frame, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 12))

        # Helper to build action buttons
        def action_btn(parent, text, cmd, style, state=tk.DISABLED, width=15):
            btn = ttk.Button(parent, text=text, command=cmd, bootstyle=style, width=width, state=state)
            btn.pack(side=tk.LEFT, padx=(0, 8))
            return btn

        left_actions = tk.Frame(action_frame, bg=COLORS["bg_content"])
        left_actions.pack(side=tk.LEFT)

        self._btn_view = action_btn(left_actions, "🔍  Visualizar", self._open_details_selected, "info-outline")
        self._btn_edit = action_btn(left_actions, "✏️  Editar",     self._open_edit_form,     "primary-outline")
        self._btn_pdf  = action_btn(left_actions, "📄  Gerar PDF",  self._generate_pdf,       "success-outline")

        right_actions = tk.Frame(action_frame, bg=COLORS["bg_content"])
        right_actions.pack(side=tk.RIGHT)

        self._btn_delete = action_btn(right_actions, "🗑  Excluir", self._delete_selected, "danger-outline", width=12)

        # Selection hint
        self._hint_var = tk.StringVar(value="Selecione uma operação na tabela para habilitar as ações.")
        tk.Label(
            action_frame,
            textvariable=self._hint_var,
            font=FONTS["caption"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_muted"],
        ).pack(side=tk.LEFT, padx=(16, 0))

    def _build_status_bar(self) -> None:
        status_bar = tk.Frame(self, bg=COLORS["bg_table_header"], pady=5, padx=20)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_var = tk.StringVar(value="Pronto.")
        tk.Label(
            status_bar,
            textvariable=self._status_var,
            font=FONTS["caption"],
            bg=COLORS["bg_table_header"],
            fg=COLORS["text_muted"],
            anchor=tk.W,
        ).pack(side=tk.LEFT)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_operations(self) -> None:
        self._set_status("Carregando operações…")
        self._loading.show("Carregando operações…")
        self._clear_selection()

        page = getattr(self, "_page", 1)
        page_size = getattr(self, "_page_size", 20)
        search_str = self._search_var.get() if hasattr(self, "_search_var") else ""
        sort_by = getattr(self, "_sort_by", "created_at")
        sort_dir = getattr(self, "_sort_dir", "desc")

        def task():
            try:
                res = self._service.get_all(page=page, page_size=page_size, search=search_str, sort_by=sort_by, sort_dir=sort_dir)
                self.after(0, lambda: self._render_operations(res))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self.after(0, lambda: self._on_load_error(exc.message, connection=True))
            except (ApiServerError, ApiNotFoundError) as exc:
                self.after(0, lambda: self._on_load_error(exc.message))
            finally:
                self.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _render_operations(self, res: dict) -> None:
        ops = res.get("items", [])
        self._table.load_data(ops)

        self._page = res.get("page", 1)
        self._total_pages = res.get("pages", 1)
        total_items = res.get("total", 0)

        self._page_label_var.set(f"Página {self._page} de {self._total_pages}")

        if self._page <= 1:
            self._btn_prev.configure(state=tk.DISABLED)
        else:
            self._btn_prev.configure(state=tk.NORMAL)

        if self._page >= self._total_pages:
            self._btn_next.configure(state=tk.DISABLED)
        else:
            self._btn_next.configure(state=tk.NORMAL)

        self._count_var.set(f"{total_items} operação{'ões' if total_items != 1 else ''} encontrada{'s' if total_items != 1 else ''}")
        self._set_status(f"{len(ops)} operação(ões) exibida(s) de {total_items} no total.")

    def _on_load_error(self, message: str, connection: bool = False) -> None:
        self._set_status("Erro ao carregar dados.")
        if connection:
            dialogs.show_connection_error(self, message)
        else:
            dialogs.show_error(self, message)

    # ── Selection handling ────────────────────────────────────────────────────

    def _on_selection_change(self, operation_id: Optional[int]) -> None:
        self._selected_id = operation_id
        has_selection = operation_id is not None

        state = tk.NORMAL if has_selection else tk.DISABLED
        for btn in (self._btn_view, self._btn_edit, self._btn_pdf, self._btn_delete):
            btn.configure(state=state)

        if has_selection:
            name = self._table.get_selected_name() or ""
            self._hint_var.set(f'Operação selecionada: "{name}"')
        else:
            self._hint_var.set("Selecione uma operação na tabela para habilitar as ações.")

    def _clear_selection(self) -> None:
        self._table.clear_selection()
        self._on_selection_change(None)

    def _require_selection(self) -> bool:
        if self._selected_id is None:
            dialogs.show_no_selection(self)
            return False
        return True

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_create_form(self) -> None:
        OperationFormScreen(
            parent=self,
            service=self._service,
            on_save=self._load_operations,
        )

    def _open_edit_form(self) -> None:
        if not self._require_selection():
            return
        op_id = self._selected_id
        self._loading.show("Carregando dados da operação…")

        def task():
            try:
                data = self._service.get_by_id(op_id)
                op = OperationModel.from_dict(data)
                self.after(0, lambda: self._show_edit_form(op))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self.after(0, lambda: dialogs.show_connection_error(self, exc.message))
            except ApiNotFoundError as exc:
                self.after(0, lambda: dialogs.show_not_found(self, exc.message))
            except ApiServerError as exc:
                self.after(0, lambda: dialogs.show_server_error(self, exc.message))
            finally:
                self.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _show_edit_form(self, op: OperationModel) -> None:
        OperationFormScreen(
            parent=self,
            service=self._service,
            on_save=self._load_operations,
            operation=op,
        )

    def _open_details(self, operation_id: Optional[int] = None) -> None:
        op_id = operation_id if operation_id is not None else self._selected_id
        if op_id is None:
            dialogs.show_no_selection(self)
            return
        OperationDetailsScreen(parent=self, service=self._service, operation_id=op_id)

    def _open_details_selected(self) -> None:
        self._open_details(self._selected_id)

    def _delete_selected(self) -> None:
        if not self._require_selection():
            return
        op_id = self._selected_id
        op_name = self._table.get_selected_name() or str(op_id)

        if not dialogs.confirm_delete(self, op_name):
            return

        self._loading.show("Excluindo operação…")

        def task():
            try:
                self._service.delete(op_id)
                self.after(0, lambda: self._on_delete_success(op_name))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self.after(0, lambda: dialogs.show_connection_error(self, exc.message))
            except ApiNotFoundError as exc:
                self.after(0, lambda: dialogs.show_not_found(self, exc.message))
            except ApiServerError as exc:
                self.after(0, lambda: dialogs.show_server_error(self, exc.message))
            finally:
                self.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _on_delete_success(self, name: str) -> None:
        dialogs.show_success(self, f'Operação "{name}" excluída com sucesso.')
        self._load_operations()

    def _generate_pdf(self) -> None:
        if not self._require_selection():
            return
        op_id = self._selected_id
        op_name = self._table.get_selected_name() or "operacao"

        if self._report_svc is None:
            self._report_svc = ReportService(self, self._service)
        self._report_svc.generate(op_id, op_name)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _set_status(self, message: str) -> None:
        self._status_var.set(message)
