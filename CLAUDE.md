# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** that gives AI assistants access to Logseq knowledge bases. Tools live under `src/tools/` and are discovered automatically. A subset is hidden by default via `@hidden` to keep the per-turn token cost down (see "Hiding / Reactivating Tools"); filesystem tools (`fs_*`) only register when `LOGSEQ_GRAPH_PATH` is set.

**Key Innovation**: Zero-configuration tool management — drop a `.py` file into `src/tools/` and it is auto-discovered, imported, and registered with the MCP server.

## Core Architecture

### Module Map

```
src/
├── server.py          # FastMCP entry point; calls setup_logging() + register_all_tools()
├── registry.py        # Iterates tools.__all__ and registers each with the MCP server
├── logging_setup.py   # setup_logging() rotating-file logger; get_logger() child logger
├── client/
│   ├── logseq_client.py   # LogseqClient — async aiohttp wrapper for every Logseq API call
│   ├── config.py          # LogseqConfig frozen dataclass; load_config() reads env vars
│   └── exceptions.py      # LogseqAPIError, LogseqAuthError, LogseqNotFoundError
├── parser/
│   └── markdown.py        # parse_content(text) → ParsedContent(blocks, properties)
├── privacy/
│   └── exclude_tags.py    # filter_pages(), is_page_excluded(), extract_tags()
└── tools/
    ├── __init__.py        # Scans *.py, imports each, adds public functions to __all__
    ├── formatters/        # Pure formatter functions (pages.py, blocks.py, search.py)
    └── *.py               # one tool per module — one public async function each
```

### Dynamic Tool Discovery

1. `src/tools/__init__.py` uses `importlib` to import every `*.py` file in `src/tools/` (skipping `_*` and `formatters/`).
2. It adds any function where `obj.__module__ == module.__name__` to `__all__`.
3. `src/registry.py` iterates `tools.__all__` and calls `mcp_server.tool()(fn)` for each.

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

`load_config()` reads `LOGSEQ_API_ENDPOINT`, `LOGSEQ_API_TOKEN`, `LOGSEQ_VERIFY_SSL`, `LOGSEQ_DB_MODE`, `LOGSEQ_GRAPH_PATH`, `LOGSEQ_EXCLUDE_TAGS`.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev tools (mypy, ruff, bandit, etc.)
uv sync --dev

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

## Hiding / Reactivating Tools

Tools can be hidden from the MCP client without deletion, via the `@hidden` decorator in `src/tools/_marker.py`. Hidden tools stay in `tools.__all__`, remain importable, and are still covered by surface-contract tests — `src/registry.py` filters them out at FastMCP registration time.

**Why hide**: each visible tool costs ~200–300 input tokens per turn in the MCP schema. Hiding 10 redundant or rarely-used tools saves roughly 2.5k tokens per turn without losing the ability to bring them back.

**To hide a tool**, two lines added to the tool file:

```python
from src.tools._marker import hidden

# Hidden: <reason — keep this comment so future readers know why>
@hidden
async def my_tool(...):
    ...
```

**To reactivate**, comment or delete those two lines and restart the MCP server:

```python
# from src.tools._marker import hidden
#
# @hidden
async def my_tool(...):
    ...
```

**Invariants**:
- `tools.__all__` always contains every discovered tool (visible + hidden). Tests audit the full surface.
- `registry.register_all_tools()` is the single point that filters `_mcp_hidden`. No env var, no global state.
- Hidden tools must still pass `mypy`, `ruff`, and all existing tests. The `@hidden` decorator does not change the function signature or behavior.

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
| `LOGSEQ_GRAPH_PATH` | *(empty)* | Absolute path to the graph root; registers the `fs_*` filesystem tools |
| `LOGSEQ_EXCLUDE_TAGS` | *(empty)* | Comma-separated tags; pages tagged with any are hidden |
| `LOGSEQ_LOG_LEVEL` | `WARNING` | Python log level for `logseq_mcp.*` logger |

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
