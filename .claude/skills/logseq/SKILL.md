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
| Read | `get_all_pages`, `get_page_blocks`, `get_block_content`, `get_page_backlinks`, `get_linked_references`, `search`, `query`, `find_pages_by_property`, `get_pages_from_namespace` | Inspecting the graph |
| Write (API) | `append_block_in_page`, `edit_block`, `insert_nested_block`, `rename_page`, `delete_page`, `delete_block` | Mutating via the Logseq HTTP API |
| Filesystem (`fs_*`) | `fs_read_page`, `fs_write_page`, `fs_append`, `fs_read_excalidraw`, `fs_write_excalidraw` | Direct, atomic disk writes to a file-mode graph |

**Journals & incremental capture:** prefer `fs_append` for adding blocks to a page
or journal — it appends without rewriting the file (low conflict) and creates the
file if missing. Journals can't be reached by the API write tools via their
`yyyy_mm_dd` filename (the HTTP API addresses them by display title), so use
`fs_append` (or `fs_write_page` for a full rewrite) for journal edits. Always
`fs_read_page` immediately before a full rewrite and overwrite the complete content.

## File-mode vs DB-mode (important)

The `fs_*` tools write directly to disk and only work on **file-mode** graphs:

- They require `LOGSEQ_GRAPH_PATH` to point at the graph root (the folder with `pages/`, `journals/`, `draws/`).
- They are **not** available when `LOGSEQ_DB_MODE=true` (SQLite graphs). In DB-mode, `fs_write_excalidraw` returns a `❌` error — fall back to the API write tools, or tell the user this feature needs a file-mode graph.

If you are unsure which mode applies, check whether `fs_read_page` works before relying on the `fs_*` tools.

## Topics

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
