# Choosing the right tool (operational guide)

The single source of truth for **which MCP tool to reach for** given a goal. This is
the *operational* axis; for *how to structure a graph well* (the domain axis) read
`best-practices.md`. Many read tools overlap — the sections below disambiguate them so
you don't fight the wrong tool.

## Read & retrieve

### The discovery → resolve pattern

Namespaces and irregular casing/whitespace make exact lookups fragile. **Never guess a
page name; resolve it first, then act.**

1. **Discover** the canonical name with `search` (token-based, tolerant) or
   `get_pages_from_namespace` (lists a hierarchy exactly).
2. **Copy the exact `originalName`** the graph returns.
3. **Act** with the precise tool (`get_page_blocks`, `fs_read_page`, …).

`search` is full-text by **tokens**, **case-insensitive**, *not* fuzzy: it tolerates
substrings, word order, and extra whitespace, but not typos. It is for *finding*, not
for *exact resolution*.

### `get_linked_references` vs `get_page_backlinks` (the common mix-up)

Both answer "what points at this page", but return very different things:

| Tool | Returns | Use when |
|------|---------|----------|
| `get_linked_references` | The **referencing blocks + their full subtree**, grouped by source page, newest-first. Supports `since_days`, `limit`, namespace children. | You want the **content** — e.g. "give me everything tagged `[[Area/Topic]]`". The programmatic *Linked References* panel. |
| `get_page_backlinks` | The **list of linking pages** (+ raw ref blocks, no subtree). | You only need **who links here**, not the nested content. |

Rule: need the *content* → `get_linked_references`. Need the *index of linkers* →
`get_page_backlinks`.

### Reading a topic that lives in journals

Capture is journals-first (see `best-practices.md` §1), so a topic's history is
scattered across dated entries. **Don't scan journals** — there is no "journals-only"
search filter, and walking them is slow and noisy. Instead:

```
get_linked_references(tag="Area/Topic")
```

It gathers every dated trace tagged to the topic automatically, newest-first — the read
side of the journals-first + collector-page pattern (`topic-tracking.md`).

### Read decision table

| Want to… | Tool |
|----------|------|
| Find a page whose exact name you're unsure of | `search` → then `get_pages_from_namespace` to confirm |
| List the children of a namespace | `get_pages_from_namespace` (flat) / `get_pages_tree_from_namespace` (tree) |
| Follow a topic scattered across journals | `get_linked_references(tag)` |
| Pull ALL content tagged with X (incl. subtrees) | `get_linked_references(tag, include_namespace_children=…)` |
| See only WHO links to a page | `get_page_backlinks` |
| Read a whole page / its block tree | `fs_read_page`, `get_page_blocks`, `get_block_content` |
| Filter pages by a `key:: value` property | `find_pages_by_property` |
| Run an advanced Datalog / simple query | `query` |

## Write & mutate

### API tools vs `fs_*` (filesystem)

| Path | Tools | Use when |
|------|-------|----------|
| API (HTTP) | `append_block_in_page`, `edit_block`, `insert_nested_block`, `rename_page`, `delete_page`, `delete_block` | Logseq is **actively editing** the page, or you need block-level structure (nesting, refs). Works in both file- and DB-mode. |
| Filesystem | `fs_append`, `fs_write_page`, `fs_read_page` | **File-mode only** (needs `LOGSEQ_GRAPH_PATH`). Fast, atomic, low-conflict. Best for large rewrites and journal edits. |

### Journals

Journals can't be reached by the API write tools via their `yyyy_mm_dd` filename (the
HTTP API addresses them by display title). For journal edits use **`fs_append`**
(appends without rewriting, creates the file if missing) or `fs_write_page` for a full
rewrite. Always `fs_read_page` immediately before a full rewrite.

### File-mode vs DB-mode caveat

`fs_*` tools are **file-mode only**; in DB-mode use the API write tools instead. Full
detail in `../../SKILL.md` ("File-mode vs DB-mode").

### Write decision table

| Want to… | Tool |
|----------|------|
| Capture on a journal / page (incremental) | `fs_append` |
| Full page rewrite | `fs_write_page` (read first with `fs_read_page`) |
| Add a block via the API | `append_block_in_page` |
| Nest sub-ideas under a block | `insert_nested_block` |
| Edit one block | `edit_block`, `update_block` |
| Set properties on a block | `set_block_properties` |
| Move a page into/out of a namespace | `rename_page` |
| Remove a page / block | `delete_page`, `delete_block` |

## Namespaces (quick reminder)

Always pass the page name with a **plain `/`** (e.g. `"Area/Topic"`) to every tool — the
server encodes it to the right on-disk form. References are **case-insensitive**
(`[[Area/Topic]]` == `[[area/topic]]`), but accents/spelling create distinct pages
(`Gestión` ≠ `Gestion`). Full detail in `best-practices.md` §6.
