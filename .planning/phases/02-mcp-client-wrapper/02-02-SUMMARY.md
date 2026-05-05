---
phase: 02-mcp-client-wrapper
plan: 02
subsystem: mcp_client
tags: [mcp-sdk, stdio, asyncio, async-context-manager, lifecycle, error-handling, logging]

# Dependency graph
requires:
  - phase: 01-foundation-pure-data-core
    provides: "pyproject.toml with pytest-asyncio strict, ruff TID251 ban on homelab_mcp imports, project package layout"
  - phase: 02-mcp-client-wrapper
    provides: "Plan 02-01 — McpServerConfig.timeout_seconds (consumed indirectly: caller passes the int into McpTestClient.__init__, no direct config import)"
provides:
  - "McpTestClient(command, args, timeout_seconds) — async context-managed stdio MCP client over the official mcp SDK"
  - "ToolNotFoundError(tool_name, available) — domain LookupError raised by McpTestClient.get_tool() (FIX-03 will surface this in a fixture)"
  - "_LoggerWriter — TextIOBase adapter routing subprocess stderr lines to stdlib logger 'mcp_test_framework.mcp_client.stderr' via the SDK's errlog parameter"
  - "live_homelab pytest marker registration + addopts = -m 'not live_homelab' so live tests are skipped by default (D-03)"
affects: [02-03-mcp-smoke-test, 04-fixtures-and-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AsyncExitStack-owned lifecycle in __aenter__/__aexit__ (Pitfall 1 mitigation: enter/exit happen in the same task)"
    - "asyncio.timeout(self._timeout_seconds) wrapped around every SDK call (initialize, list_tools, call_tool) — single uniform ceiling per D-06"
    - "shutil.which() pre-flight before stdio_client to surface friendlier missing-binary diagnostic than the SDK's bare [WinError 2]"
    - "errlog plumbed via TextIOBase adapter to stdlib logger (RESEARCH Pattern 3) rather than discarded or shoved into a list"
    - "Domain error class lives in the same module as the API that raises it (parallels ValidationIssue in schema_validator.py)"
    - "NO 5s force-kill belt — Q1 OPTION A locked: SDK's _terminate_process_tree (SIGTERM→SIGKILL on 2.0s timer; Job Object on Windows) is the production-tested fallback; CONTEXT.md D-04 was revised post-research"

key-files:
  created:
    - "src/mcp_test_framework/mcp_client.py (~159 LOC — McpTestClient, ToolNotFoundError, _LoggerWriter)"
    - "tests/unit/test_mcp_client.py (~76 LOC — 5 unit tests covering ToolNotFoundError payload + _LoggerWriter buffering)"
    - "README.md (Rule 3 deviation — minimal stub to unblock hatchling build, full README is Phase 5)"
  modified:
    - "pyproject.toml ([tool.pytest.ini_options]: markers += live_homelab, addopts += -m 'not live_homelab')"

key-decisions:
  - "Q1 OPTION A confirmed: NO 5s force-kill belt; trust SDK's _terminate_process_tree (CONTEXT D-04 revised)"
  - "D-06 honored: single uniform asyncio.timeout(self._timeout_seconds) ceiling around initialize/list_tools/call_tool — not per-method overrides"
  - "D-03 honored: live_homelab marker registered AND defaulted to skip via addopts so the smoke test in Plan 02-03 does not run on `uv run pytest`"
  - "FIX-03 wired: ToolNotFoundError carries the candidate tool list so Phase 4's target_tool fixture can render a useful diagnostic"
  - "Test scope: only mock-friendly slices (exception payload + logger adapter buffering). Live timeout/subprocess behavior is left to Plan 02-03's smoke test against the real binary — mocking stdio_client is high-cost / low-signal (CONTEXT discretion)"

patterns-established:
  - "stdio MCP client = AsyncExitStack-owned (stdio_client + ClientSession entered in same task) + asyncio.timeout outside every SDK call + errlog→logger adapter"
  - "shutil.which() pre-flight before any subprocess context manager is the cheap belt for OS-specific missing-binary errors"
  - "Domain exception classes live with the API that raises them, not in a cross-cutting models.py"
  - "Pytest live-network markers MUST also have addopts skip-by-default registration so the suite stays green on machines without the live target"

requirements-completed: [CORE-03]

# Metrics
duration: ~35min (executor wall clock; permission lockout interrupted summary write — orchestrator created this file post-hoc, see Deviations)
completed: 2026-05-05
---

# Phase 2 Plan 2: McpTestClient Summary

**Async stdio MCP client wrapper shipped: AsyncExitStack lifecycle in a single task, uniform asyncio.timeout ceiling, errlog→logger adapter, ToolNotFoundError, plus the live_homelab marker registration that keeps the suite green by default.**

## Performance

- **Duration:** ~35 min executor wall clock (excludes ~1 min orchestrator-side SUMMARY.md write below)
- **Started:** 2026-05-05T02:05Z (approx)
- **Tasks:** 2 (Task 1: client + error class + logger adapter; Task 2: unit tests + pytest marker registration)
- **Files created:** 3 (`mcp_client.py`, `test_mcp_client.py`, `README.md`)
- **Files modified:** 1 (`pyproject.toml`)

## Accomplishments

- `McpTestClient` shipped at `src/mcp_test_framework/mcp_client.py` (~159 LOC) — `__init__(command, args, timeout_seconds)`, `__aenter__`/`__aexit__`, `list_tools()`, `get_tool(name)`, `call_tool(name, arguments)`
- `ToolNotFoundError(tool_name, available)` — domain `LookupError` carrying the candidate tool list for Phase 4's `target_tool` fixture
- `_LoggerWriter` — `io.TextIOBase` adapter routing each subprocess stderr line to stdlib logger `mcp_test_framework.mcp_client.stderr` at `WARNING` level; line-buffers across partial writes and flushes residual buffer on close
- `pyproject.toml` `[tool.pytest.ini_options]` extended with `markers = ["live_homelab: ..."]` and `addopts = "-m 'not live_homelab'"` (D-03)
- 5 new unit tests (`tests/unit/test_mcp_client.py`) — 3 for `ToolNotFoundError` payload shape, 2 for `_LoggerWriter` line buffering & flush
- `uv run pytest tests/` → 29/29 passed (5 new + 24 from Phase 1)
- `uv run ruff check src tests` → clean
- Black-box rule preserved: `grep -v '^#' src/mcp_test_framework/mcp_client.py | grep -c "homelab_mcp"` → 0
- `uv run python -c "from mcp_test_framework.mcp_client import McpTestClient"` → import OK

## Task Commits

Each task was committed atomically (`--no-verify` per parallel-executor protocol):

1. **Pre-Task: README stub (Rule 3 fix)** — `291d61c` (chore) — same fix Plan 02-01 made; required for `uv run` in this worktree
2. **Task 1: Add McpTestClient + ToolNotFoundError + _LoggerWriter** — `a018da3` (feat)
3. **Task 2: Unit tests + register live_homelab marker** — `78346d7` (test)

This SUMMARY.md was written by the orchestrator after the executor returned (see Deviations below).

## Files Created/Modified

- `src/mcp_test_framework/mcp_client.py` (CREATED, 159 lines) — McpTestClient class, ToolNotFoundError, _LoggerWriter, module docstring documenting D-04..D-08 and Pitfall 1/14 mitigations
- `tests/unit/test_mcp_client.py` (CREATED, 76 lines) — 5 sync unit tests against the mock-friendly slices
- `pyproject.toml` (MODIFIED) — added 2 lines under `[tool.pytest.ini_options]`: `markers` and `addopts`
- `README.md` (CREATED) — Rule 3 deviation, identical reasoning to Plan 02-01's stub (the parallel-wave merge will collapse the duplicates)

## Decisions Made

- **Q1 OPTION A locked.** No 5s force-kill belt. `stdio_client` does not expose the `Process` handle; the SDK's `_terminate_process_tree` (SIGTERM → SIGKILL on a 2.0s timer; Job Object on Windows) is the production-tested fallback. CONTEXT.md D-04 was revised post-research to reflect this.
- **Test scope deliberately narrow** (CONTEXT discretion). Mocking `stdio_client` to exercise live timeout/subprocess behavior is high-cost / low-signal — Plan 02-03's smoke test against the real `homelab-mcp` binary covers that. The unit tests in this plan therefore cover only the parts that are mock-friendly: exception construction and the line-buffering logic of `_LoggerWriter`.
- **`shutil.which()` pre-flight** added before `stdio_client` because the SDK's bare `[WinError 2]` is a poor diagnostic. The SDK does its own which() walk (`get_windows_executable_command`); this is belt-and-suspenders and was explicitly approved by the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created README.md stub (parallel-duplicate of Plan 02-01's fix)**
- **Found during:** Task 1 verification (`uv run python -c "..."`)
- **Issue:** Same root cause as Plan 02-01 — `pyproject.toml` declares `readme = "README.md"` but the file is not committed; hatchling fails the editable build, so every `uv run` fails. Each parallel worktree hit this independently.
- **Fix:** Wrote a 6-line stub README citing PROJECT.md and the MVP spec.
- **Files modified:** `README.md` (created)
- **Verification:** `uv run pytest` then succeeded.
- **Committed in:** `291d61c`
- **Note:** When the wave's worktrees merge, both Plan 02-01 and Plan 02-02 attempt to add `README.md`. Identical content avoids a real conflict; first-write wins and the second add is a no-op.

### Orchestrator-Recovered Items

**2. [Tooling] SUMMARY.md was created and committed by the orchestrator post-hoc**
- **Found during:** Task 2 wrap-up
- **Issue:** After the executor completed Task 2 successfully, both `Write` and `Bash` (every command tested, including `git --version`) became globally denied for the executor agent. The agent could not create or commit `02-02-SUMMARY.md`.
- **Fix:** The orchestrator (which retains its tool permissions) read the agent's report-back transcript, validated all three commits (`291d61c`, `a018da3`, `78346d7`) against the worktree, read `mcp_client.py` to confirm correctness, then wrote and committed this SUMMARY.md from the orchestrator side before triggering the worktree merge.
- **Files modified:** `02-02-SUMMARY.md` (created — this file)
- **Verification:** Orchestrator confirmed all task acceptance commands passed in the executor's transcript (29/29 pytest, ruff clean, black-box grep = 0, import OK, marker registered).
- **Committed in:** orchestrator-driven commit on `worktree-agent-aa04be1491a5848d2`
- **Impact on plan:** None on deliverables. Side effect on commit metadata: the SUMMARY.md commit is authored by the orchestrator session, not the executor agent. Verifier and downstream phases should treat this SUMMARY as authoritative.

---

**Total deviations:** 1 auto-fixed Rule 3 (parallel-duplicate of Plan 02-01) + 1 orchestrator-recovered tooling item

## Issues Encountered

- **Permission lockout post-Task-2:** As described above. The substantive deliverables were already committed; only the metadata commit was blocked. Fixed by orchestrator hand-off.
- **Cold-start `uv sync` in fresh worktree** (~30s on first invocation, 40 packages): expected, same as every fresh worktree.

## User Setup Required

None — `live_homelab`-marked tests are skipped by default; `homelab-mcp` is only required for `uv run pytest -m live_homelab tests/smoke/` (Plan 02-03).

## Next Phase Readiness

- Plan 02-03 can now drive `McpTestClient` (`__aenter__` → `list_tools` → `call_tool` → `__aexit__`) against live `homelab-mcp` to satisfy Phase 2 success criteria #1 and #2.
- Phase 4's session-scoped `mcp_client` fixture (FIX-01) has its dependency: `async with McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds) as client: ...` — exactly the shape the module docstring documents.
- Phase 4's `target_tool` fixture (FIX-03) will catch `ToolNotFoundError` and raise a precise diagnostic at session-start.

## Self-Check: PASSED

- Files claimed (verified by orchestrator on the worktree):
  - `src/mcp_test_framework/mcp_client.py` — FOUND (159 lines, McpTestClient + ToolNotFoundError + _LoggerWriter)
  - `tests/unit/test_mcp_client.py` — FOUND (76 lines, 5 tests)
  - `pyproject.toml` — MODIFIED (markers + addopts present in `[tool.pytest.ini_options]`)
  - `README.md` — FOUND (Rule 3 stub)
- Commits claimed (verified via `git log --oneline` on worktree branch):
  - `291d61c` — FOUND
  - `a018da3` — FOUND
  - `78346d7` — FOUND
- Test results (from executor transcript): `uv run pytest` → 29/29 passed
- Lint: `uv run ruff check src tests` → clean
- Black-box guard: 0 references to `homelab_mcp` in `mcp_client.py`
- Q1 OPTION A: confirmed in module docstring lines 22–23; no Process-handle access, no 5s force-kill belt

---
*Phase: 02-mcp-client-wrapper*
*Completed: 2026-05-05*
*SUMMARY recovery: orchestrator-side commit after executor permission lockout (substantive code commits were already in place)*
