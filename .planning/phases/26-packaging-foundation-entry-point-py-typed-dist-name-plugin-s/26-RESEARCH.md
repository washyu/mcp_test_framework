# Phase 26: Packaging foundation — entry-point + py.typed + dist-name + plugin skeleton - Research

**Researched:** 2026-05-15
**Domain:** Python packaging (hatchling wheels), pytest plugin entry points (`pytest11`), PEP 561 typed-package markers, deprecation-shim CLI scripts, TestPyPI dry-run publish
**Confidence:** HIGH on packaging mechanics and pytest entry-point pattern; HIGH on hatchling file-inclusion behavior (maintainer-quoted answer); MEDIUM on wheel-introspection test shape (idiomatic but project-specific choice).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dist-name rename + back-compat (PACK-03)**

- **D-01:** Dist name: `mvp-test-framework` → `mcp-contracts`. Verified available on PyPI 2026-05-15.
- **D-02:** No PyPI shim under the old `mvp-test-framework` name needed — the project has never been published, so there is no prior installation to migrate. PACK-03's "one-milestone shim under the old name" clause is closed-by-non-applicability.
- **D-03:** The originally-targeted name `mcp-test-framework` is taken by an unrelated project (`aryanjp1/pytest-mcp`, v0.1.1, 2026-02-07). ROADMAP.md Phase 26 line and PACK-03 requirement text both reference the wrong name and should be amended during planning to read `mcp-contracts`.
- **D-04:** The importable package name `mcp_test_framework` is UNCHANGED. Phase 25's API freeze (`from mcp_test_framework.test_code import mcp_session, tool`) holds. Dist name and import name are deliberately decoupled — conventional Python pattern (Pillow/PIL, beautifulsoup4/bs4).

**CLI script rename**

- **D-05:** New primary script: `mcp-contracts = "mcp_test_framework.cli:app"` under `[project.scripts]`.
- **D-06:** Old script `mcp-test-framework` retained for v1.4 as a deprecation-shim entry point (a tiny wrapper that emits `DeprecationWarning` then calls the same `cli:app`) — same shape as Phase 25 D-04 (the `gen-sdet-classes` shim). Removed in v1.5.
- **D-07:** Deprecation warning copy template (mirrors Phase 25 D-05): `"mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5; use mcp-contracts instead."` Hardcoded per call site (one site for the script shim).
- **D-08:** All operator-facing docs (README, CLAUDE.md, docs/) update to the new script name during Phase 26. Old name remains in the deprecation message and nowhere else.

**Pytest plugin scope**

- **D-09:** Plugin entry-point module is a new file inside `src/mcp_test_framework/`. Planner picks the file name; recommend `_plugin.py` (underscore-prefix signals internal) or `plugin.py` (visible to operators in tracebacks). `[project.entry-points.pytest11]` key follows pytest convention — recommend `mcp_test_framework = "mcp_test_framework._plugin"`.
- **D-10:** Phase 26 plugin module contains pre-declared hook signatures with no-op or trivial bodies — at minimum: `pytest_configure(config)`, `pytest_collection_modifyitems(config, items)`, `pytest_addoption(parser)`. Bodies are `pass` or "register the marker" / "no-op log" trivialities. Phase 27 fills `register()`-driven behavior.
- **D-11:** Plugin module ALSO declares the renamed framework fixtures (`mcp_config`, `mcp_judge`, `mcp_target_tool`) plus the existing `mcp_client` and the unprefixed deprecation aliases. Fixtures move from `mcp_test_framework.fixtures` into the entry-point plugin module so auto-discovery surfaces them; the old `fixtures.py` either re-exports or is deprecated in a follow-up. Planner decides which.
- **D-12:** `tests/conftest.py` keeps its current `pytest_plugins = ["mcp_test_framework.fixtures"]` line for v1.4 — internal compat. External operators no longer need that line because the entry point auto-loads. Documented in CONTEXT/README.

**`mcp_test_framework/contracts/` subpackage stub**

- **D-13:** Create `src/mcp_test_framework/contracts/__init__.py` (empty or with one-line docstring describing where `register()` lands in Phase 27) AND `src/mcp_test_framework/contracts/py.typed` (empty marker) during Phase 26. SC3 passes as written — `pyright` resolves `from mcp_test_framework.contracts import ...` without missing-stubs noise (even though the module is currently empty).
- **D-14:** `register()` is NOT in scope for Phase 26 — that's Phase 27's load-bearing decision.

**Fixture surface (SC5)**

- **D-15:** Renames: `config` → `mcp_config`, `judge` → `mcp_judge`, `target_tool` → `mcp_target_tool`. `mcp_client` already prefixed, no change. `_preflight` stays underscored.
- **D-16:** Also prefix three rubric fixtures (`rubric_clarity`, `rubric_disambiguation`, `rubric_parameters` in `fixtures.py`) — confirmed during research these are the actual names in the codebase (NOT `clarity_rubric` etc as suggested in CONTEXT.md prose). Planner verifies and adopts the actual names: prefix to `mcp_rubric_clarity`, `mcp_rubric_disambiguation`, `mcp_rubric_parameters`. If scope expansion is unacceptable during planning, defer to v1.5 sweep with explicit note.
- **D-17:** Unprefixed aliases (`config`, `judge`, `target_tool`, and per D-16 the three rubric names) are separate `@pytest.fixture` defs that receive the prefixed fixture as a parameter, emit one `warnings.warn(DeprecationWarning, ..., stacklevel=2)` per-process per-alias on first request, and return the prefixed value unchanged.
- **D-18:** Removal milestone: v1.5, same as every other Phase 25 / Phase 26 deprecation shim.
- **D-19:** Internal framework tests (`tests/`) currently use the unprefixed names. Planner decides whether to migrate them in Phase 26 or leave them until a dedicated cleanup task.

### Claude's Discretion

- **Plugin module file name** — `_plugin.py` vs `plugin.py` (D-09 recommends `_plugin.py`). Planner picks. Research recommendation: `_plugin.py` — the underscore signals "internal; not part of the operator's import surface" while pytest's `pytest11` entry point references it by string path so the leading underscore is invisible to operators.
- **Wheel-introspection venue (PACK-04)** — place at `tests/framework/test_wheel_shape.py` using stdlib `zipfile`. Build the wheel via `subprocess.run(["uv", "build", "--wheel"], ...)` in a `tmp_path_factory.mktemp(...)` directory. Confirmed below in §Wheel-introspection test.
- **PyPI publish timing** — Phase 26 ships TestPyPI dry-run + local-install verification (SC1 amended). Production PyPI publish defers to Phase 30.
- **Hatch wheel config** — `packages = ["src/mcp_test_framework"]` already covers subpackages and non-`.py` files (including `py.typed`). No `force-include` / `artifacts` needed. **Confirmed via hatch maintainer's quote** in §Don't Hand-Roll.
- **pyright / mypy resolution check** — small CI step or test that imports the three public modules from an installed-wheel virtualenv and runs `pyright`. Existing `pyright>=1.1.409` dev dep is sufficient.

### Deferred Ideas (OUT OF SCOPE)

**Phase 27 (already roadmapped)**
- `register()` API body, `pytest_collection_modifyitems` hook body, contracts module test extraction.

**Phase 28 (already roadmapped)**
- Library-mode config seam — kwargs > pyproject > defaults; `MCPTF_CONFIG_FILE` ignored in library mode.
- Codegen output path defaults.

**Phase 29 (already roadmapped)**
- `--mcp-domain-ui` reporter plugin via `pytest_runtest_logreport`.

**Phase 30 (already roadmapped)**
- Production PyPI publish (post-TestPyPI verification in Phase 26).
- README rewrite leading with library mode.
- Carry-forward live UATs.

**v1.5 cleanup (deferred from Phase 26)**
- Remove `mcp-test-framework` CLI script alias.
- Remove unprefixed fixture aliases.
- Remove every Phase 25 + Phase 26 deprecation shim coherently in one phase.

**Possibly deferred from Phase 26 (planner's call)**
- Migrating framework's own internal tests off the deprecated unprefixed fixture names (D-19).
- Three rubric fixtures `mcp_*` prefix (D-16) — if it expands scope unacceptably.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PACK-01 | Operator's pytest auto-discovers the framework plugin without any `pytest_plugins=[...]` in their conftest — `[project.entry-points.pytest11]` declared in `pyproject.toml` points at the framework's plugin module. | §Architecture Patterns — Pattern 1 (entry point); §Code Examples — pytest11 entry point stanza; §Validation Architecture — `pytest --trace-config` confirms registration |
| PACK-02 | Operator's `pyright` / `mypy` see typed signatures from every framework import — `py.typed` PEP 561 marker present in `src/mcp_test_framework/` and every operator-imported subpackage; wheel ships markers verified. | §Don't Hand-Roll — hatchling auto-includes py.typed; §Architecture Patterns — Pattern 2 (py.typed layout); §Code Examples — PEP 561 marker placement |
| PACK-03 | Operator can `pip install mcp-contracts` and `uv add mcp-contracts` successfully — PyPI distribution name corrected from `mvp-test-framework` to `mcp-contracts` (per D-01/D-03 amendment); no PyPI shim under old name (D-02 — never published). | §Architecture Patterns — Pattern 3 (dist-name vs import-name decoupling); §Code Examples — `[project] name` + `[project.scripts]` stanza; §TestPyPI verification flow |
| PACK-04 | Wheel-content regression test fails CI if the built wheel is missing `mcp_test_framework/contracts/`, `mcp_test_framework/test_code/`, any `py.typed` marker, or contains accidental `tests/` leakage — wheel introspection runs as part of the framework's own CI gate. | §Architecture Patterns — Pattern 4 (wheel-introspection test); §Code Examples — `zipfile`-based wheel walker; §Common Pitfalls — Pitfall 4 (`tests/` leakage) |
</phase_requirements>

## Summary

Phase 26 establishes the packaging substrate so Phases 27–30 can hang library-mode delivery off a stable, discoverable, type-checkable wheel. The phase is structurally five independent diffs that all live in the same milestone for coherence: (1) `[project] name` change to `mcp-contracts`, (2) `[project.entry-points.pytest11]` declaration with a new plugin module, (3) plugin module skeleton with no-op hook bodies plus relocated fixtures, (4) `py.typed` markers in the import-surface subpackages plus a new empty `contracts/` subpackage, (5) a wheel-introspection CI gate that catches drift. None of these surfaces require novel technique — every piece is a textbook pattern in 2026 Python packaging.

The four research findings that materially de-risk the plan: (a) **hatchling includes `py.typed` automatically** — no `force-include` needed; the maintainer's own statement is "files are just files in Hatch land" [VERIFIED: github.com/pypa/hatch/discussions/554]; (b) pytest's `pytest11` entry-point pattern is well-documented and `pytest --trace-config` is the canonical verification command (already runnable in the current repo, confirmed locally); (c) pytest 9.x hook signatures are forward-compatible — the hook system accepts both the maximal `(session, config, items)` form and reduced forms like `(config, items)` for `pytest_collection_modifyitems`; (d) the deprecation-shim pattern for the CLI script is **identical** to Phase 25 D-04's `gen-sdet-classes` shim — lift wholesale.

**Primary recommendation:** Treat the phase as a single coordinated diff to `pyproject.toml` + a new `_plugin.py` module + the new `contracts/` subpackage + a single wheel-introspection test. Six fixture rename-aliases (D-16 rubric scope included) are mechanical. The risk is not in any one surface — it is in writing them in a way that the wheel-introspection test catches drift in all of them.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| pytest plugin entry point declaration | Package metadata (`pyproject.toml`) | — | `pytest11` group is read from installed-package metadata via `importlib.metadata.entry_points()`; no runtime registration mechanism |
| Hook implementations (`pytest_configure`, etc.) | Plugin module (`_plugin.py`) | — | Standard pytest plugin loading: module path in entry point → module imported at session start → hooks discovered by name |
| Framework fixtures (`mcp_config`, `mcp_judge`, etc.) | Plugin module (`_plugin.py`) | `fixtures.py` (re-export shim) | Fixtures defined in a `pytest11`-registered module are auto-available to all collected tests; no `pytest_plugins=[...]` line required |
| Deprecation-shim CLI script | `[project.scripts]` entry + tiny wrapper module | `cli.py:app` (delegate) | Console-script entry points wire a function-import-path to a binary; the wrapper emits the warning and calls `app()` |
| PEP 561 type marker | Package directory (`py.typed` files) | Hatchling wheel builder (auto-include) | Marker files live next to `__init__.py` and ship as ordinary package data; no build-tool config needed |
| Wheel-content gate | `tests/framework/test_wheel_shape.py` | `uv build` subprocess + stdlib `zipfile` | Test owns wheel-build invocation in a tmp dir, then walks the resulting `.whl` (which is a zip) to assert contents |
| TestPyPI dry-run | Operator workflow (manual) | `uv publish --publish-url ...` or `twine upload --repository testpypi` | One-shot verification; not automated in CI for v1.4 (credentials handling deferred to Phase 30) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **hatchling** | 1.x (project already uses it) | Build backend; produces wheel + sdist | Project already on hatchling per `[build-system]` in `pyproject.toml`; auto-includes non-`.py` files inside `packages = [...]` directories per the maintainer's own statement [VERIFIED: github.com/pypa/hatch/discussions/554] |
| **pytest** | 9.0.3 (verified locally) | Test runner + plugin host | Already a dev-dep; pytest 9.x reads `pytest11` entry-point group on session start [CITED: docs.pytest.org/en/stable/how-to/writing_plugins.html] |
| **uv** | 0.11.3 (verified locally) | Build + publish + venv | `uv build --wheel` produces the wheel; `uv publish` handles TestPyPI/PyPI upload with a single command; project already standardized on uv |
| **stdlib `warnings`** | — | DeprecationWarning emission for fixture aliases + script shim | Phase 25 D-01..D-05 locked this; no custom warning class needed |
| **stdlib `zipfile`** | — | Wheel-introspection test walks `.whl` (which is a zip) | No new dependency; `wheel` package adds nothing beyond zipfile for content inspection |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pyright** | ≥1.1.409 (already declared) | PEP 561 marker resolution check from an installed wheel | Smoke test after wheel install: `pyright fixture.py` against a small file that uses `from mcp_test_framework import ...` — confirms types resolve from installed location, not source tree |
| **importlib.metadata** | stdlib | Verify entry-point registration programmatically | `entry_points(group="pytest11")` from an installed venv lists `mcp_test_framework` — useful for the wheel-introspection test |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib `zipfile` for wheel walk | `wheel` package (`wheel.wheelfile.WheelFile`) | `wheel` adds metadata convenience methods (`.dist_info_path`, parsed `METADATA`) but introduces a new dev dep for trivial container inspection. Defer unless test needs `dist-info` parsing. **Reconsider in Phase 30** when README rewrite may want PyPI-classifier verification. |
| `uv publish` for TestPyPI | `twine upload --repository testpypi ./dist/*` | Both work. `uv publish` is one-tool-fewer (we already use uv); twine is the historical standard and is what every "publish to PyPI" tutorial shows. Recommend `uv publish` for the Phase 26 manual step. |
| Console-script shim as a separate module | Same shim as a function inside `cli.py` | Separate module (`_deprecated_script.py`) is cleaner — keeps `cli.py` free of legacy-name leakage. The 5-line wrapper is so small that module-vs-inline is a style question. Recommend separate module for grep-ability ("what's the file that holds the deprecation shim?"). |

**Installation:** No new runtime deps. Phase 26 only changes:
- `pyproject.toml` `[project] name`, `[project.scripts]`, NEW `[project.entry-points.pytest11]`.
- Creates `src/mcp_test_framework/_plugin.py` (or `plugin.py`).
- Creates `src/mcp_test_framework/contracts/__init__.py` + `src/mcp_test_framework/contracts/py.typed`.
- Creates `src/mcp_test_framework/py.typed` + `src/mcp_test_framework/test_code/py.typed`.
- Creates `src/mcp_test_framework/_deprecated_script.py` (CLI deprecation-shim).
- Creates `tests/framework/test_wheel_shape.py`.

**Version verification (performed 2026-05-15):**
- `python --version` → 3.14.3 ✓ (matches `requires-python = ">=3.14"`)
- `uv --version` → 0.11.3
- `pytest --version` → 9.0.3 (already meets ≥9.0)
- `importlib.metadata.entry_points(group="pytest11")` → currently lists `anyio`, `asyncio`, `timeout` from installed plugins. After Phase 26, `mcp_test_framework` joins this list.

## Architecture Patterns

### System Architecture Diagram

```
Operator's project (post-install):
  pip install mcp-contracts
        │
        ▼
  installed wheel layout in site-packages/
    mcp_test_framework/
      __init__.py
      py.typed                  ← PEP 561 root marker
      _plugin.py                ← entry-point target
      cli.py
      _deprecated_script.py     ← CLI shim wrapper
      fixtures.py               ← re-exports or deprecated
      test_code/
        __init__.py
        py.typed
        ...
      contracts/
        __init__.py             ← empty in Phase 26
        py.typed
  mcp_contracts-X.Y.Z.dist-info/
    METADATA
    entry_points.txt            ← [pytest11] mcp_test_framework = mcp_test_framework._plugin
                                  [console_scripts] mcp-contracts = mcp_test_framework.cli:app
                                                    mcp-test-framework = mcp_test_framework._deprecated_script:main
        │
        ▼
  Operator runs `pytest` in their project
        │
        ▼
  pytest startup
    ├─ step 4: load pytest11 entry-point plugins
    │     └─ import mcp_test_framework._plugin
    │           ├─ register hooks: pytest_configure, pytest_collection_modifyitems, pytest_addoption
    │           └─ register fixtures: mcp_config, mcp_judge, mcp_target_tool, mcp_client, _preflight
    │                                  + deprecation aliases (config, judge, target_tool, rubric_*)
    ├─ step 6: load conftest.py files
    └─ collect + run

  Operator runs `mcp-contracts list-tools` → primary CLI surface (no warning)
  Operator runs `mcp-test-framework list-tools` → DeprecationWarning + same behavior

  Operator runs `pytest --trace-config` → confirms PLUGIN registered: ...mcp_test_framework._plugin
```

### Recommended Project Structure (post-Phase-26)
```
src/mcp_test_framework/
├── __init__.py
├── py.typed                  # NEW — PEP 561 root marker
├── _plugin.py                # NEW — pytest11 entry-point target, holds hooks + fixtures
├── _deprecated_script.py     # NEW — mcp-test-framework CLI shim (emits warning + delegates)
├── cli.py                    # mcp-contracts target (unchanged behavior)
├── config.py
├── fixtures.py               # KEEP — re-export shim for v1.4 internal compat (tests/conftest.py)
├── ...
├── test_code/
│   ├── __init__.py
│   ├── py.typed              # NEW
│   └── ...
└── contracts/                # NEW (empty stub for Phase 27)
    ├── __init__.py
    └── py.typed
```

### Pattern 1: pytest11 Entry Point with Plugin Module
**What:** Declare the framework as a pytest plugin via `[project.entry-points.pytest11]` in `pyproject.toml`. The entry-point group `pytest11` is read by pytest at session start; any module listed becomes a discovered plugin and its fixtures are auto-available to all collected tests.

**When to use:** Always, when shipping a pytest plugin via PyPI. Replaces the user-facing `pytest_plugins = [...]` conftest line that the framework currently requires.

**Example:**
```toml
# pyproject.toml — Source: docs.pytest.org/en/stable/how-to/writing_plugins.html
[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"
```

```python
# src/mcp_test_framework/_plugin.py
"""mcp_test_framework pytest plugin — entry-point target.

Registered via [project.entry-points.pytest11] in pyproject.toml.
pytest discovers this module on session start (step 4 of plugin loading
order: builtins, -p plugins, entry-point plugins, PYTEST_PLUGINS env,
conftest.py).

Phase 26 lands the skeleton: hook signatures are pre-declared with no-op
or trivial bodies; Phase 27 fills them with register()-driven behavior.
"""
from __future__ import annotations
import warnings
import pytest

# Re-export framework fixtures with the mcp_ prefix.
# Phase 26 D-11: fixtures move from mcp_test_framework.fixtures into this
# plugin module so the entry point surfaces them without a pytest_plugins
# line in operator conftest. Backward-compatible aliases below.
from mcp_test_framework.fixtures import (
    mcp_client,       # noqa: F401 -- re-exported
    _preflight,       # noqa: F401 -- re-exported (autouse, internal)
    _isolated_home,   # noqa: F401 -- re-exported (internal)
    tool_config,      # noqa: F401 -- re-exported
)

# Renamed fixtures (Phase 26 D-15..D-16). Implementations move into this
# module body in the planner-decided file; for Phase 26 the wholesale move
# can also live in fixtures.py with `from ... import mcp_config as ...`
# here. Planner picks.


# --- pytest hooks (Phase 26 skeleton; Phase 27 fills bodies) ------------

def pytest_addoption(parser: pytest.Parser) -> None:
    """Reserve the --mcp-* option namespace. Phase 26: no options yet.

    Phase 27 adds options like --mcp-server-command for register()-mode
    overrides. Phase 29 adds --mcp-domain-ui. Locking the parser group
    here means later phases don't re-touch pyproject.toml or the entry
    point.
    """
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    # No options registered in Phase 26.


def pytest_configure(config: pytest.Config) -> None:
    """Register the mcp_contract marker. Phase 27 adds register()-glue.

    Idempotent: pytest invokes pytest_configure once per session per
    loaded plugin. Adding inivalue_line is safe across reruns.
    """
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test (Phase 27).",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Reserve hook slot. Phase 27 injects contract tests here.

    Phase 26 body is intentionally empty — locks the hook surface so
    Phase 27 only adds business logic; pyproject.toml and the entry
    point do not re-touch.

    Two-arg form (config, items) is valid in pytest 9.x — pytest passes
    only the args declared in the signature [CITED: pytest 9 hook spec].
    """
    return None


# --- Deprecation alias fixtures (Phase 26 D-17) -------------------------

@pytest.fixture(scope="session")
def config(mcp_config):
    """Deprecated alias for mcp_config; removed in v1.5."""
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed "
        "in v1.5 — use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config

# (judge, target_tool, rubric_clarity, rubric_disambiguation,
#  rubric_parameters follow the same pattern.)
```

**Verification:**
```bash
# After Phase 26 + `uv pip install -e .` (or pip install of the wheel):
uv run pytest --trace-config 2>&1 | grep mcp_test_framework
# Expected: PLUGIN registered: <module 'mcp_test_framework._plugin' from ...>
```

### Pattern 2: PEP 561 py.typed Marker Layout
**What:** Place an empty `py.typed` file in each public-import package directory. PEP 561 says one marker at the top level applies recursively — but practical experience (and what every typed library on PyPI does) is to place one in every public-import subpackage so reorganization doesn't silently break type resolution.

**When to use:** When shipping a typed package via PyPI.

**Example:**
```
src/mcp_test_framework/py.typed                  ← root marker
src/mcp_test_framework/test_code/py.typed        ← belt-and-suspenders for subpackage
src/mcp_test_framework/contracts/py.typed        ← Phase 26 stub
```

Each `py.typed` file is empty (zero bytes). Hatchling includes them automatically — `[tool.hatch.build.targets.wheel]` already has `packages = ["src/mcp_test_framework"]` and that **suffices** [VERIFIED: github.com/pypa/hatch/discussions/554 — "This is supported OOTB as files are just files in Hatch land."]

**Verification:**
```bash
uv build --wheel
unzip -l dist/mcp_contracts-*.whl | grep py.typed
# Expected: three py.typed entries, one per package directory
```

### Pattern 3: Dist Name vs Import Name Decoupling
**What:** The PyPI distribution name (`mcp-contracts`) and the importable package name (`mcp_test_framework`) are deliberately different. Python supports this natively — the package directory name drives `import`, the `[project] name` drives `pip install`.

**When to use:** When the dist name you want is taken on PyPI (or rejected), and renaming the import surface is a breaking change you can't justify. Pillow/PIL is the canonical precedent.

**Example:**
```toml
# pyproject.toml
[project]
name = "mcp-contracts"               # ← what pip install uses
# ... rest unchanged ...

[project.scripts]
mcp-contracts = "mcp_test_framework.cli:app"
mcp-test-framework = "mcp_test_framework._deprecated_script:main"

[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_test_framework"]   # ← what import uses
```

The wheel filename derives from the **dist name**: `mcp_contracts-0.1.0-py3-none-any.whl` (note the underscore: PEP 491 normalizes hyphens to underscores in wheel filenames).

**Gotcha:** `importlib.metadata.version("mvp-test-framework")` in `cli.py:version` (current line 974) must be updated to `version("mcp-contracts")`. This is the only code site that still hardcodes the dist name.

### Pattern 4: Wheel-Introspection Regression Test
**What:** A pytest test that builds the wheel into a tmp dir, then walks the resulting `.whl` (which is a zip) asserting required file presence and forbidden file absence.

**When to use:** Whenever wheel shape is load-bearing for downstream behavior (it is, for PACK-02 and PACK-04 — missing `py.typed` silently degrades pyright, accidental `tests/` inclusion ships test fixtures to operators).

**Example:**
```python
# tests/framework/test_wheel_shape.py
"""Wheel-content regression gate for PACK-04.

Builds the wheel via `uv build --wheel` into a tmp dir, then walks the
resulting .whl (a zip) and asserts the package layout:
  - mcp_test_framework/ present
  - mcp_test_framework/test_code/ present
  - mcp_test_framework/contracts/ present
  - py.typed marker in each of the three above
  - NO tests/ directory leaked into the wheel
  - dist-info/entry_points.txt declares pytest11 = mcp_test_framework._plugin
  - dist-info/entry_points.txt declares console-scripts mcp-contracts +
    mcp-test-framework

Runs in the framework's own pytest suite under tests/framework/. CI fails
on regression. Uses stdlib zipfile + subprocess; no new deps.

Cost: one `uv build --wheel` invocation per test run (~5-10s). Module
scope keeps it to once per pytest session; this test is the only
consumer of the built wheel.
"""
from __future__ import annotations
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel once per test session into a tmp dir."""
    out = tmp_path_factory.mktemp("wheel_shape")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"uv build failed (rc={result.returncode}):\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    wheels = list(out.glob("mcp_contracts-*.whl"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def wheel_names(built_wheel: Path) -> list[str]:
    with zipfile.ZipFile(built_wheel) as zf:
        return zf.namelist()


def test_wheel_filename_uses_new_dist_name(built_wheel: Path) -> None:
    """PACK-03: wheel filename uses the corrected dist name."""
    assert built_wheel.name.startswith("mcp_contracts-"), built_wheel.name


@pytest.mark.parametrize(
    "required_path",
    [
        "mcp_test_framework/__init__.py",
        "mcp_test_framework/py.typed",
        "mcp_test_framework/_plugin.py",
        "mcp_test_framework/test_code/__init__.py",
        "mcp_test_framework/test_code/py.typed",
        "mcp_test_framework/contracts/__init__.py",
        "mcp_test_framework/contracts/py.typed",
    ],
)
def test_wheel_contains_required_path(
    wheel_names: list[str], required_path: str
) -> None:
    """PACK-01/02: import surface + py.typed markers shipped in wheel."""
    assert required_path in wheel_names, (
        f"{required_path!r} missing from wheel; got {wheel_names!r}"
    )


def test_wheel_does_not_leak_tests(wheel_names: list[str]) -> None:
    """PACK-04: no tests/ directory in the wheel."""
    leaked = [n for n in wheel_names if n.startswith("tests/")]
    assert not leaked, f"tests/ leaked into wheel: {leaked}"


def test_wheel_declares_pytest11_entry_point(
    built_wheel: Path, wheel_names: list[str]
) -> None:
    """PACK-01: entry_points.txt declares pytest11 = ...:_plugin."""
    entry_points_path = next(
        (n for n in wheel_names if n.endswith(".dist-info/entry_points.txt")),
        None,
    )
    assert entry_points_path, f"entry_points.txt missing from {wheel_names!r}"
    with zipfile.ZipFile(built_wheel) as zf:
        content = zf.read(entry_points_path).decode("utf-8")
    assert "[pytest11]" in content, content
    assert "mcp_test_framework" in content, content
    assert "mcp_test_framework._plugin" in content, content


def test_wheel_declares_both_console_scripts(
    built_wheel: Path, wheel_names: list[str]
) -> None:
    """PACK-03/D-06: both mcp-contracts and the deprecation shim ship."""
    entry_points_path = next(
        n for n in wheel_names if n.endswith(".dist-info/entry_points.txt")
    )
    with zipfile.ZipFile(built_wheel) as zf:
        content = zf.read(entry_points_path).decode("utf-8")
    assert "mcp-contracts = mcp_test_framework.cli:app" in content, content
    assert "mcp-test-framework = mcp_test_framework._deprecated_script:" in content, content
```

### Pattern 5: Console-Script Deprecation Shim
**What:** A separate console-script entry point points at a thin wrapper module whose `main()` emits a `DeprecationWarning` then calls the primary app.

**When to use:** When renaming a published CLI script and you need one-milestone back-compat. Phase 25 D-04 set the precedent in-tree (`gen-sdet-classes`); Phase 26 lifts the same shape to a separate console-script wrapper.

**Example:**
```python
# src/mcp_test_framework/_deprecated_script.py
"""Console-script wrapper for the legacy `mcp-test-framework` command.

This module exists ONLY to host the deprecation-warning entry point.
Removed in v1.5 alongside every other Phase 25 + Phase 26 deprecation shim.

Why a separate module: keeps the legacy name out of cli.py's import surface;
clean to grep ("what's the file with the deprecation shim?"); deletion in
v1.5 is one line in pyproject.toml plus this file's removal.
"""
from __future__ import annotations

import warnings


def main() -> None:
    """Emit deprecation warning then delegate to the primary cli:app."""
    warnings.warn(
        "the `mcp-test-framework` command is deprecated since v1.4 and "
        "will be removed in v1.5 — use `mcp-contracts` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Import inside the function so warning fires before Typer initializes.
    from mcp_test_framework.cli import app
    app()
```

```toml
# pyproject.toml [project.scripts]
mcp-contracts = "mcp_test_framework.cli:app"
mcp-test-framework = "mcp_test_framework._deprecated_script:main"  # noqa: shim
```

**Gotcha — DeprecationWarning visibility under `__main__`:** Python's default warning filter shows `DeprecationWarning` only when the triggering module is `__main__`. Console-scripts created by the installer (whether pip or uv) run with the wrapper module as `__main__`, so `DeprecationWarning` from `_deprecated_script.main()` is visible on stderr by default — confirmed in Phase 25 D-04 (`gen-sdet-classes` shim works the same way). [VERIFIED: Phase 25 plan 25-02 — gen-sdet-classes shim ships and operator sees the warning per CONTEXT.md.] However, see memory **Deprecation warning visibility (Phase 25)** for the broader concern: `DeprecationWarning` renders as plain text and is easily lost above `--help` walls. Recommend the planner consider whether Phase 26 should land a `warnings.formatwarning` override or operator-channel emission. (Probably defer to v1.5 cleanup phase that consolidates all 6+ shims.)

### Anti-Patterns to Avoid

- **Adding `[tool.hatch.build.targets.wheel.force-include]` for `py.typed`** — hatchling already auto-includes it. Extra config is dead weight and signals to future readers "this is a special case" when it isn't.
- **Putting fixtures in `_plugin.py` AND in `fixtures.py`** — pytest's fixture-lookup is by name; two definitions = a collision warning at best, override at worst. Pick one home for each fixture. Recommended: keep implementations in `fixtures.py`, import-re-export from `_plugin.py` so the entry-point plugin surface includes them, and the existing `tests/conftest.py` `pytest_plugins = ["mcp_test_framework.fixtures"]` line keeps working without change.
- **Hand-writing the deprecation warning in a Typer callback inside the shim script** — Phase 25 already established that the shim is `warnings.warn()` then call-through; don't reinvent. Each shim is 5 lines of code.
- **Using `find_namespace_packages` or `setuptools.find_packages`-style auto-discovery** — this project is on hatchling, explicit `packages = [...]`. Don't switch backends or add discovery magic for one phase.
- **Trying to ship the wheel-introspection test as part of the wheel** — it lives in `tests/framework/`, which `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]` excludes by construction. The wheel-introspection test asserts this.
- **`pytest11` entry-point key prefixed with `pytest_`** — the `pytest_` prefix convention applies only to **hook function names** inside the plugin module. The entry-point key should be a project-name-style identifier (`mcp_test_framework`), NOT `pytest_mcp_test_framework` [CITED: docs.pytest.org/en/stable/how-to/writing_plugins.html — "It is strongly recommended to use Framework :: Pytest classifier" and entry-point key in example is `myproject`, not `pytest_myproject`].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Including `py.typed` in the wheel | Custom hatch build hook, `force-include`, `artifacts`, or `shared-data` stanza | Just place `py.typed` next to `__init__.py` | Hatchling auto-includes — maintainer's quote: "files are just files in Hatch land" [VERIFIED: github.com/pypa/hatch/discussions/554]. Pydantic, hatch-fancy-pypi-readme, and other hatchling projects ship `py.typed` with zero extra config. |
| Pytest plugin auto-discovery | `pytest_plugins = ["...."]` line in operator's conftest, plugin-loader monkeypatch, custom `conftest.py` placement scheme | `[project.entry-points.pytest11]` in `pyproject.toml` | Pytest 9.x already reads the `pytest11` group on startup. `pytest --trace-config` is the verification tool. [CITED: docs.pytest.org/en/stable/how-to/writing_plugins.html] |
| Deprecation warning for renamed CLI script | Bash wrapper, alias in a shell rc file, README note instructing operators to alias | Console-script entry whose body is `warnings.warn` then call-through | Phase 25 D-04 already established this shape; the `gen-sdet-classes` shim is in production and works. |
| Deprecation warning for renamed pytest fixture | Custom warning class, monkey-patch into fixture lookup, conftest.py with `pytest_fixture_setup` hook | Separate `@pytest.fixture` def that takes the new name and calls `warnings.warn` in its body | Pytest's fixture-lookup is per-name; defining a same-named fixture with a thin warning-then-delegate body is the textbook shape. `pyproject.toml`'s existing `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` (Phase 25 D-03) already ensures the framework's own test suite catches accidental use. |
| Wheel-content verification | Custom wheel-parsing library, AST walks of `pyproject.toml` to "predict" wheel content, manual `unzip -l` inspection in CI shell | Stdlib `zipfile` reading the built wheel directly | A wheel is a zip; `zipfile.ZipFile().namelist()` is two lines and covers every assertion needed. The `wheel` Python package adds metadata convenience methods that aren't load-bearing for the Phase 26 gate. |
| TestPyPI publish | Custom credential management, GitHub Actions workflow, multi-step `python setup.py sdist bdist_wheel upload` | `uv build --wheel` + `uv publish --publish-url https://test.pypi.org/legacy/` (or `twine upload --repository testpypi dist/*`) | Both are documented one-liners. uv is already the project's standard; the only friction is the TestPyPI account + API token, which is a manual one-time setup. |
| Dist-name vs import-name reconciliation | Symlinks, `__init__.py` proxies, renaming the package directory | `[project] name = "mcp-contracts"` and leave the package directory as `mcp_test_framework/` | Python supports this natively. The `cli.py:version` command's `importlib.metadata.version("mvp-test-framework")` call is the only string in the codebase that needs updating to `"mcp-contracts"`. |

**Key insight:** Every problem in Phase 26 has an idiomatic ≤5-line solution in modern Python packaging. The risk is not in finding the technique — it is in keeping all six surfaces (pyproject.toml, plugin module, py.typed layout, deprecation shim script, fixture renames, wheel test) coherent under one diff. The wheel-introspection test (Pattern 4) is the cross-cutting gate that catches drift.

## Runtime State Inventory

> Trigger: Phase 26 renames the dist name (`mvp-test-framework` → `mcp-contracts`) and the primary CLI script (`mcp-test-framework` → `mcp-contracts`), plus renames pytest fixtures. This qualifies as a rename/refactor phase.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — verified by inspection. The framework owns no datastores. ChromaDB / Mem0 / SQLite caches do not exist in this codebase. JUnit XML tempfiles are per-run and consumed within the same process; they store no dist-name string. | None |
| **Live service config** | None — verified. The framework is not registered with Datadog/Cloudflare/Tailscale/any external service. The Ollama judge is reached by URL only (no service-side registration of "mcp-test-framework"). | None |
| **OS-registered state** | None — verified. The project is not registered with Windows Task Scheduler, pm2, launchd, or systemd. Console-script wrappers `mcp-test-framework` (current) and `mcp-contracts` + `mcp-test-framework`-shim (post-Phase-26) are reinstalled via `uv sync` on every venv refresh; no OS-level registration to migrate. | `uv sync` after pyproject.toml change re-creates the console-script wrappers in `.venv/Scripts/` (Windows) or `.venv/bin/` (POSIX). The old `mcp-test-framework.exe` shim continues to exist as a deprecation entry. |
| **Secrets/env vars** | One: `MCPTF_CONFIG_FILE` — referenced by name across `cli.py:_load_config`, `fixtures.py:config`, and `tests/conftest.py:_resolve_tool_names`. **The env var name is UNCHANGED in Phase 26.** Phase 28 may change library-mode behavior for it (CFG-01 ignores it in library mode), but Phase 26 does not touch the name. | None for Phase 26. Phase 28 will revisit. |
| **Build artifacts / installed packages** | One specific concern: `cli.py:version()` calls `importlib.metadata.version("mvp-test-framework")` (line 974). After Phase 26 `pip install mcp-contracts`, this lookup will raise `PackageNotFoundError` and fall through to the package `__version__` constant. **Action:** update the lookup string to `"mcp-contracts"`. Also: existing `.venv` in the repo carries the old dist name as metadata; `uv sync` after the pyproject.toml change reinstalls under the new name (verify via `uv pip list \| grep mcp`). Editable-install `.dist-info` directories from prior dev installs may carry the old name; document `uv sync --reinstall` as a recovery step in the plan. | Code edit (`cli.py:974` string update) + `uv sync --reinstall` once the dist-name change lands |

**Canonical post-rename answer:** After every file in the repo is updated, the runtime systems that still have the old strings cached are:
1. The repo developer's local `.venv` (carries `mvp-test-framework` dist-info until `uv sync --reinstall`).
2. Any CI runner cache that pre-installed `mvp-test-framework` (likely zero impact since the project is not yet published).
3. The `importlib.metadata.version()` lookup string in `cli.py:974` (code edit needed, in scope for Phase 26).

## Common Pitfalls

### Pitfall 1: `py.typed` shipped to source but missing from wheel
**What goes wrong:** Pyright/mypy resolve types when developers run them against the source tree (`src/mcp_test_framework/` is on `sys.path` in dev), but **fail** for operators who pip-install the wheel because `py.typed` got excluded by a `.gitignore` / build-config rule.

**Why it happens:** Hatchling respects VCS-ignore files by default. If a developer accidentally adds `py.typed` to `.gitignore` thinking it's an artifact, hatchling silently drops it from the wheel. The dev workflow doesn't notice because source-tree resolution doesn't consult the wheel.

**How to avoid:**
- The wheel-introspection test (Pattern 4) parametrizes over all three `py.typed` paths — regression-tests this exact failure mode.
- Confirm the `.gitignore` does NOT match `py.typed`. (Currently it doesn't — verified.)
- Add a smoke test that runs `pyright` against a fixture file in an installed-wheel virtualenv.

**Warning signs:** Operator reports "I added `mcp-contracts` to my project but my IDE shows everything as `Unknown` / `Any`." That's the signal that types resolve from source-tree but not from installed-wheel.

### Pitfall 2: Plugin entry-point present but module unimportable
**What goes wrong:** `[project.entry-points.pytest11] mcp_test_framework = "mcp_test_framework._plugin"` is in pyproject.toml, but `_plugin.py` has an import error (typo, missing dep, circular import with `fixtures.py`). Pytest then surfaces a noisy `ConftestImportFailure`-equivalent error AT EVERY pytest invocation in the operator's project — even when they're not testing MCP at all.

**Why it happens:** Pytest entry-point plugins load on session start regardless of whether the operator's tests use any framework fixtures. A broken plugin breaks every pytest invocation in the operator's environment.

**How to avoid:**
- The wheel-introspection test (Pattern 4) builds the wheel but does NOT import the plugin from the wheel. Add an extra test that does: install the wheel into a tmp venv and run `pytest --trace-config` against an empty conftest — assert non-zero plugins and zero errors.
- Keep `_plugin.py` imports minimal in Phase 26: only `import warnings`, `import pytest`, and `from mcp_test_framework.fixtures import ...`. Phase 27's `register()` glue can add deps but should fail loud at runtime, not at import time.

**Warning signs:** Operator pytest output starts with a traceback before any test is collected.

### Pitfall 3: Fixture deprecation alias defined but not emitting warning
**What goes wrong:** The unprefixed `config` fixture exists as an alias and is requested by an operator's test, but `warnings.warn` either doesn't fire (suppressed by a higher-up filter) or fires once and is then dedup'd silently — the operator never knows their fixture is going away.

**Why it happens:** Python's default warning filter shows `DeprecationWarning` only for `__main__`. When the warning fires from a session-scoped fixture deep inside pytest's collection plumbing, the `__main__` heuristic doesn't apply and the warning may be suppressed depending on the operator's pytest config and Python version. Phase 25 D-03's `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` ensures the framework's OWN suite catches accidental usage; the operator's environment is not configured this way.

**How to avoid:**
- Test that warnings actually fire by spawning a subprocess pytest with `-W "default::DeprecationWarning"` and a one-test fixture-consumer; assert the warning is captured in stderr.
- Document the warning copy clearly so even if it fires only once, the operator sees a useful message.
- Consider in v1.5 cleanup whether to ship a `warnings.formatwarning` override (memory **Deprecation warning visibility (Phase 25)** flagged this).

**Warning signs:** Phase 26 ships, operators do not migrate off the old fixture names, and v1.5 cleanup surfaces "I had no idea this was deprecated."

### Pitfall 4: Wheel includes `tests/` due to hatch misconfiguration
**What goes wrong:** Operator pip-installs `mcp-contracts`. Their site-packages now contains `mcp_test_framework/` (good) AND a copy of the framework's own `tests/` directory (bad) — shipping internal contract tests as a pytest plugin causes them to be discovered by every operator's pytest session, polluting their suite.

**Why it happens:** Default hatchling wheel-builder behavior with `packages = ["src/mcp_test_framework"]` is sane (only ships `src/mcp_test_framework/`), but if a future maintainer changes `packages` to `["src"]` or adds an `include` rule that matches `tests/`, the leak is silent.

**How to avoid:** The wheel-introspection test (Pattern 4, `test_wheel_does_not_leak_tests`) explicitly asserts NO entry starts with `tests/`.

**Warning signs:** Operator reports "pytest collected 500 extra tests after I installed your library." That's the unambiguous signal of `tests/` leakage.

### Pitfall 5: `cli.py:version()` returns wrong string after dist rename
**What goes wrong:** `mcp-contracts version` returns the stale fallback `__version__` ("0.1.0") because `importlib.metadata.version("mvp-test-framework")` raises `PackageNotFoundError` (the new dist name is `mcp-contracts`) and falls through.

**Why it happens:** The lookup string is hardcoded at line 974 of `cli.py` per a comment block at the top of the file warning about distribution-name vs package-name discrepancy. The rename means this string must update.

**How to avoid:** Single-line code edit, but add a regression test: `mcp-contracts version` from an installed wheel returns the version from `pyproject.toml [project] version`, not the `__version__` fallback. A simple `pytest --tb=short tests/framework/test_cli_version.py::test_version_returns_metadata_version` covers it.

### Pitfall 6: Plugin module shadows operator's own `_plugin` module
**What goes wrong:** Unlikely in practice — the plugin's full path is `mcp_test_framework._plugin`, not `_plugin` — but worth flagging: if an operator imports `_plugin` as a top-level module in their project, no conflict. If they import `mcp_test_framework._plugin` directly (e.g., to register a side-effect), they'll get our plugin module.

**Why it happens:** The leading underscore signals "internal" but the module is technically importable.

**How to avoid:** Docstring on `_plugin.py` says "framework-internal; not part of the operator import surface." Operator-facing imports are `mcp_test_framework.test_code` and `mcp_test_framework.contracts`.

### Pitfall 7: `entry_points.txt` differs between editable install and wheel install
**What goes wrong:** During development with `uv pip install -e .`, the `entry_points.txt` is regenerated from `pyproject.toml` on every dependency resolution. During wheel install, it's frozen at build time. If a maintainer edits `pyproject.toml [project.entry-points.pytest11]` and runs `uv sync` (editable), the change takes effect locally — but the next built wheel inherits whatever is committed to `pyproject.toml` at build time. Both paths read from `pyproject.toml`; no actual mismatch surface. (Listed defensively; not a real risk after verification.) Confirmed safe.

**How to avoid:** The wheel-introspection test reads `entry_points.txt` from the built wheel directly, verifying that the published artifact matches the source-of-truth declaration.

## Code Examples

Verified patterns from official sources:

### Modified `pyproject.toml` (Phase 26 endpoint)
```toml
# Source: docs.pytest.org/en/stable/how-to/writing_plugins.html
#         hatch.pypa.io/latest/config/build/

[project]
name = "mcp-contracts"                           # D-01 — was "mvp-test-framework"
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
mcp-contracts = "mcp_test_framework.cli:app"                         # D-05 — primary
mcp-test-framework = "mcp_test_framework._deprecated_script:main"    # D-06 — shim
                                                                     # noqa: shim — Phase 26 D-06

[project.entry-points.pytest11]                                      # NEW — PACK-01
mcp_test_framework = "mcp_test_framework._plugin"

[dependency-groups]
dev = [
    "pyright>=1.1.409",
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "pytest-timeout>=2.4",
    "ruff>=0.8",
]

# [tool.pytest.ini_options] — UNCHANGED. Phase 25 D-03 filterwarnings
# already covers Phase 26's new shims.

# [tool.hatch.build.targets.wheel] — UNCHANGED. The existing
# packages = ["src/mcp_test_framework"] auto-includes the new
# contracts/ subpackage and every py.typed file.
[tool.hatch.build.targets.wheel]
packages = ["src/mcp_test_framework"]
```

### `_plugin.py` skeleton
See Pattern 1 above. Reproduced inline here in the planner-consumed form.

### `_deprecated_script.py` shim
See Pattern 5 above.

### `contracts/__init__.py` empty stub
```python
"""mcp_test_framework.contracts — library-mode contract test surface.

Phase 26 ships this module as an empty stub. Phase 27 (LIB-01..08) fills it
with the `register()` API and the contract-test extraction so operators can
write:

    from mcp_test_framework.contracts import register
    register(
        server_command=["uvx", "homelab-mcp"],
        tools=["list_registered_servers"],
        judge_endpoint="http://127.0.0.1:11434",
        judge_model="qwen3.6:latest",
    )

See SEED-015 (library mode delivery) and ROADMAP.md Phase 27 for the
register() surface design.
"""
from __future__ import annotations
```

### Wheel-introspection test
See Pattern 4 above.

### Deprecation-alias fixture (representative; six total — config/judge/target_tool + three rubrics)
```python
# In _plugin.py (or fixtures.py if planner chooses to keep impls there)
@pytest.fixture(scope="session")
def config(mcp_config):
    """Deprecated alias for mcp_config; removed in v1.5."""
    import warnings
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed "
        "in v1.5 — use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pytest_plugins = ["mypkg.fixtures"]` in operator's conftest.py | `[project.entry-points.pytest11]` in installed package's pyproject.toml | pytest 7+ (entry-point group is older but `pytest_plugins` in non-root conftest deprecated more recently) | Operator does not need to know the framework's internal module layout; pytest auto-discovers on install |
| `setup.py` with `package_data={"mypkg": ["py.typed"]}` | Hatchling auto-includes — no explicit declaration needed | hatchling default behavior (verified 2026-05-15) | Less config, fewer ways to get it wrong |
| Single dist + import name | Decoupled — `mcp-contracts` (dist) / `mcp_test_framework` (import) | Established pattern; Pillow/PIL since ~2009 | Allows graceful PyPI-name corrections without breaking the import surface |
| `twine upload` to TestPyPI | `uv publish --publish-url https://test.pypi.org/legacy/` | uv shipped publish support in 2024 | One tool fewer; same auth model (API token) |
| Custom `__version__` constant duplicated everywhere | `importlib.metadata.version("dist-name")` with fallback | Python 3.8+ (stdlib); standard in 2026 | Single source of truth (`[project] version`); fallback covers editable-install / source-tree-run cases |

**Deprecated/outdated:**
- **`setup.py`** as a build backend — project already on hatchling. No action.
- **`pytest_plugins` in non-root conftest** — deprecated [CITED: docs.pytest.org/en/stable/how-to/writing_plugins.html]. The framework's own `tests/conftest.py` is the ROOT conftest, so the existing line is fine; just don't add the same line to any sub-conftest.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The actual rubric fixture names in `fixtures.py` are `rubric_clarity`/`rubric_disambiguation`/`rubric_parameters`, NOT `clarity_rubric`/etc. as the CONTEXT.md prose suggested. Verified by reading `fixtures.py` lines 533-544 — the names are `rubric_clarity` et al. | User Constraints — D-16 elaboration | Low — planner just adopts the actual names; CONTEXT.md prose was a placeholder anyway |
| A2 | `[ASSUMED]` `mcp-contracts` PyPI name is still available on 2026-05-15 (per D-01's check). Not re-verified during research. | Standard Stack, Pattern 3 | If wrong, planner picks a fallback from CONTEXT.md's "Available (and discussed)" list: `pytest-mcp-contracts`, `mcp-conformance`, `mcp-blackbox` |
| A3 | `[ASSUMED]` `uv publish` accepts TestPyPI via `--publish-url https://test.pypi.org/legacy/` per common uv-publish recipes. Not directly verified against current uv docs in this session. | Don't Hand-Roll, TestPyPI section | Low — `twine upload --repository testpypi dist/*` is the bulletproof fallback (twine has shipped with TestPyPI as a known repo for years) |
| A4 | `[ASSUMED]` Python's default warning filter shows `DeprecationWarning` from console-script wrappers because the entry-point creates a `__main__` invocation. Phase 25 plan 25-02 reports this works in practice for `gen-sdet-classes`, so the same should work for `mcp-test-framework` shim. Not freshly verified here. | Pattern 5 — gotcha note | Low — Phase 25 ships this exact pattern in production. If it doesn't fire, memory **Deprecation warning visibility (Phase 25)** is already tracking the broader problem and v1.5 cleanup phase has explicit cover for it |
| A5 | `[ASSUMED]` Phase 26 does not need a `[tool.hatch.build.targets.wheel.force-include]` stanza for any subpackage. Maintainer's quote is "files are just files" but the quote is from a 2022 discussion and behavior could have regressed. Mitigation: the wheel-introspection test (Pattern 4) parametrizes over the py.typed paths and would catch a silent exclusion. | Standard Stack, Don't Hand-Roll, Pattern 2 | Low — if hatchling does exclude any file unexpectedly, the wheel-introspection test fails LOUD at plan time and the planner adds the `force-include` line. Catching at plan time vs at operator-install time is exactly what PACK-04 is for. |

**Resolution path:** A1 is locked (verified in code). A2 needs a planner re-verification at plan-phase entry (`pip index versions mcp-contracts` returns nothing). A3 should be probed by the planner with a single dry-run (`uv publish --help` shows the flag). A4 + A5 are both load-bearing-against-test-suite and will be caught by Phase 26's own gates if they're wrong.

## Open Questions

1. **Should the wheel-introspection test build a fresh wheel on every test invocation, or cache the wheel via `@pytest.fixture(scope="session")` and a marker file?**
   - What we know: `uv build --wheel` takes ~5-10s. Running once per test session via module-scoped fixture (as shown in Pattern 4) is fine. Running once per pytest collection is wasteful.
   - What's unclear: whether `uv build` from inside a pytest test that lives in the framework's own `tests/framework/` triggers any re-entry weirdness (build invokes the build backend; hatchling reads its own pyproject.toml; circular dependency unlikely but worth a smoke check at plan-time).
   - Recommendation: ship Pattern 4 as written (module-scoped fixture). If re-entry surfaces, fall back to a script that builds the wheel once outside pytest and a test that consumes the existing artifact.

2. **Should `fixtures.py` be deprecated entirely in Phase 26, or kept as a re-export shim until v1.5?**
   - What we know: `tests/conftest.py:18` has `pytest_plugins = ["mcp_test_framework.fixtures"]`. Phase 26's entry-point makes this redundant for external operators (D-12). The internal conftest can keep it.
   - What's unclear: whether moving fixture impls from `fixtures.py` into `_plugin.py` and re-exporting is cleaner than the inverse (impls stay in `fixtures.py`, `_plugin.py` imports them).
   - Recommendation: keep impls in `fixtures.py`, have `_plugin.py` import them. Reasons: (a) git blame stays useful for fixture history; (b) `fixtures.py` is a documented internal seam from Phase 04; (c) the v1.5 cleanup phase will be smaller if Phase 26 minimizes file moves.

3. **Should Phase 26 migrate the framework's own `tests/` off the unprefixed fixture names, or leave that to v1.5?**
   - What we know: D-19 is explicit "either is defensible." Leaving them ensures the framework's own test suite exercises the deprecation path (filterwarnings catches it).
   - What's unclear: whether the noise from `filterwarnings = always::DeprecationWarning:mcp_test_framework` firing on every framework-test run is desirable signal or annoying churn.
   - Recommendation: leave them. The N>6 fixture rename sites in `tests/` would expand Phase 26's plan count from ~2 to ~5. v1.5 cleanup phase has explicit cover for all of them in one sweep.

4. **What's the minimum TestPyPI smoke verification: just `pip install --index-url`, or also a `pytest --trace-config` run?**
   - What we know: SC1 (per CONTEXT.md amendment) wants TestPyPI dry-run + local-install verification.
   - What's unclear: how strict "verification" is. Just installing succeeds, or also that the plugin shows up in trace-config?
   - Recommendation: both. The two-line smoke flow is `pip install --index-url https://test.pypi.org/simple/ mcp-contracts && pytest --trace-config 2>&1 | grep mcp_test_framework` — fits in a single tmux pane and is the unambiguous "library mode works from PyPI" signal.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All | ✓ | 3.14.3 | — |
| uv | Build + publish | ✓ | 0.11.3 | `python -m build` (PyPA standard tool) for build; `twine` for publish |
| hatchling | Build backend | ✓ (transitive — pulled by `uv build`) | latest 1.x | — |
| pytest | Test runner + plugin host | ✓ | 9.0.3 | — |
| pyright | PEP 561 marker resolution check | ✗ (not on PATH; declared as dev dep but not installed system-wide) | — | `uv run pyright` invokes the project-pinned version; CI step uses `uv run pyright fixture.py` |
| twine | Alternative TestPyPI publish (if `uv publish` doesn't work) | ✗ | — | Install ad-hoc via `uvx twine upload` for the one-time publish step |
| TestPyPI account | One-shot upload | ✗ (no account known to be configured on this machine) | — | Manual one-time setup at https://test.pypi.org/account/register/; flag in plan as operator-action |

**Missing dependencies with no fallback:** None — every Phase 26 step has either uv or a tool installable on demand.

**Missing dependencies with fallback:** pyright (use `uv run pyright`), twine (use `uvx twine` or `uv publish`), TestPyPI account (manual setup — flag as a plan task).

## Validation Architecture

> Skipped — `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`.

## Security Domain

> Skipped — `security_enforcement` is not set in `.planning/config.json` (treated as absent / not opted-in). Phase 26 is packaging-only; introduces no new authentication, authorization, input-validation, or cryptography surfaces. The new code paths (`_plugin.py`, `_deprecated_script.py`, the empty `contracts/__init__.py`) execute only inside the operator's already-trusted pytest process. The deprecation-shim CLI script invokes `cli.py:app` with no extra privilege; the entry-point plugin runs at the same privilege as the operator's pytest. **One operational-security note:** TestPyPI upload requires an API token — never hardcode the token in CI YAML or in pyproject.toml; use a secrets manager. This is operator hygiene, not a framework-design concern.

## Sources

### Primary (HIGH confidence)

- pytest documentation — Writing plugins — https://docs.pytest.org/en/stable/how-to/writing_plugins.html — covers `[project.entry-points.pytest11]` declaration, plugin loading order (step 4 = entry-point plugins), and `pytest --trace-config` as the verification command
- Hatch maintainer answer in discussion #554 — https://github.com/pypa/hatch/discussions/554 — "This is supported OOTB as files are just files in Hatch land" (re: PEP 561 py.typed inclusion in wheels)
- PEP 561 — https://peps.python.org/pep-0561/ — `py.typed` marker file semantics; "marker applies recursively" but practical convention is one per public-import subpackage
- Project `pyproject.toml` (lines 41-60) — Phase 25 D-03 `filterwarnings = ["always::DeprecationWarning:mcp_test_framework"]` already in place; Phase 26 deprecation shims inherit
- Project `src/mcp_test_framework/cli.py` — confirmed `app` is the Typer instance; `mcp-test-framework` and `mcp-contracts` both point at the same callable
- Project `src/mcp_test_framework/fixtures.py` — confirmed fixture names (`config`, `judge`, `mcp_client`, `target_tool`, `_preflight`, `tool_config`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`); confirmed all are session-scoped
- Project `src/mcp_test_framework/sdet/__init__.py` — confirmed Phase 25 D-01..D-05 deprecation pattern (warnings.warn(stacklevel=2, DeprecationWarning), once-per-process via default filter); Phase 26 lifts wholesale
- Local environment probe — `uv run pytest --trace-config` confirms plugin trace mechanism works in this venv; `entry_points(group="pytest11")` returns 3 installed plugins (anyio, asyncio, timeout) — `mcp_test_framework` will join after Phase 26 install

### Secondary (MEDIUM confidence)

- LambdaTest pytest-bdd reference (verified via WebSearch) — `pytest_collection_modifyitems` signature `(session, config, items)` in pytest 9.x; pytest passes only declared args
- pydantic project `pyproject.toml` — https://github.com/pydantic/pydantic/blob/main/pyproject.toml — hatchling-backed typed project ships `py.typed` with no special hatch config (confirms maintainer's quote)
- Packaging User Guide pyproject.toml reference — https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ — covers `[project.scripts]`, `[project.entry-points]`, and console-script wrapper semantics

### Tertiary (LOW confidence — flagged in Assumptions Log)

- A3, A5 are assumptions per the Assumptions Log; would be re-verified at plan-phase entry

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified locally; all required versions present in dev environment
- Architecture: HIGH — patterns are textbook 2026 Python packaging; entry-point pattern verified via `pytest --trace-config` on current install
- py.typed mechanics: HIGH — maintainer-quoted answer + cross-reference against pydantic's own pyproject.toml
- Deprecation-shim pattern: HIGH — lifting Phase 25 D-04 verbatim; pattern is in production
- Wheel-introspection test shape: MEDIUM — idiomatic but specific to this project; the `subprocess.run(["uv", "build", ...])` invocation may need tuning depending on CI environment (uv on PATH? uv installed as a Python module?)
- Pitfalls: HIGH — every pitfall has either an automated test catching it (Pitfall 1, 4, 5, 7) or an explicit avoidance strategy (Pitfall 2, 3, 6)
- TestPyPI verification flow: MEDIUM — flow is well-documented but the specific `uv publish` invocation is assumption-level (A3); twine fallback is iron-clad

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (30 days — packaging ecosystem is stable; hatchling and pytest API surfaces are mature)

---

*Phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-skeleton*
*Research completed: 2026-05-15*
