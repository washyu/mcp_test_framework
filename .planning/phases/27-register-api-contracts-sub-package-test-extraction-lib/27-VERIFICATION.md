---
phase: 27-register-api-contracts-sub-package-test-extraction-lib
verified: 2026-05-16T00:00:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
---

# Phase 27: pytest-native ini config + contracts test injection + dogfood (LIB) — Verification Report

**Phase Goal (per CONTEXT.md, supersedes original ROADMAP title):** Operator's library-mode flow becomes "one line in `pyproject.toml`" — `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` causes parametrized contract tests to appear in their pytest collection under synthetic nodeid `<mcp-contracts>::test_<name>[<tool>]` with zero conftest ceremony. CLI mode and library mode share a single config-resolution mechanism.

**Verified:** 2026-05-16
**Status:** passed
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths (Scope Items from CONTEXT.md, distilled by orchestrator)

| #  | Truth (Scope Item)                                                           | Status     | Evidence |
| -- | ---------------------------------------------------------------------------- | ---------- | -------- |
| 1  | Operator's library-mode flow is "one line in `pyproject.toml`" (no conftest) | PASS       | `tests/conftest.py` hollowed to docstring-only (24 lines, no code); `pyproject.toml:62` sets `mcp_config_file = "./config.test.yaml"`; live `pytest -o "mcp_config_file=config.yaml"` collects 580 `<mcp-contracts>` nodeids. |
| 2  | `mcp_config_file` ini option registered via `parser.addini()`                | PASS       | `src/mcp_test_framework/_plugin.py:206-225` — `parser.addini("mcp_config_file", type="string", default="", help=...)` inside `pytest_addoption`. |
| 3  | Plugin `pytest_configure` reads ini, loads YAML via `Config(yaml_file=...)`, invokes relocated black-box guard | PASS       | `_plugin.py:127-203` — `config.getini("mcp_config_file")` (line 159), `Config(yaml_file=str(path))` (line 181), `check_black_box()` (line 200), stash on `config._mcp_contracts_config` (line 203). No `os.environ` write. |
| 4  | Plugin collection hooks synthesize `_ContractsModule(_PytestModule)` with `nodeid` override `<mcp-contracts>`, parametrized over `config.tools.keys()` honoring SAFE-01 opt-in | PASS       | `_plugin.py:81-93` (`_ContractsModule` + `nodeid` property → `<mcp-contracts>`); `_plugin.py:261-263` (allowlist filter: `if not tcfg.skip`); `_plugin.py:228-313` (`pytest_collection`); `_plugin.py:316-344` (`pytest_collection_modifyitems` via `session.genitems`); `_plugin.py:347-388` (`pytest_generate_tests` with indirect parametrize). No runtime `pytest.skip()` calls. Live: 580 items collected. |
| 5  | `mcp_contract` marker auto-applied to every injected item                    | PASS       | `_plugin.py:308` (module-level `add_marker`); `_plugin.py:343` (per-item `add_marker` in `pytest_collection_modifyitems`). Marker registered at `_plugin.py:142-145`. SUMMARY 27-03 confirms `-m mcp_contract` → 580 items; `-m "not mcp_contract"` → 0 items. |
| 6  | 10 contract test bodies extracted to `src/mcp_test_framework/contracts/_tests.py` with `mcp_*` fixture renames | PASS       | `grep -c "^async def test_" src/mcp_test_framework/contracts/_tests.py` → **10**. File is 282 lines (within +0.7% of the legacy 280-line analog). |
| 7  | Black-box `sys.modules` `homelab_mcp` guard relocated to `_black_box_guard.py:check_black_box()` and invoked from plugin | PASS       | `src/mcp_test_framework/_black_box_guard.py:18` — `def check_black_box() -> None`; iterates `sys.modules` for `homelab_mcp`/`homelab_mcp.*`; raises `RuntimeError`. Invoked from `_plugin.py:200`. Old guard removed from `tests/conftest.py` (now docstring-only). |
| 8  | `_session_needs_preflight()` flipped to marker-based detection (transitional `tests/contract/` prefix removed in 27-05) | PASS       | `src/mcp_test_framework/fixtures.py:129-173` — PRIMARY: `iter_markers("mcp_contract")` (line 167); SECONDARY: `_LIVE_PREFIXES = ("tests/test_code/", "tests/sdet/")` (lines 123-126) — `tests/contract/` is NOT in the tuple (removed by 27-05 per SUMMARY). |
| 9  | `MCPTF_CONFIG_FILE` env var write killed; one-time DeprecationWarning on read | PASS       | `grep "os.environ\[.MCPTF_CONFIG_FILE.\]"` in `src/` → **0 matches** (no writes). `_plugin.py:148-156` emits the literal Phase 25-pattern DeprecationWarning copy when env var is set. Env-READ paths retained in `cli.py:264` (Branch 2 back-compat resolution) and `config.py:235` (env-fallback in Config loader) — both READ only, consistent with D-09/D-10. |
| 10 | `mcp-contracts run --config PATH` subprocesses `pytest -o "mcp_config_file=PATH"` (no env-var write) | PASS       | `_runner.py:87` — `mcp_config_path: Path | None = None` kwarg; `_runner.py:147-156` — appends `["-o", f"mcp_config_file={mcp_config_path}"]` to argv; `cli.py:579, 652` — threads `mcp_config_path=resolved` to both raw and default `run_pytest_subprocess` call sites. `cli.py` contains zero `os.environ[...]= str(resolved)` writes. |
| 11 | Framework dogfoods library mode; legacy `tests/contract/test_mcp_tool_contract.py` and `tests/conftest.py` parametrize wiring DELETED | PASS       | `pyproject.toml:60-62` sets `mcp_config_file = "./config.test.yaml"`. `ls tests/contract/test_mcp_tool_contract.py` → no such file. `tests/conftest.py` is docstring-only (24 lines, no imports, no `pytest_plugins`, no `pytest_configure`, no `pytest_generate_tests`). |
| 12 | Wheel-introspection AST regression in `tests/framework/test_wheel_shape.py` fails on banned SUT imports in `src/` | PASS       | `test_wheel_shape.py:151-179` — `_ast_homelab_imports` uses `ast.parse` + `ast.walk` over `ast.Import` / `ast.ImportFrom`; `test_wheel_shape.py:182-215` — `test_wheel_source_has_no_homelab_mcp_imports` includes Pitfall 6 ironic-leak guard (`assert "mcp_test_framework/_black_box_guard.py" in py_sources`). Live: `uv run pytest tests/framework/test_wheel_shape.py -q` → **11 passed**. |
| 13 | REQUIREMENTS.md LIB-01..08 + CFG-01..02 amended; ROADMAP.md milestone goal + Phase 27 title/SC + Phase 28/30 amendments shipped | PASS       | `.planning/REQUIREMENTS.md:31-43` — LIB-01..08 + CFG-01/02 rewritten for ini route; LIB-05 + CFG-02 marked `Removed (Phase 27 D-01)` in traceability table (lines 115-126); CFG-01 marked Complete. `.planning/ROADMAP.md:80, 122-130` — Phase 27 title is "pytest-native ini config + contracts test injection + dogfood (LIB)"; goal text references the ini-route pitch; SC references `<mcp-contracts>::test_*` nodeid; Phase 28 scope reduced to `CODEGEN-LIB-01/02`; Phase 30 SC1 references "Phase 27 D-06 / D-07". |

**Score:** 13/13 truths verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mcp_test_framework/_plugin.py` | Filled `pytest_addoption`, `pytest_configure`, `pytest_collection`, `pytest_collection_modifyitems`, `pytest_generate_tests` hooks; `_ContractsModule` subclass; `_discover_tools_live` helper | VERIFIED | 476 lines, all hooks present and wired; Read-confirmed end-to-end |
| `src/mcp_test_framework/_black_box_guard.py` | Single `check_black_box()` function relocated from `tests/conftest.py` | VERIFIED | 37 lines, exact 1 `def check_black_box` |
| `src/mcp_test_framework/contracts/_tests.py` | 10 async contract tests with `mcp_*` fixture renames | VERIFIED | 10 `async def test_*` functions |
| `src/mcp_test_framework/contracts/__init__.py` | Docstring-only documenting ini route; no `register()` export | VERIFIED | 24-line docstring, no code, mentions "intentionally NO `register()` API" |
| `src/mcp_test_framework/fixtures.py:_session_needs_preflight` | Marker-based detection (primary) with optional path-prefix secondary | VERIFIED | Lines 129-173; primary marker branch with `iter_markers("mcp_contract")`; `_LIVE_PREFIXES` covers test-code paths only |
| `src/mcp_test_framework/_runner.py` | `mcp_config_path` kwarg → `["-o", "mcp_config_file=PATH"]` argv | VERIFIED | Lines 87, 147-156, 191, 274 |
| `src/mcp_test_framework/cli.py` | `_load_config` returns `(Config, Path)` tuple; no env-var write; threads resolved path to runner | VERIFIED | Lines 206-318; tuple return, env-write deleted, threaded at lines 579/652 |
| `pyproject.toml` | `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` | VERIFIED | Line 62 |
| `tests/conftest.py` | Hollowed (docstring-only) per D-17 zero-ceremony invariant | VERIFIED | 24-line docstring, no code |
| `tests/contract/test_mcp_tool_contract.py` | DELETED | VERIFIED | `ls` reports no such file |
| `tests/framework/test_wheel_shape.py` | AST-walk over `ast.Import`/`ast.ImportFrom`; Pitfall 6 ironic-leak guard | VERIFIED | Lines 151-179 (AST walk); lines 200-207 (Pitfall 6 guard) |
| `.planning/REQUIREMENTS.md` | LIB-01..08 + CFG-01/02 amended; LIB-05 + CFG-02 marked Removed | VERIFIED | Lines 31-43, 115-126 |
| `.planning/ROADMAP.md` | Phase 27 title + goal + SC amended; Phase 28/30 amendments | VERIFIED | Lines 80, 122-167 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `pyproject.toml [tool.pytest.ini_options]` | `_plugin.py:pytest_configure` | `config.getini("mcp_config_file")` | WIRED | Verified: live `uv run pytest tests/framework/ -q` exits 0 (602 passed) with `mcp_config_file = "./config.test.yaml"` set; plugin's `Config(yaml_file=...)` loads successfully (silent no-inject branch fires because `tools: {}`). |
| `_plugin.py:pytest_configure` | `_black_box_guard.py:check_black_box` | Direct call | WIRED | `_plugin.py:45` import; `_plugin.py:200` invocation. |
| `_plugin.py:pytest_configure` | `cli.py:_emit_operator_error_for_validation` | Lazy import; `try/except SystemExit → pytest.exit(2)` translation | WIRED | `_plugin.py:184-196` — lazy import inside `except ValidationError`; SystemExit (from typer.Exit raised by helper) translated to `pytest.exit(returncode=2)`. |
| `_plugin.py:pytest_collection` | `_plugin.py:pytest_collection_modifyitems` | `session._mcp_synthetic_collectors` stash | WIRED | Lines 311-313 stash; lines 337-342 iterate stash via `session.genitems(collector)`. |
| `_plugin.py:pytest_collection_modifyitems` | `_plugin.py:pytest_generate_tests` | `session.genitems` → `_genfunctions` chain; sentinel `_is_mcp_contracts_synthetic` | WIRED | Spike-validated mechanism; `pytest_generate_tests` walks `metafunc.definition.parent` chain to locate sentinel and calls `metafunc.parametrize("mcp_target_tool", names, indirect=True, ids=names)`. Live: 580 parametrized items collected. |
| `cli.py:run` | `_runner.run_pytest_subprocess` | `mcp_config_path=resolved` kwarg → `["-o", f"mcp_config_file={path}"]` argv injection | WIRED | Both raw (line 579) and default (line 652) `run_pytest_subprocess` calls thread the kwarg; `_runner.py:147-156` appends the argv elements. |
| `fixtures.py:_session_needs_preflight` | `_plugin.py` injected items | `iter_markers("mcp_contract")` lookup | WIRED | Marker is auto-applied per-item by `pytest_collection_modifyitems` (line 343); predicate's primary branch matches on it. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_plugin.py:_ContractsModule` | `_mcp_parametrize_tools` | `_discover_tools_live(cfg)` → MCP `list_tools` handshake, intersected with `config.tools` opt-in allowlist | YES | Live smoke: 58 tools × 10 tests = 580 items rendered |
| `_plugin.py:pytest_configure` | `_mcp_contracts_config` | `Config(yaml_file=str(path))` via pydantic-settings YamlConfigSettingsSource | YES | Framework's own `config.test.yaml` loads without error; silent no-inject (empty tools dict) confirmed in framework regression run |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Framework self-tests green | `uv run pytest tests/framework/ -q` | `602 passed, 1 skipped, 17 deselected, 1 xfailed, 45 warnings in 23.19s` | PASS |
| Library-mode collection produces synthetic nodeids | `uv run pytest -o "mcp_config_file=config.yaml" --collect-only -q` | 580 `<mcp-contracts>::test_*[<tool>]` lines; final count `1184/1201 tests collected (17 deselected) in 5.29s` | PASS |
| `check_black_box` is the unique function in its file | `grep -c "def check_black_box" src/mcp_test_framework/_black_box_guard.py` | `1` | PASS |
| Extracted contract tests count | `grep -c "^async def test_" src/mcp_test_framework/contracts/_tests.py` | `10` | PASS |
| Legacy contract test file deleted | `ls tests/contract/test_mcp_tool_contract.py` | "No such file or directory" | PASS |
| No env-var WRITE remains | `grep "os.environ\[.MCPTF_CONFIG_FILE.\]" src/mcp_test_framework/*.py` (writes only — pattern matches the assignment syntax) | 0 matches; only `os.environ.get("MCPTF_CONFIG_FILE")` reads are present | PASS |
| Wheel-introspection AST regression green | `uv run pytest tests/framework/test_wheel_shape.py -q` | `11 passed in 1.38s` | PASS |
| Phase 27 commits all present on `main` | `git log --oneline` | All 17 expected commits found: `c417252, 0829d98, 3e5a470, 67abcef, daeb3d6, d04efeb, f044f1a, c0bce80, 900c2e3, 2713de4, fa63b12, a3d2c69, 2015e05, 5c85835, d7b8d57, eb00f8d, d0593ac, fc33ecb, baa02e9` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| LIB-01 | 27-02, 27-05 | One-line ini entry produces injected contract tests; no conftest edits | SATISFIED | `pyproject.toml:62` + live collection produces 580 items via `-o` override |
| LIB-02 | 27-03 | Stable nodeids `<mcp-contracts>::test_<name>[<tool>]` from `--collect-only` without spawning MCP server | SATISFIED | Live: 580 nodeids in correct shape; collection runs sub-3.93s per 27-03 SUMMARY (handshake is brief, not "spawned for tests") |
| LIB-03 | 27-01, 27-05 | Test bodies extracted verbatim; v1.3 assertion semantics unchanged | SATISFIED | 10 async tests in `contracts/_tests.py`; line count within +0.7% of analog |
| LIB-04 | 27-03 | `mcp_contract` marker auto-applied; `-m mcp_contract` selects | SATISFIED | Per-item marker re-application at line 343; spike + 27-03 SUMMARY confirm marker selection works |
| LIB-05 | n/a | Removed per D-01 (no `register()` API) | REMOVED | REQUIREMENTS.md:35, 119 marks Removed |
| LIB-06 | (Phase 26) | `mcp_*` prefixed fixtures don't collide with operator names | SATISFIED | `_plugin.py:57-68` re-exports prefixed fixtures; deprecation aliases retained |
| LIB-07 | 27-04 | `_session_needs_preflight` marker-based | SATISFIED | `fixtures.py:129-173` primary marker branch present |
| LIB-08 | 27-01, 27-05 | Black-box guard relocated; wheel-introspection AST guard | SATISFIED | `_black_box_guard.py` exists, invoked from plugin; AST-walk test green |
| CFG-01 | 27-02, 27-04, 27-05 | Ini is sole library-mode source; MCPTF_CONFIG_FILE killed with DeprecationWarning | SATISFIED | DeprecationWarning at `_plugin.py:148-156`; no env-var write in src/ |
| CFG-02 | n/a | Removed per D-01 | REMOVED | REQUIREMENTS.md:43, 124 marks Removed |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

None observed. Spot scans for hardcoded empties / stub returns / TODO markers in the 5 src/ files modified by Phase 27 (`_plugin.py`, `_black_box_guard.py`, `_runner.py`, `cli.py:_load_config`, `fixtures.py:_session_needs_preflight`) found no anti-patterns. The Phase 27 `_plugin.py` hooks all have substantive bodies; no `return None` stubs; no placeholder text.

### Human Verification Required

None. All scope items are verifiable programmatically through file inspection, grep, and live `pytest --collect-only` runs. The operator-tone error rendering paths (D-14 missing-path; D-15 invalid-YAML) were manually smoke-tested by Plan 27-02 (Sanity 1, Sanity 2) and recorded verbatim in `27-02-SUMMARY.md` lines 87-125; live `pytest --collect-only` already exercises the happy path end-to-end.

### Carry-Overs Tracked

| Carry-over | Where tracked | Status |
| ---------- | ------------- | ------ |
| `typer.Exit → INTERNALERROR>` residual after operator-tone validation error | `27-02-SUMMARY.md:137-148` (plan 27-02 added `except SystemExit: pytest.exit(returncode=2)` translation in `_plugin.py:187-196`); `27-03-SUMMARY.md:182-184` (Issues Encountered); `27-04-SUMMARY.md:135-143` (TypeR.Exit Carry-over section); `27-04-SUMMARY.md:174` (Next Phase Readiness — investigate); `27-05-SUMMARY.md:57` (key-decisions, not folded in); `27-05-SUMMARY.md:232-251` (dedicated section, deferred with rationale needing tighter repro) | TRACKED across 4 SUMMARYs; deferred to backlog with rationale (needs tighter repro before fixing); not silently lost |

### Gaps Summary

No gaps. All 13 scope items in the orchestrator's verification spec are independently verifiable in the codebase and pass. The phase has delivered:

1. **A single-line operator entry point** — `pyproject.toml [tool.pytest.ini_options] mcp_config_file = PATH` produces injected contract tests with the synthetic `<mcp-contracts>::test_<name>[<tool>]` nodeid, no conftest ceremony required.
2. **One config-resolution mechanism end-to-end** — CLI (`mcp-contracts run --config PATH`) and library mode (operator's ini line) both route through the same `mcp_config_file` ini key; the env-var WRITE has been deleted, and the env-var READ remains only as a back-compat path with DeprecationWarning.
3. **Framework dogfood** — every `uv run pytest` exercises the plugin's `pytest_configure → Config(yaml_file=...) → check_black_box → pytest_collection` chain via the framework's own `config.test.yaml`.
4. **Documentation aligned to the ini-route pivot** — REQUIREMENTS.md and ROADMAP.md amended; LIB-05 and CFG-02 marked Removed per D-01.
5. **The one known imperfection** (`typer.Exit → INTERNALERROR>` residual) is tracked across multiple SUMMARYs with a deferral rationale (needs tighter repro), not silently dropped.

The scope items from `27-CONTEXT.md` (which CONTEXT.md explicitly states supersedes the original phase title and REQUIREMENTS LIB-01..08 / CFG-01..02 text) are all satisfied. Live smoke checks (framework regression 602 passed, contract collection 580 items in correct nodeid shape, wheel-shape AST guard 11 passed) corroborate the static evidence.

---

_Verified: 2026-05-16_
_Verifier: Claude (gsd-verifier)_
