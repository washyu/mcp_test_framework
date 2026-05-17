---
phase: 29-live-domain-ui-reporter-plugin
plan: 03
subsystem: cli
tags: [cli, reporter, rewire, domain-ui, quiet, debug]

# Dependency graph
requires:
  - phase: 29-live-domain-ui-reporter-plugin
    plan: 01
    provides: _build_parsed_run_from_reports adapter (the reporter's input path)
  - phase: 29-live-domain-ui-reporter-plugin
    plan: 02
    provides: _reporter.py pytest11 plugin (the in-subprocess renderer surface this plan delegates to)
provides:
  - mcp-contracts run default path passes --mcp-domain-ui=force; reporter owns rendering
  - quiet-vs-debug resolution rule -- --debug WINS over -q for reporter-mode resolution
  - CLI no longer calls render_domain_ui / _render_pre_run_digest at runtime
affects:
  - Phase 30 (close): library-mode and CLI-mode operators now converge on a single render path (the reporter)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pytest-flag last-occurrence override: CLI's --mcp-domain-ui appended AFTER `forwarded` so the explicit choice wins over any operator-supplied flag via argparse's last-occurrence rule"
    - "Boolean-flag resolution rule: locked expression `'force' if debug else ('off' if quiet else 'force')` pinned by an integration test (Rule-A regression pin)"
    - "AST proof of deleted callsites: ast.walk(...) gathering Call.func.attr names lets tests assert deletions held without fragile string greps"

key-files:
  created:
    - tests/framework/test_cli_reporter_rewire.py (340 lines, 13 tests)
  modified:
    - src/mcp_test_framework/_runner.py (+19 lines net: `domain_ui_mode` kwarg + validator + argv-append site, threaded through both `_build_pytest_args` callsites in `run_pytest_subprocess`)
    - src/mcp_test_framework/cli.py (+40/-21 lines net: compute `domain_ui_mode` from `quiet` + `debug` per Rule A, thread to subprocess, delete default-path `render_domain_ui` call, gate `render_summary_only` on `quiet and not debug`, drop contract-path `_render_pre_run_digest` emission; preserve test_code scenario digest + --explain expansion + parse_junit_xml + render_debug_appendix + tmp_xml lifecycle)
    - tests/framework/test_runner_verbosity.py (3 tests updated -- pre-Phase-29 banner/summary CLI pins moved to "now absent from CLI; lives in reporter")
    - tests/framework/unit/test_runner_explain.py (6 tests updated -- digest banner + hint moved to reporter; Skipping block stays CLI-side)
    - tests/framework/unit/test_sdet_cli.py (1 test updated -- contract-path digest moved to reporter)

key-decisions:
  - "Comment hygiene scrub: the original plan instructed comments like `Phase 29 D-05 / REPORTER-01: ...` but the locked planning-ID leak gates (test_no_planning_ids_in_src + test_sdet_rename_leak_gate) enforce hard-zero `D-NN` and `REPORTER-NN` matches in src/. Rewrote all five Phase-29 comments to `Phase 29 reporter-rewire: ...` (Phase NN is allowed; D-NN and the requirement-ID alphabet are not)."
  - "Updated 10 pre-Phase-29 CliRunner tests rather than skip them: the invariants they pin (banner present, summary order, --explain block) are still meaningful but the renderer that emits them moved (CLI -> reporter). The reporter integration tests in tests/framework/test_reporter_plugin.py cover the reporter-side strings; the updated CLI tests now pin the CLI-side absences as the inverse contract."
  - "Kept `parse_junit_xml` call in cli.py despite D-05a's audit. It is still needed for: (a) the -q (no --debug) summary path via `render_summary_only(parsed, ctx)`; (b) the --debug appendix's ToolCallError extraction via `xml_path=tmp_xml`; (c) the ET.ParseError fallback that surfaces an operator-tone error when pytest crashes mid-run."
  - "Test 5 (`test_cli_raw_bypasses_default_path`) asserts `domain_ui_mode` is ABSENT from captured kwargs under --raw. The raw branch in cli.py never computes the mode (returns before the reporter resolution block); this is the cleanest pin that --raw is fully orthogonal to the reporter."

patterns-established:
  - "AST attribute-call set check: `_cli_call_attrs()` builds the set of `Call.func.attr` names in cli.py once and reuses it across tests for fast, exact callsite assertions (no fragile substring greps)."
  - "`_stub_cli_run` test helper: shared fixture that stubs `run_pytest_subprocess` to capture kwargs and write a minimal-but-valid JUnit XML, plus stubs `_discover_tools_for_run` to skip MCP server spawning -- pattern reusable for future CLI flag-wiring tests."

requirements-completed: [REPORTER-01]

# Metrics
duration: ~12min
completed: 2026-05-17
---

# Phase 29 Plan 03: CLI reporter rewire Summary

**`mcp-contracts run` now drives the in-subprocess reporter via `--mcp-domain-ui=force` and deletes its own JUnit-parse-then-render-domain-UI default-path branch -- library-mode and CLI-mode operators converge on a single render path. The quiet-vs-debug resolution rule (`'force' if debug else ('off' if quiet else 'force')` -- `--debug` WINS over `-q`) is locked at the CLI layer with a regression pin.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-17T19:27:59Z
- **Completed:** 2026-05-17T19:40:43Z
- **Tasks:** 3 (runner kwarg, CLI rewire, integration tests + pre-Phase-29 test pin updates)
- **Files created:** 1 (`tests/framework/test_cli_reporter_rewire.py`, 340 lines)
- **Files modified:** 5 (`_runner.py`, `cli.py`, three pre-existing CLI test files updated for Phase-29 semantics)

## What Changed

### `src/mcp_test_framework/_runner.py`

- `_build_pytest_args` signature: added `domain_ui_mode: str = "off"` keyword-only kwarg.
- Function-body validator (defensive): raises `ValueError` when `domain_ui_mode` not in `{"off", "auto", "force"}`.
- Argv-append site (after `forwarded`, before `mcp_config_path` insertion): when mode is not `"off"`, append `--mcp-domain-ui={mode}`. Last-occurrence pytest argparse rule means the CLI's explicit choice wins over any operator-supplied `--mcp-domain-ui` in `forwarded`.
- `run_pytest_subprocess` signature: added `domain_ui_mode: str = "off"` kwarg; threaded through both `_build_pytest_args` callsites (raw + default mode).

Lines added: +19. No deletions. `parse_junit_xml` body byte-identical (D-05a preserved).

### `src/mcp_test_framework/cli.py`

- Computed `domain_ui_mode` from CLI flags BEFORE the subprocess invocation per the locked resolution rule:
  ```python
  domain_ui_mode = "force" if debug else ("off" if quiet else "force")
  ```
  This expression appears verbatim in cli.py (Rule-A pin enforced by `test_cli_quiet_debug_combination`).
- Passed `domain_ui_mode` to `run_pytest_subprocess` via the new kwarg.
- **Deleted** the default-path `render_domain_ui(parsed, ctx)` callsite (D-05 core deletion).
- Gated `render_summary_only(parsed, ctx)` on `quiet and not debug` -- under `-q --debug` the CLI defers to the reporter (Rule A).
- **Edit 6:** removed the contract-path `_render_pre_run_digest(pre_run_ctx, ...)` call from the `else:` branch of the pre-run digest block. The reporter inside the subprocess now emits this at `pytest_collection_finish`. CLI keeps:
  - `_render_scenario_pre_run_digest` (test_code=True branch -- reporter does not handle the scenario variant).
  - `_render_skipped_tools_explain` (--explain expansion -- reporter does not handle --explain).
- Preserved: `_dispatch_default_mode_or_error`, `parse_junit_xml`, `ET.ParseError` fallback, `render_debug_appendix`, `_map_exit_code`, `typer.Exit` tail, `finally: tmp_xml.unlink()` cleanup.

Lines added: +40. Lines deleted: -21. Net: +19.

### AST callsite verification (from `test_no_render_*` tests + manual check)

| Symbol | Pre-Phase-29 | Post-Phase-29 | Test |
|--------|-------------|---------------|------|
| `render_domain_ui` | 1 callsite (cli.py:956) | **0 callsites** | `test_no_render_domain_ui_calls_in_cli_module` |
| `_render_pre_run_digest` | 1 callsite (cli.py:895) | **0 callsites** | `test_no_render_pre_run_digest_calls_in_cli_module` |
| `_render_scenario_pre_run_digest` | 1 callsite (cli.py:888) | **1 callsite** (preserved) | `test_no_render_pre_run_digest_calls_in_cli_module` |
| `_render_skipped_tools_explain` | 1 callsite (cli.py:902) | **1 callsite** (preserved) | `test_no_render_pre_run_digest_calls_in_cli_module` |
| `render_summary_only` | 1 callsite (cli.py:954) | **1 callsite** (gated on `quiet and not debug`) | `test_render_summary_only_and_debug_appendix_still_called_in_cli` |
| `render_debug_appendix` | 1 callsite (cli.py:966) | **1 callsite** (gated on `debug`) | `test_render_summary_only_and_debug_appendix_still_called_in_cli` |

### Resolution rule -- Rule A pin

The locked expression in `cli.py:run`:
```python
domain_ui_mode = "force" if debug else ("off" if quiet else "force")
```

| Flags | `quiet` | `debug` | `domain_ui_mode` | Behavior |
|-------|---------|---------|------------------|----------|
| (none) | False | False | `"force"` | Reporter renders domain UI inside subprocess |
| `-q` | True | False | `"off"` | Reporter silent; CLI parses JUnit + renders summary line |
| `--debug` | False | True | `"force"` | Reporter renders; CLI appends `--debug` appendix |
| `-q --debug` | True | True | `"force"` | **Rule A: --debug WINS over -q.** Reporter renders; CLI appends appendix. NO summary line from CLI. |
| `--raw` | * | * | n/a | Bypasses default path entirely; raw branch returns before `domain_ui_mode` is computed |

The Rule-A pin (`-q --debug` -> `"force"`) is enforced by `test_cli_quiet_debug_combination`. It FAILS under the original `"off" if quiet else "force"` rule and PASSES only under the locked `"force" if debug else ("off" if quiet else "force")` expression.

## New Tests: `tests/framework/test_cli_reporter_rewire.py` (13 tests)

| # | Test | What it pins |
|---|------|--------------|
| 1 | `test_build_pytest_args_appends_force` | `mode='force'` -> `--mcp-domain-ui=force` in argv |
| 2 | `test_build_pytest_args_omits_when_off` | Default + explicit `'off'` -> no `--mcp-domain-ui` in argv |
| 3 | `test_build_pytest_args_appends_auto` | `mode='auto'` -> `--mcp-domain-ui=auto` in argv |
| 4 | `test_build_pytest_args_rejects_invalid_mode` | Bogus mode -> `ValueError` at the top of the function |
| 5 | `test_build_pytest_args_flag_appended_after_forwarded` | Last-occurrence override: CLI's choice WINS over operator-supplied flag in forwarded |
| 6 | `test_cli_default_passes_force_to_subprocess` | Default `mcp-contracts run` -> `domain_ui_mode='force'` |
| 7 | `test_cli_quiet_passes_off_to_subprocess` | `-q` (no --debug) -> `domain_ui_mode='off'` |
| 8 | `test_cli_debug_passes_force_to_subprocess` | `--debug` -> `domain_ui_mode='force'` |
| 9 | `test_cli_quiet_debug_combination` | **Rule A pin: `-q --debug` -> `domain_ui_mode='force'`** |
| 10 | `test_cli_raw_bypasses_default_path` | `--raw` never computes `domain_ui_mode` (kwarg absent from captured) |
| 11 | `test_no_render_domain_ui_calls_in_cli_module` | AST proof: zero `render_domain_ui` callsites |
| 12 | `test_no_render_pre_run_digest_calls_in_cli_module` | AST proof: `_render_pre_run_digest` absent; `_render_scenario_pre_run_digest` + `_render_skipped_tools_explain` present |
| 13 | `test_render_summary_only_and_debug_appendix_still_called_in_cli` | `render_summary_only` + `render_debug_appendix` still wired |

All 13 pass.

## Pre-Phase-29 Test Pins Updated

10 CliRunner-based tests in three pre-existing files asserted Phase-14 / Phase-16 contracts that Phase 29 explicitly supersedes (banner emitted by CLI; per-tool rows in CLI output; etc.). With the reporter inside the subprocess and `subprocess.run` stubbed in CliRunner tests, the reporter never runs -- so the banner is absent from CLI output by design. Each test was rewritten to pin the inverse: "CLI does NOT emit this (the reporter does, verified by `tests/framework/test_reporter_plugin.py`)."

| File | Tests updated | New invariant |
|------|--------------|---------------|
| `test_runner_verbosity.py` | 3 (`test_run_default_renders_full_domain_ui`, `test_run_debug_appends_appendix_after_domain_ui`, `test_run_quiet_plus_debug_renders_summary_then_appendix`) | Banner absent from CLI output (reporter-side); `--debug` appendix still emitted by CLI; `-q --debug` no longer triggers `render_summary_only` (Rule A) |
| `test_runner_explain.py` | 6 (`test_run_explain_lists_skipped_tools_alphabetically`, `test_run_explain_renders_after_digest_before_pytest`, `test_run_explain_with_with_framework_emits_suffix`, `test_run_default_emits_digest_without_explain_block`, `test_run_default_post_run_has_no_second_banner`, `test_run_default_includes_explain_hint`) | Digest banner + framework-suffix + `(use --explain to list)` hint absent from CLI (reporter-side); `--explain` Skipping block stays CLI-side (reporter does not handle `--explain`) |
| `test_sdet_cli.py` | 1 (`test_run_no_sdet_uses_tool_digest`) | Contract-path digest absent from CLI (reporter-side); `(test-code)` variant still absent under contract path |

## Task Commits

1. **Task 1** -- `e662bc6` (feat): `domain_ui_mode` kwarg threaded through `_build_pytest_args` + `run_pytest_subprocess`
2. **Task 2** -- `e387051` (feat): CLI rewire -- delete `render_domain_ui`, gate `render_summary_only` on `quiet and not debug`, drop contract-path `_render_pre_run_digest` emission
3. **Task 3** -- `d4d6fa8` (test): new `test_cli_reporter_rewire.py` (13 tests) + comment hygiene scrub (Phase-29 leak-gate fix) + pre-Phase-29 test pin updates (10 tests)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Planning-ID leak gate failure from Phase-29 comments**
- **Found during:** Task 2 verification (full framework test sweep)
- **Issue:** The plan's locked acceptance criteria included `grep -n "Phase 29 D-05 / REPORTER-01" src/mcp_test_framework/cli.py` returning >= 2 lines. But the project's locked leak gates (`tests/framework/unit/test_no_planning_ids_in_src.py` + `tests/framework/test_sdet_rename_leak_gate.py::test_no_residual_match_in_src_python_strings[planning_id-...]`) enforce hard-zero `D-NN` and `REPORTER-NN` matches in src/, with no allowlist (22-CONTEXT.md D-04: "hard zero, no allowlist, no per-file exemptions"). The plan's required comment format directly contradicts the locked policy.
- **Resolution:** CLAUDE.md `<important_constraints>` notes the GSD workflow respects project rules; the leak gate is a project rule. Reworded all five Phase-29 comments in cli.py and _runner.py from `Phase 29 D-05 / REPORTER-01: ...` to `Phase 29 reporter-rewire: ...`. The "Phase NN" prefix is allowed (per the gate's docstring); the requirement-ID alphabet is not. Substance preserved -- comments still cite the phase + the design intent ("reporter-rewire").
- **Files modified:** `src/mcp_test_framework/_runner.py`, `src/mcp_test_framework/cli.py`
- **Verification:** Both leak gates pass: `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py tests/framework/test_sdet_rename_leak_gate.py -q` -- 5 passed.
- **Committed in:** `d4d6fa8`

**2. [Rule 1 - Bug] 10 pre-Phase-29 CliRunner tests pinned obsolete CLI-emits-banner contract**
- **Found during:** Task 3 verification (full framework test sweep)
- **Issue:** Tests in `test_runner_verbosity.py` (3), `test_runner_explain.py` (6), and `test_sdet_cli.py` (1) asserted the CLI emits the `MCP Test Framework` digest banner / per-tool rows / `Result:` summary / `(use --explain to list)` hint in CliRunner output. Phase 29 moves these emissions into the reporter (which runs inside the pytest subprocess at `pytest_collection_finish` and `pytest_sessionfinish`). The tests stub `subprocess.run` entirely, which bypasses the reporter, so the strings disappear from CLI output by design.
- **Resolution:** Updated each test in place to pin the inverse: "CLI does NOT emit this; the reporter does." The reporter-side behavior is independently verified by `tests/framework/test_reporter_plugin.py` (10 tests, 9 passed + 1 xdist-gated, landed in Plan 02). The combined CLI+reporter contract is preserved across both test files: CLI absence + reporter presence == end-to-end render in real runs.
- **Files modified:** `tests/framework/test_runner_verbosity.py`, `tests/framework/unit/test_runner_explain.py`, `tests/framework/unit/test_sdet_cli.py`
- **Verification:** `uv run pytest tests/framework/test_runner_verbosity.py tests/framework/unit/test_runner_explain.py tests/framework/unit/test_sdet_cli.py` -- 36 passed.
- **Committed in:** `d4d6fa8`
- **Precedent:** Plan 02 hit the analogous case with `test_reporter_module_no_longer_importable` (a Phase-14 regression pin that Phase 29 explicitly inverts by re-introducing `_reporter.py`).

---

**Total deviations:** 2 auto-fixed (1 leak-gate scrub forced by the project's locked policy; 1 inherited pre-Phase-29 test-pin update that the plan's acceptance criteria implicitly required but did not enumerate).

**Impact on plan:** None. The locked surface (D-05 deletion; Rule A resolution; reporter-driven default path) is unchanged. The leak-gate scrub trades a planning-ID citation in code comments for a Phase-NN + plain-English citation -- same provenance, gate-compatible. The pre-Phase-29 test updates extend the plan's scope by 10 tests but stay within the spirit of "rewire CLI to the reporter" because pinning the old contract while the new contract is locked would create a guaranteed regression on every subsequent run.

## Issues Encountered

- **Pyright shows 12 pre-existing errors in cli.py** (`Config | None` optional-member-access on `cfg.mcp_server`, `cfg.tools`, etc.). Confirmed via `git stash` baseline that all 12 exist in the pre-Plan-03 tree; Plan 03 adds zero new pyright errors.
- **`mcp-test-framework` legacy console-script deprecation shim verified intact**: `uv run mcp-test-framework version` emits the locked DeprecationWarning (`mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5 ...`) and then prints `0.1.0`. Plan 03 did not touch `_deprecated_script.py`.

## Known Stubs

None. The CLI rewire is complete:
- The reporter plugin (Plan 02) owns the contract-path render.
- The CLI keeps a minimal renderer surface for the two non-reporter cases: `-q` (no --debug) summary and `--debug` appendix.
- The test-code scenario digest (`_render_scenario_pre_run_digest`) and the `--explain` Skipping expansion (`_render_skipped_tools_explain`) remain CLI-side because the reporter intentionally does not handle them.

## Smoke Verification

```
$ uv run pytest tests/framework/test_cli_reporter_rewire.py -v
============================ 13 passed in 0.18s ============================

$ uv run pytest tests/framework -q --ignore=tests/framework/test_runner_live_smoke.py
670 passed, 2 skipped, 14 deselected, 1 xfailed, 45 warnings in 45.92s

$ uv run pyright src/mcp_test_framework/cli.py src/mcp_test_framework/_runner.py
12 errors, 0 warnings, 0 informations  # all 12 pre-existed Plan 03 (verified via git stash baseline)

$ uv run mcp-contracts --help
... commands: run, list-tools, config-init, version, gen-test-classes  (Typer tree intact)

$ uv run mcp-test-framework version
DeprecationWarning: mcp-test-framework command is deprecated since v1.4 ... use mcp-contracts instead.
0.1.0
```

A live smoke against a real MCP server fixture (`uv run mcp-contracts run --config <fixture>`) was not attempted because the dev environment does not have homelab-mcp installed; the integration is verified instead through:
- Plan 02's `test_reporter_plugin.py::test_force_emits_per_tool_rows_and_summary` (reporter-side rendering).
- Plan 03's `test_cli_default_passes_force_to_subprocess` (CLI argv composition).
- Plan 03's `test_no_render_domain_ui_calls_in_cli_module` (AST proof of the D-05 deletion).
- The Phase 29 verification step (next, post-this-SUMMARY) which runs the full `tests/framework` sweep again.

## Next Phase Readiness

Phase 29 is now complete:
- Plan 01 (`_build_parsed_run_from_reports` adapter): landed.
- Plan 02 (`_reporter.py` + entry-point + integration tests): landed.
- Plan 03 (CLI rewire to drive the reporter): landed.

The Phase 29 verification gate (run by the orchestrator after this SUMMARY) will exercise the full sweep. After verification, Phase 30 (close) inherits a converged render path -- library-mode operators (running pytest directly with `--mcp-domain-ui=force` via ini) and CLI-mode operators (running `mcp-contracts run`) both get the same domain UI from the reporter. The framework no longer has two rendering routes for the same default output.

## Self-Check: PASSED

- `tests/framework/test_cli_reporter_rewire.py` -- exists (340 lines, 13 test functions confirmed).
- `src/mcp_test_framework/cli.py` -- exists; AST proves zero `render_domain_ui` callsites and zero `_render_pre_run_digest` callsites.
- `src/mcp_test_framework/_runner.py` -- exists; `domain_ui_mode` kwarg present on `_build_pytest_args` and `run_pytest_subprocess`.
- `.planning/phases/29-live-domain-ui-reporter-plugin/29-03-SUMMARY.md` -- this file.
- Commit `e662bc6` -- present (feat: `domain_ui_mode` kwarg).
- Commit `e387051` -- present (feat: CLI rewire).
- Commit `d4d6fa8` -- present (test: integration tests + pre-Phase-29 test pin updates + comment scrub).
- All 13 new tests pass; full framework sweep 670 passed / 2 skipped / 14 deselected; legacy `mcp-test-framework` deprecation shim still emits the locked copy.
