class ApiClientError(RuntimeError):
    """Base exception for outbound API client failures."""


class ApiClientTimeoutError(ApiClientError):
    """Raised when the upstream request exceeds the configured timeout."""


class ApiClientHTTPStatusError(ApiClientError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiClientPayloadError(ApiClientError):
    """Raised when the upstream returns malformed or unsupported payloads."""

