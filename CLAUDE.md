# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** that gives AI assistants access to Logseq knowledge bases. It ships **22 standard tools** (read + write) and 2 optional vector-search tools, all discovered and registered automatically.

**Key Innovation**: Zero-configuration tool management — drop a `.py` file into `src/tools/` and it is auto-discovered, imported, and registered with the MCP server.

## Core Architecture

### Module Map

```
src/
├── server.py          # FastMCP entry point; calls setup_logging() + register_all_tools()
├── registry.py        # Iterates tools.__all__; conditionally adds vector tools
├── logging_setup.py   # setup_logging() rotating-file logger; get_logger() child logger
├── client/
│   ├── logseq_client.py   # LogseqClient — async aiohttp wrapper for every Logseq API call
│   ├── config.py          # LogseqConfig frozen dataclass; load_config() reads env vars
│   └── exceptions.py      # LogseqAPIError, LogseqAuthError, LogseqNotFoundError
├── parser/
│   └── markdown.py        # parse_content(text) → ParsedContent(blocks, properties)
├── privacy/
│   └── exclude_tags.py    # filter_pages(), is_page_excluded(), extract_tags()
├── tools/
│   ├── __init__.py        # Scans *.py, imports each, adds public functions to __all__
│   ├── formatters/        # Pure formatter functions (pages.py, blocks.py, search.py)
│   └── *.py               # 22 tool modules — one public async function each
└── vector/
    ├── __init__.py        # VECTOR_AVAILABLE = True/False (safe lancedb import)
    ├── config.py          # VectorConfig dataclass; load_vector_config()
    ├── sync.py            # sync_graph(), watch_graph(), cli_entry()
    ├── search.py          # vector_search() MCP tool
    └── status.py          # vector_db_status() MCP tool
```

### Dynamic Tool Discovery

1. `src/tools/__init__.py` uses `importlib` to import every `*.py` file in `src/tools/` (skipping `_*` and `formatters/`).
2. It adds any function where `obj.__module__ == module.__name__` to `__all__`.
3. `src/registry.py` iterates `tools.__all__` and calls `mcp_server.tool()(fn)` for each.
4. When `VECTOR_AVAILABLE` is `True` and `load_vector_config()` is not `None`, `vector_search` and `vector_db_status` are also registered.

**Critical rule**: A tool function must be **defined in its own file** — not imported from another module — for dynamic discovery to pick it up.

### Tool Pattern

Every tool follows the **injected-client pattern**:

```python
# src/tools/my_tool.py
async def _run(client: LogseqClient, config: LogseqConfig, param: str) -> List[TextContent]:
    """Private; accepts injected client for testing."""
    try:
        _log.debug("%s called", __name__)
        result = await client.some_method(param)
        return [TextContent(type="text", text=f"...{result}...")]
    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {exc}")]

async def my_tool(param: str) -> List[TextContent]:
    """MCP-facing function; creates real client from env config."""
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, param)
```

`_run` is what tests call. The public `my_tool` is what the MCP server registers.

### LogseqConfig

Frozen dataclass in `src/client/config.py`:

```python
@dataclass(frozen=True)
class LogseqConfig:
    endpoint: str
    token: str
    verify_ssl: bool = True
    db_mode: bool = False
    exclude_tags: list[str] = field(default_factory=list)
```

`load_config()` reads `LOGSEQ_API_ENDPOINT`, `LOGSEQ_API_TOKEN`, `LOGSEQ_VERIFY_SSL`, `LOGSEQ_DB_MODE`, `LOGSEQ_EXCLUDE_TAGS`.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev tools (mypy, ruff, bandit, etc.)
uv sync --dev

# Install with vector extras
uv sync --group vector

# Run test suite
uv run --group test pytest tests/ -v

# With coverage gate (≥85% required)
uv run --group test pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=85

# Format and lint (must pass before every commit)
uv run ruff check --fix && uv run ruff format

# Type check
uv run mypy src/ --ignore-missing-imports

# Security scan
uv run bandit -r src/

# Start MCP server
uv run mcp run src/server.py

# Dev mode with MCP Inspector
uv run mcp dev src/server.py

# One-shot vector sync
uv run logseq-sync --once
```

## Adding New Tools

### 1. Create `src/tools/your_tool.py`

```python
from typing import List
from mcp.types import TextContent
from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.logging_setup import get_logger

_log = get_logger(__name__)

async def _run(client: LogseqClient, config: LogseqConfig, param: str) -> List[TextContent]:
    try:
        _log.debug("%s called", __name__)
        data = await client.some_api_method(param)
        return [TextContent(type="text", text=str(data))]
    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {exc}")]

async def your_tool(param: str) -> List[TextContent]:
    """One-line description becomes the MCP tool description.

    Args:
        param: Description used in MCP tool schema.

    Returns:
        List with one TextContent.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, param)
```

### 2. Create `tests/tools/test_your_tool.py`

```python
from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.your_tool import _run

_cfg = LogseqConfig("http://x", "t")

async def test_your_tool_happy_path():
    client = FakeLogseqClient({"some_api_method": {"key": "value"}})
    result = await _run(client, _cfg, "input")
    assert "value" in result[0].text

async def test_your_tool_handles_exception():
    class Broken(FakeLogseqClient):
        async def some_api_method(self, *a, **kw):
            raise RuntimeError("oops")
    result = await _run(Broken(), _cfg, "input")
    assert "❌" in result[0].text
```

### 3. That's it

No imports, no registration, no config changes required.

## Testing Strategy

### FakeLogseqClient

`tests/conftest.py` defines `FakeLogseqClient`:

```python
class FakeLogseqClient(LogseqClient):
    def __init__(self, responses: dict = None):
        # does NOT call super().__init__()
        self.responses = responses or {}
        self.calls = []   # [(method_name, *args, **kwargs), ...]

    async def some_method(self, *args, **kwargs):
        self.calls.append(("some_method", *args, kwargs))
        return self.responses.get("some_method")
```

- Pass `{"method_name": return_value}` to pre-configure return values.
- Read `client.calls` to assert what the tool invoked and with what arguments.
- **Never use `patch("aiohttp.ClientSession")` in tool tests.** Reserve `aiohttp` patching for `tests/client/`.

### Test Hierarchy

| Directory | What it tests | Allowed mocks |
|---|---|---|
| `tests/client/` | `LogseqClient`, `LogseqConfig`, exceptions | `aiohttp` patching OK |
| `tests/parser/` | `parse_content()` and `BlockNode` | None (pure functions) |
| `tests/privacy/` | `filter_pages()`, tool-level exclusion | `FakeLogseqClient` |
| `tests/tools/` | Individual tool `_run()` functions | `FakeLogseqClient` |
| `tests/vector/` | VectorConfig, sync, search, status | `unittest.mock.patch` on lancedb |

### TDD Invariants

- `uv run --group test pytest tests/ -v` — must be **fully green** after every commit.
- `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` — must pass before every commit.
- `uv run mypy src/ --ignore-missing-imports` — zero errors before merging a phase.
- Every new `src/client/`, `src/privacy/`, `src/parser/`, or `src/tools/formatters/` function is tested with **no mocks** (pure functions).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOGSEQ_API_ENDPOINT` | `http://127.0.0.1:12315/api` | Logseq HTTP API URL |
| `LOGSEQ_API_TOKEN` | *(required)* | Bearer auth token |
| `LOGSEQ_VERIFY_SSL` | `true` | Set `false`/`0`/`no` to skip TLS verification |
| `LOGSEQ_DB_MODE` | `false` | Enable Logseq database-format API paths |
| `LOGSEQ_EXCLUDE_TAGS` | *(empty)* | Comma-separated tags; pages tagged with any are hidden |
| `LOGSEQ_LOG_LEVEL` | `WARNING` | Python log level for `logseq_mcp.*` logger |
| `LOGSEQ_VECTOR_ENABLED` | `false` | Enable vector search tools |
| `LOGSEQ_VECTOR_PATH` | `~/.cache/logseq-api-mcp/vector_db` | LanceDB directory |
| `LOGSEQ_GRAPH_PATH` | `~/logseq` | Logseq markdown graph root for vector sync |

## Key Dependencies

| Package | Purpose |
|---|---|
| `mcp[cli]` | FastMCP server + MCP protocol |
| `aiohttp` | Async HTTP client for Logseq API |
| `load-dotenv` | `.env` file loading |
| `ruff` (dev) | Formatting and linting |
| `mypy` (dev) | Static type checking |
| `bandit` (dev) | Security linting |
| `pytest` + `pytest-asyncio` (test) | Test runner with async support |
| `lancedb` (vector) | Vector database for semantic search |
| `watchdog` (vector) | File-system watcher for graph sync |
