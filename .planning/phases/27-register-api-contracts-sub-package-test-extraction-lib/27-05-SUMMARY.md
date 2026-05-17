---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
plan: 05
subsystem: testing
tags: [dogfood, deletion, docstring-sweep, ast-guard, requirements, roadmap, library-mode]

# Dependency graph
requires:
  - phase: 27-02
    provides: plugin pytest_configure reads mcp_config_file ini -> Config(yaml_file=path) -> _mcp_contracts_config stash
  - phase: 27-03
    provides: plugin synthesizes <mcp-contracts> module + applies mcp_contract marker per item
  - phase: 27-04
    provides: CLI subprocess pytest -o "mcp_config_file=PATH"; _session_needs_preflight marker hybrid
provides:
  - framework dogfoods library mode via [tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"
  - legacy on-disk tests/contract/ collection path fully deleted; tests/conftest.py hollowed to docstring-only (D-17)
  - contracts/__init__.py documents ini route end-to-end; no register() API; no public exports
  - _LIVE_PREFIXES drops transitional tests/contract/ entry; marker branch alone covers contract tests
  - wheel-introspection guard upgraded to ast.parse + ast.walk over Import/ImportFrom (LIB-08 AST-walk language satisfied verbatim); Pitfall 6 ironic-leak guard asserts _black_box_guard.py is in wheel AND scanned
  - REQUIREMENTS.md + ROADMAP.md amended for ini-route pivot; LIB-05 + CFG-02 explicitly Removed; CFG-01 closes in Phase 27; Phase 28 scope shrunk; Phase 30 CLOSE-01 reframed to verify already-landed dogfood
affects: [28, 30]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "framework dogfood via pyproject ini line — every CI run is a live operator simulation against the plugin path"
    - "ast.walk(ast.parse(source)) over Import/ImportFrom nodes for banned-SUT detection inside wheel sources"
    - "docstring-only conftest.py demonstrating D-17 zero-ceremony invariant"

key-files:
  created:
    - .planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-05-SUMMARY.md
    - config.test.yaml  (rewritten from v1 to v2 schema with tools: {})
  modified:
    - pyproject.toml
    - src/mcp_test_framework/contracts/__init__.py
    - src/mcp_test_framework/fixtures.py
    - tests/conftest.py  (hollowed to docstring-only, Option A)
    - tests/framework/test_wheel_shape.py
    - tests/framework/test_runner_subprocess.py
    - tests/framework/test_tool_config.py
    - tests/framework/unit/test_runner_migration.py
    - tests/framework/unit/test_runner_pre_run_digest.py
    - tests/framework/unit/test_session_needs_preflight.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
  deleted:
    - tests/contract/test_mcp_tool_contract.py

key-decisions:
  - "Option A (docstring-only conftest.py) over Option B (delete entirely). Picked because tests/conftest.py is the strongest place to demonstrate the D-17 zero-ceremony invariant in living code — operators landing on the repo see a real file with a docstring explaining 'why is this empty', whereas a missing file forces them to dig through git history to understand the framework's plugin auto-load convention."
  - "config.test.yaml rewritten from v1 schema (version: 1, target: block, 50+ tool skip entries) to a minimal v2 framework-CI config with tools: {} (empty opt-in allowlist). The empty allowlist triggers the plugin's silent no-inject branch — framework CI exercises every plugin code path that does NOT need a live MCP server, which is the strongest dogfood proof point at the CI-tier (no uvx homelab-mcp required on the runner)."
  - "Wheel-introspection AST guard upgrade was MANDATORY: pre-edit grep returned 0 for ast.parse/walk/NodeVisitor; post-edit returns 4. LIB-08's spec language 'wheel-introspection AST-walk CI test fails on banned SUT imports' was not satisfied by the prior line-prefix grep. The upgrade also added an explicit Pitfall 6 regression assertion (assert _black_box_guard.py in wheel sources) so the file whose whole job is to enforce the black-box rule cannot itself sneak in a banned import."
  - "5 Rule-1 framework self-test repairs absorbed into Task 2 and Task 3 commits (test_runner_migration.py SAFE-01 tests rewritten; test_tool_config.py call_arguments + skip-filter tests retargeted; test_runner_subprocess.py pytest_plugins regression inverted; test_runner_pre_run_digest.py _CONTRACT_FILE retargeted to mcp_test_framework.contracts._tests via __file__; test_session_needs_preflight.py two tests retargeted from path-prefix branch to marker branch). All downstream of in-scope deletions; no scope creep."
  - "typer.Exit -> INTERNALERROR> carry-over from Plan 27-04 NOT folded in. Plan 27-05's diff footprint touches contracts/__init__.py, fixtures.py, tests/contract/, tests/conftest.py, _LIVE_PREFIXES, test_wheel_shape.py, and the planning docs — none of which include _plugin.py:pytest_configure (Plan 27-02 territory) where the typer.Exit translation lives. Plan 27-04 already landed the try/except SystemExit -> pytest.exit(returncode=2) translation; if residual INTERNALERROR> still surfaces it likely originates from a separate code path. Flagged for follow-up backlog."

patterns-established:
  - "Framework dogfood via pyproject [tool.pytest.ini_options] ini line — the strongest possible regression coverage for the library-mode contract surface. Operator-equivalent path is exercised on every uv run pytest."
  - "AST-walk for SUT-import detection in wheel introspection — catches concatenated, conditional (TYPE_CHECKING), aliased, and inside-function-body imports that line-prefix grep misses."

requirements-completed: [LIB-03, LIB-05 (Removed), CFG-01, CFG-02 (Removed)]

# Metrics
duration: 20min
completed: 2026-05-17
---

# Phase 27 Plan 05: Move-and-dogfood + docs sweep + close-out Summary

**Framework dogfoods library mode via `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"`; legacy `tests/contract/` collection path deleted; `tests/conftest.py` hollowed to docstring-only; wheel-guard upgraded to AST walk; REQUIREMENTS + ROADMAP amended for the ini-route pivot — Phase 27 closes end-to-end with one config-resolution mechanism across CLI and library modes.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-17T00:49Z
- **Completed:** 2026-05-17T01:08Z
- **Tasks:** 4
- **Files modified:** 11 (5 src/, 5 tests/, 2 planning docs) + 1 deleted + 1 rewritten (config.test.yaml)

## Accomplishments

- **Framework CI dogfood activated (Task 1)** — `pyproject.toml` now sets
  `mcp_config_file = "./config.test.yaml"` under `[tool.pytest.ini_options]`.
  Every `uv run pytest` against the framework root exercises the plugin's
  `pytest_configure` -> `Config(yaml_file=...)` -> `check_black_box()` ->
  `pytest_collection` -> silent-no-inject path end-to-end. Migrated
  `config.test.yaml` from v1 schema to a minimal v2 framework-CI config
  with `tools: {}` (empty opt-in allowlist; no live MCP server needed).
- **Legacy collection path deleted (Task 2)** — `tests/contract/test_mcp_tool_contract.py`
  removed; `tests/conftest.py` hollowed to docstring-only (Option A).
  All four legacy responsibilities (`pytest_plugins` list, `pytest_configure`
  black-box guard body, `_discover_tools` / `_resolve_tool_names`
  helpers, `pytest_generate_tests` indirect parametrize) are now owned
  exclusively by `src/mcp_test_framework/_plugin.py` +
  `_black_box_guard.py`.
- **Plugin housekeeping (Task 3)** — `src/mcp_test_framework/contracts/__init__.py`
  rewritten to document the ini-driven route end-to-end (no `register()` API;
  no public exports; docstring-only). `_LIVE_PREFIXES` in `fixtures.py`
  drops the transitional `tests/contract/` entry — the `mcp_contract`
  marker is now the load-bearing detection channel for contract tests.
  `tests/framework/test_wheel_shape.py::test_wheel_source_has_no_homelab_mcp_imports`
  upgraded from line-prefix grep to `ast.parse` + walk over
  `ast.Import` / `ast.ImportFrom` (LIB-08 AST-walk language satisfied
  verbatim) + Pitfall 6 ironic-leak guard (`assert _black_box_guard.py`
  in wheel sources).
- **Documentation amendments (Task 4)** — REQUIREMENTS.md LIB-01..08 +
  CFG-01..02 + Traceability table rewritten per CONTEXT.md `<downstream_impact>`;
  LIB-05 + CFG-02 explicitly marked Removed. ROADMAP.md milestone goal
  text, Phase 27 title + Goal + SC1..5, Phase 28 scope shrink, Phase 30
  CLOSE-01 reframe all landed. Future Requirements + Out of Scope bullets
  that referenced `register()` reframed to ini-shape. Cross-phase audit:
  Phase 28/29/30 `**Plans**:` lines remain at `TBD`; zero 27-0X plan IDs
  leaked into adjacent phase blocks.

## Task Commits

Each task was committed atomically:

1. **Task 1: Dogfood library-mode via pyproject ini** — `d7b8d57` (feat)
2. **Task 2: Delete legacy contract collection path; hollow tests/conftest.py** — `eb00f8d` (feat)
3. **Task 3: contracts/__init__ docstring; drop transitional tests/contract/; AST-walk wheel guard** — `d0593ac` (feat)
4. **Task 4: Amend REQUIREMENTS + ROADMAP for ini-route pivot** — `fc33ecb` (docs)

## Dogfood + CLI Smoke Verification

### Dogfood smoke (top-level `uv run pytest`)

`uv run pytest --collect-only -q` against the framework root collects
**604 framework tests** (matches Plan 27-04 baseline; +2 from earlier
deletions netting against earlier additions) with **zero
`<mcp-contracts>` items injected** — the plugin's `pytest_configure`
loads `config.test.yaml`, runs the black-box guard, and
`pytest_collection` short-circuits cleanly because
`tools: {}` produces an empty opt-in allowlist (silent no-inject per
D-16). Every plugin code path that does NOT need a live MCP server is
exercised on every framework CI run. End-to-end: PASS.

### CLI mode smoke (`mcp-contracts run --config config.yaml`)

`uv run mcp-contracts run --config config.yaml --raw -k __no_such_test__`:
```
collected 580 items / 580 deselected / 0 selected
=========================== 580 deselected in 3.67s ===========================
```
The subprocess pytest sees the operator's `config.yaml` via the
`-o "mcp_config_file=PATH"` channel landed in Plan 27-04; the plugin
injects 580 `<mcp-contracts>::test_<name>[<tool>]` items (58 tools x 10
contract tests). Direct verification via
`uv run pytest -o "mcp_config_file=config.yaml" --collect-only -q`
confirms the nodeids render verbatim as `<mcp-contracts>::test_*[<tool>]`.
End-to-end: PASS.

## Wheel-introspection AST guard verification (LIB-08)

- **Pre-edit grep:** `grep -cE 'ast\.(parse|walk|NodeVisitor)' tests/framework/test_wheel_shape.py` returned **0**.
- **Post-edit grep:** returns **4** (`ast.parse`, `ast.walk`, `ast.Import` / `ast.ImportFrom` references in the new `_ast_homelab_imports` helper).
- **Pitfall 6 ironic-leak guard:** explicit `assert "mcp_test_framework/_black_box_guard.py" in py_sources` before the AST scan loop. If the file is renamed or excluded from the wheel, the assertion fires before the silent-skip can hide a leak.
- **Test outcome:** `uv run pytest tests/framework/test_wheel_shape.py -q` returns **11 passed**.

## Rule-1 Deviations (5 framework self-test repairs)

Downstream of in-scope deletions; no scope creep. Each is the minimum
change needed to keep the test green under the new contract.

### 1. `tests/framework/unit/test_runner_migration.py` — SAFE-01 allowlist tests
- **Found during:** Task 2 (Delete `tests/conftest.py:_resolve_tool_names`).
- **Issue:** Three tests imported `_resolve_tool_names` from the deleted helper.
- **Fix:** Rewrote tests to call a local `_allowed_tools(cfg)` helper that mirrors the plugin's inline filter (`sorted(name for name, tcfg in cfg.tools.items() if not tcfg.skip)`). Module docstring updated to reference the relocated filter.
- **Committed in:** `eb00f8d`.

### 2. `tests/framework/test_tool_config.py` — two retargets
- **Found during:** Task 2.
- **Issue (a):** `test_resolve_tool_names_filters_out_skip_true_tools` imported the deleted helper.
- **Fix (a):** Renamed to `test_allowlist_filters_out_skip_true_tools`; rewrote to use the inline filter shape inline. Dropped the sibling `xfail` test `test_resolve_tool_names_explicit_target_overrides_skip_true` (Phase 13 v2-schema removed `target:` long ago; the xfail was load-bearing on a deleted feature).
- **Issue (b):** `test_call_arguments_forwarded_to_call_tool_via_asyncmock` imported `test_empty_args_call_returns_non_error` from the deleted contract file.
- **Fix (b):** Repointed the import to `mcp_test_framework.contracts._tests` (the wheel-shipped module the plugin injects). Fixture-name renames are positional; SimpleNamespace fakes still bind.
- **Committed in:** `eb00f8d`.

### 3. `tests/framework/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter`
- **Found during:** Task 2.
- **Issue:** Test asserted the deleted `pytest_plugins = ["mcp_test_framework.fixtures"]` line was present in `tests/conftest.py`.
- **Fix:** Inverted the test to pin the new invariant — `tests/conftest.py` declares NO `pytest_plugins` list (the entry-point load path is the only mechanism). Updated docstring to reference Phase 27 D-17.
- **Committed in:** `eb00f8d`.

### 4. `tests/framework/unit/test_runner_pre_run_digest.py` — `_CONTRACT_FILE` retarget
- **Found during:** Task 2.
- **Issue:** Module-level constant resolved a stale on-disk path `tests/contract/test_mcp_tool_contract.py` that no longer exists.
- **Fix:** Retargeted via `Path(mcp_test_framework.contracts._tests.__file__)` — the same canonical contract surface the plugin's `pytest_collection` synthesizes its `_ContractsModule` from. The AST drift-guard now pins the wheel-shipped module, not a stale on-disk copy.
- **Committed in:** `eb00f8d`.

### 5. `tests/framework/unit/test_session_needs_preflight.py` — two test repurposes
- **Found during:** Task 3 (Remove transitional `tests/contract/` from `_LIVE_PREFIXES`).
- **Issue:** Two tests pinned the transitional path-prefix branch that Plan 27-05 removes.
- **Fix:** `test_one_contract_item_returns_true` inverted to `test_legacy_tests_contract_prefix_is_not_live_scope` (assert that bare `tests/contract/` nodeid with no marker does NOT arm preflight). `test_mixed_unit_plus_contract_returns_true` rewritten to use the `mcp_contract` marker channel instead of the dropped path prefix; renamed to `test_mixed_unit_plus_marked_contract_returns_true`.
- **Committed in:** `d0593ac`.

## REQUIREMENTS Traceability Audit

Cells flipped this plan:

| REQ ID | Old Status | New Status |
|--------|------------|------------|
| LIB-05 | Pending | **Removed (Phase 27 D-01)** |
| CFG-01 | Pending (Phase 28) | **Complete (Phase 27)** |
| CFG-02 | Pending (Phase 28) | **Removed (Phase 27 D-01)** |

Cells already marked Complete by Plans 27-01..04 (sanity-check audit):
LIB-01, LIB-02, LIB-03, LIB-04, LIB-06, LIB-07, LIB-08 — all `Complete (Phase 27)`.

## ROADMAP Amendments (Phase 28 / 30 follow-on cascade flags)

- **Phase 28 scope shrunk** — title now "Codegen output path (CODEGEN)";
  Requirements collapsed from `CFG-01, CFG-02, CODEGEN-LIB-01, CODEGEN-LIB-02`
  to `CODEGEN-LIB-01, CODEGEN-LIB-02`. SC1 + SC2 (env-var-ignore + register
  escape-hatch) removed. **Follow-on cascade:** Phase 28 planner should
  treat the phase as a 2-req focused capability rather than the
  originally-scoped 4-req config+codegen bundle. No new requirements
  introduced; the scope correction does not require renumbering.
- **Phase 30 CLOSE-01 reframed** — was "framework's `tests/contract/conftest.py`
  calls `register()`"; now verifies the already-landed dogfood
  (`pyproject.toml` ini line). **Follow-on cascade:** Phase 30 planner
  should treat CLOSE-01 as a pre-emption verification check rather than
  net-new dogfood work. CLOSE-02 reframed against the ini route (CLI/library
  parity via JUnit XML equivalence, not via `register()` kwarg/Typer flag
  parity). CLOSE-03 + CLOSE-04 require the README rewrite to lead with the
  ini line rather than `register()`; documentation surgery only.
- **No Phase 29 amendments needed** — REPORTER-01/02 are orthogonal to
  the config-route pivot.

## typer.Exit `INTERNALERROR>` Carry-over

**Folded in: NO. Deferred.**

Plan 27-05's diff footprint touches `contracts/__init__.py`, `fixtures.py`,
`tests/contract/`, `tests/conftest.py`, `_LIVE_PREFIXES`,
`test_wheel_shape.py`, and the planning docs. None include
`_plugin.py:pytest_configure` (Plan 27-02 territory) where the
`typer.Exit -> pytest.exit(returncode=2)` translation already lives.

Plan 27-04 landed the `try / except SystemExit:` translation in the plugin's
validation error path. If a residual `INTERNALERROR>` still surfaces it
likely originates from a different code path (e.g., `typer.Exit`
propagating from a CLI-resolution branch that pre-dates the
`pytest.exit` translation, or from `_load_config`'s caller chain where
`typer.Exit` is the correct exit channel but pytest's stderr rendering
layers `INTERNALERROR>` above it on certain shells).

**Flagged for follow-up:** backlog ticket. A tighter repro is needed
before fixing.

## Framework Self-Test Count

**602 passed, 1 skipped, 17 deselected, 1 xfailed** under
`uv run pytest tests/framework/ -q`.

- Pre-plan baseline (Plan 27-04): 602 passed, 1 skipped, 17 deselected,
  2 xfailed.
- Delta: -1 xfailed (dropped the `target:`-schema xfail in
  `test_tool_config.py` whose feature was removed in Phase 13 v2-schema
  rework). Net +0 regressions.

## config.test.yaml schema migration

**Migration required: YES.** The pre-Plan-27 file was v1 schema:
- `version: 1`
- `target:` block with `tool_name: ""`
- 50+ `tools.<name>` entries with `skip: true` + `skip_reason`

The plugin's `Config(yaml_file=...)` loader would have failed under v1
with a canonical version-mismatch error (`config version 1 not supported
by this build, expected 2`). Rewrote in-place with a minimal v2
framework-CI config:

```yaml
version: 2

ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
  timeout_seconds: 120

mcp_server:
  command: uvx
  args: [homelab-mcp]
  timeout_seconds: 30

judge_timeout_seconds: 120

test_code:
  generated_root: "tests/test_code/_generated"

tools: {}
```

`tools: {}` is the strongest dogfood proof point — exercises every
plugin code path that does NOT need a live MCP server. `test_code.generated_root`
is REQUIRED by v2 schema; pointed at a path that doesn't need to exist
for the silent-no-inject branch.

## Next Phase Readiness

**Phase 27 closes end-to-end.** All eight LIB-NN requirements addressed
(6 Complete, 1 Removed, 1 Removed); CFG-01 closes in Phase 27 (D-01
pivot); CFG-02 Removed. The orchestrator can run `/gsd-verify-phase 27`
to gate the milestone-position advance.

**Phase 28 unblocked** with reduced scope: only CODEGEN-LIB-01 +
CODEGEN-LIB-02 remain. The phase planner should treat the config seam
as already-closed and focus on `gen-test-classes` output-path policy
end-to-end.

**Phase 30 partially pre-empted** by Phase 27 D-06 (framework dogfood
already landed). CLOSE-01 reframed to a verification check; CLOSE-02..04
remain net-new docs/parity work.

**Architectural invariants preserved end-to-end:**
- ONE config-resolution mechanism end-to-end across CLI (subprocess `-o`)
  and library (`[tool.pytest.ini_options]`).
- NO `MCPTF_CONFIG_FILE` env-var WRITE in CLI mode; env-var READ retained
  for v1.4 back-compat with DeprecationWarning surface (Plan 27-04 +
  27-02).
- SEED-022 framework-primitives principle intact: every change is
  SUT-generic; the wheel-introspection AST guard explicitly verifies no
  banned imports leak anywhere inside `src/`.
- D-17 zero-ceremony invariant demonstrated in living code: framework's
  own `tests/conftest.py` is docstring-only.
- No planning-ID (`D-NN` / `LIB-NN` / `CFG-NN` / `SAFE-NN`) tokens leaked
  into `src/` docstrings or comments — verified by the leak-gate test.

## Self-Check: PASSED

- All four task commits present in `git log --oneline`: `d7b8d57`, `eb00f8d`, `d0593ac`, `fc33ecb`.
- `pyproject.toml` contains the documented `mcp_config_file = "./config.test.yaml"` ini line under `[tool.pytest.ini_options]`.
- `tests/contract/test_mcp_tool_contract.py` is DELETED on disk (verified `test ! -f` returns 0).
- `tests/conftest.py` is hollowed (no `pytest_plugins`, no `pytest_configure`, no `pytest_generate_tests`; docstring-only).
- `src/mcp_test_framework/contracts/__init__.py` is docstring-only (0 lines start with `def`, `class`, `import`, or `from`) and contains the documented `register()` mention exactly 1 time (the "intentionally NO register() API" line).
- `src/mcp_test_framework/fixtures.py:_LIVE_PREFIXES` no longer contains `tests/contract/`; contains `tests/test_code/` + `tests/sdet/` only.
- `tests/framework/test_wheel_shape.py` AST-walk grep returns 4 (>=1 required); `_black_box_guard.py` Pitfall 6 ironic-leak guard present.
- `uv run pytest tests/framework/ -q` exits 0 (602 passed / 1 skipped / 17 deselected / 1 xfailed).
- `uv run pytest --collect-only -q` (dogfood) emits zero `<mcp-contracts>` items (silent no-inject with `tools: {}`); no plugin errors.
- `uv run mcp-contracts run --config config.yaml --raw -k __no_such_test__` (CLI smoke) collects 580 contract items via subprocess `pytest -o "mcp_config_file=PATH"`; nodeids render as `<mcp-contracts>::test_<name>[<tool>]`.
- REQUIREMENTS.md: LIB-05 + CFG-02 marked `Removed (Phase 27 D-01)` in Traceability table; CFG-01 marked `Complete (Phase 27)`.
- ROADMAP.md: milestone goal text contains "Pytest-native MCP contract testing"; Phase 27 title contains "pytest-native ini config"; Phase 27 SC2 contains `<mcp-contracts>::test_*` nodeid shape; Phase 28 Requirements line collapsed to `CODEGEN-LIB-01, CODEGEN-LIB-02`; Phase 30 SC1 references "Phase 27 D-06 / D-07"; Phase 28/29/30 `Plans` lines remain at `TBD`.

---
*Phase: 27-register-api-contracts-sub-package-test-extraction-lib*
*Completed: 2026-05-17*
