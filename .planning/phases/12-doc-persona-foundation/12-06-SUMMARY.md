---
phase: 12-doc-persona-foundation
plan: 06
subsystem: docs
tags: [docs, persona, scrub, regression-guard]
requirements: [CLEAN-01, CLEAN-04, PERSONA-01]
dependency_graph:
  requires:
    - 12-03 (examples/homelab-mcp.yaml exists for README link list)
  provides:
    - operator-tone README (zero spec-IDs, persona framing, link to both examples)
    - operator-tone EXTENDING (zero spec-IDs, 4-step walkthrough)
    - tests/unit/test_doc_scrub.py regression guard for all 4 user-facing files
  affects:
    - phase 13 (SAFE) — README no longer advertises TARGET_TOOL_NAME (D-03 forward-compat)
    - phase 14 (RUNNER) — sample-run section purposely lightly edited; full rewrite when domain UI lands
tech-stack:
  added: []
  patterns:
    - per-section semantic rewrite (D-10) — every leak edit hand-rewritten, no regex strip
    - locked persona phrase verbatim in two files (CONTEXT.md `<specifics>`)
    - banned-token regression guard (mirrors v1.1 banned-imports test pattern)
key-files:
  created:
    - tests/unit/test_doc_scrub.py
  modified:
    - README.md
    - docs/EXTENDING.md
decisions:
  - D-10 honored — every edit is a per-section semantic rewrite, no dangling sentences
  - D-12 honored — PERSONA-01 framing paragraph in README + walkthrough in EXTENDING (deep-link resolves)
  - D-14 honored — README link list points at BOTH config.example.yaml (template) AND examples/homelab-mcp.yaml (worked example)
  - D-03 honored forward — TARGET_TOOL_NAME stripped from README so Phase 13 can drop the field cleanly
metrics:
  duration_minutes: ~12
  completed_at: 2026-05-09
  tasks_completed: 4
  commits: 4
  files_changed: 3
  tests_added: 10
---

# Phase 12 Plan 06: README + EXTENDING Operator Reframe Summary

Per-section semantic rewrites scrub 13 spec-ID / file:line / phase-ID leaks from README.md (7) and docs/EXTENDING.md (6); land the PERSONA-01 "Testing an MCP server you didn't write" framing paragraph in README + 4-step walkthrough in EXTENDING; expand the README link list to point at BOTH config.example.yaml (placeholder template) and examples/homelab-mcp.yaml (worked example); and lock the contract with a 10-test regression guard at tests/unit/test_doc_scrub.py.

## What Changed

- **README.md** — 7 leak sites scrubbed: `TARGET_TOOL_NAME` row removed (D-03 forward-compat), TOOLCFG-03 reserved-field cells rewritten, sample-run sentence reframed away from `TARGET_TOOL_NAME`, rubric-failure paragraph rewritten in operator tone, Phase 04.1 troubleshooting reference replaced with "an earlier release", `config.example.yaml` link bullet expanded to two bullets per CLEAN-04. New top-of-file `## Testing an MCP server you didn't write` H2 section landed with the locked black-box framing sentence and a deep-link to the EXTENDING walkthrough.
- **docs/EXTENDING.md** — 6 leak sites scrubbed: TOOLCFG-06 parenthetical removed, two `_isolation.py:NN-NN` file:line citations dropped, DOC-07/Phase 10 parenthetical dropped from the warning quote, Phase 06 D-07 reference replaced with "the current allowlist", `06-VERIFICATION.md` + `MILESTONE-AUDIT` history-of-decision bullet rewritten as standalone rationale. New `## Testing an MCP server you didn't write` walkthrough inserted as the FIRST section after the intro, with Step 1 (discover via `list-tools`), Step 2 (scaffold via `config-init`), Step 3 (opt-in tool-by-tool), Step 4 (run).
- **tests/unit/test_doc_scrub.py** — 10 new regression tests: per-file banned-token grep for all four user-facing files (README, EXTENDING, config.example.yaml, .env.example), persona-heading existence checks for both files, README link-to-both contract, README has-locked-phrase check, README persona-section anti-marketing check (Pitfall 5).

## Tasks Completed

| Task | Name                                                       | Commit  | Files                          |
| ---- | ---------------------------------------------------------- | ------- | ------------------------------ |
| 1    | Scrub README.md (CLEAN-01 — 7 leak sites)                  | 632a1aa | README.md                      |
| 2    | Add PERSONA-01 framing section to README.md (D-12)         | bd0ab72 | README.md                      |
| 3    | Scrub docs/EXTENDING.md (6 leaks) + PERSONA-01 walkthrough | 1f7a25b | docs/EXTENDING.md              |
| 4    | Wave-0 banned-token regression guard                       | 4954feb | tests/unit/test_doc_scrub.py   |

## Verification

- `uv run pytest tests/unit/test_doc_scrub.py -x` → **10 passed in 0.03s**
- `uv run pytest tests/unit/test_doc_scrub.py tests/unit/test_dotenv_example.py tests/unit/test_config_example.py tests/unit/test_examples_dir.py tests/unit/test_error_style.py -x` → **35 passed in 0.08s** (proves Plans 01/02/03/06 regression-guards co-exist cleanly)
- `uv run pytest tests/unit/ -x` → **136 passed in 0.46s** (no upstream regression)
- Manual: `uv run python -c "import re; t=open('README.md').read(); ...banned-token grep..."` → OK
- Manual: same banned-token grep on docs/EXTENDING.md → OK
- README persona heading + `#testing-an-mcp-server-you-didnt-write` deep-link both present and target heading exists in EXTENDING.md (deep link resolves on GitHub auto-anchor).

## Deviations from Plan

None — plan executed exactly as written. Edits 1-7 on README and Edits A-G on EXTENDING applied verbatim per the plan's leak-table line-targeted instructions; no architectural surprise.

`tests/test_readme_snippets.py` was confirmed leak-free of `TARGET_TOOL_NAME` references (verification step 4 noted this as a contingency that did not trigger).

## Threat Model Compliance

- T-12-16 (info-disclosure on README.md): mitigated — leak scrub strips file:line refs and internal spec IDs; tests/unit/test_doc_scrub.py prevents regression mechanically.
- T-12-17 (tampering on EXTENDING.md walkthrough): mitigated — example tool block (`list_keyring_credentials(service: str)`) is illustrative; no behavioral guidance injected.
- T-12-18 (repudiation on test guard): accepted — banned-token grep is mechanical and passes/fails deterministically.

## Phase 12 Success-Criterion #2 Status

With Plan 06 landed, Phase 12's success-criterion #2 ("zero spec-IDs in README/config.example.yaml/.env.example/EXTENDING") is satisfied across all four files. Plans 01-05 cleared the other three; Plan 06 closes the README + EXTENDING surface and locks the contract with a regression test.

## Self-Check: PASSED

- README.md: modified, contains 'Testing an MCP server you didn\'t write', no TARGET_TOOL_NAME
- docs/EXTENDING.md: modified, contains the walkthrough heading, no _isolation.py:NN-NN refs
- tests/unit/test_doc_scrub.py: created, 10 tests pass
- Commit 632a1aa (README scrub): present in git log
- Commit bd0ab72 (README persona): present in git log
- Commit 1f7a25b (EXTENDING scrub + walkthrough): present in git log
- Commit 4954feb (test_doc_scrub.py): present in git log
