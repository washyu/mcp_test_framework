---
phase: 10-v1-1-documentation
plan: 02
subsystem: docs
tags: [docs, extending, per-tool-config, cross-link, regression-test]
requires:
  - "Plan 10-01 (README anchors #per-tool-configuration and #block-b-judges-subset; tests/test_readme_snippets.py xfail gate)"
provides:
  - "docs/EXTENDING.md anchor #add-a-new-mcp-tool-target (consumed by README Further reading)"
  - "Config-only contributor seam documentation (DOC-07)"
affects:
  - docs/EXTENDING.md
tech-stack:
  added: []
  patterns:
    - "Insertion-only Edit-tool edits with verbatim old_string anchors (no whole-file rewrites)"
    - "Cross-document Markdown anchor links with relative paths (../README.md#anchor)"
    - "Reader-substitution callout (D-01b) immediately preceding placeholder-bearing YAML"
    - "Conditional pytest.xfail forward-compat gate flips to PASS once downstream content lands"
key-files:
  created: []
  modified:
    - docs/EXTENDING.md
decisions:
  - "Section placement: Add a new MCP tool target sits AFTER Swap the judge backend and BEFORE Further reading (D-04b -- lighter-weight extension follows code-extension seams, signalling a progression from heavy to light)"
  - "Skip-with-reason as the worked example (D-04c); judges-subset and call_arguments patterns are referenced via README cross-link rather than re-presented (avoids documentation drift across two files)"
  - "Placeholder name <your_destructive_tool> chosen to signal the safety value of skip + skip_reason (D-01); concrete names from any specific server are explicitly avoided"
  - "Closing prose names extra='forbid' typo-safety as the runtime guarantee (anchors example to model behavior); cites tool_config fixture by name rather than re-explaining its body"
metrics:
  duration: "~5 minutes"
  tasks_completed: 3
  files_created: 0
  files_modified: 1
  completed: 2026-05-08
---

# Phase 10 Plan 02: v1.1 EXTENDING.md documentation Summary

A new `## Add a new MCP tool target` section in `docs/EXTENDING.md` walks contributors through the config-only path to covering a new MCP tool, with cross-links into the README's per-tool config schema and Block B judges-subset pattern. The Further reading list gains back-links to the README and to `config.example.yaml`.

## Objective Recap

Wire the lighter-weight extension seam (per-tool YAML config, no code changes) into `docs/EXTENDING.md` as a peer of the existing rubric and judge-backend extension docs. The section must (a) cite `ToolConfig` as the schema source, (b) cross-link into the README for the field reference and judges-subset pattern, (c) walk the 4-step contributor workflow (`list-tools` -> decide -> add `tools.<name>:` block -> re-run `mcp-test-framework run`), and (d) anchor the worked example to the runtime via a `tool_config` fixture citation. Plan 10-01's Further-reading link from README into `docs/EXTENDING.md#add-a-new-mcp-tool-target` and its conditionally-gated regression test both flip to live state once Plan 10-02 ships.

Requirements addressed: DOC-07.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Insert `## Add a new MCP tool target` section into `docs/EXTENDING.md` (DOC-07) | `f301330` | docs/EXTENDING.md |
| 2 | Append v1.1 cross-links to `docs/EXTENDING.md` Further reading (CD-03) | `03ded0e` | docs/EXTENDING.md |
| 3 | Verify cross-document anchor integrity via `tests/test_readme_snippets.py` (CD-06) | (no commit -- verification-only) | (none modified) |

## Architecture / Pattern Notes

- **Insertion-only edits.** Both edits used the Edit tool with verbatim `old_string` anchors. The Task 1 anchor was the closing paragraph of `## Swap the judge backend` plus the trailing blank line and the `## Further reading` heading; the Task 2 anchor was the literal final bullet of the existing list. No untouched section text was reflowed.
- **Final section ordering.** `docs/EXTENDING.md` now has four `## ` top-level sections in this order: `Add a new description-quality rubric` -> `Swap the judge backend` -> `Add a new MCP tool target` -> `Further reading`. This matches the plan's success_criteria sequence exactly.
- **Cross-link convention.** The new section uses two patterns: human-readable phrase for in-doc anchors (`[Per-tool configuration](../README.md#per-tool-configuration)`, `[Block B in the README](../README.md#block-b-judges-subset)`) and backtick-fenced path for file targets (`[`config.example.yaml`](../config.example.yaml)`). The anchors resolve under GitHub's auto-slug rules (lowercase + hyphenate spaces).
- **Schema-source citation up front, runtime anchor at the close.** Opening prose cites `ToolConfig` (`src/mcp_test_framework/models.py`) as the schema source so the reader knows where the field reference is grounded. Closing prose cites the `tool_config` fixture (`src/mcp_test_framework/fixtures.py`) and the `extra="forbid"` typo-safety property, completing the load-time -> collection-time -> validation arc.
- **Worked example uses the safer pattern.** The skip-with-reason block (D-04c) is shown rather than `judges:` or `call_arguments:` because: (1) it's the most common real-world action a contributor takes when adding a new server (opt out destructive tools first), (2) it pairs naturally with `<your_destructive_tool>` as the placeholder name, (3) the more advanced patterns are one cross-link away in README Block B / Block C, eliminating documentation drift.
- **Reader-substitution callout (D-01b).** A single-line callout immediately before the YAML block tells the reader to substitute the placeholder. This matches the `<safe_read_tool_a>`/`<safe_read_tool_b>` pattern Plan 10-01 established in the README; the new section uses the analogous pattern for a destructive-tool example.
- **Forward-compat gate flipped automatically.** The `test_readme_anchor_targets_exist` test in `tests/test_readme_snippets.py` -- which Plan 10-01 wrote with a conditional `pytest.xfail` triggered only when `## Add a new MCP tool target` is absent from `docs/EXTENDING.md` -- flips to a real PASS the moment Task 1 commits. No changes to the test file were required.

## Verification Results

All three tasks' automated `<verify>` commands ran cleanly.

```
$ MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/test_readme_snippets.py -v
tests/test_readme_snippets.py::test_readme_yaml_snippets_parse PASSED       [ 33%]
tests/test_readme_snippets.py::test_readme_per_tool_fields_match_model PASSED [ 66%]
tests/test_readme_snippets.py::test_readme_anchor_targets_exist PASSED       [100%]
============================== 3 passed in 3.54s ==============================
```

The xfail from Wave 1 (`EXTENDING.md anchor pending Plan 10-02`) flipped to PASS, confirming the conditional gate logic in Plan 10-01 Task 4 was implemented correctly: the cross-document anchor `docs/EXTENDING.md#add-a-new-mcp-tool-target` now resolves to the heading inserted by Task 1.

Other verifications:
- Section ordering: `grep -n "^## " docs/EXTENDING.md` returns exactly four sections in the correct order (rubric, judge, tool target, Further reading).
- `## Add a new MCP tool target` appears exactly once.
- `../README.md#per-tool-configuration` appears in EXTENDING.md (D-04a back-link).
- `../README.md#block-b-judges-subset` appears in EXTENDING.md (D-04c judges-subset cross-ref).
- `<your_destructive_tool>` placeholder present (D-01).
- `mcp-test-framework list-tools` and `mcp-test-framework run` both present (Steps 1 and 4).
- `TOOLCFG-06` traceability tag present (Step 2 safe-defaults reference).
- `src/mcp_test_framework/models.py` and `src/mcp_test_framework/fixtures.py` both cited.
- The fenced ```yaml block in the new section parses via `yaml.safe_load`.
- README cross-references resolve: `## Per-tool configuration` and `### Block B: judges subset` both exist as headings in README.md.
- Further reading has 5 entries (3 original + 2 new); the 2 new entries appear after the original 3.
- Cross-doc anchor regex check: every `docs/EXTENDING.md#<anchor>` link in README.md slugifies to a real heading in `docs/EXTENDING.md` (the only such link, `add-a-new-mcp-tool-target`, resolves).
- Collection-only sanity: `MCPTF_CONFIG_FILE=config.yaml uv run pytest --co -q` collects 691/706 tests (same as Wave 1 -- no regressions).

## Deviations from Plan

None at the action level -- all three tasks executed exactly as written. Task 3 produced no commit because the plan explicitly stated the test file should not need modification under correct Plan 10-01 Task 4 implementation, and indeed it did not.

## Authentication Gates

None.

## Known Stubs

None. The xfail gate from Plan 10-01 has now flipped to a real PASS; no documented placeholders, TODOs, or pending content remain in the v1.1 documentation surface.

## Threat Flags

None. Documentation-only changes; no new network endpoints, auth paths, file-access patterns, or trust boundaries.

## Self-Check: PASSED

- docs/EXTENDING.md modified: FOUND (commits f301330, 03ded0e)
- New `## Add a new MCP tool target` heading at line 117 of docs/EXTENDING.md: FOUND (`grep -n "^## " docs/EXTENDING.md`)
- Both Task 1 and Task 2 commits exist on branch: FOUND (`git log --oneline` shows 03ded0e, f301330)
- `MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/test_readme_snippets.py -v` exits 0 with 3 passed: PASSED
- README -> EXTENDING.md cross-doc anchor resolves: PASSED (regex slugify check)
