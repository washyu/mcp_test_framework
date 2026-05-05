---
phase: 02-mcp-client-wrapper
plan: 01
subsystem: config
tags: [pydantic, pydantic-settings, env-var, alias-choices, precedence-test, timeout]

# Dependency graph
requires:
  - phase: 01-foundation-pure-data-core
    provides: "McpServerConfig sub-model, _BareNameNestedEnvSource, AliasChoices+populate_by_name pattern, _SPEC_ENV_VARS test idiom"
provides:
  - "McpServerConfig.timeout_seconds field (default=30, ge=1) — single uniform timeout knob (D-06)"
  - "MCP_SERVER_TIMEOUT_SECONDS env var routed to cfg.mcp_server.timeout_seconds via existing _BareNameNestedEnvSource"
  - "YAML overlay key mcp_server.timeout_seconds for the same field"
  - ".env.example and config.example.yaml documenting the new knob"
  - "Precedence-test guard against silent default-fallback (D-07 regression)"
affects: [02-02-mcp-client-wrapper, 02-03-mcp-smoke-test, 04-fixtures-and-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-field validation_alias=AliasChoices(<env>, <field>) + populate_by_name=True per sub-model"
    - "Precedence test required for every new bare-name nested env var (Phase 1 LEARNINGS lesson)"

key-files:
  created:
    - "README.md (minimal stub — Rule 3 deviation, full README is Phase 5)"
  modified:
    - "src/mcp_test_framework/models.py (one field add)"
    - ".env.example (one line)"
    - "config.example.yaml (one line)"
    - "tests/unit/test_config.py (one tuple entry, one default assertion, one new test)"

key-decisions:
  - "D-05 honored verbatim: timeout_seconds=int Field(default=30, ge=1, AliasChoices(MCP_SERVER_TIMEOUT_SECONDS, timeout_seconds))"
  - "D-07 honored: env routing covered by a dedicated precedence test; YAML/init routing deferred (single load-bearing slice is enough per plan)"
  - "Zero changes to config.py — existing _BareNameNestedEnvSource already walks the new AliasChoices automatically"

patterns-established:
  - "Adding a new env-mapped sub-model field requires NO config.py edits when _BareNameNestedEnvSource is already in place — only the AliasChoices on the sub-model field"
  - "Adding the new env name to test_config.py::_SPEC_ENV_VARS is mandatory so _clear_env strips developer-shell exports before each test"

requirements-completed: [CORE-03]

# Metrics
duration: ~25min
completed: 2026-05-05
---

# Phase 2 Plan 1: McpServerConfig.timeout_seconds Summary

**Single uniform 30s timeout knob added to McpServerConfig with env/YAML routing through the existing _BareNameNestedEnvSource, plus the D-07 precedence-test regression guard.**

## Performance

- **Duration:** ~25 min (includes a Rule 3 README fix + uv build cold start)
- **Started:** 2026-05-05T02:05Z (approx)
- **Completed:** 2026-05-05T02:30Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- `McpServerConfig.timeout_seconds: int` field added (default=30, ge=1, two-arg AliasChoices), verbatim D-05 shape
- `MCP_SERVER_TIMEOUT_SECONDS=30` documented in `.env.example`, `mcp_server.timeout_seconds: 30` documented in `config.example.yaml`
- `tests/unit/test_config.py` extended with one `_SPEC_ENV_VARS` entry, one `test_defaults` assertion, and one new env-precedence test
- All 25 tests in the project pass (10 in `test_config.py`, 9 pre-existing + 1 new)
- `uv run ruff check src tests` clean
- The Phase 2 client wrapper (next plan) can now read `cfg.mcp_server.timeout_seconds` and pass it into `asyncio.timeout(...)` ceilings

## Task Commits

Each task was committed atomically (--no-verify per parallel-executor guidance):

1. **Pre-Task: README stub (Rule 3 fix)** — `459e3a8` (chore) — unblock hatchling editable build
2. **Task 1: Add McpServerConfig.timeout_seconds field + extend example docs** — `49ecbb2` (feat)
3. **Task 2: Extend test_config.py — _SPEC_ENV_VARS, test_defaults, and new precedence test** — `597692e` (test)

The plan-metadata commit (this SUMMARY.md) follows.

## Files Created/Modified

- `README.md` (CREATED) — minimal stub citing Phase 5 as the home for the full README; required because `pyproject.toml` declares `readme = "README.md"` and hatchling refused to build without it (Rule 3 deviation)
- `src/mcp_test_framework/models.py` (MODIFIED) — appended `timeout_seconds: int = Field(default=30, ge=1, validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"))` to `McpServerConfig`; no other lines changed
- `.env.example` (MODIFIED) — added `MCP_SERVER_TIMEOUT_SECONDS=30` immediately after `MCP_SERVER_ARGS=` so the `MCP_SERVER_*` block stays grouped
- `config.example.yaml` (MODIFIED) — added `  timeout_seconds: 30` as the third entry under `mcp_server:`
- `tests/unit/test_config.py` (MODIFIED) — three small extensions per plan Action block

## Decisions Made

- Followed plan as specified for both tasks — no implementation discretion exercised inside the planned task scope.
- Pre-task Rule 3 fix: created a minimal `README.md` rather than editing `pyproject.toml` to drop the `readme` declaration. Reasoning: the project already has an Active requirement for a README (PROJECT.md), and a stub that points at Phase 5 leaves the real authoring deferred to its planned location while unblocking every `uv run` invocation in this and downstream plans. Editing `pyproject.toml` would have been more invasive (pyproject is shared infra) and would mask a real future deliverable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created README.md stub**
- **Found during:** Task 1 verification (`uv run python -c "..."`)
- **Issue:** `uv sync` (triggered by `uv run`) failed in this fresh worktree with `OSError: Readme file does not exist: README.md` because `pyproject.toml` declares `readme = "README.md"` but the file is not committed to the repo. Every `uv run` verification step in the plan would fail without this fix.
- **Fix:** Wrote a 9-line stub README pointing at PROJECT.md and the MVP spec, with an explicit note that the full README lands in Phase 5.
- **Files modified:** `README.md` (created)
- **Verification:** `uv run python -c "from mcp_test_framework.models import McpServerConfig; ..."` succeeded after the fix; `uv run pytest` passed all 25 tests.
- **Committed in:** `459e3a8`

**2. [Internal-inconsistency note — NOT a Rule deviation] Acceptance-criterion grep count off-by-one**
- **Found during:** Task 2 verification
- **Issue:** Plan acceptance criterion `grep -c "MCP_SERVER_TIMEOUT_SECONDS" tests/unit/test_config.py` expected `2` (one in `_SPEC_ENV_VARS`, one in `monkeypatch.setenv`), but the plan's mandated docstring for the new test ALSO contains the literal `MCP_SERVER_TIMEOUT_SECONDS`. Following the plan verbatim therefore yields a count of `3`, not `2`.
- **Fix:** None — followed the plan's verbatim docstring as written. The semantic intent of the criterion (env name appears in both the cleanup tuple AND in the new test) is satisfied.
- **Files modified:** none
- **Verification:** All 10 tests pass; the env name appears in `_SPEC_ENV_VARS` (line 33), the new test docstring (line 167), and `monkeypatch.setenv` (line 178).
- **Committed in:** n/a — internal plan inconsistency, not an executor deviation.

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking) + 1 internal-plan-inconsistency note
**Impact on plan:** README stub is essential for any `uv run` step to succeed; nothing else in the plan was scope-creeped. The grep-count discrepancy is a plan authoring artifact.

## Issues Encountered

- Cold-start `uv sync` in the worktree took ~30s on first invocation (40 packages installed). Not a problem; expected behavior in a fresh `.venv` in a freshly-detached worktree.

## User Setup Required

None — no external service configuration introduced by this plan. The new env var has a sensible default (30) and is purely a developer/CI knob.

## Next Phase Readiness

- `cfg.mcp_server.timeout_seconds` is now available for plan 02-02 (`McpTestClient`) to pass into `asyncio.timeout(...)` per D-06.
- `tests/unit/test_config.py` now has 10 passing tests; the precedence-test pattern is in place for future env vars added to sub-models.
- `pyproject.toml` markers / `addopts` for `live_homelab` remain untouched (those land in plan 02-03 alongside the smoke test) — no carryover blocker.

## Self-Check: PASSED

- Files claimed:
  - `README.md` — FOUND
  - `src/mcp_test_framework/models.py` — FOUND (timeout_seconds field at line ~58)
  - `.env.example` — FOUND (MCP_SERVER_TIMEOUT_SECONDS=30 present)
  - `config.example.yaml` — FOUND (`  timeout_seconds: 30` under `mcp_server:`)
  - `tests/unit/test_config.py` — FOUND (10 tests)
- Commits claimed (verified via `git log --oneline`):
  - `459e3a8` — FOUND
  - `49ecbb2` — FOUND
  - `597692e` — FOUND
- Test results: `uv run pytest` → 25/25 passed
- Lint: `uv run ruff check src tests` → All checks passed!

---
*Phase: 02-mcp-client-wrapper*
*Completed: 2026-05-05*
