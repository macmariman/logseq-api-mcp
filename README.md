# Logseq API MCP Server

**Model Context Protocol server for Logseq API integration — 22 tools, dynamic discovery, DB-mode, privacy, and optional vector search**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green)](https://modelcontextprotocol.io/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![UV](https://img.shields.io/badge/package%20manager-uv-orange)](https://docs.astral.sh/uv/)
[![Tests](https://github.com/gustavo-meilus/logseq-api-mcp/workflows/Main%20CI%20Pipeline/badge.svg)](https://github.com/gustavo-meilus/logseq-api-mcp/actions/workflows/ci.yml)
[![Quality](https://github.com/gustavo-meilus/logseq-api-mcp/workflows/Advanced%20Quality%20%26%20Security/badge.svg)](https://github.com/gustavo-meilus/logseq-api-mcp/actions/workflows/quality.yml)

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Available Tools](#available-tools)
- [DB-Mode](#db-mode)
- [Privacy & Exclude Tags](#privacy--exclude-tags)
- [Vector Search (Optional)](#vector-search-optional)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Adding New Tools](#adding-new-tools)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Logseq API MCP Server provides AI assistants with seamless access to [Logseq](https://logseq.com/) knowledge bases via the [Model Context Protocol](https://modelcontextprotocol.io/). It ships 22 standard tools covering every read and write operation you need, plus an optional semantic vector search layer.

**Key features:**

- **Dynamic tool discovery** — drop a `.py` file in `src/tools/` and it registers automatically
- **DB-mode support** — works with both markdown-file graphs and the new Logseq database format
- **Privacy enforcement** — `LOGSEQ_EXCLUDE_TAGS` hides sensitive pages from all read operations
- **Optional vector search** — semantic block search via LanceDB (install the `[vector]` extra)
- **Structured logging** — rotating log file, configurable level via `LOGSEQ_LOG_LEVEL`
- **SSL control** — disable certificate verification for local/self-signed setups

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Logseq running with HTTP API enabled (see [Getting Your API Token](#getting-your-api-token))

### Quick Setup

```bash
git clone https://github.com/gustavo-meilus/logseq-api-mcp.git
cd logseq-api-mcp

# Install core dependencies
uv sync

# Optional: install vector search extras
uv sync --group vector

# Copy and edit environment template
cp .env.template .env
# Edit .env with your Logseq API details
```

### Getting Your API Token

1. Open Logseq
2. Go to **Settings → Features → Developer mode**
3. Enable **HTTP APIs server**
4. Copy the token shown
5. Note the endpoint (default: `http://127.0.0.1:12315/api`)

## Configuration

Create a `.env` file in the project root (or set variables in your shell/MCP host config):

```env
# Required
LOGSEQ_API_ENDPOINT=http://127.0.0.1:12315/api
LOGSEQ_API_TOKEN=your_api_token_here

# Optional
LOGSEQ_VERIFY_SSL=true
LOGSEQ_DB_MODE=false
LOGSEQ_EXCLUDE_TAGS=private,secret
LOGSEQ_LOG_LEVEL=WARNING

# Vector search (requires [vector] extra)
LOGSEQ_VECTOR_ENABLED=false
LOGSEQ_VECTOR_PATH=~/.cache/logseq-api-mcp/vector_db
LOGSEQ_GRAPH_PATH=~/logseq
```

### Claude Desktop / MCP Client

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "logseq-api": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/logseq-api-mcp",
        "python", "src/server.py"
      ],
      "env": {
        "LOGSEQ_API_ENDPOINT": "http://127.0.0.1:12315/api",
        "LOGSEQ_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOGSEQ_API_ENDPOINT` | `http://127.0.0.1:12315/api` | Logseq HTTP API base URL |
| `LOGSEQ_API_TOKEN` | *(required)* | Bearer token for Logseq API auth |
| `LOGSEQ_VERIFY_SSL` | `true` | Set `false` or `0` to skip TLS verification |
| `LOGSEQ_DB_MODE` | `false` | Set `true` to enable Logseq database-format support |
| `LOGSEQ_EXCLUDE_TAGS` | *(empty)* | Comma-separated tags; pages tagged with any are hidden from all reads |
| `LOGSEQ_LOG_LEVEL` | `WARNING` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOGSEQ_VECTOR_ENABLED` | `false` | Set `true` to enable vector search tools |
| `LOGSEQ_VECTOR_PATH` | `~/.cache/logseq-api-mcp/vector_db` | LanceDB storage path |
| `LOGSEQ_GRAPH_PATH` | `~/logseq` | Root of the Logseq markdown graph (for vector sync) |

## Available Tools

### Read Operations (12 tools)

| Tool | Description |
|---|---|
| `get_all_pages` | List every page with metadata (ID, UUID, journal flag, namespace) |
| `get_page_blocks` | Hierarchical block tree with IDs, UUIDs, and children counts |
| `get_page_links` | Pages linking to a target page (alias for `get_page_backlinks`) |
| `get_page_backlinks` | Full backlink analysis including block-level references |
| `get_block_content` | Block detail with properties and immediate children |
| `get_all_page_content` | Complete page: properties, blocks, DB-property resolution, ref expansion |
| `get_linked_flashcards` | Extracts flashcard Q&A pairs from a page and all its linked pages |
| `search` | Full-text search across blocks, pages, and files |
| `query` | Execute raw Datalog/DSL queries against the graph |
| `find_pages_by_property` | Filter pages by property key and optional value |
| `get_pages_from_namespace` | List all pages under a Logseq namespace |
| `get_pages_tree_from_namespace` | Nested tree of namespace pages |

### Write Operations (10 tools)

| Tool | Description |
|---|---|
| `create_page` | Create a page with optional properties and format |
| `delete_page` | Permanently remove a page |
| `rename_page` | Rename a page (updates all references) |
| `update_page` | Append or replace content on an existing page |
| `append_block_in_page` | Add blocks at the end of a page |
| `edit_block` | Replace a block's content |
| `update_block` | Update block content by UUID |
| `insert_nested_block` | Insert a child or sibling block relative to an existing block |
| `delete_block` | Delete a block by UUID |
| `set_block_properties` | Set properties on a block (DB-mode only) |

### Optional Vector Tools (requires `[vector]` extra + `LOGSEQ_VECTOR_ENABLED=true`)

| Tool | Description |
|---|---|
| `vector_search` | Semantic similarity search across all synced blocks |
| `vector_db_status` | Report vector DB status, doc count, and sync state |

## DB-Mode

Logseq's newer **database format** stores graph data in SQLite rather than markdown files. Enable DB-mode to unlock:

- `set_block_properties` — upsert structured properties on any block
- `get_all_page_content` with `resolve_refs=true` — resolves `[[uuid]]` references to page names
- `find_pages_by_property` — property-filtered Datalog queries

```env
LOGSEQ_DB_MODE=true
```

When DB-mode is off, `set_block_properties` returns an informative error message and the rest of the tools work as usual.

## Privacy & Exclude Tags

Any page tagged with a tag listed in `LOGSEQ_EXCLUDE_TAGS` is invisible to all read operations:

```env
LOGSEQ_EXCLUDE_TAGS=private,confidential,draft
```

Enforcement layers:

| Operation | Behavior |
|---|---|
| `get_all_pages` | Excluded pages absent from the listing |
| `search` | Excluded pages and their blocks filtered out |
| `query` | Results post-filtered against excluded page names |
| `find_pages_by_property` | Results post-filtered |
| `get_page_backlinks` | Source pages that are excluded are removed from results |
| `get_all_page_content` | Returns `❌ Access denied` when the requested page is excluded |

Exclusion is computed at query time — toggling `LOGSEQ_EXCLUDE_TAGS` takes effect on the next call.

## Vector Search (Optional)

Semantic search over your Logseq graph using [LanceDB](https://lancedb.github.io/lancedb/).

### Setup

```bash
# Install vector extras
uv sync --group vector

# Enable in env
export LOGSEQ_VECTOR_ENABLED=true
export LOGSEQ_GRAPH_PATH=/path/to/your/logseq/graph

# Build the index (one-shot)
uv run logseq-sync --once

# Or run as a daemon that watches for file changes
uv run logseq-sync
```

### CLI Reference

```
logseq-sync [--once]

  --once    Sync the graph once and exit (default: watch daemon)
```

### Using the MCP Tools

Once the index is built, the `vector_search` and `vector_db_status` tools are automatically registered when `LOGSEQ_VECTOR_ENABLED=true` and the `lancedb` package is installed.

```
vector_search(query="what is domain-driven design", limit=10)
vector_db_status()
```

## Usage Examples

### Find all pages in a namespace

```
get_pages_from_namespace("Projects")
```

### Search for a topic and get full content

```
search("spaced repetition")
get_all_page_content("Learning Systems")
```

### Create a page and add blocks

```
create_page("Meeting 2025-05-19", properties={"type": "meeting"})
update_page("Meeting 2025-05-19", content="- Agenda item 1\n- Agenda item 2")
```

### Extract flashcards for study

```
get_linked_flashcards("Domain Driven Design")
```

### Query the graph with Datalog

```
query('[:find ?name :where [?p :block/name ?name] [?p :block/properties ?props] [(get ?props :type) ?t] [(= ?t "book")]]')
```

## Development

### Project Structure

```
logseq-api-mcp/
├── .github/workflows/
│   ├── ci.yml             # Main test + lint pipeline
│   ├── quality.yml        # Mypy, Bandit, safety
│   ├── release.yml        # Cross-platform release tests
│   └── pr-validation.yml  # PR tool-count gate
├── src/
│   ├── server.py          # FastMCP server entry point
│   ├── registry.py        # Dynamic tool registration (+ vector conditional)
│   ├── logging_setup.py   # Rotating-file logger
│   ├── client/
│   │   ├── logseq_client.py   # Async HTTP client for Logseq API
│   │   ├── config.py          # LogseqConfig dataclass + load_config()
│   │   └── exceptions.py      # LogseqAPIError hierarchy
│   ├── parser/
│   │   └── markdown.py        # Markdown → block tree parser
│   ├── privacy/
│   │   └── exclude_tags.py    # Page exclusion by tag
│   ├── tools/
│   │   ├── __init__.py        # Auto-discovery scanner
│   │   ├── formatters/        # Pure formatting helpers
│   │   └── *.py               # 22 tool modules
│   └── vector/
│       ├── __init__.py        # VECTOR_AVAILABLE guard
│       ├── config.py          # VectorConfig + load_vector_config()
│       ├── sync.py            # sync_graph(), watch_graph(), cli_entry()
│       ├── search.py          # vector_search() MCP tool
│       └── status.py          # vector_db_status() MCP tool
└── tests/
    ├── conftest.py            # FakeLogseqClient test double
    ├── client/                # LogseqClient unit tests
    ├── parser/                # Markdown parser tests
    ├── privacy/               # Exclude-tags enforcement tests
    ├── tools/                 # Per-tool and formatter tests
    └── vector/                # Vector module tests
```

### Development Commands

```bash
# Install all deps
uv sync --dev

# Run tests with coverage
uv run --group test pytest tests/ --cov=src --cov-report=term-missing

# Format and lint
uv run ruff check --fix && uv run ruff format

# Type check
uv run mypy src/ --ignore-missing-imports

# Security scan
uv run bandit -r src/

# Dev server with MCP inspector
uv run mcp dev src/server.py
```

## Adding New Tools

The dynamic discovery system makes adding tools simple:

### 1. Create the tool file

```python
# src/tools/my_tool.py
from typing import List
from mcp.types import TextContent
from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.logging_setup import get_logger

_log = get_logger(__name__)

async def _run(client: LogseqClient, config: LogseqConfig, param: str) -> List[TextContent]:
    try:
        _log.debug("%s called", __name__)
        result = await client.some_api_call(param)
        return [TextContent(type="text", text=f"Result: {result}")]
    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {exc}")]

async def my_tool(param: str) -> List[TextContent]:
    """One-line description used as the MCP tool description.

    Args:
        param: Description of the parameter.

    Returns:
        List with one TextContent.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, param)
```

### 2. Write a test

```python
# tests/tools/test_my_tool.py
from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.my_tool import _run

_cfg = LogseqConfig("http://x", "t")

async def test_my_tool_returns_result():
    client = FakeLogseqClient({"some_api_call": "hello"})
    result = await _run(client, _cfg, "param")
    assert "hello" in result[0].text
```

### 3. That's it

The tool is automatically discovered, imported, and registered. No configuration changes needed.

**Rules:**
- File must be in `src/tools/`
- Function name must not start with `_`
- Use the `_run(client, config, ...)` pattern for testability
- Public function creates `LogseqClient(cfg)` and calls `_run`

## Testing

```bash
# Run full suite
uv run --group test pytest tests/ -v

# With coverage
uv run --group test pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=85

# Run a specific test file
uv run --group test pytest tests/tools/test_search.py -v
```

**Current coverage: 87%** across 345 tests.

The test double `FakeLogseqClient` (defined in `tests/conftest.py`) accepts a dict of `method_name → return_value` and records all calls in `self.calls`. Every tool test uses this pattern — no `aiohttp` patching.

## CI/CD Pipeline

| Workflow | Triggers | Checks |
|---|---|---|
| `ci.yml` | push/PR to main | pytest ≥85% coverage, ruff lint+format, tool count gate |
| `quality.yml` | PR to main | mypy, bandit, safety, license check |
| `release.yml` | release event / weekly | cross-platform (ubuntu/windows/macos × py3.11/3.12/3.13) |
| `pr-validation.yml` | PR to main | verifies ≥21 standard tools are registered |

## Contributing

1. Fork and create a feature branch
2. Add a tool file to `src/tools/` following the pattern above
3. Add tests to `tests/tools/`
4. Run `uv run ruff check --fix && uv run ruff format && uv run --group test pytest tests/ -v`
5. Open a pull request

## License

MIT — see [LICENSE](LICENSE).

---

**Made for the Logseq and MCP communities**
