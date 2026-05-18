# Release Notes — v0.1.0

**Released:** 2026-05-18

## What's New

### New Tools

Nine MCP tools are available out of the box:

#### Read Operations
- **`get_all_pages`** — list all pages in the knowledge base with ID, UUID, and journal/regular classification. Supports pagination for large graphs.
- **`get_page_blocks`** — retrieve the full hierarchical block tree of any page, with block IDs, UUIDs, parent-child relationships, and extracted properties.
- **`get_page_links`** — discover all pages that link to a target page, with relationship metadata.
- **`get_block_content`** — fetch detailed content for a specific block (by UUID) including its immediate children.
- **`get_all_page_content`** — comprehensive extraction of a page's properties, blocks, flashcards, and linked references in a single call.
- **`get_linked_flashcards`** — aggregate flashcards from a target page and all pages it links to; supports multi-choice questions and cross-page discovery.

#### Write Operations
- **`append_block_in_page`** — append new blocks to any page with flexible positioning: before a specific block, as a sibling, or at the end of the page.
- **`create_page`** — create new Logseq pages with custom properties, format (markdown/org), and automatic journal detection.
- **`edit_block`** — modify an existing block's content, properties, cursor position, and focus state by UUID.

### Dynamic Tool Discovery System

The server uses a zero-configuration architecture: any `.py` file placed in `src/tools/` is automatically discovered, imported, and registered — no manual wiring required. New tools become immediately available to MCP clients without restarting or changing any configuration.

### CI/CD Pipeline

- Cross-platform matrix testing (Ubuntu, Windows, macOS) across Python 3.11, 3.12, and 3.13
- Automated code quality checks: Ruff formatting/linting, MyPy type checking
- Security scanning: Bandit static analysis, pip-audit dependency auditing
- Coverage gates: 80% minimum for PR validation, 85% for release builds

## Bug Fixes

- Replaced relative imports with absolute imports, fixing server startup when launched via `uv run mcp run src/server.py`
- Upgraded vulnerable transitive dependencies to patched versions
- Fixed CI workflow dependency group flags (`--group dev`, `--group test`)
- Replaced deprecated `safety` scanner with `pip-audit`

## Upgrade Notes

> This is the initial release. No migration steps required.

## Contributors

- [@gustavo-meilus](https://github.com/gustavo-meilus) — project author
- [@Clausinho](https://github.com/Clausinho) — pagination support for `get_all_pages`
- [@tkolleh](https://github.com/tkolleh) — `.env.template` fix
