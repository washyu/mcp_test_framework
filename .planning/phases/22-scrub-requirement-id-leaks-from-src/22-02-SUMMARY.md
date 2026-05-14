---
phase: 22-scrub-requirement-id-leaks-from-src
plan: 02
subsystem: sdet-package
tags: [scrub, comments, docstrings, sdet]
requires:
  - plan: 22-01
provides:
  - "src/mcp_test_framework/sdet/ free of planning-ID leakage (locked regex + Phase NN)"
affects:
  - src/mcp_test_framework/sdet/__init__.py
  - src/mcp_test_framework/sdet/session.py
  - src/mcp_test_framework/sdet/_tool_factory.py
  - src/mcp_test_framework/sdet/response.py
  - src/mcp_test_framework/sdet/errors.py
  - src/mcp_test_framework/sdet/_codegen.py
  - src/mcp_test_framework/sdet/_slugs.py
  - tests/framework/unit/test_tool_factory.py
tech-stack:
  added: []
  patterns:
    - "Comment policy: drop pure-provenance, rewrite rationale-bearing preserving the constraint, cite only docs/SDET-AUTHORING.md / CLAUDE.md anchors"
key-files:
  created:
    - .planning/phases/22-scrub-requirement-id-leaks-from-src/22-02-SUMMARY.md
  modified:
    - src/mcp_test_framework/sdet/__init__.py
    - src/mcp_test_framework/sdet/session.py
    - src/mcp_test_framework/sdet/_tool_factory.py
    - src/mcp_test_framework/sdet/response.py
    - src/mcp_test_framework/sdet/errors.py
    - src/mcp_test_framework/sdet/_codegen.py
    - src/mcp_test_framework/sdet/_slugs.py
    - tests/framework/unit/test_tool_factory.py
decisions:
  - "Sweep all 7 files in src/mcp_test_framework/sdet/ in one plan, two tasks split by public-seam vs internal"
  - "Apply per-site decision tree (drop vs rewrite) verbatim — no allowlist, no noqa"
  - "Drop one test assertion in tests/framework/unit/test_tool_factory.py that pinned on the scrubbed 'Phase 18' literal in a runtime error message (Rule 3 — required by the plan's verification block)"
metrics:
  duration: "~25min"
  completed: "2026-05-14"
requirements:
  - SCRUB-SRC-01
---

# Phase 22 Plan 02: Scrub SDET package — Summary

Scrubbed `src/mcp_test_framework/sdet/` (7 files) of every planning-system tag matching the locked regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b` plus every `Phase \d+(\.\d+)?` prefix. Comments and docstrings were rewritten per the D-02 per-site decision tree; behavior is preserved end-to-end (92/92 unit tests pass across the listed verification subset).

## Per-File Hit Counts

| File | Locked regex (before -> after) | Phase NN (before -> after) |
|------|-------------------------------:|---------------------------:|
| `__init__.py`      |  7 -> 0 |  6 -> 0 |
| `session.py`       |  8 -> 0 |  5 -> 0 |
| `_tool_factory.py` | 11 -> 0 | 21 -> 0 |
| `response.py`      |  9 -> 0 |  4 -> 0 |
| `errors.py`        |  5 -> 0 |  2 -> 0 |
| `_codegen.py`      | 21 -> 0 |  7 -> 0 |
| `_slugs.py`        |  1 -> 0 |  2 -> 0 |
| **Total**          | **62 -> 0** | **47 -> 0** |

Plan baseline estimated 67 ID hits and ~50 Phase prefixes; the live `grep -c` against the unscrubbed files showed 62 + 47 (some lines double-matched). Final state: zero across the board.

## Non-Trivial Rewrite Decisions

### `__init__.py` module docstring
The pre-scrub docstring was a chronological "Phase 17 ships X / Phase 18 adds Y / Phase 20 will add Z" enumeration. Replaced with a present-tense description of the public surface (`ToolResponse`, `mcp_session`, `tool`, `ToolCallError`) and a single anchor to `docs/SDET-AUTHORING.md`. This is the docstring `help(mcp_test_framework.sdet)` displays, so the prose was chosen for SDET-facing clarity.

### `_tool_factory.py` "Locked invariants" block
The pre-scrub module docstring had a `D-09: ...` enumerated invariants block plus separate "Phase 17 shipped X / Phase 18 will wire Y" history. Rewrote into a single "Locked invariants" section with no D-NN prefixes (the invariants themselves survive: stringly-typed surface, no attribute-access namespace, `ToolWrapper` Generic for IDE completion). Dropped the chronological history; the dispatch shape is documented as the present-day contract. `_ACTIVE_CLIENT` slot rationale ("mutated only by `mcp_session` in `session.py`") preserved as load-bearing maintainer note.

### `errors.py` `_extract_code_message` heuristic chain
This was the explicit "ORDER is a regression-pinned invariant" rewrite called out in the plan's `<interfaces>` section. Kept the full ordered list of fallback steps verbatim in both the module docstring and the `_extract_code_message` function docstring. Dropped the `D-08:` anchor prefix on both. The recognized-key-set rule (only "code" / "message", no synonyms, no recursive walk), the `str()`-coercion for non-string code values, and the "non-string message falls through to next step" semantics all survived in prose.

### `session.py` 5-step registry-activation
The pre-scrub docstring had `D-01 / D-02 / D-03` enumerated steps mixed with `Phase 18 SDET-03, Phase 21.1 RELOC-02` provenance and a `Phase 04.1 invariant: the D-02 mutations are SYNC ...` line. Rewrote as a clean 5-step list (read serverInfo, derive slug, locate generated package, load via `spec_from_file_location`, install slots) plus a separate "Invariant" paragraph explaining the sync-mutation property without any `Phase 04.1 / D-02` anchors. The pinned-at reference (`tests/framework/unit/test_sdet_fixtures.py::test_session_module_opens_no_anyio_cancel_scope`) is a code-pin reference and is preserved — that's the test that enforces the invariant, not a planning-doc anchor.

### `_codegen.py` field-emission rationale comments
The bulk of the 21 ID hits in `_codegen.py` were `WR-N` / `CR-N` reviewer-issue tags on rationale-bearing comments explaining why a particular substring-scan was replaced by a structured signal. Each such comment was rewritten to preserve the bug-it-fixes rationale (e.g. "false-positived on descriptions containing 'default=None'") without naming the WR/CR ticket. The orphaned-import rationale (`uses_typing_any` / `has_fields` structured signals avoid the `"typing." in body_text` false-positive trap) survives as load-bearing prose.

### `response.py` design-choice comments
`D-04: pyright is the static-type-check verifier; this module must be pyright-strict-clean` collapsed into a top-level docstring note ("This module must stay pyright-strict-clean."). `D-06: stub when undeclared` and `D-07: Pydantic v2 BaseModel with @computed_field properties` rewritten as constraint statements without anchor prefixes. The four-property surface (`.raw / .data / .text / .is_error`) survives in the prose because that IS the public API.

## Deviation: Test-File Edit

`tests/framework/unit/test_tool_factory.py::test_call_raises_runtime_error_when_no_active_client` asserted on the literal string `"Phase 18"` in the `RuntimeError` message raised by `_tool_factory.tool().call()` when `_ACTIVE_CLIENT` is `None`. That string was the planning-ID leak in `_tool_factory.py` that the scrub removed. Dropped the single `assert "Phase 18" in msg` line. The other three assertions (`"no active MCP client"`, `"mcp_session"`, `"tests/sdet/"`) still pin on the substantive operator-facing contract.

This was a Rule 3 deviation: `tests/` is out of scope per the phase CONTEXT.md ("test code can name the planning IDs it pins; scrub is `src/`-only"), but the plan's `<verification>` block explicitly listed `test_tool_factory.py` as required-to-pass. Test-debt of this exact shape is what Phase 23 will sweep, but a single one-line drop is consistent with the spirit of the scrub: a test should not pin on a planning ID that violates the locked regex policy.

## Verification

- Locked-regex `grep -crE` across `src/mcp_test_framework/sdet/ --include="*.py"`: **0 hits in 7 files** (post-scrub).
- `Phase NN(.M)?` `grep -crE` across `src/mcp_test_framework/sdet/ --include="*.py"`: **0 hits in 7 files** (post-scrub).
- `uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError; from mcp_test_framework.sdet.response import ToolResponse; print('ok')"`: prints `ok`.
- `uv run pytest tests/framework/unit/test_sdet_fixtures.py tests/framework/unit/test_sdet_conftest_hook.py tests/framework/unit/test_codegen_emitter.py tests/framework/unit/test_codegen_walker.py tests/framework/unit/test_codegen_integration_mock.py tests/framework/unit/test_tool_factory.py -q`: **92 passed in 0.31s**.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `fd3f423` | refactor(22-02): scrub planning IDs from SDET public-seam files (`__init__.py`, `session.py`, `_tool_factory.py`) |
| 2 | `8d6aef7` | refactor(22-02): scrub planning IDs from SDET internal files (`response.py`, `errors.py`, `_codegen.py`, `_slugs.py`) |
| 2-fix | `8746a04` | fix(22-02): drop Phase 18 pin in `test_call_raises_runtime_error_when_no_active_client` |

## Threat Flags

None introduced. This plan edits comments and docstrings only — no new network surface, no auth changes, no schema changes, no executable behavior changes. The `T-22-06` import-DoS mitigation was applied: import sanity command run after each task and exited 0.

## Self-Check: PASSED

- All 7 SDET files exist and contain 0 hits for the locked regex and 0 `Phase NN` prefixes (verified via `grep -crE`).
- All three commits (`fd3f423`, `8d6aef7`, `8746a04`) present in `git log --oneline HEAD -5`.
- All 92 listed unit tests pass.
