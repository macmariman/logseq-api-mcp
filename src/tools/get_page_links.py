"""Backward-compatible alias for get_page_backlinks."""

from src.tools.get_page_backlinks import _run, get_page_backlinks as get_page_links

__all__ = ["_run", "get_page_links"]
