# Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the packaging substrate that Phases 27–30 hang off. Six concrete surfaces change in lockstep:

1. **Dist name** — `pyproject.toml [project] name`: `mvp-test-framework` → `mcp-contracts` (never published — no PyPI shim needed for the old name).
2. **Pytest plugin entry point** — `[project.entry-points.pytest11]` declared, pointing at a new plugin module inside `mcp_test_framework` so `pytest --trace-config` lists the framework without any `pytest_plugins=[...]` in operator's conftest.
3. **Plugin module skeleton** — pre-declares hook signatures Phase 27 will fill (`pytest_configure`, `pytest_collection_modifyitems`, `pytest_addoption`); bodies are `pass` or trivial. Locks the hook surface, defers behavior.
4. **`py.typed` markers** — PEP 561 markers ship for `mcp_test_framework/`, `mcp_test_framework/test_code/`, AND a newly-stubbed `mcp_test_framework/contracts/` (empty `__init__.py` + `py.typed`; Phase 27 fills register()).
5. **Fixture surface (SC5)** — framework fixtures rename to `mcp_*` (`mcp_config`, `mcp_judge`, `mcp_target_tool`; `mcp_client` already correctly prefixed). One-milestone unprefixed aliases (`config`, `judge`, `target_tool`) emit `DeprecationWarning` per Phase 25 D-01..D-05; removal v1.5.
6. **CLI script rename** — `[project.scripts] mcp-contracts = ...` becomes primary; `mcp-test-framework` is a one-milestone deprecation-shim script per Phase 25 D-01..D-05; removal v1.5.

Plus the wheel-introspection CI gate (PACK-04) — fails on missing dirs/markers or `tests/` leakage.

**Out of scope (deferred to later phases):**
- `register()` API body, contracts/ module logic, `pytest_collection_modifyitems` hook body that injects contract tests — Phase 27 (LIB-01..08).
- Library-mode config seam, `MCPTF_CONFIG_FILE` library-mode behavior, codegen output path defaults — Phase 28 (CFG-01, CFG-02, CODEGEN-LIB-01..02).
- `--mcp-domain-ui` reporter plugin + `pytest_runtest_logreport` event handling — Phase 29 (REPORTER-01..02).
- Production PyPI publish (we ship a TestPyPI dry-run + local-install verification in Phase 26; production publish lands at Phase 30 alongside README rewrite per CLOSE-01..04).
- Migrating framework's own internal tests off the deprecated unprefixed fixture names — can land in Phase 26 plans if convenient, otherwise as a follow-up before v1.5.

</domain>

<decisions>
## Implementation Decisions

### Dist-name rename + back-compat (PACK-03)

- **D-01:** Dist name: `mvp-test-framework` → `mcp-contracts`. Verified available on PyPI 2026-05-15.
- **D-02:** No PyPI shim under the old `mvp-test-framework` name needed — the project has never been published, so there is no prior installation to migrate. PACK-03's "one-milestone shim under the old name" clause is closed-by-non-applicability.
- **D-03:** The originally-targeted name `mcp-test-framework` is taken by an unrelated project (`aryanjp1/pytest-mcp`, v0.1.1, 2026-02-07). ROADMAP.md Phase 26 line and PACK-03 requirement text both reference the wrong name and should be amended during planning to read `mcp-contracts`.
- **D-04:** The importable package name `mcp_test_framework` is UNCHANGED. Phase 25's API freeze (`from mcp_test_framework.test_code import mcp_session, tool`) holds. Dist name and import name are deliberately decoupled — conventional Python pattern (Pillow/PIL, beautifulsoup4/bs4).

### CLI script rename

- **D-05:** New primary script: `mcp-contracts = "mcp_test_framework.cli:app"` under `[project.scripts]`.
- **D-06:** Old script `mcp-test-framework` retained for v1.4 as a deprecation-shim entry point (a tiny wrapper that emits `DeprecationWarning` then calls the same `cli:app`) — same shape as Phase 25 D-04 (the `gen-sdet-classes` shim). Removed in v1.5.
- **D-07:** Deprecation warning copy template (mirrors Phase 25 D-05): `"mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5; use mcp-contracts instead."` Hardcoded per call site (one site for the script shim).
- **D-08:** All operator-facing docs (README, CLAUDE.md, docs/) update to the new script name during Phase 26. Old name remains in the deprecation message and nowhere else.

### Pytest plugin scope

- **D-09:** Plugin entry-point module is a new file inside `src/mcp_test_framework/`. Planner picks the file name; recommend `_plugin.py` (underscore-prefix signals internal) or `plugin.py` (visible to operators in tracebacks). `[project.entry-points.pytest11]` key follows pytest convention — recommend `mcp_test_framework = "mcp_test_framework._plugin"`.
- **D-10:** Phase 26 plugin module contains pre-declared hook signatures with no-op or trivial bodies — at minimum: `pytest_configure(config)`, `pytest_collection_modifyitems(config, items)`, `pytest_addoption(parser)`. Bodies are `pass` or "register the marker" / "no-op log" trivialities. Phase 27 fills `register()`-driven behavior.
- **D-11:** Plugin module ALSO declares the renamed framework fixtures (`mcp_config`, `mcp_judge`, `mcp_target_tool`) plus the existing `mcp_client` and the unprefixed deprecation aliases. Fixtures move from `mcp_test_framework.fixtures` into the entry-point plugin module so auto-discovery surfaces them; the old `fixtures.py` either re-exports or is deprecated in a follow-up. Planner decides which.
- **D-12:** `tests/conftest.py` keeps its current `pytest_plugins = ["mcp_test_framework.fixtures"]` line for v1.4 — internal compat. External operators no longer need that line because the entry point auto-loads. Documented in CONTEXT/README.

### `mcp_test_framework/contracts/` subpackage stub

- **D-13:** Create `src/mcp_test_framework/contracts/__init__.py` (empty or with one-line docstring describing where `register()` lands in Phase 27) AND `src/mcp_test_framework/contracts/py.typed` (empty marker) during Phase 26. SC3 passes as written — `pyright` resolves `from mcp_test_framework.contracts import ...` without missing-stubs noise (even though the module is currently empty).
- **D-14:** `register()` is NOT in scope for Phase 26 — that's Phase 27's load-bearing decision. Any operator importing from `mcp_test_framework.contracts` in v1.4 pre-Phase-27 simply finds an empty module; no helpful runtime error needed (Phase 27 ships within the same milestone before any release).

### Fixture surface (SC5)

- **D-15:** Renames: `config` → `mcp_config`, `judge` → `mcp_judge`, `target_tool` → `mcp_target_tool`. `mcp_client` is already correctly prefixed, no change. `_preflight` is an internal autouse fixture — keep underscored, NOT renamed (it's not in SC5's collision list).
- **D-16:** Three rubric fixtures (`clarity_rubric`, `disambiguation_rubric`, `parameters_rubric` in `fixtures.py`) — these are NOT in SC5's collision list (`config`, `judge`, `client`, `target_tool`) but they ARE generic-enough names that an operator could collide. **Decision:** also prefix to `mcp_clarity_rubric`, `mcp_disambiguation_rubric`, `mcp_parameters_rubric`. Add to D-01..D-05 deprecation alias set. If planner finds this expands scope unacceptably during planning, defer to v1.5 sweep with explicit note.
- **D-17:** Unprefixed aliases (`config`, `judge`, `target_tool`, and per D-16 the three rubric names) are separate `@pytest.fixture` defs that:
  - Receive the prefixed fixture as a parameter (`def config(mcp_config): ...`).
  - Emit one `warnings.warn(DeprecationWarning, ..., stacklevel=2)` per-process per-alias on first request (Phase 25 D-01..D-05 pattern, default Python warning filter handles dedup).
  - Return the prefixed value unchanged.
  - Are listed in a single docstring block at the top of the plugin module pointing at v1.5 removal.
- **D-18:** Removal milestone: v1.5, same as every other Phase 25 / Phase 26 deprecation shim — keeps the v1.5 cleanup phase coherent.
- **D-19:** Internal framework tests (`tests/`) currently use the unprefixed names. Planner decides whether to migrate them to `mcp_*` in Phase 26 (clean but +N file churn) or leave them until a dedicated cleanup task (means our own test suite exercises the deprecation pathway every run, which `filterwarnings = always::DeprecationWarning:mcp_test_framework` in pyproject already surfaces). Either choice is defensible.

### Claude's Discretion

- **Plugin module file name** — `_plugin.py` vs `plugin.py` (D-09 recommends `_plugin.py`). Planner picks.
- **Wheel-introspection venue (PACK-04)** — place the test at `tests/framework/test_wheel_shape.py` (runs in framework's normal pytest suite — fails CI naturally) using stdlib `zipfile` (no new deps). Walks the built wheel for: required dirs (`mcp_test_framework/`, `mcp_test_framework/test_code/`, `mcp_test_framework/contracts/`), required `py.typed` markers, accidental `tests/` leakage. Build the wheel via `uv build` in a tmp dir as part of the test setup.
- **PyPI publish timing** — Phase 26 ships a TestPyPI dry-run + local-install verification (`pip install --index-url https://test.pypi.org/simple/ mcp-contracts` succeeds + imports clean). Production PyPI publish defers to Phase 30 (CLI demotion + docs rewrite). SC1 should be amended during planning to specify the verification target as "TestPyPI dry-run + locally-installed wheel"; the production-PyPI clause folds into CLOSE-01..04. If user wants Phase 26 to ALSO do production publish, planner can pull it in — flag as a deviation.
- **`hatchling` build config updates** — `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` already covers subpackages. May need `[tool.hatch.build.targets.wheel.force-include]` or `[tool.hatch.build.targets.wheel.shared-data]` for `py.typed` files depending on hatch's marker-file behavior — planner verifies during research.
- **`pyright` / `mypy` resolution check (PACK-02 / SC3)** — add a small CI step or test that imports `mcp_test_framework`, `mcp_test_framework.contracts`, `mcp_test_framework.test_code` from an installed-wheel virtualenv and runs `pyright` over a fixture file that uses the typed signatures. Planner picks library version (existing `pyright>=1.1.409` in dev deps is fine).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & roadmap

- `.planning/PROJECT.md` — Vibe-coded operator persona, performance constraints, anti-vision (esp. SUT-aware framework features = locked anti-pattern), v1.4 milestone goals.
- `.planning/ROADMAP.md` §"v1.4 Library Mode Delivery" + "Phase 26" + dependent phases 27–30 — phase boundaries, success criteria, requirement mapping. NOTE: SC1 and PACK-03 text reference `mcp-test-framework` — replace with `mcp-contracts` per D-01 during planning.
- `.planning/REQUIREMENTS.md` PACK-01..04, LIB-01..08, CFG-01..02, CODEGEN-LIB-01..02, REPORTER-01..02, CLOSE-01..04 — full requirement IDs, especially the Phase 26 column.
- `.planning/STATE.md` — Phase position, milestone counters, recent activity.

### Phase 25 carry-forward (deprecation pattern)

- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-CONTEXT.md` §"Deprecation mechanics" — D-01..D-05 deprecation pattern (stdlib `DeprecationWarning`, once-per-process, `stacklevel=2`, hardcoded "v1.5" removal copy per call site). Phase 26 inherits this verbatim for the new CLI shim and fixture aliases.
- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-01-PLAN.md` — Package rename precedent (`sdet/` → `test_code/`). Shows how the project handles dual-write compat shims.
- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-02-PLAN.md` — CLI command + flag deprecation shim precedent (`gen-sdet-classes` → `gen-test-classes`, `--sdet` → `--test-code`). Phase 26's `mcp-test-framework` script shim follows the same mechanics.
- `pyproject.toml` `[tool.pytest.ini_options] filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` — Phase 25 D-03. Phase 26's new deprecation shims are caught by the same filter; no pyproject change needed.

### Seeds & vision

- `.planning/seeds/SEED-015-library-mode-delivery.md` — Library-mode reframing rationale, "three lines in conftest" target, CLI demotion plan, fixture-surface preview. Phase 26 is the substrate; Phases 27–30 fulfill the seed.
- `.planning/seeds/SEED-023-rename-sdet-surface-to-test-code.md` — Background on Phase 25's rename; explains why API surface freezes matter before PyPI publish.
- `.planning/seeds/SEED-022-framework-primitives-sdet-safety-principle.md` — Framework-primitives principle (memory `project_framework_primitives_sdet_safety_principle`). Phase 26 must not introduce any SUT-aware logic in the plugin skeleton.

### Codebase landmarks (Phase 26 will touch)

- `src/mcp_test_framework/fixtures.py` — Current home of all session-scoped fixtures. SC5 renames live here. Plugin entry-point module either replaces this or re-exports it.
- `src/mcp_test_framework/cli.py` — Typer app. New `mcp-contracts` script points at `:app`; deprecation-shim script wraps the same.
- `tests/conftest.py` — Has `pytest_plugins = ["mcp_test_framework.fixtures"]` (the "load-bearing one-line seam"). Phase 26 makes this redundant for external operators via the entry point; the internal conftest may keep it for v1.4.
- `pyproject.toml` `[project]`, `[project.scripts]`, `[project.entry-points.pytest11]` (new), `[tool.hatch.build.targets.wheel]` — packaging center of gravity.

### Python/packaging references (researcher should fetch)

- PEP 561 — `py.typed` marker semantics; wheel-content requirements.
- pytest plugin docs — `pytest11` entry-point pattern, hook signatures, fixture plugin layout. https://docs.pytest.org/en/stable/how-to/writing_plugins.html
- hatchling docs — wheel marker-file inclusion, `force-include`, `packages` config. https://hatch.pypa.io/latest/config/build/#hatchling
- TestPyPI publish workflow — https://packaging.python.org/en/latest/guides/using-testpypi/

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`src/mcp_test_framework/fixtures.py`** — All session-scoped fixtures (`config`, `judge`, `mcp_client`, `target_tool`, `_preflight`, three rubric fixtures) already structured as a pytest-loadable plugin module. Phase 26 either (a) moves these into the new entry-point plugin module, or (b) imports them from `fixtures.py` into the new plugin module. Planner decides; option (b) is lower-churn.
- **`tests/conftest.py` lines 18-19** — `pytest_plugins = ["mcp_test_framework.fixtures"]` is the existing operator-facing seam. Phase 26's entry point makes this implicit; the line stays in the framework's own conftest as internal compat.
- **`src/mcp_test_framework/cli.py`** — Typer app already cleanly mounted at `app` (referenced by `[project.scripts] mcp-test-framework`). New script entry point reuses it verbatim; deprecation shim is a 5-line wrapper module.
- **Phase 25 D-01..D-05 deprecation pattern** — stdlib `DeprecationWarning`, `stacklevel=2`, once-per-process via default Python warning filter, hardcoded "v1.5" removal copy. Lift wholesale for the script shim and fixture aliases.

### Established Patterns

- **`pyproject.toml [tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]`** — single-package wheel layout established in Phase 01-01. New `contracts/` subpackage falls under this automatically; only py.typed marker handling needs verification.
- **Banned-imports + `sys.modules` guard for black-box rule** (`tests/conftest.py` pytest_configure + `pyproject.toml [tool.ruff.lint.flake8-tidy-imports.banned-api]`) — Phase 26 plugin must not regress this. The entry-point plugin's own pytest_configure should chain to (or coexist with) the existing guard.
- **`filterwarnings = always::DeprecationWarning:mcp_test_framework`** — Phase 25 D-03 ensures framework's own pytest surfaces all internal deprecation warnings. Phase 26's new shims (CLI script, fixture aliases) inherit this safety net.
- **Hardcoded deprecation copy per call site** (Phase 25 D-05) — Phase 26 adds ~4 new sites (CLI script + 3+ fixture aliases). Keep copy literal — no central constant.

### Integration Points

- **pytest entry-point auto-load** — `pytest --trace-config` will surface the new plugin name. PACK-01 / SC2 acceptance: framework appears in trace WITHOUT any `pytest_plugins=[...]` in operator's conftest. Verify by setting up a fresh venv, `pip install` from the built wheel, and running `pytest --trace-config` from a project with an empty conftest.
- **pyright / mypy import resolution** — PACK-02 / SC3 acceptance: importing `mcp_test_framework`, `mcp_test_framework.test_code`, `mcp_test_framework.contracts` from an installed-wheel virtualenv resolves without "Missing stub" complaints. py.typed markers must ship in the wheel; verify via `unzip -l` and the wheel-introspection test.
- **Hatchling wheel build** — `uv build` should produce a wheel under the new dist name `mcp_contracts-X.Y.Z-py3-none-any.whl` (note: wheel filename uses dist name, NOT import name). Wheel introspection test verifies the package layout inside.

</code_context>

<specifics>
## Specific Ideas

- **PyPI availability checked 2026-05-15** for the following names; recording for reference in case future phases revisit branding:
  - **Taken:** `mcp-test-framework` (aryanjp1/pytest-mcp, 0.1.1, 2026-02-07); `mcp-judge` (Nilavo Boral, 0.1.4, 2025-11-07); `mcp-tester`, `mcp-validate`, `mcp-verify`.
  - **Available (and discussed):** `mcp-contracts` (chosen), `pytest-mcp-contracts`, `mcp-conformance`, `mcp-blackbox`.
- **Why `mcp-contracts` over `pytest-mcp-contracts`** — dist name aligns with the planned `mcp_test_framework.contracts.register()` API surface from SEED-015 / Phase 27. `pytest-mcp-contracts` was the runner-up for discoverability via pytest-plugin-prefix convention (`pytest-asyncio`, `pytest-xdist`).
- **The originally-taken `mcp-test-framework` PyPI project** is an interesting adjacent product — it's the codegen-via-fixture slice of what we do, packaged as a streamlit-free pytest-plugin. Operator noted it as the kind of thing they hadn't thought of doing. Not relevant to Phase 26 scope but worth keeping in mind if branding revisits.
- **Fixture-rename surgery** — six fixtures get prefixed (`config`, `judge`, `target_tool`, three rubric fixtures); one already correct (`mcp_client`); one stays internal (`_preflight`). Total deprecation-shim alias count: ~6 separate `@pytest.fixture` defs in the plugin module.

</specifics>

<deferred>
## Deferred Ideas

### Phase 27 (already roadmapped)
- `register()` API body, `pytest_collection_modifyitems` hook body, contracts module test extraction. Phase 26 ships the stub; Phase 27 fills it.

### Phase 28 (already roadmapped)
- Library-mode config seam — kwargs > pyproject > defaults; `MCPTF_CONFIG_FILE` ignored in library mode.
- Codegen output path defaults (`tests/_generated/<server_slug>/`, refuse to write under `sys.path` install dirs).

### Phase 29 (already roadmapped)
- `--mcp-domain-ui` reporter plugin via `pytest_runtest_logreport`; xdist master-only emission; CI/no-TTY auto-OFF; separate `[project.entry-points.pytest11]` key for opt-out.

### Phase 30 (already roadmapped)
- Production PyPI publish (post-TestPyPI verification in Phase 26).
- README rewrite leading with library mode; CLI demoted to appendix.
- Carry-forward live UATs (README PASS-sample re-capture, Phase 17 SC1 at ~70 tools, v1.2 Phase 13 + 14 live-stack UATs).
- Framework's own `tests/contract/conftest.py` calls `register()` (library-mode dogfood).

### v1.5 cleanup (deferred from Phase 26)
- Remove `mcp-test-framework` CLI script alias.
- Remove unprefixed fixture aliases (`config`, `judge`, `target_tool`, three rubric fixtures).
- Remove every Phase 25 + Phase 26 deprecation shim coherently in one phase.

### Possibly deferred from Phase 26 (planner's call)
- Migrating framework's own internal tests off the deprecated unprefixed fixture names. Either lands in Phase 26 plans or as a follow-up — see D-19.
- Three rubric fixtures `mcp_*` prefix (D-16) — if it expands Phase 26 scope unacceptably, can defer to v1.5 sweep with explicit note.

</deferred>

---

*Phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-skeleton*
*Context gathered: 2026-05-15*
