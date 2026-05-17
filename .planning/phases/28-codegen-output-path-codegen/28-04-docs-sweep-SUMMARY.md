---
phase: 28-codegen-output-path-codegen
plan: 04
subsystem: docs
tags: [docs-sweep, requirements, roadmap, codegen-lib-01, codegen-lib-02]
requires: [28-01, 28-02, 28-03]
provides: [planning-artifacts-aligned-with-implementation]
affects: [.planning/REQUIREMENTS.md, .planning/ROADMAP.md]
tech_added: []
patterns: [docs-sync-after-scope-pivot]
key_files:
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
  created:
    - .planning/phases/28-codegen-output-path-codegen/28-04-docs-sweep-SUMMARY.md
decisions:
  - "Preserved the existing `[x]` status markers on CODEGEN-LIB-01/CODEGEN-LIB-02 in REQUIREMENTS.md and on the four 28-NN plans in ROADMAP.md. Plan body's verbatim Edit blocks predated the in-flight execution of 28-01..03; reverting the markers to `[ ]` would have erased real completion state. Rule 1 deviation."
  - "ROADMAP.md Progress-table row left at `3/4 | In Progress` (not flipped to `0/4 | In progress` as plan body instructed). Same reasoning: plan's instruction predated execution; downstream `roadmap.update-plan-progress 28` bumps the row to `4/4 | Complete` after this commit lands. Rule 1 deviation."
  - "Plans-block inside Phase 28 Details left unchanged (existing block already contains the four real plan filenames with correct `[x]`/`[ ]` markers); plan body's Edit 2 would have stomped those markers. Edit 2 narrowed to Goal+SC1+SC2+SC3 only. Rule 1 deviation."
metrics:
  duration: 4min
  completed: 2026-05-17
  task_count: 2
  file_count: 2
---

# Phase 28 Plan 04: Docs Sweep Summary

Aligned REQUIREMENTS.md CODEGEN-LIB-01 and ROADMAP.md Phase 28 Goal/SCs with the actual scope locked in 28-CONTEXT.md (fail-loud, pyproject-ini route, pre-handshake guard, non-TTY abort) — the prior text described the rejected smart-default + `--output-dir` design.

## What Shipped

- **REQUIREMENTS.md line 47 (CODEGEN-LIB-01)** — Single-line rewrite covering four locked sub-behaviors: (a) fail-loud operator-tone error naming the missing field + `mcp-contracts config-init` pointer; (b) no `--output-dir` flag (config is sole source of truth); (c) non-empty target prompts before overwrite + non-TTY abort with exit code 2 (no `--yes`/`--force`); (d) `[tool.pytest.ini_options] mcp_config_file` pyproject-ini route as same config-resolution path pytest uses, with full precedence ladder.
- **REQUIREMENTS.md line 48 (CODEGEN-LIB-02)** — Untouched. Strict-guard + fail-fast-at-command-start interpretation locked verbatim.
- **ROADMAP.md line 82 (v1.4 task-list brief)** — Replaced stale "`tests/_generated/` default that refuses to write into `site-packages/`" framing with "refuses to invent an output path or write under its own install tree, prompts before overwriting non-empty targets, and reads the same `mcp_config_file` ini route pytest uses".
- **ROADMAP.md Phase 28 Details (lines 140-146)** — Goal rewritten (drops sensible-default-path framing; new framing names the pyproject-ini route + project-layout-ignorant posture); SC1 rewritten around fail-loud + TTY/non-TTY paths + no-bypass-flag clause; SC2 refined to specify pre-handshake timing + names field + resolved path + framework install root + no-bypass clause; SC3 added covering pyproject-ini-route parity with pytest + full precedence ladder.
- **ROADMAP.md Progress-table row** — Left at `3/4 | In Progress` (downstream `roadmap.update-plan-progress 28` flips to `4/4 | Complete` after this plan's final commit lands).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Amend REQUIREMENTS.md CODEGEN-LIB-01 + leave CODEGEN-LIB-02 verbatim | 42994cf | .planning/REQUIREMENTS.md |
| 2 | Amend ROADMAP.md Phase 28 Goal + Success Criteria (SC1 rewritten, SC2 refined, SC3 added) | b6c75e8 | .planning/ROADMAP.md |

## Verification

All plan-level grep checks pass:

| Check | Result |
|-------|--------|
| `grep -n "tests/_generated/<server_slug>" .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns NO matches | PASS (empty output) |
| `grep -n -- "--output-dir" .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns only the negation clause in CODEGEN-LIB-01 ("No `--output-dir` flag") | PASS (single match; new text is explicit negation, not stale flag spec) |
| `grep -n "fail-loud operator-tone error naming the missing field"` returns matches in BOTH files | PASS (REQUIREMENTS.md:47 + ROADMAP.md:145) |
| `grep -n "BEFORE the MCP handshake" .planning/ROADMAP.md` returns a match | PASS (line 146) |
| `grep -c "mcp_config_file" .planning/ROADMAP.md` ≥ 2 (SC3 + Goal mention) | PASS (15 occurrences) |
| CODEGEN-LIB-02 in REQUIREMENTS.md byte-identical to pre-edit state | PASS (line 48 untouched; grep confirms text intact) |

Per-task acceptance criteria all met:

- Task 1: CODEGEN-LIB-01 contains the four required literal strings; stale "tests/_generated/<server_slug>/" and "by default — no config required" strings removed; CODEGEN-LIB-02 line is byte-identical to pre-edit state.
- Task 2: Phase 28 Goal contains "refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses"; SC1 contains "fail-loud operator-tone error naming the missing field" and "no `--yes` / `--force` flag exists"; SC2 contains "BEFORE the MCP handshake" and "No bypass flag or config knob exists"; SC3 contains "`[tool.pytest.ini_options] mcp_config_file`"; stale "tests/_generated/" and "--output-dir" strings removed from ROADMAP.md (the only "--output-dir" hit is the negation clause inside REQUIREMENTS.md CODEGEN-LIB-01).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Stale plan instruction would regress real state] Preserved existing `[x]` status markers on completed REQUIREMENTS.md items and ROADMAP.md plan-list entries**
- **Found during:** Task 1 setup and Task 2 setup.
- **Issue:** The plan body's verbatim Edit blocks for REQUIREMENTS.md CODEGEN-LIB-01/02 used `[ ]` markers (consistent with the plan being written before any 28-NN plan had executed). REQUIREMENTS.md actually contained `[x]` for both rows. Mechanically applying the Edit would have flipped two complete items back to incomplete.
- **Fix:** Edits used `[x]` to preserve the real status. The plan's tail-end note ("leave the status as `Pending` — the verification phase will flip these to `Complete`") was authored under the assumption REQUIREMENTS.md still read `[ ]` / `Pending`; the actual file state had already advanced past that.
- **Files modified:** .planning/REQUIREMENTS.md (line 47 only)
- **Commit:** 42994cf

**2. [Rule 1 - Stale plan instruction would regress real state] ROADMAP.md Phase 28 Plans-block left untouched; Edit 2 narrowed to Goal/SC1/SC2/SC3 lines only**
- **Found during:** Task 2.
- **Issue:** The plan body's Edit 2 instructed a wholesale replacement of lines 139-147 (the entire Phase 28 Details block). At plan-authoring time those lines ended with `**Plans**: TBD`. The actual file state had `**Plans**: 4 plans` followed by four real plan-filename rows with `[x]/[x]/[x]/[ ]` markers reflecting actual completion of 28-01/02/03 and pending 28-04. Mechanical replacement would have stomped both the filenames and the completion markers.
- **Fix:** Edit 2 scoped to a partial-block replacement covering only the Goal + SC1 + SC2 lines (with SC3 added as a new line). Plans-block left intact.
- **Files modified:** .planning/ROADMAP.md (Goal line + SC1 + SC2 + new SC3 line)
- **Commit:** b6c75e8

**3. [Rule 1 - Stale plan instruction would regress real state] ROADMAP.md Progress-table row left at `3/4 | In Progress` instead of plan's `0/4 | In progress`**
- **Found during:** Task 2.
- **Issue:** Plan's Edit 3 instructed replacing the Progress-table row with `| 28. Codegen output path (CODEGEN) | v1.4 | 0/4 | In progress | - |`. Current row already reads `| 28. Codegen output path (CODEGEN) | v1.4 | 3/4 | In Progress|  |` — three of four plans completed in real execution. Mechanical replacement would erase three completed plans' worth of state.
- **Fix:** Progress-table row left at `3/4 | In Progress`. The downstream `gsd-sdk query roadmap.update-plan-progress 28` invocation (run after this plan's final metadata commit) bumps the row to `4/4 | Complete` after Plan 28-04 itself ships, which is the correct final state.
- **Files modified:** .planning/ROADMAP.md (row 212 unchanged)
- **Commit:** n/a (intentional no-op)

No Rule 2 (missing critical functionality), Rule 3 (blocking issue), or Rule 4 (architectural decision) deviations.

## Traceability Table Status

Per the plan's `<action>` block on Task 1: the REQUIREMENTS.md Traceability table CODEGEN-LIB-01 + CODEGEN-LIB-02 status is intentionally NOT flipped from `Pending` → `Complete` in this Wave 4 sweep. Spot-check of REQUIREMENTS.md line 126 confirms CODEGEN-LIB-02 is already `Complete` (set during 28-01 close); CODEGEN-LIB-01 row status flip is deferred to phase verification per the plan's explicit instruction.

## Authentication Gates

None.

## Known Stubs

None — this plan modifies docs only; no code or data wiring.

## Self-Check: PASSED

- File `.planning/REQUIREMENTS.md` updated: FOUND (line 47 contains the new text; CODEGEN-LIB-02 line 48 byte-identical to pre-edit state)
- File `.planning/ROADMAP.md` updated: FOUND (line 82 brief + lines 140-147 Phase Details block both contain the new text)
- File `.planning/phases/28-codegen-output-path-codegen/28-04-docs-sweep-SUMMARY.md` created: FOUND (this file)
- Commit `42994cf` exists: FOUND (`git log --oneline -5` shows it second-most-recent)
- Commit `b6c75e8` exists: FOUND (`git log --oneline -5` shows it most-recent)
