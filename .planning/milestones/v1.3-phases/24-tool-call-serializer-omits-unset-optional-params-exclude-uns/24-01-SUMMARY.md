---
phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
plan: 01
subsystem: sdet
tags: [serializer, sdet, pydantic, exclude_unset, seed-022, tool-factory]

# Dependency graph
requires:
  - phase: 18-sdet-test-surface-and-mcp-session-fixture
    provides: ToolWrapper.call serializer (the model_dump call site this plan modifies)
  - phase: 17-codegen-schema-driven-class-generation
    provides: SEED-022 framework-primitives principle (the discriminator anchor)
provides:
  - exclude_unset=True on tool().call() wire serializer
  - SDET-omitted optional fields stay off the MCP wire
  - explicit field=None still flows null on the wire (SEED-022 invariant locked)
  - three new payload-asserting tests covering unset/explicit-None/explicit-value behaviors
  - renamed kwargs-spy test with exclude_unset assertion
  - new SERIALIZER-01 requirement row + traceability entries
affects: [phase-19-stateful-primitives, phase-21-sdet-authoring-docs, phase-24-docs-ripples, homelab-mcp inputSchema bug]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Payload-level wire-format assertions on _StubClient.calls[0][1] (the actual arguments dict) lock the user-visible serializer contract"
    - "kwargs-spy via Pydantic BaseModel subclass override (instance-attr override blocked) — Phase 18 precedent extended to exclude_unset"
    - "Hand-rolled Pydantic fixtures in framework unit tests (no codegen-tree coupling)"

key-files:
  created: []
  modified:
    - "src/mcp_test_framework/sdet/_tool_factory.py — L99 serializer kwarg fix + 2 docstring updates"
    - "tests/framework/unit/test_tool_factory.py — _FakeParamsWithOptional fixture + 3 new tests + 1 renamed kwargs-spy test"
    - ".planning/REQUIREMENTS.md — SERIALIZER requirement group + traceability + phase coverage rows; rollup totals 27→28, 7→8 phases"

key-decisions:
  - "D-01 (pre-locked): exclude_unset=True is the SEED-022-compatible fix — distinguishes user-omitted from user-explicitly-set, unlike exclude_none which masks the upstream homelab-mcp inputSchema bug at the framework level"
  - "D-02: Three payload-asserting tests carry the contract weight (not just kwargs-spy)"
  - "D-04: Hand-rolled _FakeParamsWithOptional fixture — framework unit tests stay codegen-tree-independent"

patterns-established:
  - "Wire-format payload assertion via _StubClient.calls[0][1] inspection — locks the user-visible serializer contract independently of implementation details"
  - "exclude_unset filters on user intent (did the SDET set this attribute?), not on value (`is None`) — SEED-022 discriminator"

requirements-completed: [SERIALIZER-01]

# Metrics
duration: ~10min
completed: 2026-05-15
---

# Phase 24 Plan 01: Tool-call serializer exclude_unset Summary

**`tool().call()` now uses `model_dump(mode='json', exclude_unset=True)` so SDET-omitted optional fields stay off the MCP wire while explicit `field=None` still flows `null` (SEED-022 user-intent discriminator preserved); locked by three new payload-asserting unit tests + a renamed kwargs-spy test.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-15T15:47:27Z (approx — plan execution start)
- **Completed:** 2026-05-15 (this commit)
- **Tasks:** 3 (all atomic)
- **Files modified:** 3 (1 source, 1 test, 1 requirement doc)

## Accomplishments

- Switched `_tool_factory.py:99` from `model_dump(mode="json")` to `model_dump(mode="json", exclude_unset=True)` — single-line serializer fix that eliminates the framework's contribution to the upstream homelab-mcp `Input validation error: None is not of type 'string'` failures.
- Three new payload-asserting tests under `tests/framework/unit/test_tool_factory.py` lock the user-visible behavior independently of the kwargs-spy approach:
  - `test_call_omits_unset_optional_field_from_wire_arguments` — unset `cdrom` is ABSENT from `arguments`
  - `test_call_serializes_explicit_none_to_wire_null` — explicit `cdrom=None` flows `null` on the wire (SEED-022 invariant)
  - `test_call_serializes_explicit_value_unchanged` — explicit value passes through unchanged (regression guard)
- Renamed the existing kwargs-spy test in place to `test_call_serializes_params_with_mode_json_and_exclude_unset` with one new `assert captured_kwargs.get("exclude_unset") is True` line — implementation choice locked alongside `mode='json'`.
- New `_FakeParamsWithOptional(BaseModel)` fixture (one required field + one `cdrom: str | None = None`) mirrors the upstream shape that triggered the homelab-mcp bug; hand-rolled at the top of the test file (no codegen-tree coupling).
- New `SERIALIZER-01` requirement row in `.planning/REQUIREMENTS.md` under a new `SERIALIZER — Tool-call wire serializer (Phase 24)` group; traceability table + phase coverage summary updated; rollup totals 27→28 across 8 phases (17–24).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SERIALIZER-01 requirement row to REQUIREMENTS.md** — `ac9eeb0` (docs)
2. **Task 2: Add _FakeParamsWithOptional fixture + 3 payload tests + rename kwargs-spy test (RED gate)** — `435939b` (test)
3. **Task 3: Switch serializer to model_dump(mode='json', exclude_unset=True) (GREEN gate)** — `7362b0c` (feat)

_Note: This plan follows TDD per-task (task 2 lands the failing tests; task 3 makes them pass)._

## Files Created/Modified

- `src/mcp_test_framework/sdet/_tool_factory.py` — L99 serializer kwarg fix + class-level ToolWrapper docstring (L62 area) + ToolWrapper.call docstring (L82–L84 area) all updated to mention `exclude_unset=True`
- `tests/framework/unit/test_tool_factory.py` — `_FakeParamsWithOptional` fixture (top of file, after `_FakeResponse`); existing kwargs-spy test renamed in place to `test_call_serializes_params_with_mode_json_and_exclude_unset` with one new assertion; 3 new tests added after it (before `test_active_client_module_attribute_defaults_to_none`)
- `.planning/REQUIREMENTS.md` — new `SERIALIZER` requirement group, traceability row, phase coverage row, rollup totals updated

## RED-gate evidence (Task 2 intermediate run)

Before Task 3 shipped the serializer change, the Task 2 test set produced the expected mixed RED/GREEN:

```
$ uv run pytest tests/framework/unit/test_tool_factory.py -k "exclude_unset or omits_unset or explicit_none or explicit_value" --tb=line

collected 15 items / 11 deselected / 4 selected

tests\framework\unit\test_tool_factory.py FF..                           [100%]

================================== FAILURES ===================================
E   AssertionError: expected model_dump(exclude_unset=True) -- Phase 24 SERIALIZER-01; got kwargs={'mode': 'json'}
    assert None is True
     +  where None = <built-in method get of dict object at ...>('exclude_unset')
     +    where <built-in method get of dict object at ...> = {'mode': 'json'}.get
test_tool_factory.py:221: AssertionError: expected model_dump(exclude_unset=True) -- Phase 24 SERIALIZER-01; got kwargs={'mode': 'json'}
E   AssertionError: expected unset optional `cdrom` to be omitted from wire arguments; got {'name': 'x', 'cdrom': None}
    assert 'cdrom' not in {'cdrom': None, 'name': 'x'}
test_tool_factory.py:264: AssertionError: expected unset optional `cdrom` to be omitted from wire arguments; got {'name': 'x', 'cdrom': None}
=========================== short test summary info ===========================
FAILED tests/framework/unit/test_tool_factory.py::test_call_serializes_params_with_mode_json_and_exclude_unset
FAILED tests/framework/unit/test_tool_factory.py::test_call_omits_unset_optional_field_from_wire_arguments
================= 2 failed, 2 passed, 11 deselected in 0.08s ==================
```

The RED-gate fires exactly on the two tests that need the Task 3 fix:
- `test_call_serializes_params_with_mode_json_and_exclude_unset` — kwargs spy sees only `{mode: 'json'}` before fix
- `test_call_omits_unset_optional_field_from_wire_arguments` — payload contains `cdrom: None` before fix

The two SEED-022 invariant tests (`explicit_none_to_wire_null`, `explicit_value_unchanged`) pass both before and after the fix — locking the discriminator behavior independently of the wire-omission behavior.

## GREEN-gate evidence (post Task 3)

After the serializer change shipped, the targeted run:

```
$ uv run pytest tests/framework/unit/test_tool_factory.py -q --tb=short
...............                                                          [100%]
15 passed in 0.05s
```

All 15 tests in `test_tool_factory.py` pass (12 pre-existing + 3 new + 1 renamed-existing-extended). No regressions.

## Final framework suite tally

```
$ uv run pytest tests/framework/ --tb=no -q
...
578 passed, 1 skipped, 17 deselected, 2 xfailed in 36.80s
```

Exactly the predicted Phase 23 close-gate baseline (575 passed) + 3 new tests = 578 passed; 1 skipped / 17 deselected / 2 xfailed unchanged.

## Decisions Made

- **D-01 (pre-locked):** `exclude_unset=True` is the correct kwarg, not `exclude_none=True`. The discriminator filters on user intent ("did the SDET set this attribute?"), not on value ("is None"). This is SEED-022-compatible: an SDET explicitly writing `cdrom=None` to test the server's null-handling path still puts `null` on the wire.
- **D-02:** Three new payload-asserting tests added (not one consolidated kwargs assertion) — gives named failing tests if any of the three behaviors regresses, instead of one cryptic kwargs-shape failure.
- **D-03:** Existing kwargs-spy test renamed in place (not duplicated) so the spy contract for `model_dump` kwargs stays a single test that locks both `mode='json'` and `exclude_unset=True` together.
- **D-04:** Fixture is hand-rolled in the test file (`_FakeParamsWithOptional` with one required + one `cdrom: str | None = None`), not pulled from the codegen tree. Framework unit tests stay codegen-tree-independent (Phase 21.1 RELOC-03 invariant).

## Deviations from Plan

None — plan executed exactly as written.

The plan was extremely specific (exact text to insert, exact test names, exact grep checks). All three tasks landed verbatim. No deviation rules triggered.

---

**Total deviations:** 0
**Impact on plan:** None — plan was a precise single-line serializer fix with mechanical test/doc ripples. No discovery, no auto-fixes needed.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Framework-side fix shipped.** Phase 24's first plan closes the framework's contribution to the upstream homelab-mcp `inputSchema` bug. SDET tests that previously failed with `Input validation error: None is not of type 'string'` because of unset optional fields now succeed on the framework side; the upstream bug remains only for SDETs explicitly testing null-handling paths.
- **Plans 24-02 and 24-03 are unblocked.** Plan 24-01 finalizes the serializer contract; downstream plans handle the doc ripples (SDET-AUTHORING.md soften, README sample re-capture, STATE.md Deferred Items split per D-05..D-08).
- **STATE.md Deferred Items split (D-05..D-08) is part of a later plan in this phase, not this one.** Confirmed by re-reading the plan tasks — Task 1 here is REQUIREMENTS.md only.
- **v1.3 close push** (per memory `project_v1_3_close_push_and_scrub.md`) still gated by completion of all Phase 24 plans.

## Self-Check: PASSED

Verified post-write:

- `src/mcp_test_framework/sdet/_tool_factory.py` — FOUND, contains `params.model_dump(mode="json", exclude_unset=True)` exactly once; `params.model_dump(mode="json")` zero matches; `exclude_unset=True` total 3 matches (code line + 2 docstring references).
- `tests/framework/unit/test_tool_factory.py` — FOUND, contains `class _FakeParamsWithOptional` (1 match), three new test names (3 matches), renamed kwargs-spy `test_call_serializes_params_with_mode_json_and_exclude_unset` (1 match), old name `def test_call_serializes_params_with_mode_json(` (0 matches), `cdrom: str | None = None` (1 match), `exclude_unset assertion` (1 match).
- `.planning/REQUIREMENTS.md` — FOUND, `^| SERIALIZER-01` (2 matches), `### SERIALIZER — Tool-call wire serializer (Phase 24)` (1 match), `Total: 28 requirements mapped across 8 phases (17–24)` (1 match), `Total: 27 requirements` (0 matches), `exclude_unset=True` (1 match).
- Commit `ac9eeb0` (docs Task 1) — FOUND in `git log --oneline`.
- Commit `435939b` (test Task 2) — FOUND in `git log --oneline`.
- Commit `7362b0c` (feat Task 3) — FOUND in `git log --oneline`.
- Framework suite GREEN at 578 passed / 1 skipped / 17 deselected / 2 xfailed (exact match for predicted baseline +3 new tests).

---
*Phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns*
*Completed: 2026-05-15*
