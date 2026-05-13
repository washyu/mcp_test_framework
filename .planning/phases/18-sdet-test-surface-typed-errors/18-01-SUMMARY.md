---
phase: 18-sdet-test-surface-typed-errors
plan: 01
subsystem: sdet
tags: [sdet, errors, typed-exceptions, UI-02, D-07, D-08]
requires: []
provides:
  - "mcp_test_framework.sdet.errors.ToolCallError (plain Exception subclass)"
  - "mcp_test_framework.sdet.errors._extract_code_message (D-08 strict heuristic)"
affects:
  downstream:
    - "Plan 18-02 (_tool_factory.py wire body) imports both symbols"
    - "Plan 18-04 (sdet/__init__.py re-exports) adds ToolCallError to public surface"
    - "Plan 18-05 (tests/sdet/conftest.py) catches ToolCallError in pytest_exception_interact"
    - "Plan 18-07 (_runner.py JUnit XML parser) reads ToolCallError-attached user_properties"
tech_stack:
  added: []
  patterns:
    - "sibling-module convention (one operator-visible class per file, response.py style)"
    - "Pitfall 7 TextContent filter (isinstance(block, TextContent) on every content iteration)"
key_files:
  created:
    - src/mcp_test_framework/sdet/errors.py
  modified: []
decisions:
  referenced:
    - "D-07: ToolCallError is plain Exception, NOT Pydantic (traceback-friendly, zero-overhead)"
    - "D-08: strict 'code'/'message' key recognition; non-string code coerced via str(); non-string message falls through"
metrics:
  tasks_completed: 1
  files_created: 1
  files_modified: 0
  loc_added: 97
  completed_date: "2026-05-13"
---

# Phase 18 Plan 01: errors module Summary

`ToolCallError` typed exception (UI-02 / D-07) and its companion `_extract_code_message` heuristic helper (D-08) shipped as a sibling module to `response.py` under `src/mcp_test_framework/sdet/`.

## What Was Built

One new file: `src/mcp_test_framework/sdet/errors.py` (97 LOC, pyright-strict-clean).

### `ToolCallError(Exception)` — D-07 verbatim

Plain `Exception` subclass with keyword-only `__init__` taking `tool` / `code` / `message` / `raw`. Stores all four on `self`; passes `self._format_default()` to `super().__init__(...)`. `_format_default()` returns `f"[{self.code}] {self.message}"` when `self.code` is truthy, otherwise the bare `self.message`.

Symmetric with the renderer's FAIL row format (Phase 18 D-10): `str(ToolCallError(...))` matches what the operator will see in the domain UI under `--explain` / `--debug`.

Plain Exception (not Pydantic) for:
- traceback-friendly pytest integration,
- the standard `except ToolCallError as e:` idiom,
- zero runtime overhead,
- `.raw` is the live `mcp.types.CallToolResult`, not a Pydantic clone.

### `_extract_code_message(raw) -> tuple[str | None, str]` — D-08 verbatim

Three-step strict heuristic chain:

1. **`raw.structuredContent` dict** — read `code` and `message` keys. Returns only when `isinstance(message, str)`; coerces `code` via `str(...)` (so `code: 404` becomes `"404"`).
2. **First `TextContent.text`** — attempt `json.loads(...)`; if the result is a dict with a string `message`, return; otherwise `break` immediately (only the first `TextContent` is inspected, per D-08).
3. **Concat fallback** — `"".join(b.text for b in raw.content if isinstance(b, TextContent))`, `code=None`.

**Strict key set:** only `code` and `message` are recognized. Alternative names are NOT accepted. NO recursive walk. **Pitfall 7 honored** on both step 2 (`isinstance(block, TextContent)`) and step 3 (`isinstance(b, TextContent)`), preventing `AttributeError` against heterogeneous content blocks (`ImageContent` / `AudioContent` / `ResourceLink` / `EmbeddedResource`).

## Downstream Import Target Stabilized

Wave 1 ships first so the rest of Phase 18 has a stable import target. After this plan merges:

- `_tool_factory.py` (Plan 18-02) imports `ToolCallError` + `_extract_code_message` and raises the former when `result.isError` is True.
- `sdet/__init__.py` (Plan 18-04) re-exports `ToolCallError` for the public `from mcp_test_framework.sdet import ToolCallError` operator-facing surface (`_extract_code_message` stays internal-but-importable via the leading underscore).
- `tests/sdet/conftest.py` (Plan 18-05) catches `ToolCallError` in `pytest_exception_interact` and stashes `(code, message)` onto `report.user_properties` for the JUnit XML writer.
- `_runner.py` JUnit parser (Plan 18-07) reads `mcptf_error_code` / `mcptf_error_message` properties and feeds the em-dash FAIL row's `failure_message`.

## Decisions Referenced

- **D-07** (Phase 18 CONTEXT.md lines 79–99): `ToolCallError` signature verbatim. No deviations.
- **D-08** (Phase 18 CONTEXT.md lines 102–107 / PATTERNS.md lines 196–222): heuristic chain verbatim. Step 2 `break` after first `TextContent` honored. Strict `code`/`message` key set enforced (no alternative names, no recursion).

## Verification

| Check | Result |
|-------|--------|
| `grep -c "class ToolCallError(Exception)"` | 1 |
| `grep -c "def _extract_code_message"` | 1 |
| `grep -c "from mcp.types import CallToolResult, TextContent"` | 1 |
| `grep -c "isinstance(block, TextContent)"` (step 2 filter) | 2 |
| `grep -c "isinstance(b, TextContent)"` (step 3 filter) | 1 |
| `grep -c "break"` (step 2 early termination) | 1 |
| `grep -cE 'errorCode\|detail\|reason\|"error"'` (strict key set) | 0 |
| `grep -c "BaseModel"` (D-07 plain Exception) | 0 |
| `grep -cE "str\(code\)"` (non-string code coercion) | 2 |
| `grep -cE "f.\[\{self\.code\}\] \{self\.message\}."` (D-07 format string) | 1 |
| `uv run python -c "from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message"` | exit 0 |
| Plan smoke test (`str(e) == '[X] m'`, code=None bare, Exception subclass, no `model_dump`) | OK |
| `uv run pyright src/mcp_test_framework/sdet/errors.py` | 0 errors, 0 warnings, 0 informations |
| Full D-08 case sweep (step 1, step 1 coercion, step 1 missing message, step 2, step 2 non-dict, step 3, step 3 multi-text, step 3 mixed types, strict key set fall-through) | all green |
| Pitfall 7 mixed-content case (TextContent + ImageContent) | passes, returns `(None, 'a')` |

## Threat Model Compliance

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-18-01 (Tampering on `json.loads`) | mitigate | Step 2 wraps `json.loads` in `try/except (json.JSONDecodeError, ValueError)`; falls through to step 3 on any parse failure. Never re-raises. |
| T-18-02 (DoS on concat) | accept | Step 3 concat bounded by `CallToolResult` size; O(N) over content blocks. |
| T-18-03 (Info disclosure via `.raw`) | accept | `.raw` is the full `CallToolResult` by design — SDETs need full visibility. |
| T-18-04 (Elevation) | accept | Pure data extraction; no privileged operations. |

## Deviations from Plan

### Minor — Docstring rewording for grep-discipline

The original module docstring contained literal forbidden-token strings (`"error"`, `"errorCode"`, `"detail"`, `"reason"`, `BaseModel`) inside negative-statement explanatory prose ("NO synonyms (no 'error', 'detail', ...)" and "NOT Pydantic BaseModel"). These were caught by the plan's acceptance-criteria `grep -c` checks, which scan the file for these tokens without distinguishing prose from code.

**Fix (Rule 1 — bug):** Rephrased the docstring to convey the same meaning without using the forbidden tokens literally:
- "NOT Pydantic BaseModel" → "NOT a Pydantic model"
- "NO synonyms (no 'error', 'detail', 'reason', 'errorCode')" → "the recognized key set is strictly those two keys; alternative names are NOT accepted"

**Files modified:** `src/mcp_test_framework/sdet/errors.py` (docstring only, no code change).
**Commit:** rolled into the single task commit (286361a).
**Tracked as:** `[Rule 1 - Bug] grep-discipline alignment with acceptance criteria`. The acceptance criteria are mechanical guards meant to catch a coder slipping synonyms into the heuristic; the rewording preserves their integrity without weakening the module's self-documentation.

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/errors.py` — FOUND
- commit `286361a` — FOUND (`git log --oneline -1` shows `286361a feat(18-01): add ToolCallError + _extract_code_message (UI-02 D-07/D-08)`)
