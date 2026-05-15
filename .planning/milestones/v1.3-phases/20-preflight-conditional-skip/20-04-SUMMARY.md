---
phase: 20-preflight-conditional-skip
plan: 04
subsystem: test-suite-hygiene
tags: [cleanup, sdet, dogfood-removal, sut-agnostic, v1.3]
requires: []
provides:
  - "tests/sdet/ scoped to framework infrastructure only (no SUT-specific scenarios)"
  - "D-04 satisfied: Phase 19 Proxmox dogfood removed from working tree"
  - "D-06 satisfied via option (c): list_registered_servers sanity test removed"
affects:
  - "tests/sdet/test_proxmox_vm_lifecycle.py (DELETED)"
  - "tests/sdet/test_basic_call.py (DELETED)"
tech-stack:
  added: []
  patterns:
    - "Framework self-tests do not exercise SUT-specific behavior; SDET-authored scenarios live under tests/sdet/ as operator opt-in"
key-files:
  created: []
  modified: []
  deleted:
    - "tests/sdet/test_proxmox_vm_lifecycle.py"
    - "tests/sdet/test_basic_call.py"
  preserved:
    - "tests/sdet/__init__.py"
    - "tests/sdet/conftest.py"
decisions:
  - "D-06 option (c): delete test_basic_call.py rather than soften with @pytest.mark.skipif — strengthens the framework-self-tests-don't-touch-SUT boundary and defers CI sanity coverage to the planned hello-world MCP fixture"
metrics:
  duration: "~1m"
  completed: "2026-05-14"
  tasks_completed: 1
  files_deleted: 2
  files_preserved: 2
status: complete
---

# Phase 20 Plan 04: tests/sdet/ cleanup Summary

Removed both SUT-specific test files from `tests/sdet/` (Phase 19 Proxmox dogfood and Phase 18 `list_registered_servers` sanity), leaving only framework infrastructure (`__init__.py`, `conftest.py`) so the directory is ready to host operator-authored scenarios per the SDET persona.

## What was done

- **Task 1 — Delete SUT-specific test files from `tests/sdet/`**
  - Deleted `tests/sdet/test_proxmox_vm_lifecycle.py` via `git rm` (commit `01ed0c0`). D-04 satisfied — the Phase 19 Proxmox-hardcoded dogfood is gone from the working tree. The architectural patterns it demonstrated (module-scope yield fixture, ScenarioState dataclass, cleanup-on-failure, VMID isolation) survive in Phase 19's CONTEXT.md / SUMMARY artifacts for Phase 21 docs (`docs/SDET-AUTHORING.md`) to lift.
  - Deleted `tests/sdet/test_basic_call.py` via `git rm` (commit `8cd492d`). D-06 satisfied via the planner-locked option (c) — by the same logic as D-04, this test exercises a specific live MCP server (homelab-mcp) and cannot run in CI without operator infrastructure. The CI-runnable sanity surface this test was approximating is now explicitly deferred to the planned hello-world MCP fixture (CONTEXT.md Deferred Ideas).
  - Preserved `tests/sdet/__init__.py` (empty package marker) and `tests/sdet/conftest.py` (Phase 18 JUnit `user_properties` hook for `ToolCallError`). Both files are byte-identical to their pre-task state — verified via Grep on the docstring (`"ToolCallError -> JUnit user_properties hook"`) and the hook signature (`def pytest_exception_interact(node, call, report):`).
  - Verified `uv run pytest --collect-only tests/sdet/` reports `collected 0 items` and `no tests collected` — the directory has no test files but the discovery scope still resolves cleanly.

## D-06 disposition note (for Phase 21 docs)

The planner picked option (c) — `delete` rather than (a) `leave as-is` or (b) `add @pytest.mark.skipif inline`. Rationale:

- **(a) was rejected** because leaving a SUT-touching test in the project's own test suite leaks the homelab-mcp dependency into the framework's identity. The framework is generic; its shipped tests must be too.
- **(b) was rejected** because the SDET-side `@pytest.mark.skipif` recipe is better demonstrated in `docs/SDET-AUTHORING.md` (Phase 21) than in a half-hearted in-repo example that still requires a probe callable. Option (c) keeps the in-repo demonstration debt unincurred until the canonical recipe lands in docs.
- **(c) was chosen** because after D-04 the `tests/sdet/` directory was already trending toward "framework infrastructure only" — removing `test_basic_call.py` makes the contract crisp: this directory is the SDET surface, not the framework's self-test surface.

**Phase 21 should mention** in `docs/SDET-AUTHORING.md` that the deferred hello-world MCP CI fixture is the planned home for cross-tool sanity coverage (the "did every discovered tool get wrapped" check that `test_basic_call.py` partially approximated). The in-tree MCP work is itself captured under CONTEXT.md Deferred Ideas ("Hello-world MCP server for CI/CD coverage").

## Deviations from Plan

None — the plan was executed exactly as written. Both `git rm` operations succeeded, framework infrastructure files were not touched, the verify command (pytest `--collect-only`) returned the expected zero-collection result.

## Verification

- `Test-Path 'tests/sdet/test_proxmox_vm_lifecycle.py'` → `False` (verified via `ls`/`[ -f ]`).
- `Test-Path 'tests/sdet/test_basic_call.py'` → `False` (verified via `ls`/`[ -f ]`).
- `Test-Path 'tests/sdet/__init__.py'` → `True`.
- `Test-Path 'tests/sdet/conftest.py'` → `True`.
- `tests/sdet/conftest.py` content unchanged: contains `"ToolCallError -> JUnit user_properties hook"` docstring and `def pytest_exception_interact(node, call, report):` hook (verified via Grep).
- `uv run pytest --collect-only tests/sdet/` → `collected 0 items`, `no tests collected in 0.01s` — exit OK.
- `git log --oneline -2` shows both deletions as separate commits with conventional messages flagging plan-driven intent (D-04, D-06).

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `01ed0c0` | `test(20-04): delete tests/sdet/test_proxmox_vm_lifecycle.py (D-04)` |
| 2 | `8cd492d` | `test(20-04): delete tests/sdet/test_basic_call.py (D-06)` |

The orchestrator's pre-merge deletion guard should treat both deletions as authorized — each commit message explicitly references the CONTEXT.md decision ID that locked the disposition (D-04 / D-06), and the plan frontmatter's `must_haves.truths` lists both deletions as required post-state.

## Requirements satisfied

- **CLEANUP-DOGFOOD-01** — SUT-specific dogfood test files removed from `tests/sdet/`; the project test suite stays SUT-agnostic.

## Self-Check: PASSED

- FOUND: `tests/sdet/__init__.py`
- FOUND: `tests/sdet/conftest.py`
- MISSING (expected): `tests/sdet/test_proxmox_vm_lifecycle.py`
- MISSING (expected): `tests/sdet/test_basic_call.py`
- FOUND commit: `01ed0c0` (proxmox lifecycle deletion)
- FOUND commit: `8cd492d` (basic_call deletion)
- pytest collection: `0 items` from `tests/sdet/` — invariant met
