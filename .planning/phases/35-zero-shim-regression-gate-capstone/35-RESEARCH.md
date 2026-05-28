# Phase 35: Zero-shim regression gate (capstone) — Research

**Researched:** 2026-05-27
**Domain:** Python AST inspection, pytest in-process probing, Typer CliRunner
**Confidence:** HIGH — all findings verified from live source files in this session

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Behavioral-first + narrow AST backstop. Primary detection = probe each surface and assert it hard-rejects or no-ops. "Zero shims" means "no functional shim / every surviving surface hard-rejects," NOT "the word `sdet` never appears."
- **D-02:** Behavior-only assertions. Each probe asserts observable behavior (import raises, CLI exits non-zero, fixture fails at resolution, `tests/sdet/` not auto-collected, config alias rejected at load, `MCPTF_CONFIG_FILE` inert). Does NOT re-assert exact operator-tone message text — Phase 31/32 per-surface tests pin that.
- **D-03:** Narrow AST backstop for the two FULLY-DELETED config surfaces (no surviving intercept): assert via AST that `src/` contains no `Field(alias="sdet")` on the config model and no `os.environ` read of `MCPTF_CONFIG_FILE` in config-source code. NOT a text-regex sweep for the token `sdet`.
- **D-04:** Separate named test function per surface (e.g. `test_import_surface_shim_absent`, `test_cli_surface_shims_reject`, etc.). Five surface groups; sub-shims within a surface are separate asserts inside the surface's function.
- **D-05:** Self-explaining failure messages naming: the surface, the specific probe, the requirement id (SHIM-0x), and the fact that the shim must remain a hard-reject intercept until v1.6 clean-delete.
- **D-06:** Coexist with `test_sdet_rename_leak_gate.py`. Phase 35 corrects its stale docstring: `"Removed in v1.5 when the deprecation shims drop and the gate becomes a no-op."` → reflects that grandfathered intercepts keep it live until v1.6. LIGHT docstring fix only, NOT a behavior change.
- **D-07:** Do not duplicate per-surface message-text tests (Phase 31/32 already own those).
- **D-08:** Single file under `tests/framework/`, no shared fixtures, runtime <1s standalone (in-process probes + AST sweeps only — NO subprocess, NO network).

### Claude's Discretion

- Exact test-function names and internal ordering of surface probes.
- Whether the AST backstop lives in its own helper or inline.

### Deferred Ideas (OUT OF SCOPE)

- v1.6 clean-deletion of the grandfathered intercepts.
- CHANGELOG / milestone footnote for the v1.4→v1.5 shim retirement.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHIM-09 | Regression-test gate pins zero-shim state in CI — a single test sweep across importable surface (`mcp_test_framework.sdet`), CLI surface (`--sdet`, `gen-sdet-classes`, `mcp-test-framework`), config surface (`cfg.sdet.*`, `MCPTF_CONFIG_FILE`), fixture names (unprefixed), and discovery surface (`tests/sdet/`) returns zero matches and blocks reintroduction. | All five surfaces verified from live source. RFP-1 and RFP-2 answered concretely with copy-pasteable AST node shapes and the chosen no-subprocess console-script approach. |
</phase_requirements>

---

## Summary

Phase 35 ships a single test file (`tests/framework/test_zero_shim_regression_gate.py`) with one named test function per surface. All five surfaces have been verified from live source. The two primary research questions (RFP-1: AST backstop shapes; RFP-2: no-subprocess console-script probe) are answered concretely below with the exact node types visible in the current source.

The gate is behavioral-first: it probes each surface by exercising its intercept in-process and asserting a hard reject. The AST backstop is narrowly scoped to the two config surfaces that were fully deleted (no surviving intercept) — it asserts ABSENCE of specific AST constructs rather than presence of the token `sdet`.

**Primary recommendation:** Five `pytest` functions, no shared fixtures, no subprocess, no network. Runtime <1s. AST walks cover `src/mcp_test_framework/config.py` only. Every other surface is probed in-process with `importlib`, `typer.testing.CliRunner`, and `pytest.Pytester` — the same techniques already established in the per-surface tests this gate must not duplicate.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Import-surface intercept probe | Test process (importlib) | — | `sdet/__init__.py` raises at module load; importlib.import_module captures the raise in-process |
| CLI surface intercept probe | Test process (typer CliRunner) | — | `CliRunner.invoke(app, ...)` runs Typer in-process; no subprocess needed |
| Config AST backstop | Test process (ast module) | — | AST walk on config.py source; pure static analysis, no runtime config load |
| Fixture surface probe | pytester subprocess (unavoidable) | — | Fixture resolution only fires inside a pytest session; pytester is the standard in-process-but-subprocess mechanism |
| Discovery surface probe | Test process (path check) | — | Verify `tests/sdet/` is not in pytest's default testpaths |
| Console-script hard-reject probe | Test process (import + call) | — | `_deprecated_script.main()` calls `sys.exit(2)`; catch with `pytest.raises(SystemExit)` |

---

## RFP-1: AST Backstop — Exact Node Shapes and Target Module

### Which module to walk

`src/mcp_test_framework/config.py` is the sole target. [VERIFIED: read live source]

Phase 31 fully deleted:
- The `validation_alias=AliasChoices('test_code','sdet')` on the `test_code` field.
- The `_warn_or_reject_legacy_sdet_key` model validator.
- The `_check_legacy_sdet_key_in_yaml` pre-scan.
- The `model_validate` classmethod override.
- The `os.environ.get("MCPTF_CONFIG_FILE")` path-pointer fallback inside `settings_customise_sources`.

The current `config.py` has:
- `test_code: TestCodeConfig = Field(...)` — plain `Field(...)`, no alias keyword at all.
- `settings_customise_sources` reads `init_settings.init_kwargs.pop("yaml_file", None)` and has NO `os.environ` call anywhere. The comment block explicitly documents that the env-var fallback was deleted in v1.5. [VERIFIED: read `config.py` lines 1–123]

The env-var detection that DOES survive lives in `_plugin.py:pytest_configure` (`os.environ.get("MCPTF_CONFIG_FILE")` at line 186 of `_plugin.py`). The AST backstop must target **`config.py` only**, not `_plugin.py`. The Phase 31 scrub test (`test_phase_31_mcptf_config_file_scrub.py`) already asserts `_plugin.py` is the sole survivor — the SHIM-09 AST backstop is an orthogonal check on the config MODEL specifically.

### AST node shape to assert ABSENT: `Field(alias="sdet")` keyword argument

The check is: no `ast.Call` node in `config.py` whose func resolves to `Field` (or `AliasChoices`) carries an `ast.keyword` with `arg="alias"` or `arg="validation_alias"` whose value is an `ast.Constant` with `.value` in `{"sdet"}`.

The current (post-deletion) field declaration is:

```python
# config.py line 61
test_code: TestCodeConfig = Field(...)
```

In AST terms, this is an `ast.Assign` (or `ast.AnnAssign`) whose value is an `ast.Call` to `Field` with a single `ast.Constant(value=Ellipsis)` positional arg and NO keywords. The gate asserts no `ast.keyword` with `arg` in `{"alias", "validation_alias"}` and value `ast.Constant(value="sdet")` appears in ANY `ast.Call` anywhere in the file.

**Concrete walk pattern:**

```python
import ast
from pathlib import Path

CONFIG_PY = Path("src/mcp_test_framework/config.py")
source = CONFIG_PY.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(CONFIG_PY))

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg in ("alias", "validation_alias") and isinstance(kw.value, ast.Constant):
                if kw.value.value == "sdet":
                    # This is the reintroduction shape — assertion fails here
                    ...
```

The pre-deletion shape (what the gate guards against reintroduction of) was:

```python
# (DELETED) pre-Phase-31 config.py — the shape the gate must detect if reintroduced
from pydantic import AliasChoices
test_code: TestCodeConfig = Field(
    ...,
    validation_alias=AliasChoices('test_code', 'sdet')
)
```

In AST terms that is: `ast.Call(func=Name("Field"), keywords=[ast.keyword(arg="validation_alias", value=ast.Call(func=Name("AliasChoices"), args=[Constant("test_code"), Constant("sdet")]))])`. A simpler sentinel that catches both the direct `alias="sdet"` and the `AliasChoices(..., "sdet")` form: walk for any `ast.Constant(value="sdet")` that appears as a direct `keyword.value` OR as an argument inside a `keyword.value` `ast.Call` where the outer `keyword.arg` is `"alias"` or `"validation_alias"`. The simplest approach that is not over-broad: assert no `ast.keyword` in any `ast.Call` satisfies `kw.arg in {"alias", "validation_alias"} and _contains_sdet_literal(kw.value)`.

### AST node shape to assert ABSENT: `os.environ` read of `MCPTF_CONFIG_FILE`

The check is: no call to `os.environ.get(...)`, `os.environ[...]`, or `os.getenv(...)` in `config.py` passes the string literal `"MCPTF_CONFIG_FILE"` as an argument.

The current `config.py` has zero `os` imports and zero `os.environ` or `os.getenv` references. [VERIFIED: read entire `config.py`]

The pre-deletion shape was (inside `settings_customise_sources`):

```python
# (DELETED) pre-Phase-31 config.py
import os
yaml_file = os.environ.get("MCPTF_CONFIG_FILE") or init_settings.init_kwargs.pop("yaml_file", None)
```

**Concrete walk pattern:**

```python
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        # os.environ.get("MCPTF_CONFIG_FILE") or os.getenv("MCPTF_CONFIG_FILE")
        if _is_environ_read(node):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value == "MCPTF_CONFIG_FILE":
                    # Reintroduction detected
                    ...
    if isinstance(node, ast.Subscript):
        # os.environ["MCPTF_CONFIG_FILE"]
        ...
```

Where `_is_environ_read(node)` matches:
- `ast.Call` whose `func` is `ast.Attribute(attr="get")` on `ast.Attribute(attr="environ")` on `ast.Name(id="os")` — i.e., `os.environ.get(...)`
- `ast.Call` whose `func` is `ast.Attribute(attr="getenv")` on `ast.Name(id="os")` — i.e., `os.getenv(...)`

And the `ast.Subscript` check covers `os.environ["MCPTF_CONFIG_FILE"]`.

**Simpler alternative** (recommended for the gate): since `config.py` currently has no `os` import at all, the gate can first assert `"MCPTF_CONFIG_FILE"` does not appear as any `ast.Constant` string value in the entire file. This is correct because: (a) config.py has no comment-level references to the env var today, and (b) if it were reintroduced, the literal would appear as a constant arg. This is NOT the same as a text-regex scan — it only matches string literals in the AST, not identifiers or comments. The gate should use this as a sentinel for config.py specifically and clearly document that the separate `test_phase_31_mcptf_config_file_scrub.py` already handles the broader src/ sweep.

---

## RFP-2: Console-Script Hard-Reject Without Subprocess

### The existing per-surface test

`tests/framework/unit/test_console_script_removed.py` uses a **subprocess** (`subprocess.run([sys.executable, "-c", "from mcp_test_framework._deprecated_script import main; main()"])`). The per-surface test pins verbatim message text and exit code 2 via subprocess. [VERIFIED: read file]

SHIM-09 must NOT use a subprocess (D-08 constraint: <1s, no network, no subprocess). It also must NOT duplicate the message-text assertions (D-02/D-07).

### The in-process approach: import + `pytest.raises(SystemExit)`

`src/mcp_test_framework/_deprecated_script.py` has this structure [VERIFIED: read live source]:

```python
import sys

def main() -> None:
    msg = "[mcp-contracts] mcp-test-framework was removed in v1.5\n..."
    print(msg, file=sys.stderr)
    sys.exit(2)
```

`sys.exit(2)` raises `SystemExit(2)`. In-process, this is catchable with `pytest.raises(SystemExit)`.

**Recommended in-process probe:**

```python
import sys
import pytest
from mcp_test_framework import _deprecated_script

def test_console_script_surface_shim_absent():
    with pytest.raises(SystemExit) as exc_info:
        _deprecated_script.main()
    assert exc_info.value.code == 2, (
        "SHIM-08 / SHIM-09: mcp-test-framework console-script hard-reject "
        "must sys.exit(2); got code={exc_info.value.code!r}. "
        "The _deprecated_script.main() entry must remain a hard-reject "
        "intercept (not a working wrapper) until the v1.6 clean-delete. "
        "Reintroducing a functional shim body here breaks the gate."
    )
```

This is zero-subprocess, zero-network, instantaneous. It asserts the behavioral STATE (hard-rejects with exit code 2) without duplicating the message-text assertions in `test_console_script_removed.py`.

### Alternative: parse pyproject.toml wiring

Assert `pyproject.toml` `[project.scripts]` still wires `mcp-test-framework` to `mcp_test_framework._deprecated_script:main` rather than a working entrypoint. This is a structural probe (no execution), but it does NOT verify the body actually raises — a contributor could change `main()` to a working wrapper while keeping the pyproject.toml entry. The execution probe is more robust.

**Verdict:** Use the `pytest.raises(SystemExit)` probe. Add a pyproject.toml structural check as a secondary assertion inside the same test function to catch the "delete the entrypoint entirely" regression (stock `command not found` gives zero operator guidance).

**pyproject.toml check pattern:**

```python
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def _check_pyproject_scripts():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_bytes().decode())
    scripts = data.get("project", {}).get("scripts", {})
    assert "mcp-test-framework" in scripts, (
        "SHIM-08 / SHIM-09: [project.scripts].mcp-test-framework entry missing from "
        "pyproject.toml. The entry must remain wired (to the hard-reject stub) through "
        "v1.5 so operators get a pointer message instead of shell 'command not found'. "
        "Clean-delete this entry in v1.6, not before."
    )
    target = scripts.get("mcp-test-framework", "")
    assert "_deprecated_script" in target, (
        f"SHIM-08 / SHIM-09: mcp-test-framework script wiring ({target!r}) no longer "
        "points at _deprecated_script. Must remain wired to the hard-reject stub "
        "through v1.5; v1.6 removes the entry."
    )
```

Note: Python 3.11+ has `tomllib` in stdlib. Python 3.14 (this project's runtime) has it. No extra dep needed.

---

## Secondary Research: Per-Surface Probe Techniques

### Surface 1 — Import surface (`mcp_test_framework.sdet`)

**Live intercept:** `src/mcp_test_framework/sdet/__init__.py` raises `ModuleNotFoundError` unconditionally at module scope (line 11). [VERIFIED: read file]

**In-process probe technique** (matches `test_error_style.py` lines 185–208 which already verifies this):

```python
import importlib
import sys

# Pop the cached module (if this test session imported it earlier).
sys.modules.pop("mcp_test_framework.sdet", None)
with pytest.raises(ModuleNotFoundError):
    importlib.import_module("mcp_test_framework.sdet")
```

**SHIM-09 assertion (behavior-only, no message text):** `ModuleNotFoundError` is raised. Period. The exact message text is pinned by `test_error_style_sdet_package_removed` in `test_error_style.py` — do not duplicate it.

**What behavioral regression looks like:** If the `sdet/` package is cleaned-deleted outright (no `__init__.py`), Python's stock `ModuleNotFoundError: No module named 'mcp_test_framework.sdet'` is still raised — so this probe remains green. The RENAME-06 text gate (`test_sdet_rename_leak_gate.py`) separately guards against the shim's operator-tone message disappearing from the source. SHIM-09 does not need to guard both.

**What functional reintroduction looks like:** If `sdet/__init__.py` is changed from `raise ModuleNotFoundError(...)` back to re-exporting symbols, the `pytest.raises(ModuleNotFoundError)` fails. That is the regression the gate catches.

### Surface 2 — CLI surface (`--sdet`, `gen-sdet-classes`)

**Live intercepts:**
- `cli.py` line 773–779: `sdet_legacy: bool = typer.Option(False, "--sdet", hidden=True, callback=_sdet_flag_removed, is_eager=True)`. The callback raises `typer.BadParameter` with pointer text. [VERIFIED: grep result]
- `cli.py` line 1458–1473: `@app.command("gen-sdet-classes", hidden=True)` with body `raise typer.BadParameter(...)`. [VERIFIED: read source]

**In-process probe technique** (matches `test_error_style.py` lines 211–262):

```python
from typer.testing import CliRunner
from mcp_test_framework.cli import app

runner = CliRunner()

# --sdet flag
result = runner.invoke(app, ["run", "--sdet"])
assert result.exit_code == 2

# gen-sdet-classes command
result = runner.invoke(app, ["gen-sdet-classes"])
assert result.exit_code == 2
```

**SHIM-09 assertion:** exit code == 2 for both. No message text assertions (D-02).

**What functional reintroduction looks like:** If `_sdet_flag_removed` is changed to return normally (instead of raising `BadParameter`), or `_gen_sdet_classes_removed` runs real codegen logic, the exit code drops to 0. The gate catches it.

### Surface 3 — Console-script surface (`mcp-test-framework`)

Covered in full under RFP-2 above.

### Surface 4 — Config surface (`cfg.sdet.*`, `MCPTF_CONFIG_FILE`)

**Live situation:** No surviving intercept. Both surfaces are FULLY DELETED. The AST backstop (D-03) guards against reintroduction. [VERIFIED: read `config.py` entirely]

**Probe technique:** AST walk of `config.py` only. See RFP-1 above for the exact node shapes.

**What functional reintroduction looks like:**
- `Field(alias="sdet")` or `Field(validation_alias=AliasChoices('test_code','sdet'))` reappears on the `test_code` field → the AST check finds the keyword and fails.
- `os.environ.get("MCPTF_CONFIG_FILE")` reappears in `settings_customise_sources` → the AST check finds the literal and fails.

**Important: do NOT probe the `sdet:` config rejection dynamically.** The `cli.py` `_emit_operator_error_for_validation` function already has a live intercept for `sdet:` YAML keys (`extra_forbidden` at `loc=("sdet",)`) — but this is handled by `cli.py`'s error mapper (lines 309–335), NOT by `config.py` itself. The config model's `extra="forbid"` already rejects `sdet:` as a generic ExtraForbidden error. The SHIM-09 gate does not need to dynamically load a YAML with `sdet:` and assert rejection — `test_config_sdet_field.py` already pins that. The AST backstop is sufficient because it guards against the MODEL itself re-acquiring an alias.

### Surface 5 — Fixture surface (six unprefixed stub-raise fixtures)

**Live intercept:** `_plugin.py` lines 549–648 define six `@pytest.fixture(scope="session")` stubs: `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`. Each body calls `pytest.fail(MSG, pytrace=False)`. [VERIFIED: read live source]

**In-process probe problem:** Fixture resolution only fires inside a real pytest session; you cannot call `config()` directly in unit-test context. The per-surface test (`test_plugin_unprefixed_fixtures_removed.py`) already uses `pytester.runpytest_subprocess()` to verify each fixture. That test is expensive (6 subprocess runs). [VERIFIED: read file]

**SHIM-09 approach (state sweep, not execution):** Assert the six fixture names are still registered in `_plugin.py` as stubs by inspecting the SOURCE — check that `@pytest.fixture` decorated functions named `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters` exist in `_plugin.py` and each calls `pytest.fail`. An AST-based check on `_plugin.py` is appropriate here (same technique as the config backstop).

Alternatively, import `mcp_test_framework._plugin` and inspect that the fixture names are registered via `pytest`'s fixture manager — but this requires a real pytest session context.

**Recommended approach for SHIM-09:** Source-code structural check (AST walk `_plugin.py`). Assert each of the six stub function names is present and each has a body that calls `pytest.fail`. This catches:
- Clean-deletion of a stub → name no longer in the AST → gate fails.
- Replacement of `pytest.fail(...)` with `return mcp_config` (re-aliasing) → body no longer calls `pytest.fail` → gate fails.

**Pattern:**

```python
import ast

PLUGIN_SRC = (REPO_ROOT / "src" / "mcp_test_framework" / "_plugin.py").read_text(encoding="utf-8")
tree = ast.parse(PLUGIN_SRC, filename="_plugin.py")

EXPECTED_STUBS = {"config", "judge", "target_tool", "rubric_clarity", "rubric_disambiguation", "rubric_parameters"}

# Collect fixture-decorated function names whose bodies contain pytest.fail
stub_funcs = set()
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        # Check @pytest.fixture decorator
        for dec in node.decorator_list:
            if _is_pytest_fixture(dec):
                # Check body contains pytest.fail call
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and _is_pytest_fail(child):
                        stub_funcs.add(node.name)
                        break

missing = EXPECTED_STUBS - stub_funcs
assert not missing, (
    f"SHIM-07 / SHIM-09: fixture stub-raise intercepts for {sorted(missing)!r} "
    "are no longer registered in _plugin.py as pytest.fail stubs. ..."
)
```

### Surface 6 — Discovery surface (`tests/sdet/` warn-on-presence)

**Live intercept:** `_plugin.py` lines 332–353 in `pytest_collection` hook: checks `session.config.rootpath / "tests" / "sdet"` and if it exists with `test_*.py` files, emits a `DeprecationWarning` via `warnings.warn(...)`. Discovery of `tests/sdet/` is NOT added to pytest's collection path. [VERIFIED: read `_plugin.py`]

**SHIM-09 assertion:** Assert that `tests/sdet/` is NOT in the configured `testpaths` / is not auto-discovered. The behavioral state is: the path is excluded from collection.

**In-process probe for the gate:** Check that `tests/sdet/` is not in pytest's default discovery paths from `pyproject.toml`. The pyproject.toml `testpaths = ["tests"]` means pytest WOULD descend into `tests/sdet/` unless excluded. The framework excludes it by not having `tests/sdet/` in the tree (the actual `tests/sdet/` in this repo is the one created by the user to hold test files — check if it's absent from the default `testpaths`).

**More robust approach:** Assert the WARN-DETECTOR is present in `_plugin.py` (structural check): the source contains the warn string `"tests/sdet/ is no longer auto-discovered as of v1.5"`. If a contributor deletes the detector, `tests/sdet/` files silently collect without warning — which is a different regression than functional shim reintroduction, but worth catching.

**Simplest in-process check:** Assert the repo does NOT contain `tests/sdet/test_*.py` files (i.e., no test files live in the legacy directory). This verifies the discovery surface from the other direction: the directory either doesn't exist or contains no collectible tests.

```python
import glob
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sdet_tests = list((REPO_ROOT / "tests" / "sdet").glob("test_*.py")) if (REPO_ROOT / "tests" / "sdet").is_dir() else []
assert not sdet_tests, (
    f"SHIM-06 / SHIM-09: tests/sdet/ contains {len(sdet_tests)} test_*.py file(s): "
    f"{[str(p.relative_to(REPO_ROOT)) for p in sdet_tests]!r}. ..."
)
```

Note: The actual `tests/sdet/` in this repo contains generated files, not test files — verify with `Glob` before planning. The structural detector in `_plugin.py` fires only when `test_*.py` files exist there.

---

## Structural Analog: `test_sdet_rename_leak_gate.py`

**Current docstring (stale — D-06 fix target):**

```python
"""RENAME-06 acceptance gate: scan operator-facing surfaces for residual `sdet` terminology and planning-ID leaks.

Implements D-17 patterns + D-16 scope + D-18 exclusions for the Phase 25 public-API rename.
Removed in v1.5 when the deprecation shims drop and the gate becomes a no-op.
"""  # noqa: sdet-rename-shim
```

The **stale line** is: `"Removed in v1.5 when the deprecation shims drop and the gate becomes a no-op."`

The correct replacement: something like `"Survives v1.5 — the grandfathered hard-reject intercepts keep the noqa exclusions live until the v1.6 clean-delete."` (exact wording is Claude's discretion per D-06).

**Reusable patterns from this gate:**
- `REPO_ROOT = Path(__file__).resolve().parents[2]` — standard REPO_ROOT derivation. [VERIFIED: line 14]
- `ast.parse(source) + ast.walk(tree)` — standard walk pattern.
- `# noqa: sdet-rename-shim` exclusion mechanism — the SHIM-09 AST backstop bypasses this entirely by matching constructs (not tokens), so it does NOT need to honor or maintain the marker list.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing in test | Custom string parsing | `tomllib` (stdlib 3.11+) | Project is Python 3.14; `tomllib` is in stdlib, zero additional dep |
| In-process CLI invocation | `subprocess.run(["mcp-contracts", ...])` | `typer.testing.CliRunner().invoke(app, [...])` | Same technique as per-surface tests; in-process, zero network |
| Fixture resolution probe | Direct `config()` call | AST structural check on `_plugin.py` | Fixture resolution requires a real pytest session; structural check is zero-subprocess |
| Module import | `importlib.reload(...)` | `sys.modules.pop + importlib.import_module` | Guarantees fresh load even if a prior test cached the module |

---

## Common Pitfalls

### Pitfall 1: AST walk scope too broad

**What goes wrong:** Walking ALL of `src/mcp_test_framework/` for the `MCPTF_CONFIG_FILE` constant catches the grandfathered detection in `_plugin.py:pytest_configure` and fails the gate.

**Prevention:** Walk `config.py` ONLY for the `MCPTF_CONFIG_FILE` check. The `test_phase_31_mcptf_config_file_scrub.py` test already handles the broader src/ sweep with the correct exclusion. Do NOT duplicate its scope.

### Pitfall 2: Text-scanning `config.py` for the token `sdet`

**What goes wrong:** `config.py` has comments (lines 109–115) referencing the env-var deletion and the cli.py mapper for the `sdet:` key (lines 309–335 in `cli.py` — not `config.py`). A text scan for `sdet` in `config.py` could catch a comment.

**Prevention:** Use the targeted AST walk (match `Field` `keyword` with `arg="alias"`/`"validation_alias"` and value `Constant("sdet")`), not a string scan of the file text. D-03 explicitly rejects text-regex sweeps for this reason.

### Pitfall 3: Duplicating per-surface message-text assertions

**What goes wrong:** Adding `assert "mcp_test_framework.sdet was removed in v1.5" in msg` to the import probe duplicates `test_error_style_sdet_package_removed`. Two tests pin the same string; one gets stale when the message changes.

**Prevention:** D-02 is explicit — SHIM-09 asserts behavior (raises/exits/fails) only. No verbatim message text.

### Pitfall 4: Using pytester for the fixture surface

**What goes wrong:** `pytester.runpytest_subprocess()` for each of the six fixtures adds 6 subprocess round-trips, violating the <1s runtime constraint.

**Prevention:** Use an AST structural check on `_plugin.py` to assert all six stubs exist and call `pytest.fail`. The behavioral proof is already provided by `test_plugin_unprefixed_fixtures_removed.py`.

### Pitfall 5: Missing `sys.modules.pop` before import probe

**What goes wrong:** If another test in the session imported `mcp_test_framework.sdet` first, the cached entry in `sys.modules` is `None` (because the import raised). A second `importlib.import_module("mcp_test_framework.sdet")` will either re-raise or return the cached value, depending on Python version.

**Prevention:** Always `sys.modules.pop("mcp_test_framework.sdet", None)` before the import probe (matches the per-surface test pattern).

### Pitfall 6: Checking pyproject.toml via text scan

**What goes wrong:** A text search for `mcp-test-framework` in `pyproject.toml` also matches comments about the deprecation history. Use `tomllib` to parse the structured `[project.scripts]` table.

**Prevention:** Use `tomllib.loads(pyproject_toml_bytes.decode())` and traverse `data["project"]["scripts"]` directly.

---

## Code Examples

### Import surface probe (in-process, no subprocess)

```python
# Source: verified from tests/framework/unit/test_error_style.py lines 185-208
import importlib
import sys

sys.modules.pop("mcp_test_framework.sdet", None)
with pytest.raises(ModuleNotFoundError):
    importlib.import_module("mcp_test_framework.sdet")
```

### CLI surface probe (in-process CliRunner)

```python
# Source: verified from tests/framework/unit/test_error_style.py lines 211-262
from typer.testing import CliRunner
from mcp_test_framework.cli import app

runner = CliRunner()
result = runner.invoke(app, ["run", "--sdet"])
assert result.exit_code == 2

result = runner.invoke(app, ["gen-sdet-classes"])
assert result.exit_code == 2
```

### Console-script probe (in-process sys.exit catch)

```python
# Source: verified from live _deprecated_script.py — main() calls sys.exit(2)
import pytest
from mcp_test_framework import _deprecated_script

with pytest.raises(SystemExit) as exc_info:
    _deprecated_script.main()
assert exc_info.value.code == 2
```

### pyproject.toml structural check

```python
# Source: stdlib tomllib (Python 3.11+, available in this project's Python 3.14)
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_bytes().decode())
scripts = data["project"]["scripts"]
assert "mcp-test-framework" in scripts  # entry still present (not prematurely deleted)
assert "_deprecated_script" in scripts["mcp-test-framework"]  # wired to the hard-reject stub
```

### Config AST backstop — Field alias check

```python
# Source: verified current config.py — Field(...) with no alias keyword
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_SRC = (REPO_ROOT / "src" / "mcp_test_framework" / "config.py").read_text(encoding="utf-8")
tree = ast.parse(CONFIG_SRC, filename="config.py")

offending_nodes = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg in ("alias", "validation_alias"):
                # Check if "sdet" appears as a constant anywhere in kw.value
                for vnode in ast.walk(kw.value):
                    if isinstance(vnode, ast.Constant) and vnode.value == "sdet":
                        offending_nodes.append(getattr(node, "lineno", "?"))
assert not offending_nodes, (
    f"SHIM-04 / SHIM-09: Field(alias='sdet') or Field(validation_alias=AliasChoices(...,'sdet')) "
    f"found at line(s) {offending_nodes!r} in config.py. ..."
)
```

### Config AST backstop — MCPTF_CONFIG_FILE env read check

```python
# Source: verified current config.py — no os import, no MCPTF_CONFIG_FILE constant
# Walk config.py only (NOT _plugin.py, which has the grandfathered detector)
offending_lines = []
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and node.value == "MCPTF_CONFIG_FILE":
        offending_lines.append(getattr(node, "lineno", "?"))
assert not offending_lines, (
    f"SHIM-05 / SHIM-09: 'MCPTF_CONFIG_FILE' appears as a string literal in config.py "
    f"at line(s) {offending_lines!r}. The env-var route was fully deleted in Phase 31. ..."
)
```

### Fixture surface structural check

```python
# Source: verified _plugin.py lines 536-648 — six stub defs, each body calls pytest.fail
PLUGIN_SRC = (REPO_ROOT / "src" / "mcp_test_framework" / "_plugin.py").read_text(encoding="utf-8")
tree_p = ast.parse(PLUGIN_SRC, filename="_plugin.py")

EXPECTED_STUBS = frozenset({"config", "judge", "target_tool", "rubric_clarity", "rubric_disambiguation", "rubric_parameters"})
stubs_with_fail: set[str] = set()

for node in ast.walk(tree_p):
    if not isinstance(node, ast.FunctionDef) or node.name not in EXPECTED_STUBS:
        continue
    # Check it's decorated with @pytest.fixture
    is_fixture = any(
        (isinstance(d, ast.Attribute) and d.attr == "fixture") or
        (isinstance(d, ast.Name) and d.id == "fixture")
        for d in node.decorator_list
    )
    if not is_fixture:
        continue
    # Check body contains a pytest.fail call
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if (isinstance(func, ast.Attribute) and func.attr == "fail") or \
               (isinstance(func, ast.Name) and func.id == "fail"):
                stubs_with_fail.add(node.name)
                break

missing = EXPECTED_STUBS - stubs_with_fail
assert not missing, (
    f"SHIM-07 / SHIM-09: {sorted(missing)!r} stub-raise fixture(s) no longer registered "
    f"as pytest.fail stubs in _plugin.py. ..."
)
```

---

## File Structure Confirmation

The single output file:

```
tests/framework/test_zero_shim_regression_gate.py
```

Five test functions (names are Claude's discretion per D-04 / D-08 guidance):

```
test_import_surface_shim_absent           # Surface 1: sdet/__init__.py raises
test_cli_surface_shims_reject             # Surface 2: --sdet, gen-sdet-classes exit 2; plus Surface 3: console-script sys.exit(2) + pyproject.toml structural check
test_config_surface_shims_absent          # Surface 4: AST backstop on config.py
test_fixture_surface_stubs_present        # Surface 5: AST structural check on _plugin.py
test_discovery_surface_not_auto_collected # Surface 6: tests/sdet/ has no test_*.py files
```

Plus a D-06 side task (not a new test function): edit the stale docstring in `test_sdet_rename_leak_gate.py`.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/static-analysis. No external dependencies beyond Python 3.14 stdlib (`ast`, `tomllib`) and the existing pytest + typer.testing already in the dev dependency group.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `tests/sdet/` in this repo contains no `test_*.py` files (only generated/scaffold files) | Discovery surface probe | If it contains live test files, the discovery probe fails — but that would be a legitimate regression catch, not a false positive |
| A2 | `tomllib` (stdlib 3.11+) is importable in the test environment without installation | Console-script pyproject probe | Low risk — project pins Python 3.14 where tomllib is guaranteed in stdlib |

---

## Sources

### Primary (HIGH confidence)

- `src/mcp_test_framework/config.py` — confirmed: no `Field(alias=...)`, no `os.environ`, no `MCPTF_CONFIG_FILE` constant. Read entire file in this session.
- `src/mcp_test_framework/_deprecated_script.py` — confirmed: `main()` calls `sys.exit(2)`. Read entire file.
- `src/mcp_test_framework/sdet/__init__.py` — confirmed: unconditional `raise ModuleNotFoundError(...)` at module scope. Read entire file.
- `src/mcp_test_framework/_plugin.py` — confirmed: six `@pytest.fixture` stubs at lines 549–648, each calling `pytest.fail`; `tests/sdet/` detector in `pytest_collection` lines 332–353; `os.environ.get("MCPTF_CONFIG_FILE")` grandfathered at line 186. Read selected sections.
- `src/mcp_test_framework/cli.py` — confirmed: `--sdet` hidden option with `_sdet_flag_removed` callback (raises `typer.BadParameter`); `gen-sdet-classes` hidden command (raises `typer.BadParameter`). Verified via grep.
- `pyproject.toml` — confirmed: `mcp-test-framework = "mcp_test_framework._deprecated_script:main"` in `[project.scripts]`. Read entire file.
- `tests/framework/test_sdet_rename_leak_gate.py` — confirmed: stale docstring text identified, REPO_ROOT pattern, AST walk structure. Read entire file.
- `tests/framework/unit/test_console_script_removed.py` — confirmed: uses subprocess; SHIM-09 must NOT. Read entire file.
- `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` — confirmed: uses `pytester.runpytest_subprocess()` per fixture pair; too slow for SHIM-09. Read entire file.
- `tests/framework/unit/test_error_style.py` lines 185–262 — confirmed: `--sdet` and `gen-sdet-classes` probed in-process via `typer.testing.CliRunner`. Read selected section.
- `.planning/phases/35-zero-shim-regression-gate-capstone/35-CONTEXT.md` — primary scope and constraint document. Read entire file.
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md` — confirmed Phase 31 fully deleted both config surfaces. Read entire file.
- `.planning/phases/32-surface-shim-removals-cli-package-fixtures-discovery/32-CONTEXT.md` — confirmed grandfathered intercept list and mechanisms. Read entire file.

---

## Metadata

**Confidence breakdown:**
- AST node shapes: HIGH — derived from reading the actual post-Phase-31 source, not from training knowledge
- In-process probe techniques: HIGH — directly verified from existing per-surface tests that use the same techniques
- Runtime <1s constraint: HIGH — all probes are in-process except the fixture surface, which uses an AST structural check (not pytester)
- Stale docstring target string: HIGH — read verbatim from `test_sdet_rename_leak_gate.py` line 4

**Research date:** 2026-05-27
**Valid until:** This research is derived from live source; valid until the source changes (i.e., as long as Phases 31/32 are not rolled back).
