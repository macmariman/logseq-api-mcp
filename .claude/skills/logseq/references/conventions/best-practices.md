# Logseq Conventions & Best Practices (file-mode)

How to structure and write a Logseq graph well, and which MCP tool to reach for.
This covers **markdown / file-mode** graphs (the `fs_*` tools). It does **not** cover
the DB version — syntax like `key:: value` properties is file-mode markdown.

> When in doubt about the current graph, prefer the lowest-friction capture path
> (a block on today's journal) over inventing a new page or hierarchy up front.

## 1. Journals-first capture

The single most repeated community rule: **most information enters on the day's
journal first**. Don't decide where a note "belongs" before writing it — capture on
the journal, let structure emerge later through links and references.

- Tasks live on journals too, so they are date-stamped automatically.
- Structure should **emerge**, not be imposed up front. Resist building elaborate
  page hierarchies before you have content to justify them.

**Tools:** the journal is just a page named by date (e.g. `2026_05_31` →
`journals/2026_05_31.md`). For the *write mechanics* — why the API can't reach
journals, and `fs_append` vs `fs_write_page` — see `tool-selection.md`.

## 2. Everything is a block (outliner discipline)

The block (one bullet) is the smallest unit. Think and link at block granularity,
not page granularity.

- Use **indentation** to express parent→child relationships instead of spawning a
  new page for every sub-idea. A page with well-nested blocks beats five thin pages.
- Keep one idea per block so it can be referenced or embedded on its own.
- Collapsing/expanding manages density — write freely, collapse later.

**Tools:** `insert_nested_block` for parent/child structure; `edit_block` /
`update_block` to refine a single block; `get_page_blocks` to inspect the tree.

## 3. Pages vs. tags vs. links

`[[Double brackets]]` and `#tag` are **functionally identical** in Logseq — both
create/link a page. The choice is cosmetic.

- `#tag` cannot contain spaces. For multi-word concepts use `#[[Two Words]]` or
  `[[Two Words]]`.
- Treat a concept page as a **collector**: you link to `[[Topic]]` not to write
  there, but so its *Linked References* gather every mention for later synthesis.
- Default to **one graph**. Reserve separate graphs for genuinely distinct, large
  projects.

**Tools:** to gather every mention into the collector use `get_linked_references`
(content) or `get_page_backlinks` (just the linking pages) — they differ; see
`tool-selection.md`. Use `search` to find where a term appears.

## 4. References and embeds (don't repeat yourself)

- **Block reference** `((block-uuid))` — an inline link to one specific block. Write
  a fact once, reference it everywhere.
- **Block embed** `{{embed ((block-uuid))}}` — render that block (and its children)
  in place.
- **Page embed** `{{embed [[Page Name]]}}` — render a whole page in place.

Rule of thumb: **reference** a single item, **embed** a whole branch/page.

**Tools:** write embeds/refs as literal text via `fs_write_page` / `append_block_in_page`.
Resolve a block's content with `get_block_content`.

## 5. Properties — `key:: value` metadata

Properties attach structured metadata that queries can filter on.

```markdown
- tipo:: tema
  equipos:: [[Talent]], [[Producto]]
  tags:: trabajo
```

- **Page properties** go in the **first block** of the page.
- **Block properties** can sit on any block.
- Values are comma-separated; values wrapped in `[[ ]]` become page links.

**Durable facts only — never maintained state.** Any property you must remember to
update will rot, and a stale value is worse than none. Keep facts that never change
(`tipo:: tema`) or change only on a real event (`equipos:: [[…]]`). Avoid
`estado:: activo` — "active" is the invisible default; record a *terminal* state
once, when it actually happens (`estado:: cerrado`). Don't duplicate what the page
name already encodes (`area:: Kz` on a `Kz/…` page).

**Tools:** `set_block_properties` to write them; `find_pages_by_property` to query
(e.g. all pages where `tipo = tema`).

## 6. Namespaces — hierarchy with `/`

`[[Parent/Child]]` creates a hierarchical page. Good for `Project/Subproject`,
`Area/Topic`, `Person/Role`. Combine with properties for consistent, queryable
structure — but don't over-nest; flat + links is often enough.

**Always pass the page name with a plain `/`** to every tool — e.g.
`fs_read_page("Area/Topic")`, `fs_write_page("Area/Topic", …)`. The server reads the
graph's `:file/name-format` (from `logseq/config.edn`) and encodes the `/` to the
right on-disk form automatically:

- `:triple-lowbar` (Logseq's modern default) → `pages/Area___Topic.md`
- `:legacy` → `pages/Area%2FTopic.md`

Do **not** hand-encode the separator (don't pass `Area___Topic` or `Area%2FTopic`) —
let the server map it. When the format can't be detected (no `config.edn`), the
server assumes `:triple-lowbar`.

**Property unifies, namespace browses.** The namespace (`Kz/Topic`) is for
autocomplete and human navigation; a property (`tipo:: tema`) is what unifies items
*across* namespaces in a single query. Reach for the property when you need the
cross-cutting view, not a third parent page.

**References are case-insensitive** — `[[Kz/Topic]]` and `[[KZ/Topic]]` resolve to
the **same** page (Logseq just displays the first-seen casing). But **accents and
spelling do create distinct pages** (`Gestión` ≠ `Gestion`). Before creating one,
list the namespace (`get_pages_from_namespace`) or `search`, then reuse the exact
form the graph already uses — `[[Kz/Talent]]`, not a flat `[[Talent]]` — or you
create orphans that link to nothing.

**Tools:** `get_pages_from_namespace` and `get_pages_tree_from_namespace` to list a
namespace; `rename_page` to move a page into/out of one.

## 7. Tasks and queries

Pick **one** task workflow and stay consistent — don't mix:

- `TODO` / `DOING` / `DONE`, **or**
- `LATER` / `NOW` / `DONE`

Schedule with `SCHEDULED: <2026-05-31>` and `DEADLINE: <2026-05-31>` on the task
block. Build dynamic views with queries:

```markdown
{{query (and [[work]] (task TODO DOING))}}
```

**Tag the task block so queries catch it.** For
`{{query (and [[Topic]] (task TODO DOING))}}` to find a task, the topic must be in
scope: either the task block itself carries the tag, **or** it sits under a parent
block that already references the topic (the query inherits the parent's context).
A free-standing task on a journal needs the tag inline:
`TODO bajar feedback [[Kz/Gestión de Bench]]`.

**Tools:** create tasks as plain blocks (`append_block_in_page`); run advanced
Datalog/simple queries through the `query` tool.

## Which tool for which goal?

This file is the **domain** axis (how to structure a graph well). For the **operational**
axis — given a goal, which tool to reach for, and how overlapping read tools differ
(e.g. `get_linked_references` vs `get_page_backlinks`) — see **`tool-selection.md`**.
