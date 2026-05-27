"""Dynamic tool discovery for logseq-api-mcp.

Iterates *.py files in this directory, imports each, and exposes any public
function defined locally via __all__.

@complexity O(T*F) where T is module count and F is function count per module.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import List


_log = logging.getLogger(__name__)
_tools_dir = Path(__file__).parent
_discovered_tools: dict = {}
__all__: List[str] = []


def _emit_import_warning(module_name: str, exc: Exception) -> None:
    """Log a tool-discovery import failure without polluting stdout."""
    _log.warning("Could not import tool module %s: %s", module_name, exc)


for py_file in _tools_dir.glob("*.py"):
    if py_file.name.startswith("_"):
        continue
    module_name = py_file.stem
    try:
        module = importlib.import_module(f".{module_name}", package=__package__)
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if obj.__module__ != module.__name__:
                continue
            # Include ALL discovered tools (even @hidden ones) in __all__ so
            # tests can audit them and they remain importable. The MCP
            # registry filters hidden tools out at registration time —
            # see src/registry.py and src/tools/_marker.py.
            _discovered_tools[name] = obj
            __all__.append(name)
            globals()[name] = obj
    except ImportError as exc:
        _emit_import_warning(module_name, exc)

__all__.sort()
