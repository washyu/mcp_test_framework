---
plan: 26-04
phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s
status: complete
completed: 2026-05-16
tasks: 3/3
key-files:
  created:
    - tests/framework/test_wheel_shape.py
    - tests/framework/test_cli_version.py
  modified: []
---

## What was built

Two new framework self-tests that lock the Phase 26 packaging substrate
against regression:

- `tests/framework/test_wheel_shape.py` — 11 assertions that build the
  project wheel via `uv build --wheel` into a tmp dir, then walk the
  resulting `.whl` (zipfile) to verify wheel content. Module-scoped
  fixture caches the build (~3-8s cold) and skips cleanly when `uv` is
  not on PATH.
- `tests/framework/test_cli_version.py` — 2 assertions that pin the
  `cli.py` version-command lookup string to `mcp-contracts` and verify
  the command exits 0 with non-empty output.

## Wheel-shape assertions (11)

| # | Test | What it pins |
|---|------|--------------|
| 1 | `test_wheel_filename_uses_new_dist_name` | wheel filename starts with `mcp_contracts-`; legacy `mvp_test_framework` does NOT appear |
| 2 | `test_wheel_ships_root_py_typed` | `mcp_test_framework/py.typed` present |
| 3 | `test_wheel_ships_test_code_py_typed` | `mcp_test_framework/test_code/py.typed` present |
| 4 | `test_wheel_ships_contracts_subpackage` | `contracts/__init__.py` + `contracts/py.typed` present |
| 5 | `test_wheel_ships_plugin_module` | `_plugin.py` (pytest11 entry-point target) present |
| 6 | `test_wheel_ships_deprecated_script_module` | `_deprecated_script.py` (console-script shim) present |
| 7 | `test_wheel_excludes_tests_directory` | no `tests/` paths leak into the wheel |
| 8 | `test_wheel_declares_pytest11_entry_point` | `[pytest11]` block + `mcp_test_framework = mcp_test_framework._plugin` line in `entry_points.txt` |
| 9 | `test_wheel_declares_primary_console_script` | `mcp-contracts = mcp_test_framework.cli:app` declared |
| 10 | `test_wheel_declares_legacy_console_script_shim` | `mcp-test-framework = mcp_test_framework._deprecated_script:main` declared |
| 11 | `test_wheel_source_has_no_homelab_mcp_imports` | no actual `import homelab_mcp` / `from homelab_mcp` lines in any wheel `.py` source |

## CLI version assertions (2)

| # | Test | What it pins |
|---|------|--------------|
| 1 | `test_version_command_exits_zero_with_non_empty_output` | `mcp-contracts version` runs to completion via Typer CliRunner |
| 2 | `test_cli_source_references_new_dist_name` | `cli.py` source contains `metadata.version("mcp-contracts")` and NOT `metadata.version("mvp-test-framework")` |

## Test count delta

- Pre-Phase-26 baseline: 584 passing in `tests/framework/`
- Post-Phase-26: 597 passing in `tests/framework/` (delta = +13, matches plan target)
- 1 skipped, 2 xfailed, 17 deselected — unchanged from baseline

## DeprecationWarnings exercised (proves alias pathway works)

Full suite run surfaces multiple `DeprecationWarning` instances from the
unprefixed fixture aliases declared in `_plugin.py` and from the
`gen-sdet-classes` CLI shim — both prove the v1.4 deprecation aliases
are wired correctly under the existing `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]`
config.

## Wheel build evidence

`uv build --wheel` produces `mcp_contracts-0.1.0-py3-none-any.whl`. The
test fixture's zipfile walk confirms the seven required artifacts plus
the entry-point declarations are all present.

## Deviations from plan

One small deviation: the original plan body for `test_wheel_source_has_no_homelab_mcp_imports`
asserted `"import homelab_mcp" not in text` as a substring check, which
false-positived against `ollama_judge.py`'s docstring that mentions the
banned import by name to describe the principle. Tightened to a
line-prefix check (`stripped.startswith("import homelab_mcp")`) so
docstrings/comments don't trigger the gate. Functionally equivalent for
real imports; safer for documentation prose.

## Self-check

- [x] Both test files created and committed atomically
- [x] All 13 new tests pass locally (`uv run pytest tests/framework/test_wheel_shape.py tests/framework/test_cli_version.py -v`)
- [x] Full framework suite passes at the new baseline (597 passed)
- [x] No previously-passing test newly fails
- [x] Wheel-shape gate exercises all seven plan invariants
- [x] CLI-version gate exercises both source-string and runtime invariants
