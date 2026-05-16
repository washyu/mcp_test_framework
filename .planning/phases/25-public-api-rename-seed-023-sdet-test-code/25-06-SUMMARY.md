---
phase: 25-public-api-rename-seed-023-sdet-test-code
plan: 06
subsystem: ci-gate / public-api-rename-acceptance
tags: [rename, sdet, test_code, ci-gate, RENAME-06, leak-detection]
requires:
  - tests/framework/ (pytest discovery scope)
  - post-plan-05 working tree (zero untagged matches established by plans 25-01..05)
  - D-16 scope, D-17 patterns, D-18 line-level exclusion semantic (locked in CONTEXT.md)
provides:
  - tests/framework/test_sdet_rename_leak_gate.py (CI-runnable RENAME-06 acceptance gate)
  - per-line shim tags on the 4 untagged README.md snapshot lines (348, 354, 416, 417)
  - permanent regression guard: Phase 26+ commits that reintroduce `sdet`-terminology or planning-ID leaks fail CI
affects:
  - tests/framework/test_sdet_rename_leak_gate.py (new; 152 lines)
  - README.md (4 lines suffix-tagged with `<!-- noqa: sdet-rename-shim -->` — Rule-1 deviation reaching back into plan-05 territory)
tech-stack:
  added: []
  patterns:
    - "ast.parse + ast.walk for docstring / Constant string-literal scanning inside src/mcp_test_framework/**/*.py (catches operator-visible string content without flagging _-prefixed identifier names per D-16)"
    - "Per-line noqa skip — `noqa: sdet-rename-shim` substring check honors both `# noqa: sdet-rename-shim` (.py) and `<!-- noqa: sdet-rename-shim -->` (.md); single marker string covers both comment styles"
    - "pytest.mark.parametrize × 2 patterns × 2 scopes = 4 test cases for clear operator failure attribution"
    - "Top-of-file comment scan as a separate pass (ast.walk doesn't surface comment nodes)"
    - "SyntaxError fallback to text-mode scan with noqa exclusion (defensive against half-applied patches)"
key-files:
  created:
    - tests/framework/test_sdet_rename_leak_gate.py (152 lines; 4 parametrize cases; RED on plan-05 baseline + 4 untagged README lines, GREEN after Task 1 tags applied)
  modified:
    - README.md (4 `<!-- noqa: sdet-rename-shim -->` suffix tags on lines 348, 354, 416, 417 inside the fenced ```text snapshot block)
decisions:
  - "Option A executed: per-line `<!-- noqa: sdet-rename-shim -->` suffixes on the 4 untagged README snapshot lines (vs Option B inline-suppress-the-whole-block-with-a-different-scanner or Option C amend plan-05 retroactively). Option A: minimal diff, honors the LOCKED D-18 line-level semantic verbatim, preserves the Phase 30 re-capture handoff exactly as plan-05 left it (HTML sentinel preamble on line 276 still tags the block as a verbatim deferred-recapture; per-line tags are the gate-honoring delta)."
  - "Plan-05 design intent — single HTML-comment sentinel preamble — did not match the locked D-18 line-level semantic the plan-06 gate enforces. Plan 05 SUMMARY explicitly called this out as a 'D-18 noqa scope' implementation deviation but only applied it to src/ shim definitions; the README snapshot block was tagged with a single preamble that the line-by-line gate cannot honor."
  - "Rule-1 deviation precedent honored: the README per-line tagging is scope-creep into plan-05 territory, but the precedent set by plans 25-01..05 (each absorbing Rule-1 fixes directly caused by upstream/in-flight changes) is followed here — fixing in-task avoids a fragmented red-at-HEAD state between plan-06 close and a later cleanup."
  - "Gate is line-by-line, NOT block-aware: confirmed by the implementation (`_scan_text_file` iterates `for ln, line in enumerate(f, 1)` — no notion of fenced-block context). This is what makes the per-line tagging the correct closure path, not a smarter scanner that would understand markdown semantics."
  - "Rendered README will display 4 literal `<!-- noqa: sdet-rename-shim -->` strings inside the ```text fenced block until Phase 30 re-captures the snapshot against the renamed surface (carry-forward item per plan-05 SUMMARY 'Scope Boundary Held' + CLOSE-04). Markdown does NOT strip HTML comments inside fenced code blocks — they render as literal text. This is intended and the gate-honoring trade-off."
  - "Bite test verified: `echo 'TODO: see SDET-99' >> README.md` makes the gate FAIL with 2-case red; `git checkout -- README.md` restores 4/4 GREEN. Proves the gate's bite end-to-end on real working-tree mutation."
  - "D-19 honored: the gate runs in the default `tests/framework/` discovery scope (no addopts skip, no marker registration); Phase 26+ CI runs collect it automatically."
metrics:
  duration: ~6 minutes
  completed: 2026-05-16
  tasks_completed: 1
  files_modified: 2  # 1 created (gate) + 1 modified (README)
  commits: 1
---

# Phase 25 Plan 06: RENAME-06 CI Acceptance Gate Summary

Created `tests/framework/test_sdet_rename_leak_gate.py` — a 152-line pytest gate that enforces D-17 patterns (planning-ID regex + `sdet`-terminology regex), D-16 scope (README + CLAUDE + docs/ + examples/ + config.example.yaml + src/mcp_test_framework/**/*.py docstrings + string literals + top-of-file comments), and D-18 line-level exclusions (`# noqa: sdet-rename-shim` and `<!-- noqa: sdet-rename-shim -->` both honored by a single substring check). The gate is RED-by-design on any commit that reintroduces `sdet`-terminology or planning-ID leaks into operator-facing surfaces; the post-plan-05 + post-Option-A working tree is GREEN at 4/4 cases.

Phase 25 (RENAME) is now closed end-to-end: 6 plans, 6 wave executions, RENAME-01 through RENAME-06 shipped.

## Objective Met

RENAME-06 (CI-gate portion) acceptance text holds:

- **Gate file exists at the correct path**: `tests/framework/test_sdet_rename_leak_gate.py` (152 lines >= 80-line `min_lines` threshold per the plan's `must_haves.artifacts` constraint).
- **D-17 patterns implemented verbatim**: `PLANNING_ID_PATTERN = re.compile(r"\b(SDET|RENAME|PERSONA|CLEAN|CLI|CODEGEN|PACK|LIB|REPORTER|CFG|CLOSE|STATE|UI|UX|UAT|SAFE|SURFACE|RUNNER|SEED)-\d+(\.\d+)?\b")` and `SDET_TERM_PATTERN = re.compile(r"\bsdet\b|\bSDET\b")`.
- **D-16 scope implemented**: `_markdown_or_yaml_or_text_files()` enumerates README + CLAUDE + config.example.yaml + `docs/*.md` (recursive) + `examples/**/*.{md,yaml,yml}`. `_src_python_files()` enumerates `src/mcp_test_framework/**/*.py`. `.planning/` and `tests/` are NEVER scanned.
- **D-18 line-level exclusion implemented**: `NOQA_MARKER = "noqa: sdet-rename-shim"` substring check applied per-line in `_scan_text_file` and per-source-line in `_scan_python_strings` (with `_range_is_noqa` for multi-line nodes — any line in a docstring node carrying the marker excludes the whole node).
- **D-19 CI-runnability**: The test is collected by default under `tests/framework/`; no marker registration, no `addopts` skip. The framework's own CI pipeline runs it on every commit. `Phase 26+ commits that reintroduce a leak fail CI` is now structurally enforced.
- **Post-plan-05 + Option-A tree passes 4/4 cases**: `uv run python -m pytest tests/framework/test_sdet_rename_leak_gate.py -v` returns `4 passed in 0.10s`.
- **Bite test passes end-to-end**: `echo "TODO: see SDET-99" >> README.md` makes the gate FAIL with 2 of 4 cases red (`planning_id` + `sdet_terminology` both trip on the injected line); `git checkout -- README.md` restores 4/4 GREEN. Verified live, not theoretical.

## Tasks Completed

| # | Name                                                                                                          | Commit  | Files                                                            |
| - | ------------------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------- |
| 1 | Implement the leak gate + apply Option A per-line tags to the 4 untagged README snapshot lines (Rule-1 absorb) | 704fb61 | tests/framework/test_sdet_rename_leak_gate.py, README.md         |

## Verification

Plan-level `<verification>` block — all pass:

- **`uv run pytest tests/framework/test_sdet_rename_leak_gate.py -v` exits zero**: `4 passed in 0.10s` (post-tag tree).
- **Gate enumerates D-16 scope**: `_markdown_or_yaml_or_text_files()` + `_src_python_files()` cover README + CLAUDE + docs/ + examples/ + config.example.yaml + `src/mcp_test_framework/**/*.py`.
- **D-18 marker correctly suppresses legitimate shims**: post-plan-05 tree contains many legitimate shim lines (config.py AliasChoices block, _runner.py `sdet=` kwarg, cli.py `--sdet` shim, examples/homelab-mcp.yaml `sdet:` alias demo, docs/SDET-AUTHORING.md stub) — all pass the gate because their `# noqa: sdet-rename-shim` / `<!-- noqa: sdet-rename-shim -->` markers are honored by the per-line substring check.
- **Bite test in acceptance criteria proves the gate fails on stray match + recovers when removed**: confirmed live (see Objective Met section above).
- **Phase 26+ leak-introducing commits fail CI**: structurally enforced by the gate's residency in `tests/framework/` and the default-collect pytest behavior; no addopts skip, no marker registration.

Specific acceptance criteria (all pass):

- `test -f tests/framework/test_sdet_rename_leak_gate.py` -> file exists
- `wc -l tests/framework/test_sdet_rename_leak_gate.py` -> 152 (>= 80)
- `grep -q "PLANNING_ID_PATTERN"` -> match
- `grep -q "SDET_TERM_PATTERN"` -> match
- `grep -q "NOQA_MARKER"` -> match
- `uv run python -c "import ast; ast.parse(open('tests/framework/test_sdet_rename_leak_gate.py').read()); print('ok')"` -> `ok`
- `uv run python -m pytest tests/framework/test_sdet_rename_leak_gate.py -v` -> `4 passed`
- Bite-test pipeline: inject `SDET-99` → gate FAIL → restore → gate PASS. All 3 stages pass.

Framework test suite end-state: `uv run python -m pytest tests/framework --tb=line -q` -> **584 passed, 1 skipped, 17 deselected, 2 xfailed, 55 warnings**. Plan-05 baseline was 580 passed; the +4 delta is exactly the 4 new gate test cases. No regression; same deprecation-warning shape as plans 25-01..05 (legacy `sdet:` YAML loader, `--sdet` flag, `gen-sdet-classes` command — all expected during the v1.4 deprecation window).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 4 README.md snapshot lines untagged at plan-06 entry, breaking gate**

- **Found during:** Initial run of the newly authored `tests/framework/test_sdet_rename_leak_gate.py` against the post-plan-05 tree. Gate was RED on the `sdet_terminology` parametrize case for `test_no_residual_match_in_operator_facing_docs` with 4 residual matches:
  - README.md:348: `MCP Test Framework (SDET)`
  - README.md:354: `Judges:      (none — SDET scope)`
  - README.md:416: `  ✗ create_returns_pending_vm — failed on setup with "mcp_test_framework.sdet.errors.ToolCallError: ..."`
  - README.md:417: `  ✗ delete_returns_ok — failed on setup with "mcp_test_framework.sdet.errors.ToolCallError: ..."`
- **Root cause:** Plan 05 design intent was a SINGLE block-level `<!-- noqa: sdet-rename-shim --> ... -->` HTML-comment sentinel preamble (still present at README.md:276) tagging the entire fenced ```text snapshot block (~lines 345-420) as a verbatim deferred-recapture. Plan 05's own SUMMARY ("Implementation deviation (D-18 noqa scope)" section) acknowledged the gate would be line-by-line and applied per-line tagging to all src/ shim definitions — but the README snapshot block was not given per-line treatment. The locked D-18 line-level semantic (which plan 06 enforces in `_scan_text_file` via `for ln, line in enumerate(f, 1): if NOQA_MARKER in line: continue`) does not honor block-level preambles. The 4 snapshot lines therefore tripped the gate.
- **Fix:** Option A — append a literal `<!-- noqa: sdet-rename-shim -->` suffix to each of the 4 lines, preserving the original line content verbatim. The HTML-comment sentinel preamble at README.md:276 is RETAINED (it still tags the block contextually for human readers and survives the Phase 30 re-capture as documentation of why the block was preserved). The per-line suffixes are the gate-honoring delta — minimal diff, line-level semantic locked, Phase 30 re-capture handoff unchanged.
- **Files modified:** README.md (4 lines: 348, 354, 416, 417).
- **Commit:** `704fb61` (bundled with the gate file creation per the plans 25-01..05 precedent of absorbing Rule-1 deviations into the originating commit — keeping gate authorship and the closure-it-requires atomically linked).

### Architectural deviation (Option A vs B vs C) — user-decided

**Plan said:** Create the gate; assume post-plan-05 tree is GREEN.

**Reality:** Post-plan-05 tree was 1-of-4-RED on the gate because of the 4 untagged README snapshot lines. Three closure options were surfaced as a `checkpoint:decision`:

- **Option A** (selected): Per-line `<!-- noqa: sdet-rename-shim -->` suffix tags on the 4 README lines. Minimal diff. Honors locked D-18 line-level semantic verbatim. Preserves Phase 30 re-capture handoff. Rendered README shows 4 literal tag strings until Phase 30. Rule-1 deviation on plan-05 territory.
- **Option B** (rejected): Teach the gate to understand fenced-block context (block-aware scanner that honors a preamble HTML-comment as covering the following ```fence). Architectural-scope change to the gate's design; broadens the gate's surface area; introduces markdown-parsing dependency to the leak detector; risks under/over-suppression. Violates D-18's "line-level" lock.
- **Option C** (rejected): Amend plan-05 retroactively to add per-line tags during plan-05's sweep. Rewrites already-shipped plan-05 history; breaks the plan-by-plan commit narrative; doesn't change the actual closure work, just moves it to a different plan's commit.

**User decision:** Option A. Locked rule (D-18 line-level semantic) takes precedence over a gate redesign or plan-history rewrite. The Phase 30 re-capture handoff already owns the snapshot regeneration; the per-line tags are a known-finite cost that disappears when Phase 30 re-captures.

This was a Rule-4 (architectural) checkpoint correctly returned to the user; not auto-fixed.

## Authentication Gates

None encountered.

## Scope Boundary Held

Per plan 06 scope rules:

- **The gate IS the deliverable.** No additional code/docs/configs touched beyond the gate file + the 4 README line tags required to make the gate GREEN at plan-06 entry.
- **Did NOT** re-capture the README §"## test-code scenarios" snapshot — explicitly carried forward to Phase 30 CLOSE-04 per plan-05 SUMMARY's "Scope Boundary Held" section and the CONTEXT.md carry-forward map.
- **Did NOT** modify any src/ shim line tagging — plan 05's per-line src/ noqa coverage already passes the gate; the only delta needed was the 4 README lines.
- **Did NOT** add the gate to any CI workflow file (e.g., GitHub Actions) — the gate runs in the default `tests/framework/` collection scope, and no CI workflow file edits were called for in plan 06's `<tasks>` block. CI integration is structurally guaranteed by the gate's residency in the framework's pytest discovery scope.
- **Did NOT** touch `docs/MIGRATION-v1-to-v2.md` — already clean at plan-05 baseline; no special D-18 handling needed.
- **Did NOT** modify any tests under `tests/` other than the new gate file — plan 05 absorbed the 15-test framework self-test repoint into plan-05's commits; no further framework-test maintenance was triggered by plan 06.

## TDD Gate Compliance

Plan type is `execute` (not `tdd`); no RED/GREEN/REFACTOR gate sequence required. However, the gate itself exhibits TDD-like properties by construction:

- **Implicit RED**: gate was authored to detect the 4 known untagged README lines (verified RED on those 4 lines before Option A applied).
- **Implicit GREEN**: post-Option-A tree passes 4/4 cases.
- **Bite test**: live-verified the gate's enforcement (inject leak → RED, restore → GREEN). This is functionally equivalent to a REFACTOR-safety property test.

The plan-06 `<task>` block explicitly says `tdd="false"` because the gate's RED/GREEN cycle is its operational behavior at HEAD, not its authoring history.

## Known Stubs

None. The gate is fully implemented end-to-end; the 4 parametrize cases each execute a complete scan + assertion pipeline against the live file set. No placeholders, no `pytest.skip()` calls, no `pytest.xfail` markers.

## Phase 25 (RENAME) Closure Summary

With plan 06 closed, Phase 25 ships RENAME-01 through RENAME-06 in 6 atomic plans across 6 waves:

| Req       | Plan(s)            | Outcome                                                                                           |
| --------- | ------------------ | ------------------------------------------------------------------------------------------------- |
| RENAME-01 | 25-01              | `src/mcp_test_framework/sdet/` -> `test_code/` with back-compat shim re-exports                  |
| RENAME-02 | 25-02              | `gen-test-classes` CLI command + `gen-sdet-classes` hidden deprecation shim                       |
| RENAME-03 | 25-02              | `--test-code` flag + hidden `--sdet` shim with DeprecationWarning                                 |
| RENAME-04 | 25-04              | `tests/test_code/` discovery + dual-scope honors legacy `tests/sdet/` for one milestone           |
| RENAME-05 | 25-03              | `TestCodeConfig` + `AliasChoices('test_code', 'sdet')` + ambiguity validator                      |
| RENAME-06 | 25-05 + 25-06      | Operator-facing terminology sweep (05) + CI-runnable acceptance gate (06)                         |

Phase 26 (PACK) is now unblocked: the public import surface is locked behind a CI gate that fails on any reintroduction. PyPI publication under the corrected dist name (`mcp-test-framework`) can proceed without risk of regressing the `test_code` namespace decision.

## Self-Check: PASSED

Commit verified (`git log --oneline -2`):
- FOUND: 704fb61 (test(25-06): add RENAME-06 acceptance leak gate + per-line tags for snapshot block)

Files verified:
- FOUND: tests/framework/test_sdet_rename_leak_gate.py (152 lines; D-17 patterns + D-16 scope + D-18 exclusion)
- FOUND: README.md (4 lines suffix-tagged with `<!-- noqa: sdet-rename-shim -->` on lines 348, 354, 416, 417)

Gate state verified:
- FOUND: `uv run python -m pytest tests/framework/test_sdet_rename_leak_gate.py -v` -> 4 passed
- FOUND: bite test (`SDET-99` injection -> 2 failures, restore -> 4 passes) confirms gate bite
