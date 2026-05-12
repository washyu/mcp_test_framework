---
phase: 16-reporter-ux-overhaul
plan: 03
subsystem: docs
tags:
  - docs
  - reporter
  - ux
  - readme
  - spec-audit
requires:
  - Plan 16-01 (locked digest shape: D-01, D-12, D-04)
  - Plan 16-02 (--explain flag + composition rules: D-05, D-06, D-08, D-09)
  - Phase 13 (locked skip-reason constants: D-12)
provides:
  - README documentation for Phase 16's pre-run digest + --explain + -q
  - Flag composition matrix (--explain × --raw × -q × --debug × --with-framework)
  - Updated 'Sample green run' snippet matching the Phase 16 output shape
  - Spec-audit finding: docs/mcp_test_framework_mvp_spec.md is intentionally silent on the operator CLI output shape and requires zero diff
affects:
  - README.md
tech-stack:
  added: []
  patterns:
    - Markdown table for flag composition rules
    - Fenced code block for canonical digest example
    - Em-dash literal (U+2014) inside example FAIL row reasoning
key-files:
  created: []
  modified:
    - README.md
decisions:
  - "Task 2 zero-diff: spec is the MVP design contract, intentionally silent on the operator CLI output shape and flag matrix; per plan Step 7 'do NOT manufacture changes to satisfy the task'"
  - "Documented --explain as wrapper-owned with composition rules under --raw / -q / --debug / --with-framework in a single Markdown table"
  - "Replaced 'Sample green run' pytest-default output (pre-Phase-14 era) with the Phase 16 digest + per-tool rows + Result: shape; documented Result: count math (56 tools × 10 cases = 560 skipped)"
metrics:
  duration_minutes: 6
  completed_date: 2026-05-12
---

# Phase 16 Plan 03: Documentation refresh Summary

Refreshed `README.md` to reflect Phase 16's pre-run digest + `--explain` + `-q`
semantics. Audited `docs/mcp_test_framework_mvp_spec.md` and confirmed
intentional zero-diff — the MVP spec is the design contract, not the operator
CLI output reference, and contains no Phase-16-relevant content (no
"post-run header" references, no obsolete pytest collection framing, no
operator flag-matrix documentation that needs `--explain` added).

## What Changed

### `README.md` (modified — single file in this plan)

**Sections touched (Markdown heading path):**

- `## Commands` → `### Run the test suite` → **new** `#### Run output shape` (added).
  - One paragraph describing the pre-run digest / post-run split.
  - Canonical small-N example block (homelab-mcp 2-of-58 selection, Phase 16 D-01 shape verbatim).
  - 5-row Markdown table documenting `--explain`, `-q`/`--quiet`, `--raw`, `--debug`, `--with-framework` composition rules.
  - **new** `##### `--explain` example` subsection with the inline `Skipping (N):` expansion block + skip-reason defaulting prose (Phase 13 D-12 constants surfaced).
- `## Sample green run` (rewritten in place — body only; heading preserved).
  - Old: pytest-default `============================= test session starts...` output (pre-Phase-14 era).
  - New: Phase 16 digest + two `✓ PASS` rows + `Result: 20 passed, 0 failed, 560 skipped` line.
  - Surrounding prose updated to explain digest-then-rows ordering, the parametrized-case `Result:` math (56 tools × 10 cases = 560 skipped), and the `✗ FAIL — <reasoning>` em-dash convention.

**Diff scale:** +107 lines / -29 lines in one commit (`a56cef9`). All edits localized to two existing sections; no other README sections touched. All level-2 headings preserved (`## Testing an MCP server you didn't write`, `## Prerequisites`, `## Setup`, `## Commands`, `## Configuration`, `## Per-tool configuration`, `## Sample green run`, `## Isolation guarantee`, `## CI integration`, `## Troubleshooting (Windows)`, `## Further reading` — all intact).

### `docs/mcp_test_framework_mvp_spec.md` (intentionally unchanged)

Read the full spec (302 lines). Specific findings from the search-and-update audit (plan Task 2 Step 4):

- **`grep -i "n collected, m deselected"` returns 0.** The spec does not hold up pytest's collection framing as the operator surface.
- **`grep -i "header"` returns 0.** No "post-run header" terminology to update.
- **`grep -i "explain"` returns 0.** Pre-existing mentions absent; no consistency issues with D-05/D-08/D-09.
- **`grep -i "post-run|pre-run|digest|reporter|domain UI"` returns 0.** Spec is silent on the renderer's structural decisions.
- **Output-shape framing** (the relevant Phase-16 surface) is captured by two MVP-era statements:
  - Line 13: "CLI entry point suitable for CI/CD pipelines (exits non-zero on test failure, prints pytest default output)" — historical MVP target, not a v1.2 contract.
  - Line 278 (Acceptance Criteria §4): "The full run produces standard pytest terminal output, exits 0 on success and non-zero on any failure." — MVP acceptance bar; unchanged because the spec is the MVP-era design truth, not the v1.2 operator-surface contract.
- **CLI flag matrix** (the conditional trigger for adding `--explain` to the spec): line 235 documents only `mcp-test-framework run [--config PATH] [-k EXPRESSION] [-v]` — a minimal MVP stub that does **not** list `-q`, `--raw`, `--debug`, `--with-framework`, or `--junit-xml`. None of the v1.1/v1.2 flags appear. Therefore the plan's conditional ("if the spec documents the flag matrix, --explain is present alongside them") **does not trigger**, and the spec is internally consistent without `--explain`.
- **`--with-framework` appears once** at line 50, but only in prose describing the Phase 15 contract/framework split ("the runner collects `tests/contract/` by default and adds `tests/framework/` only when invoked with `--with-framework`") — that is a Phase-15 testbed-shape sentence, not a flag-matrix listing.

**Verdict:** Zero diff is the correct outcome per plan Task 2 Step 7 ("If after thorough reading no Phase-16-relevant content exists... record this finding in the SUMMARY and make ZERO changes to the file. ... Do NOT manufacture changes to satisfy the task — the spec's purpose is design truth, not CLI output documentation"). The spec's MVP-era output-shape statements are historical record, not v1.2 contract; updating them would be drift, not alignment. No code or docs in v1.2 references the spec for output-shape truth — that role is held by the README and the `--help` text emitted by `cli.py`.

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1    | a56cef9 | docs(16-03): refresh README run-output section for Phase 16 pre-run digest |
| 2    | (none) | Zero diff — `docs/mcp_test_framework_mvp_spec.md` intentionally unchanged per audit (see "Decisions" + "Plan-task narrative" below) |

## Verification

- `uv run python -c "..."` automated check from plan Task 1: PASS (regex assertions on `--explain`, pre-run digest example, `use --explain to list`, and `-q` documentation all match).
- Acceptance criteria counts for Task 1 (all met):
  - `grep -c -- "--explain" README.md` → **12** (≥ 2 ✓)
  - `grep -c "use --explain to list" README.md` → **5** (≥ 1 ✓)
  - `grep -c "MCP Test Framework" README.md` → **3** (≥ 1 ✓)
  - `grep -i -c "post-run header" README.md` → **0** ✓
  - `grep -i -c "Result:" README.md` → **7** (≥ 1 ✓)
- Acceptance criteria for Task 2 (all met):
  - File exists, non-empty ✓
  - `grep -i -c "n collected, m deselected" docs/mcp_test_framework_mvp_spec.md` → **0** ✓
  - Conditional `--explain` requirement does not trigger (spec does not document the flag matrix) ✓
  - `git diff docs/mcp_test_framework_mvp_spec.md` is empty ✓
  - Sections on Python 3.14, `uv`, MCP stdio, Ollama judge, opt-in tool selection, contract/framework split: all PRESERVED unchanged ✓
- Regression smoke: `MCPTF_CONFIG_FILE=config-v2-worktree.yaml uv run pytest tests/framework/test_runner_verbosity.py tests/framework/unit/test_runner_pre_run_digest.py tests/framework/unit/test_runner_explain.py tests/framework/test_readme_snippets.py -q` → **40 passed**. No code regression from documentation edits.

## Deviations from Plan

None. Both tasks executed exactly as written. Task 1 made the prescribed edits at the prescribed sections with the canonical example block from the plan's `<action>` Step 2 (adapted slightly to use the operator-realistic homelab-mcp tools `list_keyring_credentials` and `suggest_deployments` per the PROJECT.md "Default target tools" line, in place of the plan's placeholder `list_registered_servers` and `query_inventory` — both equivalent for documentation purposes; the data shape is identical). Task 2 took the plan's explicit "zero diff is acceptable" branch (Step 7) with the SUMMARY justification.

## Out-of-Scope / Deferred (per plan §objective)

- **REQUIREMENTS.md UX-01 wording amendment (D-04 `Defaulting:` divergence)** — explicitly deferred by CONTEXT.md §deferred line 204 to a post-Phase-16 quick-task. Not addressed in this plan.
- **D-11 (`--debug` per-judge breakdown block)** — deferred to v1.3 per CONTEXT.md "Claude's Discretion" section (line 195). The XML-extraction pathway is not exercised in this phase. Captured here so the v1.2 close-out audit does not re-surface it as a gap.

## Threat Flags

None. This plan is documentation prose only — no code paths, no new inputs, no new persisted state, no new network or filesystem surface. Per plan §threat_model: "STRIDE applicability: NONE."

## Self-Check: PASSED

**Files exist:**

- README.md — FOUND (modified, +107/-29 lines per commit a56cef9)
- docs/mcp_test_framework_mvp_spec.md — FOUND (302 lines, unchanged)
- .planning/phases/16-reporter-ux-overhaul/16-03-documentation-refresh-SUMMARY.md — FOUND (this file)

**Commits exist:**

- a56cef9 — FOUND on `main` (Task 1 commit; `git log --oneline | grep a56cef9` shows present)
