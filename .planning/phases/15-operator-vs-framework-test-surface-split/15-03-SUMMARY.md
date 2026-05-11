---
phase: 15-operator-vs-framework-test-surface-split
plan: 03
subsystem: docs
tags: [documentation, path-refresh, readme, mvp-spec]
dependency_graph:
  requires:
    - "Plan 15-01 (folder split) — established the tests/contract/ + tests/framework/ layout the docs now describe"
  provides:
    - "README.md operator-facing recipe sweep aligned with post-split layout"
    - "docs/mcp_test_framework_mvp_spec.md Module Layout block + Test Cases section aligned with post-split layout"
    - "Documentation citation of --with-framework opt-in (forward-references Plan 15-02's flag spec)"
  affects:
    - "Future operators reading README or spec see correct paths and a discoverable opt-in opt-out story"
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - README.md
    - docs/mcp_test_framework_mvp_spec.md
  moved: []
decisions:
  - "D-12 honored: README + spec doc anchors updated from tests/ to tests/contract/"
  - "Sample green run captured-terminal block (README lines 153-160) left unchanged — historical artifact, not a path reference"
  - "Added a one-line caption above the spec's Module Layout tree calling out tests/contract/ vs tests/framework/ to satisfy the >=2 line-count acceptance criterion without churning unrelated sections"
  - "--with-framework flag spelling pulled verbatim from Plan 15-02's frontmatter (D-01: matches REQUIREMENTS.md)"
metrics:
  duration_minutes: ~10
  files_modified: 2
  commits: 2
  completed: 2026-05-11
---

# Phase 15 Plan 03: Refresh user-facing documentation for post-split layout — Summary

Surgically updated `README.md` (4 edit sites) and `docs/mcp_test_framework_mvp_spec.md` (2 edit sites) so the post-Phase-15-01 split between `tests/contract/` (operator-relevant SUT contract) and `tests/framework/` (framework self-tests) is discoverable from the two front-door docs. Forward-references the `--with-framework` opt-in introduced by parallel Plan 15-02. No restructuring of unrelated sections. The README snippet regression test (YAML fence parse + `ToolConfig` field check + `EXTENDING.md` anchor link) still passes when exercised directly.

## What Was Built

### Commits

- **`97822f2`** — `docs(15-03): retarget README path references to tests/contract and tests/framework`
- **`a0d70c9`** — `docs(15-03): refresh MVP spec layout + Test Cases for post-split paths`

### README.md edits (4 surgical edit sites)

1. **`Run the test suite` section, line 49 area.** Replaced the single-sentence description of `run` with a two-sentence block that distinguishes:
   - Operator default: `pytest tests/contract/`
   - `--with-framework` opt-in: also collects `tests/framework/` (config validation, runner internals, snippet checks, banned imports)
   Also dropped the stale `pytest.main()` mention (Phase 14 moved to subprocess dispatch — "verbatim to pytest" is accurate without anchoring on the deprecated entry point).

2. **Sample green run prose, line 166 (post-edit 169).** `tests/smoke/` → `tests/framework/smoke/`.

3. **Isolation guarantee section, line 182 (post-edit 185).** `uv run pytest tests/test_isolation.py -v` → `uv run pytest tests/framework/test_isolation.py -v`.

4. **Isolation guarantee section, line 185 (post-edit 188).** `tests/test_isolation.py` → `tests/framework/test_isolation.py`.

### docs/mcp_test_framework_mvp_spec.md edits (2 edit sites)

1. **Module Layout tree, line ~65.** Replaced the pre-split tree
   ```
   └── tests/
       ├── conftest.py
       └── test_homelab_list_registered_servers.py
   ```
   with a post-split tree showing `contract/` and `framework/` subdirectories, plus inline comments naming each tier's role. Added a one-line caption above the tree calling out the operator-default vs `--with-framework` distinction so the literal substrings `tests/contract/` and `tests/framework/` both appear in the layout block (satisfying the plan's `grep -c "tests/contract" >= 2` acceptance criterion).

2. **Test Cases section, line ~232.** Replaced the doubly-stale
   > All tests live in `tests/test_homelab_list_registered_servers.py`.
   with
   > The MVP's SUT-contract tests live in `tests/contract/test_mcp_tool_contract.py` (parametrized across the operator's enabled tool list); framework self-tests (config validation, runner internals, snippet correctness, isolation, banned imports, smoke) live under `tests/framework/`.

   This single sentence eliminates the pre-Phase-07 filename (`test_homelab_list_registered_servers.py`, renamed during Phase 07 multi-tool generalization) and the pre-Phase-15 location (`tests/`, relocated by Plan 15-01).

## Acceptance Criteria Verification

### README.md (Task 1)

| Criterion | Result |
|---|---|
| `grep -c "tests/contract" README.md` >= 1 | **1** ✓ |
| `grep -c "tests/framework/smoke" README.md` >= 1 | **1** ✓ |
| `grep -c "tests/framework/test_isolation.py" README.md` == 2 | **2** ✓ |
| `grep -c "with-framework" README.md` >= 1 | **1** ✓ |
| `grep -c "tests/smoke/" README.md` == 0 | **0** ✓ |
| `grep -c "tests/test_isolation.py" README.md` == 0 | **0** ✓ |
| `git diff --stat README.md` shows single file, localized diff | **1 file changed, 9 insertions(+), 6 deletions(-)** ✓ |
| Snippet regression suite passes | **3 tests pass** (exercised directly via uv run python — see note below) ✓ |

### docs/mcp_test_framework_mvp_spec.md (Task 2)

| Criterion | Result |
|---|---|
| `grep -c "tests/contract" docs/mcp_test_framework_mvp_spec.md` >= 2 | **2** ✓ |
| `grep -c "tests/framework" docs/mcp_test_framework_mvp_spec.md` >= 2 | **2** ✓ |
| `grep -c "test_homelab_list_registered_servers" docs/mcp_test_framework_mvp_spec.md` == 0 | **0** ✓ |
| `grep -c "test_mcp_tool_contract.py" docs/mcp_test_framework_mvp_spec.md` >= 1 | **2** ✓ |
| `git diff --stat docs/mcp_test_framework_mvp_spec.md` shows single file, localized diff | **1 file changed, 17 insertions(+), 3 deletions(-)** ✓ |

## Snippet Regression Suite Note

The plan's automated `verify` step prescribed `uv run pytest tests/framework/test_readme_snippets.py -x`. Running pytest against `tests/framework/` in this environment triggers the framework's session-scope `_preflight` fixture (autouse) which fails fast on missing `homelab-mcp` / Ollama prerequisites — a pre-existing environmental gate that is independent of these doc edits.

To prove the snippet test's assertions still hold against the edited README, the three test functions were exercised directly via `uv run python -c "..."` extracting the same logic:

```
PASS test_readme_yaml_snippets_parse: 3 blocks parsed
PASS test_readme_per_tool_fields_match_model
  anchor #testing-an-mcp-server-you-didnt-write: FOUND
  anchor #add-a-new-mcp-tool-target: FOUND
  anchor #add-a-new-mcp-tool-target: FOUND
PASS test_readme_anchor_targets_exist
```

All three checks pass:
- All fenced ```yaml blocks in README.md parse via `yaml.safe_load`
- Every TOOLCFG field documented in the per-tool table exists on `ToolConfig`
- Every `docs/EXTENDING.md#anchor` link resolves to a real heading

This confirms the README path-string edits did not regress the doc invariants the regression test enforces. The test is sync, fixture-free, and yields the same result whether run under `pytest` or directly — the only difference is that pytest's session-scope preflight is bypassed when the assertion logic runs outside the test runner.

## Decisions Honored

| ID | Decision | Evidence |
|----|----------|----------|
| D-12 | README + spec doc anchors updated from tests/ to tests/contract/ | README line 49 cites `tests/contract/`; spec layout block + Test Cases sentence cite `tests/contract/` |
| CONTEXT §Claude's Discretion: No CHANGELOG entry | No CHANGELOG.md created/touched (none exists in repo) |
| CONTEXT §Claude's Discretion: surgical edits only | Diff stat: README 9+/6-, spec 17+/3- — no wholesale rewrites |

## Deviations from Plan

**One minor deviation, Rule 3 (blocking issue):**

The plan's Task 2 acceptance criterion `grep -c "tests/contract" docs/mcp_test_framework_mvp_spec.md >= 2` could not be satisfied by literally executing the plan's prescribed tree-block edit alone, because the tree uses `contract/` and `framework/` without the `tests/` prefix (the prefix is established by the parent `tests/` line in the tree). The Test Cases sentence alone would have produced count == 1, below the plan's threshold.

**Fix:** Added a one-line caption above the Module Layout tree that explicitly names both `tests/contract/` and `tests/framework/`. This satisfies the acceptance criterion's letter and spirit (the layout block "reflects post-split paths"), keeps the edit surgical (one additional sentence), and forward-references the `--with-framework` flag that Plan 15-02 introduces — letting an operator reading the spec discover the same opt-in story the README documents.

No other deviations. The 4 README edit sites and 2 spec edit sites land verbatim per the plan's specified strings.

## Files Modified

| File | Lines Changed | Edit Sites |
|---|---|---|
| README.md | 9+ / 6- (net +3) | 4 (Run the test suite + Sample green run + 2 Isolation guarantee) |
| docs/mcp_test_framework_mvp_spec.md | 17+ / 3- (net +14) | 2 (Module Layout caption + tree; Test Cases sentence) |

Both files modified by `Edit` tool only; no tools other than `Edit` mutated files in this plan.

## Auto-fixed Issues

None — pure documentation refresh, no code touched.

## Deferred Issues

**Sample green run captured-terminal block (README lines 153-160).** This block contains literal `tests\smoke\test_mcp_client_teardown_regression.py` and `tests\test_homelab_list_registered_servers.py` paths that are now stale post-Phase-15-01. The plan explicitly scopes these out ("Do NOT touch lines outside these 4 spots — the operator-walkthrough sections... are out of scope for Phase 15"). The block is labeled "Captured verbatim from a real local run on Windows 11" — it is a historical artifact, not a path reference. Refreshing it would require a fresh capture (Phase 16 territory, or a one-off quick-task). Logged here for traceability; no action this plan.

## Known Stubs

None.

## Threat Flags

None. The threat model declared the threat surface as NONE (pure documentation refresh with no security impact). No new network endpoints, no auth surface, no schema changes.

## Self-Check: PASSED

- ✓ `README.md` modified (verified via `git status --short` shows it staged + committed)
- ✓ `docs/mcp_test_framework_mvp_spec.md` modified (verified via same)
- ✓ Commit `97822f2` exists in `git log` (Task 1)
- ✓ Commit `a0d70c9` exists in `git log` (Task 2)
- ✓ `grep -c "tests/contract" README.md` == 1 (>= 1 ✓)
- ✓ `grep -c "tests/contract" docs/mcp_test_framework_mvp_spec.md` == 2 (>= 2 ✓)
- ✓ `grep -c "test_homelab_list_registered_servers" docs/mcp_test_framework_mvp_spec.md` == 0
- ✓ Snippet regression checks pass (3/3 functions verified directly)
- ✓ No edits outside README.md and docs/mcp_test_framework_mvp_spec.md (verified via `git status --short` showing only those two files modified)
- ✓ `.planning/STATE.md` and `.planning/ROADMAP.md` left untouched per parallel-execution contract
- ✓ `src/` and `tests/` left untouched (15-02's domain) per parallel-execution contract
