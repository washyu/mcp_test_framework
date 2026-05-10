---
phase: 13-config-safety-opt-in-tool-selection
plan: 05
status: complete
completed: 2026-05-10
commits:
  - 4439f3f
  - e520aca
key-files:
  modified:
    - pyproject.toml
  created:
    - docs/MIGRATION-v1-to-v2.md
    - tests/unit/test_migration_doc.py
  deleted: []
---

# Plan 13-05: migration-doc — SUMMARY

## What was built

The standalone diff-driven port guide that the LOCKED SAFE-06 error message
in `src/mcp_test_framework/cli.py` points at, plus a regression test that
pins its load-bearing wording, plus a pyproject.toml comment audit.

### Task 1: docs/MIGRATION-v1-to-v2.md + regression test — commit `4439f3f`

- **`docs/MIGRATION-v1-to-v2.md`** (104 lines, 7 sections):
  1. Why this matters (plain-English opt-in vs opt-out contrast).
  2. What stays the same (per-tool fields port forward unchanged).
  3. What changes (5 itemized changes: version bump, target deletion,
     `.env` dead-letter, env vars dead-letter, unlisted -> auto-skip).
  4. Step-by-step port (7 numbered steps).
  5. Side-by-side per-tool example (before-v1 / after-v2 YAML diff).
  6. What about `.env`? (the dotenv coda).

- **`tests/unit/test_migration_doc.py`** (4 tests):
  - `test_migration_doc_exists` — file is present.
  - `test_migration_doc_pins_v2_keywords` — pins 6 load-bearing substrings.
  - `test_migration_doc_uses_ascii_dashes_not_emdash` — bans U+2014.
  - `test_migration_doc_does_not_leak_planning_ids` — same banned-token
    policy as `docs/ERROR-STYLE.md` (no Phase/Plan/spec-ID leakage).

### Task 2: pyproject.toml audit — commit `e520aca`

- Removed the misleading "(and python-dotenv)" parenthetical from the
  inline comment at `pyproject.toml:8`. Even if `mcp[cli]` still transitively
  pulls `python-dotenv`, calling it out is misleading now that the framework's
  config layer doesn't use it.
- Confirmed (grep gates green):
  - `grep -nE "dotenv|python-dotenv" pyproject.toml` returns ZERO matches.
  - `grep -rnE "import dotenv|from dotenv" src/` returns ZERO matches.
  - The `[project].dependencies` block retains its 4 deps: `mcp[cli]>=1.27`,
    `pydantic>=2.13,<3`, `pydantic-settings[yaml]>=2.14`, `jsonschema>=4.26`.

No code change was needed for the audit — Plan 13-02 already deleted the only
`from dotenv import dotenv_values` site at `config.py`. This plan closes the
audit and updates the now-stale comment.

## Acceptance gates — all green

- `Test-Path docs/MIGRATION-v1-to-v2.md` -> True.
- `grep -c "^" docs/MIGRATION-v1-to-v2.md` -> 104 (>= 60 required).
- The 5 pinned substrings (`version: 2`, `opt every tool in`,
  `config-init -o config.yaml.new`, `target:` deletion instruction,
  `not selected in config`, `.env` coda) all present.
- No em-dash, no planning-artifact tokens.
- `uv run pytest tests/unit/test_migration_doc.py -v` -> 4 passed.
- Plan 13-02's `test_error_style_safe_06_body_matches_cli_wiring` still passes
  (no regression on the cli.py-side pin).
- pyproject.toml audit gates all zero.

## Deviation: judge ID in YAML example

The plan's literal scaffold uses `judges: ["RUB-01"]` in both example YAMLs.
The regression test's banned-pattern check `\b[A-Z]{2,}-\d{2}\b` (catching
spec IDs like `SAFE-01`) also matches `RUB-01` — RUB-01 is a judge identifier
shape, not a planning artifact, but the regex can't tell them apart.

Resolution: changed the example's judge ID to `"clarity"` (a real rubric
name from `mcp_test_framework.rubrics.ClarityRubric`). This matches actual
operator usage better than a fictitious `RUB-01` ID and avoids the regex
false-positive without weakening the banned-pattern check for genuine
planning-ID leakage.

## Phase 13 status

With Plans 01-05 all complete, every SAFE-N requirement should be
delivered. Next step is `/gsd-execute-phase 13` orchestrator picking up at
the post-wave verification gates (code review + close artifacts + regression
gate + phase-goal verification).
