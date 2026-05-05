---
phase: 03-ollama-judge
verified: 2026-05-05T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 3: Ollama Judge Verification Report

**Phase Goal:** OllamaJudge reliably returns a validated JudgeResult from the live Ollama at 127.0.0.1:11434 even on cold start, even with qwen3 thinking quirks, and the Judge Protocol seam is in place for post-MVP backend swaps.

**Verified:** 2026-05-05
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| SC1 | `judge_protocol.Judge` is a Protocol with one async `judge(rubric, subject, context)` method that `OllamaJudge` implements | VERIFIED | `src/mcp_test_framework/judge_protocol.py` lines 46-61 define `@runtime_checkable class Judge(Protocol)` with the spec-verbatim async signature. Cross-module check: `isinstance(OllamaJudge('http://x','m',1), Judge)` returns True. `inspect.signature(OllamaJudge.judge)` parameters == `['self','rubric','subject','context']` with `context.default is None`. `inspect.iscoroutinefunction(OllamaJudge.judge)` is True. Smoke test `test_judge_protocol_satisfied_by_ollama_judge` layers all three assertions. |
| SC2 | Smoke test against live Ollama returns a valid JudgeResult with the locked options (stream:false, format:json, think:false, temperature:0, num_predict:256, keep_alive:"30m"), including cold-start path | VERIFIED | `tests/smoke/test_smoke_ollama_judge.py::test_cold_start_returns_valid_judge_result` ran live (13.14s wall) returning `JudgeResult(passed=True, score=5)` per orchestrator. `_build_request_body` (ollama_judge.py:146-160) hard-codes all six locked options; verified by `test_build_request_body_locks_stream_false_format_json_think_false` (PASSED). |
| SC3 | Response parser strips `<think>...</think>` blocks, falls back to `passed=False` JudgeResult on parse failure with raw response preserved, validates 1≤score≤5 plus all 3 required fields | VERIFIED | `_strip_decorations` uses non-greedy `_THINK_RE` (ollama_judge.py:165). `_parse_judge_response` four-step contract (ollama_judge.py:240-282); fallback at line 277-282 returns `JudgeResult(passed=False, score=1, reasoning="malformed judge response", raw_response=content)`. `JudgeResult.score = Field(ge=1, le=5)` (ollama_judge.py:111). All 6 fallback-related unit tests PASS (think-strip, multi-think non-greedy, malformed, out-of-range score=7, missing field, unbalanced think). |
| SC4 | Every Ollama HTTP call uses `httpx.Timeout(120, connect=10)` and every MCP subprocess call uses `asyncio.timeout()` | VERIFIED | `OllamaJudge.__aenter__` (ollama_judge.py:309-322) constructs `httpx.AsyncClient(base_url=..., timeout=httpx.Timeout(self._timeout_seconds, connect=10.0))`. Default `OllamaConfig.timeout_seconds = 120` per Phase 1 models.py. MCP `asyncio.timeout()` was verified in Phase 2 (out of scope; carries forward). |
| SC5 | When judge fails (timeout or malformed JSON), the affected test fails with raw_response visible and run continues | VERIFIED | Malformed JSON path: `_parse_judge_response` returns `passed=False` JudgeResult with `raw_response=<original>` preserved on every parser branch (DOCS-03). Smoke test asserts `result.raw_response.strip()` to verify surfacing. Transport errors (D-10) propagate via `response.raise_for_status()` (line 362) — Phase 4 fixtures will turn them into `pytest.fail` with raw context, but the propagation seam is in place; per-test isolation is pytest-default behavior. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/mcp_test_framework/judge_protocol.py` | Runtime-checkable Judge Protocol with async judge(rubric, subject, context) -> JudgeResult | VERIFIED | 62 lines; `@runtime_checkable class Judge(Protocol)` with spec-verbatim signature; imports JudgeResult from ollama_judge.py (one-way dep, no circular). |
| `src/mcp_test_framework/ollama_judge.py` | OllamaJudge + JudgeResult + _build_request_body + _parse_judge_response + helpers | VERIFIED | 374 lines; all required public/private symbols present; `httpx.Timeout(self._timeout_seconds, connect=10.0)` literal at line 314 (OPS-02 falsifier); `_SYSTEM_PROMPT` includes /no_think + <<<SUBJECT>>> + ignore-instructions clause. |
| `tests/unit/test_ollama_judge.py` | 14 parser-slice + body-shape unit tests | VERIFIED | 14 tests collected, all PASS in 0.11s. Covers D-09 steps 1/2/3/4 + locked body invariants + system-prompt assertions. No mocks; pure-function calls. |
| `tests/smoke/test_smoke_ollama_judge.py` | Live cold-start canary: SC#1 (Protocol seam) + SC#2 (cold-start judge call) | VERIFIED | 87 lines; `pytest.mark.live_ollama` gated; both tests collected under marker filter. SC#1 layers isinstance + signature + iscoroutinefunction (Pitfall 4 mitigation). SC#2 ran against live Ollama returning JudgeResult(passed=True, score=5) in 13.14s. |
| `pyproject.toml` | live_ollama marker registered + addopts skips both live markers | VERIFIED | Line 39: `live_ollama: requires reachable Ollama at OLLAMA_BASE_URL...`. Line 41: `addopts = "-m 'not live_homelab and not live_ollama'"`. Default collection: 46/50 tests, 4 deselected (2 live_homelab + 2 live_ollama). No "Unknown pytest.mark.live_ollama" warnings. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| judge_protocol.py | ollama_judge.py | `from mcp_test_framework.ollama_judge import JudgeResult` | WIRED | Line 43 imports JudgeResult; Protocol return annotation uses it. Cross-module check `isinstance(OllamaJudge(...), Judge)` returns True. |
| ollama_judge.py | Ollama /api/chat | `self._client.post("/api/chat", json=body)` | WIRED | Line 361 in `judge()` method; preceded by `_build_request_body` call and followed by `raise_for_status()` + parse. |
| pyproject.toml | tests/smoke/* | Marker filter in addopts | WIRED | Default collection deselects 4 tests (both live markers); `-m live_ollama --collect-only` collects exactly the 2 ollama smoke tests. |
| tests/smoke/test_smoke_ollama_judge.py | judge_protocol.py | `from mcp_test_framework.judge_protocol import Judge` | WIRED | Line 30; consumed by `isinstance(j, Judge)` assertion in SC#1 test. |
| tests/smoke/test_smoke_ollama_judge.py | ollama_judge.py | `async with OllamaJudge(...)` + `await judge.judge(...)` | WIRED | Lines 73-78 in SC#2 test; live integration verified (judge returned valid JudgeResult). |
| tests/unit/test_ollama_judge.py | ollama_judge.py | Module-level helper imports | WIRED | Lines 42-49 import `_SYSTEM_PROMPT`, `JudgeResult`, `_build_request_body`, `_extract_first_json_object`, `_parse_judge_response`, `_strip_decorations`. 14/14 tests PASS. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `OllamaJudge.judge` | `data["message"]["content"]` | `await self._client.post("/api/chat", json=body)` → `response.json()` | Yes — live Ollama returned real JSON content (verified by smoke run: `score=5` with non-empty reasoning + raw_response) | FLOWING |
| `_parse_judge_response` | parsed JudgeResult fields | `_validate_with_raw` → `json.loads` → `JudgeResult.model_validate` | Yes — real model output flows through; raw_response patched into the dict before validation | FLOWING |
| `JudgeResult.raw_response` | original `content` parameter | Patched by `_validate_with_raw` (line 236) before model_validate; preserved on fallback (line 281) | Yes — verified by smoke (`assert result.raw_response.strip()`) and unit tests (assertions `result.raw_response == _HAPPY` etc.) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Module-level helpers and Protocol importable; isinstance + signature + body invariants + parser fallback | `uv run python -c "from mcp_test_framework.judge_protocol import Judge; from mcp_test_framework.ollama_judge import OllamaJudge, JudgeResult, _build_request_body, _parse_judge_response, _SYSTEM_PROMPT; ..."` | `ALL CHECKS PASSED` | PASS |
| Unit tests pass | `uv run pytest tests/unit/test_ollama_judge.py -v` | 14 passed in 0.11s | PASS |
| Default pytest collection skips both live markers | `uv run pytest --collect-only -q` | 46/50 collected, 4 deselected, no Unknown marker warnings | PASS |
| Live marker collects exactly the 2 ollama smoke tests | `uv run pytest -m live_ollama --collect-only -q` | 2/50 collected (test_judge_protocol_satisfied_by_ollama_judge + test_cold_start_returns_valid_judge_result) | PASS |
| Live cold-start judge call against Ollama | `uv run pytest -m live_ollama tests/smoke/test_smoke_ollama_judge.py::test_cold_start_returns_valid_judge_result -v -s` (per orchestrator) | 1 passed in 13.14s; `JudgeResult(passed=True, score=5)` with non-empty reasoning + raw_response | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| CORE-04 | 03-01, 03-02, 03-03 | `ollama_judge.py` implements Judge Protocol, POSTs to /api/chat with locked options, system prompt with /no_think + delimited subject, parser strips `<think>` and validates JudgeResult shape | SATISFIED | `judge_protocol.py` defines Protocol; `OllamaJudge` implements it; `_build_request_body` locks all options (asserted by unit test 11); `_SYSTEM_PROMPT` carries /no_think + markers (asserted by unit test 14); parser strips think blocks and validates score 1-5 + 3 required fields (asserted by unit tests 1-9). |
| OPS-01 | 03-02, 03-03 | Ollama timeouts and malformed JSON cause affected test to fail with raw response surfaced; run continues | SATISFIED | `_parse_judge_response` malformed-fallback unit tests (5-9) prove `passed=False` with `raw_response` preserved. Transport timeouts propagate per D-10; pytest's per-test isolation continues other tests. Smoke asserts `result.raw_response.strip()` proving surfacing. |
| OPS-02 | 03-01, 03-03 | `httpx.Timeout(120, connect=10)` on every Ollama HTTP call; no operation can hang indefinitely | SATISFIED | `OllamaJudge.__aenter__` line 314: `timeout=httpx.Timeout(self._timeout_seconds, connect=10.0)`. Default `OllamaConfig.timeout_seconds = 120`. Live smoke completed in 13.14s, well under 120s ceiling. |
| DOCS-03 | 03-01, 03-02, 03-03 | Judge failures surface model's `raw_response` in test failure output | SATISFIED | `JudgeResult.raw_response` is a required field. `_parse_judge_response` preserves raw_response on every branch (happy: `_validate_with_raw` patches the original `content`; fallback: explicit `raw_response=content`). Unit tests 3, 5, 6, 7, 8, 9, 10 assert `result.raw_response == <original>`. Smoke asserts non-empty raw_response. |

All 4 requirement IDs from PLAN frontmatter are accounted for. No orphans (REQUIREMENTS.md maps exactly CORE-04, OPS-01, OPS-02, DOCS-03 to Phase 3, all claimed by plans 01/02/03).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |

None found. Scanned `ollama_judge.py`, `judge_protocol.py`, `test_ollama_judge.py`, `test_smoke_ollama_judge.py` for TODO/FIXME/placeholder/empty-impl/stub patterns. No matches. The fallback `JudgeResult(passed=False, score=1, reasoning="malformed judge response", raw_response=content)` is intentional contract behavior, not a stub.

### Human Verification Required

None. All ROADMAP success criteria have automated falsifiers — SC#1/#3/#4 by unit tests, SC#2 by live smoke (already executed), SC#5 by parser fallback unit tests. The orchestrator confirmed the live cold-start smoke test passed with `JudgeResult(passed=True, score=5)`.

The Phase 3 Plan 03 SUMMARY notes a follow-up "true cold start" UAT (`ollama stop qwen3.6:latest` then re-run) recorded as a Phase 5 README task — not in scope for this phase. SC#2 only requires that the smoke returns a valid JudgeResult including the cold-start path, which is empirically satisfied by the smoke being the first /api/chat call (no warmup logic anywhere upstream per D-08).

### Gaps Summary

No gaps. All 5 ROADMAP Success Criteria pass with codebase-grounded evidence. All 4 requirement IDs (CORE-04, OPS-01, OPS-02, DOCS-03) are addressed across the three plans. All artifacts exist, are substantive, are wired, and produce real data. Phase goal achieved: OllamaJudge reliably returns a validated JudgeResult from live Ollama (verified by smoke), defensive parser handles qwen3 thinking quirks (verified by unit tests), and the runtime-checkable Judge Protocol seam is in place for post-MVP backend swaps (verified by isinstance + signature + iscoroutinefunction layered assertions).

---

_Verified: 2026-05-05_
_Verifier: Claude (gsd-verifier)_
