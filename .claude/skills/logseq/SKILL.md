---
name: logseq
description: Work effectively with a Logseq knowledge graph through this MCP server — create high-quality Excalidraw diagrams, and follow Logseq conventions for pages, blocks, and references. Use when the user wants to draw/visualize something in Logseq, or asks how to structure pages, blocks, namespaces, or queries in their graph.
---

# Logseq

Guidance for producing good artifacts in a Logseq graph via this MCP server's tools.
This skill is organized by topic — read the relevant `references/<topic>/` file before
acting. Start lean; only pull in the topic you need.

## Tool map (this MCP server)

| Group | Tools | Use for |
|-------|-------|---------|
| Read | `get_all_pages`, `get_page_blocks`, `get_all_page_content`, `get_block_content`, `get_page_backlinks`, `get_linked_references`, `get_linked_flashcards`, `search`, `query`, `find_pages_by_property`, `get_pages_from_namespace`, `get_pages_tree_from_namespace` | Inspecting the graph |
| Write (API) | `create_page`, `append_block_in_page`, `insert_nested_block`, `edit_block`, `update_block`, `update_page`, `set_block_properties`, `rename_page`, `delete_page`, `delete_block` | Mutating via the Logseq HTTP API |
| Filesystem (`fs_*`) | `fs_read_page`, `fs_write_page`, `fs_append`, `fs_read_excalidraw`, `fs_write_excalidraw` | Direct, atomic disk writes to a file-mode graph |

This table is an **inventory**. To pick the right tool for a goal — and to tell apart
overlapping read tools (e.g. `get_linked_references` vs `get_page_backlinks`) — read
**`references/conventions/tool-selection.md`**.

**Journals & incremental capture:** journals can't be reached by the API write tools
(addressed by display title, not `yyyy_mm_dd`), so use `fs_append` for incremental
journal edits. Full read/write decision in `references/conventions/tool-selection.md`.

## File-mode vs DB-mode (important)

The `fs_*` tools write directly to disk and only work on **file-mode** graphs:

- They require `LOGSEQ_GRAPH_PATH` to point at the graph root (the folder with `pages/`, `journals/`, `draws/`).
- They are **not** available when `LOGSEQ_DB_MODE=true` (SQLite graphs). In DB-mode, `fs_write_excalidraw` returns a `❌` error — fall back to the API write tools, or tell the user this feature needs a file-mode graph.

If you are unsure which mode applies, check whether `fs_read_page` works before relying on the `fs_*` tools.

## Topics

### Choosing the right tool
Given a goal, which MCP tool to reach for — the discovery→resolve pattern, how
overlapping read tools differ (`get_linked_references` vs `get_page_backlinks`),
API vs `fs_*` for writes, and read/write decision tables — **read
`references/conventions/tool-selection.md`**.

### Excalidraw diagrams
To create or edit a diagram, **read `references/excalidraw/methodology.md` first** and follow its
full workflow (design → write via `fs_write_excalidraw` → render & validate → fix). It covers the
design methodology, the visual pattern library, the JSON element templates, the color palette, and
the mandatory render-view-fix loop.

### Logseq conventions & best practices
For how to structure a graph well — journals-first capture, outliner/block discipline,
pages vs tags vs links, references & embeds, `key:: value` properties, namespaces, and
tasks/queries — **read `references/conventions/best-practices.md`**. Each practice maps to
the MCP tool that applies. (File-mode / markdown; not the DB version.)

### Tracking a long-running topic in journals
When the user wants to *follow* a project/topic over many days (low-maintenance
trace + collector page, durable-only properties, self-contained journal entries),
**read `references/conventions/topic-tracking.md`** — a concrete application of the
conventions above.
