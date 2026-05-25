# Phase 32 Deferred Items

Logged by plan 32-06 (parallel wave-4 executor).

## Pre-existing failures discovered during 32-06 verification

### test_sdet_rename_leak_gate.py — residual sdet token leaks in src/

`uv run pytest tests/framework/test_sdet_rename_leak_gate.py` fails with 6 residual `\bsdet\b|\bSDET\b` matches in `src/mcp_test_framework/` introduced by earlier plans:

- `src/mcp_test_framework/cli.py:646` — `--sdet` removal callback docstring (plan 32-02)
- `src/mcp_test_framework/cli.py:654` — `"--sdet was removed in v1.5\n"` operator-tone text (plan 32-02)
- `src/mcp_test_framework/cli.py:741` — `--sdet` flag name string in CLI definition (plan 32-02)
- `src/mcp_test_framework/cli.py:1426` — `"gen-sdet-classes was removed in v1.5\n"` operator-tone text (plan 32-03)
- `src/mcp_test_framework/sdet/__init__.py:1` — module docstring naming the removal stub (plan 32-01)
- `src/mcp_test_framework/sdet/__init__.py:12` — `"mcp_test_framework.sdet was removed in v1.5\n"` operator-tone text (plan 32-01)

These lines all need `# noqa: sdet-rename-shim` per the D-18 compat-shim policy enforced by `test_sdet_rename_leak_gate.py`. The hits are intentional removal-stub strings (operator-facing pointer text) and should be grandfathered with the noqa marker.

**Scope:** OUT OF SCOPE for plan 32-06 — `cli.py` and `sdet/__init__.py` are owned by plans 32-04 / 32-02 / 32-03 per the wave-4 parallel coordination policy. Plan 32-06 only modifies `_deprecated_script.py`, `README.md`, `docs/ERROR-STYLE.md`, `docs/EXTENDING.md`, `docs/TEST-CODE-AUTHORING.md`, `tests/framework/unit/test_console_script_removed.py`, and (by Rule-3 cascade documented in 32-06-SUMMARY.md) `tests/framework/unit/test_error_style.py`.

**Recommended fix:** add `# noqa: sdet-rename-shim` to each of the six lines listed above. Owner: phase 32 orchestrator or follow-up Plan 32-04 amendment.

### cli.py L561 mcp-test-framework config-init pin drift

`src/mcp_test_framework/cli.py:561` still contains:

```
run `mcp-test-framework config-init -o config.yaml` to generate
```

Plan 32-06 flipped the corresponding text in `docs/ERROR-STYLE.md` (L54) and `tests/framework/unit/test_error_style.py` (L33 pin) per Pitfall 4 — but `cli.py` L561 was OUT OF SCOPE for 32-06 (owned by plan 32-04 per the wave-4 parallel coordination). As a result, `test_error_style.py::test_error_style_safe_03_body_matches_cli_wiring` (L50) still pins the OLD `mcp-test-framework config-init` wording inside `cli_text`, while the doc-side L33 pin now asserts the NEW `mcp-contracts config-init` wording. The two pins now describe DIFFERENT canonical sources — the cli.py↔ERROR-STYLE.md sync contract is silently broken.

The framework test suite still passes (both pins pass against their respective files), but the design intent of the dual-pin (cli.py SAYS what ERROR-STYLE.md SAYS) is violated. A follow-up plan should flip `cli.py:561` from `mcp-test-framework config-init` to `mcp-contracts config-init` and amend `test_error_style.py:62` to match.

**Recommended fix:** as part of plan 32-04 (or a follow-up amendment), flip `cli.py:561` to `mcp-contracts config-init` and amend `test_error_style.py:62` pin.

Similar lurking drift at `cli.py:513` (`mcp-test-framework config-init -o config.yaml`) and `cli.py:365` (`mcp-test-framework config-init -o config.yaml` regenerate). Both were left untouched per the parallel coordination boundary; sweep them in the same cli.py amendment.
