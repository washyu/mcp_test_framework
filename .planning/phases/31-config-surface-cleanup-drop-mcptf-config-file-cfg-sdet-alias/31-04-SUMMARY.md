---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 04
subsystem: docs + framework-tests
tags: [v1-decommission, doc-deletion, test-deletion]
requirements: [V1DROP-01, V1DROP-04]
dependency_graph:
  requires: []
  provides:
    - "docs/MIGRATION-v1-to-v2.md DELETED on disk"
    - "tests/framework/unit/test_migration_doc.py DELETED on disk"
  affects:
    - "Plan 05 (docs cross-ref scrub) can now land without racing against an existence-asserting test"
    - "Plan 03 (cli.py message rewrite) no longer has a doc target to point at"
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified: []
  deleted:
    - docs/MIGRATION-v1-to-v2.md
    - tests/framework/unit/test_migration_doc.py
decisions:
  - "Deleted doc + its existence-pinning test in the same commit (RESEARCH 'Strict ordering constraint 1')"
metrics:
  duration: ~3 minutes
  tasks_completed: 1
  files_deleted: 2
  completed_date: 2026-05-23
---

# Phase 31 Plan 04: Delete v1->v2 Migration Doc + Test Summary

Removed `docs/MIGRATION-v1-to-v2.md` and its companion existence-check regression test `tests/framework/unit/test_migration_doc.py` in a single atomic deletion, implementing V1DROP-01 and the migration-doc portion of V1DROP-04. The framework was never published, no live v1 operators exist, and the doc was dead weight. Cross-reference scrubs in `cli.py` and other docs are owned by sibling plans 03 and 05.

## What Was Done

### Task 1: Delete migration doc and its test
- Verified `docs/MIGRATION-v1-to-v2.md` contents one last time (106 lines documenting v1->v2 port: opt-in defaults flip, `target:` block removal, `.env` source drop, step-by-step migration, side-by-side example).
- Verified `tests/framework/unit/test_migration_doc.py` carries only existence + content-pinning assertions (file exists, contains specific v2 keywords, no em-dashes, no planning IDs leaked) -- nothing that needs rehoming elsewhere.
- Deleted both via `git rm` in a single command.
- Confirmed `git status --porcelain` shows exactly two deletions (` D` prefix on both) with no other modifications.
- Confirmed `uv run pytest tests/framework/unit/ -q --collect-only` no longer collects `test_migration_doc` (547/548 tests collected, only deselection is from existing test filters -- no `test_migration_doc` matches).
- Commit: `90d36a7`

## Verification Results

- `uv run python -c "assert not os.path.exists('docs/MIGRATION-v1-to-v2.md'); assert not os.path.exists('tests/framework/unit/test_migration_doc.py')"` -> exits 0 with `OK both deleted`.
- `uv run pytest tests/framework/unit/ -q --collect-only` -> 547 tests collected, no `test_migration_doc` (file gone, pytest does not see it).
- `git status` post-commit -> clean (only `.claude/` untracked, unrelated to this plan).

## Deviations from Plan

None -- plan executed exactly as written. Single task, two file deletions, single commit. No bugs found, no missing functionality, no blockers, no architectural decisions needed.

## Commits

| Hash | Message |
|------|---------|
| 90d36a7 | chore(31-04): delete v1 migration doc and its regression test |

## Known Stubs

None. This plan is a pure deletion -- no new code, no new placeholders.

## Self-Check: PASSED

Verified post-write:
- File `docs/MIGRATION-v1-to-v2.md` MISSING (expected -- deleted).
- File `tests/framework/unit/test_migration_doc.py` MISSING (expected -- deleted).
- Commit `90d36a7` FOUND in `git log --oneline --all`.
- SUMMARY.md committed to worktree branch for orchestrator merge.
