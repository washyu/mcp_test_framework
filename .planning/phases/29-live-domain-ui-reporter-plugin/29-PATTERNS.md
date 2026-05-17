# Phase 29: Live domain-UI reporter plugin - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 5 (1 new module, 2 modified, 1 packaging, 1 new tests)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_reporter.py` (NEW) | pytest11 plugin module | event-driven (hook callbacks) | `src/mcp_test_framework/_plugin.py` | exact (sibling module, same pytest11 shape) |
| `src/mcp_test_framework/_runner.py` `_build_parsed_run_from_reports` (MODIFY: new function) | input adapter / transform | batch transform (list[TestReport] -> ParsedRun) | `_runner.py:491` `parse_junit_xml` | exact (D-01a locks co-location; same output dataclass) |
| `src/mcp_test_framework/cli.py` (MODIFY: delete 912-969 block, add flag to argv) | CLI entry-point glue | request-response | existing `_build_pytest_args` callsite + JUnit-parse block | exact (same file, in-place rewire) |
| `pyproject.toml` (MODIFY: add second pytest11 key) | packaging metadata | config | existing `[project.entry-points.pytest11]` block lines 27-32 | exact (sibling key) |
| `tests/framework/test_reporter.py` (NEW — location TBD) | unit tests | request-response | `tests/framework/unit/test_runner_parser.py` + `tests/framework/test_phase27_spike_synthetic_module.py` | role-match (no `test_plugin.py` exists; hybrid of two existing test styles) |

---

## Pattern Assignments

### `src/mcp_test_framework/_reporter.py` (pytest11 plugin, event-driven)

**Analog:** `src/mcp_test_framework/_plugin.py`

**Module docstring style** (`_plugin.py:1-33`):
The reporter should open with a docstring naming the entry-point role, distinguishing it from `_plugin.py`, and stating the framework-primitive constraint (no SUT awareness). Pattern from `_plugin.py:1-33`:

```python
"""mcp_test_framework pytest plugin — entry-point target.

Registered via [project.entry-points.pytest11] in pyproject.toml so pytest
auto-discovers the framework's fixtures and hooks WITHOUT any
`pytest_plugins=[...]` declaration in the operator's conftest.
...
This plugin is intentionally framework-primitive: NO SUT-aware logic, NO
homelab-mcp imports, NO opinions about what tools exist.
"""
```

**Imports pattern** (`_plugin.py:34-68`):
```python
from __future__ import annotations

import asyncio
import os
import warnings
from pathlib import Path

import pytest
from _pytest.python import Module as _PytestModule
from pydantic import ValidationError

from mcp_test_framework._black_box_guard import check_black_box
from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
```

Reporter equivalent (per RESEARCH.md "Reporter plugin skeleton"): drop `Module`, `asyncio`, `ValidationError`, `check_black_box`, `Config`, `McpTestClient`; ADD `import sys`, `from dataclasses import dataclass, field`, `from mcp_test_framework import _runner`.

**`pytest_addoption` pattern** (`_plugin.py:206-225`):
The existing plugin already creates the `mcp_test_framework` option group; the reporter MUST reuse it via `parser.getgroup("mcp_test_framework")` (not create a new one). Excerpt:
```python
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.getgroup("mcp_test_framework", "MCP test framework options")
    parser.addini(
        "mcp_config_file",
        type="string",
        default="",
        help=(
            "Path to MCP test framework YAML config; relative paths are "
            "resolved relative to pyproject.toml's directory. Absent or "
            "empty = library mode opted out (no contract tests injected)."
        ),
    )
```

Reporter copies this shape (same group call, same `help=` indentation/wrapping style, same docstring tone) but registers an `addoption` not an `addini`. Locked surface per D-04:
- `action="store"`, `nargs="?"`, `const="auto"`, `default="off"`, `choices=["auto","force","off"]`.

**`pytest_configure` pattern** (`_plugin.py:127-203`):
The existing plugin demonstrates the canonical pytest_configure shape used in this codebase: short docstring listing the responsibilities, early-return on opt-out, side-effect stashing on `config.<attr>`. Reporter follows the same shape:

```python
def pytest_configure(config: pytest.Config) -> None:
    """Resolve --mcp-domain-ui mode and initialize the accumulator.

    Responsibilities:
      - Worker no-op: early-return when running under xdist worker
        (hasattr(config, "workerinput")).
      - Read --mcp-domain-ui choice; if 'off' -> early-return.
      - If 'auto' and stdout is not a TTY -> early-return.
      - Initialize _ReporterState and stash on module-level _STATE.
    """
    global _STATE
    if hasattr(config, "workerinput"):
        return
    choice = config.getoption("--mcp-domain-ui", default="off")
    if choice == "off":
        return
    if choice == "auto" and not bool(getattr(_ORIGINAL_STDOUT, "isatty", lambda: False)()):
        return
    _STATE = _ReporterState(enabled=True)
```

Two patterns to lift verbatim:
1. **Stash convention:** `_plugin.py` stashes on `config._mcp_contracts_config` (line 203, with `# type: ignore[attr-defined]`). Reporter mirrors with `config._mcp_reporter_state` if it also needs config-keyed access; otherwise the module-level `_STATE` per RESEARCH.md Pitfall 5 is acceptable.
2. **No-op-when-disabled idiom:** `_plugin.py:253-255` `if cfg is None: return  # silent no-op carry-forward`. Reporter mirrors at every hook entry.

**Collection hook pattern** (`_plugin.py:228-313` for `pytest_collection`):
The existing plugin shows the gating idiom — read stash, defensive `return` on absence, then do work. Reporter's `pytest_collection_finish` uses this shape for both the worker-early-return AND the missing-`_mcp_contracts_config` graceful degrade (RESEARCH.md Pitfall 2 + 3).

**Mark presence read pattern** (`_plugin.py:316-344`):
For filtering `session.items` to `mcp_contract`-marked items, follow the pattern shown there which uses `pytest.mark.mcp_contract` and `item.add_marker(...)`. Reporter reads via `"mcp_contract" in item.keywords` — already validated by RESEARCH.md Don't Hand-Roll table.

---

### `src/mcp_test_framework/_runner.py` — `_build_parsed_run_from_reports` (input adapter, batch transform)

**Analog:** `_runner.py:491` `parse_junit_xml`

**Signature pattern** (`_runner.py:491-510`):
```python
def parse_junit_xml(xml_path: Path) -> ParsedRun:
    """Parse a pytest JUnit XML file into a ``ParsedRun`` domain model.
    ...
    Aggregation (any-fail-wins):
      1. <testcase> with <failure> or <error> child -> verdict = FAIL (sticky)
      2. else passed (no child elements)            -> verdict = PASS unless
                                                       FAIL already set
      3. else <skipped> child                       -> verdict = SKIP if no
                                                       PASS/FAIL set; record
                                                       de-duplicated reason
    ...
    """
```

`_build_parsed_run_from_reports` MUST:
- Live immediately after `parse_junit_xml` in `_runner.py` (D-01a co-location lock).
- Take `reports: list[pytest.TestReport]` and return `ParsedRun`.
- Carry a docstring with the same "Aggregation (any-fail-wins):" enumerated rules — adapted for phase-precedence semantics (RESEARCH.md Pattern 3) since TestReports fire 3× per test.

**Bucket construction pattern** (`_runner.py:540-572`):
```python
for tc in suite.iter("testcase"):
    name = tc.get("name", "")
    tool = _extract_tool_name(name)
    if tool is None:
        # test-code-scope fall-through: testcases under tests/test_code/
        ...
        classname = tc.get("classname", "")
        if (
            classname.startswith("tests.test_code.test_")
            or classname.startswith("tests.sdet.test_")  # noqa: sdet-rename-shim
        ):
            group = classname.rsplit(".", 1)[-1].removeprefix("test_")
            row_label = name.removeprefix("test_")
            tool = f"{group}::{row_label}"
        else:
            continue

    bucket = run.per_tool.setdefault(
        tool, ToolVerdict(name=tool, verdict="PASS")
    )
    bucket.case_count += 1
    try:
        bucket.duration += float(tc.get("time", "0") or "0")
    except (TypeError, ValueError):
        pass
```

Reporter adapter mirror:
- Replace `tc.get("name", "")` with `_extract_tool_name(report.nodeid)` (the same helper — `_extract_tool_name` already handles both nodeid and JUnit name per `_runner.py:391-393` docstring).
- Replace `tc.get("classname", "")` with parsing from `report.nodeid` (which already encodes module path). The fall-through `tests.test_code.test_*` / `tests.sdet.test_*` branch MUST be preserved (Open Question 3 — planner should default to YES given parity intent).
- `case_count` increments ONCE PER TEST, not per phase. Bucket by nodeid first, then iterate buckets (see RESEARCH.md Pitfall 1).
- `bucket.duration += sum(getattr(r, 'duration', 0.0) for r in phases.values())` sums all three phases.

**Failure / property-extraction pattern** (`_runner.py:578-615`):
This is the most important code to mirror exactly. The XML version reads `mcptf_error_code` / `mcptf_error_message` from `<property>` children:
```python
if failure is not None or error is not None:
    bucket.verdict = "FAIL"
    elem = failure if failure is not None else error
    props = tc.find("properties")
    prop_msg: str | None = None
    if props is not None:
        code: str | None = None
        msg_field: str | None = None
        for prop in props.iter("property"):
            n = prop.get("name", "")
            v = prop.get("value", "")
            if n == "mcptf_error_code":
                code = v or None
            elif n == "mcptf_error_message":
                msg_field = v
        if msg_field is not None:
            prop_msg = f"[{code}] {msg_field}" if code else msg_field

    msg = elem.get("message")
    if prop_msg is not None and bucket.failure_message is None:
        bucket.failure_message = prop_msg
    elif msg and bucket.failure_message is None:
        bucket.failure_message = msg
    body = (elem.text or "").strip()
    if body and bucket.failure_body is None:
        bucket.failure_body = body
    continue
```

The TestReport equivalent — iterate `report.user_properties` (list of `(name, value)` tuples) instead of `<property>` children. RESEARCH.md Pitfall 4 gives the explicit translation; the `[{code}] {message}` formatting MUST produce byte-identical strings to the JUnit path so the renderer tests remain valid.

**Skip-reason pattern** (`_runner.py:617-625`):
```python
if skipped is not None:
    reason = _strip_pytest_skipped_prefix(skipped.get("message"))
    if reason and reason not in bucket.skip_reasons:
        bucket.skip_reasons.append(reason)
    if bucket.verdict != "FAIL" and not _has_pass.get(tool, False):
        bucket.verdict = "SKIP"
    continue
```

Mirror with `_strip_pytest_skipped_prefix(getattr(skip_report, "longrepr", ...))` — TestReport's skip reason lives on `report.longrepr` (a 3-tuple `(file, lineno, reason)` for setup/teardown skips, or a `Skipped` exception repr for `pytest.skip()` calls). The `_strip_pytest_skipped_prefix` helper is reusable as-is.

**Totals aggregation pattern** (`_runner.py:527-533`):
JUnit reads totals from the `<testsuite>` attributes:
```python
run = ParsedRun(
    total_time=float(suite.get("time", "0") or "0"),
    total_cases=int(suite.get("tests", "0") or "0"),
    total_failures=int(suite.get("failures", "0") or "0"),
    total_skipped=int(suite.get("skipped", "0") or "0"),
    total_errors=int(suite.get("errors", "0") or "0"),
)
```

TestReport equivalent: compute from the bucketed reports (RESEARCH.md Pattern 3 final section). NOTE the semantic shift — JUnit `total_cases` counts test cases at the suite level; the reporter version counts deduplicated nodeids. Renderer's "Test plan: N contract cases" line will see the same number.

---

### `src/mcp_test_framework/cli.py` (CLI glue, request-response)

**Analog:** existing JUnit-parse block at `cli.py:912-980` (the code being DELETED).

**Block to DELETE** (`cli.py:912-980`):
```python
try:
    # If the subprocess crashed before writing the tempfile, surface a
    # domain-shaped error pointing at --raw for raw pytest output.
    _runner._dispatch_default_mode_or_error(tmp_xml, rc, captured_stderr)

    # JUnit XML parse error -> exit 2 via operator-tone message.
    try:
        parsed = _runner.parse_junit_xml(tmp_xml)
    except ET.ParseError as exc:
        _emit_operator_error(
            summary="JUnit XML parse failed",
            ...
        )

    ctx = _runner.RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered_tools,
        tools_config=cfg.tools,
        judges=judges,
        total_planned_cases=parsed.total_cases,
    )
    if quiet:
        _runner.render_summary_only(parsed, ctx)
    else:
        _runner.render_domain_ui(parsed, ctx)

    if debug:
        _runner.render_debug_appendix(
            captured_stdout, captured_stderr, parsed,
            xml_path=tmp_xml,
        )

    mapped, warning = _runner._map_exit_code(rc)
    if warning is not None:
        typer.echo(warning, err=True)
    raise typer.Exit(code=mapped)
finally:
    if tmp_xml is not None and tmp_xml.exists():
        try:
            tmp_xml.unlink()
        except OSError:
            pass
```

**Planner note (per RESEARCH.md "parse_junit_xml caller audit"):** `--debug` appendix and `render_summary_only` (quiet mode) currently consume `parsed`. Phase 29's CLI rewire MUST decide whether:
- (a) The reporter still renders inside the pytest subprocess and CLI just maps exit codes (`--debug` / `-q` then need to plumb through `--mcp-domain-ui` mode flags OR a second flag).
- (b) Keep parsing in CLI for `--debug` / `-q` paths only and use reporter for the default render path.

This is a planner-resolvable surface; PATTERNS.md notes it but does not lock direction.

**Argv-add pattern** (`_runner.py:144-156` inside `_build_pytest_args`):
```python
if junit_xml is not None:
    args.append(f"--junitxml={junit_xml}")
args.extend(forwarded)
if mcp_config_path is not None:
    args.extend(["-o", f"mcp_config_file={mcp_config_path}"])
return args
```

The new flag is inserted in the SAME pattern — after `forwarded` (so an explicit operator-provided value can override under pytest's last-occurrence rule) OR before (so it's the default). Locked semantics: when CLI runs pytest, argv ends with `--mcp-domain-ui=force`. Cleanest: append unconditionally near the bottom of `_build_pytest_args`. Pattern lift:
```python
args.append("--mcp-domain-ui=force")
```

**CLI exit-code mapping pattern** (`cli.py:971-974`):
```python
mapped, warning = _runner._map_exit_code(rc)
if warning is not None:
    typer.echo(warning, err=True)
raise typer.Exit(code=mapped)
```

This 4-line tail SURVIVES the delete; it's the post-reporter exit path. The block above it (parse + render + debug-appendix) is what goes.

---

### `pyproject.toml` (packaging, config)

**Analog:** existing `[project.entry-points.pytest11]` block at lines 27-32.

**Current state** (lines 27-32):
```toml
[project.entry-points.pytest11]
# Phase 26 D-09 / PACK-01: pytest auto-loads this plugin via the pytest11
# entry-point group. Operators no longer need `pytest_plugins=[...]` in
# their conftest. Module body is created in Plan 26-02; this declaration
# only references it (the wheel-shape gate in 26-04 verifies both halves).
mcp_test_framework = "mcp_test_framework._plugin"
```

**Phase 29 addition** (locked surface):
```toml
[project.entry-points.pytest11]
# Phase 26 D-09 / PACK-01: pytest auto-loads this plugin via the pytest11
# entry-point group. ...
mcp_test_framework = "mcp_test_framework._plugin"
# Phase 29 REPORTER-02: second pytest11 key for the live domain-UI reporter.
# Independently disable-able via `pytest -p no:mcp_test_framework_reporter`
# while keeping the contract fixtures registered under the key above.
mcp_test_framework_reporter = "mcp_test_framework._reporter"
```

The comment style mirrors line 28's "Phase 26 D-09 / PACK-01:" cross-reference convention. No structural change beyond adding one key — Hatchling's wheel build (line 123 `[tool.hatch.build.targets.wheel] packages = ["src/mcp_test_framework"]`) already ships the new module since it's inside the package directory.

---

### `tests/framework/test_reporter.py` (NEW unit tests, request-response)

**No `test_plugin.py` exists** — there is no direct analog for plugin-hook unit tests. The two closest patterns are:

**Analog A:** `tests/framework/unit/test_runner_parser.py` (for the `_build_parsed_run_from_reports` adapter tests)

Header pattern (lines 1-27):
```python
"""Phase 14 Plan 02 unit tests: JUnit XML parser + ported aggregation helpers.

Pins Phase 14 D-02/D-05/D-08/D-09 + Phase 09 D-03 (any-fail-wins) +
Phase 13 D-12 (locked skip-reason constants).
...
"""
from __future__ import annotations

from pathlib import Path
import pytest

from mcp_test_framework._runner import (
    ParsedRun,
    ToolVerdict,
    _REASON_EXPLICIT_DEFAULT,
    _REASON_NOT_SELECTED,
    _SKIP_REASON_CAP,
    _extract_tool_name,
    _format_skip_reasons,
    _strip_pytest_skipped_prefix,
    parse_junit_xml,
)
```

Adapter tests for `_build_parsed_run_from_reports` lift this exact shape — replace the parse_junit_xml import with `_build_parsed_run_from_reports`, replace the XML fixture path with hand-constructed `pytest.TestReport` objects (or `pytest._pytest.reports.TestReport(...)` directly). Each test is a small one-fact assertion (same style as lines 39-99).

**Test case style** (lines 39-50):
```python
def test_runner_skip_reason_constants_locked() -> None:
    """Phase 13 D-12: two reason strings must not drift silently."""
    assert _REASON_NOT_SELECTED == "not selected in config"
    assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"


def test_skip_reason_cap_locked_at_3() -> None:
    """Phase 09 D-05: dedup + cap stays at 3."""
    assert _SKIP_REASON_CAP == 3
```

Reporter tests mirror: short docstring naming the locked decision (D-01 / D-03 / D-04), single assertion per test, no setup overhead.

**Analog B:** `tests/framework/test_phase27_spike_synthetic_module.py` (for plugin-hook integration tests requiring subprocess pytest)

Subprocess-pytest pattern (lines 28-49 + payload-string idiom):
```python
"""...
The spike runs an embedded pytest session via subprocess (not
`pytest.main()` in-process) to isolate plugin state, rootdir, and ini
options from the outer framework test session — pytest registers many
state-bearing singletons that would collide with the outer asyncio
strict-mode framework configuration.
"""
import subprocess
import sys
import textwrap
from pathlib import Path
```

Reporter integration tests (verifying hook firing, option parsing, xdist gating) use this idiom: write a minimal payload `conftest.py` + `test_*.py` to `tmp_path`, spawn `subprocess.run([sys.executable, "-m", "pytest", ...], cwd=tmp_path, ...)`, assert on stdout. Specifically needed for:
- `--mcp-domain-ui` absent → no domain UI in output.
- `--mcp-domain-ui=force` → domain header + summary in output.
- `--mcp-domain-ui=bogus` → exit code 4 (pytest usage error) on `choices` violation.
- (Optional / Open Question 1) `-n 2 --mcp-domain-ui=force` with pytest-xdist installed → header emitted exactly once.

---

## Shared Patterns

### Plugin hook idiom (apply to ALL reporter hooks)
**Source:** `src/mcp_test_framework/_plugin.py:127-203, 253-255, 316-344`
**Apply to:** every hook in `_reporter.py`

```python
def pytest_<hook>(...):
    """Short docstring naming Responsibilities: ... bullet list."""
    state = getattr(<container>, "_mcp_reporter_state", None)
    if state is None or not state.enabled:
        return  # silent no-op carry-forward
    # ... actual work
```

Two project-locked rules:
1. Every hook starts with a defensive `getattr` for its dependency and early-returns on absence.
2. Docstrings list the responsibilities as a bulleted "Responsibilities:" block (matches `_plugin.py:131-141`).

### Error handling / fail-loud pattern
**Source:** `src/mcp_test_framework/_plugin.py:169-196` (`pytest.exit(...)` with operator-tone "next:" guidance)
**Apply to:** ANY new fail-loud path in `_reporter.py` (likely: none for Phase 29 — the reporter degrades gracefully per Pitfall 2; no exit paths).

The reporter's only "failure" modes are silent graceful degrades (missing config -> skip header; worker -> no-op). If a planner adds a fail-loud (e.g., RenderContext construction blows up), use `pytest.exit("<one-line summary>\n\nnext: <actionable hint>", returncode=2)` per `_plugin.py:170-176` template.

### Comment-anchor style for phase cross-references
**Source:** `pyproject.toml:28`, `_plugin.py:127`, `_runner.py:380-385`
**Apply to:** ALL new code in this phase

Format: `# Phase 29 D-NN / REPORTER-NN: <one-line rationale>`. Visible in `_plugin.py:127` (`# Phase 26 D-09 / PACK-01`), `_runner.py:380-385` (multi-line phase-bound constant pin), `pyproject.toml:28-31` (multi-line block-level explainer).

### `# noqa: sdet-rename-shim` markers
**Source:** `_plugin.py` shows `# noqa: sdet-rename-shim` on every `sdet`/`tests/sdet` mention (e.g., line 86, 105, 107, 109, 111, 113-115)
**Apply to:** ANY mention in `_reporter.py` of test-code scenario fall-through that references `tests.sdet.*`

Only relevant if the planner answers Open Question 3 as "yes, replicate scenario fall-through." If so, the `_build_parsed_run_from_reports` branch that mirrors `_runner.py:557` `classname.startswith("tests.sdet.test_")` MUST carry the `# noqa: sdet-rename-shim` marker for parity with the JUnit path.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `tests/framework/test_reporter.py` (full plugin integration) | pytest plugin integration test | request-response | No prior `test_plugin*.py` integration test for `_plugin.py` exists. The framework's plugin behavior is tested IMPLICITLY by the rest of `tests/contract/` running through the auto-loaded plugin. | Use the **subprocess-pytest** pattern from `tests/framework/test_phase27_spike_synthetic_module.py` (lines 36-49 + payload strings) for hook-firing tests; use **adapter unit-test style** from `tests/framework/unit/test_runner_parser.py` for `_build_parsed_run_from_reports` data tests. |

---

## Metadata

**Analog search scope:** `src/mcp_test_framework/`, `tests/framework/`, `pyproject.toml`
**Files scanned:** 8 (cli.py, _plugin.py, _runner.py, _black_box_guard.py search, pyproject.toml, test_runner_parser.py, test_phase27_spike_synthetic_module.py, fixtures.py via _plugin.py imports)
**Pattern extraction date:** 2026-05-17
**Pattern confidence:** HIGH — `_plugin.py` is a direct sibling-shape analog; `parse_junit_xml` is an output-shape-identical adapter analog; the renderer's `RenderContext` and `ParsedRun` shapes are frozen and consumed verbatim per D-01.
