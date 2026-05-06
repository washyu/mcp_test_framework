---
phase: 04-fixtures-test-cases
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/mcp_test_framework/rubrics.py
  - tests/unit/test_rubrics.py
  - src/mcp_test_framework/fixtures.py
  - tests/conftest.py
  - tests/test_homelab_list_registered_servers.py
findings:
  blocker: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-05
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 4 ships three deliverables: rubric models, session-scoped fixtures with a preflight gate, and ten integration tests against `homelab-mcp` / `list_registered_servers`. Code is generally well-structured: the rubric hardening preamble is a single source of truth and matches `ollama_judge.py`'s marker contract; the `_preflight` gate is correctly autouse session-scoped with a unit-test short-circuit; the black-box `sys.modules` guard is preserved; and tests do not import `homelab_mcp`.

No BLOCKER findings — none of the code paths inspected reach a guaranteed crash, security gap, or data-loss risk on the documented inputs. There are six WARNINGs worth addressing before shipping the framework as a reusable adopter seam, plus four INFO items.

Per the agent prompt's deferred-items list, two known issues are excluded from new findings:
- DEF-04-03-A: TEST-06 disambiguation score against `list_registered_servers` is a SUT signal, not a framework defect.
- DEF-04-03-B: Cancel-scope teardown error in the `mcp_client` fixture is tracked for Phase 04.1.

## Warnings

### WR-01: `_preflight` payload-shape assumption can crash with bare traceback (BLOCKER avoided)

**File:** `src/mcp_test_framework/fixtures.py:117-125`

**Issue:** The Ollama `/api/tags` response is parsed inside the try/except (line 117 `payload = resp.json()`), but the *use* of `payload` is OUTSIDE the try block:

```python
except Exception as exc:
    pytest.exit(...)

available_models = [m.get("name", "") for m in (payload.get("models") or [])]
```

If Ollama (or a misconfigured proxy) returns a JSON value that is not a dict — e.g. a list, a string, or `null` — `payload.get(...)` raises `AttributeError` and the whole `_preflight` fixture crashes with a raw traceback instead of emitting the structured single-line diagnostic the docstring promises (line 87 "single-line diagnostic naming the failed precondition"). Same risk if `payload["models"]` is non-iterable: list comprehension raises `TypeError`.

This is the exact failure mode FIX-02 / D-preflight-4 is designed to prevent ("No ERROR cascade across 10 tests").

**Fix:** Validate shape and route any failure through the same `pytest.exit(returncode=2)` path:

```python
try:
    async with httpx.AsyncClient(...) as client:
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        payload = resp.json()
    if not isinstance(payload, dict):
        raise TypeError(f"unexpected /api/tags shape: {type(payload).__name__}")
    models = payload.get("models") or []
    if not isinstance(models, list):
        raise TypeError(f"unexpected /api/tags 'models' shape: {type(models).__name__}")
    available_models = [m.get("name", "") for m in models if isinstance(m, dict)]
except Exception as exc:
    pytest.exit(
        f"Ollama at {config.ollama.base_url} not reachable: "
        f"{exc.__class__.__name__}: {exc}",
        returncode=2,
    )

if config.ollama.model not in available_models:
    pytest.exit(...)
```

---

### WR-02: `pytest.exit` diagnostic message can contain newlines, breaking the "single-line" contract

**File:** `src/mcp_test_framework/fixtures.py:104-106, 119-122, 142-145`

**Issue:** Every `pytest.exit` message includes `{exc}` interpolation. `httpx`/`asyncio`/MCP-SDK exception messages routinely contain embedded newlines (e.g. multi-line connect errors on Windows, MCP handshake stack traces). The docstring (line 87) promises "structured single-line diagnostic naming the failed precondition", and CI log scrapers downstream may grep for the prefix — embedded newlines break that.

**Fix:** Sanitize exception text before interpolation:

```python
def _one_line(exc: BaseException) -> str:
    return " | ".join(str(exc).splitlines())

pytest.exit(
    f"Ollama at {config.ollama.base_url} not reachable: "
    f"{exc.__class__.__name__}: {_one_line(exc)}",
    returncode=2,
)
```

---

### WR-03: `_preflight` swallows `pytest.exit` propagation paths via broad `except Exception`

**File:** `src/mcp_test_framework/fixtures.py:118, 141`

**Issue:** `except Exception as exc:` is too wide for a fixture body that re-emits via `pytest.exit`. Two concrete risks:

1. `KeyboardInterrupt` and `SystemExit` are correctly NOT caught (they're `BaseException`). OK.
2. `asyncio.CancelledError` in 3.11+ inherits from `BaseException`, so it's not swallowed either. OK.
3. **However**, an `Exception` from inside `httpx.AsyncClient.__aenter__` or `__aexit__` (TLS handshake bugs, DNS races) gets reported as "Ollama not reachable" even when the actual failure is a client-side bug. The diagnostic misleads operators.

This is a quality issue, not a correctness bug. The narrow set of expected exceptions is `httpx.HTTPError` (covers timeouts, connect errors, non-2xx) plus `ValueError` (JSON parse).

**Fix:** Narrow the except clause to the expected exception family, and let surprises propagate so they show up as a real test-runner traceback (which is more diagnostic than a misleading `pytest.exit` message):

```python
except (httpx.HTTPError, ValueError) as exc:
    pytest.exit(
        f"Ollama at {config.ollama.base_url} not reachable: "
        f"{exc.__class__.__name__}: {exc}",
        returncode=2,
    )
```

Same treatment for the MCP handshake block (line 134-146): catch the SDK's documented exception set rather than bare `Exception`.

---

### WR-04: TEST-04 assumes every property schema is a dict — JSON Schema 2020-12 also allows boolean schemas

**File:** `tests/test_homelab_list_registered_servers.py:80-86`

**Issue:**

```python
for prop_name, prop_schema in properties.items():
    assert prop_schema.get("description"), ...
```

JSON Schema Draft 2020-12 (which MCP tool schemas use, per the `Draft202012Validator` import in the same file) permits boolean schemas: `{"properties": {"x": true}}` is valid. `True.get(...)` raises `AttributeError`, producing an `ERROR` instead of a `FAIL`.

This is unlikely against `homelab-mcp` today, but the test claims to be a generic deterministic schema check (TEST-04 description), so it should fail cleanly rather than crash on a legal-but-degenerate schema.

**Fix:** Treat non-dict property schemas as a TEST-04 failure (they cannot have a description):

```python
for prop_name, prop_schema in properties.items():
    assert isinstance(prop_schema, dict), (
        f"param {prop_name!r} property schema is not a dict: {prop_schema!r}"
    )
    assert prop_schema.get("description"), ...
    assert any(k in prop_schema for k in ("type", "oneOf", "anyOf")), ...
```

---

### WR-05: TEST-10 silently passes when no `TextContent` blocks exist at all

**File:** `tests/test_homelab_list_registered_servers.py:198-217`

**Issue:** The "JSON parses" loop only counts blocks that have a `text` attribute:

```python
for block in (result.content or []):
    text = getattr(block, "text", None)
    if text is None:
        continue
    attempts.append(text)
    ...
if not parsed_any:
    pytest.fail(...)
```

If `result.content` is `[]` or contains zero text blocks (only image/resource blocks), `attempts` stays empty AND `parsed_any` stays `False`, so `pytest.fail` does fire — that's correct.

But the failure message reports `len(attempts)` — which is `0` — making the diagnostic ambiguous: was the issue zero text blocks, or zero text blocks that parsed as JSON? TEST-10's docstring says ">=1 TextContent block parses as JSON", so the test should distinguish.

This is a quality / diagnostic finding, not a correctness bug.

**Fix:** Distinguish "no text blocks" from "text blocks didn't parse":

```python
if not attempts:
    pytest.fail(
        f"No TextContent blocks in result.content (len={len(result.content or [])}); "
        f"cannot test JSON parseability"
    )
if not parsed_any:
    truncated = [a[:200] + ("..." if len(a) > 200 else "") for a in attempts]
    pytest.fail(
        f"No TextContent block parsed as JSON. "
        f"attempts ({len(attempts)} blocks): {truncated!r}"
    )
```

---

### WR-06: `_session_needs_preflight` short-circuit relies on a fragile path-prefix string

**File:** `src/mcp_test_framework/fixtures.py:57-74`

**Issue:** The unit-test detection uses `item.nodeid.startswith("tests/unit/")`. Three failure modes:

1. If a contributor moves unit tests under `tests/unit_tests/` or splits them across `tests/unit/` AND `tests/lint/` (e.g. `tests/lint/test_banned_imports.py` — there is already a `tests/unit/test_banned_imports.py` so this is plausible), the new directory triggers preflight unnecessarily and unit-test runs require Ollama.
2. The comment says "item.nodeid uses forward slashes on every platform pytest supports" — true today, but it's an undocumented pytest internal. A more robust check uses `pathlib.PurePosixPath(item.nodeid).parts`.
3. There is no test in `tests/unit/test_rubrics.py` that locks this behavior — a future refactor of the prefix would silently regress the "unit tests pass without Ollama" Plan 04-02 Task 3 acceptance.

**Fix:** Either (a) use a marker-based check (`item.get_closest_marker("integration")`) and tag integration tests, or (b) lift the prefix to a module constant and add a unit test that asserts the short-circuit returns `False` when only `tests/unit/...` nodeids are present:

```python
_UNIT_TEST_PREFIX = "tests/unit/"

def _session_needs_preflight(request) -> bool:
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    return any(not item.nodeid.startswith(_UNIT_TEST_PREFIX) for item in items)
```

Then add a unit test using a fake `request.session` with stub items.

---

## Info

### IN-01: `Rubric.__str__` recomputes the same string on every call — minor allocation hot path

**File:** `src/mcp_test_framework/rubrics.py:56-63`

**Issue:** Each judge call passes `str(rubric_clarity)`, `str(rubric_disambiguation)`, `str(rubric_parameters)`. The rubrics are session-scoped, frozen, and the `__str__` output is fixed at instance-construction time. Computing the join on every call is wasteful — though performance is explicitly out of v1 review scope, this is also a *clarity* issue: a reader expects "frozen + fixed inputs" to imply "computed once".

**Fix (optional):** Cache via `functools.cached_property` on a private `_rendered` attribute, or compute in `model_post_init`. Not required for MVP.

---

### IN-02: `tests/conftest.py` `noqa: E402` is correct but non-obvious; brief inline note would help readers

**File:** `tests/conftest.py:14`

**Issue:** `import sys  # noqa: E402` after `pytest_plugins = [...]` works because `pytest_plugins` is a literal binding pytest discovers via AST. The comment after `noqa: E402` ("pytest_plugins must be a top-level statement") explains *why* the import is below `pytest_plugins`, but a casual reader may still wonder why the import isn't simply moved to the top. The current ordering is correct — `pytest_plugins` is the first non-docstring statement, which some style guides prefer for pytest registration.

**Fix:** No code change needed. Optional: expand the comment to "pytest_plugins must be the first top-level statement (pytest convention); imports follow."

---

### IN-03: `_LoggerWriter` in `mcp_client.py` is dead code (per its own comment)

**File:** `src/mcp_test_framework/mcp_client.py:64-99`

**Issue:** Out of scope for this phase but surfaced because `mcp_client.py` is reachable from the fixture review. The class is documented as not currently wired (line 64-69) and is exercised only by unit tests. This is acceptable as a "seed" but is dead code today and mildly inflates the surface area readers must understand.

**Fix:** No change required for Phase 4. Track for a future cleanup or move to a `_drafts/` subpackage.

---

### IN-04: TEST-10 uses `getattr(target_tool, "outputSchema", None)` defensively, but `Tool.outputSchema` is a Pydantic field

**File:** `tests/test_homelab_list_registered_servers.py:220`

**Issue:** `mcp.types.Tool` declares `outputSchema: dict[str, Any] | None` as a real Pydantic field. The `getattr` defense suggests uncertainty about the SDK's API surface. Either:
- the author is hedging against an older SDK version (in which case the project should pin a min version), or
- direct attribute access (`target_tool.outputSchema`) is clearer.

**Fix:** Use direct attribute access; let an `AttributeError` surface as a real signal that the SDK contract changed:

```python
output_schema = target_tool.outputSchema
if result.structuredContent is not None and output_schema:
    Draft202012Validator(output_schema).validate(result.structuredContent)
```

---

_Reviewed: 2026-05-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
