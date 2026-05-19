"""Logseq HTTP API exception hierarchy."""


class LogseqAPIError(Exception):
    """Base class for any Logseq HTTP API failure with a status code.

    @param message     Human-readable description.
    @param status_code HTTP status code if applicable.
    @complexity O(1).
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LogseqAuthError(LogseqAPIError):
    """401 Unauthorized — bad or missing Bearer token."""


class LogseqNotFoundError(LogseqAPIError):
    """404 Not Found — unknown method or missing entity."""


class LogseqConnectionError(LogseqAPIError):
    """Network failure — connection refused, DNS failure, socket timeout.

    Not raised for HTTP-level errors; those become LogseqAPIError subclasses.
    """
