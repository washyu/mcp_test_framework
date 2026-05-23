---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/MIGRATION-v1-to-v2.md
  - tests/framework/unit/test_migration_doc.py
autonomous: true
requirements: [V1DROP-01, V1DROP-04]
tags: [v1-decommission, doc-deletion, test-deletion]
must_haves:
  truths:
    - "`docs/MIGRATION-v1-to-v2.md` does not exist on disk."
    - "`tests/framework/unit/test_migration_doc.py` does not exist on disk."
    - "No git-tracked file in the repo contains the path string `docs/MIGRATION-v1-to-v2.md` (after this plan + Plan 05; this plan handles the file deletions, Plan 05 scrubs remaining cross-refs in docs/)."
  artifacts:
    - path: "docs/MIGRATION-v1-to-v2.md"
      provides: "DELETED on disk"
      contains: ""
    - path: "tests/framework/unit/test_migration_doc.py"
      provides: "DELETED on disk"
      contains: ""
  key_links: []
---

<objective>
Delete the v1→v2 migration walkthrough document and its companion existence-check regression test in a single change. Implements V1DROP-01 and the migration-doc-test portion of V1DROP-04 per Phase 31 CONTEXT and RESEARCH §"Strict ordering constraint 1" (the doc and its test must be deleted in the same wave to avoid a confusing state where the test is green for a file that no longer exists).

Purpose: Decommission the v1→v2 migration story. The framework has never been published and no live v1 operators exist; the file is dead weight that drags the message-rewrite work in Plan 03 sideways.

Output: Two file deletions. Zero new content. Cross-reference scrubs in README/ERROR-STYLE/LIBRARY-MODE/EXTENDING/.env.example/cli.py are handled by sibling plans (Plan 03 for cli.py; Plan 05 for docs).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md
@.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Disk filesystem -> regression test | The test pins file existence; deleting the file without deleting the test = test-suite red |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-31-04-01 | Repudiation (INFORMATIONAL) | Historical v1→v2 migration story is lost from the docs tree | accept | Framework was never published; no live v1 operators exist. Git history preserves the file (`git log -- docs/MIGRATION-v1-to-v2.md`) for future archaeology. CONTEXT.md §"Deferred Ideas" notes optional one-line CHANGELOG capture as backlog. |
| T-31-04-02 | Tampering (LOW) | Other files still reference `docs/MIGRATION-v1-to-v2.md` after deletion -> broken links | mitigate | Plan 03 handles the cli.py cross-ref (version branch rewrite); Plan 05 handles README/ERROR-STYLE/LIBRARY-MODE/EXTENDING cross-refs. Plan 05 is in WAVE 2, depending on this plan, so the deletion lands before the scrub — RESEARCH §"Strict ordering constraint 1" is honored end-to-end. |

ASVS classification: N/A (pure deletion). Phase has no HIGH threats.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Delete docs/MIGRATION-v1-to-v2.md and tests/framework/unit/test_migration_doc.py</name>
  <files>docs/MIGRATION-v1-to-v2.md, tests/framework/unit/test_migration_doc.py</files>
  <read_first>
    - docs/MIGRATION-v1-to-v2.md (verify the file's contents one last time before deletion — sanity check that nothing load-bearing is being lost; the user has explicitly approved deletion via D-12 + V1DROP-01)
    - tests/framework/unit/test_migration_doc.py (read entire file — it's 58 lines per RESEARCH; confirm it only asserts the file exists + carries certain v2-related strings, with no other assertions that need rehoming elsewhere)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md (V1DROP-01 locked deletion)
    - .planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-RESEARCH.md §"Self-Test Inventory" (test_migration_doc.py disposition: DELETE entire file)
  </read_first>
  <behavior>
    - After this task: `test -f docs/MIGRATION-v1-to-v2.md` exits non-zero (file gone).
    - After this task: `test -f tests/framework/unit/test_migration_doc.py` exits non-zero (file gone).
    - The git working tree shows both files as deleted (staged or unstaged).
    - No other file in the repo is modified by this task.
  </behavior>
  <action>
    Two file deletions.

    1. **Delete `docs/MIGRATION-v1-to-v2.md`**.
       PowerShell: `Remove-Item docs\MIGRATION-v1-to-v2.md`
       Or via git: `git rm docs/MIGRATION-v1-to-v2.md`

    2. **Delete `tests/framework/unit/test_migration_doc.py`**.
       PowerShell: `Remove-Item tests\framework\unit\test_migration_doc.py`
       Or via git: `git rm tests/framework/unit/test_migration_doc.py`

    Do NOT touch any other file. Cross-reference scrubs in other docs (README, ERROR-STYLE.md, LIBRARY-MODE.md, EXTENDING.md) are Plan 05's responsibility — Plan 05 depends on Plan 04, so the scrub will land after the file is gone (RESEARCH §"Strict ordering constraint 1").

    Verify with two grep-equivalent checks (acceptance criteria below) before declaring the task done. If either file still exists, the deletion did not commit — repeat the removal.
  </action>
  <verify>
    <automated>uv run python -c "import os; assert not os.path.exists('docs/MIGRATION-v1-to-v2.md'), 'docs/MIGRATION-v1-to-v2.md still exists'; assert not os.path.exists('tests/framework/unit/test_migration_doc.py'), 'tests/framework/unit/test_migration_doc.py still exists'; print('OK both deleted')"</automated>
  </verify>
  <acceptance_criteria>
    - `test ! -f docs/MIGRATION-v1-to-v2.md` (file does NOT exist).
    - `test ! -f tests/framework/unit/test_migration_doc.py` (file does NOT exist).
    - `git status --porcelain docs/MIGRATION-v1-to-v2.md tests/framework/unit/test_migration_doc.py` shows both as deleted (` D` prefix or `D ` prefix, depending on stage).
    - No other file under `docs/` or `tests/framework/` is modified in this task (`git status --porcelain` shows only the two deletions for the scope of this plan).
  </acceptance_criteria>
  <done>
    Both files are gone from the working tree; Plan 05's scrub can land cleanly without race against an existing-file regression test.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after the task completes:

1. `uv run python -c "import os; assert not os.path.exists('docs/MIGRATION-v1-to-v2.md'); assert not os.path.exists('tests/framework/unit/test_migration_doc.py'); print('OK')"` exits 0.
2. `uv run pytest tests/framework/unit/ -q --collect-only` does NOT collect `test_migration_doc` (the file is gone; pytest will skip it).
3. `git status` shows two deletions in the working tree.
4. Note: after this plan ships, other files (README, ERROR-STYLE, LIBRARY-MODE, EXTENDING, the cli.py version branch from Plan 03) may still reference `docs/MIGRATION-v1-to-v2.md` — those scrubs are Plan 03 + Plan 05's responsibility. Do NOT block this plan's completion on those external scrubs.
</verification>

<success_criteria>
- The task's acceptance criteria met.
- `docs/MIGRATION-v1-to-v2.md` and `tests/framework/unit/test_migration_doc.py` are both deleted from the working tree.
- Plan 05 can now scrub cross-references without racing against a regression test that asserts the deleted file exists.
</success_criteria>

<output>
After completion, create `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-04-SUMMARY.md`
</output>
