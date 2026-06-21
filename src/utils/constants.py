from typing import Final

# ── Window ────────────────────────────────────────────────────────────────────
APP_TITLE: Final[str] = "Police Operation Desktop"
APP_WIDTH: Final[int] = 1280
APP_HEIGHT: Final[int] = 780
APP_MIN_WIDTH: Final[int] = 960
APP_MIN_HEIGHT: Final[int] = 620
SIDEBAR_WIDTH: Final[int] = 230

# ── API ───────────────────────────────────────────────────────────────────────
API_TIMEOUT: Final[int] = 15

# ── Operation Types ───────────────────────────────────────────────────────────
OPERATION_TYPES: Final[dict[str, str]] = {
    "OSTENSIVE": "Operações Ostensivas e Preservação da Ordem",
    "INVESTIGATIVE": "Operações de Polícia Judiciária e Investigativa",
    "TACTICAL": "Operações de Forças Táticas e Especiais",
}

TYPE_SHORT_LABELS: Final[dict[str, str]] = {
    "OSTENSIVE": "Ostensiva",
    "INVESTIGATIVE": "Investigativa",
    "TACTICAL": "Tática Especial",
}

# Display labels for the combo boxes (key → display label)
TYPE_DISPLAY_OPTIONS: Final[list[str]] = [
    "Ostensiva — Preservação da Ordem",
    "Investigativa — Polícia Judiciária",
    "Tática — Forças Especiais",
]

DISPLAY_TO_TYPE_KEY: Final[dict[str, str]] = {
    "Ostensiva — Preservação da Ordem": "OSTENSIVE",
    "Investigativa — Polícia Judiciária": "INVESTIGATIVE",
    "Tática — Forças Especiais": "TACTICAL",
}

TYPE_KEY_TO_DISPLAY: Final[dict[str, str]] = {
    v: k for k, v in DISPLAY_TO_TYPE_KEY.items()
}

# ── Domain Constants ──────────────────────────────────────────────────────────
VALID_WEAPONS: Final[list[str]] = [
    "pistola",
    "fuzil",
    "carabina",
    "espingarda",
    "submetralhadora",
    "rifle de precisão",
    "revólver",
    "metralhadora",
]

VALID_ROLES: Final[list[str]] = [
    "soldado",
    "cabo",
    "sargento",
    "tenente",
    "capitão",
    "major",
    "tenente-coronel",
    "coronel",
    "delegado",
    "investigador",
    "agente",
    "inspetor",
    "atirador de elite",
    "comandante tático",
    "especialista",
]

VALID_EQUIPMENTS: Final[list[str]] = [
    "câmera",
    "gravador",
    "laptop",
    "kit forense",
    "rastreador GPS",
    "visão noturna",
    "drone",
    "rádio comunicador",
    "binóculo",
    "kit de impressão digital",
    "kit de vigilância",
]

# ── Color Palette ─────────────────────────────────────────────────────────────
COLORS: Final[dict[str, str]] = {
    # backgrounds
    "bg_app": "#F0F4F8",
    "bg_content": "#FFFFFF",
    "bg_card": "#FFFFFF",
    "bg_sidebar": "#DCDCDC",         
    "bg_header": "#1E293B",
    "bg_input": "#FFFFFF",
    "bg_table_header": "#F1F5F9",
    "bg_row_even": "#FFFFFF",
    "bg_row_odd": "#F8FAFC",
    "bg_selected": "#DBEAFE",
    "bg_hover": "#EFF6FF",
    "bg_section": "#F8FAFC",
    # text
    "text_primary": "#1E293B",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",
    "text_header": "#F1F5F9",
    "text_accent": "#3B82F6",
    "text_danger": "#EF4444",
    "text_success": "#10B981",
    "sidebar_item_active": "#6B7280", # cinza escuro do item selecionado
    "text_sidebar": "#1F2937",
    "text_sidebar_active": "#FFFFFF",
    # borders
    "border": "#E2E8F0",
    "border_focus": "#3B82F6",
    "border_input": "#CBD5E1",
    # sidebar
    "sidebar_item_hover": "#64748B",
    "sidebar_divider": "#64748B",
    # buttons (action colors)
    "btn_primary": "#2563EB",
    "btn_primary_hover": "#1D4ED8",
    "btn_danger": "#DC2626",
    "btn_danger_hover": "#B91C1C",
    "btn_success": "#059669",
    "btn_success_hover": "#047857",
    "btn_secondary": "#64748B",
    "btn_secondary_hover": "#475569",
    "btn_warning": "#D97706",
    "btn_warning_hover": "#B45309",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONTS: Final[dict[str, tuple]] = {
    "app_title": ("Segoe UI", 15, "bold"),
    "heading_lg": ("Segoe UI", 14, "bold"),
    "heading_md": ("Segoe UI", 12, "bold"),
    "heading_sm": ("Segoe UI", 11, "bold"),
    "body_lg": ("Segoe UI", 12),
    "body_md": ("Segoe UI", 11),
    "body_sm": ("Segoe UI", 10),
    "label_bold": ("Segoe UI", 10, "bold"),
    "caption": ("Segoe UI", 9),
    "sidebar_title": ("Segoe UI", 12, "bold"),
    "sidebar_item": ("Segoe UI", 11),
    "table_header": ("Segoe UI", 10, "bold"),
    "table_body": ("Segoe UI", 10),
    "button": ("Segoe UI", 10, "bold"),
    "mono": ("Consolas", 10),
}
