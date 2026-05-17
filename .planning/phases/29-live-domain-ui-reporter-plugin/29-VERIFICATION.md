---
phase: 29-live-domain-ui-reporter-plugin
verified: 2026-05-17T00:00:00Z
status: human_needed
score: 4/4 truths verified
overrides_applied: 0
human_verification:
  - test: "Run `mcp-contracts run --config <fixture pointing at a real or stub MCP server with at least one tool>` from a TTY and confirm the domain-UI header, per-tool rows, and summary line all stream live to the operator's terminal during the run (not buffered to end)."
    expected: "Header appears before pytest collection finishes; per-tool rows appear as tests complete (or at least before the final Result: line); Result: summary appears at session end. Banner is NOT swallowed and is NOT duplicated."
    why_human: "Stream-stdout vs. capture-stdout behavior under a real TTY (not the captured-output mode all framework tests use) is the exact seam CR-01 fixed; no automated test exercises `mcp-contracts run` against a real subprocess with stdout=None inherited. Plan 03 SUMMARY explicitly notes this smoke was not attempted."
  - test: "Run `pytest --mcp-domain-ui -n auto` (with pytest-xdist installed) against a payload that generates `[<tool>]`-parametrized tests across multiple workers."
    expected: "The `MCP Test Framework` banner appears EXACTLY ONCE in stdout (controller-only emission), per-tool rows aggregate test results from all workers, and worker-side raw output is not multiplexed into the per-tool render."
    why_human: "REPORTER-02 Success Criterion 4 (xdist controller-only emission). `test_xdist_master_only_emission` in `tests/framework/test_reporter_plugin.py` is gated with `pytest.importorskip('xdist')` and SKIPS in the dev environment because pytest-xdist is not installed. The duck-typed `hasattr(config, 'workerinput')` probe is in place at two code sites and the design is sound, but the operator-facing assumption A3 (controller forwards events; banner count==1) is unverified."
  - test: "Open REQUIREMENTS.md and confirm REPORTER-02's status is updated from `Pending` to `Complete` (or hold REPORTER-02 closure until the xdist smoke above runs)."
    expected: "Line 53 checkbox `[ ]` flipped to `[x]` AND line 128 traceability row `REPORTER-02 | Phase 29 | Pending` updated to `Complete`."
    why_human: "Traceability table out-of-date. Code-wise REPORTER-02 is satisfied (separate pytest11 key, worker no-op, `-p no:` disable verified). But the requirements ledger still shows Pending — needs a documentation sync OR an explicit decision to keep REPORTER-02 open pending the xdist live UAT above."
---

# Phase 29: live-domain-ui-reporter-plugin Verification Report

**Phase Goal:** Operator who wants the v1.2/v1.3-style MCP domain UI output (header / per-tool rows / summary) under library mode passes `--mcp-domain-ui` to pytest and gets it driven by live `pytest_runtest_logreport` events. Default OFF; CI/no-TTY auto-OFF unless `--mcp-domain-ui=force`. Separate pytest11 entry-point key; xdist controller-only.
**Verified:** 2026-05-17
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (= ROADMAP Success Criteria)

| #   | Truth (Success Criterion)                                                                                                                                                                                                                                | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `pytest --mcp-domain-ui` against a library-mode server emits header, per-tool rows, summary from live `pytest_runtest_logreport` events (NO JUnit XML parsing path).                                                                                     | VERIFIED   | `src/mcp_test_framework/_reporter.py:237-258` accumulates `TestReport` events in `pytest_runtest_logreport` (after WR-03 `report.when` filter). `:275` calls `_build_parsed_run_from_reports` (live adapter) at `pytest_sessionfinish` and `:281` calls `render_domain_ui` — no `parse_junit_xml` import or call in `_reporter.py` (purity check passed). Test pass: `test_force_emits_domain_ui_in_piped_stdout` + `test_force_emits_per_tool_rows_and_summary`. |
| 2   | `pytest` (no flag) emits NO domain UI even with contract tests present.                                                                                                                                                                                  | VERIFIED   | `pytest_addoption` sets `default='off'`. `pytest_configure:133` returns immediately when `choice == 'off'` — `_STATE` stays None — all downstream hooks early-return at `_STATE is None`. Test pass: `test_default_off_no_domain_ui`.                                                                                                                                                       |
| 3   | `pytest --mcp-domain-ui` in CI/no-TTY remains OFF unless `=force`; other terminal plugins not hijacked.                                                                                                                                                  | VERIFIED   | `_ORIGINAL_STDOUT = sys.__stdout__ or sys.stdout` at module load (line 59 — WR-02 fix preserves Pitfall 7 intent). `pytest_configure:135` checks `_ORIGINAL_STDOUT.isatty()` for auto mode; returns silently when False. Reporter never registers `pytest_terminal_summary` and never reassigns `sys.stdout` (purity check passed). Tests pass: `test_bare_flag_auto_resolves_to_off_when_no_tty`, `test_explicit_off_value`, `test_bogus_value_rejected_by_choices`. |
| 4   | Reporter ships under separate `[project.entry-points.pytest11]` key (`mcp_test_framework_reporter`); `-p no:` disables it; xdist controller-only emission.                                                                                              | VERIFIED (auto checks); needs human for xdist | `pyproject.toml:37` declares the separate key. `entry_points(group='pytest11')` enumeration returns both keys. `pytest_configure:125` early-returns on `hasattr(config, 'workerinput')`; `pytest_collection_finish:184` re-checks. Test pass: `test_p_no_disables_reporter_and_removes_option`. xdist smoke test (`test_xdist_master_only_emission`) SKIPPED — pytest-xdist not installed in dev env. |

**Score:** 4/4 truths verified (auto). SC4 has one component (xdist runtime ordering) unverified — see human_verification.

### Required Artifacts

| Artifact                                                          | Expected                                                          | Status    | Details                                                                                                                                                                                                                                                                                |
| ----------------------------------------------------------------- | ----------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/mcp_test_framework/_runner.py`                               | `_build_parsed_run_from_reports` adapter + `_classname_from_nodeid` | VERIFIED  | `_runner.py:723` defines the adapter; `:698` defines `_classname_from_nodeid`; module-level `import pytest` present. WR-01 fix at `:780-784` attributes duration to `call` phase only.                                                                                                  |
| `src/mcp_test_framework/_reporter.py`                             | pytest11 plugin: 6 hooks, TTY/CI/xdist gating, live event accumulation | VERIFIED  | 288 lines, hooks: `pytest_addoption`, `pytest_configure`, `pytest_collection_finish`, `pytest_runtest_logreport`, `pytest_sessionfinish`, `pytest_unconfigure`. WR-02 None-guard, WR-03 `report.when` filter, WR-04 re-init guard all present. CR-02 contract-scope gate at `:210-215`. |
| `src/mcp_test_framework/cli.py`                                   | Default branch delegates to reporter; CR-01 stream-stdout fix     | VERIFIED  | AST: zero `render_domain_ui` calls; zero `_render_pre_run_digest` calls. `_render_scenario_pre_run_digest` + `_render_skipped_tools_explain` + `render_summary_only` + `render_debug_appendix` preserved. `cli.py:918` Rule A expression verbatim; `:932` `stream_stdout = (not quiet) and (not debug)`. |
| `pyproject.toml`                                                  | Separate pytest11 entry-point key                                 | VERIFIED  | `pyproject.toml:37`: `mcp_test_framework_reporter = "mcp_test_framework._reporter"`. Existing `mcp_test_framework = "..._plugin"` key (:32) untouched. Both keys installed (`importlib.metadata.entry_points` confirms).                                                                  |
| `tests/framework/unit/test_runner_reports_adapter.py`             | ≥11 unit tests for the adapter                                    | VERIFIED  | 11 tests, all pass.                                                                                                                                                                                                                                                                   |
| `tests/framework/test_reporter_plugin.py`                         | ≥9 subprocess integration tests (xdist gated)                     | VERIFIED  | 10 tests, 9 pass + 1 xdist-gated skip.                                                                                                                                                                                                                                                |
| `tests/framework/test_cli_reporter_rewire.py`                     | ≥8 CLI rewire tests, including Rule A pin + AST proof             | VERIFIED  | 13 tests, all pass. `test_cli_quiet_debug_combination` pins Rule A; `test_no_render_domain_ui_calls_in_cli_module` + `test_no_render_pre_run_digest_calls_in_cli_module` AST proofs pin Edit 6.                                                                                          |

### Key Link Verification

| From                                                              | To                                                                | Via                                          | Status   | Details                                                                                                                                                          |
| ----------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_reporter.pytest_runtest_logreport`                              | `_STATE.reports`                                                  | accumulator append                           | WIRED    | `_reporter.py:258`: `_STATE.reports.append(report)`. WR-03 filter at `:256` rejects non-canonical `when` values.                                                  |
| `_reporter.pytest_sessionfinish`                                  | `_runner._build_parsed_run_from_reports`                          | direct call                                  | WIRED    | `_reporter.py:275`: `parsed = _runner._build_parsed_run_from_reports(_STATE.reports)`.                                                                            |
| `_reporter.pytest_sessionfinish`                                  | `_runner.render_domain_ui`                                        | direct call                                  | WIRED    | `_reporter.py:281`: `_runner.render_domain_ui(parsed, ctx)`.                                                                                                       |
| `_reporter.pytest_configure`                                      | `sys.__stdout__`                                                  | cached `_ORIGINAL_STDOUT.isatty()` probe     | WIRED    | `_reporter.py:59`: `_ORIGINAL_STDOUT = sys.__stdout__ or sys.stdout` (WR-02 hardening); `:135`: `_ORIGINAL_STDOUT.isatty()`. Sole TTY probe.                       |
| `_reporter.pytest_configure`                                      | xdist worker detection                                            | `hasattr(config, 'workerinput')`             | WIRED    | `_reporter.py:125` (configure) and `:184` (collection_finish). Both early-return on workers. No xdist import — runtime ordering unverified (see human).           |
| `cli.run`                                                         | `_runner._build_pytest_args`                                      | `--mcp-domain-ui={mode}` argv append         | WIRED    | `cli.py:918` computes mode; threaded via `run_pytest_subprocess(domain_ui_mode=...)` at `:941`. `_runner.py:167` appends `--mcp-domain-ui={mode}` when not 'off'.   |
| `cli.run` default-UI path                                         | child subprocess stdout                                           | `stream_stdout=True` → `stdout=None` inherit | WIRED (auto); needs human for live TTY | `cli.py:932`: `stream_stdout = (not quiet) and (not debug)`; passed at `:942`. `_runner.py:333-351` uses `stdout=None` when `stream_stdout=True`. No automated test exercises a real TTY; CR-01 fix sketch tests not added. |
| `pyproject.toml [project.entry-points.pytest11]`                  | `src/mcp_test_framework/_reporter.py`                             | entry-point declaration                      | WIRED    | Installed; `pytest --help` shows the option.                                                                                                                       |

### Data-Flow Trace (Level 4)

| Artifact                | Data Variable                  | Source                                                                                       | Produces Real Data | Status     |
| ----------------------- | ------------------------------ | -------------------------------------------------------------------------------------------- | ------------------ | ---------- |
| `_reporter._STATE.reports` | `list[pytest.TestReport]`    | `pytest_runtest_logreport` hook fired by pytest for every test phase                         | Yes (pytest contract) | FLOWING    |
| `_reporter` → `ParsedRun` | `parsed.per_tool` dict        | `_build_parsed_run_from_reports(_STATE.reports)` at sessionfinish                            | Yes (parity-tested vs `parse_junit_xml`) | FLOWING    |
| `_reporter` → terminal  | `print()` inside `render_domain_ui` | `sys.stdout` of pytest subprocess; reaches operator when `cli.run` passes `stream_stdout=True` OR when operator invokes pytest directly | Yes (in subprocess integration tests); needs human for live TTY | FLOWING (auto); HUMAN for TTY |

### Behavioral Spot-Checks

| Behavior                                              | Command                                                                                                                  | Result                                                            | Status |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ------ |
| Both pytest11 entry-points installed                  | `python -c "from importlib.metadata import entry_points; print(sorted(e.name for e in entry_points(group='pytest11') if 'mcp_test_framework' in e.name))"` | `['mcp_test_framework', 'mcp_test_framework_reporter']`           | PASS   |
| `--mcp-domain-ui` option visible                      | `uv run pytest --help \| grep -- --mcp-domain-ui`                                                                          | `  --mcp-domain-ui=[{auto,force,off}]`                            | PASS   |
| Phase 29 test files pass                              | `uv run pytest tests/framework/test_reporter_plugin.py tests/framework/test_cli_reporter_rewire.py tests/framework/unit/test_runner_reports_adapter.py -q` | `33 passed, 1 skipped` (skipped = xdist-gated)                    | PASS   |
| Reporter purity (no XML, no terminal_summary, no stdout hijack, no SUT name) | Grep `_reporter.py` for `parse_junit_xml`, `xml.etree`, `pytest_terminal_summary`, `sys.stdout =`, `homelab` | 0 matches for all forbidden tokens                                | PASS   |
| CLI AST: zero `render_domain_ui`, zero `_render_pre_run_digest` | AST walk of `cli.py`                                                                                       | Both attrs absent; scenario digest + explain + summary + appendix preserved | PASS   |

### Requirements Coverage

| Requirement  | Source Plan         | Description                                                                                                                                       | Status                              | Evidence                                                                                                                                                                |
| ------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REPORTER-01  | 29-01, 29-02, 29-03 | Operator passing `--mcp-domain-ui` sees domain UI driven by live `pytest_runtest_logreport` events (NOT XML). Default OFF. CI auto-OFF.           | SATISFIED                           | SC1+SC2+SC3 above verified; adapter colocated in `_runner.py`; reporter is XML-free.                                                                                  |
| REPORTER-02  | 29-02               | Separate pytest11 entry-point key; xdist controller-only emission.                                                                                | SATISFIED (entry-point); NEEDS HUMAN (xdist live) | Entry-point key declared and installed; `-p no:` disable verified by test. xdist worker no-op design correct (duck-typed probe at 2 sites). xdist live ordering smoke not run — pytest-xdist absent from dev env. **Traceability table in REQUIREMENTS.md still shows Pending** (line 53 + line 128) — needs sync. |

### Anti-Patterns Found

None. Scans for `TODO`/`FIXME`/`PLACEHOLDER`/empty-return/hardcoded-empty-state in the four Phase-29 source artifacts produced no blockers. WR-03 filter explicitly excludes plugin re-run events from corrupting bucket accumulators; CR-02 gate prevents two-banner regression under `--test-code`; all six code-review findings (CR-01, CR-02, WR-01..04) are fixed and accompanied by either an updated test or a documented semantic.

### Human Verification Required

See frontmatter `human_verification:` entries. Three items:

1. **Live-TTY `mcp-contracts run` smoke** — confirm CR-01's stream-stdout path actually delivers the domain UI to a real terminal as the run progresses (no captured-mode tests exercise this seam end-to-end).
2. **`pytest --mcp-domain-ui -n auto` xdist smoke** — exercise SC4's xdist controller-only assumption. Test scaffold exists (`test_xdist_master_only_emission`) but is skipped pending pytest-xdist installation.
3. **REQUIREMENTS.md traceability sync** — REPORTER-02 still listed as `Pending`; code-wise complete. Update the ledger OR hold REPORTER-02 open pending item 2.

### Gaps Summary

No code gaps. Every Success Criterion is implemented and tested via at least one automated check (subprocess integration, AST proof, or unit test). The phase produced 34 new tests (11 adapter + 10 reporter + 13 CLI rewire) plus 6 code-review fix commits with corresponding regression coverage. The full framework sweep reports 670 passed / 2 skipped / 17 deselected / 1 xfailed with no new failures.

What is **not** automatically verified and therefore routed to human verification:

- The end-to-end UX path from `mcp-contracts run` (default flags, real TTY) to a streamed domain UI on the operator's terminal. CR-01 fixed the capture-and-discard defect, but the only automated coverage stubs `run_pytest_subprocess` (CLI tests) or invokes pytest directly without going through the CLI's `subprocess.run(stdout=None)` path (reporter integration tests).
- The xdist runtime ordering — controller forwards `pytest_runtest_logreport` for every worker test; banner emits exactly once on the controller. Design is sound (no xdist import; duck-typed `workerinput` probe at two hook sites), but the live ordering is unexercised in this environment.
- REQUIREMENTS.md REPORTER-02 status sync (documentation, not code).

---

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
