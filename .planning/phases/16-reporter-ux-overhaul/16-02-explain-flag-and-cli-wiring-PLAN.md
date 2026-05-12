---
phase: 16-reporter-ux-overhaul
plan: 02
type: execute
wave: 2
depends_on:
  - 16-01
files_modified:
  - src/mcp_test_framework/cli.py
  - tests/framework/unit/test_runner_pre_run_digest.py
  - tests/framework/unit/test_runner_explain.py
  - tests/framework/test_runner_verbosity.py
autonomous: true
requirements:
  - UX-01
  - UX-02
  - UX-04
  - UX-05
must_haves:
  truths:
    - "Running `mcp-test-framework run --help` lists `--explain` with help text mentioning --raw and -q interactions."
    - "Running `mcp-test-framework run` (default mode) emits the pre-run digest BEFORE pytest's subprocess starts, and the post-run output (per-tool rows + summary) does NOT include a second banner."
    - "Running `mcp-test-framework run --explain` emits the digest, then a `Skipping (N):` block with one alphabetized line per skipped tool, then pytest output, then post-run rows + summary."
    - "Running `mcp-test-framework run -q` suppresses BOTH the pre-run digest AND `--explain` expansion; output is exactly one line (`Result: ...`)."
    - "Running `mcp-test-framework run --raw` bypasses the digest and explain (existing --raw short-circuit at cli.py:470 is unchanged)."
    - "Running `mcp-test-framework run --with-framework` emits the digest with Test plan line annotated as `Test plan:   N contract cases + framework self-tests`."
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "--explain Typer flag registered between --with-framework and pytest_args; pre-run digest + explain calls inserted between discovery and subprocess; quiet gating applies to both"
      contains: "explain: bool = typer.Option"
      contains_also: ["_render_pre_run_digest", "_render_skipped_tools_explain"]
    - path: "tests/framework/unit/test_runner_pre_run_digest.py"
      provides: "renderer-shape regression tests + CASES_PER_CONTRACT_TOOL constant pin + AST-counted parametrize match"
      min_lines: 80
    - path: "tests/framework/unit/test_runner_explain.py"
      provides: "--explain end-to-end tests covering sort order + composition with -q / --raw / --with-framework"
      min_lines: 80
    - path: "tests/framework/test_runner_verbosity.py"
      provides: "extended with `-q` one-line parity test + `-q --explain` no-op test; Phase 14 negative test test_run_help_does_not_list_explain INVERTED (now asserts --explain IS in help)"
  key_links:
    - from: "cli.py:run"
      to: "_runner._render_pre_run_digest(ctx)"
      via: "direct call AFTER discovery + RenderContext build AND BEFORE run_pytest_subprocess; gated on `not quiet`"
      pattern: "if not quiet:\\s*\\n\\s*_runner\\._render_pre_run_digest"
    - from: "cli.py:run"
      to: "_runner._render_skipped_tools_explain(ctx)"
      via: "direct call AFTER pre-run digest; gated on `not quiet and explain`"
      pattern: "if explain:\\s*\\n\\s*_runner\\._render_skipped_tools_explain"
    - from: "tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count"
      to: "tests/contract/test_mcp_tool_contract.py"
      via: "ast.parse + filter test_* funcs; asserts len == CASES_PER_CONTRACT_TOOL"
      pattern: "ast\\.parse"
---

<scope_note>
REVISION (checker WARNING 6): scope was reviewed and accepted at 4 tasks / 4 files because the cli.py wiring + its three test surfaces (new unit tests for the digest, new end-to-end tests for --explain, and the inverted Phase 14 negative test in test_runner_verbosity.py) must land atomically — `--explain` cannot ship without the test pinning, and the Phase 14 negative test fails the moment the flag is registered. Splitting would break atomicity and create a known-broken intermediate state.
</scope_note>

<objective>
Wire Plan 01's renderer additions through the Typer CLI and add the test surface that pins every Phase 16 invariant.

Three deliverables:
1. **`--explain` Typer flag** in `cli.py:run` (D-07, registered after `--with-framework` per D-08), owned by the wrapper (NEVER forwarded to pytest).
2. **Pre-run rendering pipeline:** RenderContext build moves before the subprocess; `_render_pre_run_digest(ctx)` + optional `_render_skipped_tools_explain(ctx)` fire between discovery and `run_pytest_subprocess`, both gated on `not quiet` (D-09).
3. **Test suite** pinning: (a) digest shape at small N and N=70 (D-12); (b) CASES_PER_CONTRACT_TOOL locked + AST-matched against `tests/contract/test_mcp_tool_contract.py` parametrize count (D-03); (c) `--explain` sort order + format + composition with `--raw`/`-q`/`--with-framework` (D-08); (d) `-q` parity (D-09 / UX-05); (e) Phase 14's `test_run_help_does_not_list_explain` INVERTED to assert `--explain` is now in help.

Purpose: Operator-facing UX overhaul lands here. After this plan ships, `mcp-test-framework run` prints the domain-shaped digest by default and `--explain` works end-to-end.

Output: Modified `cli.py`, two new test files, one extended test file.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md
@.planning/phases/16-reporter-ux-overhaul/16-PATTERNS.md
@.planning/phases/16-reporter-ux-overhaul/16-01-pre-run-digest-renderer-PLAN.md

<interfaces>
<!-- Symbols from Plan 01 (new in _runner.py, ready to import). -->
<!-- Locked Typer flag idiom from cli.py:394–403 (--with-framework). -->

From src/mcp_test_framework/_runner.py (Plan 01 output):
```python
CASES_PER_CONTRACT_TOOL: int = 10

def _compose_pre_run_skip_reasons(discovered_tools: list[str], tools_config: dict) -> dict[str, str]: ...
def _render_pre_run_digest(ctx: RenderContext, file=None) -> None: ...
def _render_skipped_tools_explain(ctx: RenderContext, file=None) -> None: ...
# render_domain_ui no longer calls _render_header
```

From src/mcp_test_framework/cli.py (current run signature; --explain inserts AFTER with_framework at line 403):
```python
def run(
    config: Path | None = typer.Option(None, ...),
    junit_xml: Path | None = typer.Option(None, ...),
    raw: bool = typer.Option(False, "--raw", ...),
    debug: bool = typer.Option(False, "--debug", ...),
    quiet: bool = typer.Option(False, "-q", "--quiet", ...),
    with_framework: bool = typer.Option(False, "--with-framework", ...),
    # <-- INSERT --explain HERE -->
    pytest_args: list[str] | None = typer.Argument(None, ...),
) -> None:
```

Current flow inside `run` (lines 466–560; key insertion points):
- Line 466: `cfg = _load_config(config)` (pre-flight gate; --raw also gated here)
- Lines 470–484: `--raw` short-circuit (DO NOT TOUCH — composition rule D-08 enforced by ordering)
- Line 490: `discovered_tools = _discover_tools_for_run(cfg)`  ← keep here
- Line 492: `rc, tmp_xml, captured_stdout, captured_stderr = _runner.run_pytest_subprocess(...)` ← move RenderContext build BEFORE this and inject digest/explain
- Lines 522–538: RenderContext construction (currently AFTER subprocess) — move BEFORE subprocess. `total_planned_cases` field stays as `parsed.total_cases` post-run (set in a second-pass assignment after parsing, OR field stays 0 pre-run since the digest computes from running×constant, not from this field).
- Lines 545–548: existing `if quiet: render_summary_only else: render_domain_ui` block — UNCHANGED structurally. `render_domain_ui` now silently emits only rows+summary (per Plan 01's call-site removal).

Test analog patterns (from tests/framework/test_runner_verbosity.py):
```python
# _invoke / CliRunner pattern (test_runner_verbosity.py:131–145)
def _invoke(*args: str) -> Result:
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app
    return CliRunner().invoke(app, list(args))

# _stub_subprocess_writing_xml (test_runner_verbosity.py:154–168)
def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")
    def _fake(argv, **kwargs):
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        return SimpleNamespace(returncode=returncode, stdout="...", stderr="", args=argv)
    return _fake

# _make_valid_config (test_runner_verbosity.py:170–180) — copy/import as-is
```

Fixtures path (from tests/framework/unit/test_runner_parser.py:31):
```python
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
```

Locked skip-reason constants the explain output MUST surface verbatim:
```python
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted in tools_config
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): tools_config[t].skip is True
```
(Operator-overridden `skip_reason: "<custom>"` takes precedence over the state-(c) default per `_compose_unparametrized_skips_from_config` lines 588–591.)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Register --explain Typer flag and rewire run() to render digest pre-subprocess</name>
  <files>src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py (lines 343–566 — the entire `run` Typer command)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-01, D-06, D-07, D-08, D-09
    - .planning/phases/16-reporter-ux-overhaul/16-PATTERNS.md (Typer flag declaration idiom + Quiet-mode gating idiom blocks)
  </read_first>
  <behavior>
    - `mcp-test-framework run --help` exits 0 and stdout contains `--explain` and the help text mentions both `--raw` and `-q`.
    - `mcp-test-framework run` (no flags) emits the digest BEFORE pytest subprocess output; post-run output (per-tool rows + summary) does not contain a second `MCP Test Framework` banner.
    - `mcp-test-framework run --explain` emits digest + `Skipping (N):` block + pytest output + per-tool rows + summary, in that order.
    - `mcp-test-framework run -q` emits exactly one `Result:` line — no digest, no explain expansion, no per-tool rows.
    - `mcp-test-framework run --raw` emits NEITHER digest NOR explain (existing --raw short-circuit at cli.py:470 is unchanged and runs before the digest block).
    - `--explain` is OWNED by the Typer wrapper: `_build_pytest_args` is NOT modified, pytest never sees `--explain`.
    - `mcp-test-framework run --with-framework` emits a digest whose Test plan line is `Test plan:   N contract cases` immediately followed by a continuation line `             + framework self-tests` (NOT a blank-then-suffix sequence). Emitted from inside `_render_pre_run_digest` per REVISION WARNING 3.
  </behavior>
  <action>
**Step A: Add the `--explain` Typer Option** between `with_framework` (currently line 394–403) and `pytest_args` (currently line 404–407):

```python
    explain: bool = typer.Option(
        False,
        "--explain",
        help=(
            "Expand the pre-run digest's 'Skipping (N)' hint into one line "
            "per skipped tool with its skip reason, sorted alphabetically. "
            "Renders inline before the pytest subprocess starts. "
            "Ignored under --raw (no domain UI) and under -q / --quiet "
            "(summary-only output)."
        ),
    ),
```

**Step B: Restructure the body of `run()` between the `--raw` short-circuit (current line 484, `raise typer.Exit(...)`) and the existing subprocess call (current line 492).** The CURRENT order is:

```
discovered_tools = _discover_tools_for_run(cfg)                  # line 490
rc, tmp_xml, captured_stdout, captured_stderr = run_pytest_subprocess(...)  # line 492
try:
    _dispatch_default_mode_or_error(...)
    parsed = parse_junit_xml(tmp_xml)
    server_cmd = ...
    judges_set = ...
    judges = sorted(judges_set)
    ctx = RenderContext(..., total_planned_cases=parsed.total_cases)  # currently line 532
    if quiet: render_summary_only(parsed, ctx)
    else:     render_domain_ui(parsed, ctx)
    ...
```

CHANGE TO (build ctx pre-subprocess so digest can fire):

```python
    # Phase 14: discovery runs BEFORE the subprocess so the header's
    # Skipping count includes state-(a) unlisted tools.
    discovered_tools = _discover_tools_for_run(cfg)

    # Phase 16 D-01: build RenderContext BEFORE the subprocess so the
    # pre-run digest can render. total_planned_cases is set from
    # running×CASES_PER_CONTRACT_TOOL pre-run (post-run code below
    # overwrites it via the recomputed ctx2 with parsed.total_cases for
    # the post-run summary's count source — but the digest never needs
    # the actual count, only the pre-run estimate).
    server_cmd = f"{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}".strip()
    judges_set: set[str] = set()
    for tool_cfg in cfg.tools.values():
        for judge_name in getattr(tool_cfg, "judges", []) or []:
            judges_set.add(judge_name)
    judges = sorted(judges_set)

    pre_run_ctx = _runner.RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered_tools,
        tools_config=cfg.tools,
        judges=judges,
        total_planned_cases=0,  # set post-parse on the recomputed ctx below
    )

    # Phase 16 D-09: pre-run digest + --explain expansion BOTH gate on
    # `not quiet`. -q wins over --explain per D-08 / UX-05.
    # REVISION (checker WARNING 3 + 4): pass with_framework=/explain= through
    # so the digest renders the suffix inline (no awkward blank gap) and
    # omits the "(use --explain to list)" hint when --explain is set.
    if not quiet:
        _runner._render_pre_run_digest(
            pre_run_ctx,
            with_framework=with_framework,
            explain=explain,
        )
        if explain:
            _runner._render_skipped_tools_explain(pre_run_ctx)

    rc, tmp_xml, captured_stdout, captured_stderr = _runner.run_pytest_subprocess(
        junit_xml=junit_xml,
        pytest_args=pytest_args,
        raw=False,
        with_framework=with_framework,
    )
    try:
        _runner._dispatch_default_mode_or_error(tmp_xml, rc, captured_stderr)

        try:
            parsed = _runner.parse_junit_xml(tmp_xml)
        except ET.ParseError as exc:
            _emit_operator_error(
                summary="JUnit XML parse failed",
                detail=[
                    f"could not parse the test runner's results file: {exc}",
                    "this usually means pytest crashed mid-run.",
                ],
                next_step=(
                    "re-run with `--raw` to see pytest's native output, or "
                    "check the captured stderr above"
                ),
            )

        # Phase 16: rebuild ctx with the real total_planned_cases for the
        # post-run summary. discovered_tools / tools_config / judges /
        # server_cmd are unchanged from pre_run_ctx.
        ctx = _runner.RenderContext(
            server_cmd=server_cmd,
            discovered_tools=discovered_tools,
            tools_config=cfg.tools,
            judges=judges,
            total_planned_cases=parsed.total_cases,
        )

        # Phase 14 D-12/D-13: verbosity ladder unchanged. render_domain_ui
        # now emits ONLY per-tool rows + summary (Plan 01 removed the
        # _render_header call site).
        if quiet:
            _runner.render_summary_only(parsed, ctx)
        else:
            _runner.render_domain_ui(parsed, ctx)

        if debug:
            _runner.render_debug_appendix(
                captured_stdout, captured_stderr, parsed,
            )
    finally:
        # existing tempfile cleanup stays here unchanged
        ...
```

DO NOT modify the existing `--raw` short-circuit at lines 470–484 (D-08: composition with `--raw` is enforced by the short-circuit returning before the digest block runs).

DO NOT add `--explain` to any pytest-args building function. Verify by checking `_build_pytest_args` (`_runner.py:102–108` per CONTEXT.md) is unchanged.

DO NOT move `_discover_tools_for_run(cfg)` — it stays at its current position.

The existing `finally:` clause for tempfile cleanup stays in place. Preserve everything below the rendering block (debug, exit-code map, raise) unchanged.
  </action>
  <verify>
    <automated>uv run mcp-test-framework run --help 2>&amp;1 | grep -E "^\s*--explain" &amp;&amp; uv run python -c "import re; src = open('src/mcp_test_framework/cli.py', encoding='utf-8').read(); assert 'explain: bool = typer.Option' in src; assert '_runner._render_pre_run_digest(pre_run_ctx)' in src; assert '_runner._render_skipped_tools_explain(pre_run_ctx)' in src; assert re.search(r'if not quiet:\s*\n\s*_runner\._render_pre_run_digest', src), 'pre-run digest gating broken'; assert re.search(r'if explain:\s*\n\s*_runner\._render_skipped_tools_explain', src), 'explain gating broken'; from mcp_test_framework._runner import _build_pytest_args; args = _build_pytest_args(junit_xml=None, pytest_args=None, with_framework=False); assert '--explain' not in args, '--explain leaked into pytest args: ' + str(args); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "explain: bool = typer.Option" src/mcp_test_framework/cli.py` returns exactly one match.
    - `grep -n '"--explain"' src/mcp_test_framework/cli.py` returns at least one match (the flag literal in the Typer Option).
    - `grep -c "_runner._render_pre_run_digest" src/mcp_test_framework/cli.py` returns exactly 1.
    - `grep -c "_runner._render_skipped_tools_explain" src/mcp_test_framework/cli.py` returns exactly 1.
    - `grep -n "if not quiet:" src/mcp_test_framework/cli.py` shows at least one match with `_render_pre_run_digest` on a subsequent line within 5 lines.
    - `grep -n "if explain:" src/mcp_test_framework/cli.py` shows one match with `_render_skipped_tools_explain` on the next line.
    - `uv run mcp-test-framework run --help` exit code is 0 and stdout contains literal `--explain`.
    - Help text for `--explain` mentions both `--raw` and `-q` (case-insensitive grep).
    - `_build_pytest_args(...)` return value does NOT contain `"--explain"` (verified by `<automated>` block).
    - `grep -n "^    if raw:" src/mcp_test_framework/cli.py` is unchanged from pre-task baseline (--raw short-circuit untouched).
    - REVISION (WARNING 3): `with_framework` Test plan suffix is emitted INSIDE `_render_pre_run_digest` (Plan 16-01 Task 2), NOT from `cli.py`. `grep -c "+ framework self-tests" src/mcp_test_framework/cli.py` returns 0. The cli.py call site reads `_runner._render_pre_run_digest(pre_run_ctx, with_framework=with_framework, explain=explain)` (single call, no separate suffix print).
    - REVISION (WARNING 4): cli.py passes `explain=explain` into the digest call. `grep -n "explain=explain" src/mcp_test_framework/cli.py` returns at least one match.
  </acceptance_criteria>
  <done>`--explain` is a Typer-wrapper-owned flag; the digest renders pre-subprocess (gated on not-quiet); `--explain` adds the skipped-tools block (gated on not-quiet-and-explain); `--raw` and `--with-framework` compose correctly; pytest never sees `--explain`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create test_runner_pre_run_digest.py — digest shape + CASES_PER_CONTRACT_TOOL pin + parametrize match</name>
  <files>tests/framework/unit/test_runner_pre_run_digest.py</files>
  <read_first>
    - tests/framework/unit/test_runner_parser.py (lines 31, 39–47 — _FIXTURES path + locked-constant idiom)
    - tests/framework/test_runner_verbosity.py (lines 34–71 — _ctx builder + capsys assertion pattern)
    - tests/contract/test_mcp_tool_contract.py (count `test_*` async functions — must equal 10)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-03, D-12
  </read_first>
  <behavior>
    Tests pin:
    - `CASES_PER_CONTRACT_TOOL == 10` (drift guard 1).
    - AST count of `test_*` (sync or async) function defs at module scope of `tests/contract/test_mcp_tool_contract.py` equals `CASES_PER_CONTRACT_TOOL` (drift guard 2; either constant or test-file changes will break this).
    - `_render_pre_run_digest` at N=3 (1 running, 2 skipping) emits exactly 10 lines and contains the expected banner + label rows + `Test plan:   10 contract cases`.
    - `_render_pre_run_digest` at N=70 (2 running, 68 skipping — matches homelab-mcp's safe-default scope) emits exactly 10 lines (D-12 invariant).
    - `_render_pre_run_digest` with `judges=[]` prints `Judges:      (none configured)`.
    - `_compose_pre_run_skip_reasons(["a","b"], {"a": SimpleNamespace(skip=False)})` returns `{"b": "not selected in config"}` (state-a default).
    - `_compose_pre_run_skip_reasons(["a"], {"a": SimpleNamespace(skip=True, skip_reason=None)})` returns `{"a": "explicit skip in config"}` (state-c default; verify the ToolConfig attribute name matches what `_compose_unparametrized_skips_from_config` expects — read its body if uncertain).
  </behavior>
  <action>
Create the file with the following structure. Use the SimpleNamespace shim for `tools_config` values to avoid coupling to the Pydantic `ToolConfig` model (precedent: `test_runner_verbosity.py:34-41` uses an empty `{}`). Match the `_FIXTURES` path convention.

```python
"""Phase 16 D-01/D-03/D-12: pre-run digest renderer regression tests.

Pins:
- CASES_PER_CONTRACT_TOOL constant (must not silently drift)
- AST-counted parametrize count in tests/contract/test_mcp_tool_contract.py
  must equal the constant (drift guard: either side changing breaks this)
- Digest height ≤ 10 lines at all N (D-12 invariant)
- Banner / label / Test plan line shape (locked by Phase 14 D-07 + D-03)
"""
from __future__ import annotations

import ast
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework._runner import (
    CASES_PER_CONTRACT_TOOL,
    RenderContext,
    _compose_pre_run_skip_reasons,
    _render_pre_run_digest,
)

# tests/framework/unit/<here> -> tests/framework/fixtures (precedent: test_runner_parser.py:31)
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
# tests/framework/unit/<here> -> repo_root/tests/contract/test_mcp_tool_contract.py
_CONTRACT_FILE = Path(__file__).resolve().parents[3] / "tests" / "contract" / "test_mcp_tool_contract.py"


def _ctx(discovered=None, tools_config=None, judges=None, server_cmd="uvx homelab-mcp"):
    return RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered if discovered is not None else ["alpha", "beta", "gamma"],
        tools_config=tools_config if tools_config is not None else {},
        judges=judges if judges is not None else ["clarity"],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# Locked-constant regression (D-03)
# ---------------------------------------------------------------------------


def test_cases_per_contract_tool_constant_locked() -> None:
    """D-03: pre-run test-plan count = running × CASES_PER_CONTRACT_TOOL.
    Sources: 5 schema validators + 4 judge dimensions + 1 output conformance = 10."""
    assert CASES_PER_CONTRACT_TOOL == 10


def test_cases_per_contract_tool_matches_actual_parametrize_count() -> None:
    """D-03: the constant must equal the number of test_* functions in
    tests/contract/test_mcp_tool_contract.py. If either side moves and the
    other doesn't, this test fails — preventing silent drift between the
    digest's pre-run count and the actual contract surface.
    """
    assert _CONTRACT_FILE.exists(), f"expected contract test at {_CONTRACT_FILE}"
    source = _CONTRACT_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    test_funcs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
    ]
    assert len(test_funcs) == CASES_PER_CONTRACT_TOOL, (
        f"contract file has {len(test_funcs)} test_* funcs but "
        f"CASES_PER_CONTRACT_TOOL = {CASES_PER_CONTRACT_TOOL}. "
        f"Update one to match the other."
    )


# ---------------------------------------------------------------------------
# Digest shape (D-01)
# ---------------------------------------------------------------------------


def test_pre_run_digest_emits_banner_and_label_block(capsys) -> None:
    ctx = _ctx(
        discovered=["alpha", "beta", "gamma"],
        tools_config={"alpha": SimpleNamespace(skip=False)},
        judges=["clarity"],
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    lines = out.split("\n")
    # Banner = 40 equals signs (Phase 14 D-07 locked)
    assert lines[0] == "=" * 40
    assert lines[1] == "MCP Test Framework"
    assert lines[2] == "=" * 40
    assert "MCP server:  uvx homelab-mcp" in out
    assert "Discovered:  3 tools" in out
    assert "Running:      1  (alpha)" in out, repr(out)
    assert "Skipping:     2  (use --explain to list)" in out, repr(out)
    assert "Judges:      clarity" in out
    assert "Test plan:   10 contract cases" in out, repr(out)


def test_pre_run_digest_test_plan_uses_constant(capsys) -> None:
    """D-03: Test plan = running_n × CASES_PER_CONTRACT_TOOL."""
    ctx = _ctx(
        discovered=["a", "b"],
        tools_config={"a": SimpleNamespace(skip=False), "b": SimpleNamespace(skip=False)},
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert f"Test plan:   {2 * CASES_PER_CONTRACT_TOOL} contract cases" in out


def test_pre_run_digest_height_bounded_at_small_N(capsys) -> None:
    """D-12: digest height ≤ 10 content lines regardless of N."""
    ctx = _ctx(
        discovered=["alpha"],
        tools_config={"alpha": SimpleNamespace(skip=False)},
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    content_lines = [l for l in out.split("\n") if l != ""] + [""]
    # 8 label-bearing lines + 1 trailing blank == max 10 split chunks
    assert len(out.split("\n")) <= 11, f"got {len(out.split(chr(10)))} lines: {out!r}"


def test_pre_run_digest_height_bounded_at_N_70(capsys) -> None:
    """D-12: digest height ≤ 10 lines even at homelab-mcp's full N=70 surface.
    The Skipping list is NEVER inline-expanded here — `--explain` is the
    expansion surface, not the digest.
    """
    discovered = [f"tool_{i:02d}" for i in range(70)]
    tools_config = {
        "tool_00": SimpleNamespace(skip=False),
        "tool_01": SimpleNamespace(skip=False),
    }
    ctx = _ctx(discovered=discovered, tools_config=tools_config, judges=["clarity"])
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert len(out.split("\n")) <= 11, f"N=70 digest too tall: {len(out.split(chr(10)))} lines"
    # Sanity: the 68 skipped tool names must NOT appear inline.
    assert "tool_02" not in out, "Skipping list leaked into digest at N=70"
    # Test plan still computes correctly: 2 × 10 = 20.
    assert "Test plan:   20 contract cases" in out


def test_pre_run_digest_handles_empty_judges(capsys) -> None:
    ctx = _ctx(discovered=["a"], tools_config={"a": SimpleNamespace(skip=False)}, judges=[])
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "Judges:      (none configured)" in out


# ---------------------------------------------------------------------------
# _compose_pre_run_skip_reasons (D-05 / D-14)
# ---------------------------------------------------------------------------


def test_compose_pre_run_skip_reasons_state_a_unlisted() -> None:
    """state (a): tool discovered but not in tools_config => 'not selected in config'."""
    skipped = _compose_pre_run_skip_reasons(["a", "b"], {"a": SimpleNamespace(skip=False)})
    assert "b" in skipped
    assert skipped["b"] == "not selected in config"
    assert "a" not in skipped


def test_compose_pre_run_skip_reasons_empty_on_all_running() -> None:
    skipped = _compose_pre_run_skip_reasons(["a"], {"a": SimpleNamespace(skip=False)})
    assert skipped == {}
```

For the state-(c) test: read `_compose_unparametrized_skips_from_config` body at `_runner.py:553-592` to confirm whether it inspects `skip` and `skip_reason` attributes. If the body uses `tools_config[t].skip` and `tools_config[t].skip_reason`, a `SimpleNamespace(skip=True, skip_reason=None)` shim works. If it uses `getattr(...)`, the shim still works. Either way, add this test:

```python
def test_compose_pre_run_skip_reasons_state_c_explicit_default() -> None:
    """state (c): tool in config with skip=True and no custom reason
    => 'explicit skip in config' (locked Phase 13 D-12 string)."""
    skipped = _compose_pre_run_skip_reasons(
        ["a"], {"a": SimpleNamespace(skip=True, skip_reason=None)}
    )
    assert skipped.get("a") == "explicit skip in config"


def test_compose_pre_run_skip_reasons_state_c_custom_reason() -> None:
    """state (c) with operator-supplied skip_reason: custom text replaces the default."""
    skipped = _compose_pre_run_skip_reasons(
        ["a"], {"a": SimpleNamespace(skip=True, skip_reason="dangerous in CI")}
    )
    assert skipped.get("a") == "dangerous in CI"
```

If the actual composer's attribute access surface differs (e.g., it uses `.skip_reason or default`), adjust the shim above accordingly during execution — but the assertion strings stay locked.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/framework/unit/test_runner_pre_run_digest.py` exists.
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -v` exits 0 with at least 8 tests passing.
    - File contains `test_cases_per_contract_tool_constant_locked` AND `test_cases_per_contract_tool_matches_actual_parametrize_count`.
    - File contains `test_pre_run_digest_height_bounded_at_N_70` and the assertion `len(out.split("\n")) <= 11`.
    - File imports `CASES_PER_CONTRACT_TOOL`, `_compose_pre_run_skip_reasons`, `_render_pre_run_digest` from `mcp_test_framework._runner`.
    - Test file uses `ast.parse` to count `test_*` functions in `tests/contract/test_mcp_tool_contract.py`.
    - Test file uses `_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"` (or equivalent — matches `test_runner_parser.py:31`).
  </acceptance_criteria>
  <done>Digest shape + height + constants pinned; either side moving (constant or contract test file) breaks a test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_runner_explain.py — --explain CLI tests with sort order + composition</name>
  <files>tests/framework/unit/test_runner_explain.py</files>
  <read_first>
    - tests/framework/test_runner_verbosity.py (lines 131–219 — _invoke + _stub_subprocess_writing_xml + _make_valid_config + end-to-end test pattern)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-05, D-06, D-08, D-09
    - .planning/phases/16-reporter-ux-overhaul/16-PATTERNS.md (tests/framework/unit/test_runner_explain.py CREATE block)
  </read_first>
  <behavior>
    Tests pin (using CliRunner end-to-end):
    - `--explain` adds `--explain` to help; help text mentions `--raw` and `-q`.
    - `mcp-test-framework run --explain` output contains a `Skipping (N):` block with one line per skipped tool sorted alphabetically, em-dash separator, state-(a) and state-(c) reasons present.
    - Skipped lines come AFTER the digest (in order: digest banner → digest labels → Skipping block → pytest output → per-tool rows + summary).
    - `mcp-test-framework run -q --explain` emits ONLY the `Result:` line (D-09: quiet wins, UX-05 trumps UX-02).
    - `mcp-test-framework run --raw --explain` emits no digest, no Skipping block (--raw short-circuit at cli.py:470 bypasses all wrapper-side rendering).
    - `mcp-test-framework run --explain --with-framework` works: digest emits with `+ framework self-tests` suffix; Skipping block lists tool-side skips only.
  </behavior>
  <action>
Create the file. Duplicate the helpers `_invoke`, `_stub_subprocess_writing_xml`, `_make_valid_config` from `test_runner_verbosity.py:131–180` (duplication is fine per precedent — `test_runner_parser.py` does its own setup). Use the existing `tests/framework/fixtures/junit-all-pass.xml` fixture.

```python
"""Phase 16 D-05/D-06/D-08/D-09: --explain Typer flag end-to-end tests.

Pins:
- --explain is registered in `run --help` (inverse of Phase 14 D-14)
- --explain expands the Skipping bucket to one line per tool, sorted, em-dash
- --explain composes correctly with -q (quiet wins), --raw (raw bypasses),
  --with-framework (framework suffix coexists)
- --explain is NEVER forwarded to pytest (wrapper-owned per D-07)
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _invoke(*args: str):
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app
    return CliRunner().invoke(app, list(args))


def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")

    def _fake(argv, **kwargs):
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        # D-07 guard: --explain must never reach pytest's argv.
        assert "--explain" not in argv, "--explain leaked to pytest argv"
        return SimpleNamespace(returncode=returncode, stdout="...", stderr="", args=argv)

    return _fake


def _make_valid_config(tmp_path: Path, tools: dict | None = None) -> Path:
    """Minimal config.yaml. `tools` dict controls which tools are in
    tools_config (state-b) vs absent (state-a)."""
    cfg = tmp_path / "config.yaml"
    tools_yaml = "tools: {}\n" if not tools else ""
    if tools:
        tools_yaml = "tools:\n"
        for name, spec in tools.items():
            tools_yaml += f"  {name}:\n"
            if spec.get("skip"):
                tools_yaml += f"    skip: true\n"
                if "skip_reason" in spec:
                    tools_yaml += f"    skip_reason: \"{spec['skip_reason']}\"\n"
            judges = spec.get("judges", [])
            if judges:
                tools_yaml += f"    judges: {judges}\n"
    cfg.write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\n"
        + tools_yaml,
        encoding="utf-8",
    )
    return cfg


# ---------------------------------------------------------------------------
# Help registration (inverts Phase 14's negative test)
# ---------------------------------------------------------------------------


def test_run_help_lists_explain_flag() -> None:
    """Phase 16 D-07: --explain is owned by the Typer wrapper, registered here.
    Inverts Phase 14 D-14's negative test (which is updated separately)."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--explain" in result.output


def test_run_help_explain_mentions_raw_and_quiet_interactions() -> None:
    """D-08: --explain help text must document composition with --raw and -q."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0
    # Find the chunk of help text near `--explain` and assert it mentions both.
    out = result.output.lower()
    assert "--explain" in out
    assert "--raw" in out, "--explain help should mention --raw composition"
    assert "-q" in out or "--quiet" in out, "--explain help should mention quiet"


# ---------------------------------------------------------------------------
# Skipping block shape (D-05 / D-06)
# ---------------------------------------------------------------------------


def test_run_explain_lists_skipped_tools_alphabetically(monkeypatch, tmp_path) -> None:
    cfg = _make_valid_config(tmp_path, tools={"alpha": {"judges": ["clarity"]}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    # Discovered: alpha (running), gamma + beta (skipping state-a, sorted in explain)
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "gamma", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    out = result.output
    assert "MCP Test Framework" in out  # digest still emits
    assert "Skipping (2):" in out
    # em-dash present, sort order beta < gamma
    assert "—" in out, repr(out)
    beta_idx = out.index("beta")
    gamma_idx = out.index("gamma")
    assert beta_idx < gamma_idx, "explain sort order broken"
    # state-a reason verbatim
    assert "not selected in config" in out


def test_run_explain_renders_after_digest_before_pytest(monkeypatch, tmp_path) -> None:
    """D-06: digest → Skipping block → pytest output order."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    out = result.output
    digest_idx = out.index("MCP Test Framework")
    explain_idx = out.index("Skipping (1):")
    result_idx = out.index("Result:")
    assert digest_idx < explain_idx < result_idx, (
        f"order: digest={digest_idx} explain={explain_idx} result={result_idx}\n{out}"
    )


# ---------------------------------------------------------------------------
# Composition (D-08 / D-09)
# ---------------------------------------------------------------------------


def test_run_quiet_with_explain_is_noop(monkeypatch, tmp_path) -> None:
    """D-09 / UX-05: -q suppresses BOTH digest AND --explain expansion."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "-q", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" not in result.output  # no digest
    assert "Skipping (" not in result.output  # no explain block
    assert "Result:" in result.output  # summary line only


def test_run_raw_with_explain_is_bypassed(monkeypatch, tmp_path) -> None:
    """D-08: --raw bypasses domain UI entirely; --explain has no effect."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})

    def _fake_subprocess(argv, **kwargs):
        # Under --raw, no tempfile is written by the wrapper; just return rc=0.
        # --explain must NOT appear in argv (wrapper-owned).
        assert "--explain" not in argv
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake_subprocess)
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--raw", "--explain", "--config", str(cfg))
    # --raw exits via Typer.Exit with the mapped pytest exit code (0 here)
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" not in result.output
    assert "Skipping (" not in result.output


def test_run_explain_with_with_framework_emits_suffix(monkeypatch, tmp_path) -> None:
    """D-03 / D-08: --explain --with-framework: digest gets the suffix,
    Skipping block lists tool-side skips only."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--with-framework", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "+ framework self-tests" in result.output
    assert "Skipping (1):" in result.output


def test_run_default_emits_digest_without_explain_block(monkeypatch, tmp_path) -> None:
    """D-01: default mode emits digest but NOT the Skipping (N): block."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" in result.output  # digest emits
    assert "(use --explain to list)" in result.output  # hint stays
    assert "Skipping (1):" not in result.output  # no inline expansion


def test_run_default_post_run_has_no_second_banner(monkeypatch, tmp_path) -> None:
    """D-01: post-run output (per-tool rows + summary) MUST NOT include
    a second `MCP Test Framework` banner. Banner appears exactly once."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert result.output.count("MCP Test Framework") == 1, (
        f"banner repeated: {result.output!r}"
    )


# REVISION (checker WARNING 4): the digest's "(use --explain to list)" hint
# must be omitted when --explain is set (the list is right there inline; the
# hint would lie). Pinned here at the CLI end-to-end layer.


def test_run_default_includes_explain_hint(monkeypatch, tmp_path) -> None:
    """WARNING 4: default mode (no --explain) shows the hint string."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "(use --explain to list)" in result.output


def test_run_explain_suppresses_hint(monkeypatch, tmp_path) -> None:
    """WARNING 4: --explain mode omits the hint (the list is inline below)."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "(use --explain to list)" not in result.output, (
        f"hint should be suppressed under --explain: {result.output!r}"
    )
    # Sanity: the Skipping (N): block header still emits.
    assert "Skipping (1):" in result.output
```

Confirm the `tests/framework/fixtures/junit-all-pass.xml` fixture exists (it should — it's used by `test_runner_verbosity.py:183-219`). If it doesn't exist under that name, use whichever all-PASS fixture is in `tests/framework/fixtures/` (read directory listing during execution).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_runner_explain.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/framework/unit/test_runner_explain.py` exists.
    - `uv run pytest tests/framework/unit/test_runner_explain.py -v` exits 0 with at least 8 tests passing.
    - File contains `test_run_help_lists_explain_flag`, `test_run_explain_lists_skipped_tools_alphabetically`, `test_run_quiet_with_explain_is_noop`, `test_run_raw_with_explain_is_bypassed`, `test_run_explain_with_with_framework_emits_suffix`, `test_run_default_post_run_has_no_second_banner`.
    - Subprocess stub includes `assert "--explain" not in argv` (D-07 guard).
    - At least one test asserts em-dash `—` is present in `--explain` output.
    - At least one test asserts ordering `digest_idx < explain_idx < result_idx`.
    - REVISION (WARNING 4): file contains `test_run_default_includes_explain_hint` AND `test_run_explain_suppresses_hint`. The latter asserts `"(use --explain to list)" not in result.output` under `--explain`.
  </acceptance_criteria>
  <done>End-to-end CLI tests pin --explain shape, sort order, composition with -q / --raw / --with-framework, and the D-07 wrapper-ownership guard (--explain never reaches pytest argv).</done>
</task>

<task type="auto" tdd="false">
  <name>Task 4: Extend test_runner_verbosity.py with -q parity test and invert the Phase 14 negative test</name>
  <files>tests/framework/test_runner_verbosity.py</files>
  <read_first>
    - tests/framework/test_runner_verbosity.py (lines 131–219, especially 139–147 which is the test being inverted)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-09 + cross-ref to UX-05
  </read_first>
  <behavior>
    - The existing `test_run_help_does_not_list_explain` (Phase 14 D-14 negative) is REMOVED or rewritten — `--explain` is now in help and that test would fail otherwise.
    - A new test `test_run_quiet_emits_exactly_one_line` asserts that `mcp-test-framework run -q` against a passing fixture emits exactly one non-empty line (the `Result:` line).
    - A new test `test_run_quiet_suppresses_pre_run_digest` asserts `-q` output does NOT contain `MCP Test Framework`.
  </behavior>
  <action>
**Step A: Locate and rewrite `test_run_help_does_not_list_explain`** at the existing lines 139–147 (per CONTEXT.md and PATTERNS.md). The current body asserts `--explain` is absent from help; this MUST be inverted. Two options:

Option 1 (RECOMMENDED — preserve history): Rewrite the function body in place, renaming the function:

```python
def test_run_help_lists_explain_phase16() -> None:
    """Phase 16 D-07: --explain is registered by the Typer wrapper.
    (Inverts Phase 14 D-14's deferral assertion now that Phase 16 ships.)
    """
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--explain" in result.output
```

Option 2 (acceptable): Delete the function entirely. The new positive coverage lives in `tests/framework/unit/test_runner_explain.py::test_run_help_lists_explain_flag` from Task 3.

Pick Option 1 for in-place clarity (the test's existence as a sentinel — "Phase 16 owns --explain" — remains valuable as a regression breadcrumb).

**Step A.5 (REVISION — checker BLOCKER 2):** Audit and update banner-position-dependent tests. `grep -n "MCP Test Framework" tests/framework/test_runner_verbosity.py` shows the following call sites (pre-revision):

| Line | Function | Current assertion shape | Required update |
|------|----------|-------------------------|-----------------|
| 54 | inside a helper or early test | `assert "MCP Test Framework" not in out` | Re-read in context. If it tests `-q` summary-only / `--raw` bypass behavior (banner absent), NO CHANGE — the assertion still holds (digest is suppressed under `-q`/`--raw`). |
| 199 | `test_run_quiet_renders_summary_only` (around `:183-200`) | `assert "MCP Test Framework" not in result.output` | NO CHANGE — `-q` still suppresses the (now pre-run) digest per D-09. Assertion remains valid. |
| 216 | `test_run_default_renders_full_domain_ui` (around `:203-219`) | `assert "MCP Test Framework" in result.output` | NO CHANGE — banner still appears, just earlier in stdout (pre-pytest instead of post-pytest). `in result.output` doesn't care about position. |
| 236, 239 | `test_run_debug_appends_appendix_after_domain_ui` (around `:222-241`) | `assert "MCP Test Framework" in result.output` (`:236`); `header_idx = result.output.index("MCP Test Framework")` + `assert header_idx < appendix_idx` (`:239`) | NO CHANGE to `:236`. NO CHANGE to `:239` assertion either — the banner still appears BEFORE the debug appendix (banner is now pre-pytest, appendix is post-pytest, so `header_idx < appendix_idx` is even MORE true). The semantic intent ("banner comes before debug appendix") is preserved by Phase 16. |
| 262 | `test_run_quiet_plus_debug_renders_summary_then_appendix` (around `:244-270`) | `assert "MCP Test Framework" not in result.output` | NO CHANGE — `-q` suppresses the digest, so banner is still absent. |
| 289 | `test_run_raw_ignores_quiet_and_debug` (around `:273-291`) | `assert "MCP Test Framework" not in result.output` | NO CHANGE — `--raw` short-circuits before the digest renders. |

CONCLUSION (post-audit): **all six existing call sites remain semantically correct after Phase 16** because (a) the banner moves from post-pytest to pre-pytest but still appears in the default-mode default-debug-mode output stream, and (b) the `-q` / `--raw` suppression invariants are preserved by D-09 / D-08. The only test that MUST change is the help-list assertion at `:139` (Step A above).

**The executor MUST verify this audit during execution** by re-reading `tests/framework/test_runner_verbosity.py` lines 50–60, 180–270, and 270–295, confirming that:
1. Every `assert "MCP Test Framework" in result.output` is in a default-mode (non-quiet, non-raw) test → still passes (banner still emits).
2. Every `assert "MCP Test Framework" not in result.output` is in a `-q` or `--raw` test → still passes (suppression preserved).
3. The `:239` ordering check (`header_idx < appendix_idx`) still holds because both surfaces are produced by the same `run` invocation and the digest precedes the subprocess which precedes the debug appendix.

If any of these audited tests FAILS after Plan 16-02 lands (verified by `uv run pytest tests/framework/test_runner_verbosity.py -x -q`), update the failing assertion in this same task — do NOT defer to a follow-up plan. Document any updated assertions in the SUMMARY with the line number + before/after.

**Step B: Append new tests to the existing `# CLI end-to-end` section after line 219**:

```python
def test_run_quiet_emits_exactly_one_line(monkeypatch, tmp_path) -> None:
    """Phase 16 D-09 / UX-05: -q output is exactly one non-empty line
    (the `Result:` summary). The pre-run digest and per-tool rows are both
    suppressed."""
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta", "gamma"],
    )
    result = _invoke("run", "-q", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    non_empty = [l for l in result.output.split("\n") if l.strip()]
    assert len(non_empty) == 1, f"-q emitted {len(non_empty)} non-empty lines: {result.output!r}"
    assert non_empty[0].startswith("Result:"), repr(non_empty[0])


def test_run_quiet_suppresses_pre_run_digest(monkeypatch, tmp_path) -> None:
    """Phase 16 D-09: -q gates the pre-run digest off in cli.py:run."""
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha"],
    )
    result = _invoke("run", "-q", "--config", str(cfg))
    assert "MCP Test Framework" not in result.output
    assert "Discovered:" not in result.output
    assert "use --explain to list" not in result.output
```

The existing `test_run_quiet_renders_summary_only` test (around line 183) probably still passes — it predates the pre-run digest but its assertions (`"Result:" in out`, `"MCP Test Framework" not in out`) align with Phase 16's `-q` behavior. Do NOT modify it; if it fails post-Plan 02 because of `-q` semantics, update its assertions to match the new pipeline (the pre-run digest is suppressed under `-q`, so its `"MCP Test Framework" not in out` assertion still holds).

DO NOT add tests that overlap with `test_runner_explain.py` (Task 3 owns --explain coverage). This file owns -q and the help-list inversion only.
  </action>
  <verify>
    <automated>uv run pytest tests/framework/test_runner_verbosity.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "test_run_help_does_not_list_explain" tests/framework/test_runner_verbosity.py` returns 0 (function renamed or deleted).
    - `grep -c "test_run_help_lists_explain_phase16" tests/framework/test_runner_verbosity.py` returns 1 (if Option 1 chosen) — OR the function is deleted (Option 2) and the only such positive assertion lives in `test_runner_explain.py`.
    - `grep -n "test_run_quiet_emits_exactly_one_line" tests/framework/test_runner_verbosity.py` returns one match.
    - `grep -n "test_run_quiet_suppresses_pre_run_digest" tests/framework/test_runner_verbosity.py` returns one match.
    - `uv run pytest tests/framework/test_runner_verbosity.py -v` exits 0; ALL tests in the file pass.
    - The full Phase 14 test surface still passes: `uv run pytest tests/framework/ -x -q` exits 0.
    - REVISION (BLOCKER 2): `uv run pytest tests/framework/test_runner_verbosity.py -x -q` passes for the WHOLE file (not just the new tests). Every banner-position-dependent test enumerated in Step A.5 above is verified to still pass after Phase 16 lands. Any test that fails post-audit is updated in this same task and recorded in the SUMMARY with line number + before/after.
  </acceptance_criteria>
  <done>The Phase 14 negative test is inverted/removed; new -q parity tests pin UX-05; the Phase 14 file's existing tests still pass against the post-Plan-02 codebase.</done>
</task>

</tasks>

<threat_model>
**STRIDE applicability: LOW.** This plan adds a Typer flag, reorders stdout rendering calls inside the existing `run` command, and adds tests. No new trust boundaries, no new inputs accepted from the network or filesystem, no new authentication/authorization surfaces.

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-16-02-01 | Tampering | `_compose_pre_run_skip_reasons` reading operator's `tools_config[t].skip_reason` (free-text string from YAML) printed to stdout | accept | The same data already flows through `_compose_unparametrized_skips_from_config` post-run (Phase 14 surface). YAML is operator-controlled config; trust boundary is unchanged from Phase 13. No HTML/shell context — pure stdout text with no interpretation. The em-dash separator is locked content, not interpolated user data. |
| T-16-02-02 | Information disclosure | Pre-run digest prints `server_cmd` (operator's MCP server command-line, may contain paths) BEFORE pytest runs | accept | Identical surface to Phase 14's `_render_header` post-run output (same `ctx.server_cmd` field). Phase 14 already accepted this trade-off (operator-visible only; no remote consumer). |

The `--explain` flag is wrapper-owned and never forwarded to pytest (D-07; enforced by the `assert "--explain" not in argv` guard inside the test stub). No new injection vector into the pytest subprocess.
</threat_model>

<verification>
1. `uv run mcp-test-framework run --help | grep -E "^\s*--explain"` returns a match.
2. `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -v` exits 0.
3. `uv run pytest tests/framework/unit/test_runner_explain.py -v` exits 0.
4. `uv run pytest tests/framework/test_runner_verbosity.py -v` exits 0.
5. Full framework test surface still green: `uv run pytest tests/framework/ -x -q` exits 0.
6. Contract surface unaffected: `uv run pytest tests/contract/ -x --collect-only -q` collects the same number of test items as pre-Plan-02 (10 cases per discovered tool × N tools).
7. Live-suppression smoke: `uv run mcp-test-framework run -q --config config.example.yaml` (with stubbed subprocess via local config) emits exactly one `Result:` line — manually verifiable but covered by `test_run_quiet_emits_exactly_one_line`.
</verification>

<success_criteria>
- `--explain` is registered as a Typer flag on `mcp-test-framework run`, with help text mentioning `--raw` and `-q` interactions.
- Default-mode `run` emits the pre-run digest BEFORE the subprocess and post-run output (per-tool rows + summary) only.
- `--explain` adds an inline `Skipping (N):` block between the digest and the subprocess, sorted alphabetically, em-dash separator.
- `-q` suppresses both digest and explain; only `Result:` line emits.
- `--raw` short-circuit unchanged; --explain is a no-op under --raw.
- `--with-framework --explain` composes: digest + `+ framework self-tests` suffix + Skipping block.
- pytest never sees `--explain` (D-07 ownership invariant, asserted by test stub).
- The Phase 14 negative test `test_run_help_does_not_list_explain` is inverted (or removed).
- Two new `-q` parity tests pin UX-05.
- All existing tests in `tests/framework/` still pass.
</success_criteria>

<output>
After completion, create `.planning/phases/16-reporter-ux-overhaul/16-02-SUMMARY.md` per the GSD summary template. Include:
- `--explain` flag registration line + help text snippet.
- The before/after of `cli.py:run` execution order (digest → explain → subprocess → rows → summary).
- Three test files modified/created with their assertion counts.
- Confirmation that the Phase 14 negative test was inverted (preserved as `test_run_help_lists_explain_phase16`) OR deleted with the positive coverage living in `test_runner_explain.py`.
- Note any deviations from the planned `_compose_pre_run_skip_reasons` shim attributes if the actual `_compose_unparametrized_skips_from_config` body required different `SimpleNamespace` fields than predicted.
</output>
