# Release Notes — v1.0.1

**Released:** 2026-05-19

v1.0.1 is a correctness, hygiene, and contract-fixing release. It addresses 15 findings surfaced by the v1.0.0 audit against the [Logseq HTTP API](https://wiki.jamesravey.me/books/software-engineering/page/logseq-http-api), the [`IEditorProxy`](https://logseq.github.io/plugins/interfaces/IEditorProxy.html) TypeScript signatures, and the [MCP `build-server`](https://modelcontextprotocol.io/docs/develop/build-server) stdio constraint. It also retracts the non-functional vector-search subsystem.

## What's New

### Privacy helper with caching
- `LogseqClient.excluded_page_names(ttl_seconds=60.0) -> frozenset[str]`: cached lower-cased set of pages hidden by `LOGSEQ_EXCLUDE_TAGS`. `search`, `query`, `find_pages_by_property`, and `get_page_backlinks` now call this once per request instead of fetching `get_all_pages()` inline.
- `extract_tags` is now case-insensitive and accepts the DB-mode `[{"name": "x"}]` shape in addition to lists and comma-strings.

### Exception hierarchy
- `LogseqNotFoundError` is now raised on HTTP `404`.
- `LogseqConnectionError` is reserved for genuine network failures (`aiohttp.ClientConnectorError`, `asyncio.TimeoutError`) — no longer used as a catch-all wrapper.

### Markdown parser
- Frontmatter parsing now uses `pyyaml`'s `safe_load`. Lists, quoted strings, and nested mappings round-trip correctly. `tags: [a, b]` produces `["a", "b"]` (was the literal string `"[a, b]"`).

## Tool Improvements

### `update_page`
- Replace mode now uses `logseq.Editor.insertBatchBlock` instead of per-block `appendBlockInPage`. Nested block hierarchy from the markdown parser is preserved.

### `find_pages_by_property`
- Accepts namespaced property names like `logseq.order-list-type` (regex widened to allow `.`).
- Escapes both `\` and `"` in property values before DSL embedding.
- Rejects values longer than 256 characters with a guard clause.

### DB-mode tools
- `get_all_page_content` resolves UUIDs to page names via `get_page` before calling `getPageBlocksTree` (workaround for [logseq/logseq#4920](https://github.com/logseq/logseq/issues/4920)).
- `resolve_page_uuids` batches into a single Datascript query (was O(U) HTTP calls per UUID).
- `resolve_property_ident` now binds `?ident` (was incorrectly `?e`) and escapes input.

## Architecture

- `register_all_tools(mcp, client, config)` — the FastMCP server now constructs **one** `LogseqClient` at startup and injects it into every tool via `functools.partial`. Tools no longer call `load_config()` or instantiate `LogseqClient` themselves. Single `aiohttp.ClientSession` lifetime across the process.
- Every tool's public function now accepts `(client, config, …)` as its first two parameters. MCP-exposed schemas hide those two via partial binding.

## Bug Fixes

- `LogseqClient.create_page` passes `properties` as the second positional argument per the official `IEditorProxy.createPage(pageName, properties?, opts?)` signature (was packed inside `options`).
- `LogseqClient.append_block_in_page` forwards its `options` argument (was silently dropped).
- `_call` maps HTTP `401/404/4xx/5xx` to typed exceptions; only `ClientConnectorError` and `TimeoutError` are wrapped as `LogseqConnectionError`.
- `src/tools/__init__.py` no longer writes to `stdout` — tool-discovery `ImportError`s now log via `logger.warning`. Fixes MCP JSON-RPC stream corruption on stdio transport.

## Maintenance

- Dependency cleanup: replaced the unmaintained `load-dotenv` shim with `python-dotenv>=1.0`. Removed the abandoned `pathlib>=1.0.1` PyPI backport. Real `description` set on the project. `pyyaml>=6.0` added as a runtime dependency. `types-PyYAML` added to the dev group for stub coverage.
- Vector subsystem retracted: `src/vector/`, the `[vector]` dependency group, the `logseq-sync` console script, the 2 vector MCP tools, and all related CI matrix entries are gone. The v1.0.0 implementation shipped without an embedder and was non-functional; a redesigned vector subsystem may return in a future release.
- CI matrix simplified to plain Python 3.11/3.12/3.13.
- `mypy src/ --ignore-missing-imports`: zero errors across 38 source files.
- `bandit -r src/`: zero high-severity findings.
- Test coverage: 91% (gate: ≥85%).

## Upgrade Notes

This is labeled a patch release because v1.0.0 had only been in the wild for one day. There ARE breaking changes — see [`MIGRATION.md`](./MIGRATION.md) for the full table.

Headline items:

| Change | Migration |
|---|---|
| `get_page_links` tool removed | Use `get_page_backlinks` (same args, same output) |
| Vector tools removed | None — the feature was non-functional in v1.0.0 |
| `LogseqConfig.verify_ssl` default `False` → `True` | Pass `verify_ssl=False` explicitly or set `LOGSEQ_VERIFY_SSL=false` if you need to skip TLS verification |
| HTTP 404 → `LogseqNotFoundError` instead of `LogseqAPIError` | If you catch the broader class, no action needed |
| Other 4xx/5xx → `LogseqAPIError` instead of `LogseqConnectionError` | Switch `except LogseqConnectionError` to `except LogseqAPIError` if you relied on the old wrapping |
| `create_page` wire shape: `[title, properties or {}, opts]` | No code change if you use the Python wrapper — only the JSON sent to Logseq changes |
| `pathlib` and `load-dotenv` dropped, `pyyaml` added | `uv sync` / `pip install -e .` picks this up automatically |
| `logseq-sync` console script gone | Remove any cron jobs that invoked it |

The MCP tool surface is now exactly **21 standard tools** (was 22 in v1.0.0; one was the duplicated `get_page_links` alias and two were the vector tools).

## Contributors

- Claude (`claude-opus-4-7`) — implementation under the [`superpowers:brainstorming`](https://github.com/obra/superpowers/tree/main/skills/brainstorming) and [`superpowers:writing-plans`](https://github.com/obra/superpowers/tree/main/skills/writing-plans) methodology, subagent-driven execution.
- Gustavo Meilus — design review and approval.
