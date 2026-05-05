---
phase: 03-ollama-judge
plan: 02
subsystem: ollama_judge
tags: [judge, parser, unit-tests, qwen3, pydantic-v2]
requires:
  - src/mcp_test_framework/ollama_judge.py (Plan 03-01 module-level helpers under test)
provides:
  - tests/unit/test_ollama_judge.py (14 parser-slice + body-shape unit tests)
affects:
  - tests/smoke/test_smoke_ollama_judge.py (Plan 03-03 will populate; relies on parser already proven by these unit tests)
tech-stack:
  added: []
  patterns:
    - Pure-data unit tests on module-level helpers (no HTTP mocking, no event loop)
    - Falsifying-assertion style — every locked invariant has at least one test that breaks if the invariant is removed
key-files:
  created:
    - tests/unit/test_ollama_judge.py
  modified: []
decisions:
  - "Tests are sync (no @pytest.mark.asyncio, no pytestmark): _build_request_body and _parse_judge_response are pure functions and do not require an event loop — matches CONTEXT 'Phase 3 unit-test scope' Discretion."
  - "No httpx mocking: every test calls a module-level helper directly. The HTTP layer is exercised by the live_ollama smoke (Plan 03-03), not unit tests."
  - "Test 10 (brace-in-string) is the explicit T-03-02-01 falsifier — guards against a future 'use a regex' refactor of _extract_first_json_object."
metrics:
  duration_minutes: ~3
  tasks_completed: 1
  files_created: 1
  files_modified: 0
  completed_date: 2026-05-05
  unit_test_wallclock_seconds: 0.14
requirements_addressed: [CORE-04, OPS-01, DOCS-03]
---

# Phase 3 Plan 02: OllamaJudge Parser-Slice + Body-Shape Unit Tests Summary

A 14-test, mock-free, sync unit-test file at `tests/unit/test_ollama_judge.py` now locks every D-09 parser branch and every CORE-04 / D-07 request-body invariant of the OllamaJudge implementation. Tests run under default `uv run pytest` (no live marker) in 0.14s wall-clock — the parser contract is now exercised on every developer machine and every CI invocation, even without Ollama present.

## What Shipped

### `tests/unit/test_ollama_judge.py` (new, 306 lines, 14 tests)

A single sync, mock-free unit-test file covering two slices:

1. **D-09 parser branches** (10 tests) — every branch of the four-step defensive parser shipped by Plan 03-01.
2. **D-07 / CORE-04 request-body and system-prompt invariants** (4 tests) — the locked `/api/chat` body shape and the `_SYSTEM_PROMPT` constant.

All tests are plain `def test_*` (no `@pytest.mark.asyncio`, no `pytestmark`) — they consume only module-level helpers (`_strip_decorations`, `_extract_first_json_object`, `_parse_judge_response`, `_build_request_body`, `_SYSTEM_PROMPT`, `JudgeResult`) and never touch `httpx`, `AsyncClient`, or the event loop.

## Test Catalogue (14 tests, parser branch each one falsifies)

| #  | Test                                                                               | Branch / Invariant Falsified                                                                                  |
| -- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 1  | `test_strip_decorations_removes_single_think_block`                                | D-09 step 1: single `<think>...</think>` is stripped, trailing JSON intact                                    |
| 2  | `test_strip_decorations_removes_multiple_think_blocks_non_greedy`                  | D-09 step 1: non-greedy regex strips both blocks independently — falsifies a future greedy `.*` refactor      |
| 3  | `test_parse_judge_response_happy_path_overwrites_raw_response`                     | D-09 step 2 + DOCS-03: clean JSON → JudgeResult with `raw_response` = full original input                     |
| 4  | `test_parse_judge_response_think_block_then_fenced_json`                           | D-09 steps 1+2: `<think>` + ` ```json ``` ` fence is stripped, JSON parses cleanly                            |
| 5  | `test_parse_judge_response_brace_recovery_from_prose_prefix`                       | D-09 step 3: prose-prefixed JSON is recovered by the brace-balanced extractor                                 |
| 6  | `test_parse_judge_response_malformed_returns_fallback_with_raw_preserved`          | D-09 step 4 + OPS-01 + DOCS-03: garbage → locked `passed=False, score=1, reasoning="malformed judge response"`|
| 7  | `test_parse_judge_response_out_of_range_score_returns_fallback`                    | D-09 step 4: `score=7` violates `Field(ge=1, le=5)` → fallback (T-03-05 mitigation)                           |
| 8  | `test_parse_judge_response_missing_required_field_returns_fallback`                | D-09 step 4: missing `reasoning` → Pydantic ValidationError → fallback                                        |
| 9  | `test_parse_judge_response_unbalanced_think_no_json_returns_fallback`              | PITFALLS Pitfall 6: unbalanced `<think>` with no JSON falls through all three try-branches to step 4         |
| 10 | `test_extract_first_json_object_handles_braces_inside_strings`                     | PITFALLS Pitfall 5 + T-03-02-01: braces inside JSON string literals do NOT mis-balance the scanner           |
| 11 | `test_build_request_body_locks_stream_false_format_json_think_false`               | CORE-04 / SC#2: stream/format/think/keep_alive/options/model/messages all locked                              |
| 12 | `test_build_request_body_with_context_includes_json_context_line`                  | CORE-04: `Context: {"tool_name": "x"}` substring (json.dumps sort_keys stable) appears in user message        |
| 13 | `test_build_request_body_without_context_omits_context_line`                       | CORE-04: no `Context:` substring when `context is None` — guards against literal `Context: None`              |
| 14 | `test_system_prompt_contains_no_think_and_subject_markers_and_ignore_clause`       | D-07 + T-03-01: `/no_think`, `<<<SUBJECT>>>`, `<<<END SUBJECT>>>`, ignore-instructions clause                 |

## Tasks Completed

| Task | Name                                                                          | Commit  | Files                              |
| ---- | ----------------------------------------------------------------------------- | ------- | ---------------------------------- |
| 1    | Create `tests/unit/test_ollama_judge.py` with parser-slice + body-shape tests | 399369a | `tests/unit/test_ollama_judge.py` |

## Verification

All `<acceptance_criteria>` from the plan satisfied:

- **File exists:** `tests/unit/test_ollama_judge.py` — FOUND
- **Test count:** `grep -c "^def test_" tests/unit/test_ollama_judge.py` returns 14 (≥ 14 required) — PASS
- **No async tests:** `grep -c "^async def test_" tests/unit/test_ollama_judge.py` returns 0 — PASS
- **Import line present:** `grep -F 'from mcp_test_framework.ollama_judge import' ...` matches — PASS
- **D-09 step 4 falsifier present:** `grep -F 'malformed judge response' ...` matches — PASS
- **Think-block corpus present:** `grep -F '<think>' ...` matches in 5 places (corpus + tests) — PASS (≥ 4)
- **Out-of-range corpus present:** `grep -F '"score": 7' ...` matches — PASS
- **Pitfall 5 corpus present:** `grep -F 'score = }5{' ...` matches — PASS
- **Body invariant `stream` + `False`:** matches in test 11 — PASS
- **D-07 falsifier present:** `grep -F '/no_think' ...` matches — PASS
- **No `pytestmark`:** `grep -F 'pytestmark' ...` returns no matches — PASS
- **Black-box invariant:** `grep -E "^import homelab_mcp|^from homelab_mcp" ...` returns no matches — PASS
- **No HTTP mocking:** `grep -E "AsyncClient|httpx\\.|monkeypatch.*post|mock.*request" ...` returns no matches — PASS
- **Tests pass under default pytest:** `uv run pytest tests/unit/test_ollama_judge.py -v` → 14 passed in 0.14s — PASS
- **Collection count:** `uv run pytest tests/unit/test_ollama_judge.py --collect-only -q` → 14 tests collected — PASS
- **Lint clean:** `uv run ruff check tests/unit/test_ollama_judge.py` → All checks passed — PASS
- **Full default suite still green:** `uv run pytest` → 46 passed, 2 deselected (32 pre-existing + 14 new; 2 = pre-existing live_homelab smoke) — PASS
- **Unit tests NOT under live_ollama marker:** `uv run pytest -m live_ollama --collect-only -q | grep -c "tests/unit/test_ollama_judge.py"` → 0 — PASS

## Threat Model Mitigations Implemented

| Threat ID    | Mitigation in Tests                                                                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-03-02-01   | Test 10 (`test_extract_first_json_object_handles_braces_inside_strings`) explicitly exercises the brace-in-string edge case — a future "let's just use a regex" refactor of `_extract_first_json_object` will fail this test. |
| T-03-02-02   | Accept (test diagnostic output): synthetic corpus only; no PII/secrets in test strings.                                                                                                                                   |
| T-03-02-03   | Accept (slow tests): 14 tests run in 0.14s; well under the spec's 1s budget.                                                                                                                                              |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff I001 import-order failure on first run**
- **Found during:** Task 1 verification (`uv run ruff check tests/unit/test_ollama_judge.py`).
- **Issue:** Initial import block listed `JudgeResult` before `_SYSTEM_PROMPT`; ruff's I001 isort rule sorts ASCII-strict (lowercase `_` 0x5F > uppercase `Z` 0x5A), so all underscore-prefixed names sort AFTER capitalized ones in a single import.
- **Fix:** Ran `uv run ruff check --fix tests/unit/test_ollama_judge.py` to apply ruff's autofix. Resulting import order: `JudgeResult`, `_SYSTEM_PROMPT`, `_build_request_body`, `_extract_first_json_object`, `_parse_judge_response`, `_strip_decorations`. Functionally identical.
- **Files modified:** `tests/unit/test_ollama_judge.py`
- **Commit:** `399369a` (same commit; fix applied before commit).

### Note on Worktree File Placement

The Write tool initially placed `test_ollama_judge.py` at the project root path `<home>\projects\mvp_test_framework\tests\unit\test_ollama_judge.py` instead of the worktree path `<home>\projects\mvp_test_framework\.claude\worktrees\agent-a7a21a2015d342202\tests\unit\test_ollama_judge.py`. Detected immediately when `uv run pytest tests/unit/test_ollama_judge.py` reported "no tests ran" inside the worktree. Resolved by `cp`-ing the file into the worktree and `rm`-ing the host-path copy, then re-running tests in the worktree where they passed. The committed file lives in the worktree branch only; the host path is now empty again. Tracked here for transparency.

## Files Created / Modified

**Created:**
- `tests/unit/test_ollama_judge.py` (306 lines, 14 tests)

**Modified:**
- (none)

## What's Next

- **Plan 03-03** writes `tests/smoke/test_smoke_ollama_judge.py` carrying `@pytest.mark.live_ollama`. The smoke can rely on the parser contract being already proven by these unit tests — its only job is to prove the live HTTP path (cold-start canary, `isinstance(judge, Judge)`, real `await judge.judge(rubric, subject)` round-trip).
- **Phase 4 FIX-01** consumes `OllamaJudge` as a session-scoped fixture; no test changes here.
- **Future SEED-001** (pluggable backends): swapping `OllamaJudge` for a different `Judge` implementation requires re-validating ONLY the smoke (live HTTP shape) and any new parser logic — these unit tests pin the contract, not the wire.

## Self-Check: PASSED

- `tests/unit/test_ollama_judge.py` exists in worktree — FOUND
- Commit `399369a` exists in `git log --oneline --all` — FOUND
- 14 tests collected by pytest — FOUND
- Full default suite green (46 passed, 2 deselected) — FOUND
- ruff clean on the new file — FOUND
- No deletions in commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` returns empty) — FOUND
- No `homelab_mcp` imports — FOUND
- No `httpx` / `AsyncClient` / `monkeypatch.*post` / `mock.*request` references — FOUND
- No `pytestmark` declaration — FOUND
- Wall-clock unit-test runtime: 0.14s — well under the 1s budget
