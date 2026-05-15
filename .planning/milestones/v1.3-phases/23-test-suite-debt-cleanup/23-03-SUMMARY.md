---
phase: 23-test-suite-debt-cleanup
plan: 03
subsystem: docs
tags: [doc-scrub, banned-tokens, operator-invocation, cluster-c]
provides:
  - "README.md operator-facing invocations all paired with --config"
  - "README.md zero banned-token regex hits"
requires:
  - "tests/framework/unit/test_doc_scrub.py (close-gate contract; read-only)"
affects:
  - "README.md (only file modified)"
tech-stack:
  added: []
  patterns:
    - "Phase 12 D-08 --config pairing rule (D-05)"
    - "Phase 12 D-10 semantic-rewrite-not-regex-strip (D-06)"
key-files:
  created: []
  modified:
    - "README.md"
decisions:
  - "D-05 fix shape applied verbatim from PATTERNS §README.md: line 104 paired with --config config.yaml"
  - "D-06 single banned-token comment rewritten to cite docs/SDET-AUTHORING.md (the surviving anchor closest to the operator-meaningful intent of the maintainer reminder)"
metrics:
  duration: "~6 min"
  completed: "2026-05-15"
  tasks_total: 4
  tasks_committed: 2
  tasks_diagnostic_only: 2
  files_modified: 1
  commits: 2
---

# Phase 23 Plan 03: Cluster C — README D-05 + D-06 Fixes Summary

Cleared the two README defects flagged by `tests/framework/unit/test_doc_scrub.py` so the close-gate plan (Plan 04) sees green: the bare `--explain` invocation now pairs with `--config config.yaml`, and the maintainer comment referencing planning-system anchors was semantically rewritten to cite a surviving doc anchor.

## Task Inventory and Fixes

### Task 1 — Enumerate D-05 unpaired-invocation hits (diagnostic, no commit)

**Verification command:**
```
uv run pytest tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config -v
```

**Hits found in README.md:**

| Line | Bare invocation                                |
| ---- | ---------------------------------------------- |
| 104  | `$ mcp-test-framework run --explain`           |

Single hit, exactly matching the prediction in CONTEXT.md / PATTERNS.md. The `EXTENDING.md` parametrization (`path1`) was already green.

### Task 2 — Enumerate D-06 banned-token hits (diagnostic, no commit)

**Verification command:**
```
uv run pytest tests/framework/unit/test_doc_scrub.py::test_readme_exists_and_no_banned_tokens -v
```

**Regexes that matched (from assertion message):** `\bPhase \d`, `\bD-\d{2}`.

**Per-regex grep against `README.md`:**

| Regex                       | Line | Surrounding text                                                                                                  |
| --------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------- |
| `\bPhase \d`                | 274  | `<!-- mirrors _runner.py output — re-run the framework when output format changes (Phase 21 D-14) -->`            |
| `\bD-\d{2}`                 | 274  | (same line — both tokens in one HTML maintainer comment)                                                          |
| `\bPlan \d-\d`              | —    | no matches                                                                                                        |
| `\bTOOLCFG-\d`, `\bISOL-\d`, `\bOUTPUT-\d`, `\b\d{6}-[a-z0-9]{3}` | — | no matches                                                                       |
| `src/[\w/.]+\.py:\d+`       | —    | no matches                                                                                                        |

Both banned tokens (`Phase 21` and `D-14`) sit inside one HTML comment annotating the SDET sample block (`tests/sdet/test_proxmox_vm_lifecycle.py`). The comment's operator-meaningful intent: "regenerate this sample if the runner output format changes." Per Phase 12 D-10, semantically rewrite to preserve that intent and cite the surviving doc anchor `docs/SDET-AUTHORING.md` (which already documents the SDET-mode digest contract).

### Task 3 — Apply D-05 fix (commit `f937212`)

**File:** `README.md`

**BEFORE (line 104):**
```
$ mcp-test-framework run --explain
```

**AFTER (line 104):**
```
$ mcp-test-framework run --config config.yaml --explain
```

Surrounding fenced-code block, downstream sample output (header rows, `MCP server:`, `Discovered:`, `Running:`, `Skipping:`), and prose preceding the block were untouched.

**Verification:**
```
$ uv run pytest tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config -v
PASSED [path0]  PASSED [path1]   2 passed
```

### Task 4 — Apply D-06 fix (commit `deefa26`)

**File:** `README.md`

**BEFORE (line 274):**
```
<!-- mirrors _runner.py output — re-run the framework when output format changes (Phase 21 D-14) -->
```

**AFTER (line 274):**
```
<!-- mirrors live runner output — re-run the framework and refresh this block when the operator-facing output format changes; see docs/SDET-AUTHORING.md for the SDET-mode digest contract -->
```

**Rewrite rationale:** Preserved the operator-/maintainer-meaningful intent ("re-run the framework and refresh this block when the runner output format changes"). Replaced the planning-anchors `Phase 21 D-14` with a citation of the surviving doc anchor `docs/SDET-AUTHORING.md` (one of the allowed anchors per the plan, and the one that documents the SDET-mode digest contract being illustrated by the sample below the comment). The path reference `_runner.py` was rephrased to `live runner output` to drop the source-relative implementation detail without losing the "this mirrors actual output" signal. No `noqa`-style allowlist was added; no test was modified.

**Verification:**
```
$ uv run pytest tests/framework/unit/test_doc_scrub.py -v
13 passed
```

All 13 tests in `test_doc_scrub.py` green; the two close-gate tests targeted by this plan (`test_readme_exists_and_no_banned_tokens` and `test_doc_invocations_consistently_pair_with_config`) both pass.

## Final Verification

```
$ uv run pytest tests/framework/unit/test_doc_scrub.py::test_readme_exists_and_no_banned_tokens \
    tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config -v
PASSED  test_readme_exists_and_no_banned_tokens
PASSED  test_doc_invocations_consistently_pair_with_config[path0]   (README.md)
PASSED  test_doc_invocations_consistently_pair_with_config[path1]   (docs/EXTENDING.md)
3 passed
```

## Deviations from Plan

None — plan executed exactly as written. Single D-05 hit and the predicted single D-06 line both matched what CONTEXT.md / PATTERNS.md anticipated.

## Commits

| Hash      | Message                                                                       |
| --------- | ----------------------------------------------------------------------------- |
| `f937212` | docs(23-03): pair --explain example with --config (D-05)                      |
| `deefa26` | docs(23-03): semantic rewrite of runner-output sample comment (D-06)          |

(Tasks 1 and 2 are diagnostic-only — they produced inventory but no file changes, so no commits.)

## Threat Surface Scan

No new security-relevant surface introduced. The plan only edits `README.md` (operator-facing doc, no code changes, no new endpoints, no schema/auth changes). T-23-03-01 and T-23-03-02 from the plan's `<threat_model>` are mitigated by the fixes themselves (no banned tokens leak; `--config` pairing reinforced).

## Self-Check: PASSED

- File `README.md` exists and contains the AFTER strings:
  - `mcp-test-framework run --config config.yaml --explain` — present at line 104.
  - `mirrors live runner output … docs/SDET-AUTHORING.md for the SDET-mode digest contract` — present at line 274.
- Commits `f937212` and `deefa26` exist in `git log`.
- Both close-gate tests pass (verified above; full `tests/framework/unit/test_doc_scrub.py` 13/13 green).
- Only `README.md` was modified across both commits.
