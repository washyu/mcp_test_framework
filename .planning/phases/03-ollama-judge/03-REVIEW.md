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
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 3: Code Review Report (Re-Review)

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Re-review of the Phase 3 implementation after fixes for prior WR-01..WR-04
landed in commits `f12bcf2` (WR-01), `64058b2` (WR-02), `c7c1ca8` (WR-03),
and `48c4c21` (WR-04). All four prior WARNING findings have been properly
resolved against the live source — verified line-by-line below.

One incidental WARNING surfaces during re-review (WR-05): the WR-02 fix
correctly defends `data["message"]["content"]` against shape failures
**after** `response.json()` succeeds, but `response.json()` itself can still
raise `json.JSONDecodeError` on a 2xx-but-non-JSON body (HTML error page
from a misbehaving proxy, empty body, etc.). This is the same class of
defect that motivated WR-02 and the same docstring contract still applies:
"Malformed-content failures (valid 2xx response but unparseable body) fall
through the four-step defensive parser" — but a non-JSON 2xx body bypasses
the parser today.

Of the prior five INFO items, two (IN-01, IN-05) are resolved transitively
by the WR-03 / WR-04 commits; three (IN-02, IN-03, IN-04) remain pending.

No BLOCKER defects found.

## Verification of Prior Findings

| ID    | Status   | Evidence                                                                                       |
|-------|----------|------------------------------------------------------------------------------------------------|
| WR-01 | RESOLVED | `ollama_judge.py:369-373` — `assert` replaced with `if self._client is None: raise RuntimeError(...)`; survives `python -O`. |
| WR-02 | RESOLVED | `ollama_judge.py:395-400` — envelope shape guarded with `isinstance(data, dict)` / `isinstance(message, dict)` / `isinstance(content, str)`; falls through to `_parse_judge_response(response.text)`. |
| WR-03 | RESOLVED | `ollama_judge.py:173, 188-195` — `_FENCE_RE` (with `$` anchor) replaced by `_FENCE_OPEN_RE` plus `rpartition("```")`; no end-of-string brittleness. |
| WR-04 | RESOLVED | `ollama_judge.py:280, 288, 290-292, 295` — DEBUG record on every parser branch; plus `done_reason` / `load_duration` / `eval_duration` logged at `405-412`. |
| IN-01 | RESOLVED (transitive) | `_FENCE_RE` no longer exists; replacement `_FENCE_OPEN_RE` at `:173` uses only `re.IGNORECASE`. |
| IN-02 | PENDING  | `tests/unit/test_ollama_judge.py` — no `_ESCAPED_QUOTE` test case for the brace-scanner `escape` branch. |
| IN-03 | PENDING  | `tests/smoke/test_smoke_ollama_judge.py:87` — `print(f"judge result: {result!r}")` still present. |
| IN-04 | PENDING  | `tests/smoke/test_smoke_ollama_judge.py:17-19` — docstring still implies both tests fail fast on missing Ollama. |
| IN-05 | PENDING  | `ollama_judge.py:269-272` — "dead-code documentation" wording still present, still misleading. |

## Warnings

### WR-05: `response.json()` on a 2xx-but-non-JSON body bypasses the defensive parser

**File:** `src/mcp_test_framework/ollama_judge.py:386`
**Issue:** The WR-02 fix (commit `64058b2`) correctly guards every
`data["message"]["content"]` dereference, but the line immediately above —
`data = response.json()` — can still raise `json.JSONDecodeError` when the
2xx body is not valid JSON at all. Real-world cases:

- A reverse-proxy/middleware returns an HTML error page with status 200
  (sniffed-content-type defaults).
- A misconfigured ngrok / cloudflare tunnel rewrites the body.
- Ollama's `/api/chat` is hit when only `/v1/chat/completions` is
  proxied — the proxy serves an HTML 200 with the OpenAPI route list.

The docstring contract at `ollama_judge.py:366-367` says: "Malformed-content
failures (valid 2xx response but unparseable body) fall through the
four-step defensive parser (D-09) and return a `passed=False` JudgeResult
with `raw_response` preserved." A non-JSON 2xx body is the canonical
"unparseable body" case but bypasses the parser today and surfaces as a
raw `json.JSONDecodeError` traceback in the test output — exactly the
debuggability problem WR-02 was solving for envelope-shape failures.

This is a small surface-area extension of WR-02, not a deep design issue.
**Fix:** Wrap the JSON parse in a try/except that routes the same way the
envelope-shape failures do:
```python
response = await self._client.post("/api/chat", json=body)
response.raise_for_status()  # D-10: 4xx/5xx propagates as httpx.HTTPStatusError
try:
    data = response.json()
except ValueError:
    # Non-JSON 2xx body (proxy HTML, empty body, etc.) -- same docstring
    # contract as malformed envelope: route through the four-step parser
    # so raw_response is preserved and operators see the actual body.
    return _parse_judge_response(response.text)

message = data.get("message") if isinstance(data, dict) else None
...
```
A unit test covering this would mock `httpx` to return 200 with body
`<html>Bad Gateway</html>` and assert the locked fallback `JudgeResult`.

## Info

### IN-02 (carried forward): missing test for escaped-quote brace-scanner branch

**File:** `tests/unit/test_ollama_judge.py`
**Issue:** The `escape`/`in_string` state machine in
`_extract_first_json_object` (`ollama_judge.py:215-225`) is correct but
not exercised by any unit test. `_BRACE_IN_STRING` covers braces inside a
string; nothing covers `\"` (escaped quote inside a string). A future
refactor that drops the `escape` branch as "dead" would not be caught.
**Fix:**
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

### IN-03 (carried forward): stray `print` in smoke test

**File:** `tests/smoke/test_smoke_ollama_judge.py:87`
**Issue:** Unconditional `print(f"judge result: {result!r}")` pollutes
pytest output and bypasses the production module's "never the full Ollama
response body by default" logging policy
(`src/mcp_test_framework/ollama_judge.py:42-45`).
**Fix:** Convert to a logger call so the verifier can opt in via
`--log-cli-level`:
```python
import logging
_log = logging.getLogger("mcp_test_framework.ollama_judge")
...
_log.info("cold-start judge result: %r", result)
```
Or use `record_property` so the value lands in JUnit XML rather than
stdout.

### IN-04 (carried forward): smoke docstring overstates fail-fast behaviour

**File:** `tests/smoke/test_smoke_ollama_judge.py:17-19`
**Issue:** The module docstring claims "If missing, the test fails fast
inside the test body via `httpx.ConnectError`" — but
`test_judge_protocol_satisfied_by_ollama_judge` never enters `async with`
and so cannot exercise the connect path. The Protocol-shape test passes
even when no Ollama is reachable.
**Fix:** Tighten the wording to scope the claim:
```
Pre-req: Ollama reachable at cfg.ollama.base_url with cfg.ollama.model in
/api/tags. The cold-start test fails fast via httpx.ConnectError if missing
(transport error -- D-10 propagates). The Protocol-shape test does not
require a live Ollama and runs independently.
```

### IN-05 (carried forward): "dead-code documentation" comment is misleading

**File:** `src/mcp_test_framework/ollama_judge.py:269-272`
**Issue:** The docstring says: "`json.JSONDecodeError` is a `ValueError`
subclass; catching `(ValidationError, ValueError)` covers both. The D-09
wording mentions `JSONDecodeError` explicitly and is honored as dead-code
documentation per Pydantic v2.13." `ValueError` is **not** dead — it
actively catches `JSONDecodeError`. A future maintainer trimming the
catch tuple to `ValidationError` only (thinking `ValueError` is dead) would
break step-3 brace-recovery on raw JSON syntax errors.
**Fix:** Reword the comment so the dependency is explicit:
```python
# Note: json.JSONDecodeError is a ValueError subclass; the
# (ValidationError, ValueError) tuple intentionally covers both Pydantic
# shape errors AND raw JSON syntax errors. Do NOT narrow the catch to
# ValidationError alone -- step 3's brace-extracted retry depends on
# syntax errors flowing here too.
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
