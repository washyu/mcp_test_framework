---
phase: 04-fixtures-test-cases
plan: 02
subsystem: testing
tags: [pytest-asyncio, fixtures, preflight, AsyncExitStack, judge-protocol, session-scope]

# Dependency graph
requires:
  - phase: 01-foundation-pure-data-core
    provides: "Config() loader + frozen sub-models (OllamaConfig, McpServerConfig, TargetConfig); tests/conftest.py black-box guard"
  - phase: 02-mcp-client-wrapper
    provides: "McpTestClient(command, args, timeout_seconds) async stdio client with AsyncExitStack ownership; ToolNotFoundError(name, available)"
  - phase: 03-ollama-judge
    provides: "OllamaJudge(base_url, model, timeout_seconds) + Judge Protocol seam in judge_protocol.py"
  - plan: 04-01
    provides: "Rubric base + ClarityRubric / DisambiguationRubric / ParametersRubric subclasses with shared hardening preamble"
provides:
  - "src/mcp_test_framework/fixtures.py: 8 session-scoped fixtures (config, mcp_client, judge, target_tool, _preflight, rubric_clarity, rubric_disambiguation, rubric_parameters)"
  - "AsyncExitStack ownership inside mcp_client and judge fixture bodies (Pitfall 1 mitigation)"
  - "_preflight autouse session gate: shutil.which -> Ollama /api/tags -> MCP brief handshake -> target tool membership; pytest.exit(returncode=2) on failure"
  - "_session_needs_preflight guard: short-circuits autouse preflight when only tests/unit/ items collected (deviation Rule 1)"
  - "tests/conftest.py: pytest_plugins registration of mcp_test_framework.fixtures (D-layout-1 seam)"
affects:
  - 04-03-tests-plan (the 10 integration tests consume these fixtures by name via pytest dependency injection)
  - Phase 5 CLI (run command will pytest.main against this fixture set unchanged)

# Tech tracking
tech-stack:
  added: []  # No new dependencies; httpx is transitive via mcp / used by ollama_judge.py.
  patterns:
    - "Autouse session-scoped pytest_asyncio fixture with autouse-skip guard via request.session.items inspection"
    - "Fixture-arg dependency injection: target_tool takes _preflight as a no-yield-value arg so pytest sequences preflight first"
    - "Type-annotate fixture return against Protocol (Judge) not concrete class (OllamaJudge) -- D-layout-2 / SEED-001 enabler"

key-files:
  created:
    - "src/mcp_test_framework/fixtures.py"
  modified:
    - "tests/conftest.py"

key-decisions:
  - "All 8 fixtures live in src/mcp_test_framework/fixtures.py rather than tests/conftest.py; tests/conftest.py registers via pytest_plugins so post-MVP framework adopters add a one-line plugin registration to inherit the fixture set."
  - "judge fixture is type-annotated `-> Judge` (Protocol) not `-> OllamaJudge` (concrete). Internal OllamaJudge instantiation stays inside the fixture body so SEED-001 backend swap is a one-fixture-body change."
  - "_preflight is autouse=True session-scoped but guarded by _session_needs_preflight(request) which inspects request.session.items and short-circuits when every collected nodeid starts with 'tests/unit/'. Plan acceptance requires `pytest tests/unit/ -v` to pass on a machine without homelab-mcp; integration runs (tests/test_*.py) get the full four-step preflight."
  - "target_tool takes _preflight as a fixture arg (in addition to mcp_client) so pytest's dependency resolver runs preflight -> mcp_client -> target_tool. Defense in depth alongside preflight's check (D-preflight-3): McpTestClient.get_tool raises ToolNotFoundError with the candidate-tool list."
  - "AsyncExitStack ownership inside mcp_client and judge fixture bodies (not just `async with X(...) as y: yield y`). Matches Phase 2's McpTestClient.__aenter__ and Phase 3's OllamaJudge.__aenter__ pattern -- the documented Pitfall 1 mitigation: 'reverse-order unwind in the SAME task that did __aenter__'."

patterns-established:
  - "Autouse session-scoped preflight gate with fail-fast pytest.exit(returncode=2) and structured single-line diagnostics naming both the failed precondition and the configured value (e.g., 'Ollama at http://127.0.0.1:11434 not reachable: ConnectError'). Returncode 2 distinguishes preflight-abort from pytest pass/fail (0/1) for CI branching."
  - "Autouse-skip guard: when an autouse session fixture should NOT fire for a subset of tests (e.g., unit tests with no I/O dependency), inspect request.session.items at setup and short-circuit. Preserves autouse semantics for the integration session while letting unit-only sessions pass on machines without the integration deps."
  - "Type-annotate fixture returns against the Protocol seam, not the concrete implementation. `judge: Judge`, never `judge: OllamaJudge`. Future backend swaps stay 1-fixture-body changes."

requirements-completed: [FIX-01, FIX-02, FIX-03]

# Metrics
duration: ~3.5 min
completed: 2026-05-06
---

# Phase 4 Plan 02: Pytest-Asyncio Fixtures + _preflight Gate Summary

**8 session-scoped framework fixtures wired together with AsyncExitStack ownership, an autouse `_preflight` session gate that fails fast on missing MCP/Ollama deps, and `pytest_plugins` registration in tests/conftest.py -- the load-bearing seam Plan 03's 10 integration tests will consume by name.**

## Performance

- **Duration:** ~3.5 min
- **Started:** 2026-05-06T00:02:19Z (worktree branch base verified at 674ac245)
- **Completed:** 2026-05-06T00:05:58Z
- **Tasks:** 3 (all completed; one Rule 1 deviation fix applied)
- **Files created:** 1
- **Files modified:** 1

## Accomplishments

- Eight session-scoped fixtures shipped: `config`, `mcp_client`, `judge`, `target_tool`, `_preflight`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`.
- `_preflight` autouse gate runs four cheapest-first checks (`shutil.which` -> Ollama `/api/tags` -> MCP brief handshake -> target tool membership) and emits structured single-line diagnostics on failure via `pytest.exit(returncode=2)`.
- `mcp_client` and `judge` own their I/O lifecycle through `AsyncExitStack` inside the fixture body -- Pitfall 1 mitigation, "reverse-order unwind in the SAME task that did __aenter__".
- `judge` fixture return-type annotation is `Judge` (Protocol from `judge_protocol.py`), never `OllamaJudge` -- SEED-001 backend swap remains a one-fixture-body change.
- `tests/conftest.py` retains the Phase 1 black-box guard verbatim and adds `pytest_plugins = ["mcp_test_framework.fixtures"]` -- the load-bearing one-line seam adopters add to their own conftest.
- Deviation Rule 1 fix: `_session_needs_preflight(request)` guard short-circuits the autouse session preflight when only `tests/unit/` items are collected, so unit tests pass on machines without homelab-mcp / Ollama (Plan acceptance requirement).

## Task Commits

Each task was committed atomically (--no-verify per parallel-executor protocol):

1. **Task 1: Create src/mcp_test_framework/fixtures.py -- all 8 fixtures with AsyncExitStack ownership and _preflight gate** -- `c112a10` (feat)
2. **Task 2: Modify tests/conftest.py -- add pytest_plugins registration; preserve black-box guard verbatim** -- `d2cceef` (feat)
3. **Task 3 deviation fix: skip _preflight when only tests/unit/ items collected** -- `9d413d2` (fix)

Task 3's verification was inline (collection-only + `tests/unit/` run); the deviation fix was the only file change Task 3 produced and is captured in commit `9d413d2`.

_Plan metadata commit covered by orchestrator after worktree merge._

## Files Created/Modified

- **`src/mcp_test_framework/fixtures.py`** (245 lines) -- 8 fixtures + `_preflight` + `_session_needs_preflight` helper. Autouse session-scoped preflight; AsyncExitStack ownership inside `mcp_client` and `judge` fixture bodies; `judge` return-type-annotated as `Judge` Protocol.
- **`tests/conftest.py`** (modified, +8 / -4 lines) -- added `pytest_plugins = ["mcp_test_framework.fixtures"]` at module top; updated docstring to describe the load-bearing seam; Phase 1 `pytest_configure` body and the `Black-box rule violated` RuntimeError preserved verbatim.

## Fixture Decorator/Scope Map (per plan output spec)

| Fixture | Decorator | Scope | Loop scope | Type annotation | Notes |
|---------|-----------|-------|------------|-----------------|-------|
| `config` | `@pytest.fixture` | `session` | n/a (sync) | `-> Config` | Trivially returns `Config()`; cached for the session. |
| `_preflight` | `@pytest_asyncio.fixture(autouse=True, ...)` | `session` | `session` | (no return) | autouse=True so it runs before any test without explicit injection. Skips when only `tests/unit/` items collected. |
| `mcp_client` | `@pytest_asyncio.fixture` | `session` | `session` | (no annotation; yields `McpTestClient`) | AsyncExitStack-owned; depends on `_preflight`. |
| `judge` | `@pytest_asyncio.fixture` | `session` | `session` | `-> Judge` (Protocol) | AsyncExitStack-owned `OllamaJudge` instance; tests annotate `judge: Judge`. |
| `target_tool` | `@pytest_asyncio.fixture` | `session` | `session` | (no annotation; returns `Tool`) | Takes `_preflight` as fixture arg so pytest sequences preflight first. |
| `rubric_clarity` | `@pytest.fixture` | `session` | n/a (sync) | `-> ClarityRubric` | Trivial sync fixture. |
| `rubric_disambiguation` | `@pytest.fixture` | `session` | n/a (sync) | `-> DisambiguationRubric` | Trivial sync fixture. |
| `rubric_parameters` | `@pytest.fixture` | `session` | n/a (sync) | `-> ParametersRubric` | Trivial sync fixture. |

## _preflight Four-Step Order + Verbatim Diagnostics

1. **MCP binary on PATH** -- `shutil.which(config.mcp_server.command)`. On miss:
   ```
   MCP command 'homelab-mcp' not found on PATH
   ```
2. **Ollama `/api/tags` reachable** -- `httpx.AsyncClient(...timeout=httpx.Timeout(10.0, connect=10.0)).get("/api/tags")` with `raise_for_status()`. On any exception:
   ```
   Ollama at http://127.0.0.1:11434 not reachable: <ExcClass>: <exc>
   ```
3. **Configured model present** -- after `/api/tags` payload parses, check `config.ollama.model in [m.name for m in payload.models]`. On miss:
   ```
   model 'qwen3.6:latest' not in /api/tags (available: ['<other-models>', ...])
   ```
4. **MCP brief handshake + target tool membership** -- `async with McpTestClient(...) as brief: tools = await brief.list_tools()` (single subprocess spawn, then close). On any exception during handshake:
   ```
   MCP handshake with 'homelab-mcp' failed: <ExcClass>: <exc>
   ```
   On `target.tool_name` not in `[t.name for t in tools]`:
   ```
   target tool 'list_registered_servers' not in MCP server tool list (available: [...])
   ```

Each `pytest.exit(...)` call passes `returncode=2` so a future CI can branch on preflight-abort vs. regular pass/fail (0/1) without parsing stderr.

## Confirmation Checklist (per plan `<output>` spec)

- [x] `judge` fixture is annotated `-> Judge` (Protocol from `mcp_test_framework.judge_protocol`), NOT `-> OllamaJudge`. Verified: `grep -c '-> Judge'` returns 1.
- [x] `target_tool` fixture takes `_preflight` as an arg (in addition to `mcp_client` and `config`) so pytest's dependency resolver runs preflight first. Verified: `async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):`.
- [x] `tests/conftest.py` retains the Phase 1 guard body verbatim. Verified: `grep -c 'Black-box rule violated'` returns 1; `grep -c 'def pytest_configure'` returns 1.
- [x] `pytest_plugins = ["mcp_test_framework.fixtures"]` registered. Verified: `import tests.conftest; assert tests.conftest.pytest_plugins == ['mcp_test_framework.fixtures']`.
- [x] All 8 fixtures importable from `mcp_test_framework.fixtures`. Verified: `python -c "from mcp_test_framework.fixtures import config, mcp_client, judge, target_tool, _preflight, rubric_clarity, rubric_disambiguation, rubric_parameters; print('all 8 importable')"` prints `all 8 importable`.

## Verification Run

- `uv run pytest tests/ --collect-only -q` -- 56/60 collected, 4 deselected (smoke tests with `live_homelab` / `live_ollama` markers), no `error in` substring.
- `uv run pytest tests/unit/ -v` -- 56 passed, 0 failed (Plan 01's 9 rubric tests + Phase 1-3 unit tests all green; preflight short-circuits because every nodeid starts with `tests/unit/`).
- `uv run ruff check src/mcp_test_framework/fixtures.py tests/conftest.py` -- All checks passed.
- `uv run python -c "from mcp_test_framework.fixtures import ...; print('all 8 importable')"` -- prints `all 8 importable`.

## Decisions Made

- **Place all 8 fixtures in `src/mcp_test_framework/fixtures.py` and register via `pytest_plugins`** (D-layout-1) -- so post-MVP framework adopters add the same one-line plugin registration to their own conftest. Tests/conftest.py retains the Phase 1 black-box guard body verbatim.
- **`judge` fixture return-annotated `-> Judge`, not `-> OllamaJudge`** (D-layout-2) -- preserves SEED-001 backend-swap as a one-fixture-body change. The fixture body internally instantiates `OllamaJudge(...)` inside an `AsyncExitStack`.
- **`_preflight` is autouse session-scoped + skip-guarded** -- the autouse semantics gate every integration test (D-preflight-1: "before any test starts"); the skip guard inspects `request.session.items` to bypass preflight when only `tests/unit/` items are collected. This was a Rule 1 deviation fix: the plan acceptance criteria mandated both `autouse=True` and `pytest tests/unit/ -v` passing on a machine without homelab-mcp on PATH; the guard reconciles them.
- **`target_tool` takes `_preflight` as a fixture arg** -- pytest's dependency resolver sequences `_preflight -> mcp_client -> target_tool` so preflight runs before the long-lived MCP session spawns.
- **Cheapest-first preflight ordering** (D-discretion) -- `shutil.which` (no I/O) -> `/api/tags` (one HTTP) -> MCP brief handshake (one subprocess spawn) -> target tool membership (already in step-3 output). Abort early on the first failure with that check's diagnostic.
- **Use `pytest.exit(reason, returncode=2)` for preflight failures** (D-markers-2) -- distinguishes preflight-abort from regular pytest pass/fail. Single-line diagnostic naming both the failed precondition and the configured value (D-preflight-4); no ERROR cascade across 10 tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Autouse session-scoped `_preflight` was firing on `tests/unit/` runs**

- **Found during:** Task 3 verification (`uv run pytest tests/unit/ -v`)
- **Issue:** The plan's Task 1 specified `_preflight` as `autouse=True, scope="session"` with no skip guard. This caused the four-step preflight to run at session start for `pytest tests/unit/`, which immediately failed with `MCP command 'homelab-mcp' not found on PATH` -- correct behavior for an integration session, but the unit tests are pure-data sync tests with no MCP/Ollama dependency. Plan 04-02 Task 3 acceptance explicitly required `uv run pytest tests/unit/ -v exits 0`. Without a guard, the two acceptance items contradicted each other.
- **Fix:** Added `_session_needs_preflight(request)` helper that inspects `request.session.items` at fixture setup; if every collected nodeid starts with `tests/unit/`, the fixture short-circuits via `yield; return` without running the four checks. For integration runs (`tests/test_*.py`), the full four-step preflight runs unchanged.
- **Files modified:** `src/mcp_test_framework/fixtures.py`
- **Commit:** `9d413d2`
- **Invariants preserved:** `autouse=True` (count: 2 -- the fixture decorator + a docstring reference; the decorator is the load-bearing one), `scope="session"`, `loop_scope="session"`, structured `pytest.exit(returncode=2)` diagnostics on each failure path, AsyncExitStack ownership in `mcp_client` and `judge`. Verified via grep counts after the fix.

**Total deviations:** 1 (auto-fixed Rule 1 bug)
**Impact on plan:** None to architecture; the `_preflight` contract from D-preflight-1 is preserved for integration runs. Acceptance for Task 3 (`tests/unit/` green) now passes.

## Issues Encountered

- **Ruff I001 import ordering + invalid noqa directive** -- Initial Task 1 fixtures.py had a stray comment block between imports and used a malformed `# noqa: ASYNC` directive that ruff flagged. Auto-fixed via `ruff check --fix` (import block reflow) and a manual edit removing the bogus noqa. No deviation rule needed -- these were lint-time issues caught before commit.
- **`asyncio_default_test_loop_scope=function` warning** -- pytest-asyncio's session output shows `asyncio_default_test_loop_scope=function` (the default), distinct from the locked `asyncio_default_fixture_loop_scope=session`. This is informational; tests in Plan 03 will use `pytest.mark.asyncio(loop_scope="session")` to align test loops with the fixture loop (Pitfall 1 + the `tests/smoke/test_smoke_homelab_mcp.py` reference shape).

## Threat Surface Scan

The new files introduce NO new attack surface beyond what the plan's `<threat_model>` mitigates:

- **T-04-04 (DoS -- MCP subprocess hangs):** mitigated by `AsyncExitStack` ownership in `mcp_client` + the brief preflight session, both inheriting Phase 2's `asyncio.timeout(self._timeout_seconds)` SDK-call wrapping. Two distinct subprocess lifecycles per session -- preflight's brief client closes before `mcp_client` spawns its long-lived session.
- **T-04-05 (DoS -- Ollama unreachable):** mitigated by the locked `httpx.Timeout(10.0, connect=10.0)` on the preflight `/api/tags` call. All exceptions funnel into a single `except Exception as exc` -> `pytest.exit(returncode=2)` path with no silent retry.
- **T-04-06 (Info disclosure in diagnostics):** accepted -- diagnostic strings include `base_url`, model name, MCP command, and tool name. These are local-network values from `Config()` and operator-public per FIX-02 acceptance ("fails fast with a clear diagnostic").
- **T-04-07 (Tampering -- judge fixture body swap):** accepted -- post-MVP hardening item. The `Judge` Protocol is `@runtime_checkable`; adding `assert isinstance(instance, Judge)` after instantiation is a future safety net, not a Plan 02 deliverable.

No new surface (no network endpoints, no auth paths, no schema changes, no file access patterns).

## Known Stubs

None. All 8 fixtures are wired end-to-end:

- `config` returns a real `Config()`.
- `mcp_client` and `judge` enter their respective `AsyncExitStack`-owned async context managers and yield live instances.
- `target_tool` calls `mcp_client.get_tool(...)` and returns a real `Tool` (or raises `ToolNotFoundError`).
- `_preflight` runs four real checks against the configured Ollama and MCP.
- The three rubric fixtures return real `ClarityRubric()` / `DisambiguationRubric()` / `ParametersRubric()` instances from Plan 01.

## TDD Gate Compliance

This plan ships in three commits ordered `feat -> feat -> fix`. The plan was not flagged `tdd="true"` -- it's an integration-wiring plan, not a TDD plan. Plan 03 will land the actual integration tests against these fixtures, and those tests are the lock-in suite for FIX-01/02/03 in practice. The plan author intentionally split the verification surface across Plan 02 (fixture wiring) and Plan 03 (live integration tests).

## User Setup Required

None for this plan. The fixtures are imported via `pytest_plugins`; no env vars added; no external services configured.

For Plan 03's tests to actually run green, the user's machine needs:
- `homelab-mcp` on PATH (or invocable via `uvx homelab-mcp`).
- Ollama reachable at `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`) with the configured model (`qwen3.6:latest`) pulled.

If those are missing, `_preflight` aborts the session at the first missing precondition with a structured single-line diagnostic and `returncode=2`. No ERROR cascade.

## Next Phase Readiness

- **Plan 04-03 (integration tests)** can now write the 10 spec'd tests using fixture-arg dependency injection. The fixtures auto-load via `pytest_plugins`; tests don't need to re-import them. Test signatures look like:
  ```python
  async def test_description_clarity(judge: Judge, target_tool, rubric_clarity): ...
  async def test_empty_args_call_returns_non_error(mcp_client, config): ...
  ```
- The `Judge` Protocol annotation surface is locked: tests annotate `judge: Judge`, never `judge: OllamaJudge`. No test should import `OllamaJudge`.
- `loop_scope="session"` is the contract for all Plan 03 async tests (matches `pyproject.toml` lock + the smoke-test reference shape). Tests use `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` at module top.
- No blockers for Plan 03. The fixture seams are all in place.

## Self-Check

Verify all claims:

**Files created/modified (exist on disk):**
- `src/mcp_test_framework/fixtures.py` -- FOUND (245 lines)
- `tests/conftest.py` -- FOUND (modified; pytest_plugins added; Phase 1 guard preserved)

**Commits exist in git log:**
- `c112a10` -- FOUND (`feat(04-02): add 8 session-scoped fixtures + _preflight gate`)
- `d2cceef` -- FOUND (`feat(04-02): register fixtures plugin in tests/conftest.py`)
- `9d413d2` -- FOUND (`fix(04-02): skip _preflight when only tests/unit/ items collected`)

**Acceptance criteria for Task 1 (all met):**
- File exists, 245 lines (>= 150) -- PASS
- Smoke verify command prints `OK fixtures present: [...]` listing all 8 -- PASS
- `pytest_asyncio.fixture(loop_scope="session", scope="session")` count >= 4 (3 explicit + 1 autouse-variant `pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")`) -- PASS
- `AsyncExitStack` count >= 2 (count = 7 -- imports + mcp_client body + judge body + multiple references) -- PASS
- `pytest.exit(` count >= 4 (count = 7 -- 5 call sites + 2 docstring references) -- PASS
- `returncode=2` (non-comment) count >= 4 (count = 8) -- PASS
- `-> Judge` count >= 1 (count = 1) -- PASS
- `autouse=True` count >= 1 (count = 2 -- decorator + docstring reference) -- PASS
- `async def target_tool` count = 1 with `_preflight` in params -- PASS
- No `import homelab_mcp` / `from homelab_mcp` -- PASS

**Acceptance criteria for Task 2 (all met):**
- `pytest_plugins = ["mcp_test_framework.fixtures"]` count = 1 -- PASS
- `def pytest_configure` count = 1 (Phase 1 guard preserved) -- PASS
- `Black-box rule violated` count = 1 (Phase 1 RuntimeError message preserved verbatim) -- PASS
- `uv run ruff check tests/conftest.py` exits 0 -- PASS
- Automated `import tests.conftest` smoke prints `OK conftest.py` -- PASS

**Acceptance criteria for Task 3 (all met after deviation fix):**
- `uv run pytest tests/ --collect-only -q` exits 0 -- PASS (56/60 collected, 4 deselected)
- Output does NOT contain `error in` substring -- PASS
- Output lists at least 9 collected items -- PASS (56 collected)
- `uv run pytest tests/unit/ -v` exits 0 with all unit tests passing -- PASS (56 passed, 0 failed)
- No `homelab-mcp.exe` process leaks (collection-only spawned no subprocess; unit tests spawn no subprocess; preflight skip-guard prevents brief-handshake spawn) -- PASS

## Self-Check: PASSED

---
*Phase: 04-fixtures-test-cases*
*Plan: 02*
*Completed: 2026-05-06*
