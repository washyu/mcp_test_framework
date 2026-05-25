# Phase 32 Deferred Items

Out-of-scope discoveries flagged during plan execution that do NOT affect the plan's success criteria.

## Plan 32-04

### Pre-existing leak gate failures unrelated to SHIM-06

`tests/framework/test_sdet_rename_leak_gate.py::test_no_residual_match_in_src_python_strings[sdet_terminology-*]` flags 6 pre-existing lines that contain `--sdet` / `sdet` literals inside operator-facing strings without trailing `# noqa: sdet-rename-shim` markers on the string-constant line itself (the surrounding `# noqa` markers exist but the AST-walk scopes them to the function header, not the string body):

- `src/mcp_test_framework/cli.py:646` -- docstring of `_sdet_flag_removed`
- `src/mcp_test_framework/cli.py:654` -- "--sdet was removed in v1.5" error string
- `src/mcp_test_framework/cli.py:741` -- `--sdet` Typer option name
- `src/mcp_test_framework/cli.py:1426` -- "gen-sdet-classes was removed in v1.5" error string
- `src/mcp_test_framework/sdet/__init__.py:1` -- module docstring
- `src/mcp_test_framework/sdet/__init__.py:12` -- "mcp_test_framework.sdet was removed in v1.5" error string

These are PRE-EXISTING failures introduced by Phase 31's SHIM-01/02/03 shim-rejection plumbing; the per-line `# noqa: sdet-rename-shim` annotation was missed on the string-constant lines. Out of scope for SHIM-06 per Rule 1 scope boundary.

Plan 32-04 added the same per-line `# noqa: sdet-rename-shim` markers to its new operator-facing `tests/sdet/` references in `_plugin.py` (pytest_collection warn block + module-level helper comment), so the gate's failure count did not regress for the SHIM-06 scrub itself.
