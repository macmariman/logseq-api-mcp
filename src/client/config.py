"""Logseq client configuration."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LogseqConfig:
    """Immutable configuration for the Logseq HTTP client.

    Args:
        endpoint: Full API endpoint URL including /api path.
        token: Bearer token for authorization.
        verify_ssl: Whether to verify TLS certificates.
        db_mode: Whether the Logseq instance runs in DB mode.
        exclude_tags: Page tags that should be hidden from all tools.

    Complexity: O(1) construction.
    """

    endpoint: str
    token: str
    verify_ssl: bool = False
    db_mode: bool = False
    exclude_tags: tuple[str, ...] = field(default_factory=tuple)


def load_config() -> LogseqConfig:
    """Load LogseqConfig from environment variables.

    Reads LOGSEQ_API_TOKEN (required), LOGSEQ_API_ENDPOINT or LOGSEQ_API_URL,
    LOGSEQ_VERIFY_SSL, LOGSEQ_DB_MODE, and LOGSEQ_EXCLUDE_TAGS.

    Returns:
        LogseqConfig populated from environment.

    Raises:
        ValueError: If LOGSEQ_API_TOKEN is not set.

    Complexity: O(E) where E is number of exclude tags.
    """
    token = os.getenv("LOGSEQ_API_TOKEN", "")
    if not token:
        raise ValueError("LOGSEQ_API_TOKEN environment variable is required but not set.")

    # Resolve endpoint: explicit full URL takes priority, then base URL, then default
    endpoint = os.getenv("LOGSEQ_API_ENDPOINT", "")
    if not endpoint:
        base_url = os.getenv("LOGSEQ_API_URL", "")
        if base_url:
            endpoint = base_url.rstrip("/") + "/api"
        else:
            endpoint = "http://127.0.0.1:12315/api"

    # SSL: explicit env var overrides scheme-based default
    verify_ssl_env = os.getenv("LOGSEQ_VERIFY_SSL", "")
    if verify_ssl_env:
        verify_ssl = verify_ssl_env.lower() not in ("0", "false", "no")
    else:
        verify_ssl = endpoint.startswith("https")

    db_mode = os.getenv("LOGSEQ_DB_MODE", "").lower() in ("1", "true", "yes")

    raw_tags = os.getenv("LOGSEQ_EXCLUDE_TAGS", "")
    exclude_tags: tuple[str, ...] = tuple(
        t.strip() for t in raw_tags.split(",") if t.strip()
    ) if raw_tags else ()

    return LogseqConfig(
        endpoint=endpoint,
        token=token,
        verify_ssl=verify_ssl,
        db_mode=db_mode,
        exclude_tags=exclude_tags,
    )
