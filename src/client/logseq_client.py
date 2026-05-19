"""Async HTTP client for the Logseq local API."""

import asyncio

import aiohttp

from .config import LogseqConfig
from .exceptions import (
    LogseqAPIError,
    LogseqAuthError,
    LogseqConnectionError,
    LogseqNotFoundError,
)


async def _interpret(response: aiohttp.ClientResponse, method: str) -> object:
    """Translate an aiohttp response into a value or a typed exception.

    @param response aiohttp response object (already awaited as context manager).
    @param method   The logseq method called, used for error messages.
    @returns        Parsed JSON body when status == 200.
    @throws LogseqAuthError, LogseqNotFoundError, LogseqAPIError.
    @complexity O(1).
    """
    status = response.status
    if status == 200:
        try:
            return await response.json()
        except Exception:
            return await response.text()
    if status == 401:
        raise LogseqAuthError(f"Auth failed calling {method}", status_code=401)
    if status == 404:
        raise LogseqNotFoundError(f"Unknown method {method}", status_code=404)
    body = await response.text()
    raise LogseqAPIError(
        f"HTTP {status} from {method}: {body[:200]}", status_code=status
    )


class LogseqClient:
    """Async HTTP client for the Logseq local API.

    All methods correspond 1:1 to Logseq Editor/DB API calls.
    Constructed with an injected LogseqConfig; never reads env vars.

    Args:
        config: Immutable configuration object.

    Complexity: O(1) construction.
    """

    def __init__(self, config: LogseqConfig) -> None:
        self._config = config

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _call(self, method: str, args: list | None = None) -> object:
        """Issue a JSON-RPC POST to /api and map HTTP status to typed exceptions.

        @param method  Logseq method name, e.g. "logseq.Editor.getAllPages".
        @param args    Positional args list forwarded as JSON; defaults to [].
        @returns       Parsed JSON response body.
        @throws LogseqAuthError       on HTTP 401.
        @throws LogseqNotFoundError   on HTTP 404.
        @throws LogseqAPIError        on any other 4xx/5xx with status_code set.
        @throws LogseqConnectionError on aiohttp connector errors and asyncio timeouts.
        @complexity O(1) network call.
        """
        payload = {"method": method, "args": args or []}
        headers = {
            "Authorization": f"Bearer {self._config.token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._config.endpoint,
                    json=payload,
                    headers=headers,
                    ssl=self._config.verify_ssl,
                ) as response:
                    return await _interpret(response, method)
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as exc:
            raise LogseqConnectionError(
                f"Cannot reach Logseq API at {self._config.endpoint}: {exc}"
            ) from exc

    # ── Page read operations ──────────────────────────────────────────────────

    async def get_all_pages(self) -> list[dict]:
        """Return all pages in the Logseq graph.

        Returns:
            List of page dicts. Empty list if API returns None.

        Complexity: O(N) where N is page count.
        """
        result = await self._call("logseq.Editor.getAllPages")
        return result if result is not None else []

    async def get_page(self, page_name: str) -> dict | None:
        """Return a single page by name.

        Args:
            page_name: Exact page name.

        Returns:
            Page dict, or None if not found.

        Complexity: O(1).
        """
        return await self._call("logseq.Editor.getPage", [page_name])

    async def get_page_blocks_tree(self, page_identifier: str) -> list[dict]:
        """Return the block tree for a page.

        Args:
            page_identifier: Page name or UUID.

        Returns:
            List of top-level block dicts with nested children.

        Complexity: O(N) where N is block count.
        """
        result = await self._call("logseq.Editor.getPageBlocksTree", [page_identifier])
        return result if result is not None else []

    async def get_page_linked_references(self, page_name: str) -> list:
        """Return backlinks for a page.

        Args:
            page_name: Exact page name.

        Returns:
            List of [page_info, blocks] pairs.

        Complexity: O(R) where R is reference count.
        """
        result = await self._call("logseq.Editor.getPageLinkedReferences", [page_name])
        return result if result is not None else []

    async def get_pages_from_namespace(self, namespace: str) -> list[dict]:
        """Return a flat list of pages within a namespace.

        Args:
            namespace: Namespace prefix (e.g. 'Projects').

        Returns:
            List of page dicts.

        Complexity: O(N).
        """
        result = await self._call("logseq.Editor.getPagesFromNamespace", [namespace])
        return result if result is not None else []

    async def get_pages_tree_from_namespace(self, namespace: str) -> list[dict]:
        """Return a nested page tree for a namespace.

        Args:
            namespace: Root namespace (e.g. 'Projects').

        Returns:
            Nested list of page dicts with 'children' keys.

        Complexity: O(N).
        """
        result = await self._call(
            "logseq.Editor.getPagesTreeFromNamespace", [namespace]
        )
        return result if result is not None else []

    # ── Page write operations ─────────────────────────────────────────────────

    async def create_page(
        self,
        title: str,
        properties: dict | None = None,
        fmt: str | None = None,
    ) -> dict:
        """Create a new page.

        Args:
            title: Page title.
            properties: Optional page-level properties dict.
            fmt: Optional format string ('markdown' or 'org').

        Returns:
            Created page dict.

        Complexity: O(1).
        """
        options: dict = {}
        if properties:
            options["properties"] = properties
        if fmt:
            options["format"] = fmt
        result = await self._call("logseq.Editor.createPage", [title, options])
        return result or {}

    async def delete_page(self, page_name: str) -> None:
        """Delete a page by name.

        Args:
            page_name: Exact page name to delete.

        Complexity: O(1).
        """
        await self._call("logseq.Editor.deletePage", [page_name])

    async def rename_page(self, old_name: str, new_name: str) -> None:
        """Rename a page and update all references.

        Args:
            old_name: Current page name.
            new_name: New page name.

        Complexity: O(R) where R is reference count.
        """
        await self._call("logseq.Editor.renamePage", [old_name, new_name])

    async def set_page_properties(self, page_name: str, properties: dict) -> None:
        """Set page-level properties.

        Args:
            page_name: Exact page name.
            properties: Dict of property key/value pairs.

        Complexity: O(P) where P is property count.
        """
        await self._call("logseq.Editor.setPageProperties", [page_name, properties])

    # ── Block read operations ─────────────────────────────────────────────────

    async def get_block(
        self, block_uuid: str, include_children: bool = True
    ) -> dict | None:
        """Return a single block by UUID.

        Args:
            block_uuid: Block UUID string.
            include_children: Whether to recursively include child blocks.

        Returns:
            Block dict with optional children, or None if not found.

        Complexity: O(N) where N is descendant count when include_children=True.
        """
        options = {"includeChildren": include_children}
        return await self._call("logseq.Editor.getBlock", [block_uuid, options])

    # ── Block write operations ────────────────────────────────────────────────

    async def append_block_in_page(
        self,
        page_identifier: str,
        content: str,
        options: dict | None = None,
    ) -> dict:
        """Append a new block at the end of a page.

        Args:
            page_identifier: Page name or UUID.
            content: Block text content.
            options: Optional block options dict.

        Returns:
            Created block dict.

        Complexity: O(1).
        """
        result = await self._call(
            "logseq.Editor.appendBlockInPage",
            [page_identifier, content],
        )
        return result or {}

    async def insert_block(
        self,
        parent_uuid: str,
        content: str,
        properties: dict | None = None,
        sibling: bool = False,
    ) -> dict:
        """Insert a block as a child or sibling of an existing block.

        Args:
            parent_uuid: UUID of the reference block.
            content: Text content for the new block.
            properties: Optional block properties dict.
            sibling: False = child insertion, True = sibling insertion.

        Returns:
            Created block dict.

        Complexity: O(1).
        """
        options: dict = {"sibling": sibling}
        if properties:
            options["properties"] = properties
        result = await self._call(
            "logseq.Editor.insertBlock", [parent_uuid, content, options]
        )
        return result or {}

    async def insert_batch_block(
        self,
        src_block_uuid: str,
        blocks: list[dict],
        sibling: bool = True,
    ) -> list[dict]:
        """Insert multiple blocks in batch.

        Args:
            src_block_uuid: UUID of the reference block.
            blocks: List of IBatchBlock dicts.
            sibling: Whether to insert as siblings of src_block.

        Returns:
            List of created block dicts.

        Complexity: O(N) where N is block count.
        """
        options = {"sibling": sibling}
        result = await self._call(
            "logseq.Editor.insertBatchBlock", [src_block_uuid, blocks, options]
        )
        return result if result is not None else []

    async def update_block(self, block_uuid: str, content: str) -> None:
        """Replace the content of an existing block.

        Args:
            block_uuid: Block UUID string.
            content: New content string.

        Complexity: O(1).
        """
        await self._call("logseq.Editor.updateBlock", [block_uuid, content])

    async def delete_block(self, block_uuid: str) -> None:
        """Delete a block by UUID.

        Args:
            block_uuid: Block UUID string.

        Complexity: O(1).
        """
        await self._call("logseq.Editor.removeBlock", [block_uuid])

    async def upsert_block_property(
        self, block_uuid: str, key: str, value: object
    ) -> None:
        """Set or update a single property on a block.

        Args:
            block_uuid: Block UUID string.
            key: Property key (internal ident for DB mode).
            value: Property value.

        Complexity: O(1).
        """
        await self._call("logseq.Editor.upsertBlockProperty", [block_uuid, key, value])

    async def edit_block(
        self,
        block_uuid: str,
        content: str | None = None,
        properties: dict | None = None,
        cursor_pos: int | None = None,
        focus: bool | None = None,
    ) -> dict:
        """Open a block in the Logseq editor (sets cursor focus).

        Args:
            block_uuid: Block UUID string.
            content: Optional new content to set.
            properties: Optional properties to set.
            cursor_pos: Optional cursor position.
            focus: Optional focus flag.

        Returns:
            API response dict.

        Complexity: O(1).
        """
        options: dict = {}
        if content is not None:
            options["content"] = content
        if properties is not None:
            options["properties"] = properties
        if cursor_pos is not None:
            options["pos"] = cursor_pos
        if focus is not None:
            options["focus"] = focus
        result = await self._call("logseq.Editor.editBlock", [block_uuid, options])
        return result or {}

    # ── Search & Query ────────────────────────────────────────────────────────

    async def search(self, query: str, options: dict | None = None) -> dict:
        """Full-text search across pages and blocks.

        Args:
            query: Search query string.
            options: Optional search options dict (e.g. {'limit': 20}).

        Returns:
            Search result dict with 'blocks', 'pages', 'files' keys.

        Complexity: O(N) where N is matching content count.
        """
        result = await self._call("logseq.App.search", [query, options or {}])
        return result if result is not None else {}

    async def query_dsl(self, query: str) -> list[dict]:
        """Execute a Logseq DSL query.

        Args:
            query: Logseq DSL query string (e.g. '(page-property status active)').

        Returns:
            List of matching page or block dicts.

        Complexity: O(N) where N is result count.
        """
        result = await self._call("logseq.DB.q", [query])
        return result if result is not None else []

    # ── DB-mode operations ────────────────────────────────────────────────────

    async def datascript_query(self, query: str) -> list:
        """Execute a raw Datascript query.

        Args:
            query: Datascript query string.

        Returns:
            List of result tuples or dicts.

        Complexity: O(N) where N is result count.
        """
        result = await self._call("logseq.DB.datascriptQuery", [query])
        return result if result is not None else []

    async def resolve_page_uuids(self, uuids: list[str]) -> dict[str, str]:
        """Resolve a list of page UUIDs to their display names.

        Args:
            uuids: List of UUID strings.

        Returns:
            Dict mapping uuid → page name.

        Complexity: O(U) where U is uuid count (one API call per UUID).
        """
        result: dict[str, str] = {}
        for uuid in uuids:
            page = await self._call("logseq.Editor.getPage", [uuid])
            if page and isinstance(page, dict):
                name = page.get("originalName") or page.get("name")
                if name:
                    result[uuid] = name
        return result

    async def get_blocks_db_properties(self, blocks: list[dict]) -> dict[str, dict]:
        """Fetch DB-mode properties for a list of blocks.

        Args:
            blocks: List of block dicts with 'uuid' keys.

        Returns:
            Dict mapping block uuid → {property_key: value}.

        Complexity: O(B) where B is block count.
        """
        result: dict[str, dict] = {}
        for block in blocks:
            uuid = block.get("uuid")
            if not uuid:
                continue
            props = block.get("properties", {})
            if props:
                result[str(uuid)] = {
                    k: v for k, v in props.items() if not str(k).startswith(":logseq")
                }
        return result

    async def resolve_property_ident(self, property_name: str) -> str | None:
        """Resolve a property display name to its internal DB ident.

        Args:
            property_name: Human-readable property name (e.g. 'status').

        Returns:
            Internal ident string, or None if not found.

        Complexity: O(1).
        """
        query = f'[:find ?e :where [?e :db/ident ?i] [(= (name ?i) "{property_name}")]]'
        rows = await self.datascript_query(query)
        if rows and rows[0]:
            return rows[0][0]
        return None
