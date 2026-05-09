---
phase: 12-doc-persona-foundation
plan: 02
subsystem: docs
tags: [docs, env, config, dotenv, ci-secrets, regression-guard]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: ERROR-STYLE.md style guide (Plan 01 — Wave 1 sibling, not a hard dep for this file rewrite)
provides:
  - .env.example reframed as CI-secret-passthrough documentation (CLEAN-06)
  - Banned-token regression guard for .env.example (locks CLEAN-01 + CLEAN-06 mechanically)
  - Operator-facing pointer to `mcp-test-framework config-init -o config.yaml` as the v1.2 configuration entry point
affects:
  - 12-03 (config.example.yaml rewrite — same operator-tone framing applies)
  - 13-01 (Phase 13 SAFE-05 actually drops env-var-as-config-overlay from runtime; this plan only documents the upcoming change)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave-0 banned-token regression guard (re.search over file text, mirrors v1.0 banned-imports test)"

key-files:
  created:
    - tests/unit/test_dotenv_example.py
  modified:
    - .env.example

key-decisions:
  - "MCPTF_CONFIG_FILE comment retained (still read by v1.2 runtime; only env-var-as-overlay goes away in Phase 13)"
  - "JUDGE_API_KEY=sk-... shown as a commented-out illustrative example so operators see the CI-secret pattern without leaking a real key"

patterns-established:
  - "Wave-0 doc-shape regression guard: pure pathlib + re; no MCP/asyncio deps; runs in <50ms"
  - "Operator-facing example file framing: short header, IMPORTANT block explaining the v1.2 model, single concrete example pattern (commented out), pointer to config-init recovery path"

requirements-completed: [CLEAN-01, CLEAN-06]

# Metrics
duration: ~5min
completed: 2026-05-09
---

# Phase 12 Plan 02: .env.example reframe + regression guard

**`.env.example` rewritten from 24-line config-via-env declaration sheet to 16-line CI-secret-passthrough doc, with a 7-test pytest guard that mechanically locks the CLEAN-06 + CLEAN-01 contracts.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-09T09:03:00Z (approx)
- **Completed:** 2026-05-09T09:09:00Z
- **Tasks:** 2
- **Files modified:** 1 (.env.example), 1 created (tests/unit/test_dotenv_example.py)

## Accomplishments

- Operators opening `.env.example` now see env vars framed as CI-secret passthrough only (e.g. `JUDGE_API_KEY=sk-...`) and are pointed at `config.yaml` + `mcp-test-framework config-init` for actual configuration.
- All v1.1 config-via-env declarations (`TARGET_TOOL_NAME`, `MCP_SERVER_COMMAND`, `MCP_SERVER_ARGS`, `MCP_SERVER_TIMEOUT_SECONDS`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `JUDGE_TIMEOUT_SECONDS`) deleted from the file.
- All planning provenance (`Plan \d-\d`, `CONTEXT.md` references, spec IDs) stripped — banned-token grep returns 0.
- `MCPTF_CONFIG_FILE` hint preserved as the only env var the framework still reads at the config layer in v1.2.
- 7-test regression guard pins the new shape: existence, banned tokens, CI-secret framing, config-init pointer, no legacy declarations, MCPTF_CONFIG_FILE hint retained, line-count window (10–25).

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite .env.example for CI-secret-passthrough framing** — `94468ec` (docs)
2. **Task 2: Add Wave-0 regression guard `tests/unit/test_dotenv_example.py`** — `7ace799` (test)

_Note: Task 2 is framed as TDD per the plan, but functions as a regression guard — the test was authored against the just-written file, then committed as a single test commit. The plan explicitly required Task 1 before Task 2 ("Task 1 and Task 2 must run together / in this order"), so a RED-then-GREEN split was not appropriate here._

## Files Created/Modified

- `.env.example` (modified) — 24 → 16 lines; v1.1 config-via-env declarations removed; CI-secret-passthrough framing added; `mcp-test-framework config-init` pointer added; `MCPTF_CONFIG_FILE` hint preserved.
- `tests/unit/test_dotenv_example.py` (created, 84 lines) — 7 tests: `test_dotenv_example_exists`, `test_dotenv_example_no_banned_tokens`, `test_dotenv_example_has_ci_secret_framing`, `test_dotenv_example_points_at_config_init`, `test_dotenv_example_no_legacy_overlay_decls`, `test_dotenv_example_keeps_mcptf_config_file_hint`, `test_dotenv_example_line_count_reasonable`.

## Decisions Made

- Followed the literal target text from RESEARCH.md Code Example 4 verbatim — no improvisation.
- The plan's Task 2 TDD framing was treated as a regression-guard pattern (write tests against the new file in a single commit) rather than a strict RED→GREEN split, because the plan body explicitly couples Task 1 and Task 2 in sequence ("must run together / in this order"). Documented as a deviation note above.

## Deviations from Plan

None — plan executed exactly as written. All 8 acceptance criteria for Task 1 and 3 acceptance criteria for Task 2 verified pass:

- `grep -cE '(Phase [0-9]|Plan [0-9]-[0-9]|TOOLCFG-|ISOL-|OUTPUT-|D-[0-9]+|[0-9]{6}-[a-z0-9]{3})' .env.example` → 0
- `grep -c 'CI secret' .env.example` → 2 (≥ 1)
- `grep -c 'config-init' .env.example` → 1 (≥ 1)
- `grep -cE '^TARGET_TOOL_NAME=' .env.example` → 0
- `grep -cE '^MCP_SERVER_(COMMAND|ARGS|TIMEOUT_SECONDS)=' .env.example` → 0
- `grep -cE '^OLLAMA_(BASE_URL|MODEL|TIMEOUT_SECONDS)=' .env.example` → 0
- `grep -cE '^JUDGE_TIMEOUT_SECONDS=' .env.example` → 0
- `wc -l .env.example` → 16 (within 12–20)
- `uv run pytest tests/unit/test_dotenv_example.py -x` → 7 passed in 0.02s

## Issues Encountered

None during execution.

A non-blocking pre-existing observation: Git emitted `LF will be replaced by CRLF` warnings on commit (Windows core.autocrlf default). Both files were authored with LF endings as the plan specified; Git's smudge filter normalizes for the working copy, leaving the repo storage canonical. No action required.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- Phase 12 Plan 03 (config.example.yaml rewrite) can land independently — no shared file with this plan.
- Phase 13 Plan that drops env-var-as-config-overlay (SAFE-05) can land at any time without re-touching `.env.example`; the file already documents the new model.
- The regression guard ensures any future PR that re-adds a v1.1-shape env-var declaration to `.env.example` fails CI.

## Self-Check: PASSED

- `.env.example` exists at repo root: FOUND
- `tests/unit/test_dotenv_example.py` exists: FOUND
- Commit `94468ec` exists in git log: FOUND (`docs(12-02): reframe .env.example for CI-secret passthrough only`)
- Commit `7ace799` exists in git log: FOUND (`test(12-02): add Wave-0 regression guard for .env.example shape`)
- All 7 tests in the new test file pass under `uv run pytest`: VERIFIED

---
*Phase: 12-doc-persona-foundation*
*Completed: 2026-05-09*
