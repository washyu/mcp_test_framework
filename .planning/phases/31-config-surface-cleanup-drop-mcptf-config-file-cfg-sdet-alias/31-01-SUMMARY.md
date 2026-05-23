---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 01
subsystem: config
tags: [config, deprecation-shim, operator-error, pydantic, pydantic-settings, sdet-removal]

# Dependency graph
requires:
  - phase: 25-cli-public-api-rename-sdet-to-test-code
    provides: validation_alias=AliasChoices('test_code','sdet') shim that this plan removes
provides:
  - Config model is now alias-free; bare extra='forbid' is the sole rejection mechanism for unknown top-level keys
  - cli._emit_operator_error_for_validation routes (extra_forbidden, loc=('sdet',)) to the D-02 verbatim three-part operator-tone message
  - Pinned-text regression test in tests/framework/unit/test_error_style.py locks the D-02 wording
affects: [31-02-shim-05, 31-03-v1drop-03, 31-06-v1drop-04, 32-shim-removals, 35-regression-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Targeted (err_type, loc) tuple branches in _emit_operator_error_for_validation -- the next-handler pattern walks errors[] rather than relying on primary"
    - "extra='forbid' + dispatcher branch as the post-shim rejection mechanism (no validators, no pre-scans)"

key-files:
  created:
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-01-SUMMARY.md
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/deferred-items.md
  modified:
    - src/mcp_test_framework/config.py (-194 lines net; removed all sdet-alias machinery)
    - src/mcp_test_framework/cli.py (+27 lines; new extra_forbidden+sdet branch)
    - tests/framework/unit/test_error_style.py (+42 lines; D-02 pin test)

key-decisions:
  - "Bare extra='forbid' replaces all sdet-alias machinery -- no validators, no pre-scans, no model_validate override"
  - "Branch detection scans the full errors[] list (mirroring the version_err idiom), not primary, so the sdet error fires even when co-occurring with other errors"
  - "D-02 verbatim wording is operator-approved -- the test pins it to prevent silent drift"
  - "Test fixture cleanup for other test files using sdet: YAML is deferred to Plan 31-06 per the phase roadmap"

patterns-established:
  - "Pattern: targeted operator-tone branch via (err_type, loc) tuple match in the dispatcher -- reusable for future per-key rejections (e.g. SHIM-05 MCPTF_CONFIG_FILE)"
  - "Pattern: full-errors[] scan-and-prefer idiom for branches that may co-occur with other validation errors"

requirements-completed: [SHIM-04]

# Metrics
duration: 25min
completed: 2026-05-23
---

# Phase 31 Plan 01: SHIM-04 sdet alias removal Summary

**Removed the cfg.sdet.* YAML-alias machinery from the Config model; top-level sdet: keys now surface as Pydantic extra_forbidden errors and route through a new targeted (extra_forbidden, loc=('sdet',)) branch in cli._emit_operator_error_for_validation to render the D-02 verbatim three-part operator-tone rejection message.**

## Performance

- **Duration:** ~25 minutes (offset by Windows path-format troubleshooting on Write tool)
- **Started:** 2026-05-23T~16:14Z
- **Completed:** 2026-05-23T~16:39Z
- **Tasks:** 3
- **Files modified:** 3 source files + 2 planning artifacts

## Accomplishments

- Deleted ~197 lines of v1.4 sdet-alias shim machinery from `config.py` (validators, classmethod override, YAML pre-scan helper, AliasChoices import, all `# noqa: sdet-rename-shim` markers).
- Added a 27-line targeted branch to `_emit_operator_error_for_validation` that maps the new `(extra_forbidden, loc=('sdet',))` shape to the D-02 verbatim operator-tone message and raises `typer.Exit(2)`.
- Pinned the D-02 wording with a new end-to-end regression test (`test_error_style_sdet_rejection_message`) that drives the full `Config(yaml_file=...) -> ValidationError -> dispatcher -> stderr` path.
- Verified both routes (CLI mode `cli._load_config` + library mode `_plugin.pytest_configure`) share the dispatcher hook -- no plugin changes needed.

## Task Commits

Each task was committed atomically (TDD-shaped; the failing pre-condition was demonstrated before each implementation):

1. **Task 1: Delete sdet: alias machinery from Config model** -- `f2c8b03` (refactor)
2. **Task 2: Add extra_forbidden+sdet branch to _emit_operator_error_for_validation** -- `6d7381c` (feat)
3. **Task 3: Pin the D-02 sdet-rejection message in test_error_style.py** -- `ba60878` (test)

## Files Created/Modified

- `src/mcp_test_framework/config.py` -- shrunk from 312 -> 118 lines. Removed: `AliasChoices` import, `validation_alias=AliasChoices("test_code","sdet")` on the `test_code` field, `_warn_or_reject_legacy_sdet_key` model_validator, `model_validate` classmethod override, `_check_legacy_sdet_key_in_yaml` helper, the call to that helper inside `settings_customise_sources`, every `# noqa: sdet-rename-shim` marker. Preserved: `extra="forbid"` (the central mechanism), `_validate_version`, `settings_customise_sources` pipeline shape, `MCPTF_CONFIG_FILE` fallback (Plan 31-02 will unwire that next).
- `src/mcp_test_framework/cli.py` -- inserted a new 27-line branch in `_emit_operator_error_for_validation` between the version-mismatch branch (line ~292-315) and the missing-required-field branch (line ~316-329). Branch walks `errors` for `(err_type='extra_forbidden', loc=('sdet',))`, renders the D-02 message via the existing `_emit_operator_error` helper, raises `typer.Exit(2)`. Existing v1-rejection branch (`config file uses an older format`) untouched -- Plan 31-03 owns that rewrite.
- `tests/framework/unit/test_error_style.py` -- added `test_error_style_sdet_rejection_message` (42 lines). Uses `tmp_path` to write a `version: 2\nsdet: ...` YAML, drives `Config(yaml_file=...)` -> `ValidationError`, invokes the dispatcher, asserts (1) `typer.Exit.exit_code == 2`, (2) all four verbatim D-02 substrings appear in captured stdout/stderr.
- `.planning/phases/31-.../deferred-items.md` -- logs the pre-existing test files (`test_runner_subprocess.py`, `test_sdet_cli.py`, etc.) that use `sdet:` YAML fixtures and now fail after Task 1's alias removal. Per the phase roadmap, those swaps are owned by Plan 31-06 (`v1drop-04-sdet-yaml-swaps-and-test-cleanup`); pre-rewriting them in this plan would violate the plan-files contract and create merge conflict surface against Plan 06.

## Decisions Made

- **Bare `extra="forbid"` replaces the alias machinery.** No validators, no pre-scans, no `model_validate` override. Pydantic's native `extra_forbidden` error is sufficient; the dispatcher branch added in Task 2 carries the operator-tone surface so the raw Pydantic shape never leaks to the operator.
- **`errors[]` full-list scan (not `primary`).** Mirrors the existing `version_err` idiom (lines 267-275) -- the sdet error may co-occur with other errors (e.g., a v1 `sdet:`-keyed YAML that also has a v1 `version: 1`), so relying on `primary = errors[0]` would silently shift behavior. Scan with `next((e for e in errors if ...), None)` keeps the branch order-independent.
- **D-02 wording is operator-approved.** Both Task 2's branch and Task 3's test use the verbatim text from CONTEXT D-02. Test asserts the literal substrings; future edits to either side break the test, by design.
- **No CLI/plugin wiring changes.** The dispatcher is the shared entry point per CONTEXT D-04 -- both CLI mode (`cli._load_config`) and library mode (`_plugin.pytest_configure`) lazy-import `_emit_operator_error_for_validation`. Adding the branch inside that function reaches both personas automatically.

## Deviations from Plan

None requiring auto-fix. The pre-existing test failures in `tests/framework/unit/test_sdet_cli.py`, `test_runner_subprocess.py`, etc. are **by-design breakage** from the alias removal -- those test files use `sdet:` YAML fixtures that are scoped to **Plan 31-06** (`v1drop-04-sdet-yaml-swaps-and-test-cleanup`) per the phase roadmap. Plan 31-01's `<files_modified>` list explicitly excludes those test files, and the plan's `<action>` for Task 2 explicitly cautions: "do not pre-rewrite or you create a merge conflict surface against Plan 03." Documented in `deferred-items.md` for traceability.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** Plan executed exactly as written. Three files modified, three task commits, one deferred-items log. Acceptance criteria for all three tasks verified.

## Issues Encountered

- **Windows path-format quirk in the Write tool.** Initial Writes using the forward-slash form (`C:/Users/...`) reported success but did not flush to disk. Switching to the backslash form (`C:\Users\...`) worked. Lost ~5-10 minutes diagnosing. Subsequent tool calls (Edit, Write) all use backslash paths.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- **Plan 31-02 (SHIM-05 MCPTF_CONFIG_FILE unwiring)** is unblocked. The `settings_customise_sources` pipeline still reads `MCPTF_CONFIG_FILE` as an IPC fallback (lines ~109-111 of the new config.py); Plan 02 removes that.
- **Plan 31-03 (V1DROP-03 v1-rejection rewrite)** is independent of this plan but will modify the same `_emit_operator_error_for_validation` function -- expected to land in a different wave.
- **Plan 31-06 (V1DROP-04 sdet YAML swaps + test cleanup)** has its scope confirmed by this plan's deferred-items list. The failing tests will be turned green there.

## Self-Check: PASSED

- src/mcp_test_framework/config.py: FOUND (118 lines; grep -c AliasChoices = 0; grep -c extra="forbid" = 2)
- src/mcp_test_framework/cli.py: FOUND (grep -c "unknown config key: sdet" = 1; grep -c "rename the .sdet:" = 1)
- tests/framework/unit/test_error_style.py: FOUND (grep -c "test_error_style_sdet_rejection_message" = 1; pytest run = 1 passed)
- .planning/phases/31-.../deferred-items.md: FOUND
- Commit f2c8b03: FOUND in git log
- Commit 6d7381c: FOUND in git log
- Commit ba60878: FOUND in git log

---
*Phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias*
*Plan: 01*
*Completed: 2026-05-23*
