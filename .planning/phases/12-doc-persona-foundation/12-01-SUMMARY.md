---
phase: 12-doc-persona-foundation
plan: 01
subsystem: docs
tags: [docs, error-style, examples, persona, wave-0-scaffold]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: phase context (CONTEXT.md decisions D-11/D-15/D-16/D-17, RESEARCH.md skeleton)
provides:
  - "docs/ERROR-STYLE.md — citation target for every Phase 12 error rewrite"
  - "SAFE-03 reference message body (verbatim, locked)"
  - "SAFE-06 reference message body (verbatim, locked)"
  - "examples/ directory + naming-convention README"
  - "Wave-0 drift guards (test_error_style.py, test_examples_dir.py)"
affects:
  - 12-02 (CLEAN-01 README/EXTENDING.md sweep — cites ERROR-STYLE.md style)
  - 12-03 (CLEAN-02..06 — populates examples/homelab-mcp.yaml beside README)
  - 12-04 (PERSONA-03 error rewrites in cli.py / config.py — copy from ERROR-STYLE.md)
  - 12-05 + 12-06 (PERSONA-01/02 README + list-tools — share operator-tone bar)
  - 13-* (SAFE-03 / SAFE-06 implementations copy locked bodies verbatim)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Locked-text drift guards via banned-token regex tests (4 tests pin SAFE-03/SAFE-06 verbatim)"
    - "Operator-facing prose excludes spec IDs / phase IDs / file:line refs (mechanical regression guard)"
    - "Wave-0 scaffold pattern: drop tests beside the doc/code surface that proves the contract before the consuming phase lands"

key-files:
  created:
    - "docs/ERROR-STYLE.md"
    - "examples/README.md"
    - "tests/unit/test_error_style.py"
    - "tests/unit/test_examples_dir.py"
  modified: []

key-decisions:
  - "Reworded two 'Phase 13' meta-prose lines in ERROR-STYLE.md to 'downstream config-safety work' / 'downstream implementations' so the file's own no-spec-ID rule applies to itself"
  - "examples/homelab-mcp.yaml drift guard uses pytest.mark.skipif (not xfail) so Plan 03's git mv is an additive landing, not a flip"

patterns-established:
  - "Banned-token drift-guard pattern: split file at known section heading, regex-scan only the prose half, exempt the documented-pattern checklist"
  - "Repo-root resolver via pyproject.toml ascent (mirrors tests/unit/test_config.py convention)"

requirements-completed: [PERSONA-03]

# Metrics
duration: ~12min
completed: 2026-05-09
---

# Phase 12 Plan 01: Doc & persona foundation Summary

**docs/ERROR-STYLE.md (4 rules + exit-code table + SAFE-03/SAFE-06 locked verbatim) and examples/README.md ship with two Wave-0 drift-guard test files (7 passing, 1 correctly skipped pending Plan 03 yaml).**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-09T08:58Z (worktree branch reset to base)
- **Completed:** 2026-05-09T09:10Z
- **Tasks:** 3
- **Files created:** 4

## Accomplishments

- Operator-grade error style guide landed at `docs/ERROR-STYLE.md` — four rules, 8-row exit-code contract table, SAFE-03 + SAFE-06 reference messages locked verbatim per D-17, and a banned-strings checklist that names the patterns Phase 12+ rewrites must avoid.
- `examples/` directory bootstrapped with a 17-line naming-convention README (D-11) — Plan 03 will drop `homelab-mcp.yaml` beside it via `git mv`.
- Two Wave-0 drift guards (`tests/unit/test_error_style.py` + `tests/unit/test_examples_dir.py`) pin the locked SAFE-03/SAFE-06 bodies, the banned-token regression rule, and the examples-README contract. Total: 7 PASS + 1 SKIP (homelab-mcp.yaml — Plan 03 closes the loop).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write docs/ERROR-STYLE.md (D-15, D-16, D-17)** — `bb4da61` (docs)
2. **Task 2: Write examples/README.md (D-11)** — `4a067e6` (docs)
3. **Deviation fix (Rule 1) — strip 'Phase 13' from ERROR-STYLE.md meta-prose** — `96d1137` (fix)
4. **Task 3: Add Wave-0 scaffolds (test_error_style.py, test_examples_dir.py)** — `91b2bd9` (test)

## Files Created/Modified

- `docs/ERROR-STYLE.md` — Operator-facing error style guide; cited by Phase 12+ error rewrites; locks SAFE-03/SAFE-06 message bodies for Phase 13.
- `examples/README.md` — One-server-per-file convention, links to homelab-mcp.yaml (Plan 03 lands the YAML).
- `tests/unit/test_error_style.py` — 4 tests (file-exists, SAFE-03 verbatim, SAFE-06 verbatim, banned-tokens-outside-checklist).
- `tests/unit/test_examples_dir.py` — 4 tests (README exists, links homelab-mcp.yaml, no spec IDs, homelab-mcp.yaml exists [skipif until Plan 03]).

## Decisions Made

- **Reworded `Phase 13` meta-prose in ERROR-STYLE.md.** Plan acceptance criteria for Task 1 ban `Phase \d` outside the documented checklist, and the Wave-0 banned-token test enforces the same rule. Two prose lines that introduced the locked reference messages used the phrase "Phase 13 implements" — both reworded to "downstream config-safety work" and "downstream implementations" so the guide's own rule applies to itself. SAFE-03 and SAFE-06 message bodies were untouched (their lock contract takes precedence).
- **Skipif (not xfail) on the homelab-mcp.yaml drift guard.** Plan 03 will land the YAML via `git mv config.example.yaml examples/homelab-mcp.yaml` — once present the test asserts file-exists + non-trivial size. xfail would require flipping the marker after Plan 03; skipif makes the landing additive (no test-file edit needed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed 'Phase 13' tokens from ERROR-STYLE.md meta-prose**
- **Found during:** Task 3 (running the Wave-0 banned-token test)
- **Issue:** The literal ERROR-STYLE.md skeleton in the plan text included two preamble lines using "Phase 13" ("Phase 13 will implement verbatim", "Phase 13 implements them verbatim"). The plan's own Task 1 acceptance criteria ban `\bPhase [0-9]` outside the banned-strings checklist, and the test (Task 3) enforces this mechanically. The skeleton conflicted with the rule it documents.
- **Fix:** Reworded both lines: "Phase 13 will implement verbatim" → "downstream config-safety work will implement verbatim"; "Phase 13 implements them verbatim" → "Downstream implementations copy them verbatim". SAFE-03 and SAFE-06 message bodies — which are explicitly locked verbatim — were untouched.
- **Files modified:** docs/ERROR-STYLE.md
- **Verification:** `uv run pytest tests/unit/test_error_style.py tests/unit/test_examples_dir.py -x` → 7 passed, 1 skipped (the test now passes; without the fix it failed at offsets 256 and 1670).
- **Committed in:** `96d1137` (separate fix commit between Task 2 and Task 3 because the bug was in already-committed Task 1 output)

---

**Total deviations:** 1 auto-fixed (1 bug — internal contradiction between the plan's locked-skeleton text and its own banned-token rule)
**Impact on plan:** Self-contained correction. No scope creep — preserves the locked SAFE-03/SAFE-06 message bodies and the four-rule structure. The fix actually strengthens the contract by making ERROR-STYLE.md follow its own rules.

## Issues Encountered

- **Plan-prose verification grep over-matches inside Rule 1.** The plan's `<verification>` block specifies `grep -nE '\b(Phase [0-9]|Plan [0-9]-[0-9]|TOOLCFG-|ISOL-|OUTPUT-|...)' docs/ERROR-STYLE.md` and says "the first match (if any) MUST be inside the '## Banned strings' checklist". After the Rule-1 fix, the grep still finds 3 matches — but all three are inside Rule 1's prose definition (line 11: ``` `TOOLCFG-`/`D-`/`CD-` ``` documenting what's banned) or the banned-strings checklist itself. None are in operator-facing message bodies. The Wave-0 test (`test_error_style_no_banned_tokens_outside_checklist`) uses a tighter regex (`\bTOOLCFG-\d` requires a digit) that correctly skips the rule-definition prose. The test is the authoritative drift guard going forward; the plan-level grep is a coarser human-eyeball check. Plan-author intent (Rule 1 must name the banned patterns to be a useful rule) is preserved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **For Plan 12-02 (CLEAN-01 README/EXTENDING.md sweep — wave 2):** `docs/ERROR-STYLE.md` is the citation target. Sweep can now reference the style guide whenever a sentence calls out an error message rewrite.
- **For Plan 12-03 (CLEAN-02..06 — wave 2):** `examples/README.md` already names `homelab-mcp.yaml` as the link target. Plan 12-03's `git mv config.example.yaml examples/homelab-mcp.yaml` lands beside the README and unfreezes the skipif-guarded `test_examples_homelab_mcp_yaml_exists`.
- **For Plan 12-04 (PERSONA-03 — wave 3):** `_emit_operator_error` rewrites copy the four-rule shape and cite the style guide. Banned-token test guards against drift in the SAFE-03/SAFE-06 bodies.
- **For Phase 13 (SAFE):** SAFE-03 and SAFE-06 message bodies are locked verbatim in `docs/ERROR-STYLE.md`. Phase 13 implementations are copy-paste, not redraft.
- **No blockers.** Wave-1 work (this plan) is hermetic — pure prose + tests, zero upstream code coupling.

## Self-Check: PASSED

- `docs/ERROR-STYLE.md` exists (verified)
- `examples/README.md` exists (verified)
- `tests/unit/test_error_style.py` exists (verified)
- `tests/unit/test_examples_dir.py` exists (verified)
- Commit `bb4da61` exists in `git log` (verified)
- Commit `4a067e6` exists in `git log` (verified)
- Commit `96d1137` exists in `git log` (verified)
- Commit `91b2bd9` exists in `git log` (verified)

---
*Phase: 12-doc-persona-foundation*
*Completed: 2026-05-09*
