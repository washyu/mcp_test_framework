---
phase: 03-ollama-judge
fixed_at: 2026-05-05T00:00:00Z
review_path: .planning/phases/03-ollama-judge/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-05-05
**Source review:** `.planning/phases/03-ollama-judge/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (all WARNING; 0 CRITICAL; 5 INFO out of scope under `critical_warning`)
- Fixed: 4
- Skipped: 0

All four WARNING findings were applied to `src/mcp_test_framework/ollama_judge.py`.
The five INFO findings (IN-01 through IN-05) were intentionally not addressed
because the configured `fix_scope` was `critical_warning`.

Each fix was verified with Tier 1 (re-read of edited section) and Tier 2
(`python -c "import ast; ast.parse(...)"` syntax check). WR-03 and WR-04 also
got an additional functional smoke test invoking `_strip_decorations` and
`_parse_judge_response` directly to confirm the existing happy-path behaviour
was preserved and the new branches behave as expected.

## Fixed Issues

### WR-01: `assert self._client is not None` is elided under `python -O`

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `f12bcf2`
**Applied fix:** Replaced the bare `assert self._client is not None, "OllamaJudge not entered"` at the top of `judge()` with an explicit `if self._client is None: raise RuntimeError(...)`. The new error message points the caller at the correct `async with OllamaJudge(...) as judge:` pattern. The check now survives `python -O` / `PYTHONOPTIMIZE` so downstream consumers running pytest under optimized bytecode get the actionable lifecycle error instead of `AttributeError: 'NoneType' object has no attribute 'post'`.

### WR-02: malformed-but-2xx Ollama envelope bypasses the defensive parser

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `64058b2`
**Applied fix:** Replaced the unguarded `content = data["message"]["content"]` with defensive `data.get("message")` / `message.get("content")` extraction with `isinstance` checks. When the envelope is malformed (e.g., `{"error": "..."}`, missing `message`, `null` content), the code now routes the verbatim `response.text` through `_parse_judge_response`, which lands the four-step fallback path and returns a `JudgeResult(passed=False, score=1, reasoning="malformed judge response", raw_response=<envelope>)`. Transport-level errors (D-10) remain unchanged because `raise_for_status()` runs first.

### WR-03: trailing-fence regex requires end-of-string and silently no-ops on stray suffix text

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `c7c1ca8`
**Applied fix:** Replaced the brittle single-pattern `_FENCE_RE` (which anchored its trailing-fence alternative on `$`) with a two-pass strategy: a one-shot `_FENCE_OPEN_RE.sub(..., count=1)` for the opening fence and `str.rpartition("```")` for the closing fence. The new code drops anything after the last closing fence, including stray model commentary like `\nDone.`, so brace recovery in step 3 no longer has to compensate for fence-stripping shortcomings. Functional smoke test (running `_strip_decorations` and `_parse_judge_response` against a `"<think>x</think>\n\`\`\`json\n{...}\n\`\`\`\nDone."` input) confirmed the new behavior parses cleanly via step 2 instead of falling into step 3 or step 4.

**Logic-bug note:** This change touches a string-transformation routine that is well covered by existing unit tests for the happy path (`test_strip_decorations_*`, `test_parse_judge_response_think_block_then_fenced_json`). The reviewer suggested adding a unit test for the trailing-text case "to lock current behaviour either way" -- that is a follow-up not part of this fix scope. The Phase 4 verifier should still re-run the unit corpus to confirm no regression.

### WR-04: `_extract_first_json_object` returns `None` for unbalanced braces -- silently swallowed at step 3

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `48c4c21`
**Applied fix:** Added `_log.debug(...)` records on every parser branch transition: step 2 validation failure (with the exception message), step 3 success-or-no-balanced-object, step 3 validation failure (with the exception message), and step 4 fallback. Also added `data.get("done_reason")` to the response-shape debug log so an operator can distinguish `done_reason="length"` (num_predict exhaustion / truncated output) from genuine malformed model output when the parser falls through to step 4. Verified end-to-end by running each parser path with `logging.basicConfig(level=logging.DEBUG)` and confirming each branch emits exactly one debug record.

---

_Fixed: 2026-05-05_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
