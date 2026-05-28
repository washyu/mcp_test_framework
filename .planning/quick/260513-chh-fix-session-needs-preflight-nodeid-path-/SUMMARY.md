---
phase: quick-260513-chh
plan: 01
status: complete
subsystem: fixtures / preflight gate
tags: [bugfix, tdd, quick-task, phase-18-followup, fixtures, preflight]
dependency_graph:
  requires:
    - "src/mcp_test_framework/fixtures.py::_session_needs_preflight (existing)"
  provides:
    - "src/mcp_test_framework/fixtures.py::_LIVE_PREFIXES (new module-level constant)"
    - "tests/framework/unit/test_session_needs_preflight.py (new regression-pin module, 9 cases)"
  affects:
    - "any operator running `uv run pytest tests/framework[/...]` on a machine without homelab-mcp"
    - "Phase 18 verifier (no longer needs --noconftest workaround)"
tech_stack:
  added: []
  patterns:
    - "Allowlist predicate (Option B from the originating todo) — replaces stale denylist tied to a pre-Phase-15 path"
key_files:
  created:
    - "tests/framework/unit/test_session_needs_preflight.py"
    - ".planning/quick/260513-chh-fix-session-needs-preflight-nodeid-path-/deferred-items.md"
  modified:
    - "src/mcp_test_framework/fixtures.py"
  renamed:
    - ".planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md -> .planning/todos/completed/..."
decisions:
  - "Option B (live-scope allowlist) over Option A (unit-scope denylist) — single source of truth with Phase 18 renderer; defaults to NOT preflight, which is the safer default for any new tests/<future-scope>/ directory."
  - "Legacy tests/unit/ prefix is explicitly NOT honored as a live scope — pinned by test 9 to prevent silent re-introduction if someone ever recreates the directory."
  - "Out-of-scope failures in tests/framework (10 fail, 1 error) are deferred — confirmed pre-existing via git stash round-trip; documented in deferred-items.md."
metrics:
  duration_minutes: ~7
  completed_date: "2026-05-13"
  tasks: 2
  files_touched: 4
  commits: 3
---

# Quick Task 260513-chh: Fix `_session_needs_preflight` Nodeid Path Mismatch — Summary

**One-liner:** Inverted the autouse-preflight gate from a stale `tests/unit/` denylist to a `tests/contract/` + `tests/sdet/` allowlist so framework-only suites run without `homelab-mcp` / Ollama on the box.

## Problem

`_session_needs_preflight` in `src/mcp_test_framework/fixtures.py` short-circuited the live-MCP preflight by checking `item.nodeid.startswith("tests/unit/")`. Phase 15's reorg moved unit tests to `tests/framework/unit/`, so the prefix never matched and preflight always fired. Operators had to either set `MCPTF_CONFIG_FILE` to point at a real `homelab-mcp` config or pass `--noconftest` — both surfaced as friction during Phase 18 (logged in 18-02, 18-03, 18-08 SUMMARYs).

## Fix

### Before

```python
def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Skip preflight if every collected test lives under tests/unit/."""
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        if not item.nodeid.startswith("tests/unit/"):
            return True
    return False
```

### After

```python
_LIVE_PREFIXES: tuple[str, ...] = ("tests/contract/", "tests/sdet/")


def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Return True iff any collected item is under a live-MCP scope."""
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        if item.nodeid.startswith(_LIVE_PREFIXES):
            return True
    return False
```

The `_preflight` fixture docstring was also updated to describe the new short-circuit semantics (live-MCP scopes, not `tests/unit/`).

## Regression Tests Pinned

`tests/framework/unit/test_session_needs_preflight.py` (9 cases, pure-data, `SimpleNamespace` fakes — no pytest fixtures):

| # | Nodeids in collection | Expected | Rationale |
|---|-----------------------|----------|-----------|
| 1 | (empty) | `False` | Nothing to preflight for. |
| 2 | `tests/framework/unit/test_foo.py::test_x` (×2) | `False` | The regression — was `True` pre-fix. |
| 3 | `tests/framework/smoke/test_foo.py::test_x` | `False` | Framework smoke is pure-data. |
| 4 | `tests/framework/test_runner_renderer.py::test_x` | `False` | Runner self-tests are pure-data. |
| 5 | `tests/contract/test_homelab.py::test_y` | `True` | Live homelab-mcp + Ollama. |
| 6 | `tests/sdet/test_scenario.py::test_z` | `True` | Live homelab-mcp + Ollama (Phase 18). |
| 7 | N unit items + one `tests/contract/` item | `True` | Live scope wins. |
| 8 | N unit items + one `tests/sdet/` item | `True` | Live scope wins. |
| 9 | `tests/unit/test_old.py::test_x` (legacy prefix) | `False` | Defensive — `tests/unit/` is retired, NOT a live scope. |

TDD gate sequence:
- **RED** (commit `96d0708`): 3 cases fail (tests 2/3/4) — exactly the cases the pre-fix predicate gets wrong.
- **GREEN** (commit `b138bd2`): all 9 pass after the predicate is inverted.

## Acceptance — Reported Numbers

```
uv run pytest tests/framework -q   # MCPTF_CONFIG_FILE NOT set
=> 10 failed, 506 passed, 1 skipped, 16 deselected, 1 xfailed, 1 error in 15.03s
```

- **No preflight `returncode=2` exit** (verified by inspecting output for `MCP command ... not found on PATH` and `returncode=2` — no matches).
- **No `homelab-mcp` FileNotFoundError from the preflight gate** (Check 1 / Check 3 of `_preflight` never fires).
- **Test execution reaches collection + run** instead of bailing at session-start.
- **Test count: 506 passed + 1 skipped + 16 deselected + 1 xfailed = 524 executed cases** (plus 10 failed + 1 errored, all pre-existing — see Deferred Issues).
- **Duration: 15.03s** pytest-reported; ~17s wall.

## Deferred Issues (Out of Scope — Scope Boundary Rule)

10 failed + 1 errored test in `tests/framework` are **pre-existing** and reproduce against pre-fix code (verified via `git stash` round-trip during execution):

- `tests/framework/test_isolation.py::test_real_state_unchanged` — `FileNotFoundError: tests\docs\MIGRATION-v1-to-v2.md` (cwd-relative path assumption).
- `tests/framework/test_tool_config.py` — 4 cases, same module.
- `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens` — source-token drift.
- `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]` — doc-drift.
- `tests/framework/unit/test_migration_doc.py` — 4 cases, doc-content drift.

Tracked in `deferred-items.md` for a future operator-pass triage. **None are preflight-related** and none affect the success criteria for this quick task.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `96d0708` | `test` | RED: add 9 failing regression cases for the live-scope predicate. |
| `b138bd2` | `fix` | GREEN: invert predicate to `_LIVE_PREFIXES` allowlist; update docstrings. |
| `1ba103b` | `chore` | Move todo from `pending/` to `completed/` (closure). |

## Deviations from Plan

None — plan executed exactly as written, with one Rule-2-aligned addition: `deferred-items.md` was created to log the pre-existing out-of-scope `tests/framework` failures discovered during the acceptance run. This is the documented Scope Boundary behavior, not a deviation from intent.

## Cross-References

This closes the deferral repeatedly logged in:

- `.planning/phases/18-sdet-test-surface-typed-errors/18-02-...-SUMMARY.md` ("preflight forced `--noconftest` workaround")
- `.planning/phases/18-sdet-test-surface-typed-errors/18-03-...-SUMMARY.md`
- `.planning/phases/18-sdet-test-surface-typed-errors/18-08-...-SUMMARY.md`

Future framework-suite runs (CI or local) no longer need `MCPTF_CONFIG_FILE` set or `--noconftest` to pass collection.

## Self-Check: PASSED

- `src/mcp_test_framework/fixtures.py` — modified, `_LIVE_PREFIXES` present (verified by `git diff`).
- `tests/framework/unit/test_session_needs_preflight.py` — created, 9 tests, all pass.
- `.planning/todos/completed/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md` — present.
- `.planning/todos/pending/2026-05-13-fix-session-needs-preflight-nodeid-path-mismatch.md` — absent.
- Commits `96d0708`, `b138bd2`, `1ba103b` present in `git log`.
