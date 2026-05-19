# Migration guide — v1.0.0 → v1.0.1

This release ships breaking changes despite the patch version label. The
rationale: v1.0.0 shipped with several incorrect API contracts that needed
fixing before they spread further. See the v1.0.1 design doc for details.

## Tool surface

| Removed | Replacement |
|---|---|
| `get_page_links` | `get_page_backlinks` (functionally identical; same args, same output) |
| `vector_search` | None — re-evaluated for a future release |
| `vector_db_status` | None |

If your MCP client referenced any of these by name, update the call sites.

## Configuration defaults

| Setting | v1.0.0 | v1.0.1 |
|---|---|---|
| `LogseqConfig.verify_ssl` (dataclass default) | `False` | `True` |

If you construct `LogseqConfig` directly with no `verify_ssl` argument and rely
on the previous default to skip TLS verification, pass `verify_ssl=False`
explicitly. The `LOGSEQ_VERIFY_SSL` env var continues to override.

## Exception semantics

| Status | v1.0.0 | v1.0.1 |
|---|---|---|
| HTTP 404 | `LogseqAPIError` (or `LogseqConnectionError`) | `LogseqNotFoundError` |
| Network failure (DNS/timeout/refused) | `LogseqConnectionError` | `LogseqConnectionError` (unchanged) |
| Other 4xx/5xx | `LogseqConnectionError` (wrong) | `LogseqAPIError` with `status_code` |

`LogseqConnectionError` is now reserved for genuine network failures. If you
catch it expecting any backend error, switch to `except LogseqAPIError`.

## Dependencies

- `pathlib>=1.0.1` removed (was an abandoned PyPI backport; `pathlib` is in
  the stdlib).
- `load-dotenv` replaced with `python-dotenv>=1.0.0`. Imports are
  source-compatible (`from dotenv import load_dotenv`).
- `pyyaml>=6.0` added for Markdown frontmatter parsing.
- `[dependency-groups].vector` removed entirely.

## CLI

`logseq-sync` no longer exists. The accompanying `[project.scripts]` entry was
removed. If you had a cron job, drop it.

## Internal helpers added (privacy)

- `LogseqClient.excluded_page_names(ttl_seconds=60.0) -> frozenset[str]` —
  cached lower-cased set of pages hidden by `LOGSEQ_EXCLUDE_TAGS`. Tools call
  this once per request instead of fetching `get_all_pages()` inline.
