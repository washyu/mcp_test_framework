---
phase: 25-public-api-rename-seed-023-sdet-test-code
plan: 01
subsystem: public-api / package-rename
tags: [rename, sdet, test_code, deprecation-shim, RENAME-01]
requires:
  - mcp_test_framework.sdet package (pre-rename, src/mcp_test_framework/sdet/)
provides:
  - mcp_test_framework.test_code (canonical public surface)
  - mcp_test_framework.sdet (back-compat shim with DeprecationWarning)
affects:
  - src/mcp_test_framework/cli.py (two local-import lines inside gen_sdet_classes)
  - tests/framework/unit/ (11 framework self-test modules — Rule 1 deviation)
tech-stack:
  added: []
  patterns:
    - "stdlib DeprecationWarning shim (stacklevel=2, Python default once-per-process filter)"
    - "git mv for package rename to preserve blame history (D-06 convention)"
    - "# noqa: sdet-rename-shim token on every shim line (D-18) for plan 06 sweep exclusion"
key-files:
  created:
    - src/mcp_test_framework/sdet/__init__.py (25-line shim; commit baf1509)
  modified:
    - src/mcp_test_framework/test_code/__init__.py (renamed from sdet/; docstring + 4 imports)
    - src/mcp_test_framework/test_code/_codegen.py (renamed; 4 dotted-path string replacements)
    - src/mcp_test_framework/test_code/_slugs.py (renamed; no content change)
    - src/mcp_test_framework/test_code/_tool_factory.py (renamed; 3 dotted-path references)
    - src/mcp_test_framework/test_code/errors.py (renamed; no content change)
    - src/mcp_test_framework/test_code/response.py (renamed; no content change)
    - src/mcp_test_framework/test_code/session.py (renamed; 2 import lines)
    - src/mcp_test_framework/cli.py (2 local imports inside gen_sdet_classes)
    - tests/framework/unit/test_codegen_emitter.py (Rule 1 fix)
    - tests/framework/unit/test_codegen_integration_mock.py (Rule 1 fix)
    - tests/framework/unit/test_codegen_typecheck.py (Rule 1 fix)
    - tests/framework/unit/test_codegen_walker.py (Rule 1 fix)
    - tests/framework/unit/test_sdet_conftest_hook.py (Rule 1 fix)
    - tests/framework/unit/test_sdet_fixtures.py (Rule 1 fix)
    - tests/framework/unit/test_sdet_renderer.py (Rule 1 fix)
    - tests/framework/unit/test_session_loader_invariants.py (Rule 1 fix)
    - tests/framework/unit/test_tool_call_error.py (Rule 1 fix)
    - tests/framework/unit/test_tool_factory.py (Rule 1 fix)
    - tests/framework/unit/test_tool_response.py (Rule 1 fix)
decisions:
  - "D-01 honored: stdlib DeprecationWarning, no custom subclass, no FutureWarning"
  - "D-02 honored: stacklevel=2, Python's default once-per-process filter"
  - "D-05 honored: warning text uses the locked template '<old> is deprecated since v1.4 and will be removed in v1.5 — use <new> instead.'"
  - "D-06 honored: git mv preserves blame across the rename (verified: git log --follow shows history back to Phase 17)"
  - "D-15 honored: __all__ unchanged in test_code/__init__.py — exactly the four-name surface (ToolCallError, ToolResponse, mcp_session, tool)"
  - "D-18 honored: every shim line carries '# noqa: sdet-rename-shim' for the plan 06 sweep gate"
  - "Plan-scope boundary held: gen-sdet-classes command name, --sdet flag, _BOOTSTRAP_SDET_STUB, cfg.sdet references all preserved (plans 02/03 own those)"
metrics:
  duration: ~9 minutes
  completed: 2026-05-16
  tasks_completed: 3
  files_modified: 18  # 7 renamed package files + 1 cli.py + 11 framework tests; sdet/__init__.py is created (separate)
  commits: 4
---

# Phase 25 Plan 01: Public-API Rename (sdet → test_code) — Package Rename + Shim Summary

Renamed `src/mcp_test_framework/sdet/` to `test_code/` via `git mv` (blame preserved), repointed every internal `mcp_test_framework.sdet` import to the new path, and dropped a 25-line back-compat shim at `src/mcp_test_framework/sdet/__init__.py` that re-exports the four public names (`mcp_session`, `tool`, `ToolCallError`, `ToolResponse`) from `test_code/` and fires one `DeprecationWarning` per process naming the v1.4→v1.5 removal milestone.

## Objective Met

RENAME-01 acceptance text holds:

- `from mcp_test_framework.test_code import mcp_session, tool, ToolCallError, ToolResponse` resolves to the renamed package (verified via package-load smoke).
- `from mcp_test_framework.sdet import ...` still resolves and emits a `DeprecationWarning` naming the v1.5 removal (verified via `showwarning` hook + `python -W always::DeprecationWarning`).
- No `from mcp_test_framework.sdet` references remain inside `src/` other than the shim package itself (verified via grep across `src/mcp_test_framework/`).
- Public import surface preserved verbatim: `__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]` in `test_code/__init__.py`.

## Tasks Completed

| # | Name                                                                                            | Commit  | Files                                                                              |
| - | ----------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| 1 | git mv sdet/ → test_code/ and rewrite internal imports inside the renamed package               | 5107b9a | 7 renamed files under src/mcp_test_framework/test_code/                            |
| 2 | Update internal import sites OUTSIDE the renamed package (cli.py local imports inside gen_sdet_classes) | c02a685 | src/mcp_test_framework/cli.py                                                      |
| 3 | Create back-compat sdet/ shim package re-exporting from test_code/ with DeprecationWarning      | baf1509 | src/mcp_test_framework/sdet/__init__.py                                            |
| — | **Deviation (Rule 1):** repoint framework self-test imports                                     | ed7d9ec | 11 modules under tests/framework/unit/                                             |

## Verification

- `uv run python -c "from mcp_test_framework.test_code import mcp_session, tool, ToolCallError, ToolResponse; print('ok')"` → `ok`
- `uv run python -W always::DeprecationWarning -c "import warnings; warnings.simplefilter('always'); import mcp_test_framework.sdet"` → fires the literal D-05 string `mcp_test_framework.sdet is deprecated since v1.4 and will be removed in v1.5 — use mcp_test_framework.test_code instead.`
- `uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse; print('ok')"` → `ok` (shim re-export works)
- Identity check: `mcp_session is sdet.mcp_session and tool is sdet.tool and ToolCallError is sdet.ToolCallError and ToolResponse is sdet.ToolResponse` → True (shim re-exports the same objects, not copies).
- `git log --follow src/mcp_test_framework/test_code/__init__.py --oneline | head` → history goes back through Phase 22 / Phase 18 / Phase 17 commits (blame preserved).
- `grep -rn "from mcp_test_framework.sdet" src/mcp_test_framework/test_code/` → 0 matches
- `grep -rn "mcp_test_framework\.sdet" src/mcp_test_framework/test_code/` → 0 matches
- `grep -c "gen-sdet-classes" src/mcp_test_framework/cli.py` → 12 (preserved per scope boundary, plan 02 owns)
- `grep -c '"--sdet"' src/mcp_test_framework/cli.py` → 1 (preserved per scope boundary, plan 02 owns)
- `uv run python -m pytest tests/framework/ --tb=no -q` → 578 passed, 1 skipped, 2 xfailed, 1 warning, 17 deselected. The single warning is the expected DeprecationWarning fired from `tests/sdet/conftest.py:19` — plan 04 owns the migration of that scenario tree.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 11 framework self-tests broken by the package rename**

- **Found during:** Post-Task-3 smoke run of `pytest tests/framework/unit/`.
- **Issue:** Before this plan, `mcp_test_framework.sdet` was a real package containing `_tool_factory`, `_codegen`, `_slugs`, `errors`, `response`, `session` submodules. Framework self-tests under `tests/framework/unit/` imported from those private submodules (e.g. `from mcp_test_framework.sdet._tool_factory import tool, ToolWrapper`). After Tasks 1+3, the `sdet/` shim only re-exports the four public names from `__init__.py`; the private submodules no longer live under that namespace. 7 framework test modules failed pytest collection with `ImportError: cannot import name '_tool_factory' from 'mcp_test_framework.sdet'`.
- **Fix:** Bulk replace `mcp_test_framework.sdet` → `mcp_test_framework.test_code` across 11 files under `tests/framework/unit/` (covers imports, docstrings, and a `test_codegen_walker.py` assertion that pins the dotted path emitted by codegen).
- **Files modified:** `tests/framework/unit/test_codegen_emitter.py`, `test_codegen_integration_mock.py`, `test_codegen_typecheck.py`, `test_codegen_walker.py`, `test_sdet_conftest_hook.py`, `test_sdet_fixtures.py`, `test_sdet_renderer.py`, `test_session_loader_invariants.py`, `test_tool_call_error.py`, `test_tool_factory.py`, `test_tool_response.py`
- **Commit:** ed7d9ec

**Why this isn't out-of-scope:** The breakage is a direct, immediate consequence of Tasks 1+3 of this plan — these tests were green at the baseline commit (`b25520c`) immediately before the rename. Rule 1 says: "issues DIRECTLY caused by the current task's changes". Per project memory `feedback_phase_scope_intent.md` ("when a phase title names a fix, the actual fix is in scope; don't let sub-agents reframe it as cross-cutting / defer"), a rename plan that breaks framework self-tests must repair them here, not defer to a later plan.

**Why this isn't owned by plan 04 (tests/sdet/ migration):** Plan 04's frontmatter `files_modified` lists only `tests/sdet/conftest.py`, `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py`, `_runner.py`, `fixtures.py`, `pyproject.toml`. It scopes to operator-authored scenario migration + dual-discovery scaffolding; it does NOT touch `tests/framework/unit/`.

**D-03 intent preserved:** The framework's own `pyproject.toml` `filterwarnings = always::DeprecationWarning:mcp_test_framework` entry (to land in plan 04 per its frontmatter) is for catching FUTURE re-introductions of the old surface. With this deviation, framework self-tests use the canonical `test_code` path going forward; the filter still bites if a future framework commit reaches back to `mcp_test_framework.sdet` for anything other than the shim itself.

## Scope Boundary Held

Per plan 25-01 Task 2 scope rules and CONTEXT.md ownership map, the following were intentionally **not** touched:

- `@app.command("gen-sdet-classes")` decorator + `gen_sdet_classes` function name (plan 02 owns)
- `--sdet` flag on the `run` command (plan 02 owns)
- `_BOOTSTRAP_SDET_STUB`, `cfg.sdet`, `Config.sdet` references (plan 03 owns)
- User-facing terminology "SDET" / "sdet" in docstrings, help text, error messages (plans 02 / 05 own)
- `tests/sdet/conftest.py`, `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` migration (plan 04 owns)
- `docs/SDET-AUTHORING.md` doc rename and content scrub (plan 05 owns) — only the docstring reference inside `test_code/__init__.py` was forward-pointed to `docs/TEST-CODE-AUTHORING.md` per Task 1 step 3
- `tests/sdet/_generated/` regeneration (untracked operator artifact; will be regenerated by `gen-sdet-classes` against the new dotted path)

## TDD Gate Compliance

Plan type is `execute` (not `tdd`); no RED/GREEN/REFACTOR gate sequence required.

## Self-Check: PASSED

Commits verified (`git log --oneline -6`):
- FOUND: 5107b9a
- FOUND: c02a685
- FOUND: baf1509
- FOUND: ed7d9ec

Files verified:
- FOUND: src/mcp_test_framework/test_code/__init__.py
- FOUND: src/mcp_test_framework/test_code/session.py
- FOUND: src/mcp_test_framework/test_code/_tool_factory.py
- FOUND: src/mcp_test_framework/sdet/__init__.py (shim)
