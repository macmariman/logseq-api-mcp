"""Tests for VectorConfig and load_vector_config."""

import os
import pytest
from pathlib import Path

from src.vector.config import VectorConfig, load_vector_config


def test_load_vector_config_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("LOGSEQ_VECTOR_ENABLED", "false")
    assert load_vector_config() is None


def test_load_vector_config_returns_none_when_not_set(monkeypatch):
    monkeypatch.delenv("LOGSEQ_VECTOR_ENABLED", raising=False)
    assert load_vector_config() is None


def test_load_vector_config_returns_config_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_VECTOR_ENABLED", "true")
    monkeypatch.setenv("LOGSEQ_VECTOR_PATH", str(tmp_path / "vector_db"))
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path / "graph"))

    cfg = load_vector_config()

    assert cfg is not None
    assert isinstance(cfg, VectorConfig)
    assert cfg.db_path == tmp_path / "vector_db"
    assert cfg.graph_path == tmp_path / "graph"


def test_vector_config_defaults():
    cfg = VectorConfig(
        db_path=Path("/tmp/db"),
        graph_path=Path("/tmp/graph"),
    )
    assert cfg.chunk_size == 512
    assert cfg.watch_debounce == 2.0
    assert cfg.exclude_tags == []


def test_load_vector_config_uses_defaults_for_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_VECTOR_ENABLED", "1")
    monkeypatch.delenv("LOGSEQ_VECTOR_PATH", raising=False)
    monkeypatch.delenv("LOGSEQ_GRAPH_PATH", raising=False)

    cfg = load_vector_config()

    assert cfg is not None
    assert cfg.db_path is not None
    assert cfg.graph_path is not None
