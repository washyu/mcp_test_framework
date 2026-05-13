---
phase: 17-schema-driven-codegen-surface
plan: 05
subsystem: sdet-codegen-verification
tags: [pyright, typecheck, verification, codegen, gate]
requires:
  - "Plan 17-01 ToolResponse base (sdet/response.py)"
  - "Plan 17-02 _codegen.generate() file emitter"
  - "Plan 17-04 gen-sdet-classes CLI (indirect; this plan verifies the generator the CLI invokes)"
provides:
  - "pyright>=1.1.409 dev dep + [tool.pyright] scope config (D-04)"
  - "tests/framework/unit/test_codegen_typecheck.py -- pyright strict-mode gate for generated SDET classes"
  - "Negative-coverage test that proves the gate is real (anti-no-op insurance)"
affects:
  - "src/mcp_test_framework/sdet/_codegen.py (Rule 1 bug fix in _format_field_line)"
  - "pyproject.toml (dev dep + [tool.pyright] block)"
  - "uv.lock (pyright + nodeenv resolution)"
tech-stack-added:
  - "pyright 1.1.409 (with bundled nodeenv 1.10.0)"
patterns:
  - "subprocess.run([sys.executable, '-m', 'pyright', ...]) gating pattern"
  - "@pytest.mark.skipif(not _HAS_PYRIGHT) graceful CI fallback"
  - "Synthetic fixture (not live homelab-mcp) for deterministic verification"
key-files-created:
  - "tests/framework/unit/test_codegen_typecheck.py"
key-files-modified:
  - "pyproject.toml"
  - "uv.lock"
  - "src/mcp_test_framework/sdet/_codegen.py"
decisions:
  - "Pyright dev-dep version: >=1.1.409 (latest stable as of 2026-05; nodeenv-bundled Python wheel that 'uv add --group dev' resolves cleanly)"
  - "Scope: [tool.pyright] limits include + strict to sdet/generated/ + sdet/response.py only (Pitfall 4 mitigation; expand later when v1.0-v1.2 type debt is addressed)"
  - "Synthetic 5-tool fixture instead of live homelab-mcp -- gate is deterministic and doesn't drift with real-world server changes"
  - "Negative-coverage test (deliberately-broken generated file) added to prove the gate is real, not a no-op (T-17.05-01 mitigation)"
  - "Pyright NOT invoked from operator CLI (gen-sdet-classes) -- pyright runs in tests/CI only, per security_requirement"
metrics:
  duration: "~35 min"
  completed: "2026-05-12"
  tasks: 2
  commits: 3
status: complete
---

# Phase 17 Plan 05: Pyright Strict-Mode Typecheck Gate Summary

Add `pyright>=1.1.409` as a dev dependency, scope it to the generated SDET surface only, and ship the test that proves generated classes pass pyright strict mode against a synthetic 5-tool fixture (scalars + array + nested object + 2 degraded paths). Verification capstone for CODEGEN-04 + D-02 degradation strategy.

## What changed

### `pyproject.toml`
- Added `"pyright>=1.1.409"` to `[dependency-groups].dev` (between `pytest-timeout` and `ruff`).
- Added new `[tool.pyright]` block:
  - `include = ["src/mcp_test_framework/sdet/generated", "src/mcp_test_framework/sdet/response.py"]`
  - `strict = ["src/mcp_test_framework/sdet/generated", "src/mcp_test_framework/sdet/response.py"]`
  - `reportMissingTypeStubs = false`, `pythonVersion = "3.14"`
- Pitfall 4 (17-RESEARCH.md): the rest of `src/` carries v1.0-v1.2 type debt; the narrow scope prevents that from blocking the v1.3 gate.

### `tests/framework/unit/test_codegen_typecheck.py` (new, 187 lines)
- `test_synthetic_generated_passes_pyright_strict`: drives `_codegen.generate(...)` against the 5-tool fixture (simple_tool, array_tool, object_tool, enum_tool, oneof_tool), runs pyright as a subprocess via `python -m pyright`, asserts exit 0.
- `test_pyright_rejects_deliberately_broken_generated_file`: negative-coverage check. Mutates `simple_tool.py` to inject `_typecheck_violation: int = SimpleToolParams(name='x').name` (str -> int), asserts pyright fails. Pins T-17.05-01 (regression in `translate_tool` that emits type-broken source must surface).
- Skips cleanly via `@pytest.mark.skipif(not _HAS_PYRIGHT, ...)` when pyright is not on PATH (CI fallback per RESEARCH guidance).
- `_run_pyright()` uses `--pythonversion 3.14` + `timeout=120` to bound subprocess runtime (T-17.05-02 mitigation).

### `src/mcp_test_framework/sdet/_codegen.py` (Rule 1 bug fix in `_format_field_line`)
- **Bug uncovered by the new gate:** `_format_field_line` gated the `| None` union on `spec.degrade_reason is None`. Nested-object degradation produces `dict[str, typing.Any]` (a concrete type, NOT `typing.Any`), so the `| None` was skipped even though the field has `default=None`. Pyright (correctly) rejected `config: dict[str, Any] = Field(default=None)` with `reportAssignmentType`.
- **Fix:** dropped the `degrade_reason is None` clause from the predicate. The `py_type != "typing.Any"` guard alone already handles the "no `| None` on Any" intent. Now degraded-but-concrete-typed optional fields receive `| None` correctly.
- One-line predicate change; expanded comment documents the pyright finding for future readers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion `degraded_fields == 2` was wrong; actual is 3**
- **Found during:** Task 2 RED phase
- **Issue:** The plan's transcribed test body asserted `counts["degraded_fields"] == 2`, but the synthetic fixture triggers 3 degradations under Plan 17-02's walker: enum + oneOf + nested-object-with-properties. The plan's "5-tool fixture" comment in `<interfaces>` even noted "object_tool ... (degrades to dict[str, Any] in v1.3)".
- **Fix:** Updated assertion to `== 3` and added an inline comment explaining the three degradation sources.
- **Files modified:** `tests/framework/unit/test_codegen_typecheck.py`
- **Commit:** `3f2fd7c` (RED)

**2. [Rule 1 - Bug] `_format_field_line` skipped `| None` on degraded-but-typed optional fields**
- **Found during:** Task 2 (pyright rejected the generated `object_tool.py`)
- **Issue:** `_format_field_line` had a predicate `spec.degrade_reason is None and py_type != "typing.Any"` that excluded nested-object degradation (which emits the concrete type `dict[str, typing.Any]`). Optional + no default + degraded -> `Field(default=None)` but no `| None` -> pyright `reportAssignmentType` failure.
- **Fix:** dropped the `degrade_reason is None` clause. `py_type != "typing.Any"` already gates the Any case.
- **Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
- **Commit:** `eb06256` (GREEN)
- **Validation:** all 70 Phase 17 unit tests still pass after the fix; the synthetic-generated test now passes; the negative-coverage test continues to fail (which is the expected/asserted behavior -- it proves pyright rejects deliberate errors).

This is exactly the kind of regression T-17.05-01 in the threat model said the gate must catch -- and on its first run, it did. Strong evidence the gate is doing its job.

### Pre-existing baseline issues (out of scope)

Running the full `tests/framework/unit/` suite revealed 6 pre-existing failures (5 in `test_migration_doc.py`, 1 in `test_doc_scrub.py`, 1 in `test_cli_errors.py`) caused by `tests/docs/MIGRATION-v1-to-v2.md` being absent from the worktree's base commit. These are unrelated to Phase 17 and out of scope per the executor's "only auto-fix issues directly caused by current task's changes" rule. The Phase 17 plan's regression check (`tests/framework/unit/test_tool_response.py + test_codegen_walker.py + test_codegen_emitter.py + test_tool_factory.py + test_gen_sdet_classes_cli.py + test_codegen_typecheck.py`) -- 70 tests total -- all pass.

## Synthetic 5-tool fixture (for future refresh baseline)

The fixture in `_synthetic_tools()` exercises the D-02 coverage matrix and is intentionally compact + deterministic:

| Tool name | Schema shape | Generator output | Degraded? |
| --- | --- | --- | --- |
| `simple_tool` | `name: str (required)`, `count: int = 1` | scalars + default | no (0 degraded) |
| `array_tool` | `tags: list[str] (required)` | `list[str]` | no (0 degraded) |
| `object_tool` | `config: object with properties (optional, no default)` | `dict[str, typing.Any] \| None` | yes -- nested-object-recursion (1 degraded) |
| `enum_tool` | `kind: string + enum (required)` | `typing.Any` | yes -- enum (1 degraded) |
| `oneof_tool` | `target: oneOf (optional, no default)` | `typing.Any` | yes -- oneOf (1 degraded) |

All five tools have `outputSchema=None`, so their `<Tool>Response` classes are D-06 stubs (`pass` body). Total degraded fields: 3.

The fixture is rebuilt at every test run into `tmp_path` so there is no on-disk baseline file to maintain.

## v1.4 expansion path

When `[tool.pyright]` scope expands (the eventual goal once v1.0-v1.2 type debt is paid down):

1. Add `"src/mcp_test_framework"` to `include`. Move to `strict` only after every error is fixed.
2. Consider tightening `_codegen.translate_tool` further to emit `Literal[...]` for enums (currently `typing.Any`) and `X | None` for `type: ["X", "null"]` (currently `typing.Any`). The pyright gate will surface any regressions.
3. The synthetic fixture in `_synthetic_tools()` can grow new entries; the negative-coverage test stays as the anti-no-op anchor.

## Threat Flags

None. This plan adds verification only; it introduces no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check: PASSED

- `tests/framework/unit/test_codegen_typecheck.py` exists at expected path.
- Commit `26adec9` (chore: pyright dev dep), `3f2fd7c` (test: RED), `eb06256` (fix: GREEN) all reachable in `git log`.
- `uv run pyright --version` -> `pyright 1.1.409`, exit 0.
- `uv run pyright src/mcp_test_framework/sdet/response.py` -> `0 errors, 0 warnings, 0 informations`, exit 0.
- Full Phase 17 regression (70 tests across test_tool_response, test_codegen_walker, test_codegen_emitter, test_tool_factory, test_gen_sdet_classes_cli, test_codegen_typecheck): all PASS.

## TDD Gate Compliance

Plan declared `type: execute` at frontmatter level; Task 2 carried `tdd="true"`. Gate sequence in `git log` shows the correct ordering:

- `3f2fd7c test(17-05): add failing pyright strict-mode typecheck gate` -- RED gate (test fails because of the codegen bug it exposes)
- `eb06256 fix(17-05): emit \`| None\` on optional fields even when degraded` -- GREEN gate (codegen fix makes the test pass)

No REFACTOR commit was needed; the fix was a one-line predicate change with no follow-up cleanup.
