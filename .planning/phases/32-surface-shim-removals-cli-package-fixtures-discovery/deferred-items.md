# Phase 32 Deferred Items

Out-of-scope discoveries flagged during plan execution that do NOT affect each plan's success criteria. Logged by parallel wave-4 executors (plans 32-04 and 32-06).

## Plan 32-04 — pre-existing leak gate failures unrelated to SHIM-06

`tests/framework/test_sdet_rename_leak_gate.py::test_no_residual_match_in_src_python_strings[sdet_terminology-*]` flags 6 pre-existing lines that contain `--sdet` / `sdet` literals inside operator-facing strings without trailing `# noqa: sdet-rename-shim` markers on the string-constant line itself (the surrounding `# noqa` markers exist but the AST-walk scopes them to the function header, not the string body):

- `src/mcp_test_framework/cli.py:646` — docstring of `_sdet_flag_removed`
- `src/mcp_test_framework/cli.py:654` — "--sdet was removed in v1.5" error string
- `src/mcp_test_framework/cli.py:741` — `--sdet` Typer option name
- `src/mcp_test_framework/cli.py:1426` — "gen-sdet-classes was removed in v1.5" error string
- `src/mcp_test_framework/sdet/__init__.py:1` — module docstring
- `src/mcp_test_framework/sdet/__init__.py:12` — "mcp_test_framework.sdet was removed in v1.5" error string

These are PRE-EXISTING failures introduced by Phase 31's SHIM-01/02/03 shim-rejection plumbing; the per-line `# noqa: sdet-rename-shim` annotation was missed on the string-constant lines. Out of scope for SHIM-06 per Rule 1 scope boundary.

Plan 32-04 added the same per-line `# noqa: sdet-rename-shim` markers to its new operator-facing `tests/sdet/` references in `_plugin.py` (pytest_collection warn block + module-level helper comment), so the gate's failure count did not regress for the SHIM-06 scrub itself.

**Recommended fix:** add `# noqa: sdet-rename-shim` to each of the six lines listed above. Owner: phase 32 orchestrator follow-up.

## Plan 32-06 — cli.py L561 mcp-test-framework config-init pin drift

`src/mcp_test_framework/cli.py:561` still contains:

```
run `mcp-test-framework config-init -o config.yaml` to generate
```

Plan 32-06 flipped the corresponding text in `docs/ERROR-STYLE.md` (L54) and `tests/framework/unit/test_error_style.py` (L33 pin) per Pitfall 4 — but `cli.py` L561 was OUT OF SCOPE for 32-06 (owned by plan 32-04 per the wave-4 parallel coordination). As a result, `test_error_style.py::test_error_style_safe_03_body_matches_cli_wiring` (L50) still pins the OLD `mcp-test-framework config-init` wording inside `cli_text`, while the doc-side L33 pin now asserts the NEW `mcp-contracts config-init` wording. The two pins now describe DIFFERENT canonical sources — the cli.py↔ERROR-STYLE.md sync contract is silently broken.

The framework test suite still passes (both pins pass against their respective files), but the design intent of the dual-pin (cli.py SAYS what ERROR-STYLE.md SAYS) is violated. A follow-up plan should flip `cli.py:561` from `mcp-test-framework config-init` to `mcp-contracts config-init` and amend `test_error_style.py:62` to match.

Similar lurking drift at `cli.py:513` (`mcp-test-framework config-init -o config.yaml`) and `cli.py:365` (`mcp-test-framework config-init -o config.yaml` regenerate). Both were left untouched per the parallel coordination boundary; sweep them in the same cli.py amendment.

**Recommended fix:** as part of a follow-up amendment, flip `cli.py:365`, `cli.py:513`, and `cli.py:561` to `mcp-contracts config-init` and amend `test_error_style.py:62` pin.
