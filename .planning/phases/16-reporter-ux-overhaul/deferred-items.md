# Phase 16 Deferred Items

## Pre-existing test failures (not caused by Plan 16-01)

These failures reproduce on the pre-task baseline (git stash + same env).
They are environmental (MCPTF_CONFIG_FILE pointed at v2 config interacts
with config-default tests that assume v1 default) or unrelated path-resolution
bugs in tests. Out of scope for Plan 16-01.

- `tests/framework/test_tool_config.py::test_default_config_version_and_tools`
  — asserts `cfg.version == 1` from `Config()` defaults; conflicts with the
  v2 config in MCPTF_CONFIG_FILE that we need for preflight to pass.
- `tests/framework/test_tool_config.py::test_config_rejects_unsupported_version[2]`
- `tests/framework/test_tool_config.py::test_yaml_overlay_loads_tools_block`
- `tests/framework/test_tool_config.py::test_call_arguments_forwarded_to_call_tool_via_asyncmock`
- `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens`
  — path bug: looks for `tests/src/mcp_test_framework/cli.py` instead of
  `src/mcp_test_framework/cli.py`.
- `tests/framework/unit/test_migration_doc.py::test_migration_doc_*` (4 tests)
  — assert presence/properties of a `docs/MIGRATION-v1-to-v2.md` file that
  is not in the working tree.

These should be addressed in a separate hygiene quick-task, not Plan 16-01.
