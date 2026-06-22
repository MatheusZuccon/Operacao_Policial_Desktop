import threading
import tkinter as tk
import re
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

# Regex that matches strings containing at least one letter (accented included)
_HAS_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")

def _validate_text_field(parent: Optional[tk.Widget], value: str, field_label: str, max_length: Optional[int] = None) -> bool:
    """Validate a text field: min 3 chars, at least one letter, optional max length."""
    stripped = value.strip()
    if len(stripped) < 3:
        dialogs.show_warning(parent, f"O campo '{field_label}' deve ter no mínimo 3 caracteres.")
        return False
    if not _HAS_LETTER_RE.search(stripped):
        dialogs.show_warning(parent, f"O campo '{field_label}' não pode conter apenas números ou caracteres especiais. Informe um texto com ao menos uma letra.")
        return False
    if max_length is not None and len(stripped) > max_length:
        dialogs.show_warning(parent, f"O campo '{field_label}' deve ter no máximo {max_length} caracteres.")
        return False
    return True


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


class _CheckboxQuantityList(tk.Frame):
    """Scrollable list of items with checkboxes and quantities (1 to 99)."""

    def __init__(self, parent: tk.Widget, items: list[str], height: int = 150, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_section"], relief=tk.FLAT, **kw)
        self._items = items
        self._entries: dict[str, tuple[tk.BooleanVar, tk.StringVar, ttk.Entry, tk.Checkbutton]] = {}
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

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for item in items:
            row_frame = tk.Frame(inner, bg=COLORS["bg_section"])
            row_frame.pack(fill=tk.X, expand=True, padx=8, pady=4)

            var = tk.BooleanVar(value=False)
            qty_var = tk.StringVar(value="1")

            # Max 2 digits constraint for quantity
            def enforce_qty(*args, qvar=qty_var):
                val = qvar.get()
                digits = "".join(c for c in val if c.isdigit())
                if len(digits) > 2:
                    digits = digits[:2]
                qvar.set(digits)

            qty_var.trace_add("write", enforce_qty)

            cb = tk.Checkbutton(
                row_frame,
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
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(
                row_frame,
                text="Qtd:",
                font=FONTS["caption"],
                bg=COLORS["bg_section"],
                fg=COLORS["text_secondary"]
            ).pack(side=tk.LEFT, padx=(10, 4))

            qty_entry = ttk.Entry(
                row_frame,
                textvariable=qty_var,
                font=FONTS["body_sm"],
                width=5,
                state=tk.DISABLED
            )
            qty_entry.pack(side=tk.LEFT)

            def make_toggle_callback(item_name, entry_ctrl, check_var):
                def on_toggle():
                    if check_var.get():
                        entry_ctrl.configure(state=tk.NORMAL)
                    else:
                        entry_ctrl.configure(state=tk.DISABLED)
                return on_toggle

            cb.configure(command=make_toggle_callback(item, qty_entry, var))

            self._entries[item] = (var, qty_var, qty_entry, cb)

    def get_selected(self) -> list[dict]:
        selected = []
        for item, (var, qty_var, _, _) in self._entries.items():
            if var.get():
                try:
                    qty = int(qty_var.get())
                except ValueError:
                    qty = 1
                selected.append({
                    "name": item,
                    "quantity": qty
                })
        return selected

    def set_selected(self, items: list) -> None:
        self.reset()
        for it in items:
            if isinstance(it, dict):
                name = it.get("weapon") or it.get("equipment") or it.get("name")
                qty = it.get("quantity", 1)
            elif hasattr(it, "weapon"):
                name = it.weapon
                qty = it.quantity
            elif hasattr(it, "equipment"):
                name = it.equipment
                qty = it.quantity
            else:
                name = str(it)
                qty = 1

            if name in self._entries:
                var, qty_var, qty_entry, _ = self._entries[name]
                var.set(True)
                qty_var.set(str(qty))
                qty_entry.configure(state=tk.NORMAL)

    def reset(self) -> None:
        for var, qty_var, qty_entry, _ in self._entries.values():
            var.set(False)
            qty_var.set("1")
            qty_entry.configure(state=tk.DISABLED)


class _RoleOfficerList(tk.Frame):
    """Widget for adding/removing officers for a specific role."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_section"], **kw)
        self._officers: list[str] = []
        self._build()

    def _build(self) -> None:
        # Input row: officer name + add button
        input_row = tk.Frame(self, bg=COLORS["bg_section"])
        input_row.pack(fill=tk.X, pady=(4, 4))

        tk.Label(
            input_row,
            text="Nome do Policial:",
            font=FONTS["caption"],
            bg=COLORS["bg_section"],
            fg=COLORS["text_secondary"]
        ).pack(side=tk.LEFT, padx=(0, 4))

        self._officer_name_var = tk.StringVar()
        self._officer_entry = ttk.Entry(input_row, textvariable=self._officer_name_var, width=30)
        self._officer_entry.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        self._officer_entry.bind("<Return>", lambda _: self._add_officer())

        ttk.Button(
            input_row,
            text="+ Adicionar",
            command=self._add_officer,
            bootstyle="outline-primary",
            width=12
        ).pack(side=tk.LEFT)

        # Treeview to show officers
        tree_frame = tk.Frame(self, bg=COLORS["bg_section"])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        cols = ("nome",)
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=3)
        self._tree.heading("nome", text="Policiais")
        self._tree.column("nome", width=300, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Remove button
        ttk.Button(
            self,
            text="🗑 Remover Selecionado",
            command=self._remove_officer,
            bootstyle="outline-danger"
        ).pack(anchor=tk.E)

    def _add_officer(self) -> None:
        name = self._officer_name_var.get().strip()
        if not name:
            dialogs.show_warning(self, "Informe o nome do policial.")
            return
        if not _validate_text_field(self, name, "nome do policial", max_length=150):
            return
        if name in self._officers:
            dialogs.show_warning(self, f"O policial '{name}' já foi adicionado.")
            return

        self._officers.append(name)
        self._tree.insert("", tk.END, values=(name,))
        self._officer_name_var.set("")
        self._officer_entry.focus()

    def _remove_officer(self) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        for item in selected:
            idx = self._tree.index(item)
            if 0 <= idx < len(self._officers):
                self._officers.pop(idx)
            self._tree.delete(item)

    def get_officers(self) -> list[str]:
        return list(self._officers)

    def set_officers(self, officers: list[str]) -> None:
        self._officers = []
        for item in self._tree.get_children():
            self._tree.delete(item)
        for name in officers:
            self._officers.append(name)
            self._tree.insert("", tk.END, values=(name,))

    def reset(self) -> None:
        self._officers = []
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._officer_name_var.set("")


class _RoleCheckboxList(tk.Frame):
    """Scrollable list of roles with checkboxes, quantities (1-99), and officer list."""

    def __init__(self, parent: tk.Widget, items: list[str], height: int = 350, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_section"], relief=tk.FLAT, **kw)
        self._items = items
        self._entries: dict[str, tuple[tk.BooleanVar, tk.StringVar, _RoleOfficerList, ttk.Entry, tk.Checkbutton, tk.Frame]] = {}
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

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for item in items:
            role_frame = tk.Frame(inner, bg=COLORS["bg_section"])
            role_frame.pack(fill=tk.X, expand=True, padx=8, pady=4)

            # Top row: checkbox + quantity
            top_row = tk.Frame(role_frame, bg=COLORS["bg_section"])
            top_row.pack(fill=tk.X)

            var = tk.BooleanVar(value=False)
            qty_var = tk.StringVar(value="1")

            def enforce_qty(*args, qvar=qty_var):
                val = qvar.get()
                digits = "".join(c for c in val if c.isdigit())
                if len(digits) > 2:
                    digits = digits[:2]
                qvar.set(digits)

            qty_var.trace_add("write", enforce_qty)

            cb = tk.Checkbutton(
                top_row,
                text=f"  {item.capitalize()}",
                variable=var,
                font=FONTS["body_sm"],
                bg=COLORS["bg_section"],
                fg=COLORS["text_primary"],
                activebackground=COLORS["bg_section"],
                selectcolor=COLORS["bg_section"],
                relief=tk.FLAT,
                anchor=tk.W,
                width=16
            )
            cb.pack(side=tk.LEFT)

            tk.Label(
                top_row,
                text="Qtd:",
                font=FONTS["caption"],
                bg=COLORS["bg_section"],
                fg=COLORS["text_secondary"]
            ).pack(side=tk.LEFT, padx=(6, 2))

            qty_entry = ttk.Entry(
                top_row,
                textvariable=qty_var,
                font=FONTS["body_sm"],
                width=4,
                state=tk.DISABLED
            )
            qty_entry.pack(side=tk.LEFT)

            # Officer list container (shown when checkbox is active)
            officer_list_frame = tk.Frame(role_frame, bg=COLORS["bg_section"])
            officer_list = _RoleOfficerList(officer_list_frame)
            
            def make_toggle_callback(q_ctrl, o_frame, check_var):
                def on_toggle():
                    state = tk.NORMAL if check_var.get() else tk.DISABLED
                    q_ctrl.configure(state=state)
                    if check_var.get():
                        o_frame.pack(fill=tk.X, pady=(8, 0))
                    else:
                        o_frame.pack_forget()
                return on_toggle

            cb.configure(command=make_toggle_callback(qty_entry, officer_list_frame, var))
            officer_list.pack(fill=tk.X, expand=True)

            self._entries[item] = (var, qty_var, officer_list, qty_entry, cb, officer_list_frame)

    def get_selected(self) -> list[dict]:
        selected = []
        for item, (var, qty_var, officer_list, _, _, _) in self._entries.items():
            if var.get():
                try:
                    qty = int(qty_var.get())
                except ValueError:
                    qty = 1
                
                officers = officer_list.get_officers()
                
                selected.append({
                    "role": item,
                    "quantity": qty,
                    "officers": officers
                })
        return selected

    def set_selected(self, items: list) -> None:
        self.reset()
        for it in items:
            if isinstance(it, dict):
                role = it.get("role") or it.get("name")
                qty = it.get("quantity", 1)
                officers = it.get("officers", [])
            elif hasattr(it, "role"):
                role = it.role
                qty = it.quantity
                officers = it.officers
            else:
                role = str(it)
                qty = 1
                officers = ["Policial Legado"]

            if role in self._entries:
                var, qty_var, officer_list, q_entry, _, officer_frame = self._entries[role]
                var.set(True)
                qty_var.set(str(qty))
                officer_list.set_officers(officers)
                q_entry.configure(state=tk.NORMAL)
                officer_frame.pack(fill=tk.X, pady=(8, 0))

    def reset(self) -> None:
        for var, qty_var, officer_list, q_entry, _, officer_frame in self._entries.values():
            var.set(False)
            qty_var.set("1")
            officer_list.reset()
            q_entry.configure(state=tk.DISABLED)
            officer_frame.pack_forget()


class _VehicleList(tk.Frame):
    """Widget for adding/removing vehicles with brand, model, plate, armored."""

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, bg=COLORS["bg_content"], **kw)
        self._vehicles: list[dict] = []
        self._build()

    def _build(self) -> None:
        # ── Input row 1 (Brand & Model) ───────────────────────────────────────
        row1 = tk.Frame(self, bg=COLORS["bg_content"])
        row1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            row1, text="Marca *", font=FONTS["body_sm"],
            bg=COLORS["bg_content"], fg=COLORS["text_secondary"],
            width=8, anchor=tk.W
        ).pack(side=tk.LEFT)

        self._brand_var = tk.StringVar()
        def limit_brand(*args):
            v = self._brand_var.get()
            if len(v) > 20:
                self._brand_var.set(v[:20])
        self._brand_var.trace_add("write", limit_brand)

        self._brand_entry = ttk.Entry(row1, textvariable=self._brand_var, width=16)
        self._brand_entry.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(
            row1, text="Modelo *", font=FONTS["body_sm"],
            bg=COLORS["bg_content"], fg=COLORS["text_secondary"],
            width=8, anchor=tk.W
        ).pack(side=tk.LEFT)

        self._model_var = tk.StringVar()
        def limit_model(*args):
            v = self._model_var.get()
            if len(v) > 20:
                self._model_var.set(v[:20])
        self._model_var.trace_add("write", limit_model)

        self._model_entry = ttk.Entry(row1, textvariable=self._model_var, width=16)
        self._model_entry.pack(side=tk.LEFT)

        # ── Input row 2 (Plate & Armored & Add Button) ────────────────────────
        row2 = tk.Frame(self, bg=COLORS["bg_content"])
        row2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            row2, text="Placa *", font=FONTS["body_sm"],
            bg=COLORS["bg_content"], fg=COLORS["text_secondary"],
            width=8, anchor=tk.W
        ).pack(side=tk.LEFT)

        self._plate_var = tk.StringVar()
        def format_plate(*args):
            v = self._plate_var.get().upper()
            clean = "".join(c for c in v if c.isalnum())
            if len(clean) > 7:
                clean = clean[:7]
            self._plate_var.set(clean)
        self._plate_var.trace_add("write", format_plate)

        self._plate_entry = ttk.Entry(row2, textvariable=self._plate_var, width=16)
        self._plate_entry.pack(side=tk.LEFT, padx=(0, 15))
        self._plate_entry.bind("<Return>", lambda _: self._add())

        self._armored_var = tk.BooleanVar()
        tk.Checkbutton(
            row2, text="Blindada", variable=self._armored_var,
            font=FONTS["body_sm"], bg=COLORS["bg_content"],
            fg=COLORS["text_primary"], activebackground=COLORS["bg_content"],
            selectcolor=COLORS["bg_content"], relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(
            row2, text="+ Adicionar",
            command=self._add, bootstyle="outline-primary", width=12,
        ).pack(side=tk.LEFT)

        # ── Treeview ──────────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=COLORS["bg_content"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("marca", "modelo", "placa", "blindada")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
        self._tree.heading("marca", text="Marca")
        self._tree.heading("modelo", text="Modelo")
        self._tree.heading("placa", text="Placa")
        self._tree.heading("blindada", text="Blindada")
        self._tree.column("marca", width=120, anchor=tk.W)
        self._tree.column("modelo", width=140, anchor=tk.W)
        self._tree.column("placa", width=100, anchor=tk.CENTER)
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
        brand = self._brand_var.get().strip()
        model = self._model_var.get().strip()
        plate = self._plate_var.get().strip().upper()
        armored = self._armored_var.get()

        if not brand:
            dialogs.show_warning(self, "Informe a marca da viatura.")
            return
        if not _validate_text_field(self, brand, "marca da viatura", max_length=20):
            return
        if not model:
            dialogs.show_warning(self, "Informe o modelo da viatura.")
            return
        if not _validate_text_field(self, model, "modelo da viatura", max_length=20):
            return
        if not plate:
            dialogs.show_warning(self, "Informe a placa da viatura.")
            return

        # Validation Regex (ABC1234 or ABC1D23)
        plate_regex = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")
        if not plate_regex.match(plate):
            dialogs.show_warning(
                self,
                "Formato de placa inválido. Exemplos aceitos:\n- ABC1234 (antigo)\n- ABC1D23 (Mercosul)"
            )
            return

        # Check duplicate plates locally
        for v in self._vehicles:
            if v["plate"].upper() == plate:
                dialogs.show_warning(self, f"A placa '{plate}' já foi adicionada.")
                return

        self._vehicles.append({
            "brand": brand,
            "model": model,
            "plate": plate,
            "armored": armored
        })
        self._tree.insert("", tk.END, values=(brand, model, plate, "Sim" if armored else "Não"))
        self._brand_var.set("")
        self._model_var.set("")
        self._plate_var.set("")
        self._armored_var.set(False)
        self._brand_entry.focus()

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

    def set_vehicles(self, vehicles: list) -> None:
        self._vehicles = []
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        for v in vehicles:
            if isinstance(v, dict):
                brand = v.get("brand", "")
                model = v.get("model", "")
                plate = v.get("plate", "")
                armored = bool(v.get("armored", False))
            else:
                brand = getattr(v, "brand", "")
                model = getattr(v, "model", getattr(v, "name", ""))
                plate = getattr(v, "plate", "")
                armored = getattr(v, "armored", False)

            entry = {
                "brand": brand,
                "model": model,
                "plate": plate,
                "armored": armored
            }
            self._vehicles.append(entry)
            self._tree.insert("", tk.END, values=(brand, model, plate, "Sim" if armored else "Não"))

    def reset(self) -> None:
        self._vehicles = []
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        self._brand_var.set("")
        self._model_var.set("")
        self._plate_var.set("")
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

        # ── Widget references ─────────────────────────────────────────────────
        self._weapon_list: Optional[_CheckboxQuantityList] = None
        self._vehicle_list: Optional[_VehicleList] = None
        self._role_list: Optional[_RoleCheckboxList] = None
        self._equip_list: Optional[_CheckboxQuantityList] = None
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

        # ── Bottom buttons ────────────────────────────────────────────────────
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
        def limit_name(*args):
            v = self._name_var.get()
            if len(v) > 150:
                self._name_var.set(v[:150])
        self._name_var.trace_add("write", limit_name)

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
        def limit_location(*args):
            v = self._location_var.get()
            if len(v) > 150:
                self._location_var.set(v[:150])
        self._location_var.trace_add("write", limit_location)

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

        # Description length limit trace (500 characters)
        def limit_desc(event):
            content = self._desc_text.get("1.0", "end-1c")
            if len(content) > 500:
                self._desc_text.delete("1.0 + 500 chars", tk.END)
        self._desc_text.bind("<KeyRelease>", limit_desc)

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
        self._section_title(parent, "🔫 Armamentos", "(mín. 1, quantidade 1-99)")
        self._weapon_list = _CheckboxQuantityList(parent, VALID_WEAPONS)
        self._weapon_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "🚗 Viaturas", "(mín. 1, placa Mercosul/antiga única)")
        self._vehicle_list = _VehicleList(parent)
        self._vehicle_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 1, quantidade = policiais)")
        self._role_list = _RoleCheckboxList(parent, VALID_ROLES)
        self._role_list.pack(fill=tk.X)

    def _build_investigative_section(self, parent: tk.Frame) -> None:
        self._section_title(parent, "🔫 Quantidade de Pistolas", "(mín. 1, quantidade 1-99)")
        pistol_row = tk.Frame(parent, bg=COLORS["bg_content"])
        pistol_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            pistol_row, text="Pistolas *", width=14, anchor=tk.W,
            font=FONTS["label_bold"], bg=COLORS["bg_content"],
            fg=COLORS["text_secondary"],
        ).pack(side=tk.LEFT)
        self._pistol_quantity_var = tk.StringVar(value="1")
        def limit_pistol_qty(*args):
            v = self._pistol_quantity_var.get()
            digits = "".join(c for c in v if c.isdigit())
            if len(digits) > 2:
                digits = digits[:2]
            self._pistol_quantity_var.set(digits)
        self._pistol_quantity_var.trace_add("write", limit_pistol_qty)
        ttk.Entry(
            pistol_row, textvariable=self._pistol_quantity_var, font=FONTS["body_sm"], width=10
        ).pack(side=tk.LEFT)

        self._section_title(parent, "🚗 Viaturas", "(mín. 1, placa Mercosul/antiga única)")
        self._vehicle_list = _VehicleList(parent)
        self._vehicle_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "🔬 Equipamentos Investigativos", "(mín. 1, quantidade 1-99)")
        self._equip_list = _CheckboxQuantityList(parent, VALID_EQUIPMENTS)
        self._equip_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 1, quantidade = policiais)")
        self._role_list = _RoleCheckboxList(parent, VALID_ROLES)
        self._role_list.pack(fill=tk.X)

    def _build_tactical_section(self, parent: tk.Frame) -> None:
        self._section_title(parent, "🔫 Armamentos", "(mín. 5, quantidade 1-99)")
        self._weapon_list = _CheckboxQuantityList(parent, VALID_WEAPONS)
        self._weapon_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "🚗 Viaturas", "(mín. 2, placa Mercosul/antiga única)")
        self._vehicle_list = _VehicleList(parent)
        self._vehicle_list.pack(fill=tk.X, pady=(0, 8))

        self._section_title(parent, "👮 Cargos", "(mín. 5, quantidade = policiais)")
        self._role_list = _RoleCheckboxList(parent, VALID_ROLES)
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
                self._vehicle_list.set_vehicles(op.vehicles)
            if self._role_list:
                self._role_list.set_selected(op.roles)
            if self._equip_list:
                self._equip_list.set_selected(op.investigation_equipments)
            # Populate pistol quantity for INVESTIGATIVE
            if op.operation_type == "INVESTIGATIVE" and op.weapons:
                pistol = next((w for w in op.weapons if w.weapon == "pistola"), None)
                if pistol:
                    self._pistol_quantity_var.set(str(pistol.quantity))

    # ── Collect + submit ──────────────────────────────────────────────────────

    def _collect_data(self) -> Optional[dict]:
        name = self._name_var.get().strip()
        location = self._location_var.get().strip()
        description = self._desc_text.get("1.0", tk.END).strip()
        op_type = self._current_type

        if not name:
            dialogs.show_warning(self, "O campo Nome é obrigatório.")
            return None
        if not _validate_text_field(self, name, "nome da operação", max_length=150):
            return None
        if not op_type:
            dialogs.show_warning(self, "Selecione um Tipo de Operação.")
            return None
        if not location:
            dialogs.show_warning(self, "O campo Localização é obrigatório.")
            return None
        if not _validate_text_field(self, location, "localização", max_length=150):
            return None

        weapons: list[dict] = []
        vehicles: list[dict] = []
        roles: list[dict] = []
        equipments: list[dict] = []

        if op_type == "INVESTIGATIVE":
            # Get pistol quantity from input
            pistol_qty_str = self._pistol_quantity_var.get()
            try:
                pistol_qty = int(pistol_qty_str)
            except ValueError:
                pistol_qty = 0
            weapons = [{"weapon": "pistola", "quantity": pistol_qty}]
            raw_equip = self._equip_list.get_selected() if self._equip_list else []
            equipments = [{"equipment": eq["name"], "quantity": eq["quantity"]} for eq in raw_equip]
            vehicles = self._vehicle_list.get_vehicles() if self._vehicle_list else []
            roles = self._role_list.get_selected() if self._role_list else []
        else:
            raw_weap = self._weapon_list.get_selected() if self._weapon_list else []
            weapons = [{"weapon": w["name"], "quantity": w["quantity"]} for w in raw_weap]
            vehicles = self._vehicle_list.get_vehicles() if self._vehicle_list else []
            roles = self._role_list.get_selected() if self._role_list else []

        # Validate Weapons quantity in frontend: 1 to 99
        for w in weapons:
            qty = w["quantity"]
            if qty < 1 or qty > 99:
                dialogs.show_warning(self, f"A quantidade do armamento '{w['weapon'].capitalize()}' deve estar entre 1 e 99.")
                return None

        # Validate Equipments quantity: 1 to 99
        for e in equipments:
            qty = e["quantity"]
            if qty < 1 or qty > 99:
                dialogs.show_warning(self, f"A quantidade do equipamento '{e['equipment'].capitalize()}' deve estar entre 1 e 99.")
                return None

        # Validate Roles quantity and officers count in frontend
        for r in roles:
            role_name = r["role"]
            qty = r["quantity"]
            officers = r["officers"]
            
            if qty < 1 or qty > 99:
                dialogs.show_warning(self, f"A quantidade do cargo '{role_name.capitalize()}' deve estar entre 1 e 99.")
                return None
            
            if len(officers) != qty:
                dialogs.show_warning(
                    self, 
                    f"No cargo '{role_name.capitalize()}', a quantidade informada ({qty}) é diferente do número de policiais cadastrados ({len(officers)})."
                )
                return None
            
            for officer in officers:
                if not officer.strip():
                    dialogs.show_warning(self, f"O nome de cada policial no cargo '{role_name.capitalize()}' é obrigatório.")
                    return None
                if not _validate_text_field(self, officer, f"policial no cargo '{role_name.capitalize()}'", max_length=150):
                    return None

        # Check vehicles plate uniqueness inside the list (though local add does it, just in case)
        plates = [v["plate"].upper() for v in vehicles]
        if len(plates) != len(set(plates)):
            dialogs.show_warning(self, "Placas duplicadas detectadas nas viaturas.")
            return None

        # Business validations:
        # OSTENSIVE: min 1 vehicle, min 1 weapon, min 1 role
        if op_type == "OSTENSIVE":
            if not vehicles:
                dialogs.show_warning(self, "Uma operação ostensiva deve possuir ao menos 1 viatura.")
                return None
            if not weapons:
                dialogs.show_warning(self, "Uma operação ostensiva deve possuir ao menos 1 armamento.")
                return None
            if not roles:
                dialogs.show_warning(self, "Uma operação ostensiva deve possuir ao menos 1 cargo.")
                return None
                
        # INVESTIGATIVE: min 1 weapon (pistola), min 1 vehicle, min 1 equipment, min 1 role
        elif op_type == "INVESTIGATIVE":
            if not vehicles:
                dialogs.show_warning(self, "Uma operação investigativa deve possuir ao menos 1 viatura.")
                return None
            if not equipments:
                dialogs.show_warning(self, "Uma operação investigativa deve possuir ao menos 1 equipamento investigativo.")
                return None
            if not roles:
                dialogs.show_warning(self, "Uma operação investigativa deve possuir ao menos 1 cargo.")
                return None

        # TACTICAL: min 2 vehicles, min 5 weapons (unique types), min 5 roles (unique types)
        elif op_type == "TACTICAL":
            if len(vehicles) < 2:
                dialogs.show_warning(self, "Uma operação de forças táticas e especiais deve possuir ao menos 2 viaturas.")
                return None
            if len(weapons) < 5:
                dialogs.show_warning(self, "Uma operação de forças táticas e especiais deve possuir ao menos 5 armamentos.")
                return None
            if len(roles) < 5:
                dialogs.show_warning(self, "Uma operação de forças táticas e especiais deve possuir ao menos 5 cargos.")
                return None

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
