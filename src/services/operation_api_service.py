import os
import requests
from dotenv import load_dotenv
from src.utils.constants import API_TIMEOUT

load_dotenv()


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class ApiError(Exception):
    """Base exception for all API communication errors."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ApiConnectionError(ApiError):
    """Raised when the API server cannot be reached."""
    def __init__(self, message: str = "Não foi possível conectar à API. Verifique se o servidor está rodando.") -> None:
        super().__init__(message)


class ApiTimeoutError(ApiError):
    """Raised when the request times out."""
    def __init__(self) -> None:
        super().__init__("Tempo de resposta esgotado. Verifique a conexão e tente novamente.")


class ApiValidationError(ApiError):
    """Raised when the API rejects the payload (HTTP 400)."""
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class ApiNotFoundError(ApiError):
    """Raised when the requested resource does not exist (HTTP 404)."""
    def __init__(self, message: str = "Operação não encontrada.") -> None:
        super().__init__(message, status_code=404)


class ApiServerError(ApiError):
    """Raised on HTTP 5xx errors."""
    def __init__(self, message: str = "Erro interno do servidor. Tente novamente.") -> None:
        super().__init__(message, status_code=500)


# ── Service ────────────────────────────────────────────────────────────────────

class OperationApiService:
    """Handles all HTTP communication with the Police Operation API."""

    def __init__(self) -> None:
        self.base_url: str = os.getenv("API_BASE_URL", "http://localhost:5000").rstrip("/")
        self.timeout: int = API_TIMEOUT

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        try:
            return requests.request(method, url, timeout=self.timeout, **kwargs)
        except requests.ConnectionError:
            raise ApiConnectionError()
        except requests.Timeout:
            raise ApiTimeoutError()
        except requests.RequestException as exc:
            raise ApiConnectionError(f"Erro de rede: {exc}")

    def _parse(self, response: requests.Response) -> dict:
        """Parse a JSON response and raise a typed exception on failure."""
        try:
            data = response.json()
        except Exception:
            raise ApiServerError("A resposta da API não é um JSON válido.")

        if response.status_code == 404:
            raise ApiNotFoundError(data.get("error", "Registro não encontrado."))
        if response.status_code == 400:
            raise ApiValidationError(data.get("error", "Dados inválidos."))
        if response.status_code >= 500:
            raise ApiServerError(data.get("error", "Erro interno do servidor."))
        if not data.get("success"):
            raise ApiValidationError(data.get("error", "Operação não foi bem-sucedida."))

        return data

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """GET /operations → list of operation dicts."""
        response = self._request("GET", "/operations")
        data = self._parse(response)
        return data.get("data") or []

    def get_by_id(self, operation_id: int) -> dict:
        """GET /operations/{id} → single operation dict."""
        response = self._request("GET", f"/operations/{operation_id}")
        data = self._parse(response)
        return data.get("data") or {}

    def create(self, payload: dict) -> dict:
        """POST /operations → created operation dict."""
        response = self._request("POST", "/operations", json=payload)
        data = self._parse(response)
        return data.get("data") or {}

    def update(self, operation_id: int, payload: dict) -> dict:
        """PUT /operations/{id} → updated operation dict."""
        response = self._request("PUT", f"/operations/{operation_id}", json=payload)
        data = self._parse(response)
        return data.get("data") or {}

    def delete(self, operation_id: int) -> None:
        """DELETE /operations/{id}."""
        response = self._request("DELETE", f"/operations/{operation_id}")
        self._parse(response)

    def generate_report(self, operation_id: int) -> bytes:
        """GET /operations/{id}/report → raw PDF bytes."""
        response = self._request("GET", f"/operations/{operation_id}/report")
        if response.status_code == 404:
            try:
                data = response.json()
                raise ApiNotFoundError(data.get("error", "Operação não encontrada."))
            except (ValueError, ApiNotFoundError):
                raise ApiNotFoundError()
        if response.status_code >= 400:
            raise ApiServerError("Erro ao gerar o relatório PDF.")
        return response.content
