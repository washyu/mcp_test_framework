# Phase 32: Surface-shim removals — CLI + package + fixtures + discovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 32-surface-shim-removals-cli-package-fixtures-discovery
**Areas discussed:** Plan decomposition

---

## Gray-area selection

Four gray areas were presented; user selected only "Plan decomposition" for explicit discussion. The other three were captured as Claude's-discretion defaults in CONTEXT.md (with RESEARCH-FOR-PLAN flags), to be revisited at plan time.

| Area | Description | Selected for discussion |
|------|-------------|-------------------------|
| SHIM-06 `tests/sdet/` discovery — silent vs loud | Silent removal (pytest just stops finding tests under tests/sdet/) vs loud collection-time scan that fires operator-tone error if test_*.py files exist. | |
| SHIM-07 fixture removal — stub-raise vs clean delete | Clean delete (pytest's stock 'fixture not found' error speaks) vs stub-raise (keep the 6 fixture names registered, pytest.fail with mcp_-prefixed pointer). Success criterion #4 wants 'prefixed names surfaced in the error'. | |
| SHIM-08 console script — delete entry vs keep _deprecated_script.py shim | Delete pyproject [project.scripts] entry (shell 'command not found') vs keep the entry but convert _deprecated_script.py to hard-raise migration shim pointing at mcp-contracts. | |
| Plan decomposition — 6 plans (1:1) vs grouped by surface type | 1:1 per SHIM (6 plans) vs grouped (3 plans by surface type) vs single mega-plan (1 plan). Phase 31 went 1:1. | ✓ |

---

## Plan decomposition

| Option | Description | Selected |
|--------|-------------|----------|
| 1:1 per SHIM — 6 plans | 32-01..32-06, one per requirement. Mirrors Phase 31 cadence; atomic rollback per surface; each plan small and reviewable. | ✓ |
| Grouped by surface — 3 plans | 32-01 import-surface (SHIM-01 + SHIM-08), 32-02 CLI-surface (SHIM-02 + SHIM-03), 32-03 collection-surface (SHIM-06 + SHIM-07). Fewer plans; risk = single plan failure blocks two requirements. | |
| Single mega-plan — 1 plan | All 6 removals one commit. Fastest cadence; tightest blast radius. All-or-nothing rollback; doesn't match Phase 31 precedent. | |

**User's choice:** 1:1 per SHIM — 6 plans (recommended option).
**Notes:** No additional context provided; the recommended-default sufficed. Plan order canonical numeric (01→06), interchangeable (per CONTEXT.md D-02).

---

## Claude's Discretion

User did not select these for discussion; defaults captured in CONTEXT.md with RESEARCH-FOR-PLAN flags so the planner can revisit before locking each plan.

- **SHIM-01 mechanism (D-03):** Hard-raise migration shim from `sdet/__init__.py` (not clean-delete) — success criterion #1 requires operator-tone pointer to `mcp_test_framework.test_code`, stock `ModuleNotFoundError` doesn't carry it.
- **SHIM-02/03 mechanism (D-04):** Hidden Typer intercepts registering legacy `--sdet` + `gen-sdet-classes` that raise operator-tone `UsageError` naming `--test-code` / `gen-test-classes` — success criterion #2 requires the new names in the error.
- **SHIM-06 mechanism (D-05):** Loud collection-time detection of `tests/sdet/` (warn-and-skip) — consistent with Phase 31's loud-and-friendly pattern; minimum success-criterion bar would accept silent removal.
- **SHIM-07 mechanism (D-06):** Stub-raise fixtures (keep 6 alias names registered, body = pytest.fail with prefixed-name pointer) — success criterion #4 explicitly requires "prefixed names surfaced in the error".
- **SHIM-08 mechanism (D-07):** Keep `[project.scripts] mcp-test-framework` entry + convert `_deprecated_script.py` from DeprecationWarning wrapper to hard-raise migration shim — preserves loud-pointer pattern vs shell-level "command not found".
- **Shared `_emit_legacy_surface_pointer` helper (D-08):** Recommend planner research whether Phase 31 D-04 actually extracted `_operator_errors.py`; reuse or extract.

## Deferred Ideas

- v1.6 capstone clean-deletion of every Phase 32 surviving surface (sdet/ dir, hidden Typer intercepts, stub-raise fixtures, _deprecated_script.py + console-script entry, tests/sdet/ warn-on-presence path-string). Phase 35 SHIM-09 must grandfather these for v1.5.
- Single-line CHANGELOG / MILESTONES footnote capturing the v1.4→v1.5 shim-retirement story (out of Phase 32 scope; historical record).
- Phase 35 SHIM-09 regression-gate grandfathering list — forwarded to Phase 35 planner via CONTEXT.md `<deferred>`.
