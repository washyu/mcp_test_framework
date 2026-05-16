# Phase 26: Packaging foundation — Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 12 (5 modified, 7 created)
**Analogs found:** 11 / 12 (one — `test_wheel_shape.py` — has no exact prior wheel-introspection precedent; partial match below)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pyproject.toml` *(modified)* | config (build metadata) | declarative | `pyproject.toml` (lines 1–21, 41–60, 98–108 — own prior diffs) | exact (same file) |
| `src/mcp_test_framework/cli.py` *(modified, line 974 + module docstring lines 27, 30–33)* | CLI/controller | request-response | `src/mcp_test_framework/cli.py:970-977` (current `version` cmd) | exact (same file) |
| `tests/conftest.py` *(unchanged per D-12; documentation note only)* | test config | event-driven (pytest hooks) | n/a — keep as-is | n/a |
| `README.md` / `CLAUDE.md` / `docs/*` *(modified)* | docs | text | repo-wide grep for `mcp-test-framework` script tokens | role-match (text replace) |
| `src/mcp_test_framework/_plugin.py` *(NEW)* | pytest plugin module / fixtures | event-driven (hooks) + DI (fixtures) | `src/mcp_test_framework/fixtures.py` (whole file — fixture defs) + `tests/conftest.py:30-55` (pytest_configure shape) | exact-role |
| `src/mcp_test_framework/_deprecated_script.py` *(NEW)* | CLI shim / entry-point wrapper | request-response | `src/mcp_test_framework/cli.py:1095-1114` (`_gen_sdet_classes_shim`) + `src/mcp_test_framework/sdet/__init__.py` (top-level warn-and-reexport) | exact (Phase 25 D-04 mechanics) |
| `src/mcp_test_framework/contracts/__init__.py` *(NEW)* | package stub | n/a | `src/mcp_test_framework/__init__.py` (3-line file) | role-match (subpackage init) |
| `src/mcp_test_framework/contracts/py.typed` *(NEW)* | PEP 561 marker | n/a | None in repo today | no analog — empty file |
| `src/mcp_test_framework/py.typed` *(NEW)* | PEP 561 marker | n/a | None in repo today | no analog — empty file |
| `src/mcp_test_framework/test_code/py.typed` *(NEW)* | PEP 561 marker | n/a | None in repo today | no analog — empty file |
| `tests/framework/test_wheel_shape.py` *(NEW)* | test (wheel introspection) | file I/O + subprocess | `tests/framework/smoke/test_mcp_client_teardown_regression.py:69-117` (subprocess-driven framework gate) + `tests/framework/unit/test_gen_sdet_classes_cli.py:1-32` (CliRunner shape) | partial (no prior wheel test — closest is "outer subprocess test" pattern) |
| `tests/framework/test_cli_version.py` *(NEW — regression for line 974 fix)* | test (CLI smoke) | request-response | `tests/framework/unit/test_cli_errors.py:1-60` (CliRunner+app pattern) | exact-role |

---

## Pattern Assignments

### `pyproject.toml` (modified)

**Analog:** the file's own current state, plus its Phase 25 D-03 diff at lines 54–60.

**Current `[project]` + `[project.scripts]` block** (lines 1–21):
```toml
[project]
name = "mvp-test-framework"
version = "0.1.0"
description = "Pytest framework for testing MCP servers end-to-end."
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "mcp[cli]>=1.27",
    "pydantic>=2.13,<3",
    "pydantic-settings[yaml]>=2.14",
    "jsonschema>=4.26",
]

[project.scripts]
mcp-test-framework = "mcp_test_framework.cli:app"
```

**Change per D-01 (dist rename) + D-05/D-06 (script primary+shim) + D-09 (new entry-point group):**
```toml
[project]
name = "mcp-contracts"   # PACK-03 / D-01 — was "mvp-test-framework"
# (rest unchanged)

[project.scripts]
mcp-contracts = "mcp_test_framework.cli:app"          # D-05 primary
mcp-test-framework = "mcp_test_framework._deprecated_script:main"  # D-06 shim

[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"     # D-09 / PACK-01
```

**Hatch wheel config** (lines 98–108) — **unchanged**. Maintainer-confirmed (hatch discussion #554, cited in RESEARCH §Don't Hand-Roll): `packages = ["src/mcp_test_framework"]` auto-includes non-`.py` files including `py.typed` markers. No `force-include` / `artifacts` stanza needed.

**Filterwarnings precedent** (Phase 25 D-03, lines 54–60) — **unchanged**. Already catches every new shim added in Phase 26:
```toml
filterwarnings = [
    "always::DeprecationWarning:mcp_test_framework",
]
```

**Pyright include** (lines 83–95) — recommended to add `src/mcp_test_framework/_plugin.py` if planner adopts strict-typed hooks; not strictly required for PACK-02 (which is about the operator's pyright seeing typed signatures from the import surface, satisfied by py.typed alone).

---

### `src/mcp_test_framework/cli.py` (modified — dist-name lookup fix)

**Analog:** the current `version` command at lines 970–977 in the same file.

**Current code** (lines 970–977):
```python
@app.command()
def version() -> None:
    """Print the package version."""
    try:
        v = metadata.version("mvp-test-framework")  # distribution name, NOT importable package
    except metadata.PackageNotFoundError:
        from mcp_test_framework import __version__ as v
    typer.echo(v)
```

**Change per D-01:** replace the string `"mvp-test-framework"` with `"mcp-contracts"` on line 974. Update the trailing comment if planner wants.

**Module docstring at lines 27, 30–33** also references the old dist name:
```python
# line 27:
- `version` reads `importlib.metadata.version("mvp-test-framework")` and
# lines 30-33:
Distribution-name vs package-name discrepancy:
    pyproject.toml [project] name = "mvp-test-framework"   <-- metadata.version() arg
    importable package          = "mcp_test_framework"
    console-script name         = "mcp-test-framework"
```

Update to `mcp-contracts` everywhere except `console-script name` (D-06 — old script name remains in the shim layer; document both new + legacy script names here).

---

### `src/mcp_test_framework/_plugin.py` (NEW — pytest11 entry-point target)

**Analog:** `src/mcp_test_framework/fixtures.py` (the existing fixture module) for the fixture surface; `tests/conftest.py:30-55` for the `pytest_configure` shape; `src/mcp_test_framework/cli.py:372-385` (the `_warn_sdet_flag` callback) for the once-per-process deprecation pattern.

**Recommended approach (per D-11 + research §Architecture):** Option (b) "lower-churn" — `fixtures.py` stays as the implementation home; `_plugin.py` re-exports them under `mcp_*` names and adds the deprecation aliases as separate fixture defs. Re-export form is the same shape used in `src/mcp_test_framework/sdet/__init__.py` (the back-compat shim).

**Imports pattern** (copy structure from `fixtures.py:23-50`):
```python
"""mcp_test_framework pytest plugin — entry-point target.

Registered via [project.entry-points.pytest11] in pyproject.toml.
Phase 26 lands the skeleton: hook signatures are pre-declared with no-op
bodies; Phase 27 fills them with register()-driven behavior.
"""
from __future__ import annotations

import warnings

import pytest

# Re-export framework fixtures with the mcp_ prefix.
# Phase 26 D-11: fixtures move into this plugin module for auto-discovery
# via the entry point — operators no longer need `pytest_plugins=[...]`.
# Lower-churn option (D-11): keep implementations in fixtures.py and
# re-export here; v1.5 cleanup folds fixtures.py into this module.
from mcp_test_framework.fixtures import (
    mcp_client,        # noqa: F401 -- re-exported, already correctly prefixed
    _preflight,        # noqa: F401 -- re-exported (autouse, internal)
    _isolated_home,    # noqa: F401 -- re-exported (internal)
    tool_config,       # noqa: F401 -- re-exported, scope='function'
)
```

**Rename pattern (D-15..D-16):** import the existing fixture functions and re-publish under the prefixed name. For each of `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`, add:
```python
# Pattern: rebind the existing fixture under a new name.
# pytest discovers fixtures by their decorated function name, so a simple
# alias assignment is NOT enough — pytest will not see the rebinding as a
# fixture. The cleanest path is to define the new names in fixtures.py
# (canonical) and re-export here, OR define thin wrappers in _plugin.py
# that depend on the original fixture. Planner picks; the wrapper form is
# shown below because it makes the deprecation-alias pattern symmetric.

@pytest.fixture(scope="session")
def mcp_config(config):  # NEW prefixed name; receives existing fixture
    return config

# Deprecation alias — receives the prefixed fixture so the body is one warn().
@pytest.fixture(scope="session")
def config(mcp_config):  # legacy name kept for v1.4
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config
```

**ALTERNATIVE (planner-preferred per research):** Rename the source fixtures in `fixtures.py` to `mcp_*` directly (one git diff per fixture), and have the unprefixed alias be the wrapper. This avoids the wrapper-on-top-of-original anti-pattern. Each renamed fixture in `fixtures.py:89-101` (`config`), `fixtures.py:461-477` (`judge`), `fixtures.py:485-502` (`target_tool`), `fixtures.py:532-544` (three rubric fixtures) gets its `def NAME(...)` line edited to `def mcp_NAME(...)`. Then `_plugin.py` declares **six** deprecation-alias fixtures using the `def config(mcp_config): warn(...); return mcp_config` shape above.

**Deprecation-warning copy template** (Phase 25 D-05 — lifted verbatim from `src/mcp_test_framework/sdet/__init__.py:12-13` and `cli.py:380-381`):
```
"<old> is deprecated since v1.4 and will be removed in v1.5 — use <new> instead."
```
Apply per call site (D-07; **no central constant** per Phase 25 D-05).

**pytest_configure hook pattern** (Phase 27 will fill body; Phase 26 skeleton):
```python
def pytest_configure(config: pytest.Config) -> None:
    """Register the mcp_contract marker. Phase 27 adds register()-glue.

    Idempotent: pytest invokes pytest_configure once per session per
    loaded plugin. Adding inivalue_line is safe across reruns.
    """
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test (Phase 27).",
    )
```
This **coexists** with the existing `pytest_configure` in `tests/conftest.py:30-55` (the homelab_mcp sys.modules guard) — pytest invokes both, in plugin-load order. **Critical:** the plugin's `pytest_configure` MUST NOT remove or replace the existing guard (note in "Established Patterns" in CONTEXT.md).

**pytest_collection_modifyitems + pytest_addoption** (Phase 27 fills bodies; Phase 26 skeleton):
```python
def pytest_addoption(parser: pytest.Parser) -> None:
    """Reserve the --mcp-* option namespace. Phase 26: no options yet."""
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    # Phase 27 adds --mcp-server-command etc. here.

def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Reserve hook slot. Phase 27 injects contract tests here.

    Phase 26 body is intentionally empty — locks the hook surface so
    Phase 27 only adds business logic.
    """
    # No-op in Phase 26.
```

---

### `src/mcp_test_framework/_deprecated_script.py` (NEW — `mcp-test-framework` CLI shim)

**Analog:** `src/mcp_test_framework/cli.py:1095-1114` (`_gen_sdet_classes_shim`) — the Phase 25 D-04 precedent — plus `src/mcp_test_framework/sdet/__init__.py` for the top-level "import emits warning, then delegate" file shape.

**Phase 25 `_gen_sdet_classes_shim` pattern** (cli.py:1095-1114):
```python
@app.command("gen-sdet-classes", hidden=True)  # noqa: sdet-rename-shim
def _gen_sdet_classes_shim(  # noqa: sdet-rename-shim
    config: Path | None = typer.Option(  # noqa: sdet-rename-shim
        None,  # noqa: sdet-rename-shim
        "--config",  # noqa: sdet-rename-shim
        help=(...),  # noqa: sdet-rename-shim
    ),  # noqa: sdet-rename-shim
) -> None:  # noqa: sdet-rename-shim
    """Deprecated alias for `gen-test-classes` -- removed in v1.5."""  # noqa: sdet-rename-shim
    import warnings  # noqa: sdet-rename-shim
    warnings.warn(  # noqa: sdet-rename-shim
        "gen-sdet-classes is deprecated since v1.4 and will be removed in v1.5 — "  # noqa: sdet-rename-shim
        "use gen-test-classes instead.",  # noqa: sdet-rename-shim
        DeprecationWarning,  # noqa: sdet-rename-shim
        stacklevel=2,  # noqa: sdet-rename-shim
    )  # noqa: sdet-rename-shim
    gen_test_classes(config=config)  # noqa: sdet-rename-shim
```

**Phase 26 difference:** the script entry point is at the **console-script level** (`[project.scripts] mcp-test-framework = "mcp_test_framework._deprecated_script:main"`), not the Typer-subcommand level. The shim is one function in a tiny module:

```python
"""mcp-test-framework console-script deprecation shim.

The console-script `mcp-test-framework` is retained for v1.4 as a back-compat
entry point. It emits a DeprecationWarning once per process and then dispatches
to the same Typer app the new `mcp-contracts` script targets.

Removed in v1.5 (D-06 / Phase 26).
"""
from __future__ import annotations

import warnings


def main() -> None:
    warnings.warn(
        "mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5 — "
        "use mcp-contracts instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Import here (not at module top) so a `--help` short-circuit on the
    # primary `mcp-contracts` script doesn't pay this import cost.
    from mcp_test_framework.cli import app
    app()
```

**Deprecation copy** — literal D-07 template; ONE call site (no central constant) per Phase 25 D-05.

**Visibility note** (Phase 25 D-04 precedent verified in Phase 25 UAT — see memory `project_deprecation_warning_visibility`): Python's default filter shows DeprecationWarning from `__main__` on stderr, so the shim works without `simplefilter('always')`. **But** the warning currently renders as plain gray text and is easy to lose against `--help` output — planner may want to consider a `formatwarning` override if Phase 26 should ship a presentation fix at the same time. CONTEXT.md does not require it; flagged for planner discretion.

---

### `src/mcp_test_framework/contracts/__init__.py` (NEW — stub)

**Analog:** `src/mcp_test_framework/__init__.py` (3-line file).

**Current `__init__.py`** (whole file):
```python
"""mcp_test_framework -- pytest framework for testing MCP servers end-to-end."""

__version__ = "0.1.0"
```

**New `contracts/__init__.py`** (one-line docstring per D-13):
```python
"""mcp_test_framework.contracts — Phase 27 lands register() here.

Phase 26 ships this as an empty subpackage stub so PEP 561-driven type
resolution finds `mcp_test_framework.contracts` from an installed wheel
without "missing stubs" complaints.
"""
```

No `__version__`, no exports — Phase 27 owns the `register()` body (D-14).

---

### `py.typed` markers (NEW × 3)

**Analog:** None in repo today.

**Content:** **Empty file** per PEP 561 §"Packaging Type Information". The file's presence is the signal; contents are ignored by type checkers.

**Locations** (per D-13 + research §Architecture Pattern 2):
- `src/mcp_test_framework/py.typed`
- `src/mcp_test_framework/test_code/py.typed`
- `src/mcp_test_framework/contracts/py.typed`

**Hatch behavior** — auto-included via `packages = ["src/mcp_test_framework"]`. The wheel-introspection test (next) verifies.

---

### `tests/framework/test_wheel_shape.py` (NEW — PACK-04 gate)

**Analog (partial):** `tests/framework/smoke/test_mcp_client_teardown_regression.py:69-117` is the closest "framework subprocess-driven gate" pattern in the repo. No prior wheel-introspection test exists; research recommends stdlib `zipfile` + `subprocess.run(["uv", "build", "--wheel", ...])`.

**Imports pattern** (lift from `test_mcp_client_teardown_regression.py:33-46`):
```python
"""PACK-04: wheel-content regression gate.

Builds the project wheel into a tmp dir via `uv build --wheel`, then walks
the resulting .whl (which is a zip) to assert:
  - mcp_test_framework/py.typed present
  - mcp_test_framework/test_code/py.typed present
  - mcp_test_framework/contracts/__init__.py present
  - mcp_test_framework/contracts/py.typed present
  - No tests/ directory leaked into the wheel
  - dist-info entry_points.txt lists pytest11 = mcp_test_framework._plugin
  - dist-info entry_points.txt lists mcp-contracts AND mcp-test-framework
    console scripts
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
```

**Skip-cleanly pattern** (lift from `test_mcp_client_teardown_regression.py:84-94`):
```python
@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("uv") is None:
        pytest.skip("uv not on PATH; cannot build wheel for introspection")
    out_dir = tmp_path_factory.mktemp("wheel_build")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"uv build failed: {result.stderr}")
    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return wheels[0]
```

**Assertion pattern** (per CONTEXT.md "Wheel-introspection venue" + research §Code Examples):
```python
def _wheel_names(wheel_path: Path) -> set[str]:
    with zipfile.ZipFile(wheel_path) as zf:
        return set(zf.namelist())


def test_wheel_ships_root_py_typed(built_wheel: Path) -> None:
    assert "mcp_test_framework/py.typed" in _wheel_names(built_wheel)


def test_wheel_ships_test_code_py_typed(built_wheel: Path) -> None:
    assert "mcp_test_framework/test_code/py.typed" in _wheel_names(built_wheel)


def test_wheel_ships_contracts_subpackage(built_wheel: Path) -> None:
    names = _wheel_names(built_wheel)
    assert "mcp_test_framework/contracts/__init__.py" in names
    assert "mcp_test_framework/contracts/py.typed" in names


def test_wheel_excludes_tests_directory(built_wheel: Path) -> None:
    names = _wheel_names(built_wheel)
    leaks = [n for n in names if n.startswith("tests/")]
    assert leaks == [], f"tests/ leaked into wheel: {leaks}"


def test_wheel_declares_pytest11_entry_point(built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as zf:
        # dist-info dirname is "{normalized-name}-{version}.dist-info"
        dist_info = next(
            n for n in zf.namelist()
            if n.endswith(".dist-info/entry_points.txt")
        )
        ep_txt = zf.read(dist_info).decode("utf-8")
    assert "[pytest11]" in ep_txt
    assert "mcp_test_framework = mcp_test_framework._plugin" in ep_txt


def test_wheel_declares_both_console_scripts(built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as zf:
        dist_info = next(
            n for n in zf.namelist()
            if n.endswith(".dist-info/entry_points.txt")
        )
        ep_txt = zf.read(dist_info).decode("utf-8")
    assert "mcp-contracts = mcp_test_framework.cli:app" in ep_txt
    assert "mcp-test-framework = mcp_test_framework._deprecated_script:main" in ep_txt
```

**Performance note** — `uv build` cold takes 3–8s; cache the wheel at module scope (`tmp_path_factory.mktemp` + `scope="module"` on the fixture) so the build runs once for all assertions.

---

### `tests/framework/test_cli_version.py` (NEW — regression for the `metadata.version("mvp-test-framework")` → `"mcp-contracts"` fix)

**Analog:** `tests/framework/unit/test_cli_errors.py:1-60` — canonical CliRunner+app shape used across `tests/framework/unit/`.

**Imports + invocation pattern** (lift verbatim from `test_cli_errors.py:10-22, 31-32`):
```python
"""Regression test: `mcp-contracts version` resolves the dist name.

Pins D-01 + the cli.py:974 fix — before Phase 26, the lookup string was
`metadata.version("mvp-test-framework")` which would raise
PackageNotFoundError post-rename, silently falling back to the hard-coded
`__version__` constant. This test runs the version command via CliRunner
and asserts the dist-metadata path resolves (exit 0 + non-empty output).
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))


def test_version_command_resolves_dist_name() -> None:
    result = _invoke("version")
    assert result.exit_code == 0
    # Non-empty version string; either dist metadata or __version__ fallback.
    assert result.stdout.strip() != ""


def test_version_command_uses_new_dist_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """If `mcp-contracts` is installed, metadata.version() returns its version;
    if not (wheel not installed in test env), fallback to __version__ fires.
    Either path is acceptable; the regression is that `mvp-test-framework`
    no longer appears in source.
    """
    import mcp_test_framework.cli as cli_mod
    # Read the source to ensure the dist-name argument has been renamed.
    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    assert 'metadata.version("mvp-test-framework")' not in src
    assert 'metadata.version("mcp-contracts")' in src
```

(Planner may simplify — the source-string assertion is a defensive belt-and-suspenders that complements the wheel-shape test's `entry_points.txt` check.)

---

### Docs updates (README.md / CLAUDE.md / docs/*) — D-08

**Analog:** grep-and-replace exercise; no behavioral analog needed.

**Search pattern:**
```
mcp-test-framework (followed by space, command name, --help, run, list-tools, gen-test-classes, version, config-init)
```

**Replace logic:**
- Operator-facing prose: `mcp-test-framework` → `mcp-contracts`.
- Deprecation note: add a one-paragraph "Legacy script alias" block somewhere in the operator section noting `mcp-test-framework` still works in v1.4 but emits a DeprecationWarning and is removed in v1.5 (D-07 wording template).
- Distribution-name references (e.g., `pip install mcp-test-framework` or `uv add mvp-test-framework`): replace with `mcp-contracts`.

Verify post-edit with `Grep("mcp-test-framework|mvp-test-framework", ...)` — only matches should be (a) the deprecation note, (b) the `_deprecated_script.py` source, (c) `pyproject.toml [project.scripts]` legacy entry, (d) the deprecation-warning string in `cli.py` if any, (e) the wheel-shape test assertion that checks the legacy console script is still declared.

---

## Shared Patterns

### Deprecation warning (Phase 25 D-01..D-05 — lifted wholesale per CONTEXT.md "Established Patterns")

**Source:** `src/mcp_test_framework/sdet/__init__.py:11-16` (package-import variant); `src/mcp_test_framework/cli.py:1107-1113` (Typer-command variant); `src/mcp_test_framework/cli.py:372-385` (eager-callback variant, used for the `--sdet` flag).

**Apply to:**
- `_deprecated_script.py:main` — package-import variant adapted to a function.
- `_plugin.py` — six fixture aliases (`config`, `judge`, `target_tool`, three rubric names). Each is a separate `@pytest.fixture` def that receives the prefixed fixture and calls `warnings.warn` once.

**Canonical shape:**
```python
import warnings
warnings.warn(
    "<old> is deprecated since v1.4 and will be removed in v1.5 — use <new> instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Why these defaults** (Phase 25 D-01..D-05):
- `DeprecationWarning` (not `FutureWarning`, not custom subclass) so operators can filter with the stdlib idiom.
- `stacklevel=2` so the warning is attributed to the operator's call site, not the framework's `warn()` line.
- Default Python filter dedups once-per-process; **do not** `simplefilter('always')`.
- Hardcoded literal copy per call site; **no central constant** — keeps each site greppable by `noqa: sdet-rename-shim`-style markers if the planner wants a Phase-26 equivalent (e.g., `noqa: mcp-prefix-shim`).

### Filterwarnings safety net (pyproject.toml, Phase 25 D-03)

**Source:** `pyproject.toml:54-60`.

**Apply to:** Already applies to all Phase 26 shims because the filter scopes on module-prefix `mcp_test_framework`. **No pyproject change needed** for the warning-filter line.

```toml
filterwarnings = [
    "always::DeprecationWarning:mcp_test_framework",
]
```

### Hatch wheel packaging (Phase 01-01, maintainer-confirmed)

**Source:** `pyproject.toml:106-108`.

**Apply to:** All `py.typed` markers + the new `contracts/` subpackage are auto-included. No new `[tool.hatch.build.targets.wheel]` keys.

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mcp_test_framework"]
```

### pytest_configure coexistence (tests/conftest.py)

**Source:** `tests/conftest.py:30-55`.

**Apply to:** `_plugin.py:pytest_configure`. Pytest invokes both — the plugin's hook MUST be additive only. The black-box `sys.modules` guard in conftest.py is load-bearing (memory `project_v1_3_close_push_and_scrub` neighbourhood); the plugin must not move it.

### CliRunner test shape (tests/framework/unit/)

**Source:** `tests/framework/unit/test_cli_errors.py:10-22, 31-32`.

**Apply to:** `tests/framework/test_cli_version.py` and any future Phase 26 CLI regression.

```python
from typer.testing import CliRunner
from mcp_test_framework.cli import app

def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))
```

### Subprocess-gated framework test (skip-cleanly when tool missing)

**Source:** `tests/framework/smoke/test_mcp_client_teardown_regression.py:69-117`.

**Apply to:** `tests/framework/test_wheel_shape.py` (skip if `uv` not on PATH; fail loud only if `uv build` itself fails).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/mcp_test_framework/py.typed` | PEP 561 marker | n/a | Empty file; no behavioral analog needed (PEP 561 §"Packaging Type Information") |
| `src/mcp_test_framework/test_code/py.typed` | PEP 561 marker | n/a | Same |
| `src/mcp_test_framework/contracts/py.typed` | PEP 561 marker | n/a | Same |
| `tests/framework/test_wheel_shape.py` | wheel-introspection gate | file I/O + subprocess | No prior wheel test exists in the repo; closest pattern is the subprocess-gated framework test cited above. Use RESEARCH.md §Code Examples (`zipfile.ZipFile(wheel).namelist()` walker) as primary; the subprocess-skip-cleanly shape is borrowed from the cited regression test |

---

## Metadata

**Analog search scope:** `src/mcp_test_framework/**/*.py`, `tests/framework/**/*.py`, `tests/conftest.py`, `pyproject.toml`, `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-01-PLAN.md`, `25-02-PLAN.md`.
**Files scanned:** ~30 Python sources + 6 planning artifacts.
**Pattern extraction date:** 2026-05-15.
**Key analog files (memorize these paths for the planner):**
- `src/mcp_test_framework/fixtures.py` (existing fixture module — D-11 lower-churn option means this file gets renames + stays as the implementation home)
- `src/mcp_test_framework/cli.py:372-385` (eager-callback once-per-process deprecation pattern — Phase 25 D-04)
- `src/mcp_test_framework/cli.py:1095-1114` (Typer-subcommand shim — Phase 25 D-04)
- `src/mcp_test_framework/sdet/__init__.py` (package-level warn-and-reexport — the closest shape to `_deprecated_script.py`)
- `pyproject.toml:1-21, 54-60, 98-108` (current packaging stanzas + Phase 25 D-03 filterwarnings)
- `tests/framework/smoke/test_mcp_client_teardown_regression.py:33-117` (subprocess-gated framework test shape — only one for `test_wheel_shape.py`)
- `tests/framework/unit/test_cli_errors.py:1-60` (canonical CliRunner+app test shape)
- `tests/conftest.py:30-55` (existing pytest_configure — plugin must coexist, not replace)
