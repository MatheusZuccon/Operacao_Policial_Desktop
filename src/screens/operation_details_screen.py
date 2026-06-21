import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame

from src.models import OperationModel
from src.services.operation_api_service import (
    OperationApiService,
    ApiConnectionError,
    ApiTimeoutError,
    ApiNotFoundError,
    ApiServerError,
)
from src.components.loading import LoadingOverlay
from src.components import dialogs
from src.utils.constants import COLORS, FONTS, OPERATION_TYPES
from src.utils.helpers import center_toplevel, format_datetime, list_to_bullet


class OperationDetailsScreen(tk.Toplevel):
    """
    Read-only modal window that displays the full details of a police operation.
    Fetches data from the API using the operation ID.
    """

    def __init__(
        self,
        parent: tk.Widget,
        service: OperationApiService,
        operation_id: int,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._operation_id = operation_id

        self._setup_window()
        self._build_skeleton()
        self._loading = LoadingOverlay(self)
        self._fetch()

    def _setup_window(self) -> None:
        self.title("Detalhes da Operação")
        self.resizable(True, True)
        center_toplevel(self, 680, 680, parent=self.master)
        self.transient(self.master)
        self.grab_set()
        self.configure(bg=COLORS["bg_content"])
        self.minsize(560, 500)

    def _build_skeleton(self) -> None:
        # Title bar
        bar = tk.Frame(self, bg=COLORS["bg_sidebar"], height=52)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(
            bar,
            text="  🔍  Detalhes da Operação",
            font=FONTS["heading_md"],
            bg=COLORS["bg_sidebar"],
            fg=COLORS["text_header"],
        ).pack(side=tk.LEFT, padx=20, fill=tk.Y)

        # Scrollable body
        self._body = ScrolledFrame(self, autohide=True)
        self._body.pack(fill=tk.BOTH, expand=True)

        # Close button
        btn_row = tk.Frame(self, bg=COLORS["bg_content"], pady=12)
        btn_row.pack(fill=tk.X, padx=20)
        ttk.Button(
            btn_row, text="Fechar", command=self.destroy,
            bootstyle="secondary-outline", width=14,
        ).pack(side=tk.RIGHT)

    def _fetch(self) -> None:
        self._loading.show("Carregando detalhes…")

        def task():
            try:
                data = self._service.get_by_id(self._operation_id)
                self.after(0, lambda: self._render(data))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self.after(0, lambda: dialogs.show_connection_error(self, exc.message))
                self.after(100, self.destroy)
            except ApiNotFoundError as exc:
                self.after(0, lambda: dialogs.show_not_found(self, exc.message))
                self.after(100, self.destroy)
            except ApiServerError as exc:
                self.after(0, lambda: dialogs.show_server_error(self, exc.message))
                self.after(100, self.destroy)
            finally:
                self.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _render(self, data: dict) -> None:
        op = OperationModel.from_dict(data)
        parent = self._body

        # ── Header card ───────────────────────────────────────────────────────
        header_card = tk.Frame(
            parent,
            bg=COLORS["btn_primary"],
            padx=20, pady=16,
        )
        header_card.pack(fill=tk.X, padx=20, pady=(16, 0))

        tk.Label(
            header_card,
            text=op.name,
            font=FONTS["heading_lg"],
            bg=COLORS["btn_primary"],
            fg="#FFFFFF",
            wraplength=560, justify=tk.LEFT,
        ).pack(anchor=tk.W)

        type_label = OPERATION_TYPES.get(op.operation_type, op.operation_type)
        tk.Label(
            header_card,
            text=type_label,
            font=FONTS["body_sm"],
            bg=COLORS["btn_primary"],
            fg="#BFDBFE",
        ).pack(anchor=tk.W, pady=(4, 0))

        # ── Info grid ─────────────────────────────────────────────────────────
        info_card = self._card(parent, "📋  Informações Gerais")
        info_card.pack(fill=tk.X, padx=20, pady=(12, 0))
        info_body = tk.Frame(info_card, bg=COLORS["bg_content"], padx=16, pady=12)
        info_body.pack(fill=tk.X)

        def info_row(label: str, value: str) -> None:
            row = tk.Frame(info_body, bg=COLORS["bg_content"])
            row.pack(fill=tk.X, pady=4)
            tk.Label(
                row, text=label, width=18, anchor=tk.W,
                font=FONTS["label_bold"],
                bg=COLORS["bg_content"], fg=COLORS["text_secondary"],
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=value or "—", anchor=tk.W,
                font=FONTS["body_sm"],
                bg=COLORS["bg_content"], fg=COLORS["text_primary"],
                wraplength=420, justify=tk.LEFT,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        info_row("Número da Operação:", op.operation_number or "—")
        info_row("Localização:", op.location)
        info_row("Data de Criação:", format_datetime(op.created_at or ""))
        info_row("Tipo:", OPERATION_TYPES.get(op.operation_type, op.operation_type))

        if op.description:
            info_row("Descrição:", op.description)

        # ── Resources ─────────────────────────────────────────────────────────
        res_card = self._card(parent, "⚙️  Recursos da Operação")
        res_card.pack(fill=tk.X, padx=20, pady=(12, 0))
        res_body = tk.Frame(res_card, bg=COLORS["bg_content"], padx=16, pady=12)
        res_body.pack(fill=tk.X)

        def resource_section(title: str, content: str) -> None:
            tk.Label(
                res_body, text=title,
                font=FONTS["heading_sm"],
                bg=COLORS["bg_content"], fg=COLORS["text_primary"],
            ).pack(anchor=tk.W, pady=(10, 2))
            tk.Frame(res_body, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 4))
            tk.Label(
                res_body, text=content,
                font=FONTS["body_sm"],
                bg=COLORS["bg_section"],
                fg=COLORS["text_secondary"],
                justify=tk.LEFT, anchor=tk.W,
                padx=10, pady=8, wraplength=560,
            ).pack(fill=tk.X)

        weapons_str = "\n".join(
            f"• {w.weapon.capitalize()} (Quantidade: {w.quantity})"
            for w in op.weapons
        ) if op.weapons else "Nenhum"
        resource_section("🔫 Armamentos", weapons_str)

        vehicles_str = "\n".join(
            f"• {v.brand} {v.model}  [Placa: {v.plate}]{'  [Blindada]' if v.armored else ''}"
            for v in op.vehicles
        ) if op.vehicles else "Nenhuma"
        resource_section("🚗 Viaturas", vehicles_str)

        roles_str = ""
        for r in op.roles:
            officers_str = ", ".join(r.officers) if r.officers else "Nenhum policial"
            roles_str += f"• {r.role.capitalize()} (Qtd: {r.quantity})\n  Policiais: {officers_str}\n"
        roles_str = roles_str.strip() if roles_str else "Nenhum"
        resource_section("👮 Cargos", roles_str)

        equips_str = "\n".join(
            f"• {e.equipment.capitalize()} (Quantidade: {e.quantity})"
            for e in op.investigation_equipments
        ) if op.investigation_equipments else "Nenhum"
        resource_section("🔬 Equipamentos Investigativos", equips_str)

        # bottom spacer
        tk.Frame(parent, bg=COLORS["bg_content"], height=16).pack()

    def _card(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.Frame(
            parent, bg=COLORS["bg_content"],
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        tk.Label(
            frame, text=title,
            font=FONTS["heading_sm"],
            bg=COLORS["btn_primary"], fg="#FFFFFF",
            padx=14, pady=7, anchor=tk.W,
        ).pack(fill=tk.X)
        return frame
