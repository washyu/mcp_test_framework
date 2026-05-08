---
phase: 07-multi-tool-discovery-and-parameterized-testing
plan: 01
subsystem: test-discovery
tags: [pytest, parametrize, mcp, discovery, isolation]
requires:
  - Phase 06 D-16 (McpTestClient.__aenter__ isolation-aware)
  - Phase 04 _preflight + session-scoped fixtures
provides:
  - Multi-tool discovery + indirect parametrize at pytest collection time
  - "[<tool_name>]" test IDs uniformly across all tests requesting target_tool
  - Backward-compat with TARGET_TOOL_NAME=<name> (single-item parametrize, no spawn)
  - Empty-string-to-None env-var coercion for TARGET_TOOL_NAME
affects:
  - tests/conftest.py
  - src/mcp_test_framework/models.py
  - src/mcp_test_framework/fixtures.py
  - tests/test_mcp_tool_contract.py (renamed from test_homelab_list_registered_servers.py)
  - tests/unit/test_config.py (default-assertion fix)
tech-stack:
  patterns:
    - pytest_generate_tests + indirect=True
    - module-level cache for collection-time discovery (CD-01)
    - reuse of McpTestClient.__aenter__ for new spawn sites (Phase 06 isolation inheritance)
    - empty-string-to-None Pydantic v2 field_validator at the env-config boundary
key-files:
  created:
    - tests/test_mcp_tool_contract.py (renamed via git mv -- 88% similarity preserved blame)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/deferred-items.md
  modified:
    - src/mcp_test_framework/models.py (+18/-2)
    - src/mcp_test_framework/fixtures.py (+10/-7)
    - tests/conftest.py (+76/-1)
    - tests/test_mcp_tool_contract.py (+13/-9 body edits + docstring)
    - tests/unit/test_config.py (+3/-1)
  removed:
    - tests/test_homelab_list_registered_servers.py (renamed; tracked by git as rename)
decisions:
  - D-01..D-17 + CD-01 (module-level dict cache), CD-03 (hook in conftest, not module pytestmark), CD-04 (test_mcp_tool_contract.py), CD-05 (short-circuit when tool_name set), CD-06 (single cohesive plan)
metrics:
  duration_minutes: 6
  completed: 2026-05-07
  task_count: 3
  commit_count: 3
  files_modified: 5
  files_renamed: 1
---

# Phase 07 Plan 01: Multi-Tool Discovery Summary

Generalized the v1.0 single-tool test loop to N-tools-per-run via collection-time tool discovery + indirect parametrize. Discovery now happens in a sync `pytest_generate_tests` hook (third spawn site, isolation-inherited from `McpTestClient.__aenter__`); `target_tool` is indirectly parametrized; the test module is tool-agnostic. Closes MULTI-01..MULTI-04.

## What Changed

### Task 1 — `TargetConfig.tool_name` widened to `Optional[str]`

- `src/mcp_test_framework/models.py`: `tool_name: Optional[str] = Field(default=None, ...)` with `AliasChoices("TARGET_TOOL_NAME", "tool_name")` preserved.
- New `@field_validator("tool_name", mode="before")` coerces empty/whitespace strings → `None` (Pitfall 2 — the project's `_BareNameNestedEnvSource` reads `TARGET_TOOL_NAME=''` as the literal empty string without this validator).
- `src/mcp_test_framework/fixtures.py:_preflight` membership check is now conditional on `config.target.tool_name is not None` (D-15). When unset, the discovery hook produces the parametrize list — preflight membership would be redundant.
- **Commit:** `2c26ce6`

### Task 2 — `pytest_generate_tests` discovery hook + indirect `target_tool`

- `tests/conftest.py`: new `_discover_tools` async helper, `_resolve_tool_names` cache, module-level `_DISCOVERED_TOOL_NAMES`, and `pytest_generate_tests` hook.
- Hook **reuses** `McpTestClient.__aenter__` (Phase 06 D-16) — third spawn site, isolation contract inherited automatically. **No** open-coded `stdio_client(...)`.
- CD-05 short-circuit: when `config.target.tool_name` is truthy → single-item list, **zero subprocess spawn**.
- Failure path mirrors `_preflight`: `pytest.exit(..., returncode=2)` for exit-code parity.
- `src/mcp_test_framework/fixtures.py:target_tool` rewritten to take `request: pytest.FixtureRequest`; `mcp_client.get_tool(request.param)`. The `config: Config` parameter dropped — parametrize layer in conftest now owns name source.
- **Commit:** `c7a3771`

### Task 3 — Rename test module + rewrite TEST-08/09/10

- `git mv tests/test_homelab_list_registered_servers.py → tests/test_mcp_tool_contract.py` (88% similarity; blame preserved).
- TEST-08, TEST-09, TEST-10: drop `config: Config` parameter, accept `target_tool` fixture, replace `config.target.tool_name` → `target_tool.name` (Pitfall 3).
- Module docstring updated for Phase 07 multi-tool framing.
- Unused `from mcp_test_framework.config import Config` removed.
- TEST-01..TEST-07 unchanged (already fixture-driven).
- Module-level `pytestmark` stays single-marker — parametrize lives in conftest only (CD-03).
- **Commit:** `07714b7`

## Verification Results

| Check | Status | Notes |
|-------|--------|-------|
| `uv run python -c "from mcp_test_framework.models import TargetConfig; ..."` | PASS | Default None; `tool_name=''` coerces to None; explicit value preserved |
| `uv run python -c "from mcp_test_framework.config import Config; c = Config(); ..."` | PASS | tool_name is None by default |
| `uv run ruff check tests src/mcp_test_framework/models.py src/mcp_test_framework/fixtures.py` | PASS | All Phase 07 surface clean |
| `uv run pytest tests/unit/ -q` | PASS | 56/56 unit tests pass |
| Black-box rule: `grep -nE "^(import\|from)\s+homelab_mcp" tests/conftest.py src/mcp_test_framework/{fixtures,models}.py` | PASS | Zero matches |
| Hook wiring smoke: `metafunc.parametrize` called with `("target_tool", names, indirect=True, ids=names)` | PASS | Verified via MagicMock metafunc |
| Hook short-circuit: `TARGET_TOOL_NAME=list_registered_servers` → `['list_registered_servers']` (no spawn) | PASS | Verified via direct `_resolve_tool_names` call |
| Hook no-op when `target_tool` not in `metafunc.fixturenames` | PASS | Verified via MagicMock metafunc |
| Discovery hook fires `pytest.exit(returncode=2)` when `homelab-mcp` is absent from PATH | PASS | Confirmed via `uv run pytest --collect-only` -- expected behavior per Task 2 `<done>` criteria |

### Environment-blocked checks (require `homelab-mcp` on PATH)

The worktree at `C:\Users\washy\projects\mvp_test_framework\.claude\worktrees\sweet-black-074ea5` does **not** have `homelab-mcp` installed. The plan explicitly anticipated this for Task 3 acceptance:

> `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py 2>&1 | grep -E "\\[list_registered_servers\\]"` returns at least one match (assumes homelab-mcp on PATH at execution time; if not, this acceptance check is replaced by a manual run)

The following acceptance checks are environment-deferred to a manual run on a machine with `homelab-mcp` installed:

- Phase verification #1: collection produces `<test_name>[<tool_name>]` IDs for every advertised tool (MULTI-01, MULTI-02, MULTI-03)
- Phase verification #2: `TARGET_TOOL_NAME=list_registered_servers` restricts run to that tool (MULTI-04 backward-compat — the `_resolve_tool_names` short-circuit was verified via direct Python introspection above)
- Phase verification #3: `tests/test_isolation.py` regression (ISOL-03 hash-equality — also requires homelab-mcp; the new spawn site reuses `McpTestClient.__aenter__` which already inherits `_build_isolated_env` per Phase 06 D-16)

The static contract for ISOL-03 preservation is verified at code-review time via the `grep -c "stdio_client(" tests/conftest.py` check (zero open-coded `stdio_client(...)` calls in conftest — the only occurrence is in a comment).

## Deviations from Plan

**1. [Rule 1 — Bug] Updated `tests/unit/test_config.py::test_defaults`**
- **Found during:** Task 3 verification (`uv run pytest tests/unit/`)
- **Issue:** The unit test asserted `cfg.target.tool_name == "list_registered_servers"` against the v1.0 default — this contract was changed by Task 1 (Phase 07 D-01 default is now `None`).
- **Fix:** Changed assertion to `cfg.target.tool_name is None` with a comment citing Phase 07 D-01.
- **Files modified:** `tests/unit/test_config.py`
- **Commit:** `07714b7` (folded into Task 3 commit since the change is a direct consequence of Task 1's contract shift)

**2. [Rule 2 — Hygiene] Fixed ruff I001 introduced by Task 2 import block**
- **Found during:** Task 3 verification (`uv run ruff check src tests`)
- **Issue:** New imports added in conftest.py were not alphabetized within the `# noqa: E402` post-`pytest_plugins` block (`sys` came before `asyncio`).
- **Fix:** Reordered to `asyncio`, `sys`, `from typing import Optional`.
- **Files modified:** `tests/conftest.py`
- **Commit:** `07714b7`

## Deferred Issues

**Pre-existing ruff I001 in `src/mcp_test_framework/rubrics.py`** — out of scope for Phase 07 plan 01. Logged in `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/deferred-items.md`. Verified pre-existing via `git stash` (error survives stash of all phase 07 changes).

## Patterns Surfaced

- **Reuse of `McpTestClient.__aenter__` for new spawn sites.** Every new place where the framework spawns the MCP server should go through `async with McpTestClient(...) as client:` rather than open-code `stdio_client(...)`. The context manager owns the per-instance tempdir + `_build_isolated_env` env block (Phase 06 D-16) — bypassing it creates a broken spawn site that can leak state to the user's real `~/.homelab_mcp/`. The `tests/conftest.py:_discover_tools` helper is the canonical example.

- **Lazy collection-time discovery via module-level cache.** The discovery hook caches `_DISCOVERED_TOOL_NAMES` at module level (CD-01) so the subprocess is spawned once per pytest invocation — even though `pytest_generate_tests` fires once per test function that requests `target_tool`. The first hook call populates the cache; subsequent calls reuse it.

- **Empty-string-to-None Pydantic v2 validator.** When using a custom env source (like the project's `_BareNameNestedEnvSource`), `model_validator(mode="before")` is the right place to coerce the env-var-presence-without-value sentinel — `field_validator(mode="before")` works specifically for one field and runs before type coercion, so it sees the raw string.

## Threat Flags

None. Phase 07's threat surface is identical to v1.0 plus the third spawn site, which is mitigated at code-review time (T-07-02 → `grep -c "stdio_client("` returns 0 in `tests/conftest.py`) and at runtime via Phase 06's existing ISOL-03 regression test.

## Self-Check: PASSED

- File `tests/test_mcp_tool_contract.py`: FOUND
- File `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/deferred-items.md`: FOUND
- Commit `2c26ce6`: FOUND in git log
- Commit `c7a3771`: FOUND in git log
- Commit `07714b7`: FOUND in git log
- Old file `tests/test_homelab_list_registered_servers.py`: REMOVED (tracked by git as rename, no longer in index)
