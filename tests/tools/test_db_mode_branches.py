"""Integration tests for DB-mode branches across tools.

Verifies that each tool correctly routes through its DB-mode code path
when config.db_mode=True.
"""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient

_cfg_db = LogseqConfig("http://x", "t", db_mode=True)
_cfg = LogseqConfig("http://x", "t", db_mode=False)


# ── get_all_page_content: uuid resolution ─────────────────────────────────────


class TestGetAllPageContentDbMode:
    async def test_resolve_refs_true_calls_resolve_page_uuids(self):
        from src.tools.get_all_page_content import get_all_page_content as _run

        _uuid = "12345678-1234-1234-1234-123456789012"
        page = {
            "id": 1,
            "uuid": "page-uuid",
            "originalName": "P",
            "name": "P",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        }
        block = {
            "id": 1,
            "uuid": "b1",
            "content": f"[[{_uuid}]]",
            "level": 1,
            "properties": {},
            "children": [],
        }
        client = FakeLogseqClient(
            {
                "get_page": page,
                "get_page_blocks_tree": [block],
                "resolve_page_uuids": {_uuid: "Referenced Page"},
            }
        )
        await _run(client, _cfg_db, "P", resolve_refs=True)
        assert any(c[0] == "resolve_page_uuids" for c in client.calls)

    async def test_resolve_refs_false_skips_uuid_resolution(self):
        from src.tools.get_all_page_content import get_all_page_content as _run

        page = {
            "id": 1,
            "uuid": "pu",
            "originalName": "P",
            "name": "P",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        }
        client = FakeLogseqClient({"get_page": page, "get_page_blocks_tree": []})
        await _run(client, _cfg_db, "P", resolve_refs=False)
        assert not any(c[0] == "resolve_page_uuids" for c in client.calls)

    async def test_non_db_mode_skips_uuid_resolution(self):
        from src.tools.get_all_page_content import get_all_page_content as _run

        page = {
            "id": 1,
            "uuid": "pu",
            "originalName": "P",
            "name": "P",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        }
        client = FakeLogseqClient({"get_page": page, "get_page_blocks_tree": []})
        await _run(client, _cfg, "P", resolve_refs=True)
        assert not any(c[0] == "resolve_page_uuids" for c in client.calls)


# ── get_block_content: db properties ─────────────────────────────────────────


class TestGetBlockContentDbMode:
    async def test_db_mode_calls_get_blocks_db_properties(self):
        from src.tools.get_block_content import get_block_content as _run

        block = {
            "id": 1,
            "uuid": "b1",
            "content": "text",
            "level": 1,
            "properties": {},
            "children": [],
        }
        client = FakeLogseqClient(
            {
                "get_block": block,
                "get_blocks_db_properties": {"b1": {"priority": "A"}},
            }
        )
        result = await _run(client, _cfg_db, "b1")
        assert any(c[0] == "get_blocks_db_properties" for c in client.calls)
        assert "priority" in result[0].text

    async def test_non_db_mode_skips_db_properties(self):
        from src.tools.get_block_content import get_block_content as _run

        block = {
            "id": 1,
            "uuid": "b1",
            "content": "text",
            "level": 1,
            "properties": {},
            "children": [],
        }
        client = FakeLogseqClient({"get_block": block})
        await _run(client, _cfg, "b1")
        assert not any(c[0] == "get_blocks_db_properties" for c in client.calls)


# ── search: formatter routing ─────────────────────────────────────────────────


class TestSearchDbMode:
    async def test_db_mode_result_contains_db_page_format(self):
        from src.tools.search import _run

        db_result = {
            "blocks": [
                {"page?": True, "fullTitle": "DB Page Result", "uuid": "p1"},
            ],
            "files": [],
        }
        client = FakeLogseqClient({"search": db_result, "get_all_pages": []})
        result = await _run(client, _cfg_db, "query")
        assert "DB Page Result" in result[0].text

    async def test_markdown_mode_result_uses_block_content_key(self):
        from src.tools.search import _run

        md_result = {
            "blocks": [
                {"block/content": "markdown block text", "uuid": "b1", "page": 1}
            ],
            "pages": [],
            "pages-content": [],
            "files": [],
        }
        client = FakeLogseqClient({"search": md_result, "get_all_pages": []})
        result = await _run(client, _cfg, "query")
        assert "markdown block text" in result[0].text


# ── set_block_properties: resolve_property_ident ─────────────────────────────


class TestSetBlockPropertiesDbMode:
    async def test_db_mode_calls_resolve_property_ident_per_key(self):
        from src.tools.set_block_properties import _run

        block = {
            "id": 1,
            "uuid": "b1",
            "content": "text",
            "level": 1,
            "properties": {},
            "children": [],
        }
        client = FakeLogseqClient(
            {
                "get_block": block,
                "resolve_property_ident": ":status",
            }
        )
        await _run(client, _cfg_db, "b1", {"status": "done"})
        assert any(c[0] == "resolve_property_ident" for c in client.calls)

    async def test_db_mode_uses_resolved_ident_when_found(self):
        from src.tools.set_block_properties import _run

        block = {
            "id": 1,
            "uuid": "b1",
            "content": "text",
            "level": 1,
            "properties": {},
            "children": [],
        }

        class ResolvingClient(FakeLogseqClient):
            async def resolve_property_ident(self, prop):
                self.calls.append(("resolve_property_ident", (prop,), {}))
                return f":{prop}"

        client = ResolvingClient({"get_block": block})
        await _run(client, _cfg_db, "b1", {"status": "done"})
        upsert_calls = [c for c in client.calls if c[0] == "upsert_block_property"]
        assert len(upsert_calls) == 1
        assert upsert_calls[0][1][1] == ":status"

    async def test_db_mode_falls_back_to_raw_name_when_ident_not_found(self):
        from src.tools.set_block_properties import _run

        block = {
            "id": 1,
            "uuid": "b1",
            "content": "text",
            "level": 1,
            "properties": {},
            "children": [],
        }

        class NoIdentClient(FakeLogseqClient):
            async def resolve_property_ident(self, prop):
                self.calls.append(("resolve_property_ident", (prop,), {}))
                return None

        client = NoIdentClient({"get_block": block})
        await _run(client, _cfg_db, "b1", {"status": "done"})
        upsert_calls = [c for c in client.calls if c[0] == "upsert_block_property"]
        assert upsert_calls[0][1][1] == "status"
