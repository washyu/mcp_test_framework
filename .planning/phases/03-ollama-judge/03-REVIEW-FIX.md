---
phase: 03-ollama-judge
fixed_at: 2026-05-05T00:00:00Z
review_path: .planning/phases/03-ollama-judge/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-05-05
**Source review:** `.planning/phases/03-ollama-judge/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 WARNING, 4 INFO -- fix_scope=all)
- Fixed: 5
- Skipped: 0

All five findings from the re-review were applied as atomic commits. Unit
test suite (47 tests) green after the changes; the new escaped-quote test
case (IN-02) passes against the existing parser.

Fix commits live on branch `review-fix-03-sv-03-reviewfix-OnwiEL` (created
from `master` in worktree `/tmp/sv-03-reviewfix-OnwiEL`); orchestrator
should merge that branch into `master` to bring the five fix commits into
the main working tree.

## Fixed Issues

### WR-05: `response.json()` on a 2xx-but-non-JSON body bypasses the defensive parser

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `66f29f9`
**Applied fix:** Wrapped `response.json()` in `try/except ValueError` inside
`OllamaJudge.judge`. On a non-JSON 2xx body (proxy HTML error page, empty
body, OpenAPI route list from a misconfigured tunnel), the call now routes
through `_parse_judge_response(response.text)` -- the same fallback path
WR-02 used for malformed envelopes -- so `raw_response` is preserved and
operators see the actual body in diagnostic output instead of a raw
`json.JSONDecodeError` traceback. The except clause catches `ValueError`
because `json.JSONDecodeError` is a `ValueError` subclass.

### IN-05: "dead-code documentation" comment in `_parse_judge_response`

**Files modified:** `src/mcp_test_framework/ollama_judge.py`
**Commit:** `0d8d496`
**Applied fix:** Reworded the docstring note that previously claimed
`ValueError` was 'honored as dead-code documentation per Pydantic v2.13'.
The new wording makes it explicit that the `(ValidationError, ValueError)`
union catches both Pydantic shape errors AND raw JSON syntax errors, that
step 3's brace-extracted retry depends on syntax errors flowing through
step 2, and that narrowing the catch to `ValidationError` alone would
break brace-recovery. This removes a footgun for future maintainers.

### IN-02: missing test for escaped-quote brace-scanner branch

**Files modified:** `tests/unit/test_ollama_judge.py`
**Commit:** `47e18d4`
**Applied fix:** Added `_ESCAPED_QUOTE` corpus entry containing literal
`\"` escape sequences in the reasoning value, plus
`test_extract_first_json_object_handles_escaped_quotes_in_strings`
asserting both raw extraction (escapes preserved verbatim) and parser
round-trip (decoded `reasoning == 'say "hi"'`). This pins the `escape`
branch of the brace-scanner state machine so a future refactor cannot
silently drop it as dead code. Test executes and passes against the
existing parser implementation.

### IN-04: smoke docstring overstates fail-fast behaviour

**Files modified:** `tests/smoke/test_smoke_ollama_judge.py`
**Commit:** `5c3d36f`
**Applied fix:** Tightened the module docstring to scope the fail-fast
claim to the cold-start test only. The Protocol-shape test
(`test_judge_protocol_satisfied_by_ollama_judge`) constructs `OllamaJudge`
without entering `async with` and therefore never opens a connection, so
it passes regardless of Ollama availability -- the new docstring states
that explicitly so the docs no longer mislead operators triaging a
degraded environment.

### IN-03: stray `print` in smoke test

**Files modified:** `tests/smoke/test_smoke_ollama_judge.py`
**Commit:** `7c69ad7`
**Applied fix:** Replaced `print(f"judge result: {result!r}")` with
`_log.info("cold-start judge result: %r", result)` on the same logger
namespace as the production module
(`mcp_test_framework.ollama_judge`). Default pytest runs stay quiet;
verifiers can opt in via `pytest --log-cli-level=INFO`. Honors the
production module's "never the full Ollama response body by default"
logging policy.

---

_Fixed: 2026-05-05_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
