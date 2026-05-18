# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
