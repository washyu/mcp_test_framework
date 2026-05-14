---
phase: 21-sdet-authoring-docs-readme-parity
plan: "03"
subsystem: docs
tags: [docs, claude-md, persona-note, dual-persona]
dependency_graph:
  requires:
    - "21-01: docs/SDET-AUTHORING.md exists as the link target"
  provides:
    - "CLAUDE.md routing signal: SDET-flavored questions route to docs/SDET-AUTHORING.md"
  affects:
    - "Plan 21-04 (verification sweep) — checks the appended paragraph exists and links correctly"
tech_stack:
  added: []
  patterns:
    - "Append-in-place pattern: no new H2, paragraph added to existing '## What This Project Is' section per D-03"
key_files:
  created: []
  modified:
    - CLAUDE.md
  deleted: []
decisions:
  - "Used the plan's exact prescribed paragraph verbatim (3 sentences, upper bound of D-03 budget). No rewording — the prescribed text already names all three required signals: persona name (SDET), public namespace (mcp_test_framework.sdet), and link target (docs/SDET-AUTHORING.md)."
metrics:
  duration: "~2min"
  completed: "2026-05-14"
  tasks_completed: 1
  files_modified: 1
  commits: 1
artifacts:
  - path: CLAUDE.md
    line_range: "19 (2-line insertion: blank line + new paragraph)"
    summary: "New paragraph appended between '## What This Project Is' content and '## Tooling' H2"
verification:
  acceptance_criteria_passed: "7/7"
  src_changes: 0
  contains_SDET: 1
  contains_SDET_AUTHORING_link: 1
  contains_namespace: 1
  no_new_h2: true
---

# Plan 21-03 — CLAUDE.md dual-persona note

## Summary

Appended the prescribed 3-sentence paragraph to CLAUDE.md's `## What This Project Is`
section, between the MVP-narrowness paragraph and the `## Tooling` H2. The note
names the SDET persona, the shared CLI surface (`--sdet` flag,
`mcp_test_framework.sdet` import surface, `tests/sdet/` discovery scope), and
links to `docs/SDET-AUTHORING.md` as the authoring walkthrough.

## What changed

- `CLAUDE.md`: 2-line insertion (blank line + new paragraph) at the boundary
  between the existing section and `## Tooling`. Zero other section touched.

## Commits

- `b450299` — docs(21-03): append dual-persona note to CLAUDE.md '## What This Project Is'

## Exact text appended (verbatim from the plan)

> v1.3 added the **SDET** persona as a second first-class user alongside the
> operator. The operator runs the contract pass (schema + description +
> output checks); the SDET authors stateful scenarios under `tests/sdet/`
> that exercise the MCP server end-to-end. Both personas share the same CLI
> surface — SDET adds the `--sdet` flag, the `mcp_test_framework.sdet`
> import surface (`mcp_session`, `tool()`, `ToolCallError`), and the
> `tests/sdet/` discovery scope. See
> [`docs/SDET-AUTHORING.md`](docs/SDET-AUTHORING.md) for the authoring
> walkthrough.

(3 sentences — at the D-03 upper bound, not over.)
