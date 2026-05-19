"""Tests for LogseqAPIError exception hierarchy."""

from src.client.exceptions import (
    LogseqAPIError,
    LogseqAuthError,
    LogseqConnectionError,
    LogseqNotFoundError,
)


def test_logseq_api_error_stores_message():
    err = LogseqAPIError("boom")
    assert str(err) == "boom"


def test_logseq_api_error_stores_status_code():
    err = LogseqAPIError("boom", status_code=500)
    assert err.status_code == 500


def test_logseq_api_error_status_code_defaults_none():
    err = LogseqAPIError("boom")
    assert err.status_code is None


def test_logseq_not_found_is_api_error():
    assert issubclass(LogseqNotFoundError, LogseqAPIError)


def test_logseq_auth_error_is_api_error():
    assert issubclass(LogseqAuthError, LogseqAPIError)


def test_logseq_connection_error_is_api_error():
    assert issubclass(LogseqConnectionError, LogseqAPIError)


def test_subclass_inherits_status_code():
    err = LogseqNotFoundError("not found", status_code=404)
    assert err.status_code == 404
