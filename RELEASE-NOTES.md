# Release Notes — v1.0.0

**Released:** 2026-05-19

## What's New

### 22 Standard Tools

13 new tools added on top of the original 9:

#### New Write Tools
- **`delete_block`** — remove a block and its children by UUID
- **`delete_page`** — permanently delete a page by name
- **`update_block`** — replace a block's content in-place by UUID
- **`update_page`** — append or replace page content; supports frontmatter merge
- **`insert_nested_block`** — insert a child or sibling block relative to any block
- **`rename_page`** — rename a page without breaking backlinks
- **`set_block_properties`** — upsert key/value properties on a block (DB-mode)

#### New Read & Query Tools
- **`search`** — full-text search across all pages and blocks
- **`query`** — run raw Datalog queries against the Logseq graph
- **`find_pages_by_property`** — filter pages by a property key/value pair
- **`get_pages_from_namespace`** — list all pages under a namespace prefix
- **`get_page_backlinks`** — fetch backlinks for a page with optional block content
- **`get_pages_tree_from_namespace`** — retrieve the full namespace tree

### Optional Vector Search

Two new tools activated by `LOGSEQ_VECTOR_ENABLED=true` (requires the `[vector]` extra):

- **`vector_search`** — semantic similarity search over your graph using LanceDB embeddings
- **`vector_db_status`** — report vector DB health, document count, and last-sync time

The `logseq-sync` CLI builds and watches the vector index:

```bash
uv sync --group vector
uv run logseq-sync          # watch mode
uv run logseq-sync --once   # one-shot sync
```

### DB-Mode Support

Set `LOGSEQ_DB_MODE=true` to target Logseq's SQLite database format. Unlocks:
- `set_block_properties` tool for direct property upserts
- UUID-reference resolution in `get_all_page_content`
- Datalog-powered `find_pages_by_property`

### Privacy / Exclude-Tags

`LOGSEQ_EXCLUDE_TAGS` hides pages tagged with any listed tag from all read operations: `get_all_pages`, `search`, `query`, `find_pages_by_property`, `get_page_backlinks`, and `get_all_page_content` (access-denied guard on direct fetch).

### Structured Logging

- Rotating file log at `~/.cache/logseq-api-mcp/server.log`
- stderr fallback when file log is unavailable
- Configurable via `LOGSEQ_LOG_LEVEL` (default: `WARNING`)

### Markdown Parser

`parse_content()` converts markdown strings into `ParsedContent(blocks, properties)`. Used by `create_page` and `update_page` for frontmatter extraction and block ingestion.

### Architecture Improvements

- **Injected-client pattern** — all tools split into `_run(client, config, ...)` (testable) and a public MCP-facing wrapper; zero `aiohttp` patching in tool tests
- **`LogseqClient`** — async aiohttp wrapper with SSL control and DB-mode methods
- **`LogseqConfig`** — frozen dataclass replacing raw env-var reads across all tools
- **Pure formatter modules** — `pages.py`, `blocks.py`, `search.py` extracted as zero-mock-testable pure functions
- **Privacy module** — `extract_tags`, `is_page_excluded`, `filter_pages` pure functions

### Test Suite

- Expanded from ~68 to **345 tests** with **87% coverage**
- Coverage gate raised from 80% to **85%**
- New test directories: `tests/client/`, `tests/parser/`, `tests/privacy/`, `tests/tools/formatters/`, `tests/vector/`

### CI/CD

- `ci.yml` — matrix now includes Python 3.12 + `[vector]` group; coverage gate at 85%; tool-count step verifies all 22 standard tools
- `quality.yml` — mypy now targets all new source modules
- `pr-validation.yml` (new) — three-job PR gate: tool count ≥21, coverage ≥85%, ruff lint + format

### Claude Plugin

- `.claude-plugin/plugin.json` — MCP server manifest for Claude Desktop auto-configuration
- `.claude-plugin/marketplace.json` — Claude marketplace metadata

## Upgrade Notes

> **No breaking changes.** All original 9 tools (`get_all_pages`, `get_page_blocks`, `get_page_links`, `get_block_content`, `get_all_page_content`, `get_linked_flashcards`, `append_block_in_page`, `create_page`, `edit_block`) are fully backward-compatible.
>
> New environment variables (`LOGSEQ_DB_MODE`, `LOGSEQ_EXCLUDE_TAGS`, `LOGSEQ_LOG_LEVEL`, `LOGSEQ_VECTOR_*`) are all optional with safe defaults — existing `.env` files continue to work without changes.
>
> The `[vector]` dependency group is opt-in: `uv sync --group vector`. Vector tools only register when `LOGSEQ_VECTOR_ENABLED=true`.

## Contributors

- [@gustavo-meilus](https://github.com/gustavo-meilus) — project author
- [@Clausinho](https://github.com/Clausinho) — pagination support for `get_all_pages`
- [@tkolleh](https://github.com/tkolleh) — `.env.template` fix
