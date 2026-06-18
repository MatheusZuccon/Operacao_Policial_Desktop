import threading
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame
from typing import Callable, Optional

from src.models import OperationModel, VehicleModel
from src.services.operation_api_service import (
    OperationApiService,
    ApiConnectionError,
    ApiTimeoutError,
    ApiValidationError,
    ApiNotFoundError,
    ApiServerError,
)
from src.components.loading import LoadingOverlay
from src.components import dialogs
from src.utils.constants import (
    COLORS, FONTS,
    VALID_WEAPONS, VALID_ROLES, VALID_EQUIPMENTS,
    TYPE_DISPLAY_OPTIONS, DISPLAY_TO_TYPE_KEY, TYPE_KEY_TO_DISPLAY,
)
from src.utils.helpers import center_toplevel


# ── Reusable sub-widgets ──────────────────────────────────────────────────────

class _SectionLabel(tk.Label):
    def __init__(self, parent, text: str, **kw):
        super().__init__(
            parent,
            text=text,
            font=FONTS["heading_sm"],
            bg=COLORS["bg_content"],
            fg=COLORS["text_primary"],
            **kw,
        )


class _CheckboxList(tk.Frame):
    """Scrollable list of Checkbuttons for selecting multiple string items."""

    def __init__(self, parent: tk.Widget, items: list[str], height: int = 130, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_section"], relief=tk.FLAT, **kw)
        self._vars: dict[str, tk.BooleanVar] = {}
        self._build(items, height)

    def _build(self, items: list[str], height: int) -> None:
        canvas = tk.Canvas(
            self, height=height, bg=COLORS["bg_section"],
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["bg_section"])

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind mousewheel to canvas
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        cols = 2
        for i, item in enumerate(items):
            var = tk.BooleanVar(value=False)
            self._vars[item] = var
            row, col = divmod(i, cols)
            cb = tk.Checkbutton(
                inner,
                text=f"  {item.capitalize()}",
                variable=var,
                font=FONTS["body_sm"],
                bg=COLORS["bg_section"],
                fg=COLORS["text_primary"],
                activebackground=COLORS["bg_section"],
                selectcolor=COLORS["bg_section"],
                relief=tk.FLAT,
                anchor=tk.W,
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=8, pady=2)

    def get_selected(self) -> list[str]:
        return [item for item, var in self._vars.items() if var.get()]

    def set_selected(self, items: list[str]) -> None:
        for item, var in self._vars.items():
            var.set(item in items)

    def reset(self) -> None:
        for var in self._vars.values():
            var.set(False)


class _VehicleList(tk.Frame):
    """Widget for adding/removing vehicles with name + armored flag."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_content"], **kw)
        self._vehicles: list[dict] = []
        self._build()

    def _build(self) -> None:
        # ── Input row ─────────────────────────────────────────────────────────
        input_row = tk.Frame(self, bg=COLORS["bg_content"])
        input_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            input_row, text="Nome:", font=FONTS["body_sm"],
            bg=COLORS["bg_content"], fg=COLORS["text_secondary"],
        ).pack(side=tk.LEFT, padx=(0, 4))

        self._name_var = tk.StringVar()
        self._entry = ttk.Entry(input_row, textvariable=self._name_var, width=22)
        self._entry.pack(side=tk.LEFT, padx=(0, 10))
        self._entry.bind("<Return>", lambda _: self._add())

        self._armored_var = tk.BooleanVar()
        tk.Checkbutton(
            input_row, text="Blindada", variable=self._armored_var,
            font=FONTS["body_sm"], bg=COLORS["bg_content"],
            fg=COLORS["text_primary"], activebackground=COLORS["bg_content"],
            selectcolor=COLORS["bg_content"], relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            input_row, text="+ Adicionar",
            command=self._add, bootstyle="outline-primary", width=12,
        ).pack(side=tk.LEFT)

        # ── Treeview ──────────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=COLORS["bg_content"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("nome", "blindada")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
        self._tree.heading("nome", text="Nome da Viatura")
        self._tree.heading("blindada", text="Blindada")
        self._tree.column("nome", width=240, anchor=tk.W)
        self._tree.column("blindada", width=80, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Remove button ─────────────────────────────────────────────────────
        ttk.Button(
            self, text="🗑 Remover Selecionada",
            command=self._remove, bootstyle="outline-danger",
        ).pack(anchor=tk.E, pady=(4, 0))

    def _add(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Atenção", "Informe o nome da viatura.", parent=self)
            return
        armored = self._armored_var.get()
        self._vehicles.append({"name": name, "armored": armored})
        self._tree.insert("", tk.END, values=(name, "Sim" if armored else "Não"))
        self._name_var.set("")
        self._armored_var.set(False)
        self._entry.focus()

    def _remove(self) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        for iid in selected:
            idx = self._tree.index(iid)
            if 0 <= idx < len(self._vehicles):
                self._vehicles.pop(idx)
            self._tree.delete(iid)

    def get_vehicles(self) -> list[dict]:
        return list(self._vehicles)

    def set_vehicles(self, vehicles: list[dict]) -> None:
        self._vehicles = []
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        for v in vehicles:
            entry = {"name": v["name"], "armored": bool(v.get("armored", False))}
            self._vehicles.append(entry)
            self._tree.insert("", tk.END, values=(v["name"], "Sim" if v.get("armored") else "Não"))

    def reset(self) -> None:
        self._vehicles = []
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._name_var.set("")
        self._armored_var.set(False)


# ── Main Form Screen ──────────────────────────────────────────────────────────

class OperationFormScreen(tk.Toplevel):
    """
    Modal window for creating and editing a police operation.
    When `operation` is provided, the form enters edit mode.
    The `on_save` callback is invoked after a successful API call.
    """

    def __init__(
        self,
        parent: tk.Widget,
        service: OperationApiService,
        on_save: Callable,
        operation: Optional[OperationModel] = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._on_save = on_save
        self._operation = operation
        self._edit_mode = operation is not None
        self._current_type: str = ""

        # ── Widget references (built in _build_form) ──────────────────────────
        self._weapon_list: Optional[_CheckboxList] = None
        self._vehicle_list: Optional[_VehicleList] = None
        self._role_list: Optional[_CheckboxList] = None
        self._equip_list: Optional[_CheckboxList] = None
        self._dynamic_frame: Optional[tk.Frame] = None

        self._setup_window()
        self._build()
        self._loading = LoadingOverlay(self)

        if self._edit_mode:
            self._populate(operation)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        title = "Editar Operação" if self._edit_mode else "Nova Operação"
        self.title(title)
        self.resizable(True, True)
        center_toplevel(self, 740, 700, parent=self.master)
        self.transient(self.master)
        self.grab_set()
        self.configure(bg=COLORS["bg_content"])
        self.minsize(640, 560)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=COLORS["bg_sidebar"], height=52)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        icon = "✏️" if self._edit_mode else "➕"
        tk.Label(
            title_bar,
            text=f"  {icon}  {'Editar Operação' if self._edit_mode else 'Nova Operação'}",
            font=FONTS["heading_md"],
            bg=COLORS["bg_sidebar"],
            fg=COLORS["text_header"],
        ).pack(side=tk.LEFT, padx=20, fill=tk.Y)

        # ── Scrollable body ───────────────────────────────────────────────────
        body = ScrolledFrame(self, autohide=True)
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        inner = body

        # ── Section: Informações Básicas ──────────────────────────────────────
        basic_card = self._card(inner, "📄  Informações Básicas")
        basic_card.pack(fill=tk.X, padx=20, pady=(16, 0))
        self._build_basic_fields(basic_card)

        # ── Section: Configuração (dynamic) ───────────────────────────────────
        self._dynamic_outer = tk.Frame(inner, bg=COLORS["bg_content"])
        self._dynamic_outer.pack(fill=tk.X, padx=20, pady=(12, 0))

        # ── Bottom buttons ─────────────────────────────────────────────────────
        self._build_buttons(inner)

    def _card(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a labeled section card."""
        frame = tk.Frame(
            parent,
            bg=COLORS["bg_content"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        tk.Label(
            frame,
            text=title,
            font=FONTS["heading_sm"],
            bg=COLORS["btn_primary"],
            fg="#FFFFFF",
            padx=14, pady=7,
            anchor=tk.W,
        ).pack(fill=tk.X)
        return frame

    def _build_basic_fields(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=COLORS["bg_content"], padx=16, pady=12)
        body.pack(fill=tk.X)

        def field_row(lbl: str, widget_factory) -> None:
            row = tk.Frame(body, bg=COLORS["bg_content"])
            row.pack(fill=tk.X, pady=5)
            tk.Label(
                row, text=lbl, width=14, anchor=tk.W,
                font=FONTS["label_bold"], bg=COLORS["bg_content"],
                fg=COLORS["text_secondary"],
            ).pack(side=tk.LEFT)
            widget_factory(row)

        # Name
        self._name_var = tk.StringVar()
        field_row("Nome *", lambda p: ttk.Entry(p, textvariable=self._name_var, font=FONTS["body_sm"]).pack(
            side=tk.LEFT, fill=tk.X, expand=True,
        ))

        # Type
        self._type_var = tk.StringVar()
        def build_type_combo(p):
            cb = ttk.Combobox(
                p, textvariable=self._type_var,
                values=TYPE_DISPLAY_OPTIONS,
                state="readonly", font=FONTS["body_sm"],
            )
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb.bind("<<ComboboxSelected>>", self._on_type_change)
        field_row("Tipo *", build_type_combo)

        # Location
        self._location_var = tk.StringVar()
        field_row("Localização *", lambda p: ttk.Entry(p, textvariable=self._location_var, font=FONTS["body_sm"]).pack(
            side=tk.LEFT, fill=tk.X, expand=True,
        ))

        # Description
        desc_row = tk.Frame(body, bg=COLORS["bg_content"])
        desc_row.pack(fill=tk.X, pady=5)
        tk.Label(
            desc_row, text="Descrição", width=14, anchor=tk.NW,
            font=FONTS["label_bold"], bg=COLORS["bg_content"],
            fg=COLORS["text_secondary"],
        ).pack(side=tk.LEFT)
        desc_inner = tk.Frame(desc_row, bg=COLORS["bg_content"])
        desc_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._desc_text = tk.Text(
            desc_inner, height=3, font=FONTS["body_sm"],
            relief=tk.FLAT, bd=1, wrap=tk.WORD,
            bg=COLORS["bg_input"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            highlightthickness=1,
            highlightbackground=COLORS["border_input"],
            highlightcolor=COLORS["border_focus"],
        )
        self._desc_text.pack(fill=tk.X)

    def _build_buttons(self, parent: tk.Widget) -> None:
        btn_frame = tk.Frame(parent, bg=COLORS["bg_content"], pady=16)
        btn_frame.pack(fill=tk.X, padx=20)

        tk.Frame(btn_frame, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 14))

        right = tk.Frame(btn_frame, bg=COLORS["bg_content"])
        right.pack(side=tk.RIGHT)

        ttk.Button(
            right, text="Cancelar", command=self.destroy,
            bootstyle="secondary-outline", width=12,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            right,
            text="💾  Salvar" if self._edit_mode else "✅  Criar Operação",
            command=self._submit,
            bootstyle="primary",
            width=18,
        ).pack(side=tk.LEFT)

    # ── Dynamic section ───────────────────────────────────────────────────────

    def _on_type_change(self, _event=None) -> None:
        display = self._type_var.get()
        key = DISPLAY_TO_TYPE_KEY.get(display, "")
        if key == self._current_type:
            return
        self._current_type = key
        self._rebuild_dynamic_section(key)

    def _rebuild_dynamic_section(self, op_type: str) -> None:
        # Destroy previous dynamic content
        for child in self._dynamic_outer.winfo_children():
            child.destroy()
        self._weapon_list = None
        self._vehicle_list = None
        self._role_list = None
        self._equip_list = None

        if not op_type:
            return

        card = self._card(self._dynamic_outer, "⚙️  Configuração da Operação")
        card.pack(fill=tk.X)
        body = tk.Frame(card, bg=COLORS["bg_content"], padx=16, pady=12)
        body.pack(fill=tk.X)

        if op_type == "OSTENSIVE":
            self._build_ostensive_section(body)
        elif op_type == "INVESTIGATIVE":
            self._build_investigative_section(body)
        elif op_type == "TACTICAL":
            self._build_tactical_section(body)

        self._dynamic_outer.update_idletasks()

    def _section_title(self, parent: tk.Widget, text: str, note: str = "") -> None:
        row = tk.Frame(parent, bg=COLORS["bg_content"])
        row.pack(fill=tk.X, pady=(10, 4))
        tk.Label(
            row, text=text, font=FONTS["heading_sm"],
            bg=COLORS["bg_content"], fg=COLORS["text_primary"],
        ).pack(side=tk.LEFT)
        if note:
            tk.Label(
                row, text=note, font=FONTS["caption"],
                bg=COLORS["bg_content"], fg=COLORS["text_muted"],
            ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(0, 6))

    def _build_ostensive_section(self, parent: tk.Frame) -> None:
        self._section_title(parent, "🔫 Armamentos", "(mín. 1)")
        self._weapon_list = _CheckboxList(parent, VALID_WEAPONS)
        self._weapon_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "🚗 Viaturas", "(mín. 1)")
        self._vehicle_list = _VehicleList(parent)
        self._vehicle_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 1)")
        self._role_list = _CheckboxList(parent, VALID_ROLES)
        self._role_list.pack(fill=tk.X)

    def _build_investigative_section(self, parent: tk.Frame) -> None:
        # Fixed pistol notice
        self._section_title(parent, "🔫 Armamento", "(somente pistola)")
        notice = tk.Frame(
            parent, bg="#FEF3C7",
            highlightthickness=1, highlightbackground="#F59E0B",
        )
        notice.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            notice,
            text="⚠️  Operações investigativas utilizam exclusivamente a pistola como armamento.",
            font=FONTS["body_sm"],
            bg="#FEF3C7", fg="#92400E",
            padx=12, pady=8, wraplength=560, justify=tk.LEFT,
        ).pack(fill=tk.X)

        self._section_title(parent, "🔬 Equipamentos Investigativos", "(mín. 1)")
        self._equip_list = _CheckboxList(parent, VALID_EQUIPMENTS)
        self._equip_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 1)")
        self._role_list = _CheckboxList(parent, VALID_ROLES)
        self._role_list.pack(fill=tk.X)

    def _build_tactical_section(self, parent: tk.Frame) -> None:
        self._section_title(parent, "🔫 Armamentos", "(mín. 5)")
        self._weapon_list = _CheckboxList(parent, VALID_WEAPONS)
        self._weapon_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "🚗 Viaturas", "(mín. 2)")
        self._vehicle_list = _VehicleList(parent)
        self._vehicle_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 5)")
        self._role_list = _CheckboxList(parent, VALID_ROLES)
        self._role_list.pack(fill=tk.X)

    # ── Populate (edit mode) ──────────────────────────────────────────────────

    def _populate(self, op: OperationModel) -> None:
        self._name_var.set(op.name)
        self._location_var.set(op.location)

        # Set description
        self._desc_text.delete("1.0", tk.END)
        if op.description:
            self._desc_text.insert("1.0", op.description)

        # Set type (triggers dynamic section rebuild)
        display = TYPE_KEY_TO_DISPLAY.get(op.operation_type, "")
        if display:
            self._type_var.set(display)
            self._current_type = op.operation_type
            self._rebuild_dynamic_section(op.operation_type)

            # Populate dynamic fields
            if self._weapon_list:
                self._weapon_list.set_selected(op.weapons)
            if self._vehicle_list:
                self._vehicle_list.set_vehicles(
                    [{"name": v.name, "armored": v.armored} for v in op.vehicles]
                )
            if self._role_list:
                self._role_list.set_selected(op.roles)
            if self._equip_list:
                self._equip_list.set_selected(op.investigation_equipments)

    # ── Collect + submit ──────────────────────────────────────────────────────

    def _collect_data(self) -> Optional[dict]:
        name = self._name_var.get().strip()
        location = self._location_var.get().strip()
        description = self._desc_text.get("1.0", tk.END).strip()
        op_type = self._current_type

        if not name:
            dialogs.show_warning(self, "O campo Nome é obrigatório.")
            return None
        if not op_type:
            dialogs.show_warning(self, "Selecione um Tipo de Operação.")
            return None
        if not location:
            dialogs.show_warning(self, "O campo Localização é obrigatório.")
            return None

        weapons: list[str] = []
        vehicles: list[dict] = []
        roles: list[str] = []
        equipments: list[str] = []

        if op_type == "INVESTIGATIVE":
            weapons = ["pistola"]
            equipments = self._equip_list.get_selected() if self._equip_list else []
            roles = self._role_list.get_selected() if self._role_list else []
        else:
            weapons = self._weapon_list.get_selected() if self._weapon_list else []
            vehicles = self._vehicle_list.get_vehicles() if self._vehicle_list else []
            roles = self._role_list.get_selected() if self._role_list else []

        return {
            "name": name,
            "operation_type": op_type,
            "location": location,
            "description": description,
            "weapons": weapons,
            "vehicles": vehicles,
            "roles": roles,
            "investigation_equipments": equipments,
        }

    def _submit(self) -> None:
        payload = self._collect_data()
        if payload is None:
            return

        self._loading.show("Salvando operação…")

        def task():
            try:
                if self._edit_mode:
                    result = self._service.update(self._operation.id, payload)
                    msg = "Operação atualizada com sucesso!"
                else:
                    result = self._service.create(payload)
                    msg = "Operação criada com sucesso!"
                self.after(0, lambda: self._on_success(msg))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self.after(0, lambda: dialogs.show_connection_error(self, exc.message))
            except ApiValidationError as exc:
                self.after(0, lambda: dialogs.show_validation_error(self, exc.message))
            except ApiNotFoundError as exc:
                self.after(0, lambda: dialogs.show_not_found(self, exc.message))
            except ApiServerError as exc:
                self.after(0, lambda: dialogs.show_server_error(self, exc.message))
            finally:
                self.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _on_success(self, message: str) -> None:
        dialogs.show_success(self, message)
        self._on_save()
        self.destroy()
