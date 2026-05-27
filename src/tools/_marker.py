"""Decorator to hide a tool from MCP registration.

Apply ``@hidden`` to any tool function that should NOT be exposed through
the MCP server. Hidden tools STAY in ``tools.__all__`` (so they remain
importable for tests and direct callers); the filter lives in
``src/registry.py``, which skips any function with a truthy
``_mcp_hidden`` attribute at registration time.

To un-hide a tool: remove or comment out the ``@hidden`` line (and the
import). The function itself stays callable from tests and other code —
hiding only affects MCP tool listing.

This file starts with ``_`` so the discovery loop ignores it.
"""

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def hidden(fn: F) -> F:
    """Mark a tool function as hidden from MCP registration."""
    fn._mcp_hidden = True  # type: ignore[attr-defined]
    return fn
