---
phase: 29-live-domain-ui-reporter-plugin
fixed_at: 2026-05-17T00:00:00Z
review_path: .planning/phases/29-live-domain-ui-reporter-plugin/29-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
fix_branch: reviewfix-29-iter1
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-05-17
**Source review:** `.planning/phases/29-live-domain-ui-reporter-plugin/29-REVIEW.md`
**Iteration:** 1
**Fix branch:** `reviewfix-29-iter1` (8 atomic commits on top of `714e702`)

**Summary:**
- Findings in scope: 6 (2 Critical, 4 Warning -- Info skipped per fix_scope=critical_warning)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: Default `mcp-contracts run` swallows the reporter's domain UI

**Files modified:** `src/mcp_test_framework/_runner.py`, `src/mcp_test_framework/cli.py`
**Commit:** `4ff0c34`
**Applied fix:** Added a `stream_stdout: bool = False` kwarg to `run_pytest_subprocess`. When True, the child pytest subprocess is launched with `stdout=None` (inherit parent fd) and `stderr=subprocess.PIPE`, so the in-subprocess reporter plugin's live emissions reach the operator's terminal as they happen. CLI sets `stream_stdout=True` only on the default-UI path (`(not quiet) and (not debug)`). The `-q` (no `--debug`) and `--debug` paths still capture stdout because they need it for `render_summary_only` and `render_debug_appendix` respectively. This is the reviewer's preferred option 1 ("run the subprocess WITHOUT captured stdout on the default path") with `--debug`/`-q` capture flows preserved. `_dispatch_default_mode_or_error`'s `captured_stderr.splitlines()` usage is unaffected because stderr stays captured under streaming.

### CR-02: Double-banner under `mcp-contracts run --test-code`

**Files modified:** `src/mcp_test_framework/_reporter.py`, `tests/framework/test_reporter_plugin.py`
**Commits:** `f502e3b`, `7ba424f`, `3902d03`
**Applied fix:** Added a contract-scope gate to `_reporter.pytest_collection_finish`. Initial implementation (`f502e3b`) used the reviewer's suggested `mcp_contract` keyword filter; this broke `test_force_emits_domain_ui_in_piped_stdout` because that fixture exercises the standalone `--mcp-domain-ui=force` opt-in surface (parametrized tests without the framework's marker). Adding the marker to the fixture in turn pulled in the framework's `_preflight` async fixture machinery and broke a different test. The refinement (`7ba424f`) replaced the keyword filter with a tool-extractability filter: `_runner._extract_tool_name(item.nodeid) is not None`. Items with a `[<tool>]` parametrize suffix are contract-shape (banner renders); items without (test-code hand-authored tests, framework self-tests) are scenario-shape (banner suppressed; CLI's `_render_scenario_pre_run_digest` owns the test-code surface). This aligns with the existing tool-extractability semantic in `_build_parsed_run_from_reports` and preserves the operator opt-in via `--mcp-domain-ui=force` on parametrized tests. `3902d03` adds a `# noqa: sdet-rename-shim` marker to the new docstring mention of `tests/sdet/` so the rename leak gate passes.

### WR-01: `_build_parsed_run_from_reports` over-counts duration vs JUnit parser

**Files modified:** `src/mcp_test_framework/_runner.py`, `tests/framework/unit/test_runner_reports_adapter.py`
**Commit:** `8d0073e`
**Status:** fixed: requires human verification
**Applied fix:** Restricted `bucket.duration` accumulation to `phases.get("call")` when present (matching pytest's JUnit writer default `junit_duration_report=call`). On the setup-skip / collection-error path where no call report exists, fall back to summing the available phase reports -- consistent with what pytest's JUnit writer records as `<testcase time>` for setup-only runs. Updated two unit tests that pinned the old sum-all-phases behavior: `test_three_phase_pass_produces_one_case` (0.03 -> 0.01) and `test_totals_sum_across_buckets` (0.08 -> 0.04). The parity test `test_field_equal_to_parse_junit_xml` continues to NOT assert duration agreement (left to a future iteration), but the chosen semantic now matches `<testcase time>` so the two adapters agree on a per-tool basis when the JUnit writer is in its default mode. **Requires human verification** because the choice between "match XML" and "match pytest internal phase totals" is a semantic call -- the reviewer flagged either as defensible.

### WR-02: Reporter assumes `sys.__stdout__` is non-None at module load

**Files modified:** `src/mcp_test_framework/_reporter.py`
**Commit:** `2f8711e`
**Applied fix:** Changed `_ORIGINAL_STDOUT = sys.__stdout__` to `sys.__stdout__ or sys.stdout` so the cached reference is always a writable stream under pythonw (Windows GUI launcher) and frozen-binary (pyinstaller `--noconsole`) contexts where CPython sets `sys.__stdout__` to None. Auto-mode resolution still resolves to off in those contexts because `sys.stdout` under pythonw is itself a non-TTY wrapper (its `isatty()` returns False). Existing defensive `getattr(..., "isatty", lambda: False)()` at the call site is unchanged.

### WR-03: Reporter does not validate `report.when` before bucketing

**Files modified:** `src/mcp_test_framework/_reporter.py`
**Commit:** `0199e50`
**Applied fix:** In `pytest_runtest_logreport`, after the `_STATE` gate, drop reports whose `report.when` is not one of pytest's three canonical phases (`setup`, `call`, `teardown`). Plugins like pytest-rerunfailures emit additional report kinds; xdist may forward duplicated reports. Under WR-01's new setup-skip fallback path (which sums available phase reports), an unknown `when` value would create an extra dict entry and inflate `bucket.duration`. The filter at the accumulation boundary prevents that, leaving the standard pytest flow unaffected.

### WR-04: Module-level `_STATE` global breaks pytest re-entrancy / multi-session

**Files modified:** `src/mcp_test_framework/_reporter.py`
**Commit:** `10547c5`
**Applied fix:** Added a defensive re-init guard in `pytest_configure`: after the off / auto-no-tty short-circuits and before the `_STATE = _ReporterState(enabled=True)` assignment, check whether `_STATE` is already populated. If so, emit a `RuntimeWarning` describing the stale-state scenario (pytest_unconfigure didn't fire -- in-process re-entry, IDE test runner, or library-mode `pytest.main()` re-use) and reset the accumulator. The single-session-per-process invariant is preserved; the previously silent merge-of-two-sessions bug is now visible to the operator. Did not migrate to `config.stash` per the reviewer's note that `pytest_runtest_logreport` has no config back-reference -- the module-global pattern stays.

---

## Regression check

`uv run python -m pytest tests/framework/ -q` -- **670 passed, 2 skipped, 17 deselected, 1 xfailed, 45 warnings in 30.86s.**

Test updates required to align fixtures and pins with the corrected behavior (none weakened):

- `tests/framework/unit/test_runner_reports_adapter.py`: two duration assertions updated to match WR-01's call-phase-only semantic (`test_three_phase_pass_produces_one_case`: 0.03 -> 0.01; `test_totals_sum_across_buckets`: 0.08 -> 0.04). Both updates are documented inline with the new semantic.
- `tests/framework/test_reporter_plugin.py::_write_payload_with_config`: docstring updated to explain the parametrize-suffix gate that CR-02 introduced; the fixture's `test_param.py` body is unchanged (the parametrize already produces `[<tool>]` nodeids that satisfy the new gate). No production-test pin weakened.

---

## Commit ledger (branch `reviewfix-29-iter1`)

```
3902d03 fix(29): CR-02 add sdet-rename-shim noqa to CR-02 doc comment
7ba424f fix(29): CR-02 refine contract-scope gate to use [<tool>] suffix
10547c5 fix(29): WR-04 add re-init guard for module-global _STATE
0199e50 fix(29): WR-03 filter pytest_runtest_logreport on report.when
2f8711e fix(29): WR-02 guard _ORIGINAL_STDOUT against None on pythonw
8d0073e fix(29): WR-01 attribute live duration to call phase only
f502e3b fix(29): CR-02 suppress reporter banner under non-contract scope
4ff0c34 fix(29): CR-01 stream pytest stdout on default mcp-contracts run path
```

---

_Fixed: 2026-05-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
