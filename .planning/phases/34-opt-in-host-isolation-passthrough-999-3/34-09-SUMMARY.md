---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: "09"
subsystem: config-construction + audit-doc
tags: [gap-closure, isol-05, bare-config, validation-error, cr-02, audit]
dependency_graph:
  requires: [34-01, 34-04, 34-06]
  provides: [ISOL-05-SATISFIED]
  affects: [fixtures.py, session.py, _plugin.py, proxmox-scenario, audit-doc]
tech_stack:
  added: []
  patterns: [explicit-config-construction, cr-02-hoist, source-text-pin]
key_files:
  created:
    - tests/framework/unit/test_bare_config_construction.py
  modified:
    - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py
    - src/mcp_test_framework/fixtures.py
    - src/mcp_test_framework/test_code/session.py
    - src/mcp_test_framework/_plugin.py
    - .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md
    - tests/framework/unit/test_mcp_session_host_isolation_stash.py
decisions:
  - "Explicit Config(test_code=TestCodeConfig(generated_root='tests/test_code/_generated')) used at all four bare-Config() sites (ISOL-05 gap closure)"
  - "CR-02 option (b) implemented: check_black_box() + stash assignment hoisted inside try block in _plugin.py"
  - "34-BARE-CONFIG-AUDIT.md corrected: 'inherits strict default' claim removed, session.py:67 -> session.py:mcp_session throughout, ValidationError behavior documented"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-28"
  tasks: 4
  files: 6
---

# Phase 34 Plan 09: ISOL-05 Gap Closure — Explicit Config Construction Summary

**One-liner:** Replace four bare `Config()` call sites (which raise ValidationError since Phase 21.1) with `Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))`, hoist `_plugin.py` stash assignment inside the try (CR-02), and correct the audit doc false claims.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace bare Config() at two proxmox scenario sites | facadb2 | tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py |
| 2 | Replace bare Config() fallbacks in fixtures.py and session.py | 60306d0 | src/mcp_test_framework/fixtures.py, src/mcp_test_framework/test_code/session.py |
| 3 | CR-02 hoist — move stash assignment + black-box guard inside try in _plugin.py | 8122d3a | src/mcp_test_framework/_plugin.py |
| 4 | Add regression pin + correct audit doc | b786081 | tests/framework/unit/test_bare_config_construction.py, .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md |
| Deviation | Remove ISOL-05 planning ID from src/ comments + update stash pin | 1e6275f | fixtures.py, session.py, test_mcp_session_host_isolation_stash.py |

## Verification

- `uv run pytest tests/framework/ -q` → 788 passed, 0 failed
- `uv run pytest tests/framework/unit/test_bare_config_construction.py -q` → 3 passed
- No bare `cfg = Config()` in `src/mcp_test_framework/` or the proxmox scenario
- Audit doc `inherits strict default` count: 0
- `Config(test_code=TestCodeConfig(generated_root='tests/test_code/_generated')).host_isolation` prints `strict`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ISOL-05 planning ID forbidden in src/ by test_no_planning_ids_in_src gate**
- **Found during:** Post-task full suite run
- **Issue:** Comments in `fixtures.py:111` and `session.py:77` used `ISOL-05` which matches the locked planning-ID regex `ISOL-\d+`. The `test_no_planning_ids_in_src` gate hard-fails on any planning ID in `src/`.
- **Fix:** Reworded both comments to convey the same intent without the planning ID pattern.
- **Files modified:** `src/mcp_test_framework/fixtures.py`, `src/mcp_test_framework/test_code/session.py`
- **Commit:** 1e6275f

**2. [Rule 1 - Bug] test_mcp_session_module_source_routes_through_stash pin asserted bare Config() still present**
- **Found during:** Post-task full suite run
- **Issue:** `test_mcp_session_host_isolation_stash.py` had a source-text pin asserting `cfg\s*=\s*Config\(\)` (bare Config) in session.py. Task 2 correctly replaced the bare call with explicit construction, invalidating this pin.
- **Fix:** Updated the pin assertion to check for `cfg\s*=\s*Config\(\s*test_code\s*=\s*TestCodeConfig\(` (explicit construction); updated test docstring to reflect the Phase 34-09 behavior change.
- **Files modified:** `tests/framework/unit/test_mcp_session_host_isolation_stash.py`
- **Commit:** 1e6275f

## Known Stubs

None — all four call sites now use explicit construction. The proxmox module-level loader and fixture body are fully corrected.

## Threat Flags

No new external dependencies, network calls, or credential handling introduced. CR-02 hoist is a pure control-flow reorder (T-34-09-01 mitigated). No new threat surface.

## Self-Check: PASSED

All created files exist. All task commits present (facadb2, 60306d0, 8122d3a, b786081, 1e6275f).
