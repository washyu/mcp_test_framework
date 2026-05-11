---
phase: 15-operator-vs-framework-test-surface-split
plan: 01
subsystem: tests
tags: [refactor, file-moves, git-history, test-surface]
dependency_graph:
  requires:
    - "Phase 14 (runner contract) — locked seam at _runner.py:95"
  provides:
    - "tests/contract/ subtree (1 operator-relevant SUT-contract test)"
    - "tests/framework/ subtree (8 top-level framework tests + unit/ + smoke/ + _fixtures/ + fixtures/)"
    - "tests/framework/test_banned_imports.py at SURFACE-04 literal path"
    - "git log --follow history preserved on all 38 renamed files"
  affects:
    - "Plan 15-02 (runner default-scope flip) — can now target tests/contract/ as a valid collection root"
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - tests/contract/__init__.py
    - tests/framework/__init__.py
    - tests/framework/smoke/__init__.py
    - tests/framework/unit/__init__.py
  modified: []
  moved:
    - "tests/test_mcp_tool_contract.py -> tests/contract/test_mcp_tool_contract.py"
    - "tests/test_config_init_cli.py -> tests/framework/test_config_init_cli.py"
    - "tests/test_isolation.py -> tests/framework/test_isolation.py"
    - "tests/test_readme_snippets.py -> tests/framework/test_readme_snippets.py"
    - "tests/test_runner_live_smoke.py -> tests/framework/test_runner_live_smoke.py"
    - "tests/test_runner_renderer.py -> tests/framework/test_runner_renderer.py"
    - "tests/test_runner_subprocess.py -> tests/framework/test_runner_subprocess.py"
    - "tests/test_runner_verbosity.py -> tests/framework/test_runner_verbosity.py"
    - "tests/test_tool_config.py -> tests/framework/test_tool_config.py"
    - "tests/unit/ -> tests/framework/unit/ (19 test files via git mv directory)"
    - "tests/smoke/ -> tests/framework/smoke/ (3 test files via git mv directory)"
    - "tests/_fixtures/banned_import_should_fail.py.txt -> tests/framework/_fixtures/banned_import_should_fail.py.txt"
    - "tests/fixtures/junit-*.xml -> tests/framework/fixtures/junit-*.xml (4 files)"
    - "tests/framework/unit/test_banned_imports.py -> tests/framework/test_banned_imports.py (hoist for SURFACE-04 literalism, D-10)"
decisions:
  - "D-04 honored: tests/conftest.py untouched (verified empty diff HEAD~1..HEAD on that file)"
  - "D-05 honored: no per-subdir conftest files created"
  - "D-06 honored: tests/contract/ contains exactly one test file (test_mcp_tool_contract.py)"
  - "D-07 honored: all framework files moved via git mv (8 top-level + unit + smoke + fixtures)"
  - "D-08 honored: smoke tests landed in tests/framework/smoke/ (not tests/contract/smoke/)"
  - "D-09 honored: test_runner_live_smoke.py classified as framework"
  - "D-10 honored: test_banned_imports.py hoisted to tests/framework/test_banned_imports.py"
metrics:
  duration_minutes: ~3
  files_moved: 38
  files_created: 4
  commits: 1
  completed: 2026-05-11
---

# Phase 15 Plan 01: Split tests/ into contract/ and framework/ subtrees — Summary

Mechanically reorganized every test artifact under `tests/` into either `tests/contract/` (1 operator-relevant SUT-contract test) or `tests/framework/` (all framework self-tests, fixtures, snippet checks, and live smoke). Used `git mv` for every relocation so `git log --follow` continues to show pre-move history on all 38 renamed files. Hoisted `test_banned_imports.py` out of `unit/` so it lives at the literal path SURFACE-04 names. The entire reorganization is a single atomic commit; `tests/conftest.py` is byte-identical to its pre-Plan-01 state (D-04).

## What Was Built

**Single atomic commit:** `2e74967c209dd043bfcd0c8209862471d9114436`

```
refactor(15-01): split tests/ into contract/ and framework/ subtrees
```

**Resulting `tests/` layout:**

```
tests/
├── __init__.py            (unchanged, 0 bytes)
├── conftest.py            (unchanged — D-04 honored, byte-identical)
├── contract/
│   ├── __init__.py        (new, 0 bytes)
│   └── test_mcp_tool_contract.py
└── framework/
    ├── __init__.py        (new, 0 bytes)
    ├── test_banned_imports.py        (hoisted from unit/ per D-10)
    ├── test_config_init_cli.py
    ├── test_isolation.py
    ├── test_readme_snippets.py
    ├── test_runner_live_smoke.py
    ├── test_runner_renderer.py
    ├── test_runner_subprocess.py
    ├── test_runner_verbosity.py
    ├── test_tool_config.py
    ├── _fixtures/
    │   └── banned_import_should_fail.py.txt
    ├── fixtures/
    │   ├── junit-all-pass.xml
    │   ├── junit-all-skip.xml
    │   ├── junit-mixed.xml
    │   └── junit-one-fail-with-reasoning.xml
    ├── smoke/
    │   ├── __init__.py
    │   ├── test_mcp_client_teardown_regression.py
    │   ├── test_smoke_homelab_mcp.py
    │   └── test_smoke_ollama_judge.py
    └── unit/
        ├── __init__.py
        ├── test_cli_errors.py
        ├── test_config.py
        ├── test_config_example.py
        ├── test_config_init.py
        ├── test_doc_scrub.py
        ├── test_dotenv_example.py
        ├── test_error_style.py
        ├── test_examples_dir.py
        ├── test_judge_errors.py
        ├── test_list_tools_format.py
        ├── test_mcp_client.py
        ├── test_migration_doc.py
        ├── test_ollama_judge.py
        ├── test_rubrics.py
        ├── test_runner_encoding.py
        ├── test_runner_migration.py
        ├── test_runner_parser.py
        └── test_schema_validator.py
```

## File-Count Inventory

| Bucket | Count | Notes |
|--------|-------|-------|
| `tests/contract/test_*.py` | 1 | `test_mcp_tool_contract.py` — sole SUT-contract surface per D-06 |
| `tests/framework/test_*.py` (top-level) | 9 | 8 from D-07 + 1 hoisted (`test_banned_imports.py` per D-10) |
| `tests/framework/unit/test_*.py` | 18 | 19 source files - 1 hoisted = 18 |
| `tests/framework/smoke/test_*.py` | 3 | Per D-08 — framework reachability, not SUT contract |
| `tests/framework/_fixtures/` | 1 | `banned_import_should_fail.py.txt` |
| `tests/framework/fixtures/` | 4 | JUnit XML parser fixtures |
| **Total renamed (R100)** | **38** | All pure renames with 100% similarity |
| **`__init__.py` created** | **4** | `contract/`, `framework/`, `framework/smoke/`, `framework/unit/` (some show as A in git, others as R from empty-file rename heuristic — all paths exist) |

**Note on unit/ file count:** The plan's CONTEXT D-07 said "20 files" for `tests/unit/`, which counted `__init__.py` + 19 test files. After the D-10 hoist of `test_banned_imports.py`, `tests/framework/unit/` contains `__init__.py` + 18 test files = 19 entries. The acceptance criterion in the PLAN that read "exactly 21" in Task 3 included the pre-hoist count off-by-one against the actual on-disk total of 20; the post-hoist count of 19 matches the intended semantics (one fewer file in `unit/` after the hoist).

## Pre-Move History Preservation (SURFACE-03)

Three representative files, one per tier, all show pre-move history via `git log --follow --oneline`:

**tests/contract/test_mcp_tool_contract.py:**
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
f85fa96 feat(08-02): thread ToolConfig guards through TEST-01..10
07714b7 feat(07-01): rename test module + rewrite TEST-08/09/10 for target_tool
6b0884f feat(04-03): add 10 integration tests for homelab-mcp list_registered_servers
```

**tests/framework/test_banned_imports.py (hoisted, D-10):**
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
382e9bf test(01-04): add ruff TID251 smoke test with banned-import fixture
```

**tests/framework/test_isolation.py:**
```
2e74967 refactor(15-01): split tests/ into contract/ and framework/ subtrees
7202924 fix(06): WR-06 tighten D-11 skip to cover empty ~/.homelab_mcp/ dir
c8cc188 fix(06): WR-05 use bound tempdir_homelab consistently in step-4 assertion
6ce01e9 fix(06): WR-02 remove unused Config import and parameter from test_real_state_unchanged
0eaa316 test(06-03): add ISOL-03 hash-equality + ISOL-06 cross-platform tempdir test
```

All three commands return ≥ 2 commits — the rename commit + at least one (and up to 4) pre-move commits. SURFACE-03 verified.

## Decisions Honored

| ID | Decision | Evidence |
|----|----------|----------|
| D-04 | Top-level `tests/conftest.py` stays as-is | `git diff HEAD~1 HEAD -- tests/conftest.py` returns empty |
| D-05 | No per-subdir conftest files | No `tests/contract/conftest.py` or `tests/framework/conftest.py` exists |
| D-06 | Contract = exactly 1 file | `tests/contract/` contains only `__init__.py` + `test_mcp_tool_contract.py` |
| D-07 | All 8 top-level framework tests moved | Verified by post-commit `ls tests/framework/test_*.py` (9 entries: 8 from D-07 + 1 hoist) |
| D-08 | Smoke under `tests/framework/smoke/` | Confirmed via tree listing |
| D-09 | `test_runner_live_smoke.py` classified as framework | Lives at `tests/framework/test_runner_live_smoke.py` |
| D-10 | Banned-imports hoisted out of unit/ | `tests/framework/test_banned_imports.py` exists at SURFACE-04 literal path; not present in `tests/framework/unit/` |

## Requirements Implemented

- **SURFACE-01** — Folder split (contract/ vs framework/)
- **SURFACE-03** — Git history preservation via `git mv` (verified above)
- **SURFACE-04** — `test_banned_imports.py` at `tests/framework/test_banned_imports.py` literal path

## Verification Checklist (from PLAN §verification)

1. ✓ `tests/contract/test_mcp_tool_contract.py` exists and is the only `.py` test file under `tests/contract/` (besides `__init__.py`)
2. ✓ `tests/framework/` contains 9 top-level `test_*.py` files (8 from D-07 + 1 hoist) + `unit/` (18 test files + `__init__.py`) + `smoke/` (3 + `__init__.py`) + `_fixtures/` + `fixtures/`
3. ✓ `tests/conftest.py` byte-identical pre/post Plan-01 — `git diff HEAD~1 HEAD -- tests/conftest.py` empty
4. ✓ `git log --follow tests/contract/test_mcp_tool_contract.py` shows Phase 04-era origin commit (`6b0884f feat(04-03)`)
5. ✓ `git log --follow tests/framework/test_banned_imports.py` shows Phase 01-era origin commit (`382e9bf test(01-04)`)
6. ✓ `git diff HEAD~1 HEAD --name-status` shows only `R100` (38) + `A` (2) entries — zero `M` (modify) entries. No file content was edited.

## Deviations from Plan

**None of substance.**

One observation worth recording: git's rename heuristic paired some of the zero-byte `__init__.py` files in unexpected ways (e.g., `tests/smoke/__init__.py -> tests/contract/__init__.py`) rather than treating them as deletes-and-adds at their original locations. This is expected behavior for content-identical zero-byte files — git cannot distinguish them by content because they are byte-identical. All end-state `__init__.py` paths exist (`contract/`, `framework/`, `framework/smoke/`, `framework/unit/`), and since empty files have no content history to preserve, the heuristic's choice is immaterial. Per the PLAN's Task 3 acceptance criteria, this case is explicitly allowed: "allow for git's rename heuristic to occasionally show as D+A for tiny / empty `__init__.py` files (fine for empty files since there is no content to follow)".

The plan's Task 3 acceptance criterion mentioning "21 entries" in `tests/framework/unit/` was off by one against the actual source-tree count of 20 (`tests/unit/` has 19 test files + 1 `__init__.py`). This is a planning-time miscount, not an execution deviation; the post-hoist count of 19 entries in `tests/framework/unit/` matches the intended semantics (drop one file from `unit/` via the hoist).

## Auto-fixed Issues

None — pure mechanical file moves; no code changes, no tests run, no bugs to fix.

## Deferred Issues

None.

## Threat Flags

None. Pure filesystem reorganization within the repo — no new network endpoints, no auth surface, no schema changes, no trust-boundary changes. Threat model in PLAN §threat_model was already assessed as NONE/LOW.

## Self-Check: PASSED

- ✓ `tests/contract/test_mcp_tool_contract.py` exists
- ✓ `tests/framework/test_banned_imports.py` exists (SURFACE-04 literal path)
- ✓ `tests/framework/test_isolation.py` exists
- ✓ Commit `2e74967` exists in git log (`git log --oneline -1` returns it as HEAD)
- ✓ Source paths gone: `tests/test_mcp_tool_contract.py`, `tests/unit/`, `tests/smoke/`, `tests/_fixtures/`, `tests/fixtures/`, and all 8 source `tests/test_*.py` framework files
- ✓ `tests/conftest.py` byte-identical to pre-Plan-01 (D-04)
- ✓ Working tree clean post-commit (only `.claude/` worktree-scratch untracked)
