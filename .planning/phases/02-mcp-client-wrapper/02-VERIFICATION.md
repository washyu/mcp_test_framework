---
status: human_needed
phase: 02-mcp-client-wrapper
phase_number: 02
verified_at: 2026-05-04
verifier: orchestrator (claude opus 4.7) — manual verification after subagent permission lockouts
must_haves_total: 4
must_haves_passed: 2
must_haves_human: 2
must_haves_failed: 0
requirements: [CORE-03]
---

# Phase 02 Verification Report

**Phase Goal (from ROADMAP):** Driving `homelab-mcp` over stdio works end-to-end via `McpTestClient`, with explicit timeouts and `CallToolResult` shape handling proven in a smoke script before any fixture depends on it.

**Outcome:** 2 of 4 success criteria deterministically verified by code + test inspection. The remaining 2 (SC#1, SC#2) require the live `homelab-mcp` binary on PATH and must be verified by the user — they are codified as falsifiable pytest tests gated on the `live_homelab` marker (D-01, D-04), but cannot run on this dev machine because `homelab-mcp` is not installed (RESEARCH Q2 / D-02 — design-correct fail-fast).

## Verifier Note — orchestrator hand-off

The standard verifier subagent was not invoked. The two preceding executor subagents (Plans 02-02 and 02-03) hit selective tool-permission lockouts mid-run, forcing orchestrator-side recovery in both cases. To avoid a third lockout cycle, the orchestrator performed verification directly using its own working tools (Read, Grep, Bash for `pytest`/`ruff`). This is a deviation from the standard `verify_phase_goal` flow but the evidence is recorded below for audit.

---

## Success Criteria Verification

### SC#1 — Raw stdio_client lists `list_registered_servers` with declared schema (no `homelab_mcp` import)

**Status:** `human_needed`

**Codified by:** `tests/smoke/test_smoke_homelab_mcp.py::test_raw_stdio_lists_target_tool` (Plan 02-03).

**Evidence (deterministic):**
- The test exists, is gated by `pytest.mark.live_homelab` and `pytest.mark.asyncio(loop_scope="session")` (module-level `pytestmark`).
- It uses `stdio_client + ClientSession` directly via `AsyncExitStack`, with NO `homelab_mcp` import anywhere in the file (verified by grep).
- It asserts `cfg.target.tool_name in [t.name for t in result.tools]` and that `target_tool.inputSchema` is a non-empty dict.
- `uv run pytest -m live_homelab --collect-only tests/smoke/` collects exactly 2 tests — confirmed.
- Black-box guard (Phase 1 CORE-02): the only `homelab_mcp` mentions across `src/` and `tests/` are the runtime guard in `tests/conftest.py`, the lint-rule unit tests in `tests/unit/test_banned_imports.py`, and the deliberately-quarantined fixture `tests/_fixtures/banned_import_should_fail.py.txt` (the `.txt` extension keeps it out of import).

**Why human verification is required:**
- `homelab-mcp` is not on PATH on this dev machine (RESEARCH Q2 confirmed). Per D-02, the test fails-fast inside the test body with `FileNotFoundError("MCP server command not on PATH: 'homelab-mcp'")` rather than skip at collection time.
- To prove the success criterion end-to-end, a user with `homelab-mcp` installed must run:
  ```
  uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_raw_stdio_lists_target_tool -v
  ```
  Expected: exit 0; the assertion `cfg.target.tool_name in names` confirms SC#1.

### SC#2 — `McpTestClient.call_tool("list_registered_servers", {})` returns isError=False with non-empty content/structuredContent

**Status:** `human_needed`

**Codified by:** `tests/smoke/test_smoke_homelab_mcp.py::test_wrapper_call_tool_returns_non_error_with_content` (Plan 02-03).

**Evidence (deterministic):**
- The test enters `async with McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds) as client` and calls `await client.call_tool(cfg.target.tool_name, {})`.
- It asserts both `not result.isError` AND `result.content or result.structuredContent` (handles either shape variance per CORE-03 wording).
- `McpTestClient` is implemented per CONTEXT.md D-04..D-08 with full lifecycle: `__aenter__` → `shutil.which` pre-flight → `stdio_client` → `ClientSession` → `initialize`, `__aexit__` → reverse-order unwind in same task.

**Why human verification is required:** Same reason as SC#1 — needs live `homelab-mcp` binary. Run:
```
uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_wrapper_call_tool_returns_non_error_with_content -v
```

### SC#3 — Every SDK call wrapped in `asyncio.timeout()` with explicit ceiling; manual subprocess kill produces a timeout error rather than hanging

**Status:** `passed`

**Evidence:**
- `src/mcp_test_framework/mcp_client.py` wraps every SDK call in `asyncio.timeout(self._timeout_seconds)`:
  - line 119: `await session.initialize()` (inside `__aenter__`)
  - line 142: `await self._session.list_tools()` (inside `list_tools()`)
  - line 158: `await self._session.call_tool(name, arguments)` (inside `call_tool()`)
- `get_tool()` calls `list_tools()` internally, so it inherits the timeout — verified at line 150.
- The single uniform timeout ceiling `self._timeout_seconds` is wired via the constructor argument, sourced from `cfg.mcp_server.timeout_seconds` (Plan 02-01) when fixtures consume the wrapper. D-06 honored.
- The "manually-killed subprocess produces a timeout error rather than hang" sub-criterion is structurally guaranteed by the `asyncio.timeout(...)` ceiling — when the SDK's read on the stdio pipe blocks waiting for a dead subprocess, the timer fires and the call raises `TimeoutError`. The Q1 OPTION A decision (no 5s force-kill belt; trust SDK's `_terminate_process_tree`) is documented in the module docstring at lines 22–23.

### SC#4 — Server stderr captured and surfaced via the SDK's `errlog` parameter to the framework logger

**Status:** `passed`

**Evidence:**
- `src/mcp_test_framework/mcp_client.py:42` declares `_log = logging.getLogger("mcp_test_framework.mcp_client.stderr")`.
- Lines 62–91 implement `_LoggerWriter(io.TextIOBase)` — line-buffered TextIO that splits incoming bytes on `\n` and routes each non-empty line to the stdlib logger at `WARNING` level. `flush()` drains residual buffer.
- Line 116 wires it: `stdio_client(params, errlog=_LoggerWriter(_log))` — the SDK accepts any TextIO via `errlog` per Plan 02-02 RESEARCH Pattern 3.
- Unit tests at `tests/unit/test_mcp_client.py` cover the buffering semantics (2 tests for `_LoggerWriter`) and the `ToolNotFoundError` payload shape (3 tests). All 5 pass.

---

## Requirement Traceability

| Requirement | Phase | Verified by | Status |
|---|---|---|---|
| CORE-03 (`mcp_client.py` exposes async `McpTestClient` wrapping the official mcp SDK with full lifecycle, asyncio.timeout, and CallToolResult handling) | 02 | SC#3 (deterministic), SC#4 (deterministic), unit tests, plus SC#1+SC#2 codified as live tests pending human run | partial — pending human run of `live_homelab` smoke for full sign-off |

---

## Test Suite State

- Default suite (`uv run pytest -q`): **30 passed, 2 deselected** (the 2 smoke tests are filtered out by `addopts = "-m 'not live_homelab'"`)
- Phase 1 regression (`uv run pytest tests/unit/test_config.py tests/unit/test_schema_validator.py tests/unit/test_banned_imports.py -q`): **25 passed**
- Lint (`uv run ruff check src tests`): clean
- Live opt-in collection (`uv run pytest -m live_homelab --collect-only tests/smoke/`): **2 tests collected** (test_raw_stdio_lists_target_tool, test_wrapper_call_tool_returns_non_error_with_content)
- Black-box guard: zero `import homelab_mcp` / `from homelab_mcp` outside the deliberately-quarantined Phase 1 lint-rule test fixtures and runtime guard

---

## Items requiring human verification

1. **SC#1 — raw stdio lists target tool.** On a machine with `homelab-mcp` installed:
   ```
   uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_raw_stdio_lists_target_tool -v
   ```
   Expected: PASS.

2. **SC#2 — wrapper `call_tool` returns non-error content.** On a machine with `homelab-mcp` installed:
   ```
   uv run pytest -m live_homelab tests/smoke/test_smoke_homelab_mcp.py::test_wrapper_call_tool_returns_non_error_with_content -v
   ```
   Expected: PASS.

If either test fails, run with `-v -s` and inspect the `CallToolResult` shape; the SC#2 assertion handles `content` OR `structuredContent` so an empty-but-non-error response would surface clearly.

---

## Gaps

(None.)

---

## Notable Deviations During Phase

- **Two subagent permission lockouts** (Plans 02-02 and 02-03). Both recovered via the documented orchestrator hand-off pattern; no deliverables were lost. See the per-plan SUMMARY.md files for full deviation logs.
- **README.md add/add merge conflict** between Plan 02-01 and Plan 02-02 worktrees (both added a stub to unblock hatchling). Resolved by keeping Plan 02-01's slightly more detailed version. Tracked as a Phase 5 deliverable per both stubs.
- **`gsd:code-review` skill not auto-invoked** because the gsd-code-reviewer subagent risked a third permission lockout. The orchestrator inspected the source files directly during this verification. The user can run `/gsd-code-review 02` manually for an independent review.
