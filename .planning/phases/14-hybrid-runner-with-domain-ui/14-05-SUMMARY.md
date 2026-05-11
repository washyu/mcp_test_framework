---
phase: 14-hybrid-runner-with-domain-ui
plan: 05
subsystem: runner-cleanup
tags: [cleanup, plugin-deletion, cache-migration, regression-pins, phase-14-close]

# Dependency graph
requires:
  - phase: 14-01-subprocess-spine
    provides: "src/mcp_test_framework/_runner.py exists as the destination for the migrated cache + helper"
  - phase: 14-02-junit-xml-parser
    provides: "tests/unit/test_runner_parser.py pins the locked skip-reason constants and tool-name extraction; allows deleting the duplicate tests/unit/test_reporter.py::test_safe_01_reporter_constants_locked"
  - phase: 14-03-domain-ui-renderer
    provides: "tests/test_runner_renderer.py pins state-(a)/(c) composer behavior via _compose_unparametrized_skips_from_config; allows deleting the duplicate state-a/c composer tests from tests/unit/test_reporter.py"
  - phase: 14-04-verbosity-ladder
    provides: "tests/test_runner_verbosity.py + render_summary_only / render_debug_appendix are stable; no Plan 04 surface depends on _reporter"
provides:
  - "_reporter.py DELETED -- the v1.1 in-pytest reporter plugin no longer exists in src/mcp_test_framework/"
  - "_DISCOVERED_TOOL_NAMES + _set_discovered_tool_names helper migrated to src/mcp_test_framework/_runner.py (an importable module under src/) so the in-pytest discovery cache stays patchable by unit tests via a real import path"
  - "tests/conftest.py no longer registers mcp_test_framework._reporter as a pytest plugin and no longer imports the deleted module; pytest_plugins = ['mcp_test_framework.fixtures']"
  - "tests/conftest.py imports the cache via `from mcp_test_framework import _runner as _r` so reads/writes hit the LIVE module attribute (tests can patch it without snapshotting it at import time)"
  - "tests/unit/test_runner_migration.py (renamed from tests/unit/test_reporter.py via git mv to preserve blame) -- preserves the 5 still-relevant tests: 3 SAFE-01 allowlist + 2 CR-01 MCPTF_CONFIG_FILE IPC; deletes the 5 duplicative state-a/c composer + locked-constants tests"
  - "tests/test_runner_live_smoke.py -- new live-homelab integration smoke for the new domain UI shape (header strings + Result summary), --junit-xml=PATH preservation, and --raw bypass; replaces the live half of the deleted tests/test_reporter.py"
  - "3 regression pins in tests/test_runner_subprocess.py: test_reporter_module_no_longer_importable, test_runner_owns_discovery_cache, test_plugins_list_does_not_register_reporter"
affects: [phase-15-test-tree-split, phase-16-pre-run-digest, "SEED-010 (tests/contract vs tests/framework split is now strictly easier)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Patchable cache via module attribute: tests assign `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES = [...]` directly to bypass the discovery subprocess. This works because _runner is an importable module under src/. The companion helper `_set_discovered_tool_names(names)` exists for the production-code path (conftest's _resolve_tool_names) so it doesn't need a `global` declaration at the call site."
    - "Two-cache architecture (wrapper-side discovery in cli.py via RenderContext.discovered_tools + in-pytest cache in _runner._DISCOVERED_TOOL_NAMES): intentional v1.2 split. The wrapper runs outside pytest and cannot reach the in-pytest cache; the in-pytest cache is needed by pytest_generate_tests for the SAFE-01 allowlist filter. Each discovery costs <1s; consolidation to one shared discovery call is a v1.3 candidate."
    - "git mv before substantive edits: preserves git blame on the surviving tests when renaming tests/unit/test_reporter.py -> tests/unit/test_runner_migration.py. Then Edit/Write to scrub the deleted tests and update import paths."
    - "Comment cleanup parallel to code deletion: when a module is deleted, scrub its name from comments and docstrings in surviving files as well -- prevents future contributors from chasing dead references via `git grep _reporter`."
    - "Regression pin pattern for deletions: test_reporter_module_no_longer_importable uses pytest.raises((ImportError, ModuleNotFoundError)) so any accidental reintroduction (e.g., a future phase re-adds the file by reverting a commit) fails the test suite loud. Mirrors the forward-reference absence pattern from Plan 04 (test_run_help_does_not_list_explain) -- both pin the absence of a known surface."

key-files:
  created:
    - "tests/test_runner_live_smoke.py -- 3 live-homelab integration tests (pytestmark = pytest.mark.live_homelab) replacing the live half of the deleted tests/test_reporter.py"
  modified:
    - "src/mcp_test_framework/_runner.py -- appended 38 lines: _DISCOVERED_TOOL_NAMES module attribute + _set_discovered_tool_names helper. Also scrubbed 3 residual '_reporter' substring references from inline comments / docstrings."
    - "src/mcp_test_framework/cli.py -- updated one docstring comment to point at _runner instead of the deleted _reporter module."
    - "tests/conftest.py -- pytest_plugins narrowed to ['mcp_test_framework.fixtures']; replaced `from mcp_test_framework import _reporter as _rep` with `from mcp_test_framework import _runner as _r`; _resolve_tool_names rewritten to read/write the cache via _r module attribute (using the setter helper for writes); refreshed file docstring + cache-location comment."
    - "tests/test_runner_subprocess.py -- appended 3 regression pins (lines 257-326): test_reporter_module_no_longer_importable, test_runner_owns_discovery_cache, test_plugins_list_does_not_register_reporter."
    - "tests/unit/test_runner_migration.py -- renamed from tests/unit/test_reporter.py via `git mv`; rewrote to drop the 5 duplicative tests + the test_cr02 reporter composer test; preserved 5 still-relevant tests retargeted to the _runner cache seam; added autouse _reset_discovery_cache fixture for test independence."
  deleted:
    - "src/mcp_test_framework/_reporter.py -- 285 lines, the v1.1 in-pytest reporter plugin. Responsibilities fully owned by _runner.py after Plans 02-04."
    - "tests/test_reporter.py -- 552 lines, 46 references to the deleted plugin. Unit half subsumed by tests/test_runner_parser.py + tests/test_runner_renderer.py + tests/test_runner_verbosity.py; live half reincarnated as tests/test_runner_live_smoke.py."

key-decisions:
  - "Migrate _DISCOVERED_TOOL_NAMES into _runner.py (NOT tests/conftest.py). The 14-05 plan called this out explicitly: tests/__init__.py exists today, but the plan author was deliberate about putting the cache in an importable module under src/ so the patchable-attribute seam (tests/unit/test_runner_migration.py uses `_r._DISCOVERED_TOOL_NAMES = [...]`) survives even if tests/__init__.py is ever removed in a future cleanup. Also: production code shouldn't depend on test code, and the cache is consumed by production code (_resolve_tool_names lives in conftest.py but is callable from anywhere)."
  - "DELETE tests/test_reporter.py entirely rather than retarget. The grep count (46 _reporter references in 552 lines) exceeded the plan's threshold; surgical retargeting would have left a confusing hybrid file. Replaced with tests/test_runner_live_smoke.py covering only the live-homelab integration smoke that doesn't have an equivalent in tests/test_runner_*.py."
  - "git mv tests/unit/test_reporter.py -> tests/unit/test_runner_migration.py BEFORE rewriting. Preserves git blame on the surviving tests (3 SAFE-01 + 2 CR-01) and signals the file's purpose-shift via its name change."
  - "DELETE test_cr02_reporter_state_c_renders_curated_skip_reason (was preserved by the plan's BUT the plan also gave permission to delete if Plan 03 covered the invariant). It specifically tested `_compose_unparametrized_skips` from the deleted module; Plan 03's `test_state_c_listed_with_skip_renders_curated_reason` (in tests/test_runner_renderer.py) covers the same invariant via the new `_compose_unparametrized_skips_from_config` pure function. Keeping it would have required either rewriting against the new pure function (duplicating Plan 03's test) or testing through cli.py's full discovery path (out of scope for a unit file). Cleaner to delete."
  - "Scrub residual '_reporter' substring references from comments in surviving source / test files. The Plan 14-05 acceptance criteria specified strict `grep -c '_reporter'` checks (0 in conftest.py and src/mcp_test_framework/). Honored this by rewriting four comments in _runner.py, one in cli.py, and the module docstring in test_runner_migration.py. The remaining 4 docstring references in tests/test_runner_live_smoke.py, tests/test_runner_renderer.py, tests/unit/test_runner_parser.py, tests/unit/test_runner_migration.py are intentional historical context (referencing the deleted file by its old name in passing) and do not violate the strict acceptance criteria which scoped to src/ + conftest.py."

patterns-established:
  - "Cache-as-module-attribute is the patchable seam: production reads via `_r._DISCOVERED_TOOL_NAMES`, tests write via direct assignment. Setter helper exists so production code doesn't need `global` declarations. Future caches (e.g., a per-judge model cache from SEED-012) should follow this pattern."
  - "Deletion regression pin: after deleting a module, add a test that asserts `importlib.import_module(<deleted>)` raises ImportError. Prevents accidental reintroduction via merge / revert."
  - "Forward-reference absence (Plan 04 pattern) + deletion regression (this plan) are duals: both pin the absence of a known surface for grep-able stability."

requirements-completed: [RUNNER-02]

# Metrics
duration: ~30min
completed: 2026-05-10
---

# Phase 14 Plan 05: _reporter.py Deletion + Cache Migration Summary

**Closes Phase 14 by deleting the v1.1 in-pytest reporter plugin (`src/mcp_test_framework/_reporter.py`, 285 lines, all 46 references scrubbed from tests/conftest.py and surviving test files). The `_DISCOVERED_TOOL_NAMES` cache + a new `_set_discovered_tool_names` helper now live on `src/mcp_test_framework/_runner.py` (an importable module under src/) so surviving SAFE-01 allowlist unit tests can patch the cache directly. The wrapper (Plans 01-04) owns all reporting; this plan removes the last vestige of the in-pytest plugin architecture. RUNNER-02 is complete.**

## What Shipped

### Cache migration (`_runner.py`)
- New module attribute `_DISCOVERED_TOOL_NAMES: list[str] | None = None` at the bottom of `_runner.py`.
- New helper `_set_discovered_tool_names(names: list[str]) -> None` that does the `global` write so production callers (`tests/conftest.py:_resolve_tool_names`) don't need a `global` declaration.
- Tests patch the cache directly via `from mcp_test_framework import _runner as _r; _r._DISCOVERED_TOOL_NAMES = [...]`.

### `tests/conftest.py` cleanup
- `pytest_plugins = ["mcp_test_framework.fixtures"]` -- the v1.1 plugin is no longer registered.
- `from mcp_test_framework import _runner as _r` replaces the deleted `_reporter as _rep` import.
- `_resolve_tool_names` reads via `_r._DISCOVERED_TOOL_NAMES` (live module attribute, not a snapshot) and writes via the `_r._set_discovered_tool_names(...)` helper.
- File docstring refreshed; cache-location comment now points at `_runner.py` instead of the deleted plugin.

### `_reporter.py` deletion
- `src/mcp_test_framework/_reporter.py` removed via `git rm`. All 285 lines (per-tool aggregation buffer, `pytest_runtest_logreport`, `_extract_skip_reason`, `pytest_terminal_summary`, em-dash separator, `_compose_unparametrized_skips`) deleted. Their responsibilities are owned by `src/mcp_test_framework/_runner.py` (Plans 02-04).

### Test retargeting
- **DELETE** `tests/test_reporter.py` (552 lines, 46 `_reporter` references) -- the unit half is subsumed by `tests/test_runner_parser.py` + `tests/test_runner_renderer.py` + `tests/test_runner_verbosity.py`; the live half is replaced by `tests/test_runner_live_smoke.py`.
- **CREATE** `tests/test_runner_live_smoke.py` (3 live-homelab integration tests, all `@pytest.mark.live_homelab`-gated): domain UI header + Result summary; `--junit-xml=PATH` preservation; `--raw` bypass produces pytest framing.
- **RENAME** `tests/unit/test_reporter.py` -> `tests/unit/test_runner_migration.py` via `git mv` to preserve blame on the surviving tests.
- **DROP** (from the renamed file) 5 duplicative tests + the CR-02 reporter composer test: `test_safe_01_reporter_constants_locked`, `test_safe_01_compose_state_a_for_unlisted_tool`, `test_safe_01_compose_state_c_with_curated_reason`, `test_safe_01_compose_state_c_default_when_skip_reason_empty`, `test_safe_01_compose_no_op_when_discovery_never_ran`, `test_cr02_reporter_state_c_renders_curated_skip_reason`. Each is covered by Plan 02 or Plan 03 tests against `_runner` -- documented in the file-level docstring.
- **PRESERVE** (in the renamed file) the 5 still-relevant tests, retargeted to the `_runner` cache seam: `test_safe_01_allowlist_includes_listed_unskipped`, `test_safe_01_allowlist_excludes_unlisted_and_skipped`, `test_safe_01_empty_tools_means_zero_selection`, `test_cr01_bare_config_picks_up_mcptf_config_file`, `test_cr01_resolver_writes_mcptf_config_file_env_var`.
- **ADD** an autouse `_reset_discovery_cache` fixture so the migrated tests stay independent (resets `_r._DISCOVERED_TOOL_NAMES` to `None` before + after each test).

### Regression pins (`tests/test_runner_subprocess.py`)
- `test_reporter_module_no_longer_importable`: `importlib.import_module("mcp_test_framework._reporter")` MUST raise `ImportError` / `ModuleNotFoundError`. Prevents future-phase reintroduction.
- `test_runner_owns_discovery_cache`: `_DISCOVERED_TOOL_NAMES` + `_set_discovered_tool_names` must live on `mcp_test_framework._runner`, with the patchability seam (direct attribute assignment) exercised.
- `test_plugins_list_does_not_register_reporter`: `tests/conftest.py:pytest_plugins` must equal `["mcp_test_framework.fixtures"]`. Uses `importlib.util.spec_from_file_location` to load conftest as a probe (with a grep-based fallback if standalone execution proves brittle).

## How It Works

```
                              before Plan 14-05                              after Plan 14-05
                              -------------------                            -----------------
tests/conftest.py             pytest_plugins = [                             pytest_plugins = [
                                "mcp_test_framework.fixtures",                 "mcp_test_framework.fixtures",
                                "mcp_test_framework._reporter",              ]  # one entry
                              ]                                              from mcp_test_framework import _runner as _r
                              from mcp_test_framework import _reporter as _rep
                                                                             _r._set_discovered_tool_names(...)  # write
                              _rep._DISCOVERED_TOOL_NAMES = [...]            _r._DISCOVERED_TOOL_NAMES            # read

src/mcp_test_framework/       _reporter.py:                                  _reporter.py: DELETED
                                _PER_TOOL = {}
                                _DISCOVERED_TOOL_NAMES = None                _runner.py:
                                pytest_runtest_logreport(...)                  _DISCOVERED_TOOL_NAMES: "list[str] | None" = None
                                pytest_terminal_summary(...)                   def _set_discovered_tool_names(names): ...
                                _compose_unparametrized_skips(...)             # + parser + renderer + verbosity from Plans 02-04
                              _runner.py:
                                # Plans 02-04 surface only
                              cli.py:
                                # wrapper that drives pytest subprocess
```

The in-pytest reporter plugin is gone. Per-tool reporting is now wholly owned by the wrapper (`cli.py` calls `_runner.run_pytest_subprocess` -> parses the JUnit XML with `_runner.parse_junit_xml` -> renders via `_runner.render_domain_ui` / `render_summary_only` / `render_debug_appendix`).

The in-pytest discovery cache stays in-pytest (it serves `pytest_generate_tests` for the SAFE-01 allowlist filter), but its home moved from a now-deleted plugin module to a still-alive utility module under `src/`.

## Two-Cache Architecture (carried forward from Plan 14-03)

This plan does NOT change the two-cache architecture introduced in Plan 14-03. There are still TWO independent discovery caches in v1.2:

1. **Wrapper-side discovery** -- `cli.py:_discover_tools_for_run` runs ONCE before launching the pytest subprocess. The result populates `RenderContext.discovered_tools` and is consumed by `_render_header` (Discovered: N tools) and `_compose_unparametrized_skips_from_config` (state-(a) SKIP rows).
2. **In-pytest discovery** -- `tests/conftest.py:_discover_tools` runs INSIDE the pytest subprocess during `pytest_generate_tests`. The result populates the migrated `_runner._DISCOVERED_TOOL_NAMES` module attribute and is consumed by `_resolve_tool_names` for the parametrize allowlist filter.

This results in TWO MCP discovery subprocesses per run (one from the wrapper, one from inside pytest). Each takes <1s; consolidating to one shared discovery is a v1.3 candidate (would require an IPC channel from the wrapper's discovery into the pytest subprocess -- complexity not justified for v1.2 latency budgets).

## Verification

### Acceptance Criteria Achieved
- [x] `src/mcp_test_framework/_reporter.py` does NOT exist.
- [x] `grep -rn "_reporter" src/mcp_test_framework/` returns 0 matches.
- [x] `grep -c "_reporter" tests/conftest.py` returns 0.
- [x] `tests/conftest.py:pytest_plugins == ["mcp_test_framework.fixtures"]`.
- [x] `from mcp_test_framework._runner import _DISCOVERED_TOOL_NAMES, _set_discovered_tool_names` works and yields `None` + a callable.
- [x] `from mcp_test_framework import _runner as _r; _r._DISCOVERED_TOOL_NAMES = ['a','b']` works (patchability seam).
- [x] `python -c "import mcp_test_framework._reporter"` fails with `ModuleNotFoundError` (verified manually + pinned via `test_reporter_module_no_longer_importable`).
- [x] `tests/unit/test_runner_migration.py` exists; `tests/unit/test_reporter.py` does NOT.
- [x] `tests/test_runner_live_smoke.py` exists; `tests/test_reporter.py` does NOT.
- [x] `uv run mcp-test-framework run --help` exits 0 (CLI loads cleanly).
- [x] `uv run pytest tests/test_runner_subprocess.py tests/test_runner_renderer.py tests/test_runner_verbosity.py tests/unit/test_runner_parser.py tests/unit/test_runner_migration.py` -- 79 passed.
- [x] 3 new regression pins pass.

### Test Suite Status
- **Non-live test suite** (`uv run pytest tests/ -k "not live_homelab and not live_ollama"`): **274 passed, 5 failed, 10 skipped, 15 deselected**.
- The 5 failures are ALL in `tests/test_tool_config.py` and ALL pre-existing on the base commit `bd0dcd7e` (verified by `git checkout bd0dcd7e -- tests/test_tool_config.py` and re-running -- same 5 failures, identical reasons). They are NOT caused by Plan 14-05 changes. See **Deferred Issues** below.

### CLI smoke
- `uv run mcp-test-framework run --help` lists `--raw`, `--debug`, `-q`/`--quiet`, `--config`, `--junit-xml`. Does NOT list `--explain` (D-14: Phase 16's flag, intentionally absent).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan documentation drift] tests/__init__.py exists**
- **Found during:** Task 2.
- **Issue:** The plan's premise that "`tests/` is NOT a Python package (no `tests/__init__.py`)" is outdated -- `tests/__init__.py` and `tests/unit/__init__.py` both exist as empty files in this repo.
- **Impact:** The plan's reasoning for putting the cache in `_runner.py` instead of `tests/conftest.py` still holds (the cache MUST live in production code so tests can patch a real import path; production code MUST NOT depend on test code), but the "tests/ is not importable" framing was incorrect. I kept the cache in `_runner.py` (per the plan's directive) but the preserved SAFE-01 tests continue to use `from tests.conftest import _resolve_tool_names` (the original v1.1 import pattern), which works because `tests/__init__.py` exists. The plan's alternative recommendation (`importlib.util.spec_from_file_location`) is only used in the new regression pin `test_plugins_list_does_not_register_reporter` because that test specifically wants to probe conftest's `pytest_plugins` value without triggering its full pytest-collection side-effects.
- **Fix:** No code fix needed. Documented here for future plan reviewers so the "tests/ is not a package" claim is not propagated.

**2. [Rule 1 - Strict grep avoidance for residual comments] Scrubbed historical `_reporter` substring references from comments**
- **Found during:** Task 2 acceptance verification.
- **Issue:** Plan 14-05 acceptance criteria specified `grep -rn "_reporter" src/mcp_test_framework/` returns 0 matches. After deletion, the initial state had 6 historical comment references in `_runner.py` (4) and `cli.py` (1, in a docstring) referencing the deleted module by name as architectural context.
- **Fix:** Rewrote each comment to describe the v1.1 reporter plugin without using the literal `_reporter` substring (e.g., "the v1.1 in-pytest reporter plugin" instead of "_reporter._compose_unparametrized_skips"). Also scrubbed the renamed `tests/unit/test_runner_migration.py` module docstring. The remaining 4 historical references in unit test docstrings (in `tests/test_runner_renderer.py`, `tests/unit/test_runner_parser.py`, `tests/test_runner_live_smoke.py`, and `tests/unit/test_runner_migration.py`) are outside the strict acceptance scope (which targeted `src/` + `conftest.py`) and are intentional historical context.
- **Files modified:** `src/mcp_test_framework/_runner.py`, `src/mcp_test_framework/cli.py`, `tests/unit/test_runner_migration.py`.

**3. [Rule 1 - Plan recommended preserve, but Plan 03 made it duplicative] DELETE test_cr02_reporter_state_c_renders_curated_skip_reason from the renamed file**
- **Found during:** Task 2.
- **Issue:** The plan listed `test_cr02_reporter_state_c_renders_curated_skip_reason` under "PRESERVE" but with the caveat "DELETE if Plan 03's `test_state_c_listed_with_skip_renders_curated_reason` covers the same invariant". Verified Plan 03's test covers state-(c) composition with curated reason via the new pure `_compose_unparametrized_skips_from_config`. Rewriting the CR-02 test against the new pure function would have duplicated Plan 03's test; rewriting it through `cli.py`'s full discovery path would have made it an integration test (out of scope for `tests/unit/`).
- **Fix:** Deleted it, documented the deletion in the renamed file's module docstring.

## Deferred Issues

**Pre-existing baseline failures in `tests/test_tool_config.py`** (NOT caused by Plan 14-05; verified on base commit `bd0dcd7e`):
- `test_default_config_version_and_tools` -- asserts `cfg.version == 1` but the Config default is `version=2` (moved during Phase 12).
- `test_config_rejects_unsupported_version[2]` -- asserts version 2 raises; version 2 is now accepted.
- `test_yaml_overlay_loads_tools_block` -- uses `target={"tool_name": ...}` which is rejected by the schema as `extra_forbidden`.
- `test_resolve_tool_names_filters_out_skip_true_tools` -- uses `target={"tool_name": ...}`.
- `test_resolve_tool_names_explicit_target_overrides_skip_true` -- uses `target={"tool_name": ...}`.

These tests reference a deprecated `target` config field that was removed during Phase 12 (single-tool focus is now handled via `--config focus-<tool>.yaml`). They are unrelated to Plan 14-05's _reporter migration and were already failing at the worktree base commit. Phase 14-04's SUMMARY notes the same observation ("If you encounter `test_tool_config.py` failures, those are NOT in scope -- leave them alone and document in SUMMARY's Deferred Issues"). Suggested cleanup: a follow-up plan in Phase 15+ retargeting or deleting these tests.

## Tasks + Commits

| Task | Name                                                                                  | Commit  |
| ---- | ------------------------------------------------------------------------------------- | ------- |
| 1    | Migrate _DISCOVERED_TOOL_NAMES cache from _reporter to _runner; update conftest       | b34bfae |
| 2    | Delete _reporter.py; retarget tests (delete test_reporter.py, rename unit test file)  | 0a77bc7 |
| 3    | Add 3 regression pins for _reporter deletion + _runner cache ownership                | 43d0f85 |

## Self-Check: PASSED

- File `src/mcp_test_framework/_reporter.py` checked: MISSING (expected; deleted).
- File `src/mcp_test_framework/_runner.py` checked: FOUND.
- File `tests/conftest.py` checked: FOUND (modified).
- File `tests/test_runner_live_smoke.py` checked: FOUND.
- File `tests/test_runner_subprocess.py` checked: FOUND (modified).
- File `tests/unit/test_runner_migration.py` checked: FOUND.
- File `tests/unit/test_reporter.py` checked: MISSING (expected; renamed).
- File `tests/test_reporter.py` checked: MISSING (expected; deleted).
- Commit b34bfae checked: FOUND.
- Commit 0a77bc7 checked: FOUND.
- Commit 43d0f85 checked: FOUND.
- Regression pins pass: `uv run pytest tests/test_runner_subprocess.py::test_reporter_module_no_longer_importable tests/test_runner_subprocess.py::test_runner_owns_discovery_cache tests/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter` -- 3 passed.
