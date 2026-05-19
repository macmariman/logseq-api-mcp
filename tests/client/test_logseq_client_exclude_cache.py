"""excluded_page_names cache (v1.0.1)."""

from unittest.mock import AsyncMock, patch


from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient


async def test_excluded_page_names_empty_when_no_tags_configured():
    cfg = LogseqConfig(endpoint="http://x/api", token="t")
    client = LogseqClient(cfg)
    assert await client.excluded_page_names() == frozenset()


async def test_excluded_page_names_returns_lowercase_set():
    cfg = LogseqConfig(endpoint="http://x/api", token="t", exclude_tags=("private",))
    client = LogseqClient(cfg)
    with patch.object(client, "get_all_pages", new_callable=AsyncMock) as gap:
        gap.return_value = [
            {"originalName": "Secret", "properties": {"tags": ["Private"]}},
            {"originalName": "Public", "properties": {"tags": ["public"]}},
        ]
        result = await client.excluded_page_names()
        assert result == frozenset({"secret"})


async def test_excluded_page_names_cache_hits_within_ttl():
    cfg = LogseqConfig(endpoint="http://x/api", token="t", exclude_tags=("private",))
    client = LogseqClient(cfg)
    with patch.object(client, "get_all_pages", new_callable=AsyncMock) as gap:
        gap.return_value = [{"originalName": "X", "properties": {"tags": ["private"]}}]
        await client.excluded_page_names(ttl_seconds=10.0)
        await client.excluded_page_names(ttl_seconds=10.0)
        assert gap.await_count == 1


async def test_excluded_page_names_refreshes_after_ttl_expiry():
    cfg = LogseqConfig(endpoint="http://x/api", token="t", exclude_tags=("private",))
    client = LogseqClient(cfg)
    with (
        patch.object(client, "get_all_pages", new_callable=AsyncMock) as gap,
        patch("src.client.logseq_client.time.monotonic") as mono,
    ):
        gap.return_value = []
        mono.side_effect = [0.0, 0.0, 100.0, 100.0]
        await client.excluded_page_names(ttl_seconds=10.0)
        await client.excluded_page_names(ttl_seconds=10.0)
        assert gap.await_count == 2
