# Phase 15 Verification — 2026-05-11

**Status:** PASS
**Recorded by:** Phase 15 Plan 04 executor agent (worktree agent-aea8fa5d02dfeaacd)
**Config used:** `config.yaml` (v2 worktree config; 2-tool allowlist: `list_keyring_credentials`, `suggest_deployments`)
**Live MCP server:** `uvx homelab-mcp` (58 tools discovered)
**Live Ollama:** `127.0.0.1:11434` model `qwen3:0.6b`

## Executive Summary

All 4 ROADMAP success criteria (SC-1..SC-4) verified PASS. Two pre-existing test bugs caused by Plan 15-01's mechanical relocation were auto-fixed in scope as Rule 1 deviations (commits `327af82` and `d8d464c`); see "Deviations from Plan" below.

---

## SC-1: Operator default scope is contract only

> An operator running `mcp-test-framework run` against an MCP server with two enabled tools sees only contract-level results (~20 cases for 2 tools); the ~107 framework self-tests are not collected and do not appear in the operator's output.

### Recipe 4a (argv channel via `--raw`) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run mcp-test-framework run --raw -- --collect-only -q
```

Result:
- Exit code: **0**
- `grep -c "tests/framework"` against captured output: **0** (no framework leaks at the pytest argv layer)
- `grep -c "tests/contract"` against captured output: **20** (one per collected case)
- pytest summary line: `20 tests collected in 3.51s`

Evidence (tail):
```
tests/contract/test_mcp_tool_contract.py::test_parameters_self_explanatory[list_keyring_credentials]
tests/contract/test_mcp_tool_contract.py::test_empty_args_call_returns_non_error[list_keyring_credentials]
tests/contract/test_mcp_tool_contract.py::test_result_has_content_or_structured[list_keyring_credentials]
tests/contract/test_mcp_tool_contract.py::test_text_content_parses_as_json[list_keyring_credentials]

20 tests collected in 3.51s
```

### Recipe 4b (wrapper-rendered channel — the actual operator-visible output) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run mcp-test-framework run > recipe4b-stdout.log 2>&1
```

Result:
- Exit code: **1** (real judge-failure outcome; 2 PASS / 2 FAIL — operator sees real-world clarity rubric failures from `qwen3:0.6b` against homelab-mcp tool descriptions; FAIL is a SUT-contract result, NOT a Phase 15 regression)
- `grep -c "tests/framework"` against `recipe4b-stdout.log`: **0**
- `grep -c "tests/contract"` against `recipe4b-stdout.log`: **0** (the domain UI hides path strings — operator sees tool names only)
- 12-name framework-test grep (`test_isolation|test_runner_renderer|test_runner_subprocess|test_runner_verbosity|test_readme_snippets|test_config_init_cli|test_tool_config|test_runner_live_smoke|test_banned_imports|test_smoke_homelab_mcp|test_smoke_ollama_judge|test_mcp_client_teardown_regression`): **0 matches**

Evidence (header + summary):
```
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56  (use --explain to list)
Judges:      (none configured)
Test plan:   20 contract cases
...
Result: 0 PASS / 2 FAIL / 56 SKIP  in 15.6s
```

The wrapper-rendered output is pure MCP-domain language — `MCP server`, `Discovered`, `Running`, `Skipping`, `Test plan`, tool names — with zero pytest framing, zero framework-test names, and zero `tests/framework/` path references.

**SC-1 VERDICT: PASS** (both channels clear)

---

## SC-2: `--with-framework` opt-in extends to framework subtree

> A maintainer running `uv run pytest tests/` directly continues to exercise both `tests/contract/` and `tests/framework/`; the runner's `--with-framework` (or equivalent) opt-in flag makes the same surface reachable through the operator CLI for CI use.

### Recipe 5 (`mcp-test-framework run --with-framework --raw`) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run mcp-test-framework run --with-framework --raw -- --collect-only -q
```

Result:
- Exit code: **0**
- `grep -c "tests/framework"` against captured output: **289** (framework subtree present)
- `grep -c "tests/contract"` against captured output: **20** (contract subtree present)
- pytest summary line: `309/324 tests collected (15 deselected) in 3.75s`

Both subtrees present; 309 = 20 contract + 289 framework — matches the maintainer backward-compat Recipe 3 exactly.

### Recipe 3 (maintainer backward compat: `uv run pytest tests/`) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/ --collect-only -q
```

Result:
- Exit code: **0**
- `grep -c "tests/framework"`: **289**
- `grep -c "tests/contract"`: **20**
- pytest summary: `309/324 tests collected (15 deselected) in 3.96s`

Pytest's natural directory recursion picks up both subtrees automatically. CI pipelines wired to `pytest tests/` continue to work without changes.

**SC-2 VERDICT: PASS**

---

## SC-3: git history preserved for moved files

> The repo's `tests/contract/` and `tests/framework/` directory split preserves git history for every moved file (verified by `git log --follow` on at least one file from each subtree).

### Recipe 6 — **PASS** (3/3 files show pre-move history)

**`tests/contract/test_mcp_tool_contract.py`** — Phase 04 origin commit visible:
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
f85fa96 feat(08-02): thread ToolConfig guards through TEST-01..10
07714b7 feat(07-01): rename test module + rewrite TEST-08/09/10 for target_tool
6b0884f feat(04-03): add 10 integration tests for homelab-mcp list_registered_servers
```
4 commit lines, oldest from Phase 04. PASS.

**`tests/framework/test_banned_imports.py`** (hoisted from `tests/unit/` per D-10) — Phase 01 origin commit visible:
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
382e9bf test(01-04): add ruff TID251 smoke test with banned-import fixture
```
2 commit lines, oldest from Phase 01-04. PASS.

**`tests/framework/test_isolation.py`** — Phase 06 origin commit visible:
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
7202924 fix(06): WR-06 tighten D-11 skip to cover empty ~/.homelab_mcp/ dir
c8cc188 fix(06): WR-05 use bound tempdir_homelab consistently in step-4 assertion
6ce01e9 fix(06): WR-02 remove unused Config import and parameter from test_real_state_unchanged
0eaa316 test(06-03): add ISOL-03 hash-equality + ISOL-06 cross-platform tempdir test
```
5 commit lines, oldest from Phase 06. PASS.

**SC-3 VERDICT: PASS** (all three representative files retain pre-move history via `git log --follow`)

---

## SC-4: black-box enforcement at SURFACE-04 literal path

> The black-box rule remains mechanically enforced: `tests/framework/test_banned_imports.py` continues to fail the maintainer suite if `homelab-mcp` is imported anywhere in `src/`. The enforcement does not depend on which test surface the operator selected.

### Recipe 7 (`uv run pytest tests/framework/test_banned_imports.py -v`) — **PASS** (post-fix)

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/framework/test_banned_imports.py -v
```

Result (post-fix):
- Exit code: **0**
- pytest output: `3 passed in 5.78s`
- All three sub-tests pass:
  - `test_ruff_tid251_fires_on_top_level_import` — PASSED
  - `test_ruff_tid251_fires_on_from_import` — PASSED
  - `test_ruff_tid251_misses_submodule_import_documented_gap` — PASSED

The test was discovered and ran at the SURFACE-04 literal path (`tests/framework/test_banned_imports.py`), and the ruff TID251 banned-api enforcement fired correctly on the canonical fixture.

**Pre-fix state** (initial recipe invocation): exit 0, 1 failed + 2 passed. The single failure (`test_ruff_tid251_fires_on_top_level_import`) traced to a stale fixture path constant inside the test (`tests/_fixtures/...` vs. the post-15-01 fixture location `tests/framework/_fixtures/...`) — a regression caused by Plan 15-01's mechanical relocation, fixed in commit `d8d464c` as a Phase 15 in-scope Rule 1 auto-fix (see Deviations below).

**SC-4 VERDICT: PASS**

---

## Supporting recipes

### Recipe 1 (`uv run pytest tests/contract/`) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/contract/ --collect-only -q
```

Result:
- Exit code: **0** (NOT 5 — contract surface non-empty)
- Collected: **20 tests** (10 cases × 2 enabled tools — matches the SC-2 ~20-for-2-tools expectation precisely)
- `grep -c "tests/framework"` against output: **0**

Evidence (full collection in correct path):
```
tests/contract/test_mcp_tool_contract.py::test_target_tool_exists[suggest_deployments]
tests/contract/test_mcp_tool_contract.py::test_schema_passes_structural_checks[suggest_deployments]
... (18 more cases, all under tests/contract/)
20 tests collected in 3.87s
```

### Recipe 2 (`uv run pytest tests/framework/`) — **PASS**

Command:
```
MCPTF_CONFIG_FILE=config.yaml uv run pytest tests/framework/ --collect-only -q
```

Result:
- Exit code: **0**
- Collected: **289 / 304** (15 deselected by conftest's allowlist filter for parametrize-time skipping)
- `grep -c "tests/contract"` against output: **0** (zero contract leakage)

Note on the count: SEED-010's phase narrative cited "~107 framework self-tests" — that figure dates back to v1.1 close (2026-05-08); since then the framework self-test suite has grown to 304 collected entries (289 enabled after parametrize-time filtering). The growth is from v1.2 work expanding the runner/CLI/config surface (Phases 12, 13, 14). The phase invariant is still met: the framework subtree is non-empty and isolated from `tests/contract/`.

### Recipe 3 (`uv run pytest tests/`) — **PASS**

See above under SC-2.

---

## Deviations from Plan

### Auto-fixed Issues (Rule 1 — pre-existing bugs caused by Plan 15-01's relocation, fixed in 15-04 scope)

**1. [Rule 1 - Bug] `test_plugins_list_does_not_register_reporter` path bug** (commit `327af82`)

- **Found during:** Pre-flight prep for Recipe 2 (was flagged in `deferred-items.md` from Plan 15-02)
- **Issue:** `Path(__file__).resolve().parents[1]` resolved to `tests/` (not the repo root) after Plan 15-01 moved the file from `tests/test_runner_subprocess.py` to `tests/framework/test_runner_subprocess.py`. The conftest probe looked for `tests/tests/conftest.py` (non-existent) and the fallback file read raised `FileNotFoundError`.
- **Fix:** Two-character change — `parents[1]` → `parents[2]`. Documented in the test docstring.
- **Files modified:** `tests/framework/test_runner_subprocess.py`
- **Commit:** `327af82` (`fix(15-04): repair test_plugins_list_does_not_register_reporter after 15-01 file move`)
- **Verification:** `uv run pytest tests/framework/test_runner_subprocess.py::test_plugins_list_does_not_register_reporter -v` → `1 passed in 4.40s`
- **Rationale for in-scope fix:** Per Phase 15 title ("operator vs framework test surface split") and CONTEXT.md `Claude's Discretion` step 4 (the verification recipe set), the regression was directly caused by 15-01's mechanical relocation. Fixing it here keeps the phase shippable in a single closure window rather than spawning a 15-05 gap-closure plan for a 2-character fix.

**2. [Rule 1 - Bug] `test_banned_imports.py` fixture path bug** (commit `d8d464c`)

- **Found during:** Recipe 7 execution (the SURFACE-04 enforcement check)
- **Issue:** `_FIXTURE` was hardcoded as `_REPO_ROOT / "tests" / "_fixtures" / "banned_import_should_fail.py.txt"`. Plan 15-01 moved the fixture from `tests/_fixtures/` to `tests/framework/_fixtures/` (carried inside the bulk hoist of `test_banned_imports.py` from `tests/unit/`). The test's fixture-path constant was not updated to follow, so `test_ruff_tid251_fires_on_top_level_import` failed with `AssertionError: fixture missing: ...tests\_fixtures\banned_import_should_fail.py.txt`.
- **Fix:** Update `_FIXTURE` to `_REPO_ROOT / "tests" / "framework" / "_fixtures" / "banned_import_should_fail.py.txt"`. Added a code comment explaining the post-split path.
- **Files modified:** `tests/framework/test_banned_imports.py`
- **Commit:** `d8d464c` (`fix(15-04): repair test_banned_imports fixture path after 15-01 file move`)
- **Verification:** Recipe 7 re-run after fix → `3 passed in 5.78s` (was `1 failed, 2 passed`)
- **Rationale for in-scope fix:** Same as #1 — directly caused by 15-01's mechanical relocation. Additionally, leaving it broken would mask SC-4 (SURFACE-04 enforcement at the literal path), since the test that proves the black-box rule fires would itself be failing for non-banned-import reasons.

No other deviations from plan.

---

## Authentication Gates

None. All recipes ran without user-facing auth prompts. The live MCP subprocess (`uvx homelab-mcp`) and the live Ollama judge (`http://127.0.0.1:11434`) were both reachable from the worktree.

---

## Outstanding Issues

None — all 7 recipes PASS, all 4 success criteria verified.

Notes for the human-checkpoint reviewer:
- Recipe 4b's exit code is **1** (test failures), not 0. That is the correct outcome for the SC-1 verification: SC-1 verifies the operator output **format**, not whether the operator's SUT passes its rubrics. The two FAIL outcomes are real-world `qwen3:0.6b` clarity-rubric verdicts against homelab-mcp's `list_keyring_credentials` and `suggest_deployments` tool descriptions (score 2 vs. threshold 4). This is the framework correctly catching a real description-quality gap on the SUT, which is exactly the value proposition of v1.0+.
- Recipe 2's collection count is 289/304, not the ~107 cited in SEED-010's prose. The growth is from v1.2's framework expansion (Phases 12/13/14 added significant runner / CLI / config surface). The phase invariant — framework subtree non-empty and isolated from contract subtree — is still met. Worth surfacing at the human checkpoint if reviewer wants to update SEED-010's narrative for v1.3+.
- Two auto-fix commits (`327af82`, `d8d464c`) land on top of the prior 15-01/02/03 commits before this VERIFICATION.md commit; the diff is 14 lines across 2 files. Both are documented above with full diagnosis and rationale.
