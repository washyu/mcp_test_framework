---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 02
subsystem: cli-error-mapper
tags: [error-style, operator-tone, pydantic-validation, isol-01]
requires:
  - "34-01 (Config.host_isolation Literal field + Pydantic literal_error shape on typo)"
provides:
  - "cli.py:_emit_operator_error_for_validation branch keyed on (literal_error, ('host_isolation',))"
  - "Verbatim operator-tone three-part rejection text consumed by docs plan 34-08"
  - "Library-mode persona inherits the new branch automatically via _plugin.py's lazy import"
affects:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_error_style.py
tech_stack_added: []
tech_stack_patterns:
  - "Scan-all-errors-then-emit dispatcher branch (matches existing sdet_err / version_err idiom in cli.py)"
  - "Operator-tone three-part contract (summary / detail / next_step) -- contract pinned by tests/framework/unit/test_error_style.py"
key_files_created: []
key_files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_error_style.py
decisions:
  - "Branch placed AFTER sdet_err and BEFORE the generic missing fallback (matches the scan-all-errors precedent so co-occurring missing-field errors do not steal the rendering)"
  - "No @field_validator added to Config -- operator-tone wrapping lives ONLY in cli.py per D-04"
  - "No shared-helper-module refactor -- library mode inherits the new branch via the existing lazy import at _plugin.py's pytest_configure ValidationError arm (Phase 31 D-04 precedent)"
  - "Inline comment text in cli.py drops planning-system IDs (Phase 22 D-04 hard-zero policy) -- comment names the operator-tone behavior in plain terms instead"
metrics:
  duration: ~10 minutes
  tasks_completed: 2
  files_modified: 2
  completed_date: 2026-05-27
---

# Phase 34 Plan 02: Operator-tone error for host_isolation literal_error Summary

**One-liner:** Extends `_emit_operator_error_for_validation` in `cli.py` with a `(literal_error, ('host_isolation',))` branch that renders the verbatim three-part operator-tone rejection consumed by both the CLI persona and the library-mode persona; pinned by a new regression test in `tests/framework/unit/test_error_style.py`.

## Final Branch Text (verbatim, for plan 34-08 doc reference)

Inserted into `src/mcp_test_framework/cli.py` between the existing `sdet_err` branch and the generic `missing` fallback:

```python
# Operator typo'ing the host_isolation value (e.g.
# `host_isolation: hermetic`) surfaces as a Pydantic `literal_error`
# at `loc=('host_isolation',)`. Wrap with operator-tone three-part
# text that names both valid modes and the trade-off and points at
# docs/LIBRARY-MODE.md host-isolation. Mirrors the `sdet_err`
# scan-all-errors precedent so a co-occurring missing-field error
# does not steal the rendering. The Config model emits the stock
# literal_error; the operator-tone wrapping lives ONLY here.
literal_host_isolation_err = next(
    (
        e
        for e in errors
        if e.get("type") == "literal_error"
        and tuple(e.get("loc", ())) == ("host_isolation",)
    ),
    None,
)
if literal_host_isolation_err is not None:
    bad_value = literal_host_isolation_err.get("input", "?")
    _emit_operator_error(
        summary=f"unknown host_isolation mode: {bad_value!r}",
        detail=[
            "host_isolation accepts only 'strict' or 'passthrough'.",
            "strict (default) isolates the spawned MCP subprocess from "
            "your host credentials and HOME;",
            "passthrough hands the operator's full env to the subprocess "
            "(xdist clamped to 1 worker).",
        ],
        next_step=(
            "set `host_isolation: strict` or `host_isolation: passthrough` "
            "in your config.yaml; see docs/LIBRARY-MODE.md §host-isolation "
            "for the trade-off"
        ),
    )
```

## Locked Assertion Phrases (verbatim, for plan 34-08 doc copy)

The new pin test `test_error_style_host_isolation_literal_rejection` asserts these substrings appear in the rendered output:

1. `unknown host_isolation mode: 'hermetic'` -- the summary phrase with `bad_value!r`
2. `host_isolation accepts only 'strict' or 'passthrough'.` -- first detail phrase
3. `passthrough hands the operator's full env to the subprocess` -- second detail phrase
4. `docs/LIBRARY-MODE.md` -- the doc pointer in `next_step`
5. `host-isolation` -- the doc anchor name `next_step` points at (the `§` glyph is rendered but not pinned to keep the assertion ASCII-safe)

Docs plan 34-08 should copy the **summary phrase**, the **two detail phrases**, and the **doc-pointer phrase** verbatim when authoring the README and `docs/LIBRARY-MODE.md` worked example so the prose and the runtime output align.

## `_plugin.py:228` Lazy Import Path -- Unchanged

`src/mcp_test_framework/_plugin.py` was not touched by this plan. The lazy-import path inside `pytest_configure`'s `except ValidationError` arm (Phase 31 D-04 factoring) was already wired to `_emit_operator_error_for_validation`. Adding ONE branch inside that function gives the library-mode persona the new rejection text automatically -- verified by running the full `tests/framework/` suite green after the branch landed (`_plugin.py`-driven tests pass without modification).

## Tasks Completed

| Task | Name                                                                                | Commit  | Files                                          |
| ---- | ----------------------------------------------------------------------------------- | ------- | ---------------------------------------------- |
| 1    | Write failing pin test for host_isolation literal_error operator-tone message (RED) | 4868053 | tests/framework/unit/test_error_style.py       |
| 2    | Add literal_error branch for host_isolation in cli error mapper (GREEN)             | 3080f0a | src/mcp_test_framework/cli.py                  |

## Verification

All plan-level `<verification>` and `<success_criteria>` checks pass:

- `uv run pytest tests/framework/unit/test_error_style.py -x` => 13/13 passed (12 pre-existing + 1 new pin)
- `uv run pytest tests/framework/ -x` => 767 passed, 2 skipped, 18 deselected, 1 xfailed (no regression; full suite stays green)
- `grep -nE "literal_host_isolation_err" src/mcp_test_framework/cli.py` => match at L344 / L353 / L354
- `grep -nE 'unknown host_isolation mode' src/mcp_test_framework/cli.py` => match in the new branch
- `grep -nE "host_isolation accepts only 'strict' or 'passthrough'" src/mcp_test_framework/cli.py` => match in the new branch
- `grep -nE "passthrough hands the operator's full env to the subprocess" src/mcp_test_framework/cli.py` => match in the new branch
- `grep -nE "docs/LIBRARY-MODE.md" src/mcp_test_framework/cli.py` => match in `next_step`
- `grep -cE "_emit_operator_error_for_validation_error" src/mcp_test_framework/cli.py` => 0 (the CONTEXT.md typo'd name was NOT introduced; the actual symbol `_emit_operator_error_for_validation` from `cli.py:243` is used)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inline comment carried planning-system IDs which broke the Phase 22 D-04 hard-zero policy gate**

- **Found during:** Task 2 verification (`uv run pytest tests/framework/`)
- **Issue:** The initial Task-2 comment block above the new branch used `# Phase 34 ISOL-01 D-04: ...` to explain the intent. The locked Phase 22 D-04 gate (enforced by `tests/framework/unit/test_no_planning_ids_in_src.py`) bans the substrings `Phase \d`, `ISOL-\d`, and `\bD-\d+\b` anywhere under `src/mcp_test_framework/`. The fresh comment violated all three patterns at once and failed the gate test.
- **Fix:** Rewrote the comment block to describe the branch's behavior in plain operator-tone terms (no Phase / requirement / decision IDs); kept the explanation of WHY the branch exists and what its scan-all-errors precedent is.
- **Files modified:** `src/mcp_test_framework/cli.py` (in-Task-2 amend, no separate commit)
- **Commit:** `3080f0a` (the fix landed in the same commit as the GREEN branch -- the failing gate test surfaced after the edit but before the commit, so a single corrected commit covered both)
- **Note for future executors:** any new comment added under `src/mcp_test_framework/` must avoid the locked planning-ID patterns. The regex is `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b|\bPhase \d`. Comments should describe behavior in plain English; cross-references to plans live in `.planning/`.

## Authentication Gates

None.

## Threat Flags

None. The plan's threat register (T-34-02-01..04) is fully addressed:
- T-34-02-01 (Info disclosure -- bare Pydantic error): mitigated by the new branch; pinned by the verbatim phrase asserts in the new test.
- T-34-02-02 (Tampering -- generic fallback steals the rendering): mitigated by branch placement after `sdet_err` and before the generic `missing` fallback; the pin test's YAML body contains both `host_isolation: hermetic` AND a complete `test_code:` block so the specific branch must win against a co-occurring scenario.
- T-34-02-03 (Spoofing -- bad_value injection): accepted per plan; `bad_value!r` uses `repr()` which escapes control characters. Verified: the test passes `bad_value='hermetic'` (no escape chars in normal operator typo path).
- T-34-02-04 (Repudiation -- library mode sees different error): mitigated by the lazy-import path at `_plugin.py`'s `pytest_configure` ValidationError arm being unchanged; single source edit covers both personas.

## Known Stubs

None. The branch is fully wired into the dispatcher and both personas; no placeholder text, no UI rendering paths affected. The doc plan 34-08 will land the README / `docs/LIBRARY-MODE.md` `§host-isolation` anchor that the `next_step` points at -- when that lands, the anchor will resolve; until then the pointer text is still operator-actionable ("see docs/LIBRARY-MODE.md ..." names the file, and operators will find the host_isolation discussion either in the existing doc or in the upcoming additions).

## TDD Gate Compliance

Per-task `tdd="true"` discipline observed:

- **Task 1 (RED gate):** test_error_style_host_isolation_literal_rejection added in commit `4868053` as a `test(34-02): ...` commit. Ran `uv run pytest tests/framework/unit/test_error_style.py::test_error_style_host_isolation_literal_rejection -x` -- exited non-zero with AssertionError on the first locked text substring. RED phase confirmed.
- **Task 2 (GREEN gate):** branch added in commit `3080f0a` as a `feat(34-02): ...` commit. Ran the same pytest invocation post-edit -- exited zero. Re-ran the full `tests/framework/` suite -- exited zero (767 passed). GREEN phase confirmed.
- **REFACTOR gate:** not invoked; the new branch follows the existing `sdet_err` template verbatim and required no follow-up cleanup beyond the inline-comment Rule-1 fix folded into the GREEN commit.

Commit messages use the project's `{type}({phase}-{plan}): {summary}` convention.

## Self-Check: PASSED

- src/mcp_test_framework/cli.py modified (lines 336-372 carry the new branch): FOUND
- tests/framework/unit/test_error_style.py modified (lines 98-140 carry the new test): FOUND
- Commit 4868053 (test 34-02): FOUND in git log
- Commit 3080f0a (feat 34-02): FOUND in git log
- pytest run on tests/framework/unit/test_error_style.py: 13/13 passed
- pytest run on tests/framework/: 767 passed, 0 failed
- `_emit_operator_error_for_validation_error` (CONTEXT.md typo'd name) in cli.py: 0 occurrences (correct symbol used)
- planning-ID gate test (`test_no_planning_ids_in_src`): passes (Rule 1 fix prevented leak)
