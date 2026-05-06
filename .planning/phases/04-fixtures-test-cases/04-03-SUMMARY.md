---
phase: 04-fixtures-test-cases
plan: 03
subsystem: testing
tags: [pytest-asyncio, integration-tests, ollama-judge, mcp-stdio, pitfall-1, judge-signal]

# Dependency graph
requires:
  - plan: 04-01
    provides: "ClarityRubric / DisambiguationRubric / ParametersRubric subclasses with shared hardening preamble"
  - plan: 04-02
    provides: "8 session-scoped fixtures (config, mcp_client, judge, target_tool, _preflight, rubric_*); pytest_plugins registration"
  - phase: 02-mcp-client-wrapper
    provides: "McpTestClient.call_tool, get_tool, list_tools; ToolNotFoundError"
  - phase: 03-ollama-judge
    provides: "OllamaJudge / Judge Protocol; JudgeResult shape with raw_response"
  - phase: 01-foundation-pure-data-core
    provides: "validate_tool_schema; Config()"
provides:
  - "tests/test_homelab_list_registered_servers.py: 10 unmarked async integration tests (Cat 1: TEST-01..04; Cat 2: TEST-05..07; Cat 3: TEST-08..10)"
  - ".planning/phases/04-fixtures-test-cases/04-03-RUN.txt: verbatim live-sweep output (1 failed, 9 passed, 1 teardown error)"
affects:
  - "Phase 4 acceptance: green with two documented caveats. (1) TEST-06 disambiguation=3 against `list_registered_servers` is a real judge signal about the SUT's description quality (homelab-mcp's owner, not framework); the framework correctly flagged it. (2) Cancel-scope teardown regression is reassigned to Phase 04.1."
  - "Phase 04.1 (INSERTED) owns the Pitfall-1 fix for `mcp_client` fixture teardown -- exit-code 0 acceptance lives there, not here. RESOLVED 2026-05-06 by 04.1-01-PLAN.md (owner-task + anyio.Event fixture rewrite)."
  - "Phase 5 (CLI + README) now depends on Phase 04.1, not directly on Phase 4."

# Tech tracking
tech-stack:
  added: []  # No new dependencies; jsonschema, pytest-asyncio, pytest were already pinned.
  patterns:
    - "10 unmarked async integration tests sharing pytestmark = [pytest.mark.asyncio(loop_scope='session')]"
    - "Per-rubric subject choice (D-rubrics-3): description for TEST-05/06; json.dumps(inputSchema) for TEST-07"
    - "Black-box-safe TEST-10: json.loads + optional Draft202012Validator.validate (no key assertions)"
    - "Failure diagnostics in Cat 2 surface result.raw_response for downstream debugging"

key-files:
  created:
    - "tests/test_homelab_list_registered_servers.py"
    - ".planning/phases/04-fixtures-test-cases/04-03-RUN.txt"
  modified: []

key-decisions:
  - "Plan 04-03 explicitly forbids weakening rubric thresholds, modifying test bodies, or modifying fixture logic to coerce green. Both real failures (TEST-06 score=3, TEST-10 teardown cancel-scope error) are surfaced to the user via the Task 3 checkpoint:human-verify rather than auto-fixed."
  - "TEST-06 disambiguation score 3/5 is real judge signal: the qwen3.6:latest reasoning specifically faults the description for not distinguishing list_registered_servers from hypothetical alternatives like list_all_servers / list_active_servers. The 'active_only' parameter exists but the description doesn't leverage it for disambiguation. This is a legitimate observation about the homelab-mcp description quality, not a rubric bug."
  - "TEST-10 PASSED its body assertions (>=1 TextContent block parsed as JSON) but the session-scoped mcp_client fixture's AsyncExitStack teardown raised RuntimeError('Attempted to exit cancel scope in a different task than it was entered in') -- Pitfall 1 surfacing despite Phase 2's mitigations. This is a deviation from Plan 04-03 acceptance criterion 'output does NOT contain Attempted to exit cancel scope' (5 occurrences in 04-03-RUN.txt)."
  - "Despite the cancel-scope teardown error, Get-Process homelab-mcp -ErrorAction SilentlyContinue after the run returned no matches -- Windows SC#1 (no leftover homelab-mcp.exe) IS met. The teardown error is a logging/exception-cleanliness regression, not a process-leak regression."

requirements-completed: [TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08, TEST-09, TEST-09, TEST-10]
requirements-deferred: [DEF-04-03-A]  # TEST-06 against list_registered_servers: real signal, accepted; framework demonstrated green-path against list_keyring_credentials
requirements-reassigned: []
requirements-resolved-by-followup: [DEF-04-03-B]  # cancel-scope teardown -> resolved by Phase 04.1 (see .planning/phases/04.1-mcp-client-teardown-fix/04.1-01-PLAN.md and 04.1-01-SUMMARY.md)

# Metrics
duration: ~3 min
completed: 2026-05-06
---

# Phase 4 Plan 03: Integration Tests + Live Green Sweep Summary

**10 integration tests shipped against `homelab-mcp` / `list_registered_servers`; live sweep produced 9 passed / 1 failed / 1 teardown error rather than the planned 10 passed. Two real failure signals surfaced to the user (Task 3 checkpoint:human-verify).**

## Performance

- **Duration:** ~3 min (Task 1 + Task 2 + writeup; Task 3 paused for user)
- **Started:** 2026-05-06T00:10:32Z
- **Completed (executor exit):** 2026-05-06T00:13:43Z
- **Tasks:** 2 of 3 executed (Task 3 = checkpoint:human-verify, paused per protocol)
- **Files created:** 2 (test file, run output)
- **Files modified:** 0

## Accomplishments

- 10 async integration tests defined in `tests/test_homelab_list_registered_servers.py` covering TEST-01..TEST-10 verbatim per spec.
- Tests are UNMARKED (D-markers-1) -- no `live_homelab` / `live_ollama` / new pytest markers added.
- `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` matches Phase 1 lock + Pitfall 1 mitigation.
- TEST-05/06/07 surface `result.raw_response` in failure diagnostic (DOCS-03 / OPS-01 inheritance).
- TEST-10 black-box-safe: only `json.loads` + optional `Draft202012Validator.validate(structuredContent)` against `target_tool.outputSchema`. No homelab-mcp internal-shape assertions.
- TEST-07 subject = `json.dumps(target_tool.inputSchema, indent=2)`, NOT description (D-rubrics-3 verbatim).
- No `import homelab_mcp` anywhere in the new file (black-box guard preserved).
- Live sweep ran in 27.84s wall-clock against the configured Ollama (qwen3.6:latest @ 127.0.0.1:11434) and `uvx homelab-mcp` MCP server.
- 9 tests passed functionally; **1 test failed** (TEST-06 disambiguation score=3); **1 test passed but its session-fixture teardown raised** (TEST-10 teardown cancel-scope error).
- No leftover `homelab-mcp.exe` after the run (Windows SC#1 cleanup behavior IS preserved despite the teardown exception).
- Verbatim run output captured to `.planning/phases/04-fixtures-test-cases/04-03-RUN.txt` (215 lines, committed).

## Task Commits

Each task was committed atomically (`--no-verify` per parallel-executor protocol):

1. **Task 1: Create tests/test_homelab_list_registered_servers.py — all 10 integration tests, unmarked** — `02b597d` (feat)
2. **Task 2: Live green sweep — captured 04-03-RUN.txt with full output** — `4e3f785` (test, "capture live integration sweep output")
3. **Task 3: checkpoint:human-verify** — PAUSED. The executor stopped after capturing the run output and writing this SUMMARY draft. User approval required before SUMMARY can be marked final and Phase 4 acceptance flipped.

_Plan metadata commit covered by orchestrator after worktree merge._

## Files Created/Modified

- **`tests/test_homelab_list_registered_servers.py`** (224 lines) — 10 async tests across 3 categories. Unmarked. Imports `Judge` Protocol, `McpTestClient`, `validate_tool_schema`, `Draft202012Validator`. No `import homelab_mcp`.
- **`.planning/phases/04-fixtures-test-cases/04-03-RUN.txt`** (215 lines) — verbatim pytest output from `MCPTF_CONFIG_FILE=./config.yaml uv run pytest tests/test_homelab_list_registered_servers.py -v`.

## Live Sweep Results

| TEST ID | Test name | Status | Notes |
|---------|-----------|--------|-------|
| TEST-01 | test_target_tool_exists | PASSED | target_tool fixture resolved; tool name non-empty |
| TEST-02 | test_schema_passes_structural_checks | PASSED | `validate_tool_schema(target_tool) == []` |
| TEST-03 | test_description_min_length | PASSED | description >= 20 chars |
| TEST-04 | test_every_parameter_has_description_and_type | PASSED | every property has description + type/oneOf/anyOf |
| TEST-05 | test_description_clarity | PASSED | clarity score >= 4 (exact score not surfaced; only failures echo) |
| **TEST-06** | **test_description_disambiguation** | **FAILED** | **score=3 < 4. Judge reasoning: description doesn't disambiguate from hypothetical `list_all_servers` / `list_active_servers`; `active_only` param implies a distinction the description doesn't leverage** |
| TEST-07 | test_parameters_self_explanatory | PASSED | parameters score >= 4 |
| TEST-08 | test_empty_args_call_returns_non_error | PASSED | call_tool({}) -> isError=False |
| TEST-09 | test_result_has_content_or_structured | PASSED | content or structuredContent populated |
| TEST-10 | test_text_content_parses_as_json | **PASSED w/ teardown error** | body assertion succeeded; **session fixture teardown raised** `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` (Pitfall 1) |

**Verbatim summary line from `04-03-RUN.txt`:** `==================== 1 failed, 9 passed, 1 error in 27.84s ====================`

## Two Real Failure Signals (surfaced for user decision)

### Failure A: TEST-06 disambiguation score=3 (judge signal)

The qwen3.6:latest judge returned this reasoning verbatim (from `04-03-RUN.txt`):

> "The description clearly states the tool's function (listing servers) and key output details (SSH credentials, status). However, it lacks specific disambiguation criteria to distinguish it from similar tools (e.g., 'list_all_servers' vs 'list_active_servers' or 'get_server_details'). It describes *what* the tool does but not *when* to choose it over alternatives, which is the core requirement of the disambiguation dimension. The 'active_only' parameter in the context suggests a distinction exists, but the description itself doesn't leverage this for disambiguation."

This is a coherent, defensible critique. The framework is doing its job: it found a real description-quality gap. Per Plan 04-03 explicit guidance:

> **DO NOT** weaken the rubric to make the test pass — that defeats the framework's purpose.

**Recommended response (user/planner decision):**
- (A) Accept the failure as the correct framework signal. File a deferred item to surface to homelab-mcp maintainers ("description should clarify disambiguation criteria"). Phase 4 acceptance for SC#3 (rubric Cat 2 score >= 4) becomes "framework correctly signals quality issue" rather than "all rubric tests pass against current homelab-mcp description". This aligns with the plan's "if real signal, surface upstream, do not soften rubric" guidance.
- (B) Run the live sweep N additional times to characterize variance (single-shot may be lucky/unlucky). If 3+ runs all return score=3, signal is stable. If runs alternate 3/4, threshold sits exactly at the LLM's decision boundary and the user may decide rubric calibration is post-MVP work.
- (C) If user decides homelab-mcp description should be improved, that's a homelab-mcp PR -- not a Phase 4 deliverable.

### Failure B: TEST-10 teardown cancel-scope regression (Pitfall 1)

After all 10 test bodies ran, the session-scoped `mcp_client` fixture's `AsyncExitStack` teardown raised:

```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

The error originates inside the MCP SDK's `stdio_client` context manager (anyio cancel-scope task-pinning) at `.venv/Lib/site-packages/mcp/client/stdio/__init__.py:183` and bubbles through the fixture's `AsyncExitStack.aclose()`. **5 occurrences in `04-03-RUN.txt`** (the multi-frame ExceptionGroup repeats it).

Critical context:
- **Test bodies all completed successfully** — the cancel-scope error fired only at session-end teardown.
- **Get-Process homelab-mcp returned no matches after the run** — the OS process cleanup actually worked despite the cleanup-time exception. Windows SC#1 is met in spirit (no zombies) but not in letter (the teardown emits a noisy exception).

**Plan 04-03 acceptance criterion violated:**
> "The captured output does NOT contain `Attempted to exit cancel scope` (Pitfall 1 regression check)."

The output contains 5 such occurrences. This is a teardown-time regression, not a per-test regression.

**Hypothesis (for user/planner):**
- The session-scoped event loop (`asyncio_default_fixture_loop_scope = "session"`) hosts BOTH the fixture's `__aenter__` AND `__aexit__`. But within the test session, individual test functions may run on a function-scoped task (note `asyncio_default_test_loop_scope=function` in pytest-asyncio config output — line 6 of `04-03-RUN.txt`). When the session ends and the fixture finalizer runs, anyio's cancel-scope assertion (`current_task() is self._host_task`) fails because the host task that opened the cancel scope (during `__aenter__`) is not the task that's now closing it (during finalizer).
- This is a pytest-asyncio + anyio + MCP SDK + Windows ProactorEventLoop interaction. The Phase 1 decision to lock `asyncio_default_fixture_loop_scope = "session"` is correct in principle (matches CONTEXT D-04, Pitfall 1 mitigation) but the test loop scope is `function` by default — that's the asymmetry.
- Possible fixes (NOT applied here per plan instructions):
  - Set `asyncio_default_test_loop_scope = "session"` in `pyproject.toml` so test bodies run on the same task as the session-scoped fixtures (would change Plan 02 / Phase 1 lock; needs planner sign-off).
  - Restructure `mcp_client` to be function-scoped or to use a different teardown idiom (would multiply subprocess count from 1-per-session to 1-per-test; tradeoff).
  - Catch and swallow the specific `RuntimeError("Attempted to exit cancel scope...")` in the fixture finalizer (papers over a real lifecycle issue; not recommended).
  - Investigate whether the brief `_preflight` MCP session interferes with the long-lived `mcp_client` session's task ownership (sequential, but cancel scopes are sticky).
  - Investigate whether the error is specific to ProactorEventLoop on Windows (Pitfall 4 territory).

The user/planner decides whether this is a Phase 4 blocker or a Phase 5+ hardening item.

## CHECKPOINT RESOLVED (Task 3: human-verify) — 2026-05-05

**Type:** human-verify
**Plan:** 04-03
**Progress:** 3/3 tasks completed
**User decision:** Approved with two documented follow-ups (DEF-04-03-A accepted, DEF-04-03-B reassigned to Phase 04.1).

### What changed at resolution

**1. DEF-04-03-A (TEST-06 disambiguation=3 on `list_registered_servers`) — accepted as real signal.**

The user reasoned: the framework's job is to flag weak descriptions; a failing test here is the framework working correctly. Rather than weaken the rubric or change the test, demonstrate the framework's green-path against an alternate target tool whose description has the disambiguation criteria the rubric demands.

**2. Green-path retry: `TARGET_TOOL_NAME=list_keyring_credentials uv run pytest tests/test_homelab_list_registered_servers.py`**

```
======================== 10 passed, 1 error in 25.32s =========================
```

Verbatim output captured at `.planning/phases/04-fixtures-test-cases/04-03-RUN-retry-list_keyring.txt`. All 10 tests PASSED including TEST-06 disambiguation. The judge correctly accepted `list_keyring_credentials`'s description because it explicitly disambiguates *when* to use it ("Call this before ssh_discover or ssh_execute_command") — the criterion the rubric scores against.

**Choice rationale:** `list_keyring_credentials` is read-only with empty args (TEST-08 safe — no side effects on the live homelab), single optional parameter with a description and default value, and disambiguates by usage context.

**Phase 5 spec impact:** None — the documented MVP target (`TARGET_TOOL_NAME=list_registered_servers`) stays the canonical example. The retry is a one-line env override demonstrating framework end-to-end correctness, not a change to the project's documented target.

**3. DEF-04-03-B (cancel-scope teardown) — reassigned to Phase 04.1.**

Speculative pyproject tweak (`asyncio_default_test_loop_scope = "session"`) was tried during checkpoint resolution and discarded — same RuntimeError, faster failure. Confirms the task mismatch is finalizer-task vs fixture-yield-task within the same loop, not loop-vs-loop. Real fix requires fixture-body restructure (anyio.Event-driven owner task pattern). Captured in detail at `.planning/phases/04.1-mcp-client-teardown-fix/04.1-CONTEXT.md` with locked decisions D-01..D-06.

Phase 5 acceptance (clean exit code 0) now correctly depends on Phase 04.1 in `ROADMAP.md`.

### Completed Work (recoverable from commits)

### Completed Work (recoverable from commits)

| Task | Commit | Files | Notes |
| ---- | ------ | ----- | ----- |
| Task 1 | 02b597d | tests/test_homelab_list_registered_servers.py | 10 unmarked async tests, ruff-clean, 10 collected |
| Task 2 | 4e3f785 | .planning/phases/04-fixtures-test-cases/04-03-RUN.txt | live-sweep output, 1 failed / 9 passed / 1 teardown error / no leftover homelab-mcp.exe |

## Decisions Made

- **Surface real failures rather than coerce green** — Plan 04-03 Task 2 explicitly forbids modifying rubric thresholds, test bodies, or fixture logic to make the run green. Both failure signals are real: TEST-06 is judge signal about the homelab-mcp description; TEST-10's teardown error is a Pitfall 1 surfacing in the AsyncExitStack-owned session-scoped fixture lifecycle. Both are documented for the user's Task 3 decision.
- **Write SUMMARY despite checkpoint pause** — The parallel-executor protocol requires SUMMARY.md to be committed before the executor returns (the orchestrator force-removes the worktree). This SUMMARY captures the actual state, the two failure signals, and the unresolved checkpoint so the orchestrator and any continuation agent has full context.
- **No fixture body change** — The cancel-scope teardown error originates in the MCP SDK / anyio interaction, not in the fixture body itself. The fixture follows the documented Pitfall 1 mitigation (AsyncExitStack ownership in `mcp_client` body); the regression is a downstream lifecycle issue. Fixing it would touch Plan 02 fixture code AND/OR `pyproject.toml`, both of which are out of Plan 04-03 scope.
- **Test file unchanged after run** — Resisting the temptation to silence the teardown error by changing fixture scope or to lower the rubric bar. The spec's `score >= 4` threshold and the unmarked-tests + preflight-gate design choices stay intact.

## Deviations from Plan

### None auto-fixed

Plan 04-03 explicitly forbids automatic remediation of test failures or fixture issues. The two real signals are surfaced to the user via the Task 3 checkpoint:human-verify rather than fixed.

### Acceptance criteria status (Task 1)

All Task 1 acceptance criteria PASSED:
- File exists, 224 lines (>= 150) — PASS
- `uv run pytest tests/test_homelab_list_registered_servers.py --collect-only -q` exits 0 with 10 items collected — PASS
- `grep -c 'async def test_'` = 10 — PASS
- `grep -cE 'pytest\.mark\.live_(homelab|ollama)'` = 0 — PASS
- `grep -c 'pytestmark = \[pytest.mark.asyncio(loop_scope="session")\]'` = 1 — PASS
- `grep -cE 'import homelab_mcp|from homelab_mcp'` = 0 — PASS
- `grep -c 'result.raw_response'` = 3 — PASS
- `grep -c 'Draft202012Validator'` = 3 (>= 1) — PASS
- `grep -c 'validate_tool_schema(target_tool)'` = 1 — PASS
- `grep -c 'json.dumps(target_tool.inputSchema'` = 1 — PASS
- `uv run ruff check tests/test_homelab_list_registered_servers.py` exits 0 — PASS

### Acceptance criteria status (Task 2)

| Criterion | Result |
|-----------|--------|
| `uv run pytest tests/test_homelab_list_registered_servers.py -v` exits 0 | **FAIL** (exit code != 0; 1 failed + 1 error) |
| `04-03-RUN.txt` contains line matching `=+ 10 passed` | **FAIL** (contains `1 failed, 9 passed, 1 error`) |
| `04-03-RUN.txt` does NOT contain `Attempted to exit cancel scope` | **FAIL** (5 occurrences) |
| `04-03-RUN.txt` does NOT contain `ERROR` lines (only PASSED) | **FAIL** (1 ERROR at teardown) |
| `04-03-RUN.txt` does NOT contain `pytest.exit` | **PASS** (preflight did not fail) |
| `Get-Process homelab-mcp` after run returns no matches | **PASS** (no zombies despite teardown error) |
| `uv run pytest tests/ -v` (full sweep) also exits 0 | **NOT RUN** (Task 2 marked failed; full-tree sweep deferred to Task 3 user verification) |

## Issues Encountered

- **Default `Config()` uses `mcp_server.command = homelab-mcp`** which is not on PATH; only `uvx` is. Resolved by copying `config.example.yaml` to `config.yaml` (gitignored, runtime-only) and setting `MCPTF_CONFIG_FILE=$(pwd)/config.yaml` for the live run. This matches Phase 02.1 reconciliation. No code change needed; the config seam works as designed.
- **Pre-run leftover homelab-mcp.exe (PID 33176)** from a prior agent's run was killed via PowerShell `Stop-Process -Name homelab-mcp -Force` before the live sweep, per Plan 04-03 Task 2 instructions.
- **Wall-clock cold-start was 27.84s for the full 10-test sweep** — well within the locked 120s `httpx.Timeout`. No model-warmup-induced timeouts.

## Threat Surface Scan

The new test file introduces NO new attack surface beyond what the plan's `<threat_model>` mitigates:

- **T-04-08 (Tampering — prompt injection):** mitigated by Plan 01's `Rubric._HARDENING_PREAMBLE` <<<SUBJECT>>>/<<<END SUBJECT>>> markers in tandem with `ollama_judge._SYSTEM_PROMPT`. The judge's reasoning text (TEST-06) shows the LLM correctly evaluating the description as content, not as instructions — the marker contract is working.
- **T-04-09 (DoS — MCP subprocess hang):** still mitigated by `asyncio.timeout` inside `McpTestClient`. The cancel-scope teardown regression is a clean-shutdown noise issue, NOT a hang or process-leak issue (Get-Process check confirms).
- **T-04-10 (Tampering — unparseable JudgeResult silent pass):** mitigated and verified end-to-end. TEST-06 failure correctly surfaces `result.raw_response` and `result.reasoning` in the assertion message.
- **T-04-11 (Info disclosure in TEST-10 fail diagnostic):** not exercised (TEST-10 body PASSED).
- **T-04-12 (Spoofing — future test adds live_* marker):** not exercised; lint-rule enforcement remains the documented future hardening.

No new surface (no network endpoints, no auth paths, no schema changes, no file access patterns).

## Known Stubs

None in the integration test file. All 10 tests are wired end-to-end:

- TEST-01..04 read real `Tool` fields populated by `mcp_client.list_tools()`.
- TEST-05..07 send real prompts to a live Ollama; assertions consume real `JudgeResult` instances.
- TEST-08..10 call `mcp_client.call_tool(tool_name, {})` against the live MCP subprocess.
- No mocks, no fakes, no skipped branches.

## Deferred Issues (for user / planner / next plan)

| ID | Type | Status | Description | Source |
|----|------|--------|-------------|--------|
| DEF-04-03-A | Judge signal | **accepted (real signal — not framework-side)** | TEST-06 disambiguation score=3 < 4 against homelab-mcp's `list_registered_servers` description. Framework correctly signaled a description-quality gap; the SUT's owner (homelab-mcp) is responsible for resolution if desired. Phase 4 demonstrated green-path against `list_keyring_credentials` (whose description disambiguates by usage context). | Live sweep TEST-06 failure; judge raw_response in `04-03-RUN.txt`; green retry in `04-03-RUN-retry-list_keyring.txt` |
| DEF-04-03-B | Pitfall 1 regression | **resolved (Phase 04.1)** | Session-scoped `mcp_client` fixture teardown raises `RuntimeError: Attempted to exit cancel scope in a different task`. No process leak (Get-Process clean) but pytest exit code is non-zero. Speculative `asyncio_default_test_loop_scope=session` did NOT fix it; needs fixture-body restructure (anyio.Event-driven owner task — see `.planning/phases/04.1-mcp-client-teardown-fix/04.1-CONTEXT.md` D-01..D-06). Resolved 2026-05-06 by Phase 04.1's owner-task + anyio.Event fixture rewrite (Variant B); see .planning/phases/04.1-mcp-client-teardown-fix/04.1-01-SUMMARY.md for verification evidence. | Live sweep TEST-10 teardown; full traceback in `04-03-RUN.txt` lines ~22-105 |
| DEF-04-03-C | UX | open (Phase 5) | Default `Config()` uses `mcp_server.command = homelab-mcp` (not on PATH); requires `MCPTF_CONFIG_FILE=./config.yaml` for the uvx invocation pattern. Phase 5 README must document this verbatim. | Plan 04-03 Task 2 pre-run check |
| DEF-04-03-D | Variance characterization | open (Phase 5) | TEST-05/07 passed but exact scores not surfaced (only failures echo). For Phase 5 README troubleshooting / variance baseline, run the live sweep 3-5 times and record the score distribution. | Live sweep diagnostic (passing tests are silent) |

## TDD Gate Compliance

This plan was not flagged `tdd="true"`. The spec test cases are themselves the TDD lock-in suite for FIX-01/02/03 and TEST-01..10 — they fail-fast against missing fixtures, missing rubrics, and missing tool resolution. The two commits in this plan are ordered `feat -> test`:

- `02b597d feat(04-03): add 10 integration tests for homelab-mcp list_registered_servers` — implementation
- `4e3f785 test(04-03): capture live integration sweep output (1 failed, 9 passed, 1 teardown error)` — live verification artifact

No TDD gate warning.

## User Setup Required (Phase 5 README content)

To reproduce the live sweep:

1. **Ollama** running at `http://127.0.0.1:11434` with `qwen3.6:latest` pulled.
2. **uvx** on PATH (already a `uv` standard binary).
3. **Config file:** `cp config.example.yaml config.yaml` (uses `mcp_server.command = uvx`, `args = [homelab-mcp]`).
4. **Env var:** `MCPTF_CONFIG_FILE=$(pwd)/config.yaml` (PowerShell: `$env:MCPTF_CONFIG_FILE = "$PWD/config.yaml"`).
5. **Run:** `uv run pytest tests/test_homelab_list_registered_servers.py -v`.
6. **Process cleanup verification:** `powershell -Command "Get-Process homelab-mcp -ErrorAction SilentlyContinue"` should return empty.
7. **Cold start:** ~28s for the full 10-test sweep (variance run-to-run not yet characterized — see DEF-04-03-D).

## Next Phase Readiness

- **Phase 4 acceptance is GREEN with documented caveats** (user-approved 2026-05-05). DEF-04-03-A is a real signal about homelab-mcp's description, not a framework defect. DEF-04-03-B is reassigned to Phase 04.1.
- **Phase 04.1 (INSERTED)** owns the `mcp_client` fixture teardown fix. Context locked at `.planning/phases/04.1-mcp-client-teardown-fix/04.1-CONTEXT.md`; phase 5 now depends on 04.1 in `ROADMAP.md`.
- **Phase 5 (CLI + README)** unblocked once Phase 04.1 lands. README content from this SUMMARY ("User Setup Required" section above) is ready to be lifted; DEF-04-03-C and DEF-04-03-D are open Phase 5 line items.

## Self-Check

Verify all claims:

**Files created (exist on disk and committed):**
- `tests/test_homelab_list_registered_servers.py` — FOUND (224 lines)
- `.planning/phases/04-fixtures-test-cases/04-03-RUN.txt` — FOUND (215 lines)

**Commits exist in git log:**
- `02b597d` — FOUND (`feat(04-03): add 10 integration tests for homelab-mcp list_registered_servers`)
- `4e3f785` — FOUND (`test(04-03): capture live integration sweep output (1 failed, 9 passed, 1 teardown error)`)

**Acceptance criteria for Task 1 (all met):** see Deviations from Plan above.

**Acceptance criteria for Task 2 (live-sweep failures):** see Deviations from Plan above. The plan's "Do NOT modify rubric thresholds, test bodies, or fixture logic to coerce a green result" guidance is honored — both failure signals surface to the user.

**Acceptance criteria for Task 3 (checkpoint:human-verify):** PAUSED. Awaiting user resume-signal per the plan's `<resume-signal>` contract. The orchestrator / continuation agent will complete the checkpoint loop after the user replies.

## Self-Check: PASSED (with documented checkpoint pause)

Files committed and recoverable. Plan execution stopped cleanly at Task 3 with structured state in this SUMMARY.md and the verbatim run output in `04-03-RUN.txt`. The two real failure signals are documented with raw judge reasoning + traceback evidence, and the user has the structured information needed to decide on resume-signal.

---
*Phase: 04-fixtures-test-cases*
*Plan: 03*
*Completed (executor exit): 2026-05-06; Plan acceptance pending user Task 3 approval*
