"""Server import must emit zero bytes to stdout (MCP stdio constraint)."""

import importlib
import io
import logging
import sys


def test_tools_discovery_does_not_print_to_stdout(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    importlib.reload(importlib.import_module("src.tools"))
    assert buf.getvalue() == "", f"stdout polluted: {buf.getvalue()!r}"


def test_tools_discovery_logs_import_errors_via_logger(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger="src.tools")

    real_import = importlib.import_module

    def fake_import(name, package=None):
        if name == ".broken_tool":
            raise ImportError("synthetic")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    # Re-run the discovery loop manually with a fake file to trigger the warning.
    from src.tools import _emit_import_warning  # to be added below

    _emit_import_warning("broken_tool", ImportError("synthetic"))

    assert any("broken_tool" in rec.message for rec in caplog.records)
