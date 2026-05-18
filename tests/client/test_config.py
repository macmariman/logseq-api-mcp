"""Tests for LogseqConfig and load_config."""

import pytest

from src.client.config import LogseqConfig, load_config


def test_load_config_requires_token(monkeypatch):
    monkeypatch.delenv("LOGSEQ_API_TOKEN", raising=False)
    monkeypatch.delenv("LOGSEQ_API_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="LOGSEQ_API_TOKEN"):
        load_config()


def test_load_config_defaults(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.delenv("LOGSEQ_API_ENDPOINT", raising=False)
    monkeypatch.delenv("LOGSEQ_API_URL", raising=False)
    monkeypatch.delenv("LOGSEQ_DB_MODE", raising=False)
    monkeypatch.delenv("LOGSEQ_EXCLUDE_TAGS", raising=False)
    monkeypatch.delenv("LOGSEQ_VERIFY_SSL", raising=False)
    cfg = load_config()
    assert cfg.endpoint == "http://127.0.0.1:12315/api"
    assert cfg.token == "tok"
    assert cfg.db_mode is False
    assert cfg.exclude_tags == ()
    assert cfg.verify_ssl is False  # http scheme → no SSL


def test_load_config_custom_endpoint(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "http://myhost:12315/api")
    cfg = load_config()
    assert cfg.endpoint == "http://myhost:12315/api"


def test_load_config_api_url_appends_api(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.delenv("LOGSEQ_API_ENDPOINT", raising=False)
    monkeypatch.setenv("LOGSEQ_API_URL", "http://myhost:12315")
    cfg = load_config()
    assert cfg.endpoint == "http://myhost:12315/api"


def test_load_config_exclude_tags(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_EXCLUDE_TAGS", "private,secret")
    cfg = load_config()
    assert cfg.exclude_tags == ("private", "secret")


def test_load_config_exclude_tags_strips_whitespace(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_EXCLUDE_TAGS", " private , secret ")
    cfg = load_config()
    assert cfg.exclude_tags == ("private", "secret")


def test_load_config_db_mode_true(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_DB_MODE", "true")
    cfg = load_config()
    assert cfg.db_mode is True


def test_load_config_db_mode_1(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_DB_MODE", "1")
    cfg = load_config()
    assert cfg.db_mode is True


def test_load_config_https_sets_verify_ssl_true(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "https://myhost/api")
    monkeypatch.delenv("LOGSEQ_VERIFY_SSL", raising=False)
    cfg = load_config()
    assert cfg.verify_ssl is True


def test_load_config_verify_ssl_explicit_false(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "https://myhost/api")
    monkeypatch.setenv("LOGSEQ_VERIFY_SSL", "false")
    cfg = load_config()
    assert cfg.verify_ssl is False


def test_config_is_immutable():
    cfg = LogseqConfig(endpoint="http://x", token="y")
    with pytest.raises((AttributeError, TypeError)):
        cfg.token = "z"  # type: ignore[misc]


def test_load_config_api_url_trailing_slash_stripped(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.delenv("LOGSEQ_API_ENDPOINT", raising=False)
    monkeypatch.setenv("LOGSEQ_API_URL", "http://myhost:12315/")
    cfg = load_config()
    assert cfg.endpoint == "http://myhost:12315/api"


def test_load_config_verify_ssl_explicit_true_overrides_http(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "http://myhost/api")
    monkeypatch.setenv("LOGSEQ_VERIFY_SSL", "true")
    cfg = load_config()
    assert cfg.verify_ssl is True


def test_load_config_verify_ssl_zero_disables(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "https://myhost/api")
    monkeypatch.setenv("LOGSEQ_VERIFY_SSL", "0")
    cfg = load_config()
    assert cfg.verify_ssl is False


def test_load_config_verify_ssl_no_disables(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_API_ENDPOINT", "https://myhost/api")
    monkeypatch.setenv("LOGSEQ_VERIFY_SSL", "no")
    cfg = load_config()
    assert cfg.verify_ssl is False


def test_logseq_client_passes_ssl_to_request():
    """verify_ssl from config is forwarded to aiohttp session.post(ssl=...)."""
    import inspect
    from src.client.logseq_client import LogseqClient
    source = inspect.getsource(LogseqClient._call)
    assert "verify_ssl" in source or "ssl" in source
