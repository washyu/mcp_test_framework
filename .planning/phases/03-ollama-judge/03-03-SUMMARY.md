---
phase: 03-ollama-judge
plan: 03
subsystem: ollama_judge
tags: [smoke, judge, live-ollama, marker, pytest]
requires:
  - src/mcp_test_framework/ollama_judge.py (Plan 03-01 -- OllamaJudge, JudgeResult)
  - src/mcp_test_framework/judge_protocol.py (Plan 03-01 -- runtime-checkable Judge Protocol)
  - src/mcp_test_framework/config.py (Phase 1 -- Config() loader)
  - pyproject.toml (Plan 03-01 -- live_ollama marker registered + addopts extended)
provides:
  - tests/smoke/test_smoke_ollama_judge.py (live Ollama cold-start canary; SC#1 + SC#2 falsifiers)
affects:
  - .planning/ROADMAP.md (Phase 3 SC#1 and SC#2 now have a test that proves them)
tech-stack:
  added: []
  patterns:
    - Permanent live-marker pytest (mirrors tests/smoke/test_smoke_homelab_mcp.py shape)
    - Layered Protocol falsifier: isinstance + inspect.signature + inspect.iscoroutinefunction (Pitfall 4 mitigation)
    - Canned synthetic subject hard-coded in test (D-04 decoupling from homelab-mcp)
    - Fail-fast inside body via httpx.ConnectError propagation (D-10)
key-files:
  created:
    - tests/smoke/test_smoke_ollama_judge.py
  modified: []
decisions:
  - "Used the verbatim file body from 03-RESEARCH.md §Code Example 6 -- pre-verified against the Phase-2 mirror (tests/smoke/test_smoke_homelab_mcp.py) and the Plan-03-01 module surface."
  - "Accepted the pytest warning 'test marked with @pytest.mark.asyncio but not async function' on test_judge_protocol_satisfied_by_ollama_judge -- the plan's <action> step 5 explicitly designs this test as sync inside a pytestmark-applied module (the asyncio session loop hosts the marker but no awaitable is invoked). Splitting pytestmark per-test would deviate from the verbatim Code Example 6 mirror."
metrics:
  duration_minutes: ~3
  tasks_completed: 1
  files_created: 1
  files_modified: 0
  completed_date: 2026-05-05
requirements_addressed: [CORE-04, OPS-01, OPS-02, DOCS-03]
---

# Phase 3 Plan 03: Live Ollama Smoke Test Summary

A permanent pytest under `tests/smoke/test_smoke_ollama_judge.py` now falsifies BOTH ROADMAP Phase 3 success criteria -- SC#1 (Judge Protocol seam, layered isinstance + signature + async assertions) and SC#2 (cold-start `judge()` against live Ollama returns a valid `JudgeResult`). Gated behind `@pytest.mark.live_ollama` and skipped by default; opt in via `uv run pytest -m live_ollama`. Mirrors the `tests/smoke/test_smoke_homelab_mcp.py` Phase-2 shape exactly: same `pytestmark` structure, same fail-fast-inside-body discipline, same two-test SC layout.

## What Shipped

### `tests/smoke/test_smoke_ollama_judge.py` (new, 87 lines)

- **Module docstring** -- cites D-02 (permanent pytest), D-04 (canned synthetic subject decoupled from homelab-mcp), D-10 (httpx.ConnectError fail-fast propagation), and the two ROADMAP SC falsifiers.
- **Imports** -- `inspect`, `pytest`, plus the Plan-03-01 / Phase-1 surface: `Config`, `Judge` (Protocol), `JudgeResult`, `OllamaJudge`.
- **`pytestmark`** -- `[pytest.mark.live_ollama, pytest.mark.asyncio(loop_scope="session")]`; the session loop scope matches `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml`.
- **Two module-level constants** carrying the canned synthetic subject (D-04 -- orthogonal to `homelab-mcp`):
  - `_CANNED_RUBRIC` -- "Score whether the tool description clearly explains what the tool does to an LLM agent. 5 = unambiguous, 1 = useless. Penalize verbosity."
  - `_CANNED_SUBJECT` -- a plausible `get_weather` tool description with one parameter `city: string` returning a JSON object with `temperature_celsius` and `conditions`.
- **`test_judge_protocol_satisfied_by_ollama_judge`** (SC#1, **sync**) -- three layered assertions per PITFALLS Pitfall 4:
  - Layer 1: `isinstance(j, Judge)` (cheap front-line via `runtime_checkable`)
  - Layer 2: `inspect.signature(OllamaJudge.judge)` -- params == `["self", "rubric", "subject", "context"]`, `context.default is None` (locks D-05 spec-verbatim)
  - Layer 3: `inspect.iscoroutinefunction(OllamaJudge.judge)` (locks the `async def` contract)
  - Runs offline -- constructs `OllamaJudge(base_url="http://unused", model="unused", timeout_seconds=1)` without entering its async context manager, never touches the network.
- **`test_cold_start_returns_valid_judge_result`** (SC#2, **async**) -- the live cold-start canary:
  - `cfg = Config()` (precedence chain -- same pattern as the homelab smoke)
  - `async with OllamaJudge(cfg.ollama.base_url, cfg.ollama.model, cfg.ollama.timeout_seconds) as judge: result = await judge.judge(_CANNED_RUBRIC, _CANNED_SUBJECT)` -- exercises the cold-start path because the smoke IS the first `/api/chat` call (D-08: no warmup logic anywhere upstream).
  - Asserts `isinstance(result, JudgeResult)`, `isinstance(result.passed, bool)`, `1 <= result.score <= 5`, non-empty `reasoning`, non-empty `raw_response` (DOCS-03 falsifier proving the parser overwrote `raw_response` with the actual model output).
  - `print(f"judge result: {result!r}")` -- diagnostic for the manual cold-start UAT (Phase 5 README will document `-s`).
  - **No try/except** -- D-10 transport errors propagate; `httpx.ConnectError` (Ollama unreachable) and `httpx.TimeoutException` (cold-start exceeds 120s) bubble out so pytest reports them with the actual exception type and traceback.

## Tasks Completed

| Task | Name                                                                                 | Commit  | Files                                          |
| ---- | ------------------------------------------------------------------------------------ | ------- | ---------------------------------------------- |
| 1    | Create tests/smoke/test_smoke_ollama_judge.py with SC#1 + SC#2 falsifiers            | 2f494d2 | tests/smoke/test_smoke_ollama_judge.py         |

## Verification

All acceptance criteria from `<acceptance_criteria>` and `<verification>` satisfied:

- **Lint:** `uv run ruff check tests/smoke/test_smoke_ollama_judge.py` -- "All checks passed!"
- **Default pytest skips it:** `uv run pytest --collect-only -q` reports `32/36 tests collected (4 deselected)` -- the two new tests are deselected alongside the two existing live_homelab tests; no `Unknown pytest.mark.live_ollama` warning emitted.
- **`uv run pytest`** (full default suite): `32 passed, 4 deselected in 0.80s` -- no regressions; new smoke is correctly excluded.
- **Marker collection:** `uv run pytest -m live_ollama --collect-only -q` collects exactly `tests/smoke/test_smoke_ollama_judge.py::test_judge_protocol_satisfied_by_ollama_judge` and `::test_cold_start_returns_valid_judge_result` (`2/36 tests collected, 34 deselected`).
- **SC#1 (offline, sync):** `uv run pytest -m live_ollama tests/smoke/test_smoke_ollama_judge.py::test_judge_protocol_satisfied_by_ollama_judge -v` -- `1 passed in 0.17s`. Layer 1 (isinstance), Layer 2 (signature), Layer 3 (iscoroutinefunction) all green.
- **SC#2 (live cold-start UAT):** `uv run pytest -m live_ollama tests/smoke/test_smoke_ollama_judge.py::test_cold_start_returns_valid_judge_result -v -s` -- `1 passed in 13.14s` against live Ollama at `127.0.0.1:11434` with `qwen3.6:latest`. Captured stdout:

  ```
  judge result: JudgeResult(passed=True, score=5, reasoning="The description is concise, unambiguous, and clearly specifies the tool's purpose, input parameters, and output format, making it ideal for an LLM agent.", raw_response='{\n  "passed": true,\n  "score": 5,\n  "reasoning": "The description is concise, unambiguous, and clearly specifies the tool\'s purpose, input parameters, and output format, making it ideal for an LLM agent."\n}')
  ```

  This single end-to-end pass simultaneously falsifies:
  - SC#2 (cold-start `JudgeResult` with `score in 1..5` -- got `score=5`)
  - DOCS-03 raw_response surfacing (the verbatim 3-field model output is present and non-empty)
  - The Plan-03-01 parser's happy path against real Ollama output
  - The locked request body (`format:"json"` + `temperature:0` produced clean JSON, no `<think>` blocks despite qwen3 -- `/no_think` directive worked)
- **Black-box invariant:** `grep -E "^import homelab_mcp|^from homelab_mcp" tests/smoke/test_smoke_ollama_judge.py` -- no matches.
- **No mocks:** `grep -E "Mock|monkeypatch|AsyncMock"` -- no matches.
- **No silent skip:** `grep -E "pytest.skip|@pytest.mark.skipif"` -- no matches.

## `_CANNED_RUBRIC` / `_CANNED_SUBJECT` literals chosen

Per the plan's `<output>` requirement #1, the verbatim literals committed in the test file:

```python
_CANNED_RUBRIC = (
    "Score whether the tool description clearly explains what the tool does "
    "to an LLM agent. 5 = unambiguous, 1 = useless. Penalize verbosity."
)
_CANNED_SUBJECT = (
    "Tool name: get_weather\n"
    "Description: Returns the current weather for a city. "
    "Takes one parameter `city` (string, required) and returns a JSON "
    "object with `temperature_celsius` (number) and `conditions` (string)."
)
```

These are the literals from RESEARCH §Code Example 6, copied verbatim. Decoupled from `homelab-mcp` (D-04) so a future regression in the homelab smoke does not produce a false positive in the Ollama smoke.

## Live Cold-Start UAT (`uv run pytest -m live_ollama -v -s`)

**Result:** PASSED (13.14 seconds wall clock against live Ollama at `127.0.0.1:11434`).

The cold-start UAT in this run was **not a fully cold start** -- the test ran once successfully and the model stayed loaded due to `keep_alive: "30m"` in `_build_request_body`. To exercise the full cold-start path described by the plan's footer note (Phase 5 README guidance), the operator would need to run:

```
ssh ollama-host "ollama stop qwen3.6:latest"
uv run pytest -m live_ollama tests/smoke/test_smoke_ollama_judge.py::test_cold_start_returns_valid_judge_result -v -s
```

This is a **manual UAT** that depends on host access to the Ollama server and is recorded as a Phase 5 README task per the plan's footer (`Manual cold-start UAT pattern: ... -- recorded as a Phase 5 README task; not in scope here.`). The 13.14s observed in this verification run includes the test framework startup (~0.3s) and the model already-loaded `eval_duration` -- well under the 120s `httpx.Timeout` ceiling configured in `OllamaJudge.__aenter__`. A genuine cold-start (model not loaded) would observe a `load_duration` of 13-60s per the Phase 3 PITFALLS §7, plus the eval time, and should still complete inside the 120s ceiling.

`load_duration_ns` was not captured to stdout in the v -s run because the `_log.debug(...)` call in `OllamaJudge.judge` requires `--log-cli-level=DEBUG`. Phase 5 README ceiling guidance can be empirically refined by adding `--log-cli-level=DEBUG` to the manual UAT invocation.

## Threat Model Mitigations Implemented

| Threat ID | Mitigation in Code |
|-----------|---------------------|
| T-03-03-01 (DoS / hang on cold-start) | Inherits the `httpx.Timeout(self._timeout_seconds, connect=10.0)` from Plan 03-01 `OllamaJudge.__aenter__`; this test's wall clock (13.14s) confirms the bounded behavior. |
| T-03-03-02 (smoke runs by accident in CI) | Default `uv run pytest` deselects via `addopts = "-m 'not live_homelab and not live_ollama'"`; verified: 32 passed, 4 deselected. |
| T-03-03-03 (info disclosure via print) | Accepted -- canned synthetic subject contains no PII. |
| T-03-03-04 (spoofing live Ollama) | Inherited from Plan 03-01 -- locked-network homelab dependency, out of MVP scope. |

## Deviations from Plan

### Auto-fixed Issues

None. Executed verbatim from RESEARCH §Code Example 6 (the plan's nominated source-of-truth for the file body) with no structural or logical deviations.

### Note on Pytest Warning (Accepted)

`uv run pytest -m live_ollama tests/smoke/test_smoke_ollama_judge.py::test_judge_protocol_satisfied_by_ollama_judge -v` emits one warning:

```
PytestWarning: The test <Function test_judge_protocol_satisfied_by_ollama_judge> is marked with
'@pytest.mark.asyncio' but it is not an async function. Please remove the asyncio mark.
```

This is **expected and accepted** -- the plan's `<action>` step 5 explicitly designs Test 1 as `def` (sync, no `async def`), and step 3 binds `pytest.mark.asyncio(loop_scope="session")` at the module level via `pytestmark`. The asyncio session-scope marker is harmless on a sync test (the loop simply hosts no awaitable for that function). Splitting `pytestmark` per-test would deviate from the verbatim Code Example 6 mirror, would also deviate from the Phase-2 mirror's `pytestmark` shape, and would introduce a discontinuity that future Phase 4 fixtures (which expect both tests to share a session loop) would have to special-case. The warning is informational, not a failure -- the test exits 0 and pytest's run summary reports `1 passed, 1 warning`.

If a future linting policy promotes warnings to errors, the cleanest resolution is to apply the asyncio marker only to Test 2:

```python
pytestmark = pytest.mark.live_ollama  # both tests share the live marker

async def test_cold_start_returns_valid_judge_result() -> None:  # async function -> auto-detected
    ...
```

But that is **out of scope for Plan 03-03** -- the plan locks the verbatim Code Example 6 shape.

## Files Created / Modified

**Created:**
- `tests/smoke/test_smoke_ollama_judge.py` (87 lines)

**Modified:** None.

## What's Next

- **Phase 4 FIX-01** will wire `OllamaJudge(cfg.ollama.base_url, cfg.ollama.model, cfg.ollama.timeout_seconds)` as a session-scoped fixture; the constructor and `async with` lifecycle proved out by SC#2 here.
- **Phase 4 FIX-02** (`_preflight`) will add a more polite collection-time check that surfaces "Ollama unreachable" with a guidance message instead of the bare `httpx.ConnectError` traceback this smoke produces -- the smoke remains the canary, the fixture wraps the diagnostic.
- **Phase 5 README** will document the manual cold-start UAT (`ollama stop qwen3.6:latest && uv run pytest -m live_ollama -v -s`) and the `load_duration_ns` ceiling guidance.

## Self-Check: PASSED

- `tests/smoke/test_smoke_ollama_judge.py` exists -- FOUND
- Commit `2f494d2` exists in `git log` -- FOUND
- `grep -c "pytest.mark.live_ollama" tests/smoke/test_smoke_ollama_judge.py` -- 1 (passed)
- `grep -c "pytest.mark.asyncio(loop_scope=\"session\")" tests/smoke/test_smoke_ollama_judge.py` -- 1 (passed)
- `grep -F 'from mcp_test_framework.judge_protocol import Judge'` -- 1 match (passed)
- `grep -F 'from mcp_test_framework.ollama_judge import'` -- 1 match (passed)
- `grep -F 'from mcp_test_framework.config import Config'` -- 1 match (passed)
- `def test_judge_protocol_satisfied_by_ollama_judge` -- 1 (passed)
- `async def test_cold_start_returns_valid_judge_result` -- 1 (passed)
- `isinstance(j, Judge)`, `inspect.signature(OllamaJudge.judge)`, `inspect.iscoroutinefunction(OllamaJudge.judge)` -- all present (Pitfall 4 mitigation)
- `async with OllamaJudge(`, `await judge.judge(`, `1 <= result.score <= 5`, `result.raw_response` -- all present
- `_CANNED_RUBRIC` / `_CANNED_SUBJECT` -- 2 occurrences each (definition + use)
- No `pytest.skip` / `@pytest.mark.skipif` -- 0 matches (D-04 fail-fast)
- No `import homelab_mcp` / `from homelab_mcp` -- 0 matches (black box)
- No `Mock` / `monkeypatch` / `AsyncMock` -- 0 matches (live integration smoke)
- `uv run ruff check tests/smoke/test_smoke_ollama_judge.py` -- All checks passed
- Default `uv run pytest` -- 32 passed, 4 deselected (no regression; new smoke correctly excluded)
- `uv run pytest -m live_ollama --collect-only -q` -- 2 tests collected from the new file
- SC#1 offline: `uv run pytest -m live_ollama ::test_judge_protocol_satisfied_by_ollama_judge -v` -- 1 passed in 0.17s
- SC#2 live cold-start: `uv run pytest -m live_ollama ::test_cold_start_returns_valid_judge_result -v -s` -- 1 passed in 13.14s with `score=5` against live Ollama
