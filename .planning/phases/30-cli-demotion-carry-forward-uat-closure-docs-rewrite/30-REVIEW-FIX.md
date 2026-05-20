---
status: all_fixed
phase: 30
findings_in_scope: 4
fixed: 4
skipped: 0
iteration: 1
fix_scope: critical_warning
review_source: 30-REVIEW.md
generated: 2026-05-19
---

# Phase 30 — Code Review Fix Report

## Summary

All 4 in-scope findings (1 BLOCKER + 3 WARNINGS) from `30-REVIEW.md` were fixed in a single atomic commit.
Info findings (IN-01, IN-02) were intentionally skipped per `fix_scope: critical_warning`.

**Fix commit:** `1b6b235` — `fix(30): CR-01 WR-01 WR-02 WR-03 parity test scope+markers+guard+priority`

**File modified:** [tests/framework/parity/test_cli_vs_pytest_route.py](tests/framework/parity/test_cli_vs_pytest_route.py)

**Post-fix regression check:** `uv run pytest tests/framework -x -q --tb=short` → 670 passed, 0 failures.

## Findings Fixed

### CR-01 (BLOCKER) — Route scope mismatch

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:114`

Route B argument changed from `"tests/"` to `"tests/contract"` so both routes
collect the same scope. Route A (CLI `run`) internally defaults to `tests/contract/`
via `_runner._build_pytest_args()`; Route B previously passed `"tests/"` (the full
suite). The two collections were non-equivalent — Route B would include 670+ framework
self-test nodeids absent from Route A — making the `outcomes_a == outcomes_b` assertion
always fail on a real stack, masked only by the `tools: {}` vacuous-collection state.

### WR-02 — Inner subprocess `-m` overrides `addopts` exclusions

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:106, 117`

Both inner subprocess `-m` arguments expanded from `"not parity"` to
`"not parity and not live_homelab and not live_ollama"`. Pytest's command-line `-m`
replaces (not composes with) the `addopts` `-m` expression, so the previous form
silently dropped the live-stack exclusions and could let `live_homelab` /
`live_ollama` tests leak into the inner runs.

### WR-01 — Asymmetric vacuousness guard

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:~157`

Added symmetric `assert outcomes_b, (...)` guard immediately after the existing
`assert outcomes_a, (...)`. The previous single-sided guard would let a
silently-empty Route B dict pass and then fail with a confusing divergence message
instead of a clear "Route B produced no tests" error.

### WR-03 — `_parse_outcomes` last-seen-wins instead of any-fail-wins

**File:** `tests/framework/parity/test_cli_vs_pytest_route.py:72-91`

Introduced a `PRIORITY` dict (`failed=0, error=1, skipped=2, passed=3`) and
conditional update: `if nodeid not in out or PRIORITY[outcome] < PRIORITY[out[nodeid]]`.
The previous loop body wrote `out[nodeid] = outcome` unconditionally, so a `passed`
entry emitted after an earlier `failure` for the same nodeid silently won — masking
real failures. Duplicate nodeids now resolve to the highest-priority (lowest-numeric)
outcome.

## Findings Skipped

- **IN-01** (Info, advisory): `pytest_configure` `config` param name shadows the `config`
  fixture — confirmed not a bug; docstring already explains the choice.
- **IN-02** (Info, advisory): Conditional note in `docs/LIBRARY-MODE.md` parity section —
  superseded by WR-02 fix (no addopts override interaction note needed).

## Next Steps

- `/gsd-verify-work` to re-verify Phase 30 (the CLOSE-02 gap from 30-VERIFICATION.md is now closed).
- After verification passes → `/gsd-complete-milestone v1.4`.
