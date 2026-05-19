# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.1] - 2026-05-19

### Removed
- Vector subsystem (`src/vector/`, `vector_search`, `vector_db_status`, `logseq-sync` CLI, `[vector]` dep group) — retraction; the v1.0.0 implementation shipped without an embedder and was non-functional. See `MIGRATION.md`.
- `get_page_links` tool alias — use `get_page_backlinks`.
- `pathlib>=1.0.1` and `load-dotenv` runtime dependencies.

### Added
- `LogseqClient.excluded_page_names(ttl_seconds)` cached privacy helper.
- `LogseqNotFoundError` raised on HTTP 404; `LogseqConnectionError` reserved for network failures only.
- `pyyaml` runtime dependency for proper Markdown frontmatter parsing.

### Changed
- `register_all_tools(mcp, client, config)` — shared `LogseqClient` lifetime across the process.
- `LogseqConfig.verify_ssl` default flipped to `True`.
- `LogseqClient.create_page` now passes `properties` as the second positional arg per the official `IEditorProxy` signature.
- `LogseqClient.append_block_in_page` forwards optional `options` arg.
- `LogseqClient.resolve_property_ident` query now binds `?ident` (was incorrectly `?e`) and escapes input.
- `LogseqClient.resolve_page_uuids` batches via a single datascript query.
- `extract_tags` is case-insensitive and supports the DB-mode `[{name: "x"}]` shape.
- `update_page` replace mode uses `insert_batch_block` to preserve block hierarchy.

### Fixed
- `src/tools/__init__.py` no longer writes to stdout (fixes MCP stdio JSON-RPC corruption on tool-import failure).
- `find_pages_by_property` accepts namespaced property names; escapes `\` and `"`; caps values at 256 chars.
- DB-mode tools resolve UUID → name before calling `getPageBlocksTree` (workaround for logseq/logseq#4920).

---

## [1.0.0] - 2026-05-19

### New Features

- **22 standard tools** — 13 new tools added on top of the original 9: `delete_block`, `delete_page`, `update_block`, `update_page`, `insert_nested_block`, `rename_page`, `set_block_properties` (DB-mode), `search`, `query`, `find_pages_by_property`, `get_pages_from_namespace`, `get_page_backlinks`, `get_pages_tree_from_namespace`
- **Optional vector search** — `vector_search` and `vector_db_status` tools via LanceDB; `logseq-sync` CLI builds and watches the index; activated by `LOGSEQ_VECTOR_ENABLED=true` with the `[vector]` extra
- **DB-mode support** — set `LOGSEQ_DB_MODE=true` to target Logseq's SQLite database format; unlocks `set_block_properties`, UUID-reference resolution in `get_all_page_content`, and Datalog-powered `find_pages_by_property`
- **Privacy / exclude-tags** — `LOGSEQ_EXCLUDE_TAGS` hides tagged pages from all read operations: `get_all_pages`, `search`, `query`, `find_pages_by_property`, `get_page_backlinks`, and `get_all_page_content` (access-denied guard)
- **Structured logging** — rotating file handler (`~/.cache/logseq-api-mcp/server.log`), stderr fallback, configurable via `LOGSEQ_LOG_LEVEL`
- **Markdown parser** — `parse_content()` converts markdown strings into `ParsedContent(blocks, properties)` used by `create_page` and `update_page`
- **`get_all_pages`** — new `include_journals` filter parameter
- **`get_all_page_content`** — new `format`, `max_depth`, and `resolve_refs` parameters; DB-mode UUID-reference expansion
- **`get_block_content`** — new `format`, `include_children`, and DB-mode property resolution parameters
- **`get_page_backlinks`** — renamed from `get_page_links` alias; new `include_content` parameter
- **`create_page`** — content parameter uses markdown parser for block ingestion with frontmatter support
- **`.claude-plugin/`** — `plugin.json` (MCP server manifest) and `marketplace.json` (Claude marketplace metadata)

### Architecture

- **Injected-client pattern** — all 22 tools split into `_run(client, config, ...)` (testable) and a public MCP-facing wrapper; zero `aiohttp` patching in tool tests
- **`LogseqClient`** — async aiohttp wrapper for every Logseq API call with SSL control and DB-mode methods (`datascript_query`, `resolve_page_uuids`, `get_blocks_db_properties`, `resolve_property_ident`, `upsert_block_property`)
- **`LogseqConfig`** — frozen dataclass replacing raw env-var reads in every tool
- **Pure formatter modules** — `src/tools/formatters/pages.py`, `blocks.py`, `search.py` extracted as zero-mock-testable pure functions
- **`src/privacy/exclude_tags.py`** — `extract_tags`, `is_page_excluded`, `filter_pages` pure functions
- **`src/vector/`** — `VectorConfig`, `sync_graph`, `watch_graph`, `vector_search`, `vector_db_status`, `cli_entry`

### Testing

- Test suite expanded from ~68 to **345 tests** with **87% coverage**
- Coverage gate raised from 80% to **85%** (≥85% required for CI to pass)
- New test directories: `tests/client/`, `tests/parser/`, `tests/privacy/`, `tests/tools/formatters/`, `tests/vector/`

### CI/CD

- `ci.yml` — matrix now includes Python 3.12 + `[vector]` group; coverage gate raised to 85%; tool-count step verifies all 22 standard tools are present
- `quality.yml` — mypy now targets all new source modules (`src/client/`, `src/privacy/`, `src/parser/`, `src/tools/`, `src/vector/`)
- `pr-validation.yml` (new) — three-job PR gate: tool count ≥21, coverage ≥85%, ruff lint + format

### Documentation

- `README.md` — complete rewrite: pain-point hook in first 43 words, dark/light SVG architecture diagram via `<picture>`, 22-tool tables, environment variables table, DB-mode/privacy/vector sections
- `CLAUDE.md` — updated with full module map, `FakeLogseqClient` test pattern, all env vars, and TDD invariants
- `assets/architecture-dark.svg` + `assets/architecture-light.svg` — hand-crafted SVGs with automatic GitHub dark/light mode switching

### Upgrade Notes

> No breaking changes to existing tools (`get_all_pages`, `get_page_blocks`, `get_page_links`, `get_block_content`, `get_all_page_content`, `get_linked_flashcards`, `append_block_in_page`, `create_page`, `edit_block`).
>
> New environment variables (`LOGSEQ_DB_MODE`, `LOGSEQ_EXCLUDE_TAGS`, `LOGSEQ_LOG_LEVEL`, `LOGSEQ_VECTOR_*`) are optional with safe defaults — existing `.env` files continue to work without changes.
>
> The `[vector]` dependency group is opt-in: `uv sync --group vector`. Vector tools only register when `LOGSEQ_VECTOR_ENABLED=true`.

[1.0.0]: https://github.com/gustavo-meilus/logseq-api-mcp/compare/v0.1.0...v1.0.0

---

## [0.1.0] - 2026-05-18

### New Features

- **Dynamic Tool Discovery System** — zero-configuration tool management: any `.py` file added to `src/tools/` is automatically discovered, imported, and registered with the MCP server without manual wiring
- **`get_all_pages`** — list all Logseq pages with metadata (ID, UUID, journal/regular classification); includes pagination support contributed by the community
- **`get_page_blocks`** — retrieve hierarchical block tree structure for any page with block IDs, UUIDs, parent-child relationships, and property extraction
- **`get_page_links`** — find all pages that reference a target page, with metadata and relationship analysis
- **`get_block_content`** — get detailed content of a specific block including its immediate children, by UUID
- **`get_all_page_content`** — comprehensive page content extraction including properties, all blocks, flashcard detection, and linked references
- **`get_linked_flashcards`** — extract and aggregate flashcards from a target page and all pages it links to; supports multi-choice questions and cross-page discovery
- **`append_block_in_page`** — append new blocks to a page with flexible positioning (before a block, as a sibling, or at the end); supports page-level blocks
- **`create_page`** — create new Logseq pages with custom properties, format (markdown/org), and journal detection
- **`edit_block`** — edit an existing block's content, properties, cursor position, and focus state by UUID
- **CI/CD Pipeline** — full GitHub Actions suite with test, quality, and release workflows
- **Cross-platform testing** — matrix testing across Ubuntu, Windows, macOS on Python 3.11, 3.12, and 3.13
- **Pre-commit hooks** — Ruff formatting and linting enforced on commit via `.pre-commit-config.yaml`
- **Makefile** — convenience targets for common development tasks
- **MyPy type checking** — integrated into the code quality workflow
- **Security scanning** — Bandit static analysis and pip-audit dependency vulnerability checks

### Bug Fixes

- Replace relative imports with absolute imports so `uv run mcp run src/server.py` starts correctly
- Fix CI workflow `uv sync` commands to include correct dependency groups (`--group dev`, `--group test`)
- Replace deprecated `safety` tool with `pip-audit` for vulnerability scanning
- Upgrade vulnerable transitive dependencies to patched versions
- Fix whitespace inconsistencies in `get_all_pages.py`
- Include missing `.env.template` in repository

### Refactoring

- Standardize property variable naming across all tool modules
- Improve sorting methods in multi-tool output for consistent ordering
- Remove unused example file from repository

### Documentation

- `README.md` — full documentation with tool details, usage examples, CI/CD pipeline description, and adding-new-tools guide
- `CONTRIBUTING.md` — GitHub Flow contribution guidelines and tool addition walkthrough
- `.github/ISSUE_TEMPLATE/` — bug report and feature request templates
- `.github/pull_request_template.md` — PR checklist template
- `.github/CI_CD_SETUP.md` and `.github/workflows/README.md` — workflow documentation

[0.1.0]: https://github.com/gustavo-meilus/logseq-api-mcp/commits/main
