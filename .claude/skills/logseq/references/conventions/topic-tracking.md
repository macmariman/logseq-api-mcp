# Topic tracking in journals (file-mode)

How to track a long-running topic (a *tema*) with near-zero maintenance. This is a
concrete application of `best-practices.md` — capture stays on journals; the topic
page is just a collector. Read this when the user wants to *follow* a project/topic
over many days, not for one-off notes.

## 1. The pattern: journal traces + a stub collector page

Capture every update as a block on the day's journal, tagged to the topic
(`[[Area/Topic]]`). Structure emerges from the tag, not from up-front pages.

- The **topic page is a collector** (see best-practices §3): you rarely write on it.
  Its *Linked References* gather the dated trace automatically, newest-first — so
  "recency" is free and self-maintaining.
- A topic page needs at most: a few set-and-forget properties (best-practices §5 —
  durable only, never maintained state), an optional `## Estado` block you overwrite
  in place, and a task query.
- Liveness = recency of journal traces, not an `estado::` flag. Record only the
  *terminal* state once (`estado:: cerrado`, or move the page into an
  `Area/Archivo/` namespace).
- Split `tipo:: tema` (resolves and eventually closes) from `tipo:: marco`
  (a living reference that never closes, e.g. a career-path or pricing model).
  Tagging a `marco` as a `tema` pollutes the active-temas dashboard.

**Live-topics dashboard** (a block on the topic page, or a dedicated query page):

```markdown
{{query (property tipo "tema")}}
```

## 2. Teams and topics coexist on a trace

A **team** (`Kz/Politica Salarial`) is a standing group/meeting; a **topic**
(`Kz/CareerPath`) is the thing you track. A team meeting often touches a topic that
involves other teams, so **team tags and topic tags routinely share the same journal
block** — tag both and the trace surfaces in *both* collectors.

**Tags live on the parent block; context and source go in the first child bullet.**
This matters: *Linked References* gather the matching block **plus its subtree of
children, not its siblings**. So the tagged block must be the *parent* of the
content — otherwise the topic page collects an empty header and loses the bullets.
Keep the parent clean (tags only) and put date + source on the first bullet:

```markdown
- [[Kz/Politica Salarial]] - [[Kz/CareerPath]]
	- 01/06 sync · [Krisp](https://…)
	- 3 comparaciones de perfiles con las 5 dimensiones de derrame; idea de pasarla a Reflect.
	- Soft skills = amplificador, no dimensión suelta (comunicación, negociación, visibilidad).
	- Próximo: enriquecer la presentación y probarla con perfiles tipo Franco.
```

One meeting can yield several traces in a day — one per team×topic combination —
each with its own tagged parent and bullets.

**Summarising on request:** the user usually names the **team and topic** for the
parent header and the **source to read** (Krisp, Notion, Logseq, Readwise, Drive,
…). Use exactly those as the parent tags and pull the content from the named source.

## 3. Make journal entries self-contained

Future-you should not have to open the topic page to find a link. Put the source
link **on the first bullet of the trace** (the parent block carries only the tags,
per §2). Per source: a context/title line with the link, then 3–4 short bullets —
not a paragraph. Scannable beats complete; rewrite verbose captures down rather than
letting them accrete.

**Date tagging** — the journal already provides today's date, so don't repeat it.
The date, when needed, goes on the event bullet (not the tag parent):

- **Today:** no date prefix. Just the context line and links.
- **Past or future:** prefix the event bullet with Logseq's date tag
  (`[[May 27th, 2026]]`) so the reference is clickable and queryable — not a plain
  `27/05`.

```markdown
- [[Kz/Gestión de Bench]]
	- reunión X · [Krisp](https://…) · [Notion](https://…)
		- Acordamos criterio de evaluación con 4 dimensiones.
		- Números: bench asignable ~$53k/mes, impacto may–dic ~$225k.
		- Próximo: validar umbrales con Alfredo.
	- [[May 27th, 2026]] — reunión Y · [Krisp](https://…)
		- Primera reunión sobre el tema; se plantea la propuesta.
		- Decide Talent + Alfredo con aval de Bruno.
```

**Tasks** go as children of the tagged parent block (they inherit its topic context
for queries — see best-practices §7). A free-standing task needs the tag inline.

**Tools:** `fs_append` to add a trace to today's journal; `get_linked_references`
to read a topic's accumulated trace; `find_pages_by_property` for the dashboard.
