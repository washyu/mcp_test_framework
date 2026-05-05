---
phase: 03-ollama-judge
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/mcp_test_framework/ollama_judge.py
  - src/mcp_test_framework/judge_protocol.py
  - pyproject.toml
  - tests/unit/test_ollama_judge.py
  - tests/smoke/test_smoke_ollama_judge.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 3 implements an async Ollama-backed LLM judge with a runtime-checkable
`Judge` Protocol seam, a defensive four-step response parser, a locked
`/api/chat` request body, and a constant prompt-injection-hardened system
prompt. The unit test corpus is thorough on the parser and request-body
invariants, the smoke test correctly exercises both layers of the SC#1
falsifier (Protocol + signature + async-ness), and lifecycle ownership via
`AsyncExitStack` mirrors the Phase 2 `McpTestClient` pattern as documented.

No BLOCKER defects found. Four WARNING findings cluster around defensive
robustness gaps in the live HTTP path:

1. `assert self._client is not None` is silently elided under `python -O`,
   leaking the failure mode it is meant to guard against.
2. `data["message"]["content"]` raises a confusing `KeyError` /
   `TypeError` on a 2xx-but-malformed Ollama envelope, bypassing the
   four-step parser fallback that the module's docstring promises.
3. `_strip_decorations` and `_FENCE_RE` will not strip a trailing fence when
   the model emits any non-whitespace text after the closing ` ``` `, even
   though the brace-extractor would still succeed on the input — the regex
   is more brittle than necessary.
4. `_BRACE_IN_STRING` uses a JSON-style key/value layout but its `reasoning`
   string contains a literal `}` character that does not appear in the test
   corpus comment — minor, but the unit test asserts equality with a
   string that is not valid JSON if the brace-counter were buggy. The test
   is correct; the comment around it slightly oversells what it falsifies.

Five INFO items cover dead imports, an unused regex flag, a stray `print` in
the smoke test, an inert escape branch in the brace scanner, and a
documentation drift between the module docstring and the parser exception
catch.

## Warnings

### WR-01: `assert self._client is not None` is elided under `python -O`

**File:** `src/mcp_test_framework/ollama_judge.py:350`
**Issue:** The lifecycle guard `assert self._client is not None, "OllamaJudge not entered"` is the only thing standing between a forgotten `async with` block and an `AttributeError: 'NoneType' object has no attribute 'post'` on the next line. Python's `-O` flag (and any environment that sets `PYTHONOPTIMIZE`) strips `assert` statements at compile time. Because this judge is intended to ship as a library consumed by other test suites, downstream users running pytest under `python -O` (a common micro-optimization) will see the cryptic `NoneType.post` traceback instead of the actionable "OllamaJudge not entered" message. The docstring contract ("Lifecycle owned via `AsyncExitStack` inside `__aenter__`") relies on this guard being load-bearing.
**Fix:** Replace the assertion with a real runtime check that survives `-O`:
```python
async def judge(self, rubric: str, subject: str, context: dict | None = None) -> JudgeResult:
    if self._client is None:
        raise RuntimeError(
            "OllamaJudge.judge() called outside an `async with` block; "
            "use `async with OllamaJudge(...) as judge: await judge.judge(...)`"
        )
    body = _build_request_body(self._model, rubric, subject, context)
    ...
```

### WR-02: malformed-but-2xx Ollama envelope bypasses the defensive parser

**File:** `src/mcp_test_framework/ollama_judge.py:363-364`
**Issue:** The module docstring states "Malformed-content failures (valid 2xx response but unparseable body) fall through the four-step defensive parser (D-09) and return a `passed=False` JudgeResult with `raw_response` preserved" (line 347-348). However, the implementation only wraps malformed `content` text — the envelope shape itself is dereferenced unguarded:
```python
data = response.json()
content = data["message"]["content"]
```
If Ollama returns `{"error": "model not found"}` (200 OK with a non-chat envelope), `{"message": {}}` (missing `content`), or `{"message": {"content": null}}`, this code raises `KeyError` or, in the `null` case, raises `TypeError` on the next `len(content)` log line. None of these are transport-level errors per D-10 (they are not `httpx.HTTPStatusError`, `httpx.TimeoutException`, or `httpx.ConnectError`) — they are body-shape failures that the four-step parser was designed to absorb. The exceptions also leak through the smoke test's `pytest.fail` formatting (Phase 4) as `KeyError: 'message'`, which is materially less debuggable than the locked fallback `JudgeResult` with `raw_response` set to the verbatim envelope.
**Fix:** Defensively extract the content string and route any envelope-shape failure into the same step-4 fallback path, preserving the raw envelope as `raw_response`:
```python
data = response.json()
message = data.get("message")
if not isinstance(message, dict):
    return _parse_judge_response(response.text)
content = message.get("content")
if not isinstance(content, str):
    return _parse_judge_response(response.text)

_log.debug(...)
return _parse_judge_response(content)
```
This honors the docstring contract and keeps D-10 (transport errors propagate) intact because `raise_for_status()` still runs first.

### WR-03: trailing-fence regex requires end-of-string and silently no-ops on stray suffix text

**File:** `src/mcp_test_framework/ollama_judge.py:169`
**Issue:** `_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.DOTALL)` anchors the trailing-fence alternative to `$` (end-of-string, since `re.MULTILINE` is not set). If qwen3 emits a single trailing newline-and-comment after the fence (e.g., `'\n```json\n{...}\n```\n\n'` is fine, but `'\n```json\n{...}\n```\nDone.'` is not), the trailing fence is left in place, the resulting text is `{...}\n```\nDone.`, and `json.loads` fails on the stripped content. The brace-extractor then recovers and the fallback path still works, so this is not a correctness bug today — but it is a brittle dependence on the trailing fence being followed by *only* whitespace. The fix is one-line and removes a class of future flake.
**Fix:** Either drop the `$` anchor (match a trailing fence anywhere), or — preferred — strip fences with two simpler passes that do not depend on string anchors:
```python
_FENCE_OPEN_RE = re.compile(r"```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\s*```")

def _strip_decorations(content: str) -> str:
    stripped = _THINK_RE.sub("", content)
    # Strip first opening fence and last closing fence; leave the body alone.
    stripped = _FENCE_OPEN_RE.sub("", stripped, count=1)
    # Reverse-strip the last closing fence by splitting on it.
    if "```" in stripped:
        head, _, _ = stripped.rpartition("```")
        stripped = head
    return stripped.strip()
```
At minimum, add a unit test for `'<think>x</think>\n```json\n{...}\n```\nDone.'` to lock current behaviour either way.

### WR-04: `_extract_first_json_object` returns `None` for unbalanced braces — silently swallowed at step 3

**File:** `src/mcp_test_framework/ollama_judge.py:184-219`
**Issue:** When the brace scanner walks off the end of the string with `depth > 0` (unbalanced `{`), it returns `None` and the parser falls through to step 4. That is the documented behaviour. However, the loop has no signal at all that the content was *partially* parseable — a truncated response (`num_predict: 256` is small for some rubric outputs; the model can run out of tokens mid-`reasoning`) hits this path silently and the fallback `reasoning="malformed judge response"` reveals nothing about the actual cause. There is no DEBUG log emitted on the recovery branch either, so an operator inspecting `--log-cli-level=DEBUG` cannot tell whether the parser tried brace recovery and failed vs. tried it and succeeded vs. never tried it.
**Fix:** Emit a DEBUG record on every parser branch transition so the four-step contract is observable:
```python
def _parse_judge_response(content: str) -> JudgeResult:
    stripped = _strip_decorations(content)
    try:
        return _validate_with_raw(stripped, content)
    except (ValidationError, ValueError) as e:
        _log.debug("ollama judge parse step 2 failed: %s", e)

    extracted = _extract_first_json_object(stripped)
    if extracted is not None:
        try:
            return _validate_with_raw(extracted, content)
        except (ValidationError, ValueError) as e:
            _log.debug("ollama judge parse step 3 failed: %s", e)
    else:
        _log.debug("ollama judge parse step 3: no balanced JSON object found")

    _log.debug("ollama judge parse step 4: returning malformed fallback")
    return JudgeResult(
        passed=False, score=1, reasoning="malformed judge response", raw_response=content,
    )
```
Also worth considering: surface the truncation case via `num_predict` exhaustion. Ollama returns `done_reason: "length"` in `data` when truncation occurs; logging that at the call site would distinguish "model went off the rails" from "we ran out of token budget."

## Info

### IN-01: `re.DOTALL` flag on `_FENCE_RE` is inert

**File:** `src/mcp_test_framework/ollama_judge.py:169`
**Issue:** `_FENCE_RE` is compiled with `re.IGNORECASE | re.DOTALL`. The `re.DOTALL` flag makes `.` match newlines, but the pattern contains no `.` — only `^`, `\s*`, `` ``` ``, `(?:json)?`, and `$`. The flag is dead.
**Fix:** Drop `re.DOTALL`:
```python
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
```

### IN-02: brace-scanner `escape` branch is reachable but its only effect is documented in code comments

**File:** `src/mcp_test_framework/ollama_judge.py:204-207`
**Issue:** The `escape`/`in_string` state machine in `_extract_first_json_object` is correct, but there is no unit test that exercises the `\\"` (escaped-quote inside a string) path. `_BRACE_IN_STRING` covers the "brace inside a string" case but not the "quote inside a string" case. A future refactor that drops the `escape` branch (incorrectly thinking it is dead) would not be caught by the current corpus.
**Fix:** Add a test case for an escaped quote in the reasoning string, e.g.:
```python
_ESCAPED_QUOTE = (
    r'{"passed": true, "score": 4, "reasoning": "say \"hi\"", "raw_response": ""}'
)

def test_extract_first_json_object_handles_escaped_quotes_in_strings() -> None:
    extracted = _extract_first_json_object(_ESCAPED_QUOTE)
    assert extracted == _ESCAPED_QUOTE
    result = _parse_judge_response(_ESCAPED_QUOTE)
    assert result.reasoning == 'say "hi"'
```

### IN-03: `print(f"judge result: {result!r}")` in smoke test is a debug artifact

**File:** `tests/smoke/test_smoke_ollama_judge.py:87`
**Issue:** The unconditional `print` at the end of the cold-start test pollutes pytest output and bypasses the project's `_log.debug` policy ("never the full Ollama response body by default" — `ollama_judge.py:43-45`). The docstring justifies it as "Diagnostic for cold-start UAT," but `pytest -s` or `--log-cli-level=DEBUG` is the conventional way to surface this.
**Fix:** Convert to a logger call gated on the same logger the production code uses, so it respects `--log-cli-level`:
```python
import logging
_log = logging.getLogger("mcp_test_framework.ollama_judge")
...
_log.info("cold-start judge result: %r", result)
```
Or, if the intent is to always print on success for verifier eyeballing, use `pytest`'s `capsys`/`capfd` plumbing or the `record_property` fixture so the value lands in JUnit XML rather than stdout.

### IN-04: smoke test docstring claims `httpx.ConnectError` fail-fast, but that requires entering `async with`

**File:** `tests/smoke/test_smoke_ollama_judge.py:17-19`
**Issue:** The module docstring says "If missing, the test fails fast inside the test body via `httpx.ConnectError` (transport error -- D-10 propagates)." But the first test (`test_judge_protocol_satisfied_by_ollama_judge`) never enters `async with`, so it cannot exercise the connect path. Only `test_cold_start_returns_valid_judge_result` would surface a `ConnectError`. The docstring is mildly misleading — it reads as if both tests fail fast on a missing Ollama, when in fact the protocol test will pass even with no Ollama running.
**Fix:** Tighten the docstring to scope the claim to the cold-start test:
```
Pre-req: Ollama reachable at cfg.ollama.base_url with cfg.ollama.model in
/api/tags. The cold-start test fails fast via httpx.ConnectError if missing
(transport error -- D-10 propagates). The Protocol-shape test does not
require a live Ollama and runs independently.
```

### IN-05: parser docstring mentions `JSONDecodeError` "as dead-code documentation" but the catch is not dead

**File:** `src/mcp_test_framework/ollama_judge.py:255-258`
**Issue:** The docstring says: "`json.JSONDecodeError` is a `ValueError` subclass; catching `(ValidationError, ValueError)` covers both. The D-09 wording mentions `JSONDecodeError` explicitly and is honored as dead-code documentation per Pydantic v2.13." This is slightly muddled — `JSONDecodeError` is *not* documented as dead code, it is *covered transitively* by the `ValueError` catch. The phrase "dead-code documentation" suggests the catch could be removed, but `(ValidationError, ValueError)` is exactly what catches it. A future maintainer reading "dead-code documentation" might trim the `ValueError` from the catch tuple thinking it's superfluous, breaking step 3 recovery for raw JSON syntax errors.
**Fix:** Reword the comment to make the dependency explicit:
```python
# Note: json.JSONDecodeError is a ValueError subclass; the (ValidationError,
# ValueError) tuple intentionally covers both Pydantic shape errors AND raw
# JSON syntax errors. Do NOT narrow the catch to ValidationError alone --
# step 3's brace-extracted retry depends on syntax errors flowing here too.
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
