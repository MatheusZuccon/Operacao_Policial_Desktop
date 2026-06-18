import tkinter as tk
from tkinter import messagebox


def confirm_delete(parent: tk.Widget, name: str) -> bool:
    """Ask the user to confirm a delete action. Returns True if confirmed."""
    return messagebox.askyesno(
        title="Confirmar Exclusão",
        message=f'Deseja realmente excluir a operação:\n\n"{name}"?\n\nEsta ação não pode ser desfeita.',
        icon="warning",
        parent=parent,
    )


def show_success(parent: tk.Widget, message: str, title: str = "Sucesso") -> None:
    messagebox.showinfo(title=title, message=message, parent=parent)


def show_error(parent: tk.Widget, message: str, title: str = "Erro") -> None:
    messagebox.showerror(title=title, message=message, parent=parent)


def show_warning(parent: tk.Widget, message: str, title: str = "Atenção") -> None:
    messagebox.showwarning(title=title, message=message, parent=parent)


def show_no_selection(parent: tk.Widget) -> None:
    show_warning(
        parent,
        "Selecione uma operação na tabela antes de prosseguir.",
        title="Nenhuma Operação Selecionada",
    )


def show_connection_error(parent: tk.Widget, detail: str = "") -> None:
    msg = "Não foi possível conectar ao servidor da API."
    if detail:
        msg += f"\n\nDetalhe: {detail}"
    msg += "\n\nVerifique se a Police Operation API está em execução."
    show_error(parent, msg, title="Erro de Conexão")


def show_validation_error(parent: tk.Widget, detail: str) -> None:
    show_error(parent, f"Dados inválidos:\n\n{detail}", title="Erro de Validação")


def show_not_found(parent: tk.Widget, detail: str = "") -> None:
    msg = "O registro solicitado não foi encontrado."
    if detail:
        msg += f"\n\n{detail}"
    show_error(parent, msg, title="Não Encontrado")


def show_server_error(parent: tk.Widget, detail: str = "") -> None:
    msg = "Ocorreu um erro interno no servidor."
    if detail:
        msg += f"\n\nDetalhe: {detail}"
    show_error(parent, msg, title="Erro do Servidor")


def confirm_pdf_open(parent: tk.Widget, filepath: str) -> bool:
    """Ask the user if they want to open the generated PDF."""
    return messagebox.askyesno(
        title="Relatório Gerado",
        message=f"Relatório salvo com sucesso!\n\nCaminho:\n{filepath}\n\nDeseja abrir o arquivo agora?",
        parent=parent,
    )
