# Phase 14: Hybrid runner with domain UI - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 7 (3 created, 3 modified, 1 deleted-but-ported)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_runner.py` (new — subprocess + parse + render) | runner/module | request-response (subprocess + file I/O + transform) | `src/mcp_test_framework/_reporter.py` (aggregation/render); `src/mcp_test_framework/cli.py:296-376` (subprocess argv build + typer.Exit dispatch) | role-match (composed) — no existing analog combines subprocess+XML-parse+render; closest single-concern analogs are reporter (render) and `_build_pytest_args` + `run` (subprocess dispatch) |
| `src/mcp_test_framework/cli.py:run` (322-376) — MODIFIED | controller/Typer-command | request-response | Itself (current `run` shape) + `cli.py:list_tools` (multi-phase command with try/except wrapping subprocess-like work) | exact (rewrite-in-place) |
| `tests/conftest.py` — MODIFIED (drop `_reporter` registration) | config/test-bootstrap | configuration | `tests/conftest.py:15` (current line; single-line edit) | exact |
| `tests/test_runner.py` and/or `tests/test_renderer.py` (new — unit tests against XML fixtures) | test | file-I/O + transform | `tests/unit/test_reporter.py` (pure-data unit tests under tests/unit/, no preflight); `tests/test_reporter.py` lines 41-69, 270-417 (FakeTerminal, fixture-driven verdict-aggregation tests) | exact (port + retarget) |
| `tests/fixtures/junit-*.xml` (new — small set of canned XMLs) | test-fixture | data | (no analog — first XML fixtures in repo); pytest's own JUnit dialect documented inline in `tests/test_reporter.py:456-528` | no analog (greenfield) |
| `src/mcp_test_framework/_reporter.py` — DELETED (after porting Phase 09 D-03/D-05/CD-03 + Phase 13 D-12 into `_runner.py`) | (deleted) | n/a | n/a — the file itself IS the pattern source for the new renderer | n/a |
| `tests/test_reporter.py` — DELETE or retarget (replace live `_run_framework_subprocess` cases with renderer tests over XML fixtures) | test | file-I/O + transform | Same file's own unit-level half (lines 41-417) is the pattern; the live-homelab half (lines 419-552) collapses into a single `test_runner.py::test_subprocess_returns_xml` once Phase 14 owns the subprocess dispatch | role-match |

## Pattern Assignments

### `src/mcp_test_framework/_runner.py` (new — subprocess + JUnit parse + render)

This new module composes three concerns. Each has a distinct analog.

#### Concern A: subprocess pytest dispatch + tempfile JUnit + exit-code mapping

**Analog:** `src/mcp_test_framework/cli.py:322-376` (the current `run` command)

**Subprocess + typer.Exit pattern** (cli.py:373-376) — the single-line dispatch shape Phase 14 is replacing:
```python
import pytest  # function-local: pytest is dev-only, not a runtime dep

_load_config(config)  # raises typer.Exit(2) on any unrecoverable error
raise typer.Exit(code=pytest.main(_build_pytest_args(junit_xml, pytest_args)))
```

**Argv builder pattern** (cli.py:296-319) — reused verbatim; the new runner wraps this:
```python
def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
) -> list[str]:
    forwarded = list(pytest_args or [])
    args: list[str] = ["tests"]
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    return args
```

**Operator-tone error pattern** (cli.py:71-98) — reused for D-16 "JUnit XML parse failed" and "pytest exited without producing JUnit XML":
```python
def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)
```

**Reference for subprocess + tempfile + parse flow** — closest pattern in tests for actually invoking pytest via subprocess and parsing its JUnit XML is `tests/test_reporter.py:424-485`:
```python
def _run_framework_subprocess(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "mcp-test-framework", "run", *args, "--", "-m", "live_homelab"],
        cwd=cwd, capture_output=True, text=True, check=False,
    )

# ...
proc = _run_framework_subprocess(f"--junit-xml={target}", cwd=repo_root)
assert target.exists(), ...
tree = ET.parse(target)
root = tree.getroot()
assert root.tag in {"testsuites", "testsuite"}, root.tag
```

The Phase 14 production code uses `[sys.executable, "-m", "pytest", ...]` rather than `uv run mcp-test-framework run` to avoid recursion. The `ET.parse` + `root.iter("testcase")` patterns are the right ElementTree shape (used inside `tests/test_reporter.py:512-521`).

#### Concern B: per-tool aggregation algorithm (Phase 09 D-03 any-fail-wins / D-05 dedup+cap / CD-03 ordering)

**Analog:** `src/mcp_test_framework/_reporter.py` (the file being deleted — port its algorithm into `_runner.py` first)

**Tool-name extraction from parametrize-suffix** (_reporter.py:74-84) — port verbatim, swap nodeid input for JUnit `<testcase>` `name` attribute:
```python
def _extract_tool_name(nodeid: str) -> str | None:
    """Return tool name from ``<file>::<test>[<tool>]`` nodeid, or None."""
    if "[" not in nodeid or not nodeid.endswith("]"):
        return None
    return nodeid[nodeid.rindex("[") + 1 : -1]
```

Note: pytest's JUnit writer puts the `[<tool>]` suffix on the `<testcase name="...">` attribute (see `tests/test_reporter.py:489-528` which pins this). The new module reads `tc.get("name", "")` instead of `report.nodeid`, but the bracket-suffix grammar is identical.

**Any-fail-wins verdict aggregation** (_reporter.py:108-148) — port the three-rule algorithm; replace `report.failed` / `report.outcome` with JUnit-element-presence checks (`<failure>` / `<error>` / `<skipped>` children):
```python
# D-03 rule 1: any failed/error -> FAIL (sticky).
if report.failed:  # in XML: tc.find("failure") is not None OR tc.find("error") is not None
    bucket["verdict"] = "FAIL"
    return
if report.outcome == "passed":  # in XML: no failure/error/skipped children
    if bucket["verdict"] != "FAIL":
        bucket["verdict"] = "PASS"
    return
if report.outcome == "skipped":  # in XML: tc.find("skipped") is not None
    reason = _extract_skip_reason(report.longrepr)
    if reason is not None and reason not in bucket["reasons"]:
        bucket["reasons"].append(reason)
    if bucket["verdict"] is None:
        bucket["verdict"] = "SKIP"
    return
```

**Skip-reason extraction** (_reporter.py:87-105) — port; in XML the skip reason is `<skipped message="…">…</skipped>` (use the `message` attribute, falling back to text):
```python
def _extract_skip_reason(longrepr) -> str | None:
    if isinstance(longrepr, tuple) and len(longrepr) >= 3:
        reason = longrepr[2]
        if isinstance(reason, str):
            prefix = "Skipped: "
            return reason[len(prefix):] if reason.startswith(prefix) else reason
    return None
```

In the new XML path: `tc.find("skipped").get("message")` then strip the `"Skipped: "` prefix the same way.

**Skip-reason de-dup + cap (D-05)** (_reporter.py:151-167) — port verbatim:
```python
_SKIP_REASON_CAP: int = 3

def _format_skip_reasons(reasons: list[str]) -> str:
    if not reasons:
        return ""
    if len(reasons) <= _SKIP_REASON_CAP:
        return "; ".join(reasons)
    head = "; ".join(reasons[:_SKIP_REASON_CAP])
    return f"{head}; ... ({len(reasons) - _SKIP_REASON_CAP} more)"
```

**Phase 13 D-12 locked skip-reason constants** (_reporter.py:62-63) — port verbatim; `tests/unit/test_reporter.py:82-89` pins these strings:
```python
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default
```

**State-a/state-c skip row composition** (_reporter.py:170-203) — port; the new runner constructs `Config()` itself (same pattern as `_reporter.pytest_terminal_summary:229-240`) since `MCPTF_CONFIG_FILE` flows in via Phase 13 D-03 environment export at `cli.py:289`:
```python
def _compose_unparametrized_skips(config) -> dict[str, str]:
    discovered = _DISCOVERED_TOOL_NAMES
    if not discovered:
        return {}
    tools_cfg = getattr(config, "tools", {}) or {}
    result: dict[str, str] = {}
    for name in discovered:
        if name in _PER_TOOL:
            continue
        cfg_entry = tools_cfg.get(name)
        if cfg_entry is not None and getattr(cfg_entry, "skip", False):
            reason = (getattr(cfg_entry, "skip_reason", "") or "").strip()
            result[name] = reason or _REASON_EXPLICIT_DEFAULT
        else:
            result[name] = _REASON_NOT_SELECTED
    return result
```

**IMPORTANT — discovery cache source change:** In v1.1/v1.2 the cache `_DISCOVERED_TOOL_NAMES` was written by `tests/conftest.py:_resolve_tool_names` and lived on `_reporter`. In Phase 14, the wrapper runs OUTSIDE the pytest process, so it cannot read that cache. Phase 14 options (resolve in PLAN):
- (a) re-run discovery in the wrapper before launching pytest (one extra subprocess; identical to `list-tools`), OR
- (b) compute the unparametrized-skips set in the wrapper directly from `Config.tools` (no discovery needed — the operator's allowlist IS the source of truth for state-c, and state-a names are whatever appeared in the JUnit XML as parametrize IDs… no, state-a is the set discovered-but-unlisted; needs discovery).
The discretion note in CONTEXT D-claude bullet 5 calls this out.

#### Concern C: row ordering + render (Phase 09 CD-03 + Phase 14 D-06 stdlib renderer)

**Analog:** `src/mcp_test_framework/_reporter.py:206-284` (the `pytest_terminal_summary` body)

**FAIL → SKIP → PASS alphabetical ordering** (_reporter.py:248-282):
```python
fails = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "FAIL")
skips = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "SKIP")
passes = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "PASS")

all_names = list(_PER_TOOL.keys()) + list(unparam_skips.keys())
name_width = max((len(n) for n in all_names), default=0)

if fails:
    terminalreporter.write_line("failures:")
    for tool in fails:
        terminalreporter.write_line(f"  {tool.ljust(name_width)}  FAIL")
# ... SKIP block with em-dash separator ...
all_skips = sorted(set(skips) | set(unparam_skips.keys()))
if all_skips:
    terminalreporter.write_line("skipped:")
    for tool in all_skips:
        if tool in _PER_TOOL and _PER_TOOL[tool]["verdict"] == "SKIP":
            reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
        else:
            reasons_text = unparam_skips[tool]
        if reasons_text:
            terminalreporter.write_line(
                f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"  # U+2014 em-dash
            )
        else:
            terminalreporter.write_line(f"  {tool.ljust(name_width)}  SKIP")
```

**Render channel change for Phase 14:** swap `terminalreporter.write_line(...)` / `write_sep(...)` for plain `print(...)` (or `sys.stdout.write(...)`) — Phase 14 D-06: "the new renderer uses plain print/sys.stdout.write since it owns the output channel entirely." ANSI color codes guarded by `sys.stdout.isatty()`.

**Em-dash separator:** `—` (U+2014, not ASCII hyphen). Locked at Phase 09 SC-3 and re-pinned at `tests/test_reporter.py:391-417`.

**Header rendering** — no existing analog. Phase 14 ships the SEED-011 §2 mockup verbatim. Suggested structure (per CONTEXT specifics):
```python
def _render_header(server_cmd, discovered, running, skipping, judges, total_cases) -> None:
    print("=" * 40)
    print("MCP Test Framework")
    print("=" * 40)
    print(f"MCP server:  {server_cmd}")
    print(f"Discovered:  {discovered} tools")
    print(f"Running:     {len(running):>2}  ({', '.join(running)})")
    print(f"Skipping:    {len(skipping):>2}  (use --explain to list)")
    print(f"Judges:      {', '.join(judges)}")
    print(f"Test plan:   {total_cases} contract cases")
```

**Summary line** — derived from JUnit `<testsuite time="…">` attribute (or wall-clock around the subprocess call):
```python
print(f"Result: {n_pass} PASS / {n_fail} FAIL  in {duration:.1f}s")
```

---

### `src/mcp_test_framework/cli.py:run` (MODIFIED — 322-376)

**Analog:** Itself + `cli.py:list_tools` (379-471) for the "command with multi-phase work + KeyboardInterrupt + FileNotFoundError handling" shape.

**Pre-flight gate pattern** (cli.py:375) — preserved verbatim on both default and `--raw` paths (D-03, D-11):
```python
_load_config(config)  # raises typer.Exit(2) on any unrecoverable error
```

**Typer command shape with passthrough** (cli.py:322-348) — keep `pytest_args` and `--junit-xml` as-is; ADD `--raw`, `--debug`, `-q` flags:
```python
@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def run(
    config: Path | None = typer.Option(None, "--config", help="..."),
    junit_xml: Path | None = typer.Option(None, "--junit-xml", help="..."),
    raw: bool = typer.Option(False, "--raw", help="..."),
    debug: bool = typer.Option(False, "--debug", help="..."),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="..."),
    pytest_args: list[str] | None = typer.Argument(None, help="..."),
) -> None:
```

**KeyboardInterrupt → exit 130 pattern** (cli.py:434-440) — reuse if the wrapper catches it directly; otherwise the subprocess propagates naturally (Phase 04.1 pattern + Phase 14 D-15):
```python
except KeyboardInterrupt:
    # Click's default standalone_mode would convert to exit 1; explicit
    # typer.Exit(130) makes the SIGINT contract uniform across platforms.
    raise typer.Exit(code=130)
```

**Exit-code mapping pattern** (cli.py:376) — last line of the command; bare `raise typer.Exit(code=...)`. Phase 14 maps `5 → 0 with warning` (D-15) inline.

---

### `tests/conftest.py` (MODIFIED — single-line edit)

**Analog:** Itself, line 15.

**Current line to edit** (tests/conftest.py:15):
```python
pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]
```

**After Phase 14:**
```python
pytest_plugins = ["mcp_test_framework.fixtures"]
```

Also delete the `from mcp_test_framework import _reporter as _rep` import at line 22 and update the `_resolve_tool_names` function (lines 90-145) to no longer reference `_rep._DISCOVERED_TOOL_NAMES`. **Resolution caveat:** since the wrapper runs outside pytest, the discovery-cache pattern needs to either (a) move into a runner-side discovery call, or (b) be re-derived from `Config.tools` keys. Plan-phase decides per CONTEXT D-claude bullet 5.

---

### `tests/test_runner.py` and/or `tests/test_renderer.py` (NEW)

**Analog:** `tests/unit/test_reporter.py` (the pure-data half — runs without preflight) + `tests/test_reporter.py:41-417` (FakeTerminal pattern + verdict-aggregation tests).

**SimpleNamespace duck-typed report pattern** (test_reporter.py:41-55) — adapt for XML-element-derived report dicts:
```python
def _make_report(nodeid, outcome, *, when="call", failed=False, longrepr=None):
    return SimpleNamespace(
        nodeid=nodeid, outcome=outcome, when=when, failed=failed, longrepr=longrepr,
    )
```

For Phase 14 these become small dicts built from `<testcase>` elements OR XML fixture files loaded via `ET.parse`. The Phase 14 equivalent uses real ElementTree elements:
```python
def _parse_fixture(name: str) -> ET.Element:
    fixture_path = Path(__file__).parent / "fixtures" / name
    return ET.parse(fixture_path).getroot()
```

**FakeTerminal capture pattern** (test_reporter.py:270-282) — replace with capsys for plain print:
```python
def test_renderer_emits_pass_row(capsys) -> None:
    render([...])  # new runner's render entry point
    out = capsys.readouterr().out
    assert "tool_x" in out and "PASS" in out
```

**Module-level state reset fixture** (test_reporter.py:58-68) — reuse if `_runner.py` keeps `_PER_TOOL` module-level (it should, matching the existing pattern):
```python
@pytest.fixture(autouse=True)
def _reset_per_tool_buffer():
    _runner._PER_TOOL.clear()
    yield
    _runner._PER_TOOL.clear()
```

**Constants regression-pin pattern** (tests/unit/test_reporter.py:82-89) — port verbatim against the new module:
```python
def test_runner_skip_reason_constants_locked() -> None:
    from mcp_test_framework._runner import (
        _REASON_EXPLICIT_DEFAULT, _REASON_NOT_SELECTED,
    )
    assert _REASON_NOT_SELECTED == "not selected in config"
    assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"
```

**Row ordering test pattern** (test_reporter.py:305-365) — adapt to feed XML fixtures rather than `_make_report` calls. Single XML fixture `junit-mixed.xml` with cases `[zoo]` failed, `[alpha]` failed, `[gamma]` skipped, `[mango]` passed exercises CD-03 ordering exactly.

**CliRunner pattern for top-level `run --help`** (test_config_init_cli.py:22-39) — reuse to assert `--raw`, `--debug`, `-q` appear in help:
```python
def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))

def test_run_help_lists_new_flags() -> None:
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--raw" in result.output
    assert "--debug" in result.output
    assert "-q" in result.output or "--quiet" in result.output
```

---

### `tests/fixtures/junit-*.xml` (NEW)

**No existing analog** — these are the first canned XML fixtures in the repo. Reference for the pytest JUnit XML dialect lives at `tests/test_reporter.py:456-528` (which round-trip-parses a live-generated XML via `ET.parse`).

Suggested fixture set (per CONTEXT D-claude bullet 4):
- `junit-all-pass.xml` — single `<testsuite>` with N `<testcase name="test_x[tool_a]" .../>` no children
- `junit-one-fail-with-reasoning.xml` — one `<testcase>` containing `<failure message="parameters 3/5: 'unclear param name'">…</failure>`
- `junit-all-skip.xml` — every `<testcase>` carries `<skipped message="Skipped: not selected in config"/>`
- `junit-mixed.xml` — mix of fail/skip/pass cases including alpha-ordering test cases (`[alpha]`, `[zoo]`, `[gamma]`, `[mango]`)

Minimal pytest JUnit shape (verified against pytest 9.x default `--junitxml` output):
```xml
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4" failures="1" skipped="1" errors="0" time="8.34">
    <testcase classname="tests.test_x" name="test_schema[alpha]" time="0.10"/>
    <testcase classname="tests.test_x" name="test_schema[zoo]" time="0.20">
      <failure message="parameters 3/5: 'unclear'">long traceback body...</failure>
    </testcase>
    <testcase classname="tests.test_x" name="test_schema[gamma]" time="0.05">
      <skipped message="Skipped: not selected in config" type="pytest.skip"/>
    </testcase>
    <testcase classname="tests.test_x" name="test_schema[mango]" time="0.15"/>
  </testsuite>
</testsuites>
```

Phase 14 plan can generate these once via a live `mcp-test-framework run --junit-xml=tests/fixtures/junit-mixed.xml` invocation and check them in, OR hand-write minimal shapes. Hand-writing is preferred for stability — live regeneration drifts when test counts change.

---

### `src/mcp_test_framework/_reporter.py` (DELETED)

No analog needed — this is the source the new renderer ports from. Order of operations per CONTEXT D-claude bullet 1:
1. Build new `_runner.py` with ported logic.
2. Verify renderer tests pass against XML fixtures.
3. Delete `_reporter.py`.
4. Delete `_reporter` from `tests/conftest.py:15` `pytest_plugins`.
5. Retarget `tests/test_reporter.py` (or delete and replace with `tests/test_runner.py` + `tests/test_renderer.py`).

---

### `tests/test_reporter.py` (DELETE/RETARGET)

**Analog:** Itself — the unit-level half (lines 41-417) is the template for the new renderer tests; the live-homelab half (lines 419-552) collapses into a single integration smoke that exercises subprocess + parse end-to-end.

Plan-phase decides whether to:
- Delete entirely and rebuild as `tests/test_runner.py` + `tests/test_renderer.py`, OR
- `git mv tests/test_reporter.py tests/test_renderer.py` and rewrite in place to preserve git blame on the ported assertions.

Recommend the second — the unit-level assertions (verdict aggregation, em-dash separator regression-pin, skip-reason cap, FAIL→SKIP→PASS ordering) are all directly portable.

The Phase 13 unit tests in `tests/unit/test_reporter.py` (which import `from mcp_test_framework import _reporter as _rep`) also need to `git mv` to `tests/unit/test_runner.py` and re-target their imports to `mcp_test_framework._runner`. All 7 test functions port one-to-one.

---

## Shared Patterns

### Pre-flight config gate (must run BEFORE pytest in both default and --raw modes)

**Source:** `src/mcp_test_framework/cli.py:191-293` (`_load_config`) — Phase 13 D-01/D-03; do not duplicate or re-implement.

**Apply to:** `src/mcp_test_framework/cli.py:run` (both `--raw` and default branches).

**Reuse shape (Phase 14 D-03 + D-11):**
```python
_load_config(config)  # raises typer.Exit(2) on any unrecoverable error.
                      # Side-effect: sets os.environ["MCPTF_CONFIG_FILE"] so
                      # the in-subprocess pytest session's bare Config()
                      # picks up the same resolved YAML (cli.py:289).
```

### Operator-tone error emission

**Source:** `src/mcp_test_framework/cli.py:71-98` (`_emit_operator_error`)

**Apply to:** `_runner.py` for D-16 sites:
- "pytest exited without producing a JUnit XML"
- "JUnit XML parse failed"

```python
_emit_operator_error(
    summary="pytest exited without producing a JUnit XML",
    detail=[
        "the test runner crashed before writing its results file.",
        "this usually means a collection error or a fixture-setup failure.",
    ],
    next_step="re-run with `--debug` to see the raw pytest output, or `--raw` to bypass the wrapper",
)
```

### Em-dash separator (U+2014, NOT ASCII hyphen)

**Source:** `src/mcp_test_framework/_reporter.py:275` and pinned at `tests/test_reporter.py:391-417`.

**Apply to:** every SKIP and FAIL detail row in the new renderer:
```python
f"{tool}  SKIP — {reason}"   # U+2014, literal em-dash character
f"{tool}  FAIL  (parameters 3/5: \"{reason}\")"   # per SEED-011 §2
```

### Parametrize-ID `[<tool_name>]` extraction

**Source:** `src/mcp_test_framework/_reporter.py:74-84`

**Apply to:** every site that reads a `<testcase name="...">` and needs the per-tool grouping key. Phase 14 D-09 + CONTEXT D-claude bullet 6 flag this as a candidate for a shared helper used by both renderer and any future parametrize-suffix consumer.

### Subprocess + JUnit XML round-trip pattern

**Source:** `tests/test_reporter.py:424-485` (live `subprocess.run` + `ET.parse`)

**Apply to:** `_runner.py`'s top-level dispatch and `tests/test_runner.py`'s integration smoke. The production code swaps `["uv", "run", "mcp-test-framework", "run", ...]` for `[sys.executable, "-m", "pytest", "tests", "--junitxml=<tempfile>"]` to avoid recursion.

### Module-level state reset in renderer tests

**Source:** `tests/test_reporter.py:58-68` (`_reset_per_tool_buffer` autouse fixture)

**Apply to:** all renderer-tests if the new `_runner.py` keeps `_PER_TOOL` as module-level state (it should — matches the existing pattern; pytest re-imports plugins once per session, but unit tests run many scenarios in one session).

---

## No Analog Found

| File | Role | Data Flow | Reason | Fallback |
|------|------|-----------|--------|----------|
| `tests/fixtures/junit-*.xml` | test-fixture (data) | n/a | First XML fixtures in the repo | Hand-write minimal shape per the inline reference at `tests/test_reporter.py:456-528`; or generate once via live run and commit |
| Header section of `_runner.py` renderer | renderer (presentation) | n/a | No existing pre-run header surface exists (`_reporter.py` is post-run only) | Follow SEED-011 §2 mockup verbatim per CONTEXT specifics |
| `--debug` post-UI raw-output dump | renderer (presentation) | n/a | No existing "append raw pytest stdout after summary" pattern | Plain string append per D-13: `--- raw pytest output ---` separator, then captured stdout, then any `<failure>` longrepr bodies |
| `--explain` flag hook | controller (Typer option) | n/a | D-14 defers the flag itself to Phase 16; Phase 14 only ships the literal "use --explain to list" hint string | Render the hint string verbatim per CONTEXT specifics; do NOT register the flag in Typer (per D-14 recommendation) |

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/*.py` (cli.py, _reporter.py, fixtures.py, config.py)
- `tests/*.py` and `tests/unit/*.py` (test_reporter.py, unit/test_reporter.py, test_config_init_cli.py, test_tool_config.py, conftest.py)

**Files scanned:** ~30 (5 production modules + 25 test modules)

**Strong-match analogs:** 3 (cli.py:run, _reporter.py, tests/test_reporter.py)
**Role-match analogs:** 4 (cli.py:list_tools, _build_pytest_args, _emit_operator_error, tests/unit/test_reporter.py)

**Pattern extraction date:** 2026-05-10
