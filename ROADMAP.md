# Logseq API MCP — Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` or
> `superpowers:executing-plans`
>
> **Goal:** Bring `gustavo-meilus/logseq-api-mcp` to full feature-parity with `ergut/mcp-logseq`
> (17 standard tools + 3 optional vector tools), refactor the entire codebase to comply with the
> six architectural standards below, support Logseq DB-mode and tag-based privacy exclusion, and
> maintain a fully green TDD test suite throughout every incremental step.
>
> **Do NOT skip ahead.** Each phase depends on the previous one compiling and all tests passing.
> The TDD loop is mandatory: write failing test → confirm failure → implement → confirm passing →
> commit.

---

## Architectural Standards (enforced everywhere)

| # | Standard | Rule |
|---|----------|------|
| 1 | **Algorithmic Efficiency** | Default to O(1) or O(N log N). Document Big-O in every public function's docstring. |
| 2 | **Flow Control (KISS)** | Max conditional nesting depth of 1. Mandate early returns and guard clauses. |
| 3 | **State Management** | Pure functions only. Never mutate input parameters. Isolate all I/O and side-effects from core business logic. |
| 4 | **Decoupling** | Modules are ignorant of external implementations. Inject all dependencies (client, config, formatters) via parameters or higher-order functions. |
| 5 | **Testability** | Core logic must be 100% testable in isolation. Injecting a test double must require zero monkey-patching. |
| 6 | **Documentation** | Structured docstrings: `Args:`, `Returns:`, `Raises:`, complexity note. Zero inline operational comments. |

---

## Current-State Compliance Audit

The following violations exist in the **current 9 tools** and must be resolved in Phase 0:

| Violation | Affected Files | Standard |
|-----------|---------------|----------|
| `os.getenv()` called inside tool functions | All 9 tools | #4 Decoupling |
| `aiohttp.ClientSession` constructed inside tool functions | All 9 tools | #4 Decoupling, #5 Testability |
| `.env` path resolved inside tool modules | All 9 tools | #4 Decoupling |
| Nested helper functions closing over outer-scope mutable state | `get_all_page_content.py`, `get_page_blocks.py` | #3 State Management |
| Conditional nesting > 1 level | `get_all_page_content.py` (5+ levels), `get_linked_flashcards.py` | #2 KISS |
| Formatting and I/O in the same function body | All 9 tools | #3 State Management |
| Tests patch `aiohttp.ClientSession` internals (brittle) | `tests/conftest.py` | #5 Testability |
| No structured `Args:/Returns:/Raises:` docstrings | All 9 tools | #6 Documentation |

---

## New Target Architecture

```
src/
├── server.py                    # FastMCP server (unchanged surface)
├── registry.py                  # Dynamic tool discovery (updated for new sub-packages)
├── client/
│   ├── __init__.py
│   ├── config.py                # LogseqConfig dataclass + load_config()
│   ├── exceptions.py            # LogseqAPIError hierarchy
│   └── logseq_client.py         # Async LogseqClient — all API calls live here
├── privacy/
│   ├── __init__.py
│   └── exclude_tags.py          # Pure filter functions; no I/O
├── parser/
│   ├── __init__.py
│   └── markdown.py              # Markdown → BlockNode tree (pure, no I/O)
├── tools/
│   ├── __init__.py              # Dynamic discovery (unchanged algorithm)
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── pages.py             # Pure page-data formatters
│   │   ├── blocks.py            # Pure block-data formatters
│   │   └── search.py            # Pure search-result formatters
│   │
│   │   # ── Read tools ──────────────────────────────────────
│   ├── get_all_pages.py         # Enhanced: include_journals, exclude_tags
│   ├── get_page_content.py      # Enhanced: format, max_depth, resolve_refs (DB)
│   ├── get_page_blocks.py       # Refactored (pure formatter extracted)
│   ├── get_page_backlinks.py    # Renamed from get_page_links + include_content
│   ├── get_block_content.py     # Enhanced: format=json, include_children, DB props
│   ├── get_linked_flashcards.py # Refactored (existing unique tool)
│   ├── search.py                # NEW: full-text search (logseq.App.search)
│   ├── query.py                 # NEW: DSL query (logseq.DB.q)
│   ├── find_pages_by_property.py# NEW: property-based page lookup
│   ├── get_pages_from_namespace.py    # NEW: flat namespace listing
│   ├── get_pages_tree_from_namespace.py # NEW: tree namespace view
│   │
│   │   # ── Write tools ─────────────────────────────────────
│   ├── create_page.py           # Enhanced: markdown parsing via parser module
│   ├── update_page.py           # NEW: append/replace with markdown parsing
│   ├── delete_page.py           # NEW
│   ├── rename_page.py           # NEW
│   ├── append_block_in_page.py  # Refactored (existing)
│   ├── insert_nested_block.py   # NEW: child/sibling insertion
│   ├── update_block.py          # NEW (supersedes edit_block for content-only updates)
│   ├── edit_block.py            # Refactored (existing; kept for cursor/focus control)
│   ├── delete_block.py          # NEW
│   └── set_block_properties.py  # NEW: DB-mode only
│
└── vector/                      # Optional — installed only with [vector] extra
    ├── __init__.py
    ├── config.py                # VectorConfig dataclass
    ├── sync.py                  # Graph-sync daemon + logseq-sync CLI
    ├── search.py                # Semantic search tool
    └── status.py                # VectorDB status tool
```

**Tool count target:** 9 existing (refactored) + 12 new standard tools + 3 optional vector tools = **24 tools total**

---

## Environment Variables (final set)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGSEQ_API_TOKEN` | — | **Required.** Auth token from Logseq settings |
| `LOGSEQ_API_ENDPOINT` | `http://127.0.0.1:12315/api` | Full API endpoint URL |
| `LOGSEQ_API_URL` | — | Alternative: base URL (auto-appends `/api`) |
| `LOGSEQ_VERIFY_SSL` | auto | `true`/`false`; defaults to `true` when scheme is `https` |
| `LOGSEQ_DB_MODE` | `false` | `true` to enable DB-mode property resolution |
| `LOGSEQ_EXCLUDE_TAGS` | — | Comma-separated tags; pages with these tags are hidden |
| `LOGSEQ_VECTOR_ENABLED` | `false` | Enable vector/semantic search tools |
| `LOGSEQ_VECTOR_PATH` | `~/.cache/logseq-api-mcp/vector` | LanceDB storage path |
| `LOGSEQ_GRAPH_PATH` | — | Path to Logseq graph directory for vector sync |

---

## Phase 0 — Architecture Refactor (Standards Compliance)

**Goal:** Introduce the `LogseqClient` abstraction and extract pure formatters. Every existing tool
gets refactored so its core logic is I/O-free and 100% testable without patching aiohttp.

**No new user-facing tools ship in this phase.** All 9 tools must pass their existing tests after
every step.

### Step 0.1 — Create `src/client/exceptions.py`

- [ ] **Create** `src/client/__init__.py` (empty)
- [ ] **Create** `src/client/exceptions.py`:

```python
class LogseqAPIError(Exception):
    """Base for all Logseq HTTP API errors.

    Args:
        message: Human-readable description.
        status_code: HTTP status code if applicable.

    Complexity: O(1)
    """
    def __init__(self, message: str, status_code: int | None = None) -> None: ...

class LogseqNotFoundError(LogseqAPIError): ...
class LogseqAuthError(LogseqAPIError): ...
class LogseqConnectionError(LogseqAPIError): ...
```

- [ ] **Write** `tests/client/test_exceptions.py`:

```python
def test_logseq_api_error_stores_status_code():
    err = LogseqAPIError("boom", status_code=500)
    assert err.status_code == 500

def test_logseq_not_found_is_api_error():
    assert issubclass(LogseqNotFoundError, LogseqAPIError)
```

- [ ] Run `uv run pytest tests/client/test_exceptions.py -v` → confirm **FAIL**
- [ ] Implement `exceptions.py`
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(client): add LogseqAPIError exception hierarchy`

---

### Step 0.2 — Create `src/client/config.py`

- [ ] **Create** `src/client/config.py`:

```python
from dataclasses import dataclass, field
import os

@dataclass(frozen=True)
class LogseqConfig:
    """Immutable configuration for the Logseq HTTP client.

    Args:
        endpoint: Full API endpoint URL including /api path.
        token: Bearer token for authorization.
        verify_ssl: Whether to verify TLS certificates.
        db_mode: Whether the Logseq instance is running in DB mode.
        exclude_tags: Page tags that should be hidden from all tools.

    Returns:
        Frozen dataclass instance.

    Complexity: O(1) construction.
    """
    endpoint: str
    token: str
    verify_ssl: bool = True
    db_mode: bool = False
    exclude_tags: tuple[str, ...] = field(default_factory=tuple)


def load_config() -> LogseqConfig:
    """Load LogseqConfig from environment variables.

    Returns:
        LogseqConfig populated from environment.

    Raises:
        ValueError: If LOGSEQ_API_TOKEN is not set.

    Complexity: O(E) where E is number of exclude tags.
    """
    ...
```

- [ ] **Write** `tests/client/test_config.py`:

```python
import os
import pytest
from src.client.config import load_config, LogseqConfig

def test_load_config_requires_token(monkeypatch):
    monkeypatch.delenv("LOGSEQ_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="LOGSEQ_API_TOKEN"):
        load_config()

def test_load_config_defaults(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.delenv("LOGSEQ_API_ENDPOINT", raising=False)
    cfg = load_config()
    assert cfg.endpoint == "http://127.0.0.1:12315/api"
    assert cfg.token == "tok"
    assert cfg.db_mode is False
    assert cfg.exclude_tags == ()

def test_load_config_exclude_tags(monkeypatch):
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "tok")
    monkeypatch.setenv("LOGSEQ_EXCLUDE_TAGS", "private,secret")
    cfg = load_config()
    assert cfg.exclude_tags == ("private", "secret")

def test_config_is_immutable():
    cfg = LogseqConfig(endpoint="http://x", token="y")
    with pytest.raises(Exception):
        cfg.token = "z"  # type: ignore[misc]
```

- [ ] Run tests → confirm **FAIL**
- [ ] Implement `config.py`
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(client): add LogseqConfig dataclass and load_config`

---

### Step 0.3 — Create `src/client/logseq_client.py`

This is the central abstraction. All HTTP I/O lives here. Tools never touch `aiohttp` directly.

- [ ] **Create** `src/client/logseq_client.py` with the following interface (implement stub
  `raise NotImplementedError` bodies initially):

```python
import aiohttp
from .config import LogseqConfig
from .exceptions import LogseqAPIError, LogseqNotFoundError, LogseqAuthError

class LogseqClient:
    """Async HTTP client for the Logseq local API.

    All methods correspond 1:1 to Logseq Editor/DB API calls.
    Constructed with an injected LogseqConfig; never reads env vars.

    Args:
        config: Immutable configuration object.

    Complexity: O(1) construction.
    """

    def __init__(self, config: LogseqConfig) -> None: ...

    # ── Page read operations ─────────────────────────────────────────
    async def get_all_pages(self) -> list[dict]: ...
    async def get_page(self, page_name: str) -> dict | None: ...
    async def get_page_blocks_tree(self, page_identifier: str) -> list[dict]: ...
    async def get_page_linked_references(self, page_name: str) -> list: ...
    async def get_pages_from_namespace(self, namespace: str) -> list[dict]: ...
    async def get_pages_tree_from_namespace(self, namespace: str) -> list[dict]: ...

    # ── Page write operations ────────────────────────────────────────
    async def create_page(self, title: str, properties: dict | None = None,
                          fmt: str | None = None) -> dict: ...
    async def delete_page(self, page_name: str) -> None: ...
    async def rename_page(self, old_name: str, new_name: str) -> None: ...
    async def set_page_properties(self, page_name: str, properties: dict) -> None: ...

    # ── Block read operations ────────────────────────────────────────
    async def get_block(self, block_uuid: str,
                        include_children: bool = True) -> dict | None: ...

    # ── Block write operations ───────────────────────────────────────
    async def append_block_in_page(self, page_identifier: str, content: str,
                                   options: dict | None = None) -> dict: ...
    async def insert_block(self, parent_uuid: str, content: str,
                           properties: dict | None = None,
                           sibling: bool = False) -> dict: ...
    async def insert_batch_block(self, src_block_uuid: str,
                                 blocks: list[dict],
                                 sibling: bool = True) -> list[dict]: ...
    async def update_block(self, block_uuid: str, content: str) -> None: ...
    async def delete_block(self, block_uuid: str) -> None: ...
    async def upsert_block_property(self, block_uuid: str,
                                    key: str, value: object) -> None: ...
    async def edit_block(self, block_uuid: str, content: str | None = None,
                         properties: dict | None = None,
                         cursor_pos: int | None = None,
                         focus: bool | None = None) -> dict: ...

    # ── Search & Query ───────────────────────────────────────────────
    async def search(self, query: str,
                     options: dict | None = None) -> dict: ...
    async def query_dsl(self, query: str) -> list[dict]: ...

    # ── DB-mode operations ───────────────────────────────────────────
    async def datascript_query(self, query: str) -> list: ...
    async def resolve_page_uuids(self, uuids: list[str]) -> dict[str, str]: ...
    async def get_blocks_db_properties(
        self, blocks: list[dict]
    ) -> dict[str, dict]: ...
    async def resolve_property_ident(self, property_name: str) -> str | None: ...

    # ── Internal ─────────────────────────────────────────────────────
    async def _call(self, method: str,
                    args: list | None = None) -> object: ...
```

- [ ] **Write** `tests/client/test_logseq_client.py` — use `aioresponses` or a local
  `FakeLogseqClient` for isolation:

```python
# tests/client/test_logseq_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.client.exceptions import LogseqAPIError, LogseqAuthError, LogseqNotFoundError

@pytest.fixture
def config():
    return LogseqConfig(endpoint="http://localhost:12315/api", token="test-tok")

@pytest.fixture
def client(config):
    return LogseqClient(config)

@pytest.fixture
def mock_call(client):
    """Patch the internal _call method to avoid real HTTP."""
    with patch.object(client, "_call", new_callable=AsyncMock) as mock:
        yield mock

async def test_get_all_pages_calls_correct_method(client, mock_call):
    mock_call.return_value = [{"id": 1, "name": "Test"}]
    result = await client.get_all_pages()
    mock_call.assert_awaited_once_with("logseq.Editor.getAllPages")
    assert result[0]["name"] == "Test"

async def test_get_all_pages_returns_empty_list_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.get_all_pages()
    assert result == []

async def test_call_raises_auth_error_on_401(client):
    mock_response = MagicMock()
    mock_response.status = 401
    with patch("aiohttp.ClientSession") as mock_sess:
        mock_sess.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_sess.post.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_sess.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(LogseqAuthError):
            await client._call("logseq.Editor.getAllPages")

async def test_delete_page_calls_correct_method(client, mock_call):
    mock_call.return_value = True
    await client.delete_page("My Page")
    mock_call.assert_awaited_once_with("logseq.Editor.deletePage", ["My Page"])

async def test_search_passes_options(client, mock_call):
    mock_call.return_value = {"blocks": []}
    await client.search("test", {"limit": 10})
    mock_call.assert_awaited_once_with("logseq.App.search", ["test", {"limit": 10}])
```

- [ ] Add `pytest-asyncio` mode `auto` already in `pyproject.toml` — verify it is set
- [ ] Run `uv run pytest tests/client/test_logseq_client.py -v` → confirm **FAIL**
- [ ] Implement `_call()` first (the HTTP core), then each method delegating to `_call()`
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(client): implement LogseqClient async HTTP abstraction`

---

### Step 0.4 — Create `src/tools/formatters/`

Extract all pure formatting logic from existing tool files into standalone modules.

- [ ] Create `src/tools/formatters/__init__.py` (empty)
- [ ] **Create** `src/tools/formatters/pages.py`:

```python
from datetime import datetime

def format_timestamp(ts_ms: int | None) -> str:
    """Convert a Logseq millisecond timestamp to a human-readable string.

    Args:
        ts_ms: Timestamp in milliseconds or None.

    Returns:
        ISO-like datetime string, or "N/A" if ts_ms is falsy.

    Complexity: O(1).
    """
    ...

def format_page_entry(page: dict) -> str:
    """Format a single Logseq page dict into a one-line display string.

    Args:
        page: Raw Logseq page dict with keys id, uuid, originalName, etc.

    Returns:
        Formatted string with emoji, name, ID, UUID, and timestamps.

    Complexity: O(1).
    """
    ...

def format_pages_listing(
    pages: list[dict],
    start: int | None = None,
    end: int | None = None,
) -> str:
    """Format a list of Logseq pages into the full pages listing output.

    Args:
        pages: List of raw Logseq page dicts.
        start: Optional slice start index.
        end: Optional slice end index.

    Returns:
        Multi-line formatted string with journal/regular sections.

    Complexity: O(N log N) — sort by name.
    """
    ...
```

- [ ] **Create** `src/tools/formatters/blocks.py`:

```python
def format_block_tree(
    block: dict,
    level: int = 0,
    max_level: int = 8,
    db_properties: dict[str, dict] | None = None,
    uuid_map: dict[str, str] | None = None,
) -> list[str]:
    """Recursively format a Logseq block tree into display lines.

    Args:
        block: Raw Logseq block dict with content, children, properties.
        level: Current recursion depth.
        max_level: Maximum depth to recurse.
        db_properties: Optional DB-mode property overrides keyed by block UUID.
        uuid_map: Optional UUID-to-name resolution map for DB mode.

    Returns:
        List of formatted display lines.

    Raises:
        Nothing — returns empty list on invalid input.

    Complexity: O(N) where N is total block count in subtree.
    """
    ...

def format_block_detail(block: dict, is_child: bool = False) -> list[str]:
    """Format a single block with full metadata for get_block_content output.

    Args:
        block: Raw Logseq block dict.
        is_child: Whether this block is being displayed as a child.

    Returns:
        List of formatted display lines.

    Complexity: O(P) where P is property count.
    """
    ...
```

- [ ] **Create** `src/tools/formatters/search.py` (stub for now):

```python
def format_search_results_markdown_mode(
    result: dict,
    query: str,
    limit: int = 20,
    include_blocks: bool = True,
    include_pages: bool = True,
    include_files: bool = False,
    excluded_page_names: frozenset[str] = frozenset(),
) -> str:
    """Format logseq.App.search results for markdown-mode Logseq.

    Args:
        result: Raw API response dict.
        query: Original search query (for header).
        limit: Max results to display.
        include_blocks: Whether to include block results.
        include_pages: Whether to include page results.
        include_files: Whether to include file results.
        excluded_page_names: Lowercased page names to suppress.

    Returns:
        Multi-line formatted string.

    Complexity: O(N) where N is total result count.
    """
    ...

def format_search_results_db_mode(
    result: dict,
    query: str,
    limit: int = 20,
    include_blocks: bool = True,
    include_pages: bool = True,
    include_files: bool = False,
    excluded_page_names: frozenset[str] = frozenset(),
) -> str: ...
```

- [ ] **Write** `tests/tools/formatters/test_pages.py`:

```python
from src.tools.formatters.pages import format_timestamp, format_page_entry, format_pages_listing

def test_format_timestamp_none_returns_na():
    assert format_timestamp(None) == "N/A"

def test_format_timestamp_ms():
    assert format_timestamp(1640995200000) == "2022-01-01 00:00:00"

def test_format_page_entry_journal():
    page = {"id": 1, "uuid": "abc", "originalName": "2024-01-01",
            "journal?": True, "createdAt": 0, "updatedAt": 0}
    result = format_page_entry(page)
    assert "📅" in result
    assert "2024-01-01" in result

def test_format_page_entry_regular():
    page = {"id": 1, "uuid": "abc", "originalName": "My Page",
            "journal?": False, "createdAt": 0, "updatedAt": 0}
    result = format_page_entry(page)
    assert "📄" in result
    assert "My Page" in result

def test_format_pages_listing_splits_journals():
    pages = [
        {"id": 1, "uuid": "a", "originalName": "Page A", "journal?": False, "createdAt": 0, "updatedAt": 0},
        {"id": 2, "uuid": "b", "originalName": "2024-01-01", "journal?": True, "createdAt": 0, "updatedAt": 0},
    ]
    result = format_pages_listing(pages)
    assert "REGULAR PAGES" in result
    assert "JOURNAL PAGES" in result
    assert "Page A" in result

def test_format_pages_listing_respects_slice():
    pages = [
        {"id": i, "uuid": str(i), "originalName": f"P{i}", "journal?": False, "createdAt": 0, "updatedAt": 0}
        for i in range(10)
    ]
    result = format_pages_listing(pages, start=0, end=3)
    assert "showing indices 0-3" in result
```

- [ ] **Write** `tests/tools/formatters/test_blocks.py` (3-4 unit tests for `format_block_tree`)
- [ ] Run formatter tests → confirm **FAIL**
- [ ] Implement formatters
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(formatters): extract pure formatter modules for pages and blocks`

---

### Step 0.5 — Create `src/privacy/exclude_tags.py`

- [ ] Create `src/privacy/__init__.py` (empty)
- [ ] **Create** `src/privacy/exclude_tags.py`:

```python
def extract_tags(properties: dict) -> list[str]:
    """Extract the tags list from a Logseq page properties dict.

    Args:
        properties: Raw properties dict (tags may be list or comma-string).

    Returns:
        List of tag strings, stripped and lower-cased.

    Complexity: O(T) where T is tag count.
    """
    ...

def is_page_excluded(page: dict, exclude_tags: tuple[str, ...]) -> bool:
    """Return True if the page carries any tag in the exclusion list.

    Args:
        page: Raw Logseq page dict.
        exclude_tags: Tuple of tags to exclude. Empty tuple = no exclusion.

    Returns:
        True when the page should be hidden; False otherwise.

    Complexity: O(T) where T is tag count on the page.
    """
    ...

def filter_pages(
    pages: list[dict],
    exclude_tags: tuple[str, ...],
) -> list[dict]:
    """Return a new list with excluded pages removed.

    Args:
        pages: Input list (not mutated).
        exclude_tags: Tags causing exclusion.

    Returns:
        New list without excluded pages.

    Complexity: O(N * T) where N is page count, T is tag count.
    """
    ...
```

- [ ] **Write** `tests/privacy/test_exclude_tags.py`:

```python
from src.privacy.exclude_tags import extract_tags, is_page_excluded, filter_pages

def test_extract_tags_from_list():
    assert extract_tags({"tags": ["private", "secret"]}) == ["private", "secret"]

def test_extract_tags_from_string():
    assert extract_tags({"tags": "private, secret"}) == ["private", "secret"]

def test_extract_tags_empty():
    assert extract_tags({}) == []

def test_is_page_excluded_true():
    page = {"properties": {"tags": ["private"]}}
    assert is_page_excluded(page, ("private",)) is True

def test_is_page_excluded_false():
    page = {"properties": {"tags": ["public"]}}
    assert is_page_excluded(page, ("private",)) is False

def test_is_page_excluded_no_tags():
    assert is_page_excluded({"properties": {}}, ("private",)) is False

def test_filter_pages_removes_excluded():
    pages = [
        {"id": 1, "properties": {"tags": ["private"]}},
        {"id": 2, "properties": {"tags": ["public"]}},
    ]
    result = filter_pages(pages, ("private",))
    assert len(result) == 1
    assert result[0]["id"] == 2

def test_filter_pages_does_not_mutate_input():
    pages = [{"id": 1, "properties": {"tags": ["private"]}}]
    original_len = len(pages)
    filter_pages(pages, ("private",))
    assert len(pages) == original_len
```

- [ ] Run tests → confirm **FAIL**
- [ ] Implement
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(privacy): add pure tag-based page exclusion module`

---

### Step 0.6 — Refactor the 9 existing tools

For each tool below, perform the same refactoring pattern:

1. Remove `os.getenv()` and `load_dotenv()` from module level
2. Remove `aiohttp.ClientSession` construction from inside the function
3. Add `client: LogseqClient` and `config: LogseqConfig` parameters
4. Move all formatting logic to the appropriate `formatters/` function
5. Add `get_tool_description() -> Tool` if missing (for schema validation)
6. Add structured `Args:/Returns:/Raises:/Complexity:` docstring
7. Update corresponding test to inject `FakeLogseqClient` instead of patching aiohttp

**Introduce `FakeLogseqClient` in `tests/conftest.py`:**

```python
# tests/conftest.py — add this alongside existing fixtures

class FakeLogseqClient:
    """In-memory test double for LogseqClient.
    No HTTP, no aiohttp — pure dict responses."""

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.calls: list[tuple[str, tuple, dict]] = []

    async def get_all_pages(self) -> list[dict]:
        self.calls.append(("get_all_pages", (), {}))
        return self.responses.get("get_all_pages", [])

    async def get_page_blocks_tree(self, page_identifier: str) -> list[dict]:
        self.calls.append(("get_page_blocks_tree", (page_identifier,), {}))
        return self.responses.get("get_page_blocks_tree", [])

    # ... (one method per LogseqClient method)
```

**Tools to refactor (one commit each):**

- [ ] `get_all_pages.py` — inject `client`, use `format_pages_listing`
- [ ] `get_page_blocks.py` — inject `client`, use `format_block_tree`
- [ ] `get_page_links.py` — inject `client`, use formatters
- [ ] `get_block_content.py` — inject `client`, use `format_block_detail`
- [ ] `get_all_page_content.py` — inject `client`, use `format_block_tree`
- [ ] `get_linked_flashcards.py` — inject `client`, extract flashcard helpers to `formatters/blocks.py`
- [ ] `append_block_in_page.py` — inject `client`
- [ ] `create_page.py` — inject `client`
- [ ] `edit_block.py` — inject `client`

**For each tool refactor:**
- [ ] Update the tool's test file to use `FakeLogseqClient`
- [ ] Verify `uv run pytest tests/ -v` still **fully green** after each refactor
- [ ] Commit: `refactor(<tool>): inject LogseqClient, extract pure formatters`

---

### Step 0.7 — Update `server.py` and `registry.py`

- [ ] Update `server.py` to call `load_config()` once at startup and pass `config` to `register_all_tools`
- [ ] Update `registry.py` so that `register_all_tools` passes a shared `LogseqClient` instance to each tool function via a partial or closure
- [ ] Run full test suite: `uv run pytest tests/ -v --cov=src --cov-report=term-missing`
- [ ] Confirm coverage ≥ 80%, all tests green
- [ ] Commit: `refactor(server): wire LogseqClient through registry at startup`

---

## Phase 1 — Markdown Parser

**Goal:** Implement a pure Markdown → Logseq block tree parser. Required by `create_page`,
`update_page`, and any future tool that accepts freeform markdown content.

### Step 1.1 — Data structures

- [ ] **Create** `src/parser/__init__.py` (empty)
- [ ] **Create** `src/parser/markdown.py` with the following public interface:

```python
from dataclasses import dataclass, field

@dataclass
class BlockNode:
    """A single Logseq block with optional nested children.

    Args:
        content: Block text content.
        children: List of child BlockNodes.
        properties: Block-level property dict.
        level: Heading level 0-6 (0 = body block).

    Complexity: O(1) construction.
    """
    content: str
    children: list["BlockNode"] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    level: int = 0

    def to_batch_format(self) -> dict:
        """Convert to Logseq IBatchBlock format.

        Returns:
            Dict with 'content' and 'children' keys.

        Complexity: O(N) where N is total descendant count.
        """
        ...

@dataclass
class ParsedContent:
    """Result of parsing a markdown document.

    Args:
        properties: Page-level properties from YAML frontmatter.
        blocks: Top-level BlockNode list.

    Complexity: O(1) construction.
    """
    properties: dict = field(default_factory=dict)
    blocks: list[BlockNode] = field(default_factory=list)

    def to_batch_format(self) -> list[dict]:
        """Convert all blocks to Logseq batch format.

        Returns:
            List of IBatchBlock dicts.

        Complexity: O(N) where N is total block count.
        """
        ...


def parse_content(markdown: str) -> ParsedContent:
    """Parse a markdown string into a ParsedContent tree.

    Handles: YAML frontmatter, headings (H1-H6), bullet lists,
    numbered lists, checkboxes (→ TODO/DONE), blockquotes,
    fenced code blocks, tables, and paragraphs.

    Args:
        markdown: Raw markdown string.

    Returns:
        ParsedContent with extracted properties and block tree.

    Raises:
        Nothing — malformed input degrades gracefully.

    Complexity: O(L) where L is line count.
    """
    ...
```

### Step 1.2 — TDD for parser

- [ ] **Write** `tests/parser/test_markdown.py`:

```python
from src.parser.markdown import parse_content, BlockNode

def test_parse_empty_string():
    result = parse_content("")
    assert result.properties == {}
    assert result.blocks == []

def test_parse_frontmatter():
    md = "---\nstatus: active\ntags: [python]\n---\nContent"
    result = parse_content(md)
    assert result.properties["status"] == "active"
    assert "python" in result.properties["tags"]

def test_parse_heading_creates_hierarchy():
    md = "# H1\ncontent\n## H2\nsub-content"
    result = parse_content(md)
    assert len(result.blocks) == 1
    assert result.blocks[0].content == "# H1"
    assert len(result.blocks[0].children) >= 2

def test_parse_bullet_list():
    md = "- item1\n- item2"
    result = parse_content(md)
    assert len(result.blocks) == 2
    assert result.blocks[0].content == "- item1"

def test_parse_checkbox_to_todo():
    md = "- [ ] Task A\n- [x] Task B"
    result = parse_content(md)
    assert "TODO" in result.blocks[0].content
    assert "DONE" in result.blocks[1].content

def test_parse_fenced_code_block():
    md = "```python\nprint('hi')\n```"
    result = parse_content(md)
    assert len(result.blocks) == 1
    assert "```python" in result.blocks[0].content

def test_batch_format_roundtrip():
    md = "# Title\ncontent"
    result = parse_content(md)
    batch = result.to_batch_format()
    assert isinstance(batch, list)
    assert batch[0]["content"] == "# Title"

def test_block_node_is_immutable_children():
    node = BlockNode(content="test")
    original_id = id(node.children)
    node.children.append(BlockNode(content="child"))
    assert id(node.children) == original_id  # same list (append ok, but no external mutation)
```

- [ ] Run tests → confirm **FAIL**
- [ ] Implement parser
- [ ] Run tests → confirm **PASS**
- [ ] Commit: `feat(parser): implement Markdown to Logseq block tree parser`

---

## Phase 2 — Enhance Existing Tools

**Goal:** Bring the 9 refactored tools up to ergut feature-parity without adding new tools.

### Step 2.1 — `get_all_pages` — add `include_journals` and `exclude_tags` filtering

- [ ] Add `include_journals: bool = False` parameter
- [ ] Apply `filter_pages()` from `src/privacy/exclude_tags.py` when `config.exclude_tags` is set
- [ ] **Write tests:**

```python
async def test_get_all_pages_excludes_journals_by_default(fake_client, config):
    fake_client.responses["get_all_pages"] = [
        {"id": 1, "originalName": "Regular", "journal?": False, ...},
        {"id": 2, "originalName": "2024-01-01", "journal?": True, ...},
    ]
    result = await get_all_pages(client=fake_client, config=config)
    assert "2024-01-01" not in result[0].text

async def test_get_all_pages_include_journals_true(fake_client, config):
    ...  # journals appear when include_journals=True

async def test_get_all_pages_respects_exclude_tags(fake_client, config_with_exclude):
    ...  # pages with excluded tag do not appear
```

- [ ] Run tests → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(get_all_pages): add include_journals and exclude_tags support`

---

### Step 2.2 — `get_all_page_content` — add `format`, `max_depth`, `resolve_refs`

- [ ] Add `format: str = "text"` (`"text"` | `"json"`) parameter
- [ ] Add `max_depth: int = -1` parameter (`-1` = unlimited)
- [ ] Add `resolve_refs: bool = True` parameter (DB-mode UUID resolution)
- [ ] **Write tests** for each new parameter
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(get_all_page_content): add format, max_depth, resolve_refs params`

---

### Step 2.3 — `get_page_links` → rename to `get_page_backlinks` + add `include_content`

- [ ] Rename file to `get_page_backlinks.py` and function to `get_page_backlinks`
- [ ] Keep `get_page_links.py` as a thin alias: `from .get_page_backlinks import get_page_backlinks as get_page_links` (backward compat)
- [ ] Add `include_content: bool = True` parameter
- [ ] **Write tests** for include_content=True/False
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(get_page_backlinks): rename and add include_content param`

---

### Step 2.4 — `get_block_content` — add `format`, `include_children`, DB-mode props

- [ ] Add `format: str = "text"` parameter
- [ ] Add `include_children: bool = True` parameter (currently always True)
- [ ] Add DB-mode property injection path through `LogseqClient.get_blocks_db_properties`
- [ ] **Write tests** for each parameter
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(get_block_content): add format, include_children, db-mode props`

---

### Step 2.5 — `create_page` — integrate markdown parser

- [ ] Add `content: str | None = None` parameter
- [ ] When `content` is provided, call `parse_content(content)` and use `insert_batch_block`
- [ ] Merge page-level frontmatter properties with explicit `properties` parameter
- [ ] **Write tests:**

```python
async def test_create_page_with_markdown_content(fake_client, config):
    await create_page(page_name="Test", content="# H1\ntext", client=fake_client, config=config)
    # verify fake_client received insert_batch_block call with correct blocks

async def test_create_page_frontmatter_merged_with_properties(fake_client, config):
    await create_page(
        page_name="Test",
        content="---\nstatus: active\n---\ncontent",
        properties={"priority": "high"},
        client=fake_client,
        config=config
    )
    # verify merged properties sent to API
```

- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(create_page): integrate markdown parser for content blocks`

---

## Phase 3 — New Write Tools

Each new tool follows the same TDD pattern:
1. Write test file with ≥ 5 test cases
2. Run → FAIL
3. Implement
4. Run → PASS
5. Commit

### Step 3.1 — `update_page.py`

**API calls:** `logseq.Editor.getPageBlocksTree` (clear) + `logseq.Editor.insertBatchBlock` (replace) or `logseq.Editor.appendBlockInPage` (append)

Parameters: `page_name: str`, `content: str | None`, `mode: str = "append"`, `properties: dict | None`

- [ ] **Write** `tests/tools/test_update_page.py` (≥ 5 tests):
  - `test_update_page_append_mode`
  - `test_update_page_replace_mode_clears_first`
  - `test_update_page_properties_only`
  - `test_update_page_empty_content_and_properties_returns_error`
  - `test_update_page_frontmatter_merged`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add update_page with append/replace modes`

---

### Step 3.2 — `delete_page.py`

**API call:** `logseq.Editor.deletePage`

Parameters: `page_name: str`

- [ ] **Write** `tests/tools/test_delete_page.py`:
  - `test_delete_page_success`
  - `test_delete_page_not_found_raises`
  - `test_delete_page_returns_confirmation_message`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add delete_page`

---

### Step 3.3 — `rename_page.py`

**API call:** `logseq.Editor.renamePage`

Parameters: `old_name: str`, `new_name: str`

- [ ] **Write** `tests/tools/test_rename_page.py`:
  - `test_rename_page_success`
  - `test_rename_page_same_name_is_error`
  - `test_rename_page_empty_new_name_is_error`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add rename_page`

---

### Step 3.4 — `delete_block.py`

**API call:** `logseq.Editor.removeBlock`

Parameters: `block_uuid: str`

- [ ] **Write** `tests/tools/test_delete_block.py` (≥ 3 tests)
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add delete_block`

---

### Step 3.5 — `update_block.py`

**API call:** `logseq.Editor.updateBlock`

Parameters: `block_uuid: str`, `content: str`

- [ ] **Write** `tests/tools/test_update_block.py`:
  - `test_update_block_success`
  - `test_update_block_empty_content_is_error`
  - `test_update_block_returns_uuid_in_message`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add update_block`

---

### Step 3.6 — `insert_nested_block.py`

**API call:** `logseq.Editor.insertBlock`

Parameters: `parent_block_uuid: str`, `content: str`, `properties: dict | None`, `sibling: bool = False`

- [ ] **Write** `tests/tools/test_insert_nested_block.py`:
  - `test_insert_as_child_default`
  - `test_insert_as_sibling_when_sibling_true`
  - `test_insert_with_properties`
  - `test_insert_returns_new_block_uuid`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add insert_nested_block`

---

### Step 3.7 — `set_block_properties.py`

**API call:** `logseq.Editor.upsertBlockProperty`

Parameters: `block_uuid: str`, `properties: dict`

This tool is DB-mode only. Guard with early return when `config.db_mode is False`.

- [ ] **Write** `tests/tools/test_set_block_properties.py`:
  - `test_set_block_properties_requires_db_mode`
  - `test_set_block_properties_calls_upsert_for_each_property`
  - `test_set_block_properties_unknown_property_warns`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add set_block_properties (DB-mode only)`

---

## Phase 4 — New Read Tools

### Step 4.1 — `search.py`

**API call:** `logseq.App.search`

Parameters: `query: str`, `limit: int = 20`, `include_blocks: bool = True`, `include_pages: bool = True`, `include_files: bool = False`

- [ ] Uses `format_search_results_markdown_mode` / `format_search_results_db_mode` from `formatters/search.py`
- [ ] Applies `exclude_tags` filtering to page results
- [ ] **Write** `tests/tools/test_search.py`:
  - `test_search_returns_blocks`
  - `test_search_returns_pages`
  - `test_search_no_results`
  - `test_search_excludes_restricted_pages`
  - `test_search_db_mode_uses_different_formatter`
  - `test_search_limit_respected`
- [ ] Implement `formatters/search.py` fully (both formatter functions)
- [ ] Run → **FAIL** → implement tool → **PASS**
- [ ] Commit: `feat(tools): add search with markdown and DB-mode support`

---

### Step 4.2 — `query.py`

**API call:** `logseq.DB.q`

Parameters: `query: str`, `limit: int = 100`, `result_type: str = "all"` (`"all"` | `"pages_only"` | `"blocks_only"`)

- [ ] **Write** `tests/tools/test_query.py`:
  - `test_query_returns_pages`
  - `test_query_filter_pages_only`
  - `test_query_filter_blocks_only`
  - `test_query_applies_exclude_tags`
  - `test_query_empty_result`
  - `test_query_limit_respected`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add query with DSL support`

---

### Step 4.3 — `find_pages_by_property.py`

**API call:** `logseq.DB.q` (constructs DSL query internally)

Parameters: `property_name: str`, `property_value: str | None = None`, `limit: int = 100`

- [ ] Validate `property_name` matches `^[a-zA-Z0-9_\-]+$` (guard clause, early return on invalid)
- [ ] Escape special chars in `property_value` before embedding in DSL
- [ ] **Write** `tests/tools/test_find_pages_by_property.py`:
  - `test_find_by_property_name_only`
  - `test_find_by_property_name_and_value`
  - `test_find_invalid_property_name_returns_error`
  - `test_find_no_results`
  - `test_find_limit_respected`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add find_pages_by_property`

---

### Step 4.4 — `get_pages_from_namespace.py`

**API call:** `logseq.Editor.getPagesFromNamespace`

Parameters: `namespace: str`

- [ ] **Write** `tests/tools/test_get_pages_from_namespace.py` (≥ 3 tests)
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add get_pages_from_namespace`

---

### Step 4.5 — `get_pages_tree_from_namespace.py`

**API call:** `logseq.Editor.getPagesTreeFromNamespace`

Parameters: `namespace: str`

- [ ] Implement tree formatter as a pure function in `formatters/pages.py`:

```python
def format_namespace_tree(pages: list[dict], prefix: str = "") -> list[str]:
    """Format a Logseq namespace tree into ASCII tree lines.

    Args:
        pages: Nested page list as returned by getPagesTreeFromNamespace.
        prefix: Current indentation prefix.

    Returns:
        List of tree-formatted lines.

    Complexity: O(N) where N is total node count.
    """
    ...
```

- [ ] **Write** `tests/tools/test_get_pages_tree_from_namespace.py`:
  - `test_tree_single_level`
  - `test_tree_nested`
  - `test_tree_empty_namespace`
  - `test_format_namespace_tree_uses_box_chars` (├── and └──)
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(tools): add get_pages_tree_from_namespace with ASCII tree`

---

## Phase 5 — DB-Mode Support

### Step 5.1 — Client DB-mode methods

- [ ] Implement in `LogseqClient`:
  - `datascript_query()` → `logseq.DB.datascriptQuery`
  - `resolve_page_uuids()` → batched `logseq.Editor.getPage` calls, returns `{uuid: name}`
  - `get_blocks_db_properties()` → uses `datascript_query` per block UUID
  - `resolve_property_ident()` → resolves property display name to internal ident

- [ ] **Write** `tests/client/test_logseq_client_db.py`:
  - `test_datascript_query_sends_correct_payload`
  - `test_resolve_page_uuids_batches_requests`
  - `test_get_blocks_db_properties_returns_keyed_dict`
  - `test_resolve_property_ident_returns_none_on_unknown`

- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(client): implement DB-mode methods in LogseqClient`

---

### Step 5.2 — DB-mode branches in tools

- [ ] `get_all_page_content`: when `config.db_mode` and `resolve_refs`, call `resolve_page_uuids` and pass `uuid_map` to `format_block_tree`
- [ ] `get_block_content`: same pattern
- [ ] `set_block_properties`: already gated; ensure `resolve_property_ident` is used
- [ ] `search`: route to `format_search_results_db_mode` when `config.db_mode`

- [ ] **Write** integration-style tests for each DB-mode branch using `FakeLogseqClient` with DB-mode `LogseqConfig`
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(db-mode): add DB-mode branches to content tools`

---

## Phase 6 — Privacy & Security

### Step 6.1 — Apply exclusion in all appropriate tools

- [ ] `get_all_pages` / `list_pages`: filter via `filter_pages()`
- [ ] `search`: filter page results via `excluded_page_names` set
- [ ] `query`: filter page-type results
- [ ] `find_pages_by_property`: filter results
- [ ] `get_page_content` / `get_all_page_content`: raise `LogseqAPIError` (access denied) when target page is excluded
- [ ] `get_page_backlinks`: filter source pages

- [ ] **Write** `tests/privacy/test_tool_exclusion.py`:
  - One test per tool verifying excluded page does not appear in output
  - One test verifying `get_page_content` raises error for excluded page
- [ ] Run → **FAIL** → implement → **PASS**
- [ ] Commit: `feat(privacy): apply exclude_tags filtering across all tools`

---

### Step 6.2 — `LOGSEQ_VERIFY_SSL` and `LOGSEQ_API_URL` support

- [ ] Update `load_config()` to handle `LOGSEQ_API_URL` (base URL) in addition to `LOGSEQ_API_ENDPOINT` (full URL)
- [ ] Parse `verify_ssl` from `LOGSEQ_VERIFY_SSL` env var; default to `True` when scheme is `https`
- [ ] Pass `ssl=config.verify_ssl` to `aiohttp.ClientSession` in `LogseqClient._call()`
- [ ] **Write** tests for SSL config loading
- [ ] Commit: `feat(config): add LOGSEQ_API_URL and LOGSEQ_VERIFY_SSL support`

---

## Phase 7 — Logging

### Step 7.1 — Structured logging

- [ ] Add `logging` setup in `src/server.py`:
  - Log to `~/.cache/logseq-api-mcp/server.log` with rotation
  - Fallback to stderr if log dir cannot be created
  - Log level controlled by `LOGSEQ_LOG_LEVEL` env var (default: `WARNING`)
- [ ] Each tool logs at `DEBUG` level on entry and `ERROR` on exception
- [ ] **Write** `tests/test_logging.py`: verify log file creation does not raise on permission error (test fallback)
- [ ] Commit: `feat(logging): add file-based logging with stderr fallback`

---

## Phase 8 — Optional Vector Search

**Prerequisite:** All previous phases passing.

### Step 8.1 — Add `[vector]` dependency group

- [ ] Update `pyproject.toml`:

```toml
[dependency-groups]
vector = [
    "lancedb>=0.6",
    "pyarrow>=14.0",
    "watchdog>=4.0",
    "portalocker>=2.0",
]
```

- [ ] Create `src/vector/__init__.py` with safe import guard:

```python
try:
    import lancedb  # noqa: F401
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
```

---

### Step 8.2 — `src/vector/config.py`

- [ ] **Create** `VectorConfig` dataclass with: `db_path`, `graph_path`, `exclude_tags`, `chunk_size`, `watch_debounce`
- [ ] `load_vector_config()` reads `LOGSEQ_VECTOR_ENABLED`, `LOGSEQ_VECTOR_PATH`, `LOGSEQ_GRAPH_PATH`; returns `None` when disabled
- [ ] **Write** `tests/vector/test_config.py` (3 tests)
- [ ] Commit: `feat(vector): add VectorConfig and load_vector_config`

---

### Step 8.3 — `src/vector/sync.py` — graph sync daemon

- [ ] Implement `sync_graph(config: VectorConfig) -> None` — scans markdown files, chunks, embeds, upserts into LanceDB
- [ ] Implement `watch_graph(config: VectorConfig) -> None` — uses `watchdog` to re-sync on file changes
- [ ] **Write** `tests/vector/test_sync.py` with a tmp-dir graph fixture
- [ ] Commit: `feat(vector): implement graph sync and watch daemon`

---

### Step 8.4 — `src/vector/search.py` — semantic search tool

- [ ] Function signature: `async def vector_search(query: str, limit: int = 10, client: LogseqClient | None = None, config: LogseqConfig | None = None) -> list[TextContent]`
- [ ] Embeds `query` using configured embedder, queries LanceDB, returns top-k results with page name, block UUID, and score
- [ ] **Write** `tests/vector/test_search.py` with a fixture LanceDB
- [ ] Commit: `feat(vector): add vector_search semantic search tool`

---

### Step 8.5 — `src/vector/status.py` — status tool

- [ ] Function signature: `async def vector_db_status(client: LogseqClient | None = None, config: LogseqConfig | None = None) -> list[TextContent]`
- [ ] Reports: enabled, DB path, doc count, last sync timestamp
- [ ] Commit: `feat(vector): add vector_db_status tool`

---

### Step 8.6 — Conditional registration in `registry.py`

- [ ] Import `VECTOR_AVAILABLE` from `src/vector/__init__.py`
- [ ] When `VECTOR_AVAILABLE` and `load_vector_config() is not None`, register vector tools
- [ ] **Write** test: `test_vector_tools_not_registered_when_deps_missing`
- [ ] Commit: `feat(registry): conditionally register vector tools when deps available`

---

### Step 8.7 — `logseq-sync` CLI entry point

- [ ] Add to `pyproject.toml`:

```toml
[project.scripts]
logseq-sync = "src.vector.sync:cli_entry"
```

- [ ] Implement `cli_entry()` using `argparse`: `--once` flag for one-shot sync, default is daemon watch
- [ ] Commit: `feat(vector): add logseq-sync CLI for graph vector sync`

---

## Phase 9 — Documentation & Final CI/CD

### Step 9.1 — Update `pyproject.toml`

- [ ] Add `aiohttp` SSL and connector options
- [ ] Ensure all new deps are in correct groups (`dev`, `test`, `vector`)
- [ ] Bump version to `0.2.0`
- [ ] Commit: `chore(deps): update pyproject.toml for v0.2.0`

---

### Step 9.2 — Update `README.md`

- [ ] Add all 12 new standard tools to the tool table
- [ ] Add environment variables table
- [ ] Add DB-mode section
- [ ] Add vector search section with setup instructions
- [ ] Add privacy/exclude_tags section
- [ ] Update configuration examples with new env vars
- [ ] Commit: `docs(readme): document all new tools and configuration`

---

### Step 9.3 — Update `CLAUDE.md`

- [ ] Add `src/client/`, `src/privacy/`, `src/parser/`, `src/vector/` to architecture overview
- [ ] Document `FakeLogseqClient` pattern for test authors
- [ ] Update "Adding New Tools" section to reflect injection pattern
- [ ] Commit: `docs(claude.md): update architecture and contribution guide`

---

### Step 9.4 — Test coverage gate

- [ ] Run: `uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=85`
- [ ] Fix any gaps until ≥ 85% is achieved
- [ ] Commit: `test: achieve ≥85% test coverage`

---

### Step 9.5 — CI/CD workflow updates

- [ ] Update `.github/workflows/test.yml` to include vector extra in matrix:

```yaml
matrix:
  include:
    - python-version: "3.11"
      extras: ""
    - python-version: "3.12"
      extras: "[vector]"
    - python-version: "3.13"
      extras: ""
```

- [ ] Update `quality.yml` to run mypy on `src/client/`, `src/privacy/`, `src/parser/`
- [ ] Update `pr-validation.yml` to verify tool count (expected ≥ 21 standard tools)
- [ ] Commit: `ci: update workflows for new architecture and vector extra`

---

## Deliverables Summary

| Phase | Deliverable | New Tools |
|-------|------------|-----------|
| 0 | Architecture refactor (standards compliance) | 0 |
| 1 | Markdown parser | 0 |
| 2 | Enhanced existing tools + privacy | 0 (9 enhanced) |
| 3 | New write tools | +7 |
| 4 | New read tools | +5 |
| 5 | DB-mode support | 0 |
| 6 | Privacy enforcement + SSL | 0 |
| 7 | Logging | 0 |
| 8 | Optional vector search | +3 |
| 9 | Docs + CI | 0 |
| **Total** | | **24 tools** |

---

## TDD Invariants (never break these)

- [ ] Every new function in `src/client/`, `src/privacy/`, `src/parser/`, `src/tools/formatters/` is a **pure function** tested in isolation with no mock/patch
- [ ] Every tool's test uses `FakeLogseqClient` — no `patch("aiohttp.ClientSession")` outside of `tests/client/`
- [ ] `uv run pytest tests/ -v` must be **fully green** after every commit
- [ ] `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` must pass before every commit
- [ ] `uv run mypy src/ --ignore-missing-imports` must pass with zero errors before merging each phase

---

## Quick-start command reference

```bash
# Install all deps
uv sync --dev

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Format and lint
uv run ruff check --fix && uv run ruff format

# Type check
uv run mypy src/ --ignore-missing-imports

# Security scan
uv run bandit -r src/

# Install with vector extras
uv sync --extra vector

# Run vector sync (once)
uv run logseq-sync --once

# Start MCP server
uv run mcp run src/server.py
```
