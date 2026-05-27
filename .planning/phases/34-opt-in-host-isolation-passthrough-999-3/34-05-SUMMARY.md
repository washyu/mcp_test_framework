---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 05
subsystem: pytest-plugin-hooks
tags: [pytest-xdist, plugin-hook, operator-tone-banner, host-isolation]
requires:
  - pytest_configure stash (plan 27, surface inherited)
  - Config.host_isolation field (plan 34-01)
  - _mcptf_formatwarning + _original_formatwarning module-level renderers (Phase 31 D-08)
provides:
  - "@pytest.hookimpl(tryfirst=True) on pytest_configure"
  - "xdist clamp: passthrough + -n N -> numprocesses=1, tx=['popen'], banner"
  - "strict-mode no-op (xdist parallelism preserved at operator's -n N)"
affects:
  - src/mcp_test_framework/_plugin.py
  - tests/framework/unit/test_xdist_clamp.py (new)
tech-stack:
  added: []
  patterns:
    - "Hook decorator ordering: @pytest.hookimpl(tryfirst=True) lands BEFORE xdist's @pytest.hookimpl(trylast=True) DSession registration"
    - "Dual-mutation invariant: config.option.numprocesses=1 AND config.option.tx=['popen'] (xdist NodeManager reads tx, not numprocesses)"
    - "warnings.warn(UserWarning) under _mcptf_formatwarning red-banner override; try/finally restores stdlib formatter"
    - "Stash-driven clamp guard reads getattr(config, '_mcp_contracts_config', None) so the block fires regardless of ini-arm path"
    - "TDD RED/GREEN gate sequence -- failing pin lands first, then implementation"
key-files:
  created:
    - tests/framework/unit/test_xdist_clamp.py
  modified:
    - src/mcp_test_framework/_plugin.py
decisions:
  - "Clamp reads from config._mcp_contracts_config stash via getattr, not from local cfg -- the block fires both when the ini-arm loads a Config AND when a Config is pre-stashed (test path, future direct injection)"
  - "pytest_configure early-return-on-empty-getini restructured into if/else so the clamp block at function tail runs unconditionally regardless of ini-arm execution"
  - "Banner category locked to UserWarning (not DeprecationWarning) -- the clamp is a runtime mode constraint, not a deprecation"
  - "Test capture switched from capsys to warnings.catch_warnings(record=True) -- mirrors the established pattern in test_plugin_mcptf_config_file_deprecation.py since pytest's warning filter intercepts the UserWarning before it reaches stderr"
metrics:
  duration: ~15 minutes
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 3
  framework_tests_passing: 784
completed: 2026-05-27
---

# Phase 34 Plan 05: Clamp pytest-xdist workers under host_isolation=passthrough Summary

**One-liner:** Decorated `pytest_configure` with `@pytest.hookimpl(tryfirst=True)` and appended a stash-driven clamp block that mutates BOTH `config.option.numprocesses=1` AND `config.option.tx=["popen"]` under `host_isolation='passthrough'` + `-n N`, emitting an operator-tone three-part `UserWarning` banner under the existing `_mcptf_formatwarning` red-banner override.

## Outcome

The operator who flips `host_isolation: passthrough` in `config.yaml` and runs `mcp-contracts run -n 4` now sees:

1. A single red `[mcp-contracts]` banner at session start with the three-part operator-tone shape (what happened / why / next step).
2. xdist's `NodeManager.setup_nodes()` reads `config.option.tx == ["popen"]` and spawns ONE worker -- the dual mutation closes the gap where mutating only `numprocesses` would have left 4 workers spawning.
3. The MCP subprocess inherits the operator's credentials and keyring (plan 34-03 + 34-04 surface), with serialized xdist execution so the keyring backend remains a single-owner resource.

The operator who runs the default `host_isolation: strict` mode (or who runs passthrough without `-n N`) sees no banner and no clamp. xdist parallelism is preserved end-to-end under strict.

## Final clamp block (verbatim)

```python
# Under host_isolation='passthrough', clamp pytest-xdist worker count to
# 1 so MCP subprocess spawns serialize. xdist's NodeManager reads
# config.option.tx (not numprocesses) -- BOTH must be mutated together.
# Hook ordering: this function is decorated @pytest.hookimpl(tryfirst=True)
# so the mutation lands BEFORE xdist's pytest_configure(trylast=True)
# registers DSession. Banner emitted as UserWarning under the
# _mcptf_formatwarning red-banner override; the clamp is a runtime mode
# constraint, not a deprecation.
stashed_cfg = getattr(config, "_mcp_contracts_config", None)
if (
    stashed_cfg is not None
    and stashed_cfg.host_isolation == "passthrough"
    and getattr(config.option, "numprocesses", 0)
):
    warnings.formatwarning = _mcptf_formatwarning
    try:
        warnings.warn(
            "xdist worker count clamped to 1\n"
            "\n"
            "host_isolation=passthrough serializes subprocess spawns so the "
            "operator's credentials remain a single-owner resource.\n"
            "\n"
            "next: switch to host_isolation=strict for parallel xdist runs",
            UserWarning,
            stacklevel=2,
        )
    finally:
        warnings.formatwarning = _original_formatwarning
    config.option.numprocesses = 1
    config.option.tx = ["popen"]
```

## Final `pytest_configure` decorator (verbatim)

```python
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register the `mcp_contract` marker and (if `mcp_config_file` ini is set)
    load the operator's YAML config, run the black-box guard, and stash the
    Config instance on `config._mcp_contracts_config` for the collection hook
    to consume.
    ...
    """
```

Decorator is `tryfirst=True` (NOT `trylast=True`, NOT absent). The clamp block lands BEFORE xdist's own `pytest_configure(trylast=True)` registers `DSession`, so the option-mutation propagates to `NodeManager.setup_nodes()` at `pytest_sessionstart(trylast=True)` time.

## Acceptance Criteria

All plan-level `<verification>` and `<success_criteria>` checks pass:

| Check                                                                   | Result |
| ----------------------------------------------------------------------- | ------ |
| `@pytest.hookimpl(tryfirst=True)` immediately precedes `pytest_configure` | PASS (line 160 → 161) |
| `cfg.host_isolation == 'passthrough'` clamp guard present (via stashed_cfg) | PASS |
| `config.option.numprocesses = 1` mutation present                       | PASS |
| `config.option.tx = ["popen"]` mutation present (load-bearing)          | PASS |
| Banner phrase "xdist worker count clamped to 1"                         | PASS |
| Banner phrase "single-owner resource"                                   | PASS |
| Banner phrase "host_isolation=strict for parallel xdist runs"           | PASS |
| `UserWarning` category present (NOT `DeprecationWarning`)               | PASS (2 occurrences -- import + warn) |
| `DeprecationWarning,` count unchanged (only MCPTF_CONFIG_FILE + sdet legacy detectors) | PASS (count = 2) |
| `uv run pytest tests/framework/unit/test_xdist_clamp.py -x`             | PASS (3 passed) |
| `uv run pytest tests/framework/ -x`                                     | PASS (784 passed, 2 skipped, 18 deselected, 1 xfailed) |
| `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x`  | PASS |

## Tasks Completed

| Task | Name                                                                       | RED Commit | GREEN Commit | Files                                       |
| ---- | -------------------------------------------------------------------------- | ---------- | ------------ | ------------------------------------------- |
| 1    | Write failing xdist clamp pin test (dual-mutation + banner)                | `ddd9d31`  | n/a (RED)    | `tests/framework/unit/test_xdist_clamp.py`  |
| 2    | Add `@pytest.hookimpl(tryfirst=True)` decorator + clamp block              | n/a (GREEN folded with test refactor) | `5d867e6` | `src/mcp_test_framework/_plugin.py`, `tests/framework/unit/test_xdist_clamp.py` |

## Commits (chronological)

| Hash       | Type | Message                                                                                |
| ---------- | ---- | -------------------------------------------------------------------------------------- |
| `ddd9d31`  | test | add failing pin for xdist clamp dual-mutation + banner (RED)                            |
| `5d867e6`  | feat | clamp xdist workers to 1 under host_isolation=passthrough (GREEN)                       |

## TDD Gate Compliance

Per-plan discipline observed: a `test(34-05): ...` commit lands before the `feat(34-05): ...` commit. RED commit's failure was verified (`assert 4 == 1` on the numprocesses check) before implementation. Gate sequence valid:

- Task 1 RED: `ddd9d31` (test commit creates 3 failing pins)
- Task 2 GREEN: `5d867e6` (feat commit makes all 3 GREEN + folds in a test-side refactor from `capsys` to `warnings.catch_warnings(record=True)`)

REFACTOR gate skipped -- code landed in its final shape.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test capture mechanism: capsys → warnings.catch_warnings(record=True)**

- **Found during:** Task 2 GREEN verification (test still failed even after clamp block landed; `assert "xdist worker count clamped to 1" in text` saw empty `text`).
- **Issue:** The plan's `<action>` step said "Capture stderr: `captured = capsys.readouterr()`". But pytest's warning filter intercepts `UserWarning` BEFORE it reaches the stderr stream that `capsys` captures. The mutation assertions passed but the banner-text assertions failed because the rendered banner went into pytest's warning recorder, not stderr.
- **Fix:** Switched from `capsys` to `warnings.catch_warnings(record=True)` with `warnings.simplefilter("always")` -- mirrors the established pattern in `tests/framework/unit/test_plugin_mcptf_config_file_deprecation.py` (Phase 31 SHIM-05 surface). The captured warning's `str(w.message)` carries the rendered banner text exactly as `warnings.warn` received it (which is what the operator's terminal renders via the `_mcptf_formatwarning` override at the actual session-start moment).
- **Files modified:** `tests/framework/unit/test_xdist_clamp.py` (3 test bodies + import).
- **Commit:** Folded into `5d867e6` (Task 2 GREEN) rather than a separate fix commit -- caught and fixed before the GREEN commit landed.
- **Why Rule 1 not Rule 4:** Test-capture-mechanism choice; no architectural decision required. The plan's `<acceptance_criteria>` requires the banner text be present and pinned; the mechanism for capturing the text was a planner-suggested default that didn't match pytest's actual warning-routing semantics. The existing `test_plugin_mcptf_config_file_deprecation.py` precedent (Phase 31) is the canonical pattern for this surface.

**2. [Rule 1 - Bug] pytest_configure early-return restructured into if/else**

- **Found during:** Task 2 GREEN initial implementation (clamp block at function tail never reached when `getini("mcp_config_file")` returned empty string).
- **Issue:** The plan called for placing the clamp at the "end of `pytest_configure`'s body (after `config._mcp_contracts_config = cfg` at L247)" with indent matching "the surrounding function-body indent (almost certainly 4 spaces)". But L204-206 has an early `return` when `getini` returns empty, which short-circuits the entire ini-load arm AND any clamp block placed after it. The test path pre-stashes a Config and sets `getini` to return `""` -- the early-return would have prevented the clamp from ever firing in tests AND in any future code path that pre-stashes via means other than the ini-arm.
- **Fix:** Replaced `if not raw: return` with `if raw:` wrapping the ini-arm body (load YAML, run black-box guard, stash). The clamp block at function tail reads `getattr(config, "_mcp_contracts_config", None)` -- so it sees the just-stashed Config OR any pre-stashed Config OR `None` (silent no-op when no Config is present at all).
- **Files modified:** `src/mcp_test_framework/_plugin.py` (lines 203-249, restructure; lines 251-280, append clamp block).
- **Commit:** Folded into `5d867e6` (Task 2 GREEN).
- **Why Rule 1 not Rule 4:** Structural refactor of an early-return into an if-arm; no behavioral change for the ini-driven operator path, and the clamp's stash-driven guard is the natural way to satisfy the plan's "clamp fires when passthrough mode is active" intent regardless of how the Config arrived on the pytest.Config object.

## Authentication Gates

None.

## Threat Flags

None. The five threat-register entries (T-34-05-01..05) are addressed as planned:

- **T-34-05-01 (DoS via concurrent keyring access):** mitigated. The dual mutation (`numprocesses=1` + `tx=["popen"]`) is pinned by `test_passthrough_clamps_xdist_numprocesses_and_tx`. xdist's `NodeManager.setup_nodes()` spawns one worker per `tx` entry; single-entry `tx` produces single-worker spawn.
- **T-34-05-02 (Tampering via hook ordering):** mitigated. `@pytest.hookimpl(tryfirst=True)` puts the clamp BEFORE xdist's `pytest_configure(trylast=True)` DSession registration, AND the dual `tx` + `numprocesses` mutation closes the load-bearing read-from-tx gap. Verified via xdist source citation in plan 34-05 RESEARCH Finding 1.
- **T-34-05-03 (Information disclosure -- silent serialization):** mitigated. Three-part operator-tone banner: what (`clamped to 1`) / why (`single-owner resource`) / next step (`switch to host_isolation=strict for parallel`). All three phrases pinned by `test_passthrough_clamps_xdist_numprocesses_and_tx`.
- **T-34-05-04 (Banner format drift):** mitigated. Reuses Phase 31 D-08 `_mcptf_formatwarning` red-banner surface via verbatim try/finally swap pattern. Pin tests assert the three locked phrases survive in the captured `UserWarning` message.
- **T-34-05-05 (`filterwarnings = ["error::UserWarning"]` in operator pyproject.toml):** accepted. Operator's choice; not the clamp's responsibility. RESEARCH Finding 6 spot-check confirmed the project's own pyproject.toml has no such filter.

## Known Stubs

None. The clamp is complete end-to-end. Downstream plans (34-07 `config-init` scaffold, 34-08 docs + live UAT smoke) consume this surface without re-touching it.

## Verification Results

- `uv run pytest tests/framework/unit/test_xdist_clamp.py -x` -> 3 passed (load-bearing pins all green).
- `uv run pytest tests/framework/ -x` -> 784 passed, 2 skipped, 18 deselected, 1 xfailed. No regressions; +3 new tests vs plan 34-04 (781 → 784).
- `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x` -> 1 passed. Planning-ID gate green; source comments in the new clamp block use plain language only.

## Self-Check: PASSED

- Created files exist:
  - `tests/framework/unit/test_xdist_clamp.py` -- FOUND
- Modified files exist:
  - `src/mcp_test_framework/_plugin.py` -- FOUND
- Commits exist (`git log --oneline`):
  - `ddd9d31` -- FOUND
  - `5d867e6` -- FOUND
- Acceptance criteria source-side regex checks: 9/9 PASS (decorator placement, clamp guard, dual mutation, banner phrases x3, UserWarning category, DeprecationWarning count unchanged).
- xdist clamp banner uses `UserWarning` (not `DeprecationWarning`). DeprecationWarning count in `_plugin.py` is unchanged at 2 (MCPTF_CONFIG_FILE detector + tests/sdet legacy detector).
- BOTH `config.option.numprocesses` AND `config.option.tx` are mutated together inside the clamp guard's if-block (load-bearing invariant preserved).
