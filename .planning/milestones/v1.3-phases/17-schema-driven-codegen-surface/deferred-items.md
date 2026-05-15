# Deferred Items - Phase 17

Items discovered during plan execution that are out of scope for the
current plan's tasks. Documented here per executor Rule 3 scope boundary.

## Plan 17-04 (gen-sdet-classes CLI)

### Pre-existing test failures (NOT caused by Plan 17-04 changes)

The following 6 tests fail on the Plan 17-04 base commit (verified by
running them on a clean stash). They appear to be `repo_root`
path-resolution bugs when pytest runs from a git worktree path
(`.claude/worktrees/agent-XXX/`) -- the tests compute a `repo_root`
that prepends `tests/` to absolute paths (e.g. `tests/docs/MIGRATION-v1-to-v2.md`
and `tests/src/mcp_test_framework/cli.py` are looked up but don't exist).

- `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens`
  - Path computed: `tests/src/mcp_test_framework/cli.py` (missing `tests/` prefix bug)
- `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_exists`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_pins_v2_keywords`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_uses_ascii_dashes_not_emdash`
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_does_not_leak_planning_ids`

These should be triaged separately; they may be working-directory-sensitive
or worktree-specific path-resolution issues independent of the Phase 17 work.

### Pre-existing baseline bug: `_session_needs_preflight`

`src/mcp_test_framework/fixtures.py:_session_needs_preflight` checks
`tests/unit/` (not `tests/framework/unit/`) for the preflight gate. The
plan's `<parallel_execution>` block documents the workaround
(`MCPTF_CONFIG_FILE` pointing at the parent repo's config.yaml). Out of
scope for Plan 17-04.
