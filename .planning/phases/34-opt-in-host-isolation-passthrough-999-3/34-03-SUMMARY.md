---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 03
subsystem: isolation-primitive
tags: [isolation-primitive, dispatcher, sdet-safety, tdd]
requires:
  - existing _build_isolated_env(isolated_home) in _isolation.py
provides:
  - _build_passthrough_env() -> dict[str, str]
  - _build_subprocess_env(mode, isolated_home) -> dict[str, str]
  - dispatcher seam for plan 34-04 spawn-site rerouting
affects:
  - src/mcp_test_framework/_isolation.py (module docstring + two new functions)
  - tests/framework/unit/test_isolation_dispatcher.py (new pin file)
tech-stack:
  added: []
  patterns:
    - "Caller-passes-data primitive (SDET-safety): dispatcher takes Literal[str] + Path|None, not Config"
    - "Defensive assert guard against caller drift"
    - "TDD RED/GREEN gate sequence (failing tests committed before implementation)"
key-files:
  created:
    - tests/framework/unit/test_isolation_dispatcher.py
  modified:
    - src/mcp_test_framework/_isolation.py
decisions:
  - "D-05 implemented: passthrough returns dict(os.environ) verbatim (no filter, no override)"
  - "D-07 implemented: dispatcher sibling of _build_isolated_env; legacy builder untouched"
  - "D-08 implemented: _isolation.py does not import config.py; dispatcher takes plain data"
  - "Open Question 6 resolved: strict + None isolated_home raises AssertionError"
metrics:
  duration: "~10 minutes"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 3
  framework_tests_passing: 765
completed: 2026-05-26
---

# Phase 34 Plan 03: Build passthrough env + dispatcher in `_isolation.py` Summary

**One-liner:** Added `_build_passthrough_env()` (literal `dict(os.environ)` copy) and `_build_subprocess_env(mode, isolated_home)` dispatcher to `_isolation.py` as siblings to the existing `_build_isolated_env`, keeping the strict-mode behavior byte-for-byte unchanged while introducing the opt-in passthrough seam for plan 34-04's spawn-site rerouting.

## Outcome

Plan 34-03 ships the isolation-primitive dispatcher seam that plans 34-04 (spawn-site reroute) and 34-05 (xdist clamp) will plumb through. Three load-bearing contract invariants are pinned by a new unit test file; the legacy strict-mode builder is preserved verbatim so existing callers in `fixtures.py:432` and `mcp_client.py:189` continue to work until plan 34-04 swaps them.

## Final Signatures (canonical -- pasted verbatim)

```python
def _build_passthrough_env() -> dict[str, str]:
    """Return a literal ``dict(os.environ)`` copy -- passthrough mode contract.

    Operator opted into ``host_isolation='passthrough'``: the spawned MCP subprocess
    sees the operator's full env, including HOME / USERPROFILE / TEMP and the
    operator's keyring backend. Nothing stripped, nothing injected. The hermetic
    property is explicitly traded for credential reachability.

    Framework-primitive contract (SDET-safety): this primitive takes no Config
    blob -- the caller passed the mode as plain data.
    """
    return dict(os.environ)


def _build_subprocess_env(
    mode: Literal['strict', 'passthrough'],
    isolated_home: Path | None,
) -> dict[str, str]:
    """Dispatch to the right env builder based on ``host_isolation`` mode.

    Spawn-site callers (``fixtures.py``, ``mcp_client.py``, ``_plugin.py``) pass
    ``cfg.host_isolation`` as ``mode`` and the resolved ``_isolated_home`` Path
    (or None under passthrough where the tempdir is unallocated).

    Strict mode REQUIRES an ``isolated_home`` -- the assertion is a defensive
    guard against caller drift; passthrough mode ignores it.
    """
    if mode == 'passthrough':
        return _build_passthrough_env()
    assert isolated_home is not None, (
        "_build_subprocess_env(mode='strict') requires isolated_home; "
        "caller must allocate the tempdir before invoking strict-mode dispatch"
    )
    return _build_isolated_env(isolated_home)
```

## New Module-Docstring Line (canonical wording for plan 34-08 docs)

```
- Isolation is ON BY DEFAULT (``host_isolation='strict'``) and disabled
  per-config-file via ``host_isolation='passthrough'``. The maintainer
  warning below stays in force for the strict allowlist; passthrough is
  all-or-nothing by design (no per-var widening, no per-tool toggle).
```

This replaces the previous `Isolation is ALWAYS-ON. No toggle, no ``--no-isolation`` CLI escape hatch.` line at L9.

## Confirmation Items

- **`_build_isolated_env` byte-for-byte unchanged**: signature `_build_isolated_env(isolated_home: Path) -> dict[str, str]` at L82; function body L97-108 untouched. Verified by Read of the final file at lines 82-108 against the pre-change file. Acceptance grep `^def _build_isolated_env\(isolated_home: Path\) -> dict\[str, str\]:` matches L82.
- **`_isolation.py` does NOT import `config.py`**: `grep -cE "from mcp_test_framework\.config|from \.config|from mcp_test_framework import config"` returns 0. SDET-safety framework-primitive contract is preserved -- the dispatcher takes `Literal['strict','passthrough']` + `Path | None`, never a Config blob.
- **Maintainer warning retained**: the `DO NOT widen _PASSTHROUGH_ALLOWLIST` block at L36-40 is unchanged and stays in force for the strict allowlist.

## Commits

| Hash       | Type | Message                                                                                |
| ---------- | ---- | -------------------------------------------------------------------------------------- |
| `b6ae8d1`  | test | test(34-03): add failing dispatcher contract tests (RED)                               |
| `89ba97e`  | feat | feat(34-03): add passthrough env builder + subprocess env dispatcher (GREEN)            |

## TDD Gate Compliance

- **RED gate**: commit `b6ae8d1` (test commit) adds three failing tests. Verified failure shape was `ImportError: cannot import name '_build_subprocess_env'` -- correct RED-phase failure (function not yet defined), not an AssertionError.
- **GREEN gate**: commit `89ba97e` (feat commit) makes all three tests pass. Verified via `uv run pytest tests/framework/unit/test_isolation_dispatcher.py -x` -> 3 passed.
- **REFACTOR gate**: skipped -- no cleanup pass needed (functions landed in their final shape).

Gate sequence valid: `test(...)` -> `feat(...)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed explicit `SEED-022` planning-ID token from new docstring**
- **Found during:** Task 2 (verification)
- **Issue:** The new `_build_passthrough_env` docstring cited `SEED-022:` verbatim as planned. The repo's planning-ID leak gate at `tests/framework/test_sdet_rename_leak_gate.py:145` AST-scans `src/mcp_test_framework/` Python string-Constants for `\b(SDET|...|SEED)-\d+\b` matches. `SEED-022` hit the gate; the gate's only exemption phrase is `SDET-safety`, not arbitrary `SEED-XXX` citations.
- **Fix:** Replaced the `SEED-022:` token with the doctrinal phrase `Framework-primitive contract (SDET-safety):` -- preserves the design intent (and the principle the doctrine names) without leaking a planning ID into operator-facing source surface. The PLAN.md and CONTEXT.md still reference SEED-022 as the doctrinal anchor; only the docstring narration changed.
- **Files modified:** `src/mcp_test_framework/_isolation.py` (lines 119-120 of final file).
- **Commit:** Folded into `89ba97e` rather than a separate fix commit; the issue was caught and fixed before the GREEN commit landed.
- **Why Rule 1 not Rule 4:** This is a leak-gate regression caused directly by this task's changes (a pre-existing regression gate that this addition would have broken). No architectural decision needed -- the gate's exemption phrase `SDET-safety` is already used elsewhere in the codebase for the same doctrinal cite.

## Verification Results

- `uv run pytest tests/framework/unit/test_isolation_dispatcher.py -x` -> 3 passed (the three new contract pins).
- `uv run pytest tests/framework/ -x` -> 765 passed, 2 skipped, 18 deselected, 1 xfailed. No regression in any framework self-test.
- Acceptance grep `^def _build_passthrough_env\(\) -> dict\[str, str\]:` -> matches L111.
- Acceptance grep `^def _build_subprocess_env\(` -> matches L125.
- Acceptance grep `^def _build_isolated_env\(isolated_home: Path\) -> dict\[str, str\]:` -> matches L82 (legacy unchanged).
- Acceptance grep `ON BY DEFAULT.*host_isolation='strict'` -> matches L9 (new docstring present).
- Acceptance grep `DO NOT widen` -> matches L36 (maintainer warning retained).
- Acceptance grep `from mcp_test_framework\.config|from \.config|from mcp_test_framework import config` -> 0 matches (no config import).
- Acceptance grep `Isolation is ALWAYS-ON` -> 0 matches (old docstring line removed).

## Self-Check: PASSED

- Created files exist:
  - `tests/framework/unit/test_isolation_dispatcher.py` -- FOUND
- Modified files exist:
  - `src/mcp_test_framework/_isolation.py` -- FOUND
- Commits exist (`git log --oneline --all | grep`):
  - `b6ae8d1` -- FOUND
  - `89ba97e` -- FOUND
