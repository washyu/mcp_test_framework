# Phase 09: JUnit XML output & per-tool reporting - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 4 (1 modified, 1 modified, 1 new, 1 new test file)
**Analogs found:** 4/4 (1 exact, 2 role-match, 1 partial — pytest-plugin role has no in-repo analog by design)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/cli.py` (MODIFY: add `--junit-xml`, optional `_build_pytest_args` helper) | CLI extension (Typer command) | request-response (CLI → pytest.main) | `src/mcp_test_framework/cli.py:run` (existing `--config` option on the same command) | exact (same file/function — additive arg) |
| `src/mcp_test_framework/_reporter.py` (NEW: pytest plugin with `pytest_runtest_logreport` + `pytest_terminal_summary`) | pytest plugin (reporter hooks) | event-driven (per-test report → aggregate → terminal summary) | `tests/conftest.py` (only existing pytest-hook module: `pytest_configure`, `pytest_generate_tests`) — no plugin under `src/` exists yet | role-match (hook author/style; new placement under `src/`) |
| `tests/conftest.py` (MODIFY: append `_reporter` to `pytest_plugins` list — line 12) | config / plugin registration | one-line edit | `tests/conftest.py:12` (existing `pytest_plugins = ["mcp_test_framework.fixtures"]`) | exact |
| `tests/test_reporter.py` (NEW: unit tests for `_reporter.py` + `_build_pytest_args`) | test (pytest plugin verification) | request-response (CliRunner; in-process plugin assertions) | `tests/test_config_init_cli.py` (CliRunner-based CLI surface tests, mix of unit + live) AND `tests/test_tool_config.py` (subprocess pytest invocation pattern at top of file) | role-match (CLI surface) + partial (plugin in-process verification has no analog) |

---

## Pattern Assignments

### `src/mcp_test_framework/cli.py` — adding `--junit-xml=PATH` to `run` (CLI extension, request-response)

**Analog:** `src/mcp_test_framework/cli.py` itself — the existing `--config` Typer option on the `run` command is the exact template (same function, same surface, additive flag).

**L-03 / L-04 contract reminder:** function-local `import pytest`, NO try/except wrap around `pytest.main()`, exit-code propagation via `raise typer.Exit(code=pytest.main(...))`. See `cli.py:127, 129-131`.

**Imports pattern** (`cli.py:26-41`):
```python
from __future__ import annotations

import asyncio
import json
import os
import shutil
import textwrap
from contextlib import AsyncExitStack
from importlib import metadata
from pathlib import Path

import typer
from mcp.types import Tool

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
```
Phase 09 adds nothing at module scope — `pytest` stays function-local (L-04).

**Existing Typer option pattern to mirror** (`cli.py:98-108`, the `run` signature):
```python
@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def run(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    pytest_args: list[str] | None = typer.Argument(
        None,
        help="Args after `--` are forwarded to pytest.main([\"tests\", *args]).",
    ),
) -> None:
```
**Phase 09 addition shape** (insert between `config` and `pytest_args`, preserving D-01b spelling — public flag is `--junit-xml`, internally pytest receives `--junitxml` no-dash):
```python
junit_xml: Path | None = typer.Option(
    None,
    "--junit-xml",
    help=(
        "Write JUnit XML to PATH (translates to pytest's --junitxml). "
        "If a passthrough --junitxml=... is also supplied after `--`, "
        "the passthrough wins (last-occurrence rule)."
    ),
),
```

**Existing function body pattern to extend** (`cli.py:126-131`):
```python
import pytest  # function-local: pytest is dev-only, not a runtime dep

_load_config(config)  # raises typer.Exit(2) on bad path; ValidationError propagates
forwarded = list(pytest_args or [])
raise typer.Exit(code=pytest.main(["tests", *forwarded]))
```

**Phase 09 extension** (CD-06 option 3 — extracted helper for testability; keeps L-03 no-wrap intact):
```python
import pytest  # function-local: pytest is dev-only, not a runtime dep

_load_config(config)
argv = _build_pytest_args(junit_xml, pytest_args)
raise typer.Exit(code=pytest.main(argv))
```

The helper sits at module level alongside the other `_format_*` helpers (`cli.py:299-397`), e.g. just below `_load_config`. Shape:
```python
def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
) -> list[str]:
    """Translate --junit-xml=PATH into pytest's --junitxml=PATH. D-01a:
    explicit flag is added BEFORE passthrough so user's later passthrough
    --junitxml=... overrides via pytest's last-occurrence argparse rule.
    """
    forwarded = list(pytest_args or [])
    args = ["tests"]
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    return args
```

**Existing helper-placement convention** (`cli.py:64-89`, `_load_config` style — module-level, underscore-private, terse docstring):
```python
def _load_config(path: Path | None) -> Config:
    """Shared config loader for `run` and `list-tools` commands.

    If `path` is provided, sets MCPTF_CONFIG_FILE so Config()'s
    settings_customise_sources picks up the YAML overlay. Pydantic
    ValidationError propagates uncaught -- Pydantic's own message is
    the diagnostic (CONTEXT.md Discretion bullet 2).
    ...
    """
```
Apply the same shape to `_build_pytest_args` — module-level, underscore-private, docstring cites D-01a precedence.

---

### `src/mcp_test_framework/_reporter.py` — NEW pytest plugin (pytest plugin, event-driven)

**Analog:** No in-repo pytest plugin exists yet. Closest is `tests/conftest.py` for "module that defines pytest hooks" — same hook-author conventions apply (top-level hook functions named `pytest_<hook>`, type-annotated params, terse module docstring citing the decisions it implements).

**Module placement convention** (D-02b: under `src/` not `tests/`; underscore prefix marks "internal — public surface is rendered output, not API"). Mirrors existing `src/mcp_test_framework/_isolation.py` placement (also underscore-private, also a non-public framework module):

**Module docstring style to mirror** — `src/mcp_test_framework/_isolation.py:1-40`:
```python
"""Per-session host-state isolation: env-allowlist + HOME redirect for spawned MCP subprocess.

Phase 06 implementation of ISOL-02, ISOL-04, ISOL-05, ISOL-07. Builds the COMPLETE
``env`` dict passed to ``mcp.client.stdio.StdioServerParameters`` so the spawned
MCP server inherits ONLY allowlisted environment variables and a HOME/USERPROFILE
redirected to a per-session tempdir.

Design constraints (per .planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md):
- D-05: Isolation is ALWAYS-ON. No toggle, no ``--no-isolation`` CLI escape hatch.
...
"""
from __future__ import annotations
```
Phase 09 docstring should similarly cite the phase doc and key decisions: D-02 (registration mechanism), D-02a (parametrize ID `[<tool>]` extraction; tests w/o suffix excluded), D-02c (emit via `terminalreporter`), D-03 (any-fail-wins verdict + error→FAIL collapse), D-05 (skip-reason de-dup + `;` join + cap-3).

**Hook-function style to mirror** — `tests/conftest.py:24-49` (existing top-level hook with type-annotated `config` param + module-level state guard):
```python
def pytest_configure(config) -> None:
    """Fail-fast if anything importable from homelab_mcp leaks into the test process.

    Belt-and-suspenders for ruff TID251 (which does not recursively cover
    submodule imports -- see 01-RESEARCH Pitfall 4 + the comment block in
    pyproject.toml above the [tool.ruff.lint.flake8-tidy-imports.banned-api]
    table).
    ...
    """
    leaked = [
        name
        for name in sys.modules
        if name == "homelab_mcp" or name.startswith("homelab_mcp.")
    ]
    if leaked:
        raise RuntimeError(...)
```

**Module-level state pattern** — `tests/conftest.py:65` (cache for cross-hook state, plain module global with type annotation; matches D-02a "live state — no JUnit XML re-parse"):
```python
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None
```
Phase 09 should use the same style for the per-tool aggregation buffer:
```python
# Per-tool aggregation buffer. Keyed by extracted tool name (parametrize
# suffix from report.nodeid). Values track the running verdict + collected
# skip reasons so pytest_terminal_summary can render without re-parsing JUnit.
_PER_TOOL: dict[str, dict] = {}
```

**Tool-name extraction pattern** — `tests/conftest.py:124-136` is the source of the `[<tool_name>]` IDs Phase 09 reads back. The extraction inverse:
```python
# Phase 07 emits IDs as `<test_name>[<tool_name>]` via:
#   metafunc.parametrize("target_tool", names, indirect=True, ids=names)
# Inverse: split on the LAST '[' (test name itself never contains '['),
# strip trailing ']'. Tests without `[...]` suffix (unit tests in
# tests/unit/) have no tool affinity and are excluded — D-02a.
```
Concrete shape (no in-repo analog — this is the first plugin; follow the docstring + early-return idiom from `_session_needs_preflight`, `fixtures.py:67-84`):
```python
def _extract_tool_name(nodeid: str) -> str | None:
    """Return tool name from `<file>::<test>[<tool>]` nodeid, or None.

    Phase 07 parametrize ID convention (tests/conftest.py:124-136). Tests
    without `[...]` suffix (unit tests) return None and are excluded from
    the per-tool summary per D-02a.
    """
    # Use rfind on the test-id portion only (the file path before "::" can
    # contain neither '[' nor ']' on any platform pytest supports).
    if "[" not in nodeid or not nodeid.endswith("]"):
        return None
    return nodeid[nodeid.rindex("[") + 1 : -1]
```

**Hook signature reference (from pytest docs cited in CONTEXT canonical_refs):**
```python
def pytest_runtest_logreport(report) -> None:
    """Called 3x per test (setup, call, teardown). We accumulate on
    `call` outcome by default, but skips/errors can fire at setup phase
    (Phase 08 D-09 skip-via-fixture surfaces in `setup` phase).
    """
    # Pseudocode — planner expands per D-03 algorithm:
    #   if tool := _extract_tool_name(report.nodeid):
    #       state = _PER_TOOL.setdefault(tool, {"verdict": None, "reasons": []})
    #       # report.outcome ∈ {"passed", "failed", "skipped"} + report.failed (errors)
    #       # D-03 rule: any failed/error → FAIL; else any passed → PASS; else SKIP
    #       # D-05: collect report.longrepr text on skips for de-dup later

def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """D-02c: emit via terminalreporter.write_sep / write_line, NOT print.
    D-04b: suppress under -q (terminalreporter.config.option.verbose < 0).
    CD-03: rows grouped FAIL → SKIP → PASS, alphabetical within each.
    D-05: SKIP reasons de-duped, first-seen order, capped at 3 distinct.
    """
```

**Skip-reason source (from CONTEXT specifics):** `report.longrepr` for skipped tests is a `(file, lineno, reason)` tuple where `reason` is the literal `pytest.skip(reason=...)` string. Phase 08 D-16 guarantees non-empty `skip_reason`; D-05a says verbatim-no-transform.

**Error handling pattern** — no exceptions raised in hooks (CD-01: accept pytest defaults; D-02b: plugin's value is rendered output, not API). Mirror `_isolation.py`'s zero-`try`/zero-`raise` style. The single hard guard is the type narrow on `_extract_tool_name` returning `None` — early-return at the top of `pytest_runtest_logreport`.

---

### `tests/conftest.py` — appending `_reporter` to `pytest_plugins` (config, one-line edit)

**Analog:** `tests/conftest.py:12` itself — exact pattern. The list is the load-bearing one-line seam (D-layout-1 from Phase 4).

**Existing line 12** (the EXACT shape to extend):
```python
pytest_plugins = ["mcp_test_framework.fixtures"]
```

**Phase 09 modification** (single string append; D-02 sibling-pattern explicit):
```python
pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]
```

**Order constraint:** `fixtures` should remain first because it owns `_preflight` (autouse, session-scoped, runs first). `_reporter` is append-only — its `pytest_runtest_logreport` fires AFTER fixtures resolve, regardless of `pytest_plugins` ordering, so order is cosmetic but matches D-02's "parallel to `mcp_test_framework.fixtures`, sibling pattern" wording.

**Comment context lives at top of file** (`tests/conftest.py:1-8`):
```python
"""Pytest session-level configuration.

Phase 1 ships the black-box `sys.modules` guard. Phase 4 ships the
session-scoped fixtures (mcp_client, judge, target_tool, config, _preflight,
and three rubric fixtures) via `pytest_plugins` registration of
`mcp_test_framework.fixtures` -- the load-bearing one-line seam adopters add
to their own conftest to inherit the framework's fixture set (D-layout-1).
"""
```
Planner should append a one-sentence Phase 09 amendment to this docstring noting that `_reporter` is registered alongside `fixtures` for the per-tool summary (OUTPUT-03).

---

### `tests/test_reporter.py` — NEW unit tests (test, request-response)

**Analog A (CLI surface — for `_build_pytest_args` and `--junit-xml --help`):** `tests/test_config_init_cli.py` — same `CliRunner` pattern, same unit/live split, same mix of pure-path checks (no live server) and `@pytest.mark.live_homelab` end-to-end checks.

**CliRunner pattern to copy** (`tests/test_config_init_cli.py:13-26`):
```python
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _invoke(*args: str):
    """CliRunner construction site -- isolated for forward-compat with future
    Typer kwargs (e.g. mix_stderr deprecation)."""
    return CliRunner().invoke(app, list(args))
```

**Unit-level help-flag test pattern** (`tests/test_config_init_cli.py:33-39`):
```python
def test_help_lists_flags() -> None:
    """D-21: subcommand surface includes --config, --output, --force."""
    result = _invoke("config-init", "--help")
    assert result.exit_code == 0, result.output
    assert "--config" in result.output
    assert "--output" in result.output
    assert "--force" in result.output
```
Phase 09 mirror: `test_run_help_lists_junit_xml` asserting `--junit-xml` appears in `mcp-test-framework run --help`.

**Pure-path / no-live-server gate test pattern** (`tests/test_config_init_cli.py:42-55`):
```python
def test_refuse_overwrite_without_force(tmp_path: Path) -> None:
    """D-23: --output to existing file w/o --force -> exit 2 + stderr message.

    Fires BEFORE discovery, so this test does NOT require a live MCP server
    (no @live_homelab marker -- the overwrite gate is a pure path check).
    """
```
Phase 09 mirror: unit tests for `_build_pytest_args` — pass tmp paths and arg lists, assert the resulting argv shape (D-01a precedence verified by the order of args in the returned list). No CliRunner needed for this — direct function call:
```python
from mcp_test_framework.cli import _build_pytest_args

def test_build_pytest_args_translates_dashed_flag(tmp_path: Path) -> None:
    """D-01b: public --junit-xml -> pytest's --junitxml (no-dash)."""
    result = _build_pytest_args(tmp_path / "out.xml", None)
    assert result[0] == "tests"
    assert any(arg.startswith("--junitxml=") for arg in result)
    assert not any(arg.startswith("--junit-xml=") for arg in result)
```

**Analog B (in-process plugin verification — for `_reporter.py` hooks):** `tests/test_tool_config.py:1-33` — uses subprocess pytest invocation as the canonical "drive a real pytest run and inspect its output" pattern. Plus `pytester` (pytest's built-in fixture, NOT yet used in this repo) is the recommended idiomatic alternative for hook tests.

**Subprocess-pytest pattern from `tests/test_tool_config.py:18-29`** (apply to a fixture-yaml live run for D-04 always-on summary verification):
```python
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml
from pydantic import ValidationError
```

**Live-marker pattern** (`tests/test_config_init_cli.py:63-72`):
```python
@pytest.mark.live_homelab
def test_default_emits_scaffold_to_stdout() -> None:
    """D-22 / TOOLCFG-02 / TOOLCFG-04: default mode prints version: 1 + tools: scaffold."""
    result = _invoke("config-init")
    assert result.exit_code == 0, result.output
    assert "version: 1" in result.output
    assert "tools:" in result.output
```
Phase 09 mirror: live verification reads a JUnit XML emitted from a real run (CD-04 P3 task; uses Phase 08's retained `suggest_deployments` failure as the canonical `<failure>` example per CONTEXT specifics line 123).

**Test-file ordering convention** (mirrors `tests/test_config_init_cli.py` and `tests/test_tool_config.py`): unit-level tests first under a `# === Unit-level ===` separator, then live tests under `# === Live ===`. The recurring banner in `tests/test_tool_config.py:35-38`:
```python
# ===========================================================================
# Schema tests -- sync, load-time, no live services
# ===========================================================================
```

**Recommendation for plugin hook tests:** use pytest's built-in `pytester` fixture (no in-repo analog yet; `tests/test_tool_config.py:21` shows the existing fallback pattern of `subprocess.run([sys.executable, "-m", "pytest", ...])` if `pytester` is undesired). `pytester` is lighter — it runs pytest in-process with a synthetic test tree and exposes `result.stdout.fnmatch_lines([...])` for asserting on the per-tool summary section. Planner picks based on testability appetite; both patterns are precedented.

---

## Shared Patterns

### Phase 5 D-cli-flags-3 — pytest is dev-only, function-local import

**Source:** `src/mcp_test_framework/cli.py:122-127`
**Apply to:** `cli.py:run` modifications ONLY. Do NOT pull `pytest` into `_reporter.py` module scope either — `_reporter` is loaded BY pytest (via `pytest_plugins`), so by definition pytest is in scope when `_reporter` imports execute. But hook bodies should annotate `report` / `terminalreporter` / `config` as plain typed params; no `import pytest` needed at module top of `_reporter.py` unless using `pytest.skip` / `pytest.exit` (which the reporter does not).

```python
"""...
`import pytest` is function-local: pytest is in `[dependency-groups] dev`
only, not `[project.dependencies]`. Module-scope import would break
`version` and `list-tools` for users installing the wheel without dev
extras.
"""
import pytest  # function-local: pytest is dev-only, not a runtime dep
```

### L-03 — no try/except wrap around pytest.main

**Source:** `src/mcp_test_framework/cli.py:128-131`
**Apply to:** `cli.py:run` after Phase 09 modifications. The `_build_pytest_args` helper sits BEFORE the `pytest.main(...)` call; the call itself stays bare:
```python
_load_config(config)  # raises typer.Exit(2) on bad path; ValidationError propagates
forwarded = list(pytest_args or [])
raise typer.Exit(code=pytest.main(["tests", *forwarded]))
```
Phase 09 substitution: replace `["tests", *forwarded]` with `_build_pytest_args(junit_xml, pytest_args)`. The `raise typer.Exit(code=pytest.main(...))` shape is INVARIANT.

### Underscore-private module placement under `src/`

**Source:** `src/mcp_test_framework/_isolation.py` (precedent set in Phase 06)
**Apply to:** `src/mcp_test_framework/_reporter.py` (CD-05 — `_reporter.py` matches the underscore convention; the framework already has one underscore-private module so this is two-of-a-kind, not novel).

### Module-level state for cross-hook coordination

**Source:** `tests/conftest.py:65` (`_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None`)
**Apply to:** `_reporter.py` per-tool aggregation buffer. Plain module-level dict with type annotation; no `pytest.StashKey` (CD-01 in Phase 07 chose dict over Stash for simplicity, same logic applies here per D-02 "live state").

### File header docstring cites phase + decision IDs

**Source:** every file in `src/mcp_test_framework/` and `tests/` — see `_isolation.py:1-40`, `fixtures.py:1-21`, `cli.py:1-25`, `tests/conftest.py:1-8`, `tests/test_isolation.py:1-32`.
**Apply to:** all four Phase 09 files. Every docstring leads with the phase number, names the requirements it satisfies (OUTPUT-01..03), and cites decision IDs (D-01..05, L-01..06, CD-01..06) from `09-CONTEXT.md` so the file can be audited against the context doc directly.

### `from __future__ import annotations` first

**Source:** every Python module in the repo (e.g. `cli.py:26`, `fixtures.py:22`, `tests/conftest.py:11`, `tests/test_config_init_cli.py:12`)
**Apply to:** `_reporter.py` and `tests/test_reporter.py`. Always the first import after the docstring.

### Test marker convention — live tests gated; unit tests unmarked

**Source:** `pyproject.toml:49-53` declares `live_homelab` + `live_ollama`; default `addopts = "-m 'not live_homelab and not live_ollama'"`. `tests/test_config_init_cli.py:33-39` (unmarked unit) vs `tests/test_config_init_cli.py:63-72` (`@pytest.mark.live_homelab`).
**Apply to:** `tests/test_reporter.py`. `_build_pytest_args` unit tests + `--help` snapshots stay UNMARKED. The fixture-yaml live run that produces a real JUnit XML file gets `@pytest.mark.live_homelab`. L-05: do NOT add new markers; reuse the two existing ones.

---

## No Analog Found

Files where the closest in-repo match is partial; planner should lean on RESEARCH.md / pytest official docs for the missing pieces:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/mcp_test_framework/_reporter.py` | pytest plugin (full) | event-driven (`pytest_runtest_logreport` aggregation) | The repo has pytest **hooks** (in `tests/conftest.py`) but no full-fledged **plugin module under `src/`** registered via `pytest_plugins`. The `mcp_test_framework.fixtures` module IS such a plugin (it's referenced in `pytest_plugins`), but it only declares `@pytest.fixture` / `@pytest_asyncio.fixture` — it has no terminal-reporter or runtest-logreport hooks. Planner should consult pytest docs (cited in CONTEXT canonical_refs: `pytest_terminal_summary`, `pytest_runtest_logreport`) for the hook surface, then style the module per `_isolation.py` (placement) + `tests/conftest.py:24-49` (hook function shape). |
| In-process pytest plugin tests using `pytester` | test (plugin verification) | event-driven (synthetic test run → assert on plugin output) | No prior use of `pytester` in this repo. `tests/test_tool_config.py` uses `subprocess.run([sys.executable, "-m", "pytest", ...])` as the equivalent pattern (heavier, but precedented). Planner picks `pytester` (idiomatic) or subprocess (precedented); both work. The `CliRunner` pattern from `tests/test_config_init_cli.py:13-26` covers the CLI surface directly and is unaffected by this gap. |

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/` (all 11 .py files: cli.py, config.py, fixtures.py, models.py, mcp_client.py, ollama_judge.py, judge_protocol.py, schema_validator.py, rubrics.py, _isolation.py, __init__.py)
- `tests/` (conftest.py + 3 integration test files: test_mcp_tool_contract.py, test_isolation.py, test_tool_config.py, test_config_init_cli.py)
- `tests/unit/` (5 unit test files surveyed for style convention)
- `tests/smoke/` (3 smoke test files surveyed for marker convention)
- `pyproject.toml` (markers + dep groups + ruff config)

**Files scanned:** ~22 source/test files

**Key cross-cutting observations:**
1. The framework has ONE existing pytest plugin module (`src/mcp_test_framework/fixtures.py`) registered via `pytest_plugins` in `tests/conftest.py:12`. Phase 09's `_reporter.py` is the second — same registration mechanism, sibling placement under `src/`.
2. The framework's only existing pytest hooks (`pytest_configure`, `pytest_generate_tests`) live in `tests/conftest.py`, NOT in the `fixtures.py` plugin. D-02 explicitly moves the new hooks INTO a plugin module under `src/` — this is a deliberate architectural choice, not a deviation from precedent.
3. The `[<tool_name>]` parametrize ID convention Phase 09 reads (L-01) is implemented at exactly one site: `tests/conftest.py:124-136`. Planner should cite this site as the inverse of the extraction logic in `_reporter.py`.
4. CLI option additions to existing Typer commands have one in-repo template: the `--config` option recurring on `run`, `list-tools`, `config-init` — same `typer.Option(None, "--flag", help="...")` shape every time. Phase 09's `--junit-xml` follows that exact template.

**Pattern extraction date:** 2026-05-07
