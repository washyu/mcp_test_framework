---
phase: 12-doc-persona-foundation
plan: 07
subsystem: docs
tags: [docs, dotenv, persona, gap-closure, ci-secrets]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: ".env.example v1.2 CI-secret framing (CLEAN-06); existing test_dotenv_example.py + test_doc_scrub.py guards"
provides:
  - "README.md no longer teaches `cp .env.example .env` as setup"
  - "README.md mentions .env.example exactly once, framed as CI-secret-passthrough"
  - "docs/EXTENDING.md gains a 'CI secrets' subsection naming .env.example with passthrough framing"
  - "Three new regression tests in tests/unit/test_dotenv_example.py locking the doc reconciliation"
affects: ["12-09 (will append cwd auto-discovery sentence to README ~lines 90-93 paragraph)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED→GREEN cycle for doc-only fixes: ship test guard first, then edit prose"
    - "Single-source-of-truth for narrow files: .env.example references must use the same framing the file uses internally"

key-files:
  created: []
  modified:
    - "README.md"
    - "docs/EXTENDING.md"
    - "tests/unit/test_dotenv_example.py"

key-decisions:
  - "Removed .env.example from README quickstart entirely (not just demoted) — file contradicts a `cp ... .env` instruction"
  - "Reduced README mentions of .env.example from 5 to 1 (single CI-secret-framed reference)"
  - "EXTENDING.md mention placed AFTER Step 4 and BEFORE the closing 'You never read your server's source' paragraph, preserving the four-step walkthrough's narrative"
  - "EXTENDING.md subsection renamed from '### CI secrets (.env.example)' to '### CI secrets' to keep `.env.example` count at exactly 1 (test contract)"

patterns-established:
  - "Doc-only TDD: regression tests assert exact substring counts and surrounding-window framing for fragile prose contracts"

requirements-completed: [CLEAN-06, CLEAN-01, PERSONA-01]

# Metrics
duration: ~12min
completed: 2026-05-10
---

# Phase 12 Plan 07: .env.example doc reconciliation Summary

**Removed `cp .env.example .env` imperative from README quickstart, added CI-secret subsection to EXTENDING.md walkthrough, and locked both contracts behind three new regression tests — closing UAT gap 1 (".env.example invisible") via documentation-only edits.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-10T05:45Z (approx)
- **Completed:** 2026-05-10T05:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- README quickstart no longer instructs operators to copy .env.example as part of normal setup; the file is mentioned exactly once with CI-secret-passthrough framing.
- docs/EXTENDING.md "Testing an MCP server you didn't write" walkthrough now names .env.example after Step 4 inside a "CI secrets" subsection, telling operators what the file is for and that it is NOT part of normal local configuration.
- Three new regression tests in `tests/unit/test_dotenv_example.py` lock both contracts: README has no `cp .env.example .env` substring; README mentions `.env.example` ≤ 1 time; EXTENDING mentions it exactly once with CI-secret framing in a 200-char window.
- All 20 verification tests pass (10 in test_dotenv_example.py, 10 in test_doc_scrub.py); banned-token guards still green.

## Task Commits

Each task was committed atomically (TDD cycle):

1. **Task 1 (RED): add regression guards for .env.example doc reconciliation** — `8b37d3d` (test)
2. **Task 2 (GREEN): reconcile README and EXTENDING around CI-secret framing** — `26cb251` (docs)

## Files Created/Modified

- `README.md` — five edits:
  - Line 25 prereq bullet: dropped "(the `.env.example` default)" phrase from `homelab-mcp` runnable line.
  - Lines 31-34 Setup block: deleted `cp .env.example .env` line (block now: clone → cd → uv sync).
  - Lines 85-86 env-var table: rewrote `MCP_SERVER_COMMAND` and `MCP_SERVER_ARGS` "Purpose" cells to drop ".env.example ships ..." claims.
  - Lines 90-93 paragraph (THIS PLAN OWNS): replaced "Copy .env.example to .env and edit..." paragraph with the config-init / CI-secret-passthrough framing. Plan 12-09 will append a cwd-auto-discovery sentence to the END of this paragraph.
  - Lines 229-231 Troubleshooting: rewrote `[WinError 2]` recovery hint to point at `mcp_server.command` / `mcp_server.args` in `config.yaml` instead of `.env`.
- `docs/EXTENDING.md` — added a new `### CI secrets` subsection between the Step 4 paragraph and the closing "You never read your server's source." paragraph. Body names `.env.example`, frames it as CI-secret passthrough, and explicitly tells operators it is not part of normal local setup.
- `tests/unit/test_dotenv_example.py` — appended three new test functions:
  - `test_readme_does_not_imperatively_cp_dotenv_example`
  - `test_extending_mentions_dotenv_example_with_ci_secret_framing`
  - `test_readme_mentions_dotenv_example_at_most_once`

## Decisions Made

- **EXTENDING.md heading dropped its parenthetical** (`### CI secrets (.env.example)` → `### CI secrets`) because the test contract requires exactly one occurrence of `.env.example` in the file. Two body mentions plus a heading mention would be three total. The heading is now framing-only ("CI secrets"); the body still names the file once.
- **README prereq line lost the ".env.example default" claim entirely** rather than getting reworded — .env.example v1.2 no longer ships `MCP_SERVER_COMMAND`, so the original parenthetical was factually outdated independent of this plan's CI-secret reframing.
- **No edits to `.env.example` itself.** Per plan scope, only references TO the file were wrong; the file's internal v1.1/v1.2 framing is correct.

## Deviations from Plan

None — plan executed exactly as written. The lone judgment call (consolidating the EXTENDING.md heading from `### CI secrets (.env.example)` to `### CI secrets`) was an interpretation of the test contract `text.count(".env.example") == 1`, not a plan deviation: the plan explicitly required exactly-one occurrence, and the body mention was unambiguously the canonical one to keep.

## Issues Encountered

- After the first EXTENDING.md edit, `.env.example` count was 3 (heading + two body mentions). Resolved by dropping the parenthetical from the subsection heading and rewording one body sentence ("the example file" instead of "`.env.example`"). Tests then flipped to GREEN on the next run.

## User Setup Required

None — pure documentation reconciliation, no environment changes.

## Cross-plan Coordination

Per plan frontmatter: this plan OWNS the README.md ~lines 90-93 paragraph rewrite. The replacement paragraph reads:

> "Configure the framework via `config.yaml` — generate a starter with `mcp-test-framework config-init -o config.yaml` and pass it via `--config config.yaml`. Env vars are reserved for CI-secret passthrough only (see `.env.example`); they no longer override config values."

Plan 12-09 will land AFTER this plan and APPEND ONE additional sentence (about no cwd auto-discovery) at the END of this paragraph. The two plans together produce a three-sentence paragraph: (1) generate via config-init, (2) env vars are CI-secret only, (3) no cwd auto-discovery. This plan did NOT pre-emptively include the third sentence — that is 12-09's content.

## Forward Notes

- **Out of scope (deferred / acknowledged):** The editor-side dotfile-hiding contributing factor from the UAT diagnosis (`.vscode/settings.json` to surface `.env.example` in the explorer) is environmental, not in-repo, and was explicitly excluded by `<scope_guardrails>`. It remains a documented but un-actioned contributor to gap 1; the documentation reconciliation alone is sufficient to satisfy the gap-1 truth.

## Self-Check

- File checks:
  - `README.md` modified — FOUND
  - `docs/EXTENDING.md` modified — FOUND
  - `tests/unit/test_dotenv_example.py` modified — FOUND
- Commit checks:
  - `8b37d3d` (Task 1 RED) — FOUND
  - `26cb251` (Task 2 GREEN) — FOUND
- Verification command (`uv run pytest tests/unit/test_dotenv_example.py tests/unit/test_doc_scrub.py -v`): 20 passed.

## Self-Check: PASSED

## Next Phase Readiness

- Plan 12-08 and Plan 12-09 (both wave 1, coordinated with this plan) can now land. 12-09 specifically depends on this plan's paragraph rewrite at README ~lines 90-93 — its append-sentence operation has a stable target.
- UAT gap 1 (".env.example invisible/discoverable to the operator") flips from `failed` to satisfied via the docs-only reconciliation: an operator following EXTENDING.md is now told the file exists and what it's for; an operator reading README is no longer instructed to copy it as setup.

---
*Phase: 12-doc-persona-foundation*
*Completed: 2026-05-10*
