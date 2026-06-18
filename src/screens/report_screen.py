import threading
import tkinter as tk

from src.services.operation_api_service import (
    OperationApiService,
    ApiConnectionError,
    ApiTimeoutError,
    ApiNotFoundError,
    ApiServerError,
)
from src.components.loading import LoadingOverlay
from src.components import dialogs
from src.utils.helpers import get_pdf_save_path, open_file


class ReportService:
    """
    Handles the full PDF report flow:
    1. Call GET /operations/{id}/report
    2. Save the bytes to the Downloads folder
    3. Ask the user if they want to open it
    """

    def __init__(self, parent: tk.Widget, api_service: OperationApiService) -> None:
        self._parent = parent
        self._api = api_service
        self._loading = LoadingOverlay(parent)

    def generate(self, operation_id: int, operation_name: str) -> None:
        """Trigger PDF generation in a background thread."""
        self._loading.show("Gerando relatório PDF…")

        save_path = get_pdf_save_path(operation_id, operation_name)

        def task():
            try:
                pdf_bytes = self._api.generate_report(operation_id)
                with open(save_path, "wb") as f:
                    f.write(pdf_bytes)
                self._parent.after(0, lambda: self._on_success(save_path))
            except (ApiConnectionError, ApiTimeoutError) as exc:
                self._parent.after(0, lambda: dialogs.show_connection_error(self._parent, exc.message))
            except ApiNotFoundError as exc:
                self._parent.after(0, lambda: dialogs.show_not_found(self._parent, exc.message))
            except ApiServerError as exc:
                self._parent.after(0, lambda: dialogs.show_server_error(self._parent, exc.message))
            except OSError as exc:
                self._parent.after(
                    0,
                    lambda: dialogs.show_error(
                        self._parent,
                        f"Não foi possível salvar o arquivo PDF:\n\n{exc}",
                        title="Erro ao Salvar PDF",
                    ),
                )
            finally:
                self._parent.after(0, self._loading.hide)

        threading.Thread(target=task, daemon=True).start()

    def _on_success(self, filepath: str) -> None:
        if dialogs.confirm_pdf_open(self._parent, filepath):
            open_file(filepath)
