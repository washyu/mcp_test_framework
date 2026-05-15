---
phase: 17-schema-driven-codegen-surface
plan: 01
subsystem: testing
tags: [pydantic, codegen, response-base, sdet, mcp, computed-field]

# Dependency graph
requires:
  - phase: pre-17
    provides: mcp.types.CallToolResult / TextContent, Pydantic v2, mcp_test_framework package layout
provides:
  - mcp_test_framework.sdet namespace (new public sub-package)
  - ToolResponse Pydantic v2 BaseModel with .raw / .data / .text / .is_error (CODEGEN-04, D-07)
  - CODEGEN-04 .data fallback chain pinned by 9 unit tests (Pitfall 7 + Pitfall 8 named)
affects:
  - 17-02 (codegen walker — emits per-tool Response classes that inherit from ToolResponse)
  - 17-03 (tool() factory — TypeVar bound to ToolResponse)
  - 17-04 (gen-sdet-classes generated `<Tool>Response` classes — pass-stub or typed fields)
  - 18 (mcp_session fixture — constructs ToolResponse(raw=...) at .call() runtime)
  - 18 UI-02 (ToolCallError consumes raw.isError separately; .data never short-circuits)

# Tech tracking
tech-stack:
  added: []  # zero new runtime deps; pyproject.toml unchanged
  patterns:
    - "Public sub-package re-export: src/mcp_test_framework/sdet/__init__.py re-exports ToolResponse only; future symbols (mcp_session, tool, requires_homelab) added one-phase-at-a-time"
    - "Pydantic v2 BaseModel with @computed_field @property for lazy derived views (D-07; distinct from frozen JudgeResult)"
    - "isinstance-filter pattern for heterogeneous content blocks (TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource) — Pitfall 7 guard"
    - "Test imports via PUBLIC re-export path (from mcp_test_framework.sdet import ToolResponse), pinning the public surface"

key-files:
  created:
    - "src/mcp_test_framework/sdet/__init__.py — public re-export of ToolResponse"
    - "src/mcp_test_framework/sdet/response.py — ToolResponse base class (CODEGEN-04 fallback chain)"
    - "tests/framework/unit/test_tool_response.py — 9 pure-sync unit tests pinning .data / .text / .is_error semantics"
  modified: []

key-decisions:
  - "ToolResponse shipped as Pydantic v2 BaseModel with @computed_field properties (D-07 verbatim from RESEARCH §Code Examples 1)"
  - "model_config = ConfigDict(arbitrary_types_allowed=True) — required because CallToolResult is an external (mcp.types) Pydantic model used as a field type"
  - "NOT frozen=True (D-07 explicitly distinguishes from JudgeResult — generated subclasses with typed fields may want mutability for test setup)"
  - "NOT extra='forbid' here — reserved for generated <Tool>Params per CONTEXT.md last bullet"
  - "data accessor breaks after FIRST TextContent attempt (CODEGEN-04 spec literal): second-or-later TextContent blocks are not re-attempted for JSON parsing"
  - ".data does NOT short-circuit on is_error=True (Pitfall 8); Phase 18 ToolCallError handles the error path. .data still returns whatever payload the server sent — pinned by test_data_does_not_check_is_error_pitfall_8"
  - ".text filters via isinstance(b, TextContent) — Pitfall 7. Naive iteration would AttributeError on ImageContent/AudioContent/ResourceLink/EmbeddedResource. Pinned by test_text_skips_non_text_blocks_pitfall_7"

patterns-established:
  - "sdet sub-package layout — src/mcp_test_framework/sdet/{__init__.py, response.py} is the surface; phases 18-20 will add mcp_session.py, tool.py, preflight.py alongside"
  - "Pitfall-named test pattern — test_text_skips_non_text_blocks_pitfall_7 / test_data_does_not_check_is_error_pitfall_8 carry the RESEARCH pitfall ID in the test name so a future refactor that reverts the guard immediately surfaces the named pitfall"
  - "Computed-field response model — base provides derived views; subclasses (generated in 17-04) add raw typed fields without overriding accessors"

requirements-completed: [CODEGEN-04]

# Metrics
duration: ~20min
completed: 2026-05-13
---

# Phase 17 Plan 01: ToolResponse Base Summary

**Pydantic v2 ToolResponse base ships .raw / .data / .text / .is_error with the locked CODEGEN-04 fallback chain (structuredContent → JSON-parse first TextContent → {"text": <concat>} → None) and Pitfall 7 isinstance-filter for non-text content blocks.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-13T01:49:00Z (approx — worktree reset + context load)
- **Completed:** 2026-05-13T02:08:55Z
- **Tasks:** 2
- **Files created:** 3 (sdet/__init__.py, sdet/response.py, tests/.../test_tool_response.py)
- **Files modified:** 0
- **Tests added:** 9 (all passing)
- **Lines added:** ~217 (47 sdet/__init__.py source incl. docstring + 70 sdet/response.py source + 101 test file)
- **Runtime deps added:** 0 (pyproject.toml unchanged)

## Accomplishments

- New public sub-package `mcp_test_framework.sdet` created; `from mcp_test_framework.sdet import ToolResponse` succeeds at import time.
- `ToolResponse` shipped as Pydantic v2 BaseModel with three `@computed_field @property` accessors (`is_error`, `text`, `data`) over a `raw: CallToolResult` field — verbatim from D-07 / RESEARCH §Code Examples 1.
- CODEGEN-04 `.data` fallback chain (4 steps) implemented and pinned by named unit tests covering all four branches.
- Pitfall 7 (heterogeneous content blocks must isinstance-filter) and Pitfall 8 (`.data` does NOT short-circuit on `is_error`) explicitly pinned by dedicated tests named after their pitfall ID.
- Public surface contract pinned: tests import via `from mcp_test_framework.sdet import ToolResponse` (not the internal `sdet.response` path), so a future internal rename can't silently break the public surface.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create sdet package + ToolResponse base class** — `0cc7935` (feat)
2. **Task 2: Pin ToolResponse fallback chain with unit tests** — `48f8f15` (test)

**Plan metadata:** _to be added by final metadata commit (this SUMMARY)_

## Files Created/Modified

- `src/mcp_test_framework/sdet/__init__.py` — public re-export of `ToolResponse` only; module docstring names the boundary that phases 18–20 extend (mcp_session, tool, requires_homelab) so future-add intent is documented next to the surface
- `src/mcp_test_framework/sdet/response.py` — `ToolResponse(BaseModel)` with `model_config = ConfigDict(arbitrary_types_allowed=True)`, `raw: CallToolResult`, and three `@computed_field @property` accessors. Module docstring enumerates decisions by ID (D-07, D-04, D-06) and references Pitfall 7 inline next to the `.text` accumulator
- `tests/framework/unit/test_tool_response.py` — 9 pure-sync tests; no `@pytest.mark.asyncio`, no fixtures; constructs `CallToolResult(...)` literals inline via a tiny `_result(...)` helper

## Decisions Made

All decisions were locked in 17-PLAN.md (no plan-time interpretation needed):

- **ToolResponse shape** — Pydantic v2 BaseModel with `@computed_field @property` (D-07). Locked verbatim from RESEARCH §Code Examples 1.
- **Mutability** — `model_config = ConfigDict(arbitrary_types_allowed=True)` only; NOT frozen, NOT `extra="forbid"`. D-07 explicitly distinguishes from `JudgeResult` (which IS frozen) because subclasses generated in 17-04 may want mutability for test setup, and `extra="forbid"` is reserved for generated `<Tool>Params` classes per CONTEXT.md.
- **`.data` step-2 single-shot** — Only the FIRST `TextContent` is JSON-parsed; if it fails or parses to a non-dict (list/scalar/null), the loop breaks and the algorithm falls through to step 3 (`{"text": <concat>}`). The literal comment `# only try the FIRST TextContent (CODEGEN-04 spec)` is in the source and an acceptance criterion grepped for it.
- **`.data` does NOT short-circuit on `is_error`** — Pitfall 8. Phase 18's `ToolCallError` is the typed-error path; `.data` is spec-literal. Documented in the `data` docstring and pinned by `test_data_does_not_check_is_error_pitfall_8`.

## Deviations from Plan

None — plan executed exactly as written. Source code, docstrings, and test names match the plan's `<action>` block character-for-character (with the exception of normal whitespace/line-ending differences inserted by the editor on Windows).

The CODEGEN-04 fallback chain, Pitfall 7 guard, and Pitfall 8 documentation all matched the RESEARCH-locked specification at first attempt; no auto-fix deviations were needed.

## Issues Encountered

**1. Write tool emitted files to the wrong path on first attempt**

- **Found during:** Task 1 verification
- **Issue:** The initial Write calls for `src/mcp_test_framework/sdet/__init__.py` and `src/mcp_test_framework/sdet/response.py` resolved to the **main repo root** (`C:/Users/washy/projects/mvp_test_framework/...`), NOT the worktree (`C:/Users/washy/projects/mvp_test_framework/.claude/worktrees/agent-aeb3c0786c4eff739/...`). This was discovered when `uv run python -c "from mcp_test_framework.sdet import ToolResponse"` failed with `ModuleNotFoundError` despite the files appearing to exist.
- **Fix:** Moved both files from main-repo path to worktree path via cp + rm; removed the stray `sdet/` from the main repo so its `git status` returns to its pre-execution state. All subsequent Write calls used fully-qualified absolute paths to the worktree.
- **Verification:** `ls src/mcp_test_framework/sdet/` in the worktree returns the two files; `git status` in the main repo no longer shows `sdet/` as untracked; `uv run python -c "from mcp_test_framework.sdet import ToolResponse; print('OK')"` succeeds in the worktree.
- **Lesson:** In a parallel worktree, every Write/Bash invocation must be unambiguously rooted at the worktree absolute path. Relative paths like `src/...` are not safe in a multi-worktree setup where the shell cwd is reset between tool calls.

**2. Existing `_session_needs_preflight` guard checks stale `tests/unit/` path (pre-existing baseline; not introduced by this plan)**

- **Found during:** Task 2 pytest verification
- **Issue:** `src/mcp_test_framework/fixtures.py:_session_needs_preflight` returns `True` for any test whose `nodeid` does not start with `tests/unit/`. Post-Phase 15 SURFACE split, unit tests live under `tests/framework/unit/`, so the guard never short-circuits and preflight fires (which then `pytest.exit(returncode=2)` on a missing `homelab-mcp` PATH binary or unreachable Ollama). This affects ALL existing unit tests in `tests/framework/unit/`, not just the new file added by this plan — confirmed by running `uv run pytest tests/framework/unit/test_ollama_judge.py` which fails identically.
- **Disposition:** **Out of scope for this plan.** This is a pre-existing baseline bug introduced by the Phase 15 folder split that was not caught at the time. Per the executor scope-boundary policy, only auto-fix issues DIRECTLY caused by the current task's changes — this is not one of them. Logging for a future quick task / Phase 17 follow-on plan.
- **Worked around (verification only):** Set `MCPTF_CONFIG_FILE=C:/Users/washy/projects/mvp_test_framework/config.yaml` (which points at the parent repo's real config with `homelab-mcp` via `uvx`) so preflight passes when running the verification command locally. The Ollama judge at `192.168.10.81:11434` was reachable so preflight succeeded. No production code path was modified.
- **Follow-up suggestion:** A one-line fix in `fixtures.py:_session_needs_preflight` — replace `nodeid.startswith("tests/unit/")` with `nodeid.startswith(("tests/unit/", "tests/framework/unit/"))` (or better: `not in nodeid.startswith` against an allowlist of "no-preflight-needed" prefixes). Worthy of a v1.3.x quick task entry but not a Plan 17-01 deviation.

## TDD Gate Compliance

This plan's frontmatter `type: execute` (not `type: tdd`), so plan-level TDD gate enforcement (RED-then-GREEN commit ordering) is not strictly required. Task 1 carries `tdd="true"` but Task 2 is the test-creation task — the plan deliberately structured this as `feat(17-01): ship ToolResponse` followed by `test(17-01): pin fallback chain`, not the canonical `test → feat → refactor` per-task TDD cycle. Both commit messages use conventional-commit prefixes (`feat` / `test`) so the gate sequence is observable in `git log` even if reversed from RED-first ordering.

- `feat(17-01): ship ToolResponse base for CODEGEN-04 SDET surface` — `0cc7935`
- `test(17-01): pin ToolResponse CODEGEN-04 fallback chain (9 unit tests)` — `48f8f15`

No REFACTOR commit needed (source landed clean against the RESEARCH-locked spec; no refactor pass was undertaken).

## Known Stubs

None. `ToolResponse` is a complete, executable class — no placeholders, TODOs, or empty defaults flow to a UI or caller. Subclasses (generated in Plan 17-04) will be the first place stubs might appear (per D-06: `pass`-body stubs when `outputSchema` is undeclared); that's by design and Phase 17-04's concern.

## Threat Flags

None. The plan's threat model (T-17.01-01..05) is fully addressed:

- **T-17.01-01 (Tampering — json.loads of server-controlled text):** `try/except (json.JSONDecodeError, ValueError)` wrapped; pinned by `test_data_falls_back_to_text_dict_when_json_parse_fails`.
- **T-17.01-02 (DoS — unbounded json.loads memory):** Accepted; bounded at the `call_tool` layer by `asyncio.timeout(timeout_seconds)` (already in `mcp_client.py:209`; not added by this plan).
- **T-17.01-03 (Info disclosure — error payload via .data):** Accepted per CODEGEN-04 spec; documented in `data` docstring and pinned by `test_data_does_not_check_is_error_pitfall_8`.
- **T-17.01-04 (Tampering — non-TextContent crash):** Mitigated via `isinstance(block, TextContent)` filter; pinned by `test_text_skips_non_text_blocks_pitfall_7`.
- **T-17.01-05 (Spoofing — arbitrary_types_allowed):** Accepted; Pydantic still validates the field type at construction (`raw: CallToolResult` rejects non-CallToolResult inputs with `ValidationError`).

No NEW security-relevant surface was introduced beyond what the plan's threat model already enumerated.

## User Setup Required

None — no external service configuration required.

The new `mcp_test_framework.sdet` namespace is internal Python API only; no env vars, no config keys, no dashboard work. The verification command (`uv run pytest tests/framework/unit/test_tool_response.py`) runs without homelab-mcp or Ollama once the pre-existing `_session_needs_preflight` baseline bug (see Issue 2 above) is worked around; with the bug present, the same `MCPTF_CONFIG_FILE` setup already required for all existing unit tests applies.

## Next Phase Readiness

**Plan 17-02 (codegen walker)** can now `from mcp_test_framework.sdet import ToolResponse` and emit per-tool `<ToolName>Response(ToolResponse): pass` stubs (D-06) or `<ToolName>Response(ToolResponse): field1: int; ...` typed subclasses without further plumbing.

**Plan 17-03 (tool() factory)** can now bind its response TypeVar to `ToolResponse`: `TR = TypeVar("TR", bound=ToolResponse)`.

**Plan 17-04 (gen-sdet-classes)** will write generated `<server_slug>/responses.py` files that `from mcp_test_framework.sdet.response import ToolResponse` and inherit.

**Phase 18 mcp_session fixture** will instantiate `ToolResponse(raw=<CallToolResult>)` at `.call()` runtime; the model already supports that constructor shape (validated by `ToolResponse.model_fields` containing `raw`).

**No blockers** for downstream phases.

## Self-Check: PASSED

Verified before final metadata commit:

- File `src/mcp_test_framework/sdet/__init__.py` exists in worktree: FOUND
- File `src/mcp_test_framework/sdet/response.py` exists in worktree: FOUND
- File `tests/framework/unit/test_tool_response.py` exists in worktree: FOUND
- Commit `0cc7935` (Task 1) in `git log`: FOUND
- Commit `48f8f15` (Task 2) in `git log`: FOUND
- `uv run pytest tests/framework/unit/test_tool_response.py -v`: 9 passed
- `uv run python -c "from mcp_test_framework.sdet import ToolResponse"`: OK
- `pyproject.toml dependencies` unchanged from base commit `d3a4c64`: VERIFIED (zero-diff)

---
*Phase: 17-schema-driven-codegen-surface*
*Plan: 01*
*Completed: 2026-05-13*
