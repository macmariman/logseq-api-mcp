"""Logseq API exception hierarchy."""


class LogseqAPIError(Exception):
    """Base for all Logseq HTTP API errors.

    Args:
        message: Human-readable description.
        status_code: HTTP status code if applicable.

    Complexity: O(1).
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LogseqNotFoundError(LogseqAPIError):
    """Raised when a requested page or block does not exist (HTTP 404)."""


class LogseqAuthError(LogseqAPIError):
    """Raised when the API token is missing or invalid (HTTP 401/403)."""


class LogseqConnectionError(LogseqAPIError):
    """Raised when the Logseq HTTP server cannot be reached."""
