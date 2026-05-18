---
name: release
description: Prepare a logseq-api-mcp release — bump the version, generate changelog and release notes, tag, and publish a GitHub release.
---

# Preparing a Release

## Critical Invariants

- **NEVER** auto-increment the version — always ask the user
- **NEVER** push to a branch other than `main`
- **NEVER** create the GitHub release before the version bump PR is merged
- **ALL** file edits must be staged before committing
- **ALWAYS** verify the git tag exists locally before pushing it
- **ALWAYS** run quality checks before tagging

---

## Step 1 — Discover the last release

```bash
# Most recent tag (empty output = first release)
git tag --sort=-v:refname | head -5

# If tags exist, show last release info
git show $(git tag --sort=-v:refname | head -1) --stat
```

---

## Step 2 — Ask the user for the next version

Never auto-increment. Present the current version from `pyproject.toml` and ask:

> The current version is `X.Y.Z`. What should the next version be?  
> (Follow [Semantic Versioning](https://semver.org/): MAJOR for breaking changes, MINOR for new tools/features, PATCH for bug fixes.)

---

## Step 3 — Collect changes since the last release

```bash
# If a previous tag exists
git log <last-tag>..HEAD --oneline --no-merges

# If this is the first release (no tags)
git log --oneline --no-merges
```

Categorize commits by conventional prefix:

| Prefix | Category |
|---|---|
| `feat:` / `feat(...)` | New Features |
| `fix:` / `fix(...)` | Bug Fixes |
| `refactor:` | Refactoring |
| `chore:` | Maintenance |
| `docs:` | Documentation |
| `test:` | Testing |
| `perf:` | Performance |

Drop merge commits, revert pairs, and CI-only changes that have no user-visible effect.

---

## Step 4 — Update files

### 4a. Bump version in `pyproject.toml`

```toml
[project]
version = "<new-version>"
```

### 4b. Update `CHANGELOG.md`

Prepend a new entry at the top (keep the full history below):

```markdown
## [<new-version>] - <YYYY-MM-DD>

### New Features
- ...

### Bug Fixes
- ...

### Improvements
- ...

### Maintenance
- ...
```

Use today's date. Link each entry to its commit or PR where useful.

### 4c. Overwrite `RELEASE-NOTES.md`

This file always contains **only the latest release**. Use the format:

```markdown
# Release Notes — v<new-version>

**Released:** <YYYY-MM-DD>

## What's New

### New Tools
- ...

### Tool Improvements
- ...

### Other Changes
- ...

## Bug Fixes
- ...

## Maintenance
- ...

## Upgrade Notes

> Any breaking changes, new required env vars, or migration steps go here.
> If none, write: "No breaking changes."

## Contributors
- ...
```

---

## Step 5 — Run quality checks

```bash
uv run ruff check --fix && uv run ruff format
uv run pytest tests/ -x -q
```

Fix any failures before proceeding.

---

## Step 5b — Present summary and wait for user approval

Before committing anything, show the user a summary:

```
Ready to release v<new-version>

Files to be changed:
  • pyproject.toml  — version: <old> → <new>
  • CHANGELOG.md    — prepended v<new-version> entry
  • RELEASE-NOTES.md — overwritten with latest release notes

Commit message: "chore: release v<new-version>"
Tag: v<new-version>

Proceed? (yes / no / show diff)
```

**Wait for explicit confirmation before doing anything destructive.**  
If the user asks to see the diff, run `git diff` and show it.  
If the user says no or requests changes, apply the changes and re-present the summary.  
Only proceed to Step 6 when the user confirms.

---

## Step 6 — Commit all changes

```bash
git add pyproject.toml CHANGELOG.md RELEASE-NOTES.md
git commit -m "chore: release v<new-version>"
```

---

## Step 7 — Tag and push

```bash
git tag v<new-version>
git tag --list "v<new-version>"   # verify tag exists

git push -u origin main
git push origin v<new-version>
```

---

## Step 8 — Create the GitHub release

Use the GitHub MCP tool `mcp__github__create_or_update_file` is NOT what you want here — instead use the approach below with the available tools.

First load `mcp__github__list_releases` via ToolSearch to confirm the release doesn't already exist, then use `mcp__github__create_pull_request` concepts are wrong — the correct tool is reached via:

```
ToolSearch: "select:mcp__github__get_latest_release,mcp__github__list_releases"
```

Then create the release via the GitHub API. The release should:
- Target `main`
- Use tag `v<new-version>`
- Title: `v<new-version>`
- Body: contents of `RELEASE-NOTES.md`
- Set `draft: false`, `prerelease: false` (unless it's a pre-release)

> **Note:** In the remote Claude Code environment, use `mcp__github__*` tools (load via `ToolSearch`) rather than the `gh` CLI, which is not available.

---

## Terminal States

| State | Meaning |
|---|---|
| `DONE` | All 8 steps completed; GitHub release is live |
| `DONE_WITH_CONCERNS` | Release created but a non-critical step had issues (e.g. CI still running) |
| `BLOCKED` | A required step failed (quality checks, push rejected, etc.) — report the error and stop |
