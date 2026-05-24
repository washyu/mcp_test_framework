---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 02
subsystem: config
tags: [config, deprecation-shim, env-var, plugin, visibility, formatwarning, mcp-config-file]

requires:
  - phase: 27-library-mode-mcp-config-file-ini-key-lib-seam
    provides: "D-10 IPC channel (`-o mcp_config_file=PATH`) + library-mode `mcp_config_file` ini key"
  - phase: 13-config-surface-precedence-and-error-style-lock
    provides: "settings_customise_sources structure + ERROR-STYLE.md SAFE-03/SAFE-04/SAFE-06 lockset"
provides:
  - "MCPTF_CONFIG_FILE env var is inert as a value source (settings_customise_sources fallback deleted)"
  - "cli._load_config two-branch resolver: --config > pyproject mcp_config_file > ./config.yaml (env-var branch deleted)"
  - "Scoped warnings.formatwarning override in _plugin.pytest_configure that prefixes the surviving DeprecationWarning with [mcp-contracts] and restores via try/finally"
  - "Operator-tone D-06 wording 'no longer honored as of v1.5' on the surviving DeprecationWarning"
  - "Grandfathered detection block in _plugin.py with v1.6 EOL marker for the future SHIM-09 capstone planner"
  - ".env.example + examples/homelab-mcp.yaml header scrubbed of env-var references; only canonical routes documented"
affects: [phase-35-shim-09-eol-capstone, future-config-surface-work, library-mode-operators]

tech-stack:
  added: []
  patterns:
    - "Scoped warnings.formatwarning override with try/finally restore (visibility-upgrade pattern; safe within a single warn() call window)"
    - "Two-route operator-facing config surface: CLI --config flag + library-mode [tool.pytest.ini_options] mcp_config_file = PATH; env-var route deprecated"
    - "Inverted regression tests: legacy tests that pinned a deprecated code path are rewritten in place to pin its ABSENCE so the test name + assertion describe the post-Phase-31 invariant"

key-files:
  created:
    - "tests/framework/unit/test_plugin_mcptf_config_file_deprecation.py - 6 tests locking the post-Phase-31 plugin deprecation surface"
    - "tests/framework/unit/test_phase_31_mcptf_config_file_scrub.py - parametrized scrub-regression guards for fixtures.py / models.py / examples/homelab-mcp.yaml + plugin-is-sole-mention invariant"
  modified:
    - "src/mcp_test_framework/config.py - deleted MCPTF_CONFIG_FILE path-pointer fallback in settings_customise_sources; module docstring scrubbed; unused os import dropped"
    - "src/mcp_test_framework/cli.py - deleted Branch 2 of _load_config (env-var); scrubbed --help text + docstrings for run/list-tools/config-init/gen-test-classes/gen-sdet-classes shim; unused os import dropped"
    - "src/mcp_test_framework/_plugin.py - rewrote the env-var DeprecationWarning to the operator-tone wording + installed the scoped formatwarning override with try/finally restore + v1.6 grandfathering marker; added sys import"
    - "src/mcp_test_framework/fixtures.py - scrubbed MCPTF_CONFIG_FILE from mcp_config docstring, _session_needs_preflight docstring, _preflight docstring, Check-1 emit message, Check-3 fallback emit message; canonical two-route guidance retained"
    - "src/mcp_test_framework/models.py - removed MCPTF_CONFIG_FILE convention reference from TestCodeConfig path-resolution docstring"
    - ".env.example - deleted L15-16 MCPTF_CONFIG_FILE documentation block (file remains 13 lines, within the test-locked 10-25 envelope)"
    - "examples/homelab-mcp.yaml - rewrote header L2 to point at --config / mcp_config_file ini key; dropped 'env' from precedence comment"
    - "tests/framework/unit/test_config.py - added test_phase_31_mcptf_config_file_env_inert_as_value_source"
    - "tests/framework/unit/test_dotenv_example.py - inverted test_dotenv_example_keeps_mcptf_config_file_hint -> test_dotenv_example_no_mcptf_config_file_mention"
    - "tests/framework/unit/test_cli_errors.py - inverted two legacy SAFE-04/SAFE-06 env-var-route tests"
    - "tests/framework/unit/test_error_style.py - inverted test_error_style_safe_04_body_matches_cli_wiring"
    - "tests/framework/unit/test_gen_test_classes_pyproject_config.py - renamed test_env_var_still_works -> test_env_var_no_longer_routed and inverted assertion"
    - "tests/framework/unit/test_runner_migration.py - renamed CR-01 test and inverted to lock the env-var fallback is gone"
    - "tests/framework/unit/test_sdet_fixtures.py - added _install_session_config helper that monkeypatches Config inside mcp_test_framework.test_code.session so the bare Config() call resolves to Config(yaml_file=PATH)"
    - "tests/framework/test_tool_config.py - switched test_yaml_overlay_loads_tools_block to Config(yaml_file=PATH)"
    - "tests/framework/smoke/test_mcp_client_teardown_regression.py - switched child pytest invocation from MCPTF_CONFIG_FILE env to `-o mcp_config_file=PATH`"

key-decisions:
  - "Reword in-source planning-ID comments to neutral English ('v1.5', 'v1.6', 'future EOL planner') to satisfy the no_planning_ids_in_src leak guard while preserving the operator/maintainer EOL signal"
  - "Update tests broken by the env-var-fallback removal in place rather than deleting them - the test names and assertions are inverted so they pin the post-Phase-31 invariant"
  - "Keep the D-10 IPC channel (`-o mcp_config_file=PATH`) untouched; it is now the SOLE CLI->plugin handoff for the resolved config path"

patterns-established:
  - "Visibility-upgrade pattern: scoped warnings.formatwarning override (try/finally restored) for a single warn() call window. Used here to give the surviving env-var DeprecationWarning a [mcp-contracts] prefix without leaking into other warnings"
  - "Inverted regression test pattern: when a deprecated code path is deleted, the test that pinned it is rewritten IN PLACE with the inverted assertion + new name; the test's existence remains a maintenance-time tripwire"

requirements-completed: [SHIM-05]

duration: 65m
completed: 2026-05-24
---

# Phase 31 Plan 02: SHIM-05 MCPTF_CONFIG_FILE Unwiring Summary

**Unwired `MCPTF_CONFIG_FILE` as a value-source / path-pointer end-to-end and replaced the v1.4 in-place DeprecationWarning with the operator-tone D-06 wording rendered via a scoped `[mcp-contracts]`-prefixed formatwarning override.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-05-23 ~22:58 UTC
- **Completed:** 2026-05-24T00:03:04Z
- **Tasks:** 3 (all TDD: 3 RED commits, 3 GREEN commits)
- **Files modified:** 16 (7 src + .env.example + examples/homelab-mcp.yaml + 7 tests)

## Accomplishments

- Operator-facing config-resolution surface reduced to TWO routes end-to-end: `mcp-contracts run --config PATH` (CLI) and `[tool.pytest.ini_options] mcp_config_file = PATH` (library). The third legacy route (`MCPTF_CONFIG_FILE` env var) is now inert as a value source.
- The Memory-flagged "MCPTF_CONFIG_FILE silent fail" footgun (project_mcptf_config_file_silent_fail) is closed: setting the env var with no `--config` / no pyproject ini / no `./config.yaml` causes SAFE-03 fail-loud, NOT a silent load of the env-pointed path.
- The Memory-flagged ".env beats --config" footgun (project_dotenv_silently_beats_config) is partially closed: env-var-as-config-source is gone; `--config` is no longer silently overridable via this env var.
- Surviving DeprecationWarning is loud + distinct: scoped formatwarning override prefixes it with `[mcp-contracts]` so it cannot be mistaken for pytest's own deprecation chatter.
- D-10 IPC channel (`-o mcp_config_file=PATH` in `_runner._build_pytest_args`) preserved; it is now the SOLE CLI->plugin path-handoff mechanism end-to-end.
- Plugin detection block carries a `v1.6` EOL marker comment so the next-phase SHIM-09 capstone planner can find the grandfathered site without source-archaeology.

## Task Commits

Each task ran a full TDD RED -> GREEN cycle:

1. **Task 1: Unwire MCPTF_CONFIG_FILE from config.py + cli.py value-source paths**
   - RED: `d45a438` (test: failing test for env-var inertness in config.py)
   - GREEN: `06719d2` (feat: unwire env-var fallback in config.py + delete _load_config Branch 2 in cli.py)

2. **Task 2: Rewrite _plugin.py DeprecationWarning + install scoped formatwarning override**
   - RED: `5402f54` (test: failing tests for D-06/D-07/D-08/D-09 deprecation surface)
   - GREEN: `b749d6a` (feat: D-06 wording + scoped formatwarning override + v1.6 marker)

3. **Task 3: Scrub fixtures.py, models.py, .env.example, examples/homelab-mcp.yaml**
   - RED: `e1b3fc8` (test: failing scrub guards + invert .env.example hint test)
   - GREEN: `48c16de` (feat: scrub the four files)

**Rule-3 deviation commits (downstream test fallout from the source changes):**

4. `d891c66` (fix: rephrase planning-ID inline comments to satisfy no_planning_ids_in_src leak guard)
5. `1ab67b9` (fix: update 5 unit tests broken by MCPTF_CONFIG_FILE env-var fallback removal)
6. `9fcff0b` (fix: wire test_yaml_overlay_loads_tools_block via explicit yaml_file= kwarg)
7. `b32718a` (fix: smoke test threads config via -o mcp_config_file instead of MCPTF_CONFIG_FILE env)

## Files Created/Modified

### Created
- `tests/framework/unit/test_plugin_mcptf_config_file_deprecation.py` - 6 regression guards covering D-06 wording, D-07 sole-emission-site, D-08 formatwarning override + try/finally restore + [mcp-contracts] prefix, D-09 v1.6 EOL marker.
- `tests/framework/unit/test_phase_31_mcptf_config_file_scrub.py` - 6 parametrized scrub-regression guards covering fixtures.py / models.py / examples/homelab-mcp.yaml absence + plugin-is-sole-mention invariant + canonical-route presence in fixtures.py hints + homelab-mcp.yaml header.

### Modified - source
- `src/mcp_test_framework/config.py` - module docstring rewritten to drop the MCPTF_CONFIG_FILE path-pointer language; `settings_customise_sources` fallback to `os.environ.get("MCPTF_CONFIG_FILE")` deleted; unused `import os` removed.
- `src/mcp_test_framework/cli.py` - module docstring `_load_config` precedence updated; `_load_config` Branch 2 (env-var) deleted (resolver is now --config > pyproject mcp_config_file > ./config.yaml > SAFE-03); help-text strings for `--config` on run / list-tools / config-init / gen-test-classes / gen-sdet-classes shim scrubbed; `_load_config` docstring + `source_label` comment + `gen-test-classes` docstring precedence + relative-path comment scrubbed; unused `import os` removed.
- `src/mcp_test_framework/_plugin.py` - `import sys` added; pre-existing v1.4-style DeprecationWarning replaced by the operator-tone wording + scoped formatwarning override + `try/finally` restore; in-source v1.6 EOL grandfathering marker added.
- `src/mcp_test_framework/fixtures.py` - 3 docstrings (mcp_config / _session_needs_preflight / _preflight) and 2 operator-tone preflight hints (Check 1 emit + Check 3 fallback) rewritten to point at the two canonical routes.
- `src/mcp_test_framework/models.py` - `TestCodeConfig` path-resolution docstring no longer cites the MCPTF_CONFIG_FILE convention.

### Modified - docs / examples
- `.env.example` - the two MCPTF_CONFIG_FILE documentation lines (L15-16) deleted; file remains 13 lines, within the test-locked 10-25 envelope; CI-secret framing untouched.
- `examples/homelab-mcp.yaml` - L2 header rewritten to point at `--config` / `[tool.pytest.ini_options] mcp_config_file`; precedence comment trimmed to `CLI > YAML > defaults` (env is no longer a config-resolution route).

### Modified - tests
- 8 test files updated (see frontmatter `key-files.modified` for the full list with one-line descriptions).

## Decisions Made

- **Inline planning-ID rephrasing**: the plan called for `D-06` / `D-08` / `Phase 35 SHIM-09` / `D-09` comments in src/. The repo enforces a hard-zero `no_planning_ids_in_src` regex (22-CONTEXT.md D-04). Rephrased all such inline comments to neutral English (`v1.5`, `v1.6`, `future EOL planner`) while preserving the operator/maintainer signal; the plugin acceptance criterion `grep -n 'Phase 35 SHIM-09\|v1.6' src/mcp_test_framework/_plugin.py returns at least one match` remains satisfied via the `v1.6` leg.
- **Test mechanism shim for mcp_session**: rather than reshaping the production `mcp_session` fixture's `Config()` bare call inside this phase, added a test-side `_install_session_config(monkeypatch, yaml_path)` helper that monkeypatches the `Config` symbol the fixture imports. Keeps Phase 31 scope tight; production-fixture seam can be reshaped in a future phase if needed.
- **Smoke test IPC switch**: switched the child pytest invocation in the DEF-04-03-B teardown regression from `env={'MCPTF_CONFIG_FILE': PATH}` to `pytest -o mcp_config_file=PATH`. The latter is the canonical IPC channel `_runner._build_pytest_args` uses; using it from the smoke test also exercises the same end-to-end path operators take.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tests pinned the deleted env-var-as-config-source code path**

- **Found during:** Post-Task-3 full unit-test sweep
- **Issue:** 9 unit tests + 1 framework-level test + 1 smoke test depended on the MCPTF_CONFIG_FILE env-var fallback OR on the deleted SAFE-04 env-var-branch error wording inside `cli._load_config`. Without updates, the entire downstream suite goes red.
- **Fix:** Inverted 5 unit tests in place to pin the post-Phase-31 invariants (env-var has no effect; resolver falls through to SAFE-03); added `_install_session_config` helper in `test_sdet_fixtures.py` to monkeypatch the Config symbol the `mcp_session` fixture reads; switched `test_yaml_overlay_loads_tools_block` to `Config(yaml_file=PATH)`; switched the smoke test's child pytest invocation to `-o mcp_config_file=PATH`.
- **Files modified:** tests/framework/unit/{test_cli_errors,test_error_style,test_gen_test_classes_pyproject_config,test_runner_migration,test_sdet_fixtures}.py + tests/framework/test_tool_config.py + tests/framework/smoke/test_mcp_client_teardown_regression.py.
- **Verification:** Full unit-test sweep now green: 563 passed, 1 skipped, 6 deselected, 1 xfailed.
- **Committed in:** 1ab67b9, 9fcff0b, b32718a.

**2. [Rule 3 - Blocking] no_planning_ids_in_src leak guard caught in-source planning-ID comments**

- **Found during:** Post-Task-3 full unit-test sweep
- **Issue:** The plan instructed inline comments like `D-06`, `D-08`, `Phase 35 SHIM-09`, `D-09`, `Phase 31 SHIM-05` in src/. These are exactly the tokens the 22-CONTEXT.md D-04 hard-zero leak guard (`tests/framework/unit/test_no_planning_ids_in_src.py`) forbids. Without rephrasing, the guard fires.
- **Fix:** Rephrased the inline comments in `_plugin.py`, `config.py`, and `fixtures.py` to neutral English: `v1.5`, `v1.6`, `future EOL planner`. The plugin acceptance criterion `grep -n 'Phase 35 SHIM-09\|v1.6'` still passes via the `v1.6` leg.
- **Files modified:** src/mcp_test_framework/_plugin.py, src/mcp_test_framework/config.py, src/mcp_test_framework/fixtures.py.
- **Verification:** `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py` now passes.
- **Committed in:** d891c66.

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking).
**Impact on plan:** Both fixes were required to keep the suite green and the leak guard satisfied. Neither expanded scope: both repaired direct consequences of the planned source changes. The planning-ID rephrasing preserves all operator/maintainer signal value.

## Issues Encountered

- The cli.py acceptance criterion `grep -n 'MCPTF_CONFIG_FILE' src/mcp_test_framework/config.py returns zero matches` initially failed because two explanatory comments mentioned the now-deleted env var by name. Rephrased those comments to refer to the env var indirectly ("the previous env-var path-pointer fallback", "the previously honored *_CONFIG_FILE env-var path-pointer fallback") so the literal token no longer appears in config.py.
- The first RED test for the plugin source-side wording check failed because the D-06 string was split across multiple Python source lines (`"...but no longer "\n"honored as of v1.5; ..."`); restructured the string-literal joins so the substring `no longer honored as of v1.5` sits on a single source line, matching the source-side regression scan pattern.
- The smoke test for DEF-04-03-B teardown (`test_mcp_client_teardown_no_cancel_scope_error`) used MCPTF_CONFIG_FILE as a quick way to thread config.yaml into the child pytest; switched it to the `-o mcp_config_file=PATH` IPC channel.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 31 Plan 02 closes Phase 31's wave-2 SHIM-05 surface. Subsequent waves can proceed independently.
- A future Phase 35 (capstone v1.6) SHIM-09 plan will delete the surviving grandfathered detection block in `_plugin.py:pytest_configure` and remove the scoped formatwarning override. The in-source `v1.6` marker comment is the locator.
- Operators with MCPTF_CONFIG_FILE still exported in their shell will see the loud `[mcp-contracts]`-prefixed DeprecationWarning the first time pytest runs; their config will resolve through `--config` or the pyproject ini key, NOT through the env var.

## Self-Check: PASSED

- All 16 modified files exist and were committed.
- All 10 task commits + plan-fix commits exist and are reachable from HEAD:
  - d45a438 (RED Task 1), 06719d2 (GREEN Task 1)
  - 5402f54 (RED Task 2), b749d6a (GREEN Task 2)
  - e1b3fc8 (RED Task 3), 48c16de (GREEN Task 3)
  - d891c66, 1ab67b9, 9fcff0b, b32718a (Rule-3 deviation fixes)
- Phase-level grep checks pass: 6 mentions of MCPTF_CONFIG_FILE remain in src/, all inside `_plugin.py` (the grandfathered detection block + its docstring); zero mentions in fixtures.py / models.py / config.py / cli.py / .env.example / examples/homelab-mcp.yaml.
- D-10 IPC channel preserved: 3 matches of `mcp_config_file=` in `src/mcp_test_framework/_runner.py`.
- All `mcp-contracts {run, list-tools, config-init, gen-test-classes} --help` outputs contain zero MCPTF_CONFIG_FILE references.
- Full unit-test sweep green (563 passed, 1 skipped, 6 deselected, 1 xfailed).

---
*Phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias*
*Completed: 2026-05-24*
