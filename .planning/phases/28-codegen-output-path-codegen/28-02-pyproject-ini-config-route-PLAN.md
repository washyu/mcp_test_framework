---
phase: 28-codegen-output-path-codegen
plan: 02
type: execute
wave: 2
depends_on: [28-01]
files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_gen_test_classes_pyproject_config.py
autonomous: true
requirements:
  - CODEGEN-LIB-01
must_haves:
  truths:
    - "Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in their `pyproject.toml` sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`."
    - "Operator passing `--config PATH` still wins over any pyproject.toml setting (D-11 precedence preserved)."
    - "Operator with `MCPTF_CONFIG_FILE` set in their environment continues to see the existing Phase 27 D-09 DeprecationWarning AND the env var still functions (no Phase 28 changes to env-var path; D-12)."
    - "Operator with no pyproject.toml, a malformed pyproject.toml, or a pyproject.toml lacking `[tool.pytest.ini_options]` falls through silently to `./config.yaml` autodiscovery (D-13 fail-soft)."
    - "Relative `mcp_config_file` paths in pyproject.toml resolve against pyproject.toml's directory (matches Phase 27 `_plugin.py` line 165-166 convention)."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "`_read_mcp_config_file_from_pyproject(cwd)` helper + extension of `_load_config` precedence chain to insert pyproject.toml branch between `--config` and `MCPTF_CONFIG_FILE`."
      contains: "def _read_mcp_config_file_from_pyproject("
    - path: "tests/framework/unit/test_gen_test_classes_pyproject_config.py"
      provides: "Unit tests covering: (a) pyproject.toml ini value loaded when no --config and no MCPTF_CONFIG_FILE; (b) --config overrides pyproject value; (c) missing pyproject silently falls through; (d) malformed pyproject silently falls through; (e) pyproject without [tool.pytest.ini_options] silently falls through; (f) relative path resolves against pyproject directory."
      contains: "def test_gen_test_classes_uses_pyproject_ini_when_no_config_flag"
  key_links:
    - from: "src/mcp_test_framework/cli.py::_load_config"
      to: "src/mcp_test_framework/cli.py::_read_mcp_config_file_from_pyproject"
      via: "called from inside `_load_config` between the `--config` branch and the `MCPTF_CONFIG_FILE` branch"
      pattern: "_read_mcp_config_file_from_pyproject\\("
    - from: "src/mcp_test_framework/cli.py::_load_config"
      to: "stdlib `tomllib`"
      via: "lazy import inside `_read_mcp_config_file_from_pyproject`"
      pattern: "import tomllib"
---

<objective>
Extend the Typer CLI's config-resolution chain to read `[tool.pytest.ini_options] mcp_config_file` from pyproject.toml. This closes the seam between the Typer CLI's config lookup and the pytest plugin's ini route that Phase 27 made canonical — `gen-test-classes` and `pytest` now find the operator's config via the same ini key.

Purpose: D-11 single-config-route extension. Operator who has onboarded library mode (i.e. set `mcp_config_file` in pyproject.toml) gets `mcp-contracts gen-test-classes` working with zero additional flags. Fail-soft per D-13: any pyproject parsing problem silently falls through to today's `./config.yaml` autodiscovery.

Output: new `_read_mcp_config_file_from_pyproject(cwd)` helper using stdlib `tomllib`; extension of `_load_config` precedence chain; six unit tests covering precedence, fall-through, and relative-path resolution.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md
@.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/_plugin.py
@pyproject.toml

<interfaces>
<!-- Phase 27 _plugin.py canonical resolution pattern that this plan mirrors. -->

From src/mcp_test_framework/_plugin.py (lines 158-167) — the pytest-side resolution this plan mirrors:
```python
# Read ini; empty string = operator opted out, silent no-op.
raw = (config.getini("mcp_config_file") or "").strip()
if not raw:
    return

# Resolve relative to pyproject.toml's directory.
path = Path(raw)
if not path.is_absolute():
    path = config.rootpath / path
```

This pattern is what the CLI side replicates against pyproject.toml directly via stdlib `tomllib`. Critical:
- relative paths resolve against the pyproject.toml directory (NOT cwd)
- empty-string value means "operator opted out" — fall through silently
- absent ini key behaves identically to empty string

From src/mcp_test_framework/cli.py (lines 206-317) — existing `_load_config` body. The four-branch precedence today:
```
Branch 1: --config PATH (path-not-found is fail-loud)
Branch 2: MCPTF_CONFIG_FILE env var (path-not-found is fail-loud; emits Phase 27 D-09 DeprecationWarning at plugin level)
Branch 3: ./config.yaml autodiscovery
Branch 4: nothing found -> fail-loud (no config) OR (None, None) if allow_missing=True
```

Phase 28 inserts a NEW branch between current Branch 1 and Branch 2:
```
Branch 1: --config PATH                                            (unchanged)
Branch 1.5 (NEW): pyproject.toml [tool.pytest.ini_options] mcp_config_file  (per D-11)
Branch 2: MCPTF_CONFIG_FILE env var                                (unchanged; D-12)
Branch 3: ./config.yaml autodiscovery                              (unchanged)
Branch 4: nothing found                                            (unchanged)
```

Fail-soft contract for the new branch (per D-13):
- pyproject.toml missing in cwd: silent fall-through (no warning, no error)
- pyproject.toml present but tomllib raises any exception: silent fall-through
- pyproject.toml parses but lacks `[tool.pytest.ini_options]` table: silent fall-through
- `[tool.pytest.ini_options]` exists but lacks `mcp_config_file` key OR value is empty string: silent fall-through
- `mcp_config_file` is set BUT the resolved path does not exist: this DIFFERS from the `--config` and env-var paths. Per D-11 + D-13, treat this as fail-loud (typo'd ini value should not silently fall through to other branches; that would mask the bug). Use operator-tone error with `next:` pointing at the operator's pyproject.toml.

stdlib `tomllib` reference (Python 3.11+, available in 3.14):
```python
import tomllib  # binary-mode open required
with open(path, "rb") as f:
    data = tomllib.load(f)
# Walks .get("tool", {}).get("pytest", {}).get("ini_options", {}).get("mcp_config_file")
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add pyproject.toml ini reader helper and integrate into _load_config precedence chain with unit tests</name>
  <files>src/mcp_test_framework/cli.py, tests/framework/unit/test_gen_test_classes_pyproject_config.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py lines 206-318 (`_load_config` full body) — current four-branch precedence chain to extend
    - src/mcp_test_framework/_plugin.py lines 127-200 (`pytest_configure` body) — Phase 27 canonical resolution pattern to mirror (especially lines 158-167 relative-path resolution against `config.rootpath`)
    - src/mcp_test_framework/_plugin.py lines 206-225 (`pytest_addoption`) — confirms the ini key name `"mcp_config_file"` and default `""`
    - .planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md sections `<decisions>` D-11 / D-12 / D-13 and `<canonical_refs>` "Phase 27 carry-forward"
    - docs/ERROR-STYLE.md — for the fail-loud typo'd-ini-value error message tone
    - tests/framework/unit/test_gen_sdet_classes_cli.py — CliRunner test pattern for end-to-end CLI tests; pay attention to the `_write_config` helper shape
    - pyproject.toml — confirm framework's own dogfood line `mcp_config_file = "./config.test.yaml"` exists under `[tool.pytest.ini_options]`
  </read_first>
  <behavior>
    - Test 1 (uses-pyproject): operator with pyproject.toml containing `[tool.pytest.ini_options] mcp_config_file = "./inner.yaml"` and NO `--config` flag and NO `MCPTF_CONFIG_FILE` env var sees `_load_config(path=None)` return `(Config(...), Path/to/inner.yaml resolved against pyproject directory)`.
    - Test 2 (config-flag-overrides): operator with both `--config explicit.yaml` AND pyproject.toml `mcp_config_file = "./inner.yaml"` sees `_load_config(path=Path("explicit.yaml"))` use `explicit.yaml`. The pyproject value is NOT consulted.
    - Test 3 (env-still-works): operator with `MCPTF_CONFIG_FILE=env.yaml` and NO pyproject.toml mcp_config_file sees the env var consulted (existing Phase 27 D-09 DeprecationWarning continues to fire at plugin level; Phase 28 makes no env-var changes per D-12).
    - Test 4 (missing-pyproject-falls-through): operator with NO pyproject.toml in cwd (tmp_path with no pyproject) and a `./config.yaml` falls through to `./config.yaml` autodiscovery silently.
    - Test 5 (malformed-pyproject-falls-through): operator with a pyproject.toml that contains invalid TOML (e.g. `[broken`) falls through to `./config.yaml` autodiscovery silently. No exception leaks. No warning emitted.
    - Test 6 (no-ini-options-section-falls-through): operator with valid pyproject.toml that has no `[tool.pytest.ini_options]` section (or has the section but no `mcp_config_file` key, or has empty-string value) falls through to `./config.yaml` autodiscovery silently.
    - Test 7 (relative-path-resolution): operator with `mcp_config_file = "configs/inner.yaml"` and pyproject.toml at `tmp_path/pyproject.toml` sees the resolved path equal `tmp_path / "configs" / "inner.yaml"` (NOT cwd-relative). Matches Phase 27 `_plugin.py:165-166`.
    - Test 8 (fail-loud-on-typo): operator with `mcp_config_file = "./does-not-exist.yaml"` in pyproject.toml sees `_load_config` raise `typer.Exit(code=2)` with operator-tone error mentioning the pyproject.toml path and the missing config path (D-13 fail-loud on resolved-but-missing).
  </behavior>
  <action>
    Step 1 — Add `_read_mcp_config_file_from_pyproject` helper to `src/mcp_test_framework/cli.py`. Insert after `_emit_operator_error_for_validation` (around line 203) and BEFORE `_load_config` (line 206):

```python
def _read_mcp_config_file_from_pyproject(cwd: Path) -> tuple[Path | None, Path | None]:
    """Read `[tool.pytest.ini_options] mcp_config_file` from pyproject.toml.

    Mirrors `_plugin.py::pytest_configure` ini-resolution behavior (Phase 27
    D-06 / D-11) on the Typer CLI side so `gen-test-classes` and `pytest`
    locate the operator's config through the same single source of truth.

    Fail-soft per D-13: missing pyproject.toml, malformed TOML, absent
    `[tool.pytest.ini_options]` section, absent `mcp_config_file` key, or
    empty-string value all return `(None, None)` so the caller falls
    through to the next branch in the precedence chain.

    Returns:
        Two-tuple `(resolved_config_path, pyproject_path)`:
          - When the ini value is set and the resolved path exists:
            `(Path-to-config, Path-to-pyproject.toml)`. Relative paths in
            the ini value are resolved against the pyproject.toml's
            directory (matches `_plugin.py:165-166`).
          - When the ini value is set but the resolved path does NOT
            exist: this function calls `_emit_operator_error` and never
            returns (fail-loud on typo, do NOT mask by falling through).
          - All other fail-soft cases: `(None, None)`.
    """
    import tomllib
    pyproject = cwd / "pyproject.toml"
    if not pyproject.is_file():
        return (None, None)
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
    except Exception:  # noqa: BLE001 -- D-13 silent fall-through on any TOML parse error
        return (None, None)
    raw = (
        data.get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
        .get("mcp_config_file", "")
    )
    raw = (raw or "").strip() if isinstance(raw, str) else ""
    if not raw:
        return (None, None)
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = pyproject.parent / candidate
    if not candidate.is_file():
        _emit_operator_error(
            summary=f"config file not found via pyproject.toml: {candidate}",
            detail=[
                f"`[tool.pytest.ini_options] mcp_config_file` in {pyproject} "
                f"points at `{raw}`, which resolves to `{candidate}`.",
                "that path does not exist or is not a file.",
            ],
            next_step=(
                "fix the `mcp_config_file` value in your pyproject.toml or "
                "run `mcp-contracts config-init -o config.yaml` to generate "
                "a starter config"
            ),
        )
    return (candidate, pyproject)
```

Step 2 — Insert the new branch into `_load_config` in `src/mcp_test_framework/cli.py`. Find the existing block (around lines 247-286):

Current structure:
```python
    # Branch 1: --config wins.
    if path is not None:
        ...
    else:
        # Branch 2: MCPTF_CONFIG_FILE.
        env_path_str = os.environ.get("MCPTF_CONFIG_FILE")
        if env_path_str:
            ...
        else:
            # Branch 3: ./config.yaml autodiscovery.
            ...
```

Replace the `else:` arm of `if path is not None:` so the new pyproject branch sits BEFORE the env var branch:

```python
    # Branch 1: --config wins.
    if path is not None:
        if not path.is_file():
            _emit_operator_error(
                summary=f"config file not found: {path}",
                detail=[
                    "the path passed to --config does not exist or is not a file.",
                ],
                next_step=(
                    "check the path or run "
                    "`mcp-test-framework config-init -o config.yaml` "
                    "to generate a starter config"
                ),
            )
        resolved = path
        source_label = str(path)
    else:
        # Branch 1.5 (Phase 28 D-11): pyproject.toml [tool.pytest.ini_options] mcp_config_file.
        # Mirrors _plugin.py:pytest_configure ini-resolution; closes the seam
        # between the Typer CLI and the pytest plugin so both routes find
        # the operator's config via the same ini key.
        pyproject_path, pyproject_source = _read_mcp_config_file_from_pyproject(Path.cwd())
        if pyproject_path is not None:
            resolved = pyproject_path
            source_label = str(pyproject_path)
        else:
            # Branch 2: MCPTF_CONFIG_FILE.
            env_path_str = os.environ.get("MCPTF_CONFIG_FILE")
            if env_path_str:
                env_path = Path(env_path_str)
                if not env_path.is_file():
                    _emit_operator_error(
                        summary=f"config file not found via MCPTF_CONFIG_FILE: {env_path}",
                        detail=[
                            "the path in MCPTF_CONFIG_FILE does not exist or is not a file.",
                        ],
                        next_step=(
                            "check the path or unset MCPTF_CONFIG_FILE and run "
                            "`mcp-test-framework config-init -o config.yaml` "
                            "to generate a starter config"
                        ),
                    )
                resolved = env_path
                source_label = str(env_path)
            else:
                # Branch 3: ./config.yaml autodiscovery.
                cwd_config = Path.cwd() / "config.yaml"
                if cwd_config.is_file():
                    resolved = cwd_config
                    source_label = str(cwd_config)
```

Update the `_load_config` docstring (lines 209-242) to add Branch 1.5 to the precedence list:

```
    Precedence:
        --config PATH > [tool.pytest.ini_options] mcp_config_file (pyproject.toml)
        > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud.
```

Step 3 — Create `tests/framework/unit/test_gen_test_classes_pyproject_config.py`. Use a `monkeypatch.chdir(tmp_path)` pattern to control cwd per test; mock `MCPTF_CONFIG_FILE` env var via `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)`:

```python
"""Unit tests for the Phase 28 D-11 pyproject.toml mcp_config_file route in _load_config."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import typer
import yaml

from mcp_test_framework.cli import (
    _load_config,
    _read_mcp_config_file_from_pyproject,
)


def _write_minimal_config_yaml(path: Path) -> None:
    path.write_text(
        yaml.safe_dump({
            "version": 2,
            "mcp_server": {"command": "echo", "args": []},
            "test_code": {"generated_root": str(path.parent / "_generated")},
            "tools": {},
        }),
        encoding="utf-8",
    )


def _write_pyproject_with_mcp_config_file(
    tmp_path: Path, mcp_config_file_value: str | None
) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    if mcp_config_file_value is None:
        pyproject.write_text("[project]\nname = \"x\"\nversion = \"0.0\"\n", encoding="utf-8")
    else:
        pyproject.write_text(
            textwrap.dedent(f"""\
                [project]
                name = "x"
                version = "0.0"

                [tool.pytest.ini_options]
                mcp_config_file = "{mcp_config_file_value}"
            """),
            encoding="utf-8",
        )
    return pyproject


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)


def test_gen_test_classes_uses_pyproject_ini_when_no_config_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inner = tmp_path / "inner.yaml"
    _write_minimal_config_yaml(inner)
    _write_pyproject_with_mcp_config_file(tmp_path, "./inner.yaml")
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == inner


def test_config_flag_overrides_pyproject_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pyproject_inner = tmp_path / "from-pyproject.yaml"
    _write_minimal_config_yaml(pyproject_inner)
    flag_explicit = tmp_path / "from-flag.yaml"
    _write_minimal_config_yaml(flag_explicit)
    _write_pyproject_with_mcp_config_file(tmp_path, "./from-pyproject.yaml")
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=flag_explicit)
    assert cfg is not None
    assert resolved == flag_explicit


def test_env_var_still_works_when_no_pyproject_ini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_path = tmp_path / "env.yaml"
    _write_minimal_config_yaml(env_path)
    # pyproject.toml exists but has no [tool.pytest.ini_options]
    _write_pyproject_with_mcp_config_file(tmp_path, None)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(env_path))
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == env_path


def test_missing_pyproject_falls_through_to_cwd_autodiscovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    # No pyproject.toml at all
    assert not (tmp_path / "pyproject.toml").exists()
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_malformed_pyproject_falls_through_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("[broken\nthis is not valid toml", encoding="utf-8")
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_pyproject_without_ini_options_section_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, None)
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_pyproject_empty_string_value_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, "")
    cwd_yaml = tmp_path / "config.yaml"
    _write_minimal_config_yaml(cwd_yaml)
    monkeypatch.chdir(tmp_path)
    cfg, resolved = _load_config(path=None)
    assert cfg is not None
    assert resolved == cwd_yaml


def test_relative_path_resolves_against_pyproject_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    inner = sub / "inner.yaml"
    _write_minimal_config_yaml(inner)
    _write_pyproject_with_mcp_config_file(tmp_path, "./subdir/inner.yaml")
    # Run from a DIFFERENT directory to prove resolution is pyproject-relative
    # and NOT cwd-relative.
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    # When cwd is `other`, the pyproject discovery uses cwd / pyproject.toml,
    # which does NOT exist under `other` — so this test actually verifies
    # the helper-direct path. Direct helper call:
    resolved_path, pyproject_path = _read_mcp_config_file_from_pyproject(tmp_path)
    assert resolved_path == inner
    assert pyproject_path == tmp_path / "pyproject.toml"


def test_pyproject_typo_value_raises_fail_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pyproject_with_mcp_config_file(tmp_path, "./does-not-exist.yaml")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        _load_config(path=None)
    assert exc_info.value.exit_code == 2
```

Step 4 — Run the tests to confirm GREEN:

```
uv run pytest tests/framework/unit/test_gen_test_classes_pyproject_config.py -x -v
```

Step 5 — Run the full framework test suite to verify no regression to existing behavior (especially `tests/framework/unit/test_cli_errors.py` and `tests/framework/test_config_init_cli.py` which exercise `_load_config`):

```
uv run pytest tests/framework/ -x
```

If any existing test fails, the regression is in `_load_config` precedence — preserve EVERY existing branch and only insert the new pyproject branch in the position specified.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_gen_test_classes_pyproject_config.py tests/framework/unit/test_cli_errors.py tests/framework/test_config_init_cli.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - src/mcp_test_framework/cli.py contains the literal string `def _read_mcp_config_file_from_pyproject(`
    - src/mcp_test_framework/cli.py contains the literal string `import tomllib` (inside the helper body — lazy import per cli.py convention)
    - src/mcp_test_framework/cli.py contains the literal string `_read_mcp_config_file_from_pyproject(Path.cwd())` inside `_load_config` body
    - The pyproject branch sits BETWEEN the `--config` branch and the `MCPTF_CONFIG_FILE` branch (verify by reading lines around `_load_config`)
    - The docstring for `_load_config` mentions pyproject.toml in the precedence ladder
    - tests/framework/unit/test_gen_test_classes_pyproject_config.py exists with at least nine `def test_` functions covering the eight behaviors above
    - `uv run pytest tests/framework/unit/test_gen_test_classes_pyproject_config.py -x -v` exits 0
    - `uv run pytest tests/framework/unit/test_cli_errors.py tests/framework/test_config_init_cli.py -x` exits 0 (no regression to existing _load_config callers)
    - `uv run pytest tests/framework/ -x` exits 0 (full framework suite green)
  </acceptance_criteria>
  <done>
    - Helper defined, integrated into `_load_config` precedence chain in position 1.5, eight behavior tests pass, no regression in existing framework suite.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/framework/unit/test_gen_test_classes_pyproject_config.py -x -v` exits 0
- `uv run pytest tests/framework/ -x` exits 0
- Grep confirms `import tomllib` appears in cli.py
- Grep confirms `_read_mcp_config_file_from_pyproject` is called from `_load_config` exactly once
- The new branch order in `_load_config` is `--config > pyproject > MCPTF_CONFIG_FILE > ./config.yaml > fail-loud` (per D-11)
- Framework's own dogfood line `mcp_config_file = "./config.test.yaml"` in pyproject.toml is unchanged
</verification>

<success_criteria>
`gen-test-classes` now finds the operator's config via `[tool.pytest.ini_options] mcp_config_file` in pyproject.toml — closing the seam between the Typer CLI and the pytest plugin. `--config` still wins; env var still works (D-12); fail-soft on any pyproject parsing problem (D-13); fail-loud on typo'd value. CODEGEN-LIB-01 (config-seam portion) satisfied.
</success_criteria>

<output>
After completion, create `.planning/phases/28-codegen-output-path-codegen/28-02-SUMMARY.md` documenting:
- The helper signature and fail-soft contract
- The precedence chain position (between --config and MCPTF_CONFIG_FILE)
- The relative-path resolution semantics (pyproject-relative, matching Phase 27 _plugin.py:165-166)
- The fail-loud-on-typo decision (D-13 interpretation: silent on parse problems, loud on resolved-but-missing)
</output>
