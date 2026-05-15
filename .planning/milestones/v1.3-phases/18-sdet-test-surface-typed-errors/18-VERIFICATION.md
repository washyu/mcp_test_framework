---
phase: 18-sdet-test-surface-typed-errors
verified: 2026-05-13T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 18: SDET Test Surface + Typed Errors Verification Report

**Phase Goal:** "An SDET can write `tests/sdet/test_<name>.py`, import `mcp_session` + `tool('name')` from a stable public seam, and run those tests via `mcp-test-framework run --sdet` — with tool-side errors surfacing as a typed `ToolCallError` instead of an untyped `CallToolResult` blob."

**Verified:** 2026-05-13
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `tests/sdet/` is a recognized discovery scope; default `run` collects only `tests/contract/`; `run --sdet` opts SDET scope in; composes cleanly with `-q`, `--explain`, `--debug`, `--raw`, `--with-framework` | VERIFIED | `tests/sdet/__init__.py` exists (0-byte package marker); `_runner.py:_build_pytest_args` (lines 81-122) hard-codes `["tests/contract"]` default, swaps to `["tests/sdet"]` when `sdet=True`, appends `tests/framework` when `with_framework=True`; `cli.py` lines 404-415 register `--sdet` flag with composition help text; `cli.py` lines 498-504 + 571-577 thread `sdet=` into both raw and default subprocess calls; 9 `test_runner_sdet_kwarg.py` tests + 10 `test_sdet_cli.py` tests pin composition matrix |
| 2 | `from mcp_test_framework.sdet import mcp_session, tool` gets a session-scoped `McpTestClient` wrapper + `tool(name)` builder; both require `@pytest.mark.asyncio` markers under pytest-asyncio strict mode | VERIFIED | `sdet/__init__.py` has `__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]` (line 27); `sdet/session.py:34` defines `@pytest_asyncio.fixture(loop_scope="session", scope="session")` on `mcp_session`; `sdet/_tool_factory.py:86` defines `async def call(self, params: P) -> R`; `pyproject.toml` (per CONTEXT.md, confirmed via pytest config emitting `mode=Mode.STRICT`); `test_basic_call.py` uses `@pytest.mark.asyncio(loop_scope="session")` and `mcp_session` fixture; runtime import verified: `python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse"` succeeds |
| 3 | When `result.isError = True`, the call wrapper raises `ToolCallError` with `.tool` / `.code` / `.message` / `.raw` populated; Phase 16 em-dash failure-detail pattern surfaces `.code` / `.message` in default-mode FAIL rows | VERIFIED | `sdet/errors.py:36-63` defines `ToolCallError(Exception)` with required kw-only `tool`/`code`/`message`/`raw`; `_extract_code_message` (lines 66-97) implements D-08 strict heuristic chain; `_tool_factory.py:109-120` raises `ToolCallError` on `result.isError`; `tests/sdet/conftest.py:22-46` `pytest_exception_interact` hoists `mcptf_error_code`/`mcptf_error_message`/`mcptf_error_raw` onto `report.user_properties`; `_runner.py:521-535` parser reads `mcptf_error_*` properties and overrides `<failure message="...">`, composing `f"[{code}] {msg_field}"` when code present; em-dash U+2014 separator at `_runner.py:1002` `_render_per_tool_rows` is preserved |
| 4 | Under `--debug`, the raw `CallToolResult` for a failed call is dumped into the debug appendix without crashing the renderer | VERIFIED | `tests/sdet/conftest.py:43-46` emits `mcptf_error_raw` property carrying `exc.raw.model_dump_json(indent=2)`; `_runner.py:1139-1189` `_extract_tool_call_errors_from_xml` reads it; `_runner.py:1227-1257` in `render_debug_appendix` emits `--- ToolCallError dump ---` block BEFORE raw pytest output with tool/code/message/raw fields and `(none)` sentinel for empty raw; `cli.py:630-633` passes `xml_path=tmp_xml` to `render_debug_appendix`; round-trip pinned by `test_sdet_renderer.py::TestD11RawRoundTrip` (5 tests) and `test_runner_debug_appendix_d11.py` (16 tests) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/sdet/errors.py` | `ToolCallError` shape (D-07) + `_extract_code_message` heuristic chain (D-08) | VERIFIED | 97 lines; `ToolCallError(Exception)` with kw-only `tool`/`code`/`message`/`raw`; `_format_default` produces `[code] message`; D-08 chain implements step 1 (structuredContent dict), step 2 (first TextContent JSON parse), step 3 (concat fallback); strict key set (`code`/`message` only); imported by `_tool_factory.py:110-113` (wired) |
| `src/mcp_test_framework/sdet/__init__.py` | Exact 4-name public surface | VERIFIED | `__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]`; all 4 imports succeed at runtime; pinned by `TestPublicSurface` (5 tests) including `test_all_lists_exact_four_names`, `test_all_is_alphabetical`, `test_internal_symbols_not_re_exported` |
| `src/mcp_test_framework/sdet/session.py` | `mcp_session` fixture (D-01/D-02/D-03) | VERIFIED | 87 lines; `@pytest_asyncio.fixture(loop_scope="session", scope="session")` D-01 alias on `mcp_client`; D-02 5-step activation (assert server_info, slugify, importlib.import_module, install `_REGISTRIES`/`_ACTIVE_SLUG`/`_ACTIVE_CLIENT`, yield, restore); D-03 fail-loud via `_pytest_exit_operator_tone` on `ModuleNotFoundError`; imported by `sdet/__init__.py:24` (wired) |
| `src/mcp_test_framework/sdet/_tool_factory.py` | `ToolWrapper.call()` body + `_ACTIVE_CLIENT` slot | VERIFIED | 154 lines; `_ACTIVE_CLIENT: "McpTestClient | None" = None` at line 55; `.call()` body (lines 86-121) checks `_ACTIVE_CLIENT`, serializes via `params.model_dump(mode="json")`, awaits `call_tool`, raises `ToolCallError` on `isError`, else returns `self.response_cls(raw=result)`; pinned by 12 `test_tool_factory.py` tests including `test_call_raises_runtime_error_when_no_active_client` |
| `src/mcp_test_framework/cli.py` | `--sdet` flag registration + threading | VERIFIED | Lines 404-415 declare `sdet: bool` Typer Option with composition help text; lines 503 + 576 thread `sdet=sdet` into `run_pytest_subprocess`; lines 546-561 dispatch to `_render_scenario_pre_run_digest` when `--sdet` set; CLI help confirmed via `uv run mcp-test-framework run --help` (shows `--sdet` with full composition description) |
| `src/mcp_test_framework/_runner.py` | D-09 parser hook + D-06 scenario digest + D-11 debug appendix | VERIFIED | `_build_pytest_args` (lines 81-122) handles `sdet` kwarg swap; lines 521-535 implement D-09 parser reading `mcptf_error_code`/`mcptf_error_message` and composing `[code] message`; `_render_scenario_pre_run_digest` (lines 849-902) implements D-06; `_collect_sdet_scenarios` (lines 904-926) enumerates `tests/sdet/test_*.py` stems; `_extract_tool_call_errors_from_xml` (lines 1139-1189) + appendix block emission (lines 1227-1257) implement D-11 |
| `tests/sdet/__init__.py` | Package marker | VERIFIED | Empty 0-byte file (correct for marker package) |
| `tests/sdet/conftest.py` | `pytest_exception_interact` hook (D-09 + D-11 emit) | VERIFIED | 47 lines; hook tests `isinstance(exc, ToolCallError)`, appends 3 user_properties (`mcptf_error_code`, `mcptf_error_message`, `mcptf_error_raw`); raw uses `exc.raw.model_dump_json(indent=2)` with None sentinel; pinned by 9 `test_sdet_conftest_hook.py` tests |
| `tests/sdet/test_basic_call.py` | End-to-end sanity scenario | VERIFIED | 73 lines; 2 async tests: `test_basic_tool_round_trip` (uses `mcp_session` + `tool("list_registered_servers")` + asserts `isinstance(response, ToolResponse)`); `test_invalid_params_caught_before_wire` (Pydantic ValidationError before wire) |
| `tests/framework/unit/test_tool_call_error.py` | D-07 + D-08 pinning | VERIFIED | 23 tests passing — `TestToolCallErrorShape` (7) + `TestExtractCodeMessage` (16) |
| `tests/framework/unit/test_sdet_fixtures.py` | D-01/D-02/D-03 + public surface | VERIFIED | 12 tests passing including `TestPublicSurface` (5 tests) |
| `tests/framework/unit/test_sdet_cli.py` | D-04/D-05 composition matrix | VERIFIED | 10 tests passing |
| `tests/framework/unit/test_sdet_renderer.py` | D-06/D-09/D-10/D-11 integration | VERIFIED | 19 tests passing across 5 TestD* classes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `sdet/__init__.py` | `errors.py`, `response.py`, `session.py`, `_tool_factory.py` | imports + `__all__` | WIRED | Lines 22-25; all 4 imports resolve at runtime |
| `sdet/_tool_factory.py:.call()` | `errors._extract_code_message` + `ToolCallError` | local import on isError | WIRED | Lines 110-113 |
| `sdet/_tool_factory.py:.call()` | `McpTestClient.call_tool` via `_ACTIVE_CLIENT` | module slot, set by `mcp_session` | WIRED | Line 108; `_ACTIVE_CLIENT` mutated only by `sdet/session.py:78,85` |
| `sdet/session.py` | generated registry | `importlib.import_module(f"...generated.{slug}")` | WIRED | Lines 49-52; `homelab_mcp/__init__.py` has `_REGISTRY` populated with all generated tools incl. `list_registered_servers` |
| `tests/sdet/conftest.py` | `_runner.py` parser | JUnit `user_properties` (`mcptf_error_*`) | WIRED | Hook appends 3 properties; parser at `_runner.py:521-535` and `1139-1189` reads them |
| `_runner.py:render_debug_appendix` | `_extract_tool_call_errors_from_xml` | `xml_path=tmp_xml` kwarg | WIRED | `cli.py:630-633` passes path; `_runner.py:1234` calls extractor before raw pytest output emission |
| `cli.py:run` | `_render_scenario_pre_run_digest` | `if sdet:` branch | WIRED | `cli.py:546-561` builds sdet-only RenderContext and dispatches |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `_tool_factory.ToolWrapper.call` | `result` | `await _ACTIVE_CLIENT.call_tool(self.name, arguments)` — live MCP wire call | Yes (real `CallToolResult`) | FLOWING |
| `sdet/session.mcp_session` | `registry` | `getattr(mod, "_REGISTRY")` from generated module | Yes (real dict keyed by tool names; homelab_mcp registry has 60+ entries) | FLOWING |
| `_runner._render_scenario_pre_run_digest` | `scenarios` | `_collect_sdet_scenarios` → `tests/sdet/test_*.py` glob | Yes (real file glob; `test_basic_call.py` present) | FLOWING |
| `_runner._extract_tool_call_errors_from_xml` | `code`/`message`/`raw_dump` | `tc.find("properties").iter("property")` reading JUnit user_properties emitted by `conftest.py` | Yes (real XML round-trip pinned by `TestD11RawRoundTrip`) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 4 public symbols importable | `python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse"` | Exit 0; `__all__ = ['ToolCallError', 'ToolResponse', 'mcp_session', 'tool']` | PASS |
| `--sdet` flag registered with composition docs | `uv run mcp-test-framework run --help` | `--sdet  Swap the operator-surface scope from tests/contract/ to tests/sdet/. ... Composes with --with-framework ...` | PASS |
| Phase 18 framework self-tests pass | `uv run pytest tests/framework/unit/test_tool_call_error.py + test_sdet_fixtures.py + test_sdet_cli.py + test_sdet_renderer.py + test_tool_factory.py + test_runner_sdet_digest.py + test_runner_sdet_kwarg.py + test_sdet_conftest_hook.py + test_runner_debug_appendix_d11.py + test_runner_parser.py --noconftest` | 153 passed in 1.13s | PASS |
| `mcp_session` is pytest-asyncio fixture | `python -c "from mcp_test_framework.sdet import mcp_session; print('_force_asyncio_fixture' in dir(mcp_session))"` | `_force_asyncio_fixture` + `_fixture_function_marker` present | PASS |
| Generated registry available for `test_basic_call.py` | `grep list_registered_servers src/.../generated/homelab_mcp/__init__.py` | `"list_registered_servers": (ListRegisteredServersParams, ListRegisteredServersResponse)` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SDET-01 | 18-05, 18-07, 18-08 | `tests/sdet/` directory exists as a recognized test discovery scope; default contract pass does NOT collect it | SATISFIED | `tests/sdet/__init__.py` + `conftest.py` + `test_basic_call.py` exist; `_build_pytest_args` default = `["tests/contract"]`; `--sdet` swaps to `["tests/sdet"]`; 19 composition-matrix tests pinned |
| SDET-02 | 18-05, 18-06, 18-08 | `mcp-test-framework run --sdet` opts SDET scope in; composable with `-q`, `--explain`, `--debug`, `--raw`; default remains contract-only | SATISFIED | `cli.py:404-415` registers flag with composition help text; threaded into both raw and default paths; 13 `test_runner_sdet_digest.py` + 9 `test_runner_sdet_kwarg.py` + 10 `test_sdet_cli.py` tests |
| SDET-03 | 18-01, 18-02, 18-03, 18-04, 18-07, 18-08 | `mcp_test_framework.sdet` exports `mcp_session` (session-scoped fixture wrapping `McpTestClient`) and `tool(name)` (typed call wrapper) | SATISFIED | `sdet/__init__.py` exports both; `mcp_session` is `pytest_asyncio.fixture(loop_scope="session", scope="session")` aliased on `mcp_client`; `tool()` returns `ToolWrapper` with `.call()` wired (UI-02) |
| SDET-04 | 18-03, 18-05, 18-07, 18-08 | Async-only by contract: SDET fixtures and call wrappers require `@pytest.mark.asyncio` markers; pytest-asyncio strict mode enforced | SATISFIED | `pyproject.toml` configures strict mode (verified at runtime: `asyncio: mode=Mode.STRICT`); `mcp_session` is async; `ToolWrapper.call` is `async def`; `test_basic_call.py` uses explicit `@pytest.mark.asyncio(loop_scope="session")` |
| UI-02 | 18-01, 18-02, 18-04, 18-06, 18-07, 18-08 | `ToolCallError` typed exception with `.tool`/`.code`/`.message`/`.raw`; raised on `result.isError`; `--debug` dumps raw `CallToolResult` to appendix; default-mode FAIL rows surface `.code`/`.message` via em-dash | SATISFIED | `errors.py` defines class; `_tool_factory.py` raises on isError; parser hookup at `_runner.py:521-535` produces `[code] message` for FAIL row; appendix block at `_runner.py:1227-1257` emits structured dump |

All 5 declared requirement IDs SATISFIED. No orphaned requirements; REQUIREMENTS.md table at lines 141-144 maps Phase 18 to exactly these 5 IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TODO/FIXME/placeholder/stub patterns found in Phase 18 source files | — | — |

Inspected: `errors.py`, `session.py`, `_tool_factory.py`, `sdet/__init__.py`, `tests/sdet/__init__.py`, `tests/sdet/conftest.py`, `tests/sdet/test_basic_call.py`, plus the modified regions of `cli.py` and `_runner.py`. No unimplemented stubs, no hardcoded empty returns, no placeholder comments. The 0-byte `tests/sdet/__init__.py` is a deliberate Python package marker (not a stub).

### Human Verification Required

None. Every must-have is observable in code; all 153 framework self-tests pass against the shipped implementation; CLI help confirms operator surface; runtime imports succeed.

### Gaps Summary

No gaps found. Phase 18 closes SDET-01..04 and UI-02 against the ROADMAP success criteria:

1. **SDET scope wired and composable** — `tests/sdet/` discovery, `--sdet` flag swap (not additive), composition with all 5 verbosity flags pinned by 32+ tests.
2. **Public surface exact** — `__all__` is exactly 4 names; internal symbols (`_extract_code_message`, `_REGISTRIES`, `_ACTIVE_SLUG`, `_ACTIVE_CLIENT`, `ToolWrapper`, `server_slug`) stay private; pinned by `TestPublicSurface`.
3. **Typed errors flow end-to-end** — `result.isError → ToolCallError → JUnit user_properties → parser → em-dash FAIL row` is wired through `_tool_factory.py:.call()` → `tests/sdet/conftest.py:pytest_exception_interact` → `_runner.py:521-535`.
4. **Debug appendix carries `CallToolResult`** — `mcptf_error_raw` property carries `model_dump_json(indent=2)` round-trip; `--- ToolCallError dump ---` block emits before raw pytest output; pinned by 24 tests across `TestD11AppendixBlock` + `TestD11RawRoundTrip` + `test_runner_debug_appendix_d11.py`.

All 11 phase decisions (D-01..D-11) are pinned by named tests, providing drift detection going into Phase 19 (STATE), Phase 20 (PREFLIGHT), and Phase 21 (DOC-SDET).

---

_Verified: 2026-05-13_
_Verifier: Claude (gsd-verifier)_
