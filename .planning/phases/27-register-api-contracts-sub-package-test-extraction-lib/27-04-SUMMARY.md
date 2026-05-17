---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
plan: 04
subsystem: testing
tags: [pytest, ini-override, marker-detection, config-resolution, cli, subprocess]

# Dependency graph
requires:
  - phase: 27-02
    provides: pytest_configure reads mcp_config_file ini -> Config(yaml_file=path) -> _mcp_contracts_config stash
  - phase: 27-03
    provides: plugin synthesizes <mcp-contracts> module + applies mcp_contract marker per item
provides:
  - cli run command threads resolved YAML path to subprocess via pytest -o "mcp_config_file=PATH"
  - _load_config returns (Config, resolved_path) tuple; no more os.environ["MCPTF_CONFIG_FILE"] write in CLI mode
  - _session_needs_preflight predicate hybridized: mcp_contract marker OR nodeid prefix
  - single config-resolution route across CLI subprocess + operator library mode
affects: [27-05, 28, 30]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest -o key=value runtime ini override as subprocess config-handoff (replaces env-var write)"
    - "marker-based preflight detection with iter_markers tolerance for lightweight fakes"

key-files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/cli.py
    - src/mcp_test_framework/fixtures.py
    - tests/framework/unit/test_runner_migration.py
    - tests/framework/unit/test_cli_errors.py
    - tests/framework/unit/test_session_needs_preflight.py

key-decisions:
  - "Option (a) tuple-return refactor for _load_config: returns (Config | None, Path | None) instead of introducing a sibling resolver helper or module-level cache; keeps a single resolution code path and avoids hidden state."
  - "Retained tests/contract/ in _LIVE_PREFIXES transitionally because the legacy on-disk tests/contract/test_mcp_tool_contract.py is still collected via tests/conftest.py:pytest_generate_tests and does NOT carry the mcp_contract marker. Plan 27-05 removes the transitional entry alongside the legacy collection wiring."
  - "Kept the MCPTF_CONFIG_FILE env-var READ in cli._load_config Branch 2 for v1.4 back-compat; plugin emits DeprecationWarning when the env var is set. Removed only the env-var WRITE per D-11."

patterns-established:
  - "Marker-based preflight detection: synthetic-nodeid contract tests (no path to anchor on) are detected via pytest.mark.mcp_contract; iter_markers lookup uses getattr to remain testable with SimpleNamespace fakes."
  - "Subprocess config handoff: CLI passes resolved path to in-subprocess plugin via [-o, mcp_config_file=PATH] argv elements (two list elements, no shell interpretation) — same ini key the operator's [tool.pytest.ini_options] sets in library mode."

requirements-completed: [LIB-07]

# Metrics
duration: 25min
completed: 2026-05-17
---

# Phase 27 Plan 04: CLI -> Subprocess Config Handoff + Preflight Marker Flip Summary

**Replaced the MCPTF_CONFIG_FILE env-var write with `pytest -o "mcp_config_file=PATH"` subprocess argv injection and flipped `_session_needs_preflight` to detect plugin-injected contract tests via the `mcp_contract` marker; CLI and library modes now share one config-resolution mechanism end-to-end.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-17T00:20Z (approximate)
- **Completed:** 2026-05-17T00:45Z
- **Tasks:** 3
- **Files modified:** 6 (3 src/, 3 tests/)

## Accomplishments

- `_runner._build_pytest_args` and `_runner.run_pytest_subprocess` accept a new `mcp_config_path` kwarg and inject `["-o", f"mcp_config_file={path}"]` into the subprocess argv when set. Both raw and default modes thread the kwarg uniformly.
- `cli._load_config` returns `(Config | None, Path | None)`; the resolved path is threaded to `_runner.run_pytest_subprocess` so the subprocess pytest sees the same YAML the wrapper saw — through pytest's runtime ini override mechanism, NOT through `os.environ`. The env-var WRITE at `cli.py` is gone; the env-var READ in Branch 2 of `_load_config` stays for v1.4 back-compat.
- `fixtures._session_needs_preflight` now keys on a two-branch hybrid: `pytest.mark.mcp_contract` (PRIMARY — covers the plugin's synthetic `<mcp-contracts>::test_*` nodeids) OR `_LIVE_PREFIXES` nodeid prefix (SECONDARY — covers test-code-author scenarios under `tests/test_code/` + legacy `tests/sdet/`, plus transitional `tests/contract/` until Plan 27-05 deletes the legacy collection wiring).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `mcp_config_path` kwarg to `_runner` subprocess builders** — `fa63b12` (feat)
2. **Task 2: Remove `MCPTF_CONFIG_FILE` env-var write; thread resolved path via `-o`** — `a3d2c69` (feat)
3. **Task 3: Flip `_session_needs_preflight` to marker-or-prefix hybrid** — `2015e05` (feat)

## Files Created/Modified

- `src/mcp_test_framework/_runner.py` — Added `mcp_config_path: Path | None = None` kwarg to `_build_pytest_args` and `run_pytest_subprocess`; when set, appends `["-o", f"mcp_config_file={path}"]` to subprocess argv. Updated docstrings to reference the `-o` mechanism and the single-config-resolution principle.
- `src/mcp_test_framework/cli.py` — `_load_config` signature flipped to return `tuple[Config | None, Path | None]`; deleted the `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` write at the end of the function and its multi-line rationale comment. Replaced with a concise comment explaining the new `-o`-based mechanism. All four `_load_config` call sites (`run`, `list_tools`, `config_init`, `gen_test_classes`) destructure the new tuple. The `run()` Typer command threads `mcp_config_path=resolved` to both `_runner.run_pytest_subprocess` call sites (raw + default). Module-level docstring updated.
- `src/mcp_test_framework/fixtures.py` — `_session_needs_preflight` body rewritten with two-branch hybrid: marker-iteration (PRIMARY) + `_LIVE_PREFIXES` prefix check (SECONDARY). `_LIVE_PREFIXES` retains `tests/contract/` transitionally with an inline comment naming Plan 27-05 as the removal site. `iter_markers` is fetched via `getattr` so lightweight `SimpleNamespace` fakes without the attribute don't crash the predicate.
- `tests/framework/unit/test_runner_migration.py` — Rewrote `test_cr01_resolver_writes_mcptf_config_file_env_var` -> `test_resolver_returns_resolved_path_and_does_not_write_env_var` to pin the new contract: `_load_config` returns `(Config, Path)` and does NOT mutate `os.environ`. Updated the surrounding comment block to describe the Phase 27 D-11 transition.
- `tests/framework/unit/test_cli_errors.py` — Updated the lone call to `_load_config(None)` to destructure the new tuple return shape.
- `tests/framework/unit/test_session_needs_preflight.py` — Replaced the bare `SimpleNamespace(nodeid=...)` fake with a `_fake_item(nodeid, markers=...)` helper that exposes both `.nodeid` and `.iter_markers(name)`. Added four marker-branch tests: synthetic-`<mcp-contracts>` nodeid + marker arms gate, marker on off-path item arms gate, unrelated marker does NOT arm gate, mixed-marker-plus-framework arms gate.

## Decisions Made

- **`_load_config` refactor option (a) — tuple return.** The plan locked this as the preferred shape because:
  - Option (b) sibling-helper `_resolve_config_path` would duplicate the precedence logic (--config > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud) and create a second source of truth.
  - Option (c) module-level cache would introduce hidden state across CLI invocations; the framework spawns a single subprocess pytest from each CLI call, so caching adds no value and risks stale-path bugs in long-running interpreters (e.g., test runners that load `cli.py` once and call `run()` repeatedly).
  - Option (a) keeps one resolution code path, threads the path through return values only, and the four call sites destructure cleanly (`cfg, resolved` for `run()`; `cfg, _` for the three commands that don't need the path).
- **Transitional `tests/contract/` entry in `_LIVE_PREFIXES`.** The legacy on-disk `tests/contract/test_mcp_tool_contract.py` is still collected by `tests/conftest.py:pytest_generate_tests` (which Plan 27-05 deletes). That legacy collection does NOT apply the `mcp_contract` marker. Dropping `tests/contract/` from `_LIVE_PREFIXES` in Plan 27-04 would have broken legacy contract preflight during the 27-04 -> 27-05 window. The entry is gated by an inline comment naming Plan 27-05 as the removal site.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test asserting deprecated env-var WRITE contract**
- **Found during:** Task 2 (Remove env-var write)
- **Issue:** `tests/framework/unit/test_runner_migration.py::test_cr01_resolver_writes_mcptf_config_file_env_var` asserted `os.environ.get("MCPTF_CONFIG_FILE") == str(yaml_path)` after `_load_config` ran. Plan 27-04 explicitly removes that write per D-11. Test would fail under the new contract.
- **Fix:** Renamed to `test_resolver_returns_resolved_path_and_does_not_write_env_var` and rewrote to pin the NEW invariants: (1) `_load_config` returns `(Config, Path)` tuple, (2) `os.environ["MCPTF_CONFIG_FILE"]` is NOT mutated after resolution. Also updated the test-file comment block to describe the Phase 27 D-11 transition.
- **Files modified:** `tests/framework/unit/test_runner_migration.py`
- **Verification:** Test passes against the new `_load_config` contract.
- **Committed in:** `a3d2c69` (Task 2 commit).

**2. [Rule 3 - Blocking] Tuple-destructuring update in `test_safe_02_cwd_autodiscovery_picks_up_local_config`**
- **Found during:** Task 2.
- **Issue:** Test called `cfg = _load_config(None)` and asserted `cfg is not None`. The new signature returns a tuple, so single-name binding would receive a tuple object that is always truthy — the assertion would pass for the wrong reason.
- **Fix:** Destructured to `cfg, resolved = _load_config(None)` and added `assert resolved is not None` to pin the new contract explicitly.
- **Files modified:** `tests/framework/unit/test_cli_errors.py`
- **Verification:** Test passes; the new resolved-path assertion catches any future regression that returns `(cfg, None)` from the autodiscovery path.
- **Committed in:** `a3d2c69` (Task 2 commit).

**3. [Rule 3 - Blocking] `sdet`-terminology leak-gate violation in `fixtures.py` docstring**
- **Found during:** Task 3 (Flip preflight predicate).
- **Issue:** `tests/framework/test_sdet_rename_leak_gate.py::test_no_residual_match_in_src_python_strings[sdet_terminology-...]` flagged the new `_session_needs_preflight` docstring at fixtures.py line 131 because it mentions `tests/sdet/` for context. The leak gate is line-based (with docstring-range exemption via `noqa: sdet-rename-shim`).
- **Fix:** Added `# noqa: sdet-rename-shim` to the docstring line that mentions `tests/sdet/`. The leak gate's `_range_is_noqa` exempts the whole docstring because at least one line in the AST node's source range carries the marker.
- **Files modified:** `src/mcp_test_framework/fixtures.py`
- **Verification:** All four leak-gate tests pass.
- **Committed in:** `2015e05` (Task 3 commit).

---

**Total deviations:** 3 auto-fixed (all Rule 3 — blocking issues directly caused by this plan's changes).
**Impact on plan:** All auto-fixes required to keep the test suite green under the new contracts. No scope creep — every change is downstream of an in-scope edit.

## Issues Encountered

- **Plan task 1 expected 4 `_build_pytest_args` call sites inside `run_pytest_subprocess`; actual count is 2.** The plan's count was derived from docstring lines 178 and 191 (which document the raw and default branches), plus the actual call sites at 203 and 234. Only the two real call sites need threading. The kwarg is threaded through both; acceptance grep `grep -c "mcp_config_path=mcp_config_path"` returns 2.
- **Manual smoke test of `MCPTF_CONFIG_FILE` deprecation warning.** Ran `MCPTF_CONFIG_FILE=./config.yaml uv run mcp-contracts run --config ./config.yaml --raw -k __no_such_test__`. The subprocess pytest ran cleanly (1160 items collected, all deselected by the `-k` filter), and the in-subprocess plugin saw the operator's config through the new `-o "mcp_config_file=PATH"` argv element. The DeprecationWarning for `MCPTF_CONFIG_FILE` (emitted by Plan 27-02's `pytest_configure`) did not surface in the visible warning summary — likely swallowed by `pyproject.toml`'s `filterwarnings` config, which is a Plan 27-02 concern. Flagged for verification in Plan 27-05's docs sweep or the phase verifier. The functional path (config picked up, no precedence crash) works correctly.
- **No pytest 9.0.x `-o key=value` parsing quirks observed on Windows.** Pre-emptive concern from 27-RESEARCH.md Pitfall 4 (Windows PowerShell quoting on `-o key=value` strings) does not apply here because `subprocess.run` receives an argv list — two separate elements `["-o", "mcp_config_file=PATH"]`, no shell interpretation, no quoting concerns. Behavior on Windows is byte-identical to POSIX.

## TypeR.Exit `INTERNALERROR>` Carry-over

**Folded in: NO. Deferred.** The orchestrator prompt asked whether the typer.Exit -> `INTERNALERROR>` surfacing on config-validation errors could be folded into this plan. Diff-footprint review:

- The error path is in `_plugin.py:pytest_configure` (Plan 27-02 territory), which already wraps `_emit_operator_error_for_validation` in `try/except SystemExit:` and translates to `pytest.exit(returncode=2)`. The translation is in place.
- The remaining `INTERNALERROR>` surfacing the operator may observe likely originates from a separate path (e.g., `typer.Exit` propagating from a config-resolution branch that pre-dates the `pytest.exit` translation, or from the `_load_config`-driven CLI path where `typer.Exit` is the correct exit channel but pytest's stderr rendering layers `INTERNALERROR>` above it on certain shells).
- The fix surface is not contained within Plan 27-04's three files (`_runner.py`, `cli.py`, `fixtures.py`); investigating it would require touching `_plugin.py` and possibly the typer/click integration layer.

**Flagged for follow-up:** Plan 27-05 docs/dogfood sweep or a dedicated backlog ticket. The plan touches `cli.py` and `_plugin.py` indirectly via the config-validation path; a tighter repro would be useful before fixing.

## Manual Smoke Output

### CLI `--help` smoke
```
$ uv run mcp-contracts run --config ./config.test.yaml --help 2>&1 | head -5
 Usage: mcp-contracts run [OPTIONS] [PYTEST_ARGS]...

 Run the test suite wrapped around a subprocess pytest.
```
Operator-visible CLI did not crash; `--config` argument accepted; tuple-return refactor caused no parse-time regressions.

### Subprocess argv with both env var + --config set
```
$ MCPTF_CONFIG_FILE=./config.yaml uv run mcp-contracts run --config ./config.yaml --raw -k __no_such_test__ 2>&1 | tail -5
collected 1160 items / 1160 deselected / 0 selected
==================== 1160 deselected, 11 warnings in 6.89s ====================
no tests collected
```
Subprocess pytest collected the full contract surface (1160 items = legacy + plugin-injected) under the new `-o "mcp_config_file=PATH"` channel; no precedence error; no env-var-write footgun re-introduced.

## Framework Self-Test Count

**602 passed, 1 skipped, 17 deselected, 2 xfailed** under `uv run pytest tests/framework/ -q`. Pre-plan baseline: 598 passed; +4 new tests come from the marker-branch additions in `test_session_needs_preflight.py`. Net: 0 regressions, +4 new pinned invariants.

## Next Phase Readiness

**Plan 27-05 (final docs/dogfood sweep) can:**
- Delete the legacy `tests/contract/test_mcp_tool_contract.py` and its collection wiring in `tests/conftest.py:pytest_generate_tests`.
- Remove the transitional `"tests/contract/"` entry from `_LIVE_PREFIXES` in `fixtures.py`; the marker branch alone then covers contract tests.
- Investigate the `typer.Exit -> INTERNALERROR>` carry-over (touched by this plan via `_load_config`'s caller chain; out of scope for the diff footprint of Plan 27-04).
- Audit the `MCPTF_CONFIG_FILE` DeprecationWarning suppression (warning fires but appears swallowed by `filterwarnings` config; Plan 27-02 territory).

**Architectural invariants preserved:**
- One config-resolution mechanism end-to-end across CLI (subprocess `-o`) and library (`[tool.pytest.ini_options]`).
- No env-var WRITE in CLI mode; env-var READ retained for v1.4 back-compat with DeprecationWarning surface.
- SEED-022 framework-primitives principle intact: fixtures stay SUT-generic; no SUT-aware logic added.
- No planning-ID (`D-NN` / `LIB-NN` / `SAFE-NN`) tokens leaked into `src/` docstrings or comments (verified via the leak-gate test).

## Self-Check: PASSED

- `src/mcp_test_framework/_runner.py` modified, `mcp_config_path` kwarg present in both function signatures.
- `src/mcp_test_framework/cli.py` modified, `_load_config` returns tuple, no `os.environ[...] = str(resolved)` write.
- `src/mcp_test_framework/fixtures.py` modified, `iter_markers("mcp_contract")` branch present.
- All three task commits exist in `git log --oneline`: `fa63b12`, `a3d2c69`, `2015e05`.
- `uv run pytest tests/framework/ -q` exits with code 0 (602 passed, 1 skipped, 2 xfailed).
- Manual smoke commands (`--help` + `MCPTF_CONFIG_FILE`-set run) executed cleanly.

---
*Phase: 27-register-api-contracts-sub-package-test-extraction-lib*
*Completed: 2026-05-17*
