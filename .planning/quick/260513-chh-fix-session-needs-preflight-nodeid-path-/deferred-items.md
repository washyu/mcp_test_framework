# Deferred Items — Quick Task 260513-chh

Out-of-scope failures encountered during the acceptance run of
`uv run pytest tests/framework -q` (with no `MCPTF_CONFIG_FILE` set,
on a machine without `homelab-mcp` / Ollama). These are pre-existing
and reproduce against the unmodified pre-fix code (verified via
`git stash` round-trip during execution). They are NOT caused by the
`_session_needs_preflight` change and are NOT preflight-related —
no `returncode=2`, no `MCP command ... not found on PATH` exit.

| File | Failure | Likely Root Cause |
|------|---------|-------------------|
| `tests/framework/test_isolation.py::test_real_state_unchanged` | `FileNotFoundError: tests\docs\MIGRATION-v1-to-v2.md` | Test does a relative path lookup that assumes a cwd different from `tests/framework/`. |
| `tests/framework/test_tool_config.py` (4 cases) | Various, all in same module | Likely the same cwd / relative-path assumption family. |
| `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens` | Static-source scan assertion | Probably keys on a doc/source token that's drifted; unrelated to preflight. |
| `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]` | Doc scrub mismatch | Doc-drift, unrelated to preflight. |
| `tests/framework/unit/test_migration_doc.py` (4 cases) | Various — file existence / content checks | Doc-content drift (`docs/MIGRATION-v1-to-v2.md` shape mismatches). |

Carry these into the next operator-pass triage (likely a small
`/gsd-quick` batch once someone is in the docs/test harness anyway).
The preflight fix itself is independently verified by:

- All 9 cases in `tests/framework/unit/test_session_needs_preflight.py`
- `uv run pytest tests/framework -q` reaching test execution (506 passed,
  1 xfailed, 1 skipped, 16 deselected) instead of bailing at preflight.
