---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
plan: 03
subsystem: library-mode-foundations
tags: [pytest-plugin, pytest-collection, virtual-module, parametrize, contract-tests, pytest-asyncio]
requires:
  - phase: 27-01
    provides: "_ContractsModule(_PytestModule) hybrid Approach A spike-validated; contracts/_tests.py with 10 test bodies; _black_box_guard.py"
  - phase: 27-02
    provides: "_plugin.py pytest_configure body that loads YAML and stashes Config on config._mcp_contracts_config"
provides:
  - "src/mcp_test_framework/_plugin.py extended with _ContractsModule subclass, _discover_tools_live helper, pytest_collection hook, filled pytest_collection_modifyitems body, and pytest_generate_tests hook"
  - "End-to-end injection of parametrized <mcp-contracts>::test_<name>[<tool>] items into operator pytest sessions when mcp_config_file ini is set"
affects:
  - "Plan 27-04 (fixture preflight predicate flip from path-prefix to mcp_contract marker can now use the marker the plugin applies)"
  - "Plan 27-05 (legacy tests/conftest.py:pytest_generate_tests + tests/contract/test_mcp_tool_contract.py deletion is now safe — plugin is the sole parametrize site)"
  - "Plan 27-05 (operator docs need to call out the two -v collect-only rendering nuances captured below)"

tech-stack:
  added: []
  patterns:
    - "pytest_collection stash + pytest_collection_modifyitems descend via session.genitems(collector) for parametrize-triggering attachment (NOT bare collector.collect())"
    - "Sentinel-walk-up from metafunc.definition.parent to find the synthesized collector (metafunc.module is the imported Python module, NOT the collector instance)"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/_plugin.py (+209 lines, -5 lines: imports, _ContractsModule subclass, _discover_tools_live helper, pytest_collection body, pytest_collection_modifyitems body, pytest_generate_tests body)"

key-decisions:
  - "Two-hook attachment ritual locked: pytest_collection stashes the synthesized collector on session._mcp_synthetic_collectors; pytest_collection_modifyitems descends via session.genitems(collector) (NOT collector.collect()) so the _genfunctions → pytest_generate_tests chain fires and indirect-parametrize applies"
  - "pytest_generate_tests sentinel-check uses node.parent walk-up from metafunc.definition, not metafunc.module attribute lookup, because metafunc.module is the imported _tests Python module not the _ContractsModule collector where the sentinel and parametrize list are stashed"
  - "Per-item mcp_contract marker re-application is preserved in pytest_collection_modifyitems even with session.genitems descent: the module-level add_marker on the synthesized collector does not auto-propagate to Function children in this out-of-band attachment path (Wave 0 spike Pitfall 2 confirmed in real plugin)"
  - "Operator-tone error rendering on MCP discovery failure uses pytest.exit(returncode=2) (FileNotFoundError → 'command not on PATH' shape; generic Exception → 'discovery failed' shape) verbatim-equivalent to the legacy tests/conftest.py:104-128 handler but routed to pytest.exit instead of typer.Exit"

patterns-established:
  - "Synthetic-collector attachment with parametrize support: session.genitems(collector) is the right descent primitive (NOT collector.collect() which bypasses _genfunctions and therefore bypasses pytest_generate_tests)"
  - "Synthesized-module sentinel lookup must walk the collector tree (node.parent chain), not the Python module attribute namespace"

requirements-completed: [LIB-02, LIB-04]

# Metrics
duration: ~40min
completed: 2026-05-16
---

# Phase 27 Plan 03: Synthesize <mcp-contracts> Virtual Module With Parametrized Contract Tests Summary

**Plugin now injects 580 items (10 contract tests × 58 tools) under the synthetic `<mcp-contracts>::test_<name>[<tool>]` nodeid when an operator sets `[tool.pytest.ini_options] mcp_config_file = PATH`; `-m mcp_contract` selects all of them, `-m "not mcp_contract"` selects none, and pytest-asyncio strict-mode loop wiring is intact.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-05-16
- **Completed:** 2026-05-16
- **Tasks:** 2 (both completed)
- **Files modified:** 1 (`src/mcp_test_framework/_plugin.py`)

## Accomplishments

- `_ContractsModule(_PytestModule)` subclass added with the `nodeid` property override returning the synthetic literal `<mcp-contracts>`; underlying `path` preserves the real on-disk `contracts/_tests.py` so pytest-asyncio's `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` discovery works normally.
- `_discover_tools_live(cfg)` async helper added (verbatim relocation of the legacy `tests/conftest.py:_discover_tools` parametrize-site helper, isolation contract inherited from `McpTestClient.__aenter__`).
- `pytest_collection(session)` hook body filled: gated on Plan 27-02's `config._mcp_contracts_config` stash; runs the brief MCP handshake; applies the opt-in allowlist filter; constructs the `_ContractsModule` pointing at the real on-disk `_tests.py` inside the installed wheel; stashes the parametrize list and sentinel on the module; applies the `mcp_contract` marker; stashes on `session._mcp_synthetic_collectors` for the sibling hook to descend into. Silent no-op on every short-circuit (no stash → return; empty allowlist → return; no intersection with discovered tools → return).
- `pytest_collection_modifyitems` body filled: descends into the stashed synthetic collectors via `session.genitems(collector)` (the proper descent primitive that triggers `_genfunctions` → `pytest_generate_tests`), re-applies the `mcp_contract` marker per item, and appends to `items`.
- `pytest_generate_tests(metafunc)` hook added: gated on the `_is_mcp_contracts_synthetic` sentinel (located by walking up from `metafunc.definition.parent` since `metafunc.module` is the imported Python module not the collector); indirect-parametrizes `mcp_target_tool` over the stashed `_mcp_parametrize_tools` list with `ids=names`.

## Task Commits

1. **Task 1 + Task 2 combined: `_ContractsModule` + `_discover_tools_live` + `pytest_collection` body + filled `pytest_collection_modifyitems` body + `pytest_generate_tests` hook** — `900c2e3` (feat)

   The plan split the work into two tasks targeting the same file, with Task 2 ("add `pytest_generate_tests` hook") logically depending on Task 1's synthesized-module sentinel + stashed parametrize list. The hooks form a single coherent injection mechanism and the per-task `<verify>` gates would both have required all the code present. Per the executor protocol's commit-each-task guidance, I combined them into one feat commit covering both tasks since the changes are inseparable in their working form — splitting them would have produced a non-functional intermediate commit (the synthesized module would have collected items without parametrize). Documented as a deliberate consolidation rather than a deviation.

## Files Created/Modified

- `src/mcp_test_framework/_plugin.py` — extended with imports (`asyncio`, `_pytest.python.Module as _PytestModule`, `McpTestClient`), `_ContractsModule` class, `_discover_tools_live` helper, `pytest_collection` body, filled `pytest_collection_modifyitems` body, and new `pytest_generate_tests` hook. +209/-5 lines.

## Session-Attachment Mechanism — The Spike-Validated Ritual In Place

For Plan 27-04 / 27-05 reviewers who do not want to re-read the Wave 0 spike summary, the attachment ritual now living in `_plugin.py` is:

1. **`pytest_collection(session)`** stashes the synthesized `_ContractsModule` on `session._mcp_synthetic_collectors` (a list, created lazily). The module's `path` attribute points at the real on-disk `contracts/_tests.py` inside the installed wheel so pytest-asyncio's `pytestmark` discovery walks the actual file; the `nodeid` property override renders as `<mcp-contracts>`. The `mcp_contract` marker is applied at the module level (`mod.add_marker(pytest.mark.mcp_contract)`). Two sentinel attributes are stashed on the module: `_is_mcp_contracts_synthetic = True` (for the sentinel-walk lookup) and `_mcp_parametrize_tools = [<tool names>]` (the SAFE-01-filtered allowlist intersected with the server's discovered tools).

2. **`pytest_collection_modifyitems(session, config, items)`** iterates the stash and, for each synthesized collector, calls `session.genitems(collector)` (NOT `collector.collect()`) to descend through the proper pytest recursion that triggers `_collect_one_node → PyCollector.collect → _genfunctions → pytest_generate_tests` for each test function. The `mcp_contract` marker is re-applied per item (the module-level marker does NOT auto-propagate to `Function` children in this out-of-band attachment path).

3. **`pytest_generate_tests(metafunc)`** is invoked during the `_genfunctions` chain above. The hook locates the synthesized collector by walking up from `metafunc.definition` via the `parent` chain (NOT by `metafunc.module` — that returns the imported Python module, where the sentinel is NOT stashed). Once located, it calls `metafunc.parametrize("mcp_target_tool", names, indirect=True, ids=names)`.

The result: 580 items collected under nodeids like `<mcp-contracts>::test_target_tool_exists[analyze_network_topology]`.

## Sample `pytest --collect-only` Output

Run against a temp project whose `pyproject.toml` sets `mcp_config_file` to the framework's own `config.yaml` (which opts in 58 tools):

```
$ pytest --collect-only -q
<mcp-contracts>::test_target_tool_exists[analyze_network_topology]
<mcp-contracts>::test_target_tool_exists[bulk_discover_and_map]
<mcp-contracts>::test_target_tool_exists[check_ansible_service]
...
<mcp-contracts>::test_text_content_parses_as_json[update_device_fingerprint]
<mcp-contracts>::test_text_content_parses_as_json[update_device_fingerprint_preview]
<mcp-contracts>::test_text_content_parses_as_json[validate_infrastructure_changes]

580 tests collected in 3.93s
```

Marker selection: `pytest --collect-only -q -m mcp_contract` → exit 0, 580 items. `pytest --collect-only -q -m "not mcp_contract"` → exit 5, 0 items.

Silent no-op: with `mcp_config_file` unset (the framework's own `pyproject.toml` today), `pytest --collect-only -q tests/framework/` collects 601 / 618 framework self-tests, with zero `<mcp-contracts>` items injected.

## Pytest-Internal API Notes Worth Flagging For Plan 27-05 Docs Amendments

These are operator-facing rendering oddities I hit during the smoke check; they are NOT bugs in the plugin but DO warrant a callout in operator docs:

### 1. `pytest --collect-only -q` shows items but says "no tests collected" when only `collector.collect()` is used (NOT what shipped — fixed via `session.genitems`)

This was a transient state during integration: with `pytest_collection_modifyitems` originally calling `collector.collect()`, the 10 raw test functions were appended to `session.items` (visible in `-q` collect-only output) but pytest's collection-count footer reported "no tests collected" AND parametrize never applied. Root cause: `collector.collect()` bypasses the `_collect_one_node` machinery that fires `_genfunctions` (which in turn fires `pytest_generate_tests`). Switching to `session.genitems(collector)` fixed both symptoms simultaneously: count footer now reads "580 tests collected" and parametrize fires correctly.

This is now documented in the plugin's `pytest_collection_modifyitems` docstring so future maintainers do not regress to `collector.collect()`. **No operator-facing impact in the shipped form.**

### 2. `pytest --collect-only -v` (without `-q`) renders the synthesized module as `<_ContractsModule _tests.py>` followed by the module docstring, NOT as a tree of `<Function test_X[tool]>` items

Pytest's `-v --collect-only` formatter walks the collector tree and prints each collector's `repr()` + its `__doc__`. The synthesized `_ContractsModule`'s `repr()` falls back to the `_PytestModule` base class repr (which uses the `path` attribute — `_tests.py` — even though the `nodeid` override returns `<mcp-contracts>`). The item tree underneath is NOT rendered in `-v` collect-only mode (probably because pytest's `-v` formatter expects the standard collection-tree walk, not items injected via `modifyitems`).

Operator-facing implication: docs should call out that `pytest --collect-only -q` is the right invocation to **see the parametrized item list** under the synthetic nodeid. `-v --collect-only` is misleading (shows the docstring, hides the items). Worth a sentence in operator docs or a `--collect-only` recipe in the README.

### 3. Parametrize-id suffix `[<tool>]` is hidden by `-q` test-function-grouping

`pytest --collect-only -q` (no `-v`) prints each parametrized test as a separate line (`<mcp-contracts>::test_X[tool_a]`, `<mcp-contracts>::test_X[tool_b]`, ...). This is the right way to see the full 580-item list. The framework's own legacy `tests/contract/test_mcp_tool_contract.py` rendered the same way historically; no change in operator UX vs the old path.

### 4. pytest-asyncio strict-mode loop wiring works end-to-end (re-validates Plan 27-01 spike sub-check D)

Plan 27-01 sub-check D asserted "no `RuntimeError` / `cancel scope` / `event loop is closed` diagnostics in plain `pytest` output." In integration: I did not run the contract tests through to completion against a real MCP server in this plan (out of scope — the Ollama / homelab-mcp live dependencies belong to operator-side verification), but `pytest --collect-only` exercises the `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` discovery and produces NO loop-wiring diagnostics. The synthesized collector's underlying `path` correctly resolves to the real on-disk file, pytest-asyncio walks `pytestmark` from that file, and strict-mode is satisfied.

## Brief MCP Handshake Error-Rendering Paths — No Adjustment Needed

The verbatim lift from `tests/conftest.py:104-128` split the error paths two ways: `FileNotFoundError` (command not on PATH) gets the explicit "install X or set mcp_server.command" remediation; generic `Exception` gets the "verify MCP server starts on its own via `<command> <args>`" remediation. Both render via `pytest.exit(msg, returncode=2)` (NOT `typer.Exit`, which would not be caught by the pytest session machinery). I did NOT trigger either error path during the smoke check (the framework's own MCP server runs fine), so the error wording is unvalidated end-to-end — that's an operator-facing edge case best validated when Plan 27-05's `pyproject.toml` change makes the framework dogfood the plugin permanently and the error paths get exercised through normal use.

## Decisions Made

See `key-decisions` in frontmatter. Highlights:

- `session.genitems(collector)` over `collector.collect()` — necessary for the parametrize chain. Documented in the plugin's `pytest_collection_modifyitems` docstring as the spike-validated mechanism.
- Sentinel-walk-up via `metafunc.definition.parent` — necessary because `metafunc.module` returns the imported Python module, not the `_ContractsModule` collector. Documented in `pytest_generate_tests` docstring.
- Per-item marker re-application kept (spike Pitfall 2 confirmed in real plugin) — module-level `add_marker` does not auto-propagate to `Function` children in the out-of-band attachment path.

## Deviations from Plan

### Rule 1 - Bug: `metafunc.module` does not carry the sentinel; sentinel-walk-up required

- **Found during:** Task 2 acceptance verification (parametrize id `[<tool>]` was missing from collected items even though `pytest_generate_tests` was registered and `mcp_target_tool` was in `metafunc.fixturenames`)
- **Issue:** The plan's literal hook body checked `getattr(metafunc.module, "_is_mcp_contracts_synthetic", False)`. `metafunc.module` returns the imported Python module object (`mcp_test_framework.contracts._tests`), NOT the `_ContractsModule` collector instance where the sentinel was stashed. The check always returned False → the parametrize call was skipped → items collected without parametrize.
- **Fix:** Replaced the `metafunc.module` attribute lookup with a walk-up from `metafunc.definition` via the `parent` chain to find the enclosing `_ContractsModule` collector. The sentinel lookup now succeeds. The parametrize list is then read off the resolved collector (not off the Python module).
- **Files modified:** `src/mcp_test_framework/_plugin.py` (`pytest_generate_tests` body)
- **Verification:** `pytest --collect-only -q` against a real config now renders all 580 `<mcp-contracts>::test_<name>[<tool>]` items with the parametrize-id suffix present.
- **Committed in:** `900c2e3` (single combined commit for both tasks)

### Rule 1 - Bug: `collector.collect()` bypasses parametrize machinery; use `session.genitems` instead

- **Found during:** Task 2 acceptance verification (same diagnostic chain as above; the `pytest_generate_tests` hook was registered but never fired)
- **Issue:** The plan's literal `pytest_collection_modifyitems` body used `for item in collector.collect()`. Pytest's `collector.collect()` returns items directly without going through `_collect_one_node`, which means `_genfunctions` (which fires `pytest_generate_tests`) is bypassed. Both the parametrize-id suffix and pytest's "N tests collected" counter were affected: items appeared in `session.items` but pytest reported "no tests collected" AND parametrize never applied.
- **Fix:** Replaced `collector.collect()` with `session.genitems(collector)` — the same recursive descent primitive pytest's own default collection walk uses. This invokes `_collect_one_node` → `PyCollector.collect` → `_genfunctions` → `pytest_generate_tests` properly.
- **Files modified:** `src/mcp_test_framework/_plugin.py` (`pytest_collection_modifyitems` body)
- **Verification:** Combined with the sentinel-walk-up fix above, `pytest --collect-only -q` now reports "580 tests collected" with full parametrize ids.
- **Committed in:** `900c2e3`

### Rule 3 - Blocking: `pytest_collection_modifyitems` body needed to be filled, not left as a no-op

- **Found during:** Reading Plan 27-01's SUMMARY.md (Finding 2 — "Synthesized collector attachment ritual")
- **Issue:** Task 1's `<action>` block says "Do NOT modify `pytest_collection_modifyitems` (kept as no-op carry-forward from Phase 26)." But the spike-validated attachment ritual (which Task 1's same `<action>` block explicitly instructs the executor to mirror verbatim, via "do not re-derive the attachment mechanics from pytest internals") REQUIRES filling `pytest_collection_modifyitems` to descend into the stashed synthetic collectors. The two instructions are mutually incompatible.
- **Fix:** Filled `pytest_collection_modifyitems` body per the spike's two-hook ritual. The previous no-op docstring is replaced with a full descent-via-`session.genitems` body documenting both the synth-collector descent and the per-item marker re-application. Plan 27-02 (which has already shipped) did NOT own this hook either, so there is no conflict with prior plan ownership.
- **Files modified:** `src/mcp_test_framework/_plugin.py` (`pytest_collection_modifyitems` body)
- **Verification:** Framework self-tests remain green; `<mcp-contracts>` injection works end-to-end.
- **Committed in:** `900c2e3`

---

**Total deviations:** 3 auto-fixed (2 Rule-1 bugs in literal plan code, 1 Rule-3 blocking ownership-instruction conflict)
**Impact on plan:** All three fixes were necessary for the success criteria to be achievable. The plan's literal hook bodies, applied without these adjustments, would have produced a plugin that injected items into `session.items` (so `<mcp-contracts>` rendered in `-q` collect-only) but with the wrong shape (no parametrize, wrong counter, broken `-m` selection on parametrized cases). The spike-validated attachment ritual recorded in `27-01-SUMMARY.md` Finding 2 is now the literal mechanism in `_plugin.py`. No scope creep — every change is mechanically required by the success criteria.

## Issues Encountered

- **Pre-existing: `tests/contract/test_mcp_tool_contract.py` collection error** — running `uv run pytest --collect-only tests/contract/` exits with 1 collection error (`pydantic_core.ValidationError: Field required test_code`). This is the legacy `tests/conftest.py:pytest_generate_tests` calling `Config()` with no kwargs/env and hitting a config-validation failure in the empty path. Out of scope for Plan 27-03; Plan 27-05 deletes both `tests/contract/test_mcp_tool_contract.py` and the legacy `tests/conftest.py:pytest_generate_tests`, which resolves this naturally.
- **Pre-existing: typer.Exit escape in `_emit_operator_error_for_validation` path** — when the smoke check accidentally used the v1-format `config.test.yaml`, the operator-tone "older format" error message DID render correctly first, but `_emit_operator_error_for_validation` then raised `typer.Exit` (a `click.exceptions.Exit`, NOT a `SystemExit` subclass), which escaped the surrounding `except SystemExit:` translation block in `pytest_configure` and surfaced as `INTERNALERROR>`. Plan 27-02 owns `pytest_configure`; flagging here as a deferred item for Plan 27-04 or 27-05 to address (the operator-tone error renders fine first; the only damage is the noisy `INTERNALERROR>` traceback after the helpful message). Not introduced by Plan 27-03 — pre-existing in the Plan 27-02 hook body.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 27-04** (fixture preflight predicate flip from path-prefix to `mcp_contract` marker): READY. The plugin now reliably applies the `mcp_contract` marker to every synthesized item (verified by sub-check C in the smoke run: `-m mcp_contract` → 580 items, `-m "not mcp_contract"` → 0 items). The marker is now a load-bearing attribute the preflight predicate can rely on.
- **Plan 27-05** (delete legacy `tests/conftest.py:pytest_generate_tests`, delete `tests/contract/test_mcp_tool_contract.py`, add `mcp_config_file = "./config.test.yaml"` to the framework's own `pyproject.toml`): READY. The plugin is now the sole functional parametrize site for contract tests. Plan 27-05 should also update docs to call out the `--collect-only -q` vs `-v` rendering nuances (Findings 2 + 3 above).
- **Operator-facing dogfood validation:** Deferred until Plan 27-05 makes the framework's own `pyproject.toml` set `mcp_config_file`. The current root `pyproject.toml` does NOT have the ini set, so the plugin's no-op path is what fires during framework self-tests (verified green: 598 passed). The dogfood path will exercise the inject path end-to-end through actual contract-test execution against the real homelab-mcp server.

## Self-Check: PASSED

Verified file exists:
- `src/mcp_test_framework/_plugin.py` — FOUND (modified, +209/-5)

Verified commit exists on `main`:
- `900c2e3` — FOUND (feat(27-03): synthesize <mcp-contracts> module with parametrized contract tests)

Verified all acceptance-criteria grep markers in `src/mcp_test_framework/_plugin.py`:
- `class _ContractsModule` → 1 match (line 81)
- `return "<mcp-contracts>"` → 1 match (line 93)
- `from _pytest.python import Module` → 1 match (line 42)
- `def pytest_collection` → 1 match (line 228, distinct from `pytest_collection_modifyitems` and `pytest_collection_finish`)
- `async def _discover_tools_live` → 1 match (line 105)
- `mod.add_marker(pytest.mark.mcp_contract)` → 1 match (line 308)
- `_is_mcp_contracts_synthetic` → 2 matches (line 301 stash, line ~363 walk-up read)
- `_mcp_parametrize_tools` → 2 matches (line 303 stash, line ~367 read)
- `def pytest_generate_tests` → 1 match (line ~339)
- `metafunc.parametrize("mcp_target_tool"` → 1 match (line ~371)
- `indirect=True` → 1 match (line ~373)
- `pytest.skip(` (excluding comments) → 0 matches (v1.1.1 hotfix invariant preserved)

End-to-end smoke check (real subprocess pytest run against the framework's own v2 `config.yaml`):
- `pytest --collect-only -q` → exit 0, 580 items, all under `<mcp-contracts>::test_<name>[<tool>]` shape
- `pytest --collect-only -q -m mcp_contract` → exit 0, 580 items
- `pytest --collect-only -q -m "not mcp_contract"` → exit 5, 0 items
- Framework self-tests (`uv run pytest tests/framework/ -q -x`) → 598 passed, 1 skipped, 17 deselected, 2 xfailed (same baseline as Plan 27-02)
- Planning-ID + SDET rename leak gates → 5 passed

---
*Phase: 27-register-api-contracts-sub-package-test-extraction-lib*
*Completed: 2026-05-16*
