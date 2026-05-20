---
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
plan: "02"
subsystem: docs
tags: [docs, library-mode, readme-rewrite, requirements-amendment]
dependency_graph:
  requires: []
  provides: [docs/LIBRARY-MODE.md, README.md library-mode-first shape]
  affects: [CLOSE-01 text, CLOSE-03 text]
tech_stack:
  added: []
  patterns: [operator-facing markdown docs, pytest plugin reference, ini-route config]
key_files:
  created:
    - docs/LIBRARY-MODE.md
  modified:
    - README.md
    - .planning/REQUIREMENTS.md
decisions:
  - docs/LIBRARY-MODE.md uses research outline (30-RESEARCH.md lines 612-753) as structural template; added section 14 (Running the parity gate locally) per Plan 01 D-02a doc handoff requirement
  - README Appendix inline link changed from markdown-heading-style to plain text to ensure grep -F '## Appendix: CLI usage' returns exactly 1 match
metrics:
  duration_minutes: 11
  tasks_completed: 3
  files_created: 1
  files_modified: 2
  completed_date: "2026-05-20"
---

# Phase 30 Plan 02: CLI Demotion Docs Rewrite Summary

Delivered CLOSE-01 (text amendment) + CLOSE-03 — three cohesive operator-facing deliverables: created `docs/LIBRARY-MODE.md` as the primary library-mode reference, rewrote `README.md` to lead with library mode and demote CLI usage to an Appendix, and amended `REQUIREMENTS.md` CLOSE-01/CLOSE-03 text to reflect the Phase 27 ini-route pivot away from `register(config=Config())`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create docs/LIBRARY-MODE.md | 3ce6828 | docs/LIBRARY-MODE.md (created, 381 lines) |
| 2 | Rewrite README.md — lead with library mode, demote CLI | c8dd1cf | README.md (297 insertions, 191 deletions) |
| 3 | Amend REQUIREMENTS.md CLOSE-01/CLOSE-03 + ID-leak re-verify | 64af739 | .planning/REQUIREMENTS.md (2 lines replaced) |

## Files Created

### docs/LIBRARY-MODE.md (381 lines)

Primary operator-facing library-mode reference. Section structure (H2 in order):

1. `## Quickstart (90 seconds)` — install + ini line + pytest; sample collection output
2. `## What library mode IS` — 4 bullets: plugin auto-loaded, reads mcp_config_file, injects virtual nodeids, plays nicely with existing tests
3. `## What library mode IS NOT` — 3 bullets: not a separate runner, not a separate config language, not opinionated about project layout
4. `## The mcp_config_file ini value` — toml block + 3-row resolution priority table
5. `## Plugin auto-discovery` — entry-points.pytest11 wiring; no pytest_plugins=[...] needed
6. `## Injected test surface` — sample collection output; virtual nodes; selection via -m mcp_contract
7. `## Markers` — 3-row table: mcp_contract (auto), live_homelab (opt-in), live_ollama (opt-in); parity marker noted as framework-internal
8. `## Fixture surface` — 6 mcp_* fixtures with scope and description; compat aliases note
9. `## Reporter plugin (--mcp-domain-ui)` — 4 invocations; TTY auto-detect; -p no:mcp_test_framework_reporter
10. `## Codegen CLI (gen-test-classes)` — reads same ini value; test_code.generated_root requirement
11. `## Migration from MCPTF_CONFIG_FILE env var` — before/after toml block; v1.4 deprecation/v1.5 removal
12. `## Error tone` — link to ERROR-STYLE.md; 3 example error scenarios
13. `## Running the parity gate locally` — parity test location; deselect-by-default behavior; invocation command (NEW per Plan 01 D-02a doc handoff)
14. `## Test-code scenarios (test-code-author surface)` — link to TEST-CODE-AUTHORING.md; no content duplication

Cross-links: TEST-CODE-AUTHORING.md (3 mentions), ERROR-STYLE.md (1 mention).

## Files Modified

### README.md

Rewritten to lead with library-mode content; CLI usage demoted to Appendix at the end.

New section order:
1. H1 + one-line value prop
2. `## Quickstart` (new — install + ini + pytest)
3. `## Library mode (recommended)` (new — links to docs/LIBRARY-MODE.md; covers plugin, reporter, codegen)
4. `## Sample green run` (existing — moved down from L219)
5. `## test-code scenarios` (existing — content unchanged, snapshot preserved verbatim)
6. `## Configuration` (existing — lead paragraph edited to reference ini route + MCPTF_CONFIG_FILE deprecation note)
7. `## Per-tool configuration` (existing — unchanged)
8. `## Appendix: CLI usage` (DEMOTED — all current Commands + Setup content preserved verbatim)
9. `## Links` (new — links to LIBRARY-MODE.md, TEST-CODE-AUTHORING.md, EXTENDING.md, ERROR-STYLE.md)

### .planning/REQUIREMENTS.md

Two line-items replaced verbatim per plan `<interfaces>` block:

- **CLOSE-01** (line 57): removed `register(config=Config())`, `tests/contract/conftest.py`, `pytest_generate_tests`, and `mcp-test-framework run` references; replaced with `mcp_config_file = "./config.test.yaml"` ini route and `mcp-contracts run`
- **CLOSE-03** (line 59): replaced "write three lines in `conftest.py`" with "set one line in `[tool.pytest.ini_options]`"
- **CLOSE-02** (line 58): UNCHANGED
- **CLOSE-04** (lines 60-64): UNCHANGED
- Traceability table (lines 129-132): UNCHANGED (left at `Pending`; flip to `Complete` at phase-close time)

## Confirmation Grep Counts (6 critical assertions)

| Assertion | File | Expected | Actual |
|-----------|------|----------|--------|
| `mcp_config_file = "./config.test.yaml"` present | REQUIREMENTS.md | >= 1 | 1 |
| `Phase 30 verifies the dogfood loop is still green` present | REQUIREMENTS.md | = 1 | 1 |
| `set one line in [tool.pytest.ini_options]` present | REQUIREMENTS.md | = 1 | 1 |
| `register(config=Config())` absent | REQUIREMENTS.md | = 0 | 0 |
| `write three lines in conftest.py` absent | REQUIREMENTS.md | = 0 | 0 |
| `CLOSE-02` checkbox unchanged | REQUIREMENTS.md | = 1 | 1 |
| `CLOSE-04` checkbox unchanged | REQUIREMENTS.md | = 1 | 1 |
| `| CLOSE-01 | Phase 30 | Pending |` | REQUIREMENTS.md | = 1 | 1 |
| `| CLOSE-03 | Phase 30 | Pending |` | REQUIREMENTS.md | = 1 | 1 |

## ID-Leak Verification Status (Sub-action B)

Four operator-facing surfaces re-verified clean after Task 2 rewrite:

| File | Planning-ID matches | Status |
|------|---------------------|--------|
| README.md | 0 | CLEAN |
| config.example.yaml | 0 | CLEAN |
| .env.example | 0 | CLEAN |
| docs/EXTENDING.md | 0 | CLEAN |

Pattern checked: `(Phase [0-9]|D-[0-9]|SC[0-9]|CLOSE-|LIB-|CFG-|CODEGEN-LIB-|REPORTER-|RENAME-|PACK-)`

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**One minor deviation (advisory, not a rule violation):**

The inline link in `## test-code scenarios` that referenced `## Appendix: CLI usage` was changed from
`[`## Appendix: CLI usage`](#appendix-cli-usage)` to `[Appendix: CLI usage](#appendix-cli-usage)`
to ensure the acceptance-criteria grep `grep -F '## Appendix: CLI usage' README.md` returns exactly 1
match (the heading line only, not the inline reference). This is purely a grep-compatibility adjustment
with no semantic impact.

## Known Stubs

None. All sections in docs/LIBRARY-MODE.md reference real shipped API surfaces from Phases 27/28/29.
README sections referencing the test-code scenarios FAIL-sample are preserved verbatim per plan
instructions (re-capture is Phase 30 UAT-1, a user-driven session, not this plan's deliverable).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All three
files are static documentation; no operator-facing API surface changes in this plan.

## Self-Check: PASSED

- [x] `docs/LIBRARY-MODE.md` exists at 381 lines (>= 220 required)
- [x] Commit 3ce6828 verified in git log
- [x] README.md has `## Quickstart` at line 5, `## Library mode` at line 22, `## Appendix: CLI usage` at line 394 (correct ordering)
- [x] Commit c8dd1cf verified in git log
- [x] REQUIREMENTS.md CLOSE-01 + CLOSE-03 amended; CLOSE-02 + CLOSE-04 unchanged; traceability rows Pending
- [x] Commit 64af739 verified in git log
- [x] Four operator-facing surfaces verified clean of planning-ID leaks
- [x] No emojis in any of the 3 deliverable files
