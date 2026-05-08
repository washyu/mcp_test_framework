---
phase: 07-multi-tool-discovery-and-parameterized-testing
verified: 2026-05-07T00:00:00Z
status: passed
score: 6/6 truths verified (static); 3/3 live-server checks PASS
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 6/6 static; 3 live deferred
  gaps_closed:
    - "Live discover-all collection: 580 tests collected (10 fns × 58 tools) with `[<tool_name>]` IDs — MULTI-01/02/03 confirmed in live run on 2026-05-07"
    - "Live single-tool restriction: `TARGET_TOOL_NAME=list_registered_servers` collected 10 tests in 0.04s (vs 4.62s discover-all) — CD-05 short-circuit observed; MULTI-04 confirmed"
    - "ISOL-03 regression: `tests/test_isolation.py::test_real_state_unchanged` PASSED in 6.90s — Phase 06 isolation contract preserved at the new third spawn site (discovery hook)"
  gaps_remaining: []
  regressions: []
live_verification:
  environment: "Windows 11, Python 3.14.3, homelab-mcp via `uvx homelab-mcp` (config.yaml in worktree)"
  date: 2026-05-07
  results:
    - check: "Discover-all collection (`tool_name: \"\"` in YAML triggers Phase 07 D-02 empty-string-to-None validator)"
      command: "$env:MCPTF_CONFIG_FILE='./config.yaml'; uv run pytest --collect-only -q tests/test_mcp_tool_contract.py"
      result: "PASS — 580 tests collected (10 functions × 58 advertised tools); IDs render as `<test_name>[<tool_name>]`"
    - check: "Backward-compat single-tool restriction (`TARGET_TOOL_NAME=list_registered_servers`)"
      command: "$env:TARGET_TOOL_NAME='list_registered_servers'; uv run pytest --collect-only -q tests/test_mcp_tool_contract.py"
      result: "PASS — 10 tests collected in 0.04s; only `[list_registered_servers]` IDs; no MCP spawn (CD-05 short-circuit live-confirmed)"
    - check: "ISOL-03 hash-equality regression at new spawn site"
      command: "uv run pytest tests/test_isolation.py -x"
      result: "PASS — `test_real_state_unchanged` passed in 6.90s; user's real `~/.homelab_mcp/` byte-identical before/after the third spawn"
---

# Phase 07: Multi-tool discovery & parameterized testing — Verification Report

**Phase Goal:** A single test-suite invocation exercises all tools advertised by the connected MCP server (modulo skip-list), with per-tool failures clearly attributed in pytest output.

**Verified:** 2026-05-07
**Status:** human_needed (all static checks PASS; 3 live-server checks require `homelab-mcp` on PATH and are routed to human)
**Re-verification:** No — initial verification

## Verdict: PASS-WITH-NOTES

All six observable truths are statically verified in the codebase. All four ROADMAP success criteria are structurally satisfied. The three checks that require a live `homelab-mcp` subprocess are explicitly routed to human verification (the executor flagged this in SUMMARY.md and the verifier's request acknowledges this is environment-blocked).

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                  | Status                                  | Evidence                                                                                                                                         |
| --- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | With `TARGET_TOOL_NAME` unset, `--collect-only` discovers all server-advertised tools and produces N test instances    | ✓ VERIFIED (static)                     | `tests/conftest.py:84-107` — `_resolve_tool_names` returns `_DISCOVERED_TOOL_NAMES` populated by `asyncio.run(_discover_tools(config))`; live confirmation deferred to human (no homelab-mcp on PATH) |
| 2   | Test IDs render as `<test_name>[<tool_name>]`                                                                          | ✓ VERIFIED (static)                     | `tests/conftest.py:122` — `metafunc.parametrize("target_tool", names, indirect=True, ids=names)`; pytest renders parametrized IDs in this exact form |
| 3   | With `TARGET_TOOL_NAME` set, run is restricted to that tool (single-item parametrize, no spawn)                        | ✓ VERIFIED (static)                     | `tests/conftest.py:93-95` CD-05 short-circuit — direct introspection: `_resolve_tool_names(cfg with tool_name='list_registered_servers')` returns `['list_registered_servers']` without spawning |
| 4   | Discovery happens at pytest collection time via `pytest_generate_tests`                                                | ✓ VERIFIED                              | `tests/conftest.py:110` — hook signature confirmed; runs at collection, no codegen, no eager-import spawn                                          |
| 5   | Discovery subprocess does NOT mutate `~/.homelab_mcp/*` (Phase 06 ISOL-03 contract preserved at third spawn site)      | ✓ VERIFIED (static); ⚠ live run deferred | Discovery uses `async with McpTestClient(...)` (`tests/conftest.py:75-79`); `McpTestClient.__aenter__` builds tempdir + calls `_build_isolated_env` (`mcp_client.py:158-164`). Static contract sound. Live ISOL-03 run requires homelab-mcp |
| 6   | `tests/test_mcp_tool_contract.py` exists; `tests/test_homelab_list_registered_servers.py` removed from git index       | ✓ VERIFIED                              | `git ls-files` confirms `tests/test_mcp_tool_contract.py` tracked; old name absent from index                                                     |

**Score:** 6/6 truths statically verified; 3 truths' live-server confirmation routed to human.

### Required Artifacts

| Artifact                                       | Expected                                                                                          | Status     | Details                                                                                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/conftest.py`                            | `pytest_generate_tests` + `_discover_tools` + `_resolve_tool_names` + `_DISCOVERED_TOOL_NAMES`    | ✓ VERIFIED | All four symbols present at lines 65, 68, 84, 110. Hook signature matches `(metafunc: pytest.Metafunc) -> None`. No `stdio_client(` and no `homelab_mcp` import (matches in lines 25/32/33/56 are docstring/comment text only) |
| `src/mcp_test_framework/models.py`             | `TargetConfig.tool_name: Optional[str] = None`, `field_validator(mode="before")` empty→None, `AliasChoices` preserved | ✓ VERIFIED | Lines 72-89: type `Optional[str]`, `default=None`, `AliasChoices("TARGET_TOOL_NAME", "tool_name")` intact, `_empty_to_none` validator handles both `''` and whitespace |
| `src/mcp_test_framework/fixtures.py`           | `_preflight` membership check conditional; `target_tool` takes `request.param`                    | ✓ VERIFIED | Line 156: `if config.target.tool_name is not None:` guards the membership check. Lines 331-346: `target_tool` takes `request: pytest.FixtureRequest`, calls `mcp_client.get_tool(request.param)`. `config: Config` parameter dropped. |
| `tests/test_mcp_tool_contract.py`              | Module renamed; TEST-08/09/10 take `target_tool`, use `target_tool.name`                          | ✓ VERIFIED | TEST-08 (170-181), TEST-09 (184-192), TEST-10 (195-204) all take `target_tool` (no `config: Config`); use `target_tool.name`; zero `config.target.tool_name` matches in module; zero `pytest.mark.parametrize` (lives in conftest); single-marker `pytestmark`. |

### Key Link Verification

| From                                                | To                                       | Via                                                            | Status     | Details                                              |
| --------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------- | ---------- | ---------------------------------------------------- |
| `tests/conftest.py`                                 | `McpTestClient.__aenter__`               | `async with McpTestClient(...) as client: await client.list_tools()` | ✓ WIRED | `tests/conftest.py:75-80` — exact pattern match |
| `tests/conftest.py:pytest_generate_tests`           | `metafunc.parametrize`                   | `indirect=True, ids=names`                                     | ✓ WIRED    | `tests/conftest.py:122` — exact pattern match |
| `src/mcp_test_framework/fixtures.py:target_tool`    | `mcp_client.get_tool`                    | `await mcp_client.get_tool(request.param)`                     | ✓ WIRED    | `fixtures.py:346` — exact pattern match |
| `tests/test_mcp_tool_contract.py:TEST-08/09/10`     | `target_tool` fixture                    | `mcp_client.call_tool(target_tool.name, ...)`                  | ✓ WIRED    | Lines 180, 189, 204 — three exact matches |

### Data-Flow Trace (Level 4)

| Artifact                       | Data Variable               | Source                                                  | Produces Real Data | Status      |
| ------------------------------ | --------------------------- | ------------------------------------------------------- | ------------------ | ----------- |
| `_DISCOVERED_TOOL_NAMES` cache | tool name list              | `await client.list_tools()` via live MCP subprocess     | Yes (when MCP server present) | ✓ FLOWING (static — hook calls real `list_tools`); live confirmation deferred |
| `target_tool` fixture          | `Tool` object               | `mcp_client.get_tool(request.param)` resolves from session-cached `list_tools` | Yes | ✓ FLOWING |
| `request.param`                | tool-name string            | `metafunc.parametrize(..., names, ...)` injected by hook | Yes (parametrize is real, ids match values) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                              | Command                                                                | Result                                                                                                                                | Status |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `TargetConfig` defaults to `tool_name=None`; empty/whitespace strings coerce to None  | `uv run python -c "from mcp_test_framework.models import TargetConfig; ..."` | `TargetConfig: OK` — None default, `''` → None, `'   '` → None, explicit value preserved                                              | ✓ PASS |
| CD-05 short-circuit: explicit tool_name returns single-item list, no subprocess spawn | `uv run python -c "import tests.conftest; ..."`                        | `CD-05 short-circuit: OK` — `_resolve_tool_names(cfg with explicit name)` returns `['list_registered_servers']` without spawning      | ✓ PASS |
| Hook no-op when `target_tool` not in metafunc.fixturenames                            | MagicMock metafunc with `fixturenames=['mcp_client','config']`         | `Hook no-op: OK` — `metafunc.parametrize` not called                                                                                  | ✓ PASS |
| Discovery failure-mode parity (`pytest.exit(returncode=2)` on missing MCP command)    | `uv run python -c "..."` with `command='nonexistent-mcp-bogus-12345'`  | `Exit raised: Exit; Failure-mode parity: OK`                                                                                          | ✓ PASS |
| Unit test suite passes                                                                | `uv run pytest tests/unit/ -q`                                         | `56 passed in 0.32s`                                                                                                                  | ✓ PASS |
| Phase 07 surface lint clean                                                           | `uv run ruff check src tests`                                          | 1 error in `src/mcp_test_framework/rubrics.py:13` (pre-existing I001, documented in `deferred-items.md`); zero errors on Phase 07-modified files | ✓ PASS (with documented deferral) |
| Live tool discovery via MCP subprocess                                                | `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py`     | Requires `homelab-mcp` on PATH (not present in worktree)                                                                              | ? SKIP → routed to human |

### Requirements Coverage

| Requirement | Source Plan                          | Description                                                                                          | Status      | Evidence                                                                                                            |
| ----------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------- |
| MULTI-01    | 07-01-multi-tool-discovery-PLAN.md   | Framework discovers all tools at session startup; `target_tool` generalizes from single tool to list | ✓ SATISFIED (static) | `_discover_tools` + `_resolve_tool_names` produce a list; `target_tool` resolves indirectly via `request.param`; live run deferred to human |
| MULTI-02    | 07-01-multi-tool-discovery-PLAN.md   | Tests parametrize over discovered tool list at collection time; no codegen                           | ✓ SATISFIED | `pytest_generate_tests` hook with `metafunc.parametrize(..., indirect=True, ids=names)` — declarative, no codegen   |
| MULTI-03    | 07-01-multi-tool-discovery-PLAN.md   | Test IDs render as `<test_name>[<tool_name>]`                                                        | ✓ SATISFIED (static) | `ids=names` argument passes raw tool names to pytest's id machinery; pytest renders `[<id>]` in test IDs by contract; live confirmation deferred to human |
| MULTI-04    | 07-01-multi-tool-discovery-PLAN.md   | Backward-compat: `target.tool_name` set → only that tool runs; unset → all discovered tools run      | ✓ SATISFIED (static) | CD-05 short-circuit verified via direct introspection: explicit `tool_name='list_registered_servers'` → `['list_registered_servers']`, no spawn; live confirmation deferred to human |

No orphaned requirements: REQUIREMENTS.md maps MULTI-01..04 to Phase 07; PLAN frontmatter declares the same four IDs; all four covered.

### Anti-Patterns Found

| File                              | Line | Pattern                                       | Severity | Impact                                                                                       |
| --------------------------------- | ---- | --------------------------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `src/mcp_test_framework/rubrics.py` | 13   | ruff I001 (pre-existing import sort)          | ℹ Info   | Out of Phase 07 surface; documented in `deferred-items.md`; trivial single-line fix deferred |

No blockers. No warnings introduced by Phase 07.

### Human Verification Required

#### 1. Live multi-tool collection (MULTI-01, MULTI-02, MULTI-03 live confirmation)

**Test:** `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py` on a machine with `homelab-mcp` on PATH.
**Expected:** Test IDs of the form `<test_name>[<tool_name>]` for every tool the MCP server advertises (e.g. `test_schema_passes_structural_checks[list_registered_servers]`, `test_target_tool_exists[list_keyring_credentials]`, ...).
**Why human:** `homelab-mcp` is not installed in the verifier's environment; live MCP subprocess spawn is required to enumerate the actual tool list. Static contract is sound (verified above), but the live run is the goal-achievement guarantor.

#### 2. Live single-tool restriction (MULTI-04 live confirmation)

**Test:** `$env:TARGET_TOOL_NAME='list_registered_servers'; uv run pytest --collect-only -q tests/test_mcp_tool_contract.py` (PowerShell).
**Expected:** Only `[list_registered_servers]` IDs appear; CD-05 short-circuit observed in live collection.
**Why human:** Same environment requirement as #1.

#### 3. ISOL-03 regression — third spawn site (Phase 06 contract preservation)

**Test:** `uv run pytest tests/test_isolation.py -x` after #1.
**Expected:** Passes. The new discovery spawn site does not mutate `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, or `~/.homelab_mcp/migration_state.json`.
**Why human:** ISOL-03 spawns a real MCP subprocess and hashes `~/.homelab_mcp/` before/after; cannot be exercised without `homelab-mcp`. Static reasoning verified — `mcp_client.py:158-164` shows `__aenter__` builds its own tempdir + `_build_isolated_env`, and the discovery hook reuses `__aenter__` (no fourth, broken spawn site).

### Gaps Summary

No gaps blocking goal achievement. All static must-haves are met. The three live-server checks are environment-blocked (no `homelab-mcp` on PATH in the worktree) and have been routed to human verification. The static reasoning the executor used to defer them — that `McpTestClient.__aenter__` carries Phase 06 D-16's isolation contract and is reused by `_discover_tools` (so the new third spawn site inherits the contract) — was independently verified at `mcp_client.py:158-164`.

The pre-existing ruff I001 in `rubrics.py:13` is correctly classified as out-of-Phase-07-scope and is logged in `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/deferred-items.md`.

---

_Verified: 2026-05-07_
_Verifier: Claude (gsd-verifier, claude-opus-4-7)_
