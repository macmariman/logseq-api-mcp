"""Tests for logging setup and fallback behaviour."""

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.logging_setup import setup_logging, get_logger


class TestSetupLogging:
    def test_setup_logging_returns_logger(self, tmp_path):
        logger = setup_logging(log_dir=tmp_path)
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_creates_log_file(self, tmp_path):
        setup_logging(log_dir=tmp_path)
        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) >= 1

    def test_setup_logging_fallback_to_stderr_on_permission_error(self):
        """When log_dir cannot be created, logging falls back to stderr without raising."""
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("no access")):
            logger = setup_logging(log_dir=Path("/nonexistent/readonly/path"))
        assert isinstance(logger, logging.Logger)

    def test_log_level_controlled_by_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOGSEQ_LOG_LEVEL", "DEBUG")
        logger = setup_logging(log_dir=tmp_path)
        assert logger.level <= logging.DEBUG

    def test_log_level_default_is_warning(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOGSEQ_LOG_LEVEL", raising=False)
        logger = setup_logging(log_dir=tmp_path)
        assert logger.level <= logging.WARNING

    def test_get_logger_returns_child_logger(self):
        child = get_logger("test_module")
        assert "test_module" in child.name

    def test_setup_logging_idempotent(self, tmp_path):
        """Calling setup_logging twice does not duplicate handlers."""
        logger1 = setup_logging(log_dir=tmp_path)
        handler_count = len(logger1.handlers)
        setup_logging(log_dir=tmp_path)
        assert len(logger1.handlers) == handler_count


class TestToolLogging:
    async def test_tool_logs_on_entry(self, tmp_path):
        """Tools emit a DEBUG log on entry without raising."""
        from src.logging_setup import setup_logging
        logger = setup_logging(log_dir=tmp_path)
        logger.setLevel(logging.DEBUG)

        from src.client.config import LogseqConfig
        from tests.conftest import FakeLogseqClient
        from src.tools.get_all_pages import _run

        client = FakeLogseqClient({"get_all_pages": []})
        cfg = LogseqConfig("http://x", "t")
        result = await _run(client, cfg)
        assert result  # Tool still returns normally

    async def test_tool_logs_error_on_exception(self, tmp_path, caplog):
        """Tools log ERROR when an exception is raised."""
        from src.logging_setup import setup_logging
        setup_logging(log_dir=tmp_path)

        from src.client.config import LogseqConfig
        from tests.conftest import FakeLogseqClient
        from src.tools.get_all_pages import _run

        class BrokenClient(FakeLogseqClient):
            async def get_all_pages(self):
                raise RuntimeError("forced error")

        cfg = LogseqConfig("http://x", "t")
        with caplog.at_level(logging.ERROR, logger="logseq_mcp"):
            result = await _run(BrokenClient(), cfg)
        assert "❌" in result[0].text
