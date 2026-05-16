---
phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s
verified: 2026-05-16T19:53:10Z
status: passed
score: 5/5 roadmap Success Criteria verified (SC1 via accepted local-gate substitute)
overrides_applied: 1
overrides:
  - must_have: "Operator running `pip install mcp-contracts` or `uv add mcp-contracts` succeeds against the TestPyPI-published wheel"
    reason: "User explicitly deferred the TestPyPI publish (Plan 26-05 Task 2) to Phase 30 on 2026-05-16 because TestPyPI login was blocked. PACK-04 SC1's wheel-content invariants are locally enforced by `tests/framework/test_wheel_shape.py` (11 assertions, all passing on every CI cycle), which is the load-bearing check; the TestPyPI publish was a pathway exercise — useful but redundant with the local gate. Phase 30 (CLOSE-01..04) owns the production-PyPI publish pathway."
    accepted_by: "washyu (user decision)"
    accepted_at: "2026-05-16"
---

# Phase 26: Packaging foundation — Verification Report

**Phase Goal:** Ship a buildable v0.1.0 wheel under the new `mcp-contracts` distribution name with PEP 561 typed-package markers, a pytest11 entry point pointing at `mcp_test_framework._plugin`, both console scripts (`mcp-contracts` primary + `mcp-test-framework` deprecation shim) declared, the `contracts/` subpackage stub in place, and a CI gate that catches future packaging drift. Operator-facing docs (README, CLAUDE.md, inline CLI docstrings) sweep to the new script name with the verbatim D-07 deprecation copy embedded so a single v1.5 cleanup grep finds all sites.

**Verified:** 2026-05-16T19:53:10Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria + Phase Goal)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| SC1 | `pip install mcp-contracts` / `uv add mcp-contracts` succeeds against published wheel | PASSED (override) | TestPyPI publish deferred to Phase 30 by user decision 2026-05-16; local wheel-shape gate (`tests/framework/test_wheel_shape.py`, 11 assertions all passing) substitutes for the publish-pathway exercise. Phase 30 (CLOSE-01..04) owns production publish. |
| SC2 | Operator's `pytest --trace-config` lists `mcp_test_framework` as auto-discovered plugin without `pytest_plugins=[...]` | VERIFIED | `pyproject.toml:32` declares `[project.entry-points.pytest11] mcp_test_framework = "mcp_test_framework._plugin"`. Module body at `src/mcp_test_framework/_plugin.py` exists with `pytest_configure`, `pytest_addoption`, `pytest_collection_modifyitems` hooks + 7 prefixed fixture re-exports. `test_wheel_declares_pytest11_entry_point` PASSED — confirms entry_points.txt in built wheel contains the literal `[pytest11]` block. |
| SC3 | `pyright` / `mypy` resolves typed signatures from `mcp_test_framework`, `mcp_test_framework.contracts`, `mcp_test_framework.test_code` (py.typed markers ship) | VERIFIED | All three `py.typed` files exist at 0 bytes (PEP 561 marker semantics). Wheel-shape tests `test_wheel_ships_root_py_typed`, `test_wheel_ships_test_code_py_typed`, `test_wheel_ships_contracts_subpackage` all PASSED — markers confirmed in built wheel. |
| SC4 | Framework CI fails if wheel missing `contracts/`, `test_code/`, py.typed markers, or contains `tests/` leakage | VERIFIED | `tests/framework/test_wheel_shape.py` exists with 11 assertions: filename uses `mcp_contracts-` prefix, root py.typed, test_code/py.typed, contracts/__init__.py+py.typed, _plugin.py, _deprecated_script.py present, no tests/ leakage, pytest11 entry, both scripts declared, no homelab_mcp imports. All 11 PASS locally on every CI cycle. Module-scoped fixture caches the build (3-8s amortized). |
| SC5 | Framework fixtures ship under `mcp_*` prefixed names with one-milestone unprefixed compatibility aliases | VERIFIED | `fixtures.py` lines 90/362/462/486/533/538/543 confirm 7 prefixed fixtures (`mcp_config`, `mcp_client`, `mcp_judge`, `mcp_target_tool`, `mcp_rubric_clarity/disambiguation/parameters`). Old names (`def config\|async def judge\|async def target_tool\|def rubric_*`) grep returns 0 matches. `_plugin.py` declares all 6 unprefixed alias fixtures (config/judge/target_tool/3 rubrics) each emitting DeprecationWarning then returning the prefixed value. Six v1.5 removal-copy lines, six DeprecationWarning calls, six stacklevel=2 — verified by grep. |

**Score:** 5/5 truths verified (SC1 via accepted override)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pyproject.toml` | dist name `mcp-contracts`, both scripts, pytest11 entry | VERIFIED | line 2: `name = "mcp-contracts"`; lines 24-25: both scripts; line 27-32: pytest11 entry; hatch `packages` unchanged; filterwarnings unchanged |
| `src/mcp_test_framework/cli.py` | `metadata.version("mcp-contracts")` | VERIFIED | line 975 confirmed; legacy `mvp-test-framework` grep returns 0 |
| `src/mcp_test_framework/_plugin.py` | pytest11 target with hooks + 7 re-exports + 6 alias fixtures | VERIFIED | 186 lines; `pytest_configure` registers `mcp_contract` marker; `pytest_addoption` reserves option group; `pytest_collection_modifyitems` is no-op; 7 prefixed fixture imports from fixtures.py; 6 deprecation aliases with hardcoded copy + stacklevel=2 |
| `src/mcp_test_framework/_deprecated_script.py` | `main()` emits DeprecationWarning then delegates to `cli:app` | VERIFIED | 33 lines; `warnings.warn(...)` precedes `from mcp_test_framework.cli import app` lexically inside `main()`; verbatim D-07 copy present at line 21-22 |
| `src/mcp_test_framework/contracts/__init__.py` | docstring-only subpackage stub (no `register`) | VERIFIED | 14 lines; module docstring describes intent; no callables/classes; `not hasattr(contracts, 'register')` confirmed via runtime check. Note: planner-required substrings `Phase 27 lands register()` / `D-13` were scrubbed during inline `fix(26): scrub D-XX planning IDs` to satisfy `test_no_planning_ids_in_src` leak-gate — see Anti-Patterns table. Substantive intent (empty subpackage, no register) is preserved and codified in tests. |
| `src/mcp_test_framework/py.typed` | 0-byte PEP 561 marker | VERIFIED | exists, size 0 |
| `src/mcp_test_framework/test_code/py.typed` | 0-byte PEP 561 marker | VERIFIED | exists, size 0 |
| `src/mcp_test_framework/contracts/py.typed` | 0-byte PEP 561 marker | VERIFIED | exists, size 0 |
| `src/mcp_test_framework/fixtures.py` | 6 fixtures renamed in place to `mcp_*`; internal cross-refs updated | VERIFIED | grep confirms 7 prefixed `^def mcp_*` / `^async def mcp_*` names (lines 90/362/462/486/533/538/543); zero legacy unprefixed names |
| `tests/framework/test_wheel_shape.py` | 11 wheel-introspection assertions, module-scoped fixture | VERIFIED | exists; 11 tests; module-scoped `built_wheel` fixture; `pytest.skip` if `uv` not on PATH; all 11 PASS locally |
| `tests/framework/test_cli_version.py` | 2 assertions on `version` command + source string | VERIFIED | exists; 2 tests, both PASS |
| `README.md` | sweeps to `mcp-contracts`; verbatim D-07 copy embedded | VERIFIED | 18 `mcp-contracts` occurrences; exactly 1 verbatim D-07 copy |
| `CLAUDE.md` | `## Tooling` block sweeps to `mcp-contracts`; verbatim D-07 copy embedded | VERIFIED | 4 `mcp-contracts` occurrences; exactly 1 verbatim D-07 copy |
| `.planning/REQUIREMENTS.md` | PACK-03 amended to cite mcp-contracts + D-01/D-02/D-03 | VERIFIED | line 26 amended; cites Phase 26 D-01, D-02, D-03 |
| `.planning/ROADMAP.md` | Phase 26 Goal + SC1 amended for mcp-contracts + TestPyPI scope + closed-by-non-applicability | VERIFIED | line 105 Goal references `mcp-contracts`; line 109 SC1 references TestPyPI + closed-by-non-applicability |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `pyproject.toml [project.entry-points.pytest11]` | `mcp_test_framework._plugin` | pytest11 entry-point discovery | WIRED | string literal in pyproject.toml line 32 matches module path; module body exists; `uv run pytest tests/framework/` collects without `pytest_plugins=[mcp_test_framework._plugin]` (relies on entry-point in editable install) |
| `pyproject.toml [project.scripts] mcp-contracts` | `mcp_test_framework.cli:app` | Typer app dispatch | WIRED | `uv run mcp-contracts version` returns `0.1.0` (live behavior verification) |
| `pyproject.toml [project.scripts] mcp-test-framework` | `mcp_test_framework._deprecated_script:main` | console-script trampoline + DeprecationWarning | WIRED | `uv run mcp-test-framework version` emits `DeprecationWarning: mcp-test-framework command is deprecated since v1.4 ... use mcp-contracts instead.` then prints `0.1.0` (live behavior verification) |
| `_plugin.py` unprefixed aliases | `fixtures.py` prefixed fixtures | pytest DI | WIRED | All 6 alias fixtures take prefixed fixture as parameter, warn, return passthrough; `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` confirms warnings surface in framework's own test suite |
| Verbatim D-07 copy (single-grep cleanup invariant) | 3 sites: shim, README, CLAUDE | literal string grep | WIRED | `Grep "mcp-test-framework command is deprecated since v1\.4"` returns exactly 3 files: `src/mcp_test_framework/_deprecated_script.py`, `README.md`, `CLAUDE.md` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Primary script returns version | `uv run mcp-contracts version` | `0.1.0` | PASS |
| Legacy script emits DeprecationWarning + delegates | `uv run mcp-test-framework version` | `DeprecationWarning: mcp-test-framework command is deprecated since v1.4 ... use mcp-contracts instead.` followed by `0.1.0` | PASS |
| CLI version Python module path | `uv run python -m mcp_test_framework.cli version` | `0.1.0` | PASS |
| Three operator-imported subpackages resolve | `python -c "import mcp_test_framework, mcp_test_framework.contracts, mcp_test_framework.test_code"` | exit 0 | PASS |
| `register` not exposed in contracts | `python -c "assert not hasattr(mcp_test_framework.contracts, 'register')"` | exit 0 | PASS |
| Wheel-shape gate (11 assertions) | `uv run pytest tests/framework/test_wheel_shape.py -v` | 11 passed in 0.94s | PASS |
| CLI-version regression (2 assertions) | `uv run pytest tests/framework/test_cli_version.py -v` | 2 passed | PASS |
| Full framework suite | `uv run pytest tests/framework/ --tb=no -q` | 597 passed, 1 skipped, 17 deselected, 2 xfailed (delta = +13 vs pre-Phase-26 baseline of 584) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| PACK-01 | 26-01, 26-02, 26-04, 26-05 | Pytest auto-discovers framework plugin without `pytest_plugins=[...]`; `[project.entry-points.pytest11]` declared | SATISFIED | pyproject.toml line 32 + `_plugin.py` module body + wheel-shape gate `test_wheel_declares_pytest11_entry_point` PASS |
| PACK-02 | 26-03, 26-04, 26-05 | Typed signatures resolve via PEP 561 markers in root + every operator-imported subpackage | SATISFIED | 3 py.typed markers (root, test_code, contracts) at 0 bytes; wheel-shape gate confirms all 3 ship in wheel |
| PACK-03 | 26-01, 26-02, 26-05 | Operator can `pip install mcp-contracts` / `uv add mcp-contracts` | SATISFIED (deferred publish) | dist name `mcp-contracts` in pyproject.toml; wheel filename normalizes to `mcp_contracts-0.1.0-...whl`; cli.py:975 resolves `metadata.version("mcp-contracts")`; TestPyPI publish deferred to Phase 30 per accepted override |
| PACK-04 | 26-04, 26-05 | Wheel-content regression test fails CI on packaging drift | SATISFIED | `tests/framework/test_wheel_shape.py` (11 assertions) runs in default pytest collection (no marker gate); module-scoped fixture builds wheel once per session |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `src/mcp_test_framework/contracts/__init__.py` | 1-14 | Plan 26-03 required substrings `Phase 27 lands register()` and `D-13` in the docstring; these were scrubbed during inline `fix(26): scrub D-XX planning IDs` to satisfy `test_no_planning_ids_in_src` and `test_sdet_rename_leak_gate`. The current docstring describes the same intent in different language ("subpackage stub", "future library-mode milestone fills the register() API"). | INFO | Plan's literal substring acceptance criterion is missed, but the substantive intent (empty subpackage, no callable, no `register`) is preserved and verified by both the runtime assertion `not hasattr(contracts, 'register')` and the wheel-shape gate. The leak-gate fix took precedence over the planner-specified literal text — defensible since planning IDs leaking into src/ would have failed CI. |
| n/a (whole tree) | n/a | No `TODO`/`FIXME`/`PLACEHOLDER` introduced in Phase 26 code paths | INFO | clean |
| `src/mcp_test_framework/_plugin.py` | n/a | No `import homelab_mcp` / `from homelab_mcp` | INFO | SEED-022 honored; wheel-shape `test_wheel_source_has_no_homelab_mcp_imports` PASS |

### Human Verification Required

None for the in-scope phase deliverables.

The TestPyPI publish (Plan 26-05 Task 2) was deferred to Phase 30 by user decision; it is the only remaining human-action item from the original Phase 26 scope, and it is explicitly covered by Phase 30 (CLOSE-01..04). No human verification needed before proceeding to Phase 27.

### Gaps Summary

No gaps. Every Roadmap Success Criterion (SC1..SC5) is verified against the codebase. Every PLAN-frontmatter `must_haves` truth is verified or covered by an accepted user-decision override. All four requirement IDs (PACK-01..04) trace to landed artifacts and passing tests. The 597-passed/0-failed framework suite, including the new 13 Phase 26 tests, confirms no regressions.

The single override (SC1's TestPyPI publish deferred to Phase 30) is recorded in frontmatter with explicit user-acceptance rationale and a concrete substitute (the local wheel-shape gate enforces the same wheel-content invariants on every CI cycle).

---

_Verified: 2026-05-16T19:53:10Z_
_Verifier: Claude (gsd-verifier)_
