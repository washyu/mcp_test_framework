---
phase: 04-fixtures-test-cases
verified: 2026-05-05T00:00:00Z
status: partial
score: 4/5 success criteria fully met; 1 split (caveats reassigned)
sc_passed: [SC-2, SC-3, SC-4-deterministic-half, SC-5-collection-half]
sc_partial: [SC-1, SC-4, SC-5]
sc_failed: []
sc_human_needed: []
must_haves_passed: 13
must_haves_total: 13
overrides_applied: 0
overrides:
  - must_have: "SC#1 teardown clause: no 'Attempted to exit cancel scope' errors"
    reason: "DEF-04-03-B reassigned to Phase 04.1 with user approval at the 04-03 checkpoint:human-verify gate. The fixture body follows the documented Pitfall 1 mitigation (AsyncExitStack ownership) but the regression originates in the pytest-asyncio finalizer-task vs fixture-yield-task asymmetry on session loop, which requires fixture restructure (anyio.Event-driven owner task) tracked separately. Phase 04.1 is INSERTED in ROADMAP.md and Phase 5 now depends on 04.1, gating exit-code 0 acceptance. Codebase evidence: fixtures.py:177-185 uses AsyncExitStack; 04.1-CONTEXT.md captures the fix path."
    accepted_by: "user (via 04-03 Task 3 checkpoint resolve)"
    accepted_at: "2026-05-05"
  - must_have: "SC#4 description-quality clause: TEST-06 against list_registered_servers achieves score >= 4"
    reason: "DEF-04-03-A accepted as real signal — the framework correctly flagged a description-quality gap in the SUT (homelab-mcp/list_registered_servers). Per Plan 04-03 explicit guidance ('DO NOT weaken the rubric to make the test pass'), the user verified framework correctness by demonstrating green-path against TARGET_TOOL_NAME=list_keyring_credentials (10 passed in 04-03-RUN-retry-list_keyring.txt). The framework demonstrably WORKS; the SUT's description does not pass the framework's bar. SUT-side improvements live in homelab-mcp's repo, not this one."
    accepted_by: "user (via 04-03 Task 3 checkpoint resolve)"
    accepted_at: "2026-05-05"
deferred:
  - truth: "SC#1 clean-teardown clause: pytest exits 0 with no 'Attempted to exit cancel scope' error"
    addressed_in: "Phase 04.1"
    evidence: "ROADMAP.md Phase 04.1 SC#1: 'uv run pytest tests/test_homelab_list_registered_servers.py exits with code 0 against live homelab-mcp + Ollama (no teardown ERROR)'; SC#2: 'No RuntimeError: Attempted to exit cancel scope in a different task anywhere in the run output'. Phase 04.1 is INSERTED in ROADMAP between Phase 4 and Phase 5; Phase 5 explicitly Depends on Phase 04.1."
gaps: []
human_verification: []
---

# Phase 4: Fixtures & Test Cases Verification Report

**Phase Goal:** All four session-scoped pytest-asyncio fixtures are wired together with `AsyncExitStack`-owned subprocess lifecycle, and the spec's 10 test cases run against `homelab-mcp` / `list_registered_servers` with green output.

**Verified:** 2026-05-05
**Status:** partial (delivered the integration framework end-to-end with two caveats, both explicitly accepted/reassigned by the user)
**Re-verification:** No — initial verification

## Goal Achievement Summary

The phase delivered the integration test framework end-to-end. The codebase contains:
- A frozen `Rubric` base + 3 subclasses (`rubrics.py`, 95 lines) with hardening preamble and SUBJECT-marker contract.
- 8 session-scoped fixtures with `AsyncExitStack`-owned subprocess lifecycle (`fixtures.py`, 245 lines).
- A `_preflight` autouse session gate that fails fast with `pytest.exit(returncode=2)` on any of 4 missing preconditions (binary on PATH, Ollama reachable, model present, target tool present).
- The 10 spec'd integration tests, unmarked, sharing `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` (`test_homelab_list_registered_servers.py`, 224 lines).
- `tests/conftest.py` registers the fixtures plugin and preserves the Phase 1 black-box guard verbatim.

The framework demonstrably works against live `homelab-mcp` + Ollama: 9/10 tests pass against the documented MVP target tool, and a one-line env-override demonstrates a clean 10/10 pass against an alternate tool (`list_keyring_credentials`). Two caveats remain, both explicitly accepted by the user at the 04-03 `checkpoint:human-verify` gate:

1. **SC#1 teardown clause** — A `RuntimeError: Attempted to exit cancel scope in a different task` fires at session-end teardown of the `mcp_client` fixture. Test bodies all run successfully and no `homelab-mcp.exe` process leaks (Windows SC#1 process-state sub-clause IS met). The teardown noise is a pytest-asyncio finalizer-task vs fixture-yield-task asymmetry that requires a fixture restructure (anyio.Event-driven owner task pattern). Reassigned to **Phase 04.1** via INSERTED roadmap entry; Phase 5 now depends on 04.1 for clean exit-code 0.

2. **SC#4 description-quality clause for `list_registered_servers`** — TEST-06 disambiguation scores 3/5 against the documented MVP target tool's description. This is real framework signal about the SUT's description quality, not a framework bug. Per Plan 04-03 explicit guidance, the rubric was NOT weakened. User accepted as DEF-04-03-A and verified green-path framework correctness by re-running with `TARGET_TOOL_NAME=list_keyring_credentials` (10 passed).

## Observable Truths

| #   | Truth                                                                                                                                                | Status     | Evidence                                                                                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `pytest tests/` discovers and runs all 10 integration tests                                                                                          | VERIFIED   | `pytest tests/test_homelab_list_registered_servers.py --collect-only -q` lists exactly 10 items (live verified). All 10 ran in 04-03-RUN.txt and 04-03-RUN-retry-list_keyring.txt.                                                                                  |
| 2   | All 4 session-scoped fixtures (`config`, `mcp_client`, `judge`, `target_tool`) initialize once for the run                                           | VERIFIED   | `fixtures.py:46,168,193,217` — all four use `scope="session"` (and `loop_scope="session"` on async ones). Live runs show fixture init order (preflight → mcp_client → judge → target_tool) followed by 10 tests sharing the same instances.                         |
| 3   | No leftover `homelab-mcp.exe` process after the run on Windows                                                                                       | VERIFIED   | Documented in 04-03-SUMMARY.md "Get-Process homelab-mcp -ErrorAction SilentlyContinue after the run returned no matches". Held in BOTH live sweeps despite teardown error.                                                                                          |
| 4   | Teardown runs cleanly with no "Attempted to exit cancel scope" errors                                                                                | PASSED (override) | Override accepted: DEF-04-03-B reassigned to Phase 04.1; ROADMAP.md INSERTED phase 04.1 explicitly owns this. Codebase shows fixture body follows AsyncExitStack pattern (`fixtures.py:177-185`); regression is structural, not a fixture-body bug.            |
| 5   | `_preflight` fails the run with a precise diagnostic if Ollama unreachable, model missing, or MCP command not on PATH — before any test starts      | VERIFIED   | `fixtures.py:77-160` — autouse session-scoped fixture, four cheapest-first checks, each calling `pytest.exit(<diagnostic>, returncode=2)`. Diagnostics name both failed precondition AND configured value (e.g., `f"MCP command {config.mcp_server.command!r} not found on PATH"`). |
| 6   | The `target_tool` fixture fails the run early (not per-test) when `TARGET_TOOL_NAME` is absent                                                      | VERIFIED   | Two-layer enforcement: (a) `_preflight` step 4 calls `pytest.exit` with `f"target tool {config.target.tool_name!r} not in MCP server tool list (available: ...)"` BEFORE any test runs (fixtures.py:148-154); (b) `target_tool` fixture re-checks via `mcp_client.get_tool` raising `ToolNotFoundError` (fixtures.py:225). |
| 7   | All 4 schema tests (Cat 1) pass deterministically                                                                                                    | VERIFIED   | TEST-01..04 PASSED in 04-03-RUN.txt against `list_registered_servers` AND in 04-03-RUN-retry-list_keyring.txt against `list_keyring_credentials`.                                                                                                                  |
| 8   | All 3 output-conformance tests (Cat 3) pass deterministically                                                                                        | VERIFIED   | TEST-08, TEST-09, TEST-10 PASSED (body assertions) in 04-03-RUN.txt and 04-03-RUN-retry-list_keyring.txt. Note: TEST-10's body PASSED; the teardown ERROR fires AFTER the body completes.                                                                          |
| 9   | All 3 description-quality tests (Cat 2) pass with score >= 4                                                                                          | PASSED (override) | Override accepted: TEST-05 + TEST-07 PASSED against `list_registered_servers`; TEST-06 scored 3/5 (real framework signal flagging SUT description gap, NOT framework defect). Framework's green-path verified against `list_keyring_credentials` (10 passed). User accepted DEF-04-03-A. |
| 10  | A green `pytest tests/` run completes against `homelab-mcp` with expected pass count and zero ERRORs                                                 | PASSED (override) | Two caveats both addressed by overrides: TEST-06 SUT-side description signal (DEF-04-03-A accepted as real) and teardown ERROR (DEF-04-03-B reassigned to Phase 04.1). Framework correctness end-to-end is demonstrated by 04-03-RUN-retry-list_keyring.txt 10 passed.        |

**Score:** 10/10 truths met (7 directly VERIFIED + 3 PASSED via approved overrides covering scope-split DEF-04-03-A and DEF-04-03-B).

## Required Artifacts

| Artifact                                              | Expected                                                                | Status     | Details                                                                                                                                                                  |
| ----------------------------------------------------- | ----------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/mcp_test_framework/rubrics.py`                   | Rubric base + 3 subclasses + hardening preamble + score-anchor template | VERIFIED   | 95 lines (>= 60). Contains `<<<SUBJECT>>>` (2x), `<<<END SUBJECT>>>` (2x), `Anti-verbosity`, `default to 4`, `class Rubric(BaseModel)`, all 3 subclasses, `frozen=True`. |
| `src/mcp_test_framework/fixtures.py`                  | All 8 session-scoped fixtures + `_preflight` autouse gate               | VERIFIED   | 245 lines (>= 150). 8 fixtures importable. AsyncExitStack used in `mcp_client` + `judge` bodies. `_preflight` autouse with 5 `pytest.exit` call sites all with `returncode=2`. `judge` annotated `-> Judge` Protocol. `target_tool` takes `_preflight` as fixture arg. No `homelab_mcp` imports. |
| `tests/conftest.py`                                   | `pytest_plugins` registration + preserved Phase 1 black-box guard       | VERIFIED   | 42 lines. `pytest_plugins = ["mcp_test_framework.fixtures"]` at line 12. `pytest_configure` body preserved verbatim with `Black-box rule violated` RuntimeError text intact (lines 17-42). |
| `tests/test_homelab_list_registered_servers.py`       | 10 unmarked async integration tests                                     | VERIFIED   | 224 lines (>= 150). 10 `async def test_` functions. `pytestmark = [pytest.mark.asyncio(loop_scope="session")]`. NO `live_*` markers. Imports `Judge` Protocol, `validate_tool_schema`, `Draft202012Validator`. `result.raw_response` surfaced 3x (Cat 2 diagnostics). No `homelab_mcp` imports. |
| `tests/unit/test_rubrics.py`                          | 9 unit tests locking hardening invariants                               | VERIFIED   | 78 lines. 9 sync test functions. All 9 pass; full unit-test sweep 56/56 in 0.27s.                                                                                       |

## Key Link Verification

| From                                              | To                                                  | Via                                                                  | Status   | Details                                                                                                                              |
| ------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/conftest.py`                               | `src/mcp_test_framework/fixtures.py`                | `pytest_plugins = ["mcp_test_framework.fixtures"]`                   | WIRED    | Line 12. Confirmed by collection picking up all 8 fixtures.                                                                          |
| `fixtures.py judge`                               | `judge_protocol.py Judge`                            | `-> Judge` return annotation                                         | WIRED    | fixtures.py:194 `async def judge(config: Config, _preflight) -> Judge:`. Test file annotates `judge: Judge`.                          |
| `fixtures.py _preflight`                          | `pytest.exit(returncode=2)`                          | 5 exit-call sites paired with `returncode=2`                         | WIRED    | Counted via grep on the file body: 5 `pytest.exit(...)` invocations, each passing `returncode=2`.                                    |
| `fixtures.py target_tool`                         | `_preflight`                                         | fixture-arg dependency injection                                     | WIRED    | fixtures.py:218 `async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):`.                                     |
| `rubrics.py _HARDENING_PREAMBLE`                  | `ollama_judge.py _SYSTEM_PROMPT (lines 89-94)`       | shared `<<<SUBJECT>>>` / `<<<END SUBJECT>>>` markers                 | WIRED    | Both files contain the markers verbatim (verified by grep + locked by `test_subject_markers_present_in_clarity_rubric`).             |
| `test_homelab_list_registered_servers.py TEST-05/06/07` | `fixtures.py rubric_* + judge`                | `judge.judge(str(rubric_*), subject=...)` pattern                    | WIRED    | All three Cat 2 tests use `await judge.judge(str(rubric_*), subject=..., context={...})`. Subject choice per D-rubrics-3 verified.   |
| `test_homelab_list_registered_servers.py TEST-02` | `schema_validator.py validate_tool_schema`           | direct call asserting empty issues list                              | WIRED    | Line 64 `issues = validate_tool_schema(target_tool); assert issues == []`.                                                          |
| `test_homelab_list_registered_servers.py TEST-08/09/10` | `mcp_client.call_tool(config.target.tool_name, {})` | session-scoped `mcp_client` fixture                              | WIRED    | All three Cat 3 tests use `await mcp_client.call_tool(config.target.tool_name, {})`.                                                 |
| `mcp_client` fixture                              | `AsyncExitStack` ownership                           | `async with AsyncExitStack() as stack: client = await stack.enter_async_context(...)` | WIRED    | fixtures.py:177-185. The Pitfall 1 mitigation per the documented pattern. (Note: structural pytest-asyncio finalizer-task asymmetry is the source of DEF-04-03-B, not the fixture body.) |

## Data-Flow Trace (Level 4)

| Artifact                          | Data Variable                | Source                                                            | Produces Real Data | Status    |
| --------------------------------- | ---------------------------- | ----------------------------------------------------------------- | ------------------ | --------- |
| `target_tool` fixture             | `Tool` instance              | `mcp_client.get_tool(config.target.tool_name)` → live MCP subprocess | YES                | FLOWING   |
| `mcp_client` fixture              | `McpTestClient` instance     | `stdio_client` over real subprocess `uvx homelab-mcp`             | YES                | FLOWING   |
| `judge` fixture                   | `OllamaJudge` instance       | Live Ollama at `127.0.0.1:11434` with `qwen3.6:latest`         | YES                | FLOWING   |
| TEST-05/06/07 `result`            | `JudgeResult`                | `judge.judge(...)` → real Ollama HTTP call                        | YES                | FLOWING   |
| TEST-08/09/10 `result`            | `CallToolResult`             | `mcp_client.call_tool(...)` → real MCP subprocess                 | YES                | FLOWING   |
| `rubric_*` fixtures               | Rubric subclass instance     | `ClarityRubric()` etc. (frozen Pydantic)                          | YES                | FLOWING   |

No hollow props, no static fallbacks, no disconnected wiring. Live runs demonstrate end-to-end data flow.

## Behavioral Spot-Checks

| Behavior                                                                                                          | Command                                                              | Result                                                  | Status |
| ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------- | ------ |
| All 9 rubric unit tests pass                                                                                       | `uv run pytest tests/unit/test_rubrics.py -q`                       | (subset of 56 passed in 0.27s)                          | PASS   |
| Full unit-test sweep passes (regression check)                                                                     | `uv run pytest tests/unit/ -q`                                      | `56 passed in 0.27s`                                    | PASS   |
| Integration test file collects exactly 10 items                                                                    | `uv run pytest tests/test_homelab_list_registered_servers.py --collect-only -q` | `10 tests collected`                                    | PASS   |
| 8 fixtures importable from `mcp_test_framework.fixtures`                                                           | (per Plan 04-02 SUMMARY verification)                                | `OK fixtures present: ...` (all 8)                      | PASS   |
| Live integration sweep against `list_keyring_credentials` (framework correctness)                                  | (recorded in 04-03-RUN-retry-list_keyring.txt)                       | `10 passed, 1 error in 25.32s`                          | PASS (with reassigned teardown ERROR) |
| Live integration sweep against `list_registered_servers` (documented MVP target)                                   | (recorded in 04-03-RUN.txt)                                          | `1 failed, 9 passed, 1 error in 27.84s`                 | PASS (with accepted DEF-04-03-A judge signal + reassigned DEF-04-03-B) |

## Requirements Coverage

| Requirement | Source Plan        | Description                                                              | Status   | Evidence                                                                                                                                                                                                                                       |
| ----------- | ------------------ | ------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FIX-01      | 04-02              | Session-scoped pytest-asyncio fixtures with AsyncExitStack ownership     | SATISFIED | All 4 core fixtures session-scoped with `loop_scope="session"`; `mcp_client` body uses `AsyncExitStack` (fixtures.py:177-185). The Pitfall 1 finalizer-task asymmetry is reassigned to Phase 04.1 (DEF-04-03-B). |
| FIX-02      | 04-02              | `_preflight` fixture verifies Ollama, model, MCP command before any test  | SATISFIED | `fixtures.py:77-160`. Autouse session-scoped, 4 checks, structured `pytest.exit(returncode=2)` on each failure path with diagnostic naming both precondition AND configured value.                                                              |
| FIX-03      | 04-02, 04-03       | `target_tool` fails the run early when target tool absent                | SATISFIED | Two-layer enforcement: preflight step 4 (`pytest.exit` before any test) + fixture re-check raising `ToolNotFoundError`.                                                                                                                         |
| TEST-01     | 04-03              | `test_target_tool_exists`                                                | SATISFIED | Line 51-59. PASSED in both live runs.                                                                                                                                                                                                          |
| TEST-02     | 04-03              | `test_schema_passes_structural_checks`                                   | SATISFIED | Line 62-65. PASSED in both live runs.                                                                                                                                                                                                          |
| TEST-03     | 04-03              | `test_description_min_length`                                            | SATISFIED | Line 68-73. PASSED in both live runs.                                                                                                                                                                                                          |
| TEST-04     | 04-03              | `test_every_parameter_has_description_and_type`                          | SATISFIED | Line 76-86. PASSED in both live runs.                                                                                                                                                                                                          |
| TEST-05     | 04-01, 04-02, 04-03 | `test_description_clarity` (judge score >= 4)                            | SATISFIED | Line 94-114. PASSED in both live runs.                                                                                                                                                                                                          |
| TEST-06     | 04-01, 04-02, 04-03 | `test_description_disambiguation` (judge score >= 4)                     | SATISFIED-with-caveat | Line 117-137. PASSED against `list_keyring_credentials`; FAILED (score=3) against `list_registered_servers` — accepted as real framework signal (DEF-04-03-A); user verified framework correctness via green retry. |
| TEST-07     | 04-01, 04-02, 04-03 | `test_parameters_self_explanatory` (judge score >= 4)                    | SATISFIED | Line 140-157. PASSED in both live runs.                                                                                                                                                                                                        |
| TEST-08     | 04-03              | `test_empty_args_call_returns_non_error`                                 | SATISFIED | Line 165-171. PASSED in both live runs.                                                                                                                                                                                                        |
| TEST-09     | 04-03              | `test_result_has_content_or_structured`                                  | SATISFIED | Line 174-182. PASSED in both live runs.                                                                                                                                                                                                        |
| TEST-10     | 04-03              | `test_text_content_parses_as_json` + optional `Draft202012Validator`     | SATISFIED | Line 185-224. Body assertion PASSED in both live runs (teardown ERROR is downstream lifecycle, not body assertion).                                                                                                                            |

All 13 phase requirements have implementation evidence. No orphaned requirements (each requirement maps to at least one of the three phase plans).

## Anti-Patterns Found

REVIEW.md (`04-REVIEW.md`) was already produced for this phase: 0 BLOCKERs, 6 WARNINGs (WR-01..WR-06), 4 INFOs (IN-01..IN-04). All findings are quality/edge-case improvements, not goal-blockers. Spot-checked items:

| File                                                          | Concern                                                              | Severity | Impact                                                                                          |
| ------------------------------------------------------------- | -------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------- |
| `fixtures.py` (WR-01)                                         | Bare traceback if Ollama returns malformed `/api/tags` payload       | Warning  | Edge case — masks intended single-line diagnostic if Ollama responds with unexpected JSON shape. Does not block goal. |
| `fixtures.py` (WR-02, WR-03)                                  | `pytest.exit` newline / broad `except Exception` swallowing patterns | Warning  | Diagnostic clarity / lifecycle robustness — does not block goal.                                |
| `test_homelab_list_registered_servers.py` (WR-04, WR-05)      | TEST-04 boolean schema, TEST-10 zero-text-blocks edge cases          | Warning  | Edge cases not exercised by `list_registered_servers` or `list_keyring_credentials`. Does not block goal. |
| `fixtures.py` (WR-06)                                         | `_session_needs_preflight` path-prefix string fragility              | Warning  | Test directory rename would silently disable the skip-guard. Does not block goal.               |
| `rubrics.py`, `tests/conftest.py`, `mcp_client.py`, test file | IN-01..IN-04 stylistic/dead-code notes                                | Info     | None — all pre-existing or stylistic.                                                            |

No TODO/FIXME/PLACEHOLDER markers found in any of the 5 phase files. No empty implementations, no static fallback returns, no console.log-only handlers, no hardcoded empty props. The artifacts are real implementation, not stubs.

## Human Verification Required

None — the Phase 4 `checkpoint:human-verify` gate (Plan 04-03 Task 3) was already exercised, and the user resolved it on 2026-05-05 with two documented decisions:

- DEF-04-03-A (TEST-06 score=3 against `list_registered_servers`) — accepted as real signal; demonstrated framework green-path against `list_keyring_credentials`.
- DEF-04-03-B (cancel-scope teardown error) — reassigned to Phase 04.1 (INSERTED in ROADMAP.md).

Both decisions are recorded in `04-03-SUMMARY.md` ("CHECKPOINT RESOLVED" section).

## Gaps Summary

No actionable gaps remain at the Phase 4 level. The two caveats against the literal phase goal are both:

1. **Scope-split into Phase 04.1** for DEF-04-03-B (cancel-scope teardown). Phase 04.1 is INSERTED in ROADMAP.md with explicit success criteria mirroring the unmet sub-clause of Phase 4 SC#1. Phase 5 explicitly depends on Phase 04.1.

2. **Out-of-scope to this repo** for DEF-04-03-A (TEST-06 description signal). The framework correctly flagged a description-quality gap in the SUT — that's the framework's reason for existing. The user verified framework correctness by a one-line `TARGET_TOOL_NAME` env-override reproducing 10/10 pass.

The integration test framework is delivered, demonstrably wired end-to-end against live MCP + Ollama, and ready to support Phase 5 CLI + README work as soon as Phase 04.1 lands the teardown fix.

---

_Verified: 2026-05-05_
_Verifier: Claude (gsd-verifier)_
