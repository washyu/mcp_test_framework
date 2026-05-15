---
phase: 23-test-suite-debt-cleanup
plan: 04
subsystem: testing
tags: [close-gate, verification, pytest, diagnostic-only, d-07, d-08]

# Dependency graph
requires:
  - phase: 23-test-suite-debt-cleanup-plan-01
    provides: Cluster A reds resolved (sdet-required propagation + D-03 env-pollution seal)
  - phase: 23-test-suite-debt-cleanup-plan-02
    provides: Cluster B parents[2] -> parents[3] mechanical bump at 2 sites
  - phase: 23-test-suite-debt-cleanup-plan-03
    provides: Cluster C README --config pairing + banned-token semantic rewrite
provides:
  - "Recorded green close-gate: tests/framework/ exits 0 with failed==0 and errored==0"
  - "Cumulative diff stats verifying D-02 invariant (zero src/mcp_test_framework/ changes across the entire phase)"
  - "Phase 23 sign-off — v1.3 close inherits a green framework suite"
affects: [phase-24-serializer-fix, v1.3-close]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Diagnostic-only close-gate plan (files_modified: []) — single authoritative pytest assertion for the phase, no source edits"

key-files:
  created:
    - .planning/phases/23-test-suite-debt-cleanup/23-04-SUMMARY.md
  modified: []

key-decisions:
  - "Close-gate re-run independent of orchestrator's recall — verified locally that 575 passed / 1 skipped / 17 deselected / 2 xfailed / 0 failed / 0 errored holds at HEAD (d80a0bb)"
  - "D-02 invariant verified at the cumulative-diff layer (git diff $PHASE_BASE..HEAD -- src/mcp_test_framework/) — empty across the entire phase, including the recovery commit 24434f7"
  - "T-23-04-01 (addopts tampering) mitigated: pyproject.toml addopts read first; confirmed verbatim 'not live_homelab and not live_ollama' filter unchanged"
  - "T-23-04-02 (false-positive green via masked src/ edit) mitigated: zero commits in the $PHASE_BASE..HEAD range touched src/mcp_test_framework/ (verified via git log --oneline $PHASE_BASE..HEAD -- src/mcp_test_framework/ returning empty)"

patterns-established:
  - "Phase close-gate verification template: re-run the gated command, capture verbatim summary line, snapshot cumulative phase diff against the documented base, assert D-02-style boundaries explicitly"

requirements-completed: []

# Metrics
duration: ~5min
completed: 2026-05-15
---

# Phase 23 Plan 04: Close-Gate Verification Summary

**Phase 23 close-gate is GREEN. `uv run pytest tests/framework/ --tb=no -q` exits 0 with `575 passed, 1 skipped, 17 deselected, 2 xfailed in 15.19s` — failed==0 and errored==0 (D-07/D-08 satisfied). Zero `src/mcp_test_framework/` changes across the entire phase (D-02 invariant holds end-to-end). v1.3 close inherits a green framework suite.**

## Close-Gate Result (Task 1)

### Re-run command and exit code

```
$ uv run pytest tests/framework/ --tb=no -q
```

**Exit code:** `0`

### Verbatim summary line

```
575 passed, 1 skipped, 17 deselected, 2 xfailed in 15.19s
```

### D-08 explicit assertion

| Metric    | Value                            | D-08 requirement |
|-----------|----------------------------------|------------------|
| failed    | 0 (omitted from summary)         | == 0   ✓ PASS    |
| errored   | 0 (omitted from summary)         | == 0   ✓ PASS    |
| passed    | 575                              | n/a              |
| skipped   | 1                                | pre-existing — out of scope per D-08 |
| xfailed   | 2                                | pre-existing — out of scope per D-08 |
| deselected| 17                               | live_homelab + live_ollama markers (pyproject.toml addopts) |

The pre-existing xfailed (2) and skipped (1) counts are exactly what D-08 tolerates ("pre-existing xfailed and skipped tests stay as-is — they are not red"). The 17 deselected matches the documented `not live_homelab and not live_ollama` addopts filter.

## Trend vs Phase Baseline

| Snapshot | failed | errored | passed | source |
|----------|--------|---------|--------|--------|
| Phase 23 entry baseline (per CONTEXT.md D-07) | 12 | 1 | 563 | pre-Plan 23-01 inventory |
| Post Plan 23-01 (Cluster A) | 8 | 1 | 567 | 23-01-SUMMARY.md Task 4 |
| Post Plan 23-02 (Cluster B) | 3 | 1 | n/a | 5 Cluster B reds → green |
| Post Plan 23-03 (Cluster C) | 1 | 1 | n/a | 2 Cluster C reds → green; 1 stale import + 1 live-marker error remain |
| Post recovery commit 24434f7 (D-07 catch-up) | 0 | 0 | 575 | this re-run |

Net: **−12 failed, −1 errored**. Goal achieved.

## Cumulative Diff Snapshots (Task 1 verification steps 1–3)

Phase base: `8d269ef` (the prescribed Phase 23 base from Plan 23-02 SUMMARY's worktree-base check). Range: `8d269ef..HEAD` (HEAD = `d80a0bb`).

### 1. `git diff --stat 8d269ef..HEAD -- src/mcp_test_framework/`

```
(empty — zero files modified)
```

**D-02 invariant: HOLDS.** No production code edited at any point during Phase 23 (Plans 01, 02, 03, OR the post-merge recovery commit 24434f7). Cross-checked via `git log --oneline 8d269ef..HEAD -- src/mcp_test_framework/` → empty output.

### 2. `git diff --stat 8d269ef..HEAD -- tests/framework/`

```
 tests/framework/conftest.py                      | 24 ++++++++++++
 tests/framework/smoke/test_smoke_homelab_mcp.py  | 10 ++++-
 tests/framework/smoke/test_smoke_ollama_judge.py |  9 ++++-
 tests/framework/test_config_init_cli.py          |  9 ++++-
 tests/framework/test_isolation.py                | 16 ++++++--
 tests/framework/test_tool_config.py              | 48 ++++++++++++++++++------
 tests/framework/unit/test_cli_errors.py          | 28 ++++++++++++--
 tests/framework/unit/test_migration_doc.py       |  2 +-
 8 files changed, 120 insertions(+), 26 deletions(-)
```

Attribution per file:

| File | Owning plan | Notes |
|------|-------------|-------|
| `tests/framework/conftest.py` | 23-01 (D-02 seam, NEW) | Verbatim D-02 body — session-scoped `config` fixture override |
| `tests/framework/smoke/test_smoke_homelab_mcp.py` | 23-01 (forward-compat) | S1 module stub at bare Config() sites |
| `tests/framework/smoke/test_smoke_ollama_judge.py` | 23-01 (forward-compat) | S2 inline kwarg |
| `tests/framework/test_config_init_cli.py` | 23-01 (forward-compat) | S2 inline + version 1→2 |
| `tests/framework/test_isolation.py` | 24434f7 (D-07 recovery) | Added `pytest.mark.live_homelab` to pytestmark + comment refresh |
| `tests/framework/test_tool_config.py` | 23-01 + 24434f7 | 23-01: _SDET_STUB application + version assertion bump + parametrize update. 24434f7: stale `tests.test_mcp_tool_contract` → `tests.contract.test_mcp_tool_contract` |
| `tests/framework/unit/test_cli_errors.py` | 23-01 + 23-02 | 23-01: monkeypatch.delenv env-pollution seal. 23-02: `parents[2]` → `parents[3]` at line 407 |
| `tests/framework/unit/test_migration_doc.py` | 23-02 | `parents[2]` → `parents[3]` at line 15 |

**Verdict:** Only NEW file is `tests/framework/conftest.py` (Plan 01 D-02 seam). Every other modified file maps to a documented Plan 01/02/03 target or the recovery commit 24434f7 (which closed the two D-07 residual reds). No collateral edits outside the phase's stated scope.

### 3. `git diff --stat 8d269ef..HEAD -- README.md`

```
 README.md | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

Attribution: both lines belong to Plan 23-03 — the `--explain` invocation pairing (line 104) + the runner-output sample-comment semantic rewrite (line 274). Confirmed by inspection against 23-03-SUMMARY.md "BEFORE/AFTER" tables.

## Threat Mitigation Verification

Per `<threat_model>` in the plan:

| Threat ID | Mitigation | Verified? |
|-----------|------------|-----------|
| T-23-04-01 (addopts tampering) | Read pyproject.toml first; assert addopts is the documented `not live_homelab and not live_ollama` filter | ✓ PASS — pyproject.toml line 53: `addopts = "-m 'not live_homelab and not live_ollama'"` (verbatim, unchanged) |
| T-23-04-02 (false-positive green via src/ edit) | Run `git diff --stat src/mcp_test_framework/` and assert empty | ✓ PASS — empty diff across entire phase (verified at the cumulative-range layer, not just HEAD vs HEAD~1) |
| T-23-04-03 (test flake) | Single-run assertion accepted; flake → follow-up plan per D-07 | ✓ N/A — single re-run was clean; no flake observed |

## Phase 23 Sign-Off

All success criteria met:

- [x] Phase 23 close-gate: `uv run pytest tests/framework/ --tb=no -q` exits 0 with `failed == 0 and errored == 0`
- [x] D-02 invariant: `src/mcp_test_framework/` git-diff is empty (cumulative range, not just HEAD~1)
- [x] Only `tests/framework/conftest.py` was created in `tests/framework/`; other edits limited to Plan 01/02/03 + D-07 recovery targets
- [x] README.md changes limited to Plan 23-03 sentences (4 lines, 2 insertions / 2 deletions)
- [x] pyproject.toml addopts unchanged (T-23-04-01 mitigated)
- [x] SUMMARY records exit code, full final-line summary text, and the diff-stat snapshots

**Phase 23 closes GREEN.** v1.3 milestone proceeds to Phase 24 (serializer fix) with a green framework-test baseline.

## Deviations from Plan

None — plan executed exactly as written. The plan is `files_modified: []` (diagnostic-only) and the close-gate command returned exit 0 on the first run. No follow-up plan needed; no new reds surfaced; no flake.

The two residual reds the orchestrator closed in recovery commit `24434f7` (stale `tests.test_mcp_tool_contract` import + missing `live_homelab` marker on `test_isolation.py`) were correctly classified under D-07 ("any additional reds that appear during phase execution are in scope") and patched before this close-gate plan ran. They were attributed to Phase 15 folder-split residue and Phase 20 preflight-deletion fallout respectively — both upstream-phase decisions, both mechanical fixes, neither requires reopening Plan 01/02/03.

## Self-Check: PASSED

Verified files exist:
- `.planning/phases/23-test-suite-debt-cleanup/23-04-SUMMARY.md` — this file (just written)

Verified commits referenced exist (in `git log`):
- `8d269ef` — phase base (verified by `git cat-file -e 8d269ef`)
- `24434f7` — D-07 recovery commit
- `d80a0bb` — most recent phase commit (HEAD at re-run time)

Verified close-gate result is reproducible: ran `uv run pytest tests/framework/ --tb=no -q` once during this plan; captured exit code 0 and the verbatim summary line.

Verified D-02 invariant via two independent checks:
1. `git diff --stat 8d269ef..HEAD -- src/mcp_test_framework/` → empty
2. `git log --oneline 8d269ef..HEAD -- src/mcp_test_framework/` → empty (no commits even touched files in src/)

## Deferred Issues

None new. The pre-existing deferred items captured in 23-01-SUMMARY.md ("Deferred Issues" section, items 3–4: live-marker scaffold drift in `test_config_init_cli.py` and smoke `cfg.target.tool_name` references) remain behind `live_homelab`/`live_ollama` markers and are out of close-gate scope. They were never red in the default-addopts run; capturing them here only as a pointer for a future live-run hardening pass.

---
*Phase: 23-test-suite-debt-cleanup*
*Plan 04 (close-gate): completed 2026-05-15*
