---
phase: 16-reporter-ux-overhaul
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/_runner.py
  - tests/framework/test_runner_renderer.py
autonomous: true
requirements:
  - UX-01
  - UX-03
  - UX-04
must_haves:
  truths:
    - "A new pure function `_render_pre_run_digest(ctx, file=None)` exists in `_runner.py` and emits the 8-line digest before pytest runs."
    - "A module constant `CASES_PER_CONTRACT_TOOL: int = 10` exists in `_runner.py` and is used by the pre-run digest's Test plan line."
    - "A wrapper `_compose_pre_run_skip_reasons(discovered_tools, tools_config)` exists in `_runner.py` and returns the state-(a)/(c) skip-reason dict by delegating to `_compose_unparametrized_skips_from_config(..., ran_tools=set())`."
    - "A new pure function `_render_skipped_tools_explain(ctx, file=None)` exists in `_runner.py` and emits one alphabetically-sorted line per skipped tool with U+2014 em-dash separator."
    - "`render_domain_ui` no longer calls `_render_header` (post-run shrinks to per-tool rows + summary)."
    - "Digest height is ≤ 10 lines regardless of N (10-line cap proven by capsys test at N=70)."
    - "D-02: Pre-run digest emits BEFORE pytest is spawned, so a pytest crash that prevents JUnit XML emission still leaves the operator with the digest already on stdout. No regression vs Phase 14 D-16 — the digest is intentionally more useful pre-crash than post-crash."
  artifacts:
    - path: "src/mcp_test_framework/_runner.py"
      provides: "pre-run digest renderer, explain renderer, CASES_PER_CONTRACT_TOOL constant, _compose_pre_run_skip_reasons wrapper; render_domain_ui call-site updated"
      contains: "def _render_pre_run_digest"
      contains_also: ["CASES_PER_CONTRACT_TOOL", "def _render_skipped_tools_explain", "def _compose_pre_run_skip_reasons"]
  key_links:
    - from: "_render_pre_run_digest"
      to: "RenderContext (discovered_tools, tools_config, judges, server_cmd)"
      via: "function arg ctx"
      pattern: "ctx\\.(discovered_tools|tools_config|judges|server_cmd)"
    - from: "_render_skipped_tools_explain"
      to: "_compose_unparametrized_skips_from_config"
      via: "via _compose_pre_run_skip_reasons wrapper with ran_tools=set()"
      pattern: "_compose_unparametrized_skips_from_config\\(.*ran_tools=set\\(\\)\\)"
    - from: "render_domain_ui"
      to: "_render_per_tool_rows + _render_summary_line ONLY"
      via: "call site at former line 773 deleted"
      pattern: "(?!.*_render_header)"
---

<objective>
Land the pre-run digest renderer family inside `src/mcp_test_framework/_runner.py`. Adds the `CASES_PER_CONTRACT_TOOL` module constant (D-03), the `_render_pre_run_digest` renderer (D-01, D-12), the `_compose_pre_run_skip_reasons` wrapper (D-14), and the `_render_skipped_tools_explain` renderer (D-05, D-13). Removes the `_render_header` call site inside `render_domain_ui` so post-run output shrinks to per-tool rows + summary line only (D-01).

Purpose: All renderer-side surface area for Phase 16 lands here, isolated from the CLI wiring (Plan 02) so renderer shape can be pinned independently of Typer plumbing.

Output: Modified `_runner.py` with four new module-level symbols + one deleted call site. No Typer flag yet (Plan 02). No tests in this plan (tests land in Plan 02 alongside the CLI wiring they exercise end-to-end).
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

<interfaces>
<!-- Locked symbols this plan must reuse — extracted from _runner.py. -->
<!-- Executor does NOT need to re-read the source to discover these. -->

From src/mcp_test_framework/_runner.py:

```python
# Locked constants (Phase 13 D-12, lines 301–306). DO NOT modify, DO NOT rename.
_SKIP_REASON_CAP: int = 3
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default

# RenderContext (lines 534–548). ALL FIELDS THIS PLAN NEEDS ALREADY EXIST.
@dataclass(frozen=True)
class RenderContext:
    server_cmd: str
    discovered_tools: list[str]
    tools_config: dict
    judges: list[str]
    total_planned_cases: int

# Pure composer (lines 553–592). Reuse with ran_tools=set() for pre-run.
def _compose_unparametrized_skips_from_config(
    discovered_tools: list[str],
    tools_config: dict,
    ran_tools: set[str],
) -> dict[str, str]:
    """Returns {tool_name: reason_string} for tools that should appear as
    SKIP in the renderer but never produced a JUnit testcase (state-a
    unlisted + state-c explicit-skip-in-config)."""

# ANSI helpers (lines 600–614). file-aware; safe under pipe/redirect.
def _ansi_enabled(file) -> bool: ...
def _green(s: str, file) -> str: ...
def _red(s: str, file) -> str: ...
def _dim(s: str, file) -> str: ...

# Current header (lines 622–659). MOVE its content into `_render_pre_run_digest`.
# The function may be kept as a private internal OR deleted; the call site at
# line 773 inside `render_domain_ui` MUST be removed regardless.
def _render_header(ctx: RenderContext, parsed: ParsedRun, file=None) -> None:
    # prints 9 lines: 3-line banner + 5 label lines + 1 blank
    # signature reads parsed.total_cases for Test plan line
    ...

# render_domain_ui (lines 755–775). Edit: remove the `_render_header(...)` call at line 773.
def render_domain_ui(parsed, ctx, file=None) -> None:
    if file is None:
        file = sys.stdout
    ran_tools = set(parsed.per_tool.keys())
    unparam_skips = _compose_unparametrized_skips_from_config(
        ctx.discovered_tools, ctx.tools_config, ran_tools
    )
    _render_header(ctx, parsed, file=file)        # <-- DELETE THIS LINE
    _render_per_tool_rows(parsed, unparam_skips, file=file)
    _render_summary_line(parsed, unparam_skips, file=file)
```

The banner string `"=" * 40` is locked (40 equals signs) by Phase 14 D-07. Two-space-separator and `{:>2}` numeric padding in label rows are locked. U+2014 em-dash `—` (literal in source, UTF-8) is the only separator inside FAIL/SKIP/explain lines (Phase 09 SC-3).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add CASES_PER_CONTRACT_TOOL constant and _compose_pre_run_skip_reasons wrapper</name>
  <files>src/mcp_test_framework/_runner.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py (lines 295–310 for the existing constants block; lines 553–592 for the pure composer being wrapped)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-03 + D-14
  </read_first>
  <behavior>
    - `CASES_PER_CONTRACT_TOOL` is importable: `from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL` returns `10`.
    - `_compose_pre_run_skip_reasons(["a","b","c"], {"a": ToolCfg()})` returns the SAME dict shape as `_compose_unparametrized_skips_from_config(["a","b","c"], {"a": ToolCfg()}, ran_tools=set())`.
  </behavior>
  <action>
Insert immediately AFTER the existing `_REASON_EXPLICIT_DEFAULT` constant (around line 306), preserving the existing comment-block structure:

```python
# Phase 16 D-03: pre-run "Test plan" multiplier. Pinned by
# tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_constant_locked
# AND by tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count
# (which AST-counts test_* funcs in tests/contract/test_mcp_tool_contract.py).
# Sources: 5 schema validators + 4 judge dimensions + 1 output conformance = 10.
CASES_PER_CONTRACT_TOOL: int = 10
```

Then add `_compose_pre_run_skip_reasons` as a sibling of `_compose_unparametrized_skips_from_config`. Place it IMMEDIATELY AFTER `_compose_unparametrized_skips_from_config` (around line 593, after that function's `return` statement):

```python
def _compose_pre_run_skip_reasons(
    discovered_tools: list[str],
    tools_config: dict,
) -> dict[str, str]:
    """Phase 16 D-05/D-14: pre-run skip-reason map for `--explain`.

    Thin wrapper that makes the `ran_tools=set()` pre-run intent explicit
    at the call site (pytest hasn't run yet, so no tool has 'ran').
    Returns: {tool_name: reason_string} for every state-(a)/(c) skip.
    """
    return _compose_unparametrized_skips_from_config(
        discovered_tools, tools_config, ran_tools=set()
    )
```

Do NOT change `_compose_unparametrized_skips_from_config`. Do NOT touch the locked `_REASON_NOT_SELECTED` / `_REASON_EXPLICIT_DEFAULT` constants. Do NOT add the constant inside a function — it must be module-level.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL, _compose_pre_run_skip_reasons; assert CASES_PER_CONTRACT_TOOL == 10; assert _compose_pre_run_skip_reasons([], {}) == {}; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "^CASES_PER_CONTRACT_TOOL" src/mcp_test_framework/_runner.py` returns exactly one line and the value is `: int = 10`.
    - `grep -n "^def _compose_pre_run_skip_reasons" src/mcp_test_framework/_runner.py` returns exactly one line.
    - `grep -n "ran_tools=set()" src/mcp_test_framework/_runner.py` shows at least one match inside `_compose_pre_run_skip_reasons`.
    - `grep -c "_REASON_NOT_SELECTED" src/mcp_test_framework/_runner.py` is unchanged from pre-task baseline (constants not duplicated or renamed).
    - `uv run python -c "from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL; assert CASES_PER_CONTRACT_TOOL == 10"` exits 0.
  </acceptance_criteria>
  <done>Both symbols are module-level, importable, and the wrapper delegates to the existing composer with `ran_tools=set()`.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add _render_pre_run_digest function</name>
  <files>src/mcp_test_framework/_runner.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py (lines 615–660 for `_render_header` — the template being adapted)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-01, D-03, D-04, D-12
    - .planning/phases/16-reporter-ux-overhaul/16-PATTERNS.md (Banner + label-column layout block; file=None pattern)
  </read_first>
  <behavior>
    - Calling `_render_pre_run_digest(ctx)` where `ctx` has `discovered_tools=["alpha","beta","gamma"]`, `tools_config={"alpha": cfg_with_skip_false}` (1 running), `judges=["clarity"]`, `server_cmd="uvx homelab-mcp"` emits exactly 9 lines + 1 trailing blank = 10 lines max.
    - Test plan line reads `Test plan:   {running_n * CASES_PER_CONTRACT_TOOL} contract cases` — e.g. `Test plan:   10 contract cases` for 1 running tool.
    - Running tools list is sorted alphabetically.
    - `file=None` defaults to `sys.stdout` AT CALL TIME (capsys-friendly).
    - At N=70 (1 running, 69 skipping), output is still ≤ 10 lines (skipping list is NOT expanded — only the count + `(use --explain to list)` hint).
    - REVISION (Phase 16 checker WARNING 3): When called with `with_framework=True`, the Test plan line is IMMEDIATELY followed by a continuation line `             + framework self-tests` (13 spaces of indent to align under the value column) BEFORE the trailing blank line. No separate blank between `Test plan:` and the `+ framework self-tests` continuation. With `with_framework=False` (default), no suffix.
    - REVISION (Phase 16 checker WARNING 4): When called with `explain=True`, the Skipping line OMITS the `(use --explain to list)` parenthetical — it just reads `Skipping:    {S}` (with no trailing hint). When `explain=False` (default), the hint is present as today. Rationale: under `--explain` the list is rendered right below; the hint would lie.
  </behavior>
  <action>
Add `_render_pre_run_digest` immediately AFTER the existing `_render_header` function (around line 660, before the `# Per-tool rows` comment block at line 662). Copy the layout from `_render_header` exactly, but change two things: (1) compute `running` from `discovered_tools` filtered against `tools_config` (NOT from `parsed.per_tool.keys()` — pytest hasn't run yet), and (2) compute Test plan from `running_n * CASES_PER_CONTRACT_TOOL`.

```python
# ---------------------------------------------------------------------------
# Phase 16 D-01: Pre-run digest — moves SEED-011 §2 header to BEFORE pytest.
# ---------------------------------------------------------------------------


def _render_pre_run_digest(ctx: RenderContext, with_framework: bool = False, explain: bool = False, file=None) -> None:
    """Phase 16 D-01/D-03/D-04/D-12: pre-run digest emitted before pytest runs.

    Lines (exact order, ≤ 10 total in default mode; up to 11 with with_framework=True):
      ========================================
      MCP Test Framework
      ========================================
      MCP server:  {server_cmd}
      Discovered:  {N} tools
      Running:     {R}  ({comma-joined names, sorted})
      Skipping:    {S}  (use --explain to list)   [hint omitted if explain=True]
      Judges:      {comma-joined, sorted}
      Test plan:   {R * CASES_PER_CONTRACT_TOOL} contract cases
                   + framework self-tests        [only if with_framework=True]
      (blank line)

    `file=None` -> sys.stdout at call-time (capsys-friendly; see _render_header
    docstring for the rationale).

    D-04: two buckets only — Running and Skipping. The Phase 13 state-(a) /
    state-(c) distinction is visible in --explain output, not here.
    D-12: digest height ≤ 10 lines regardless of N (the Skipping list is
    NEVER inline-expanded here — `--explain` is the expansion surface).

    Running list is derived from `ctx.discovered_tools` filtered by
    `ctx.tools_config` (state-b: listed AND not skip:true). This matches
    the runtime selection logic in tests/conftest.py without re-importing it.
    """
    if file is None:
        file = sys.stdout

    discovered_n = len(ctx.discovered_tools)
    # state-b: tool is in tools_config AND tools_config[t].skip is not True.
    # Anything else (state-a unlisted, state-c skip:true) is "skipping".
    running = sorted(
        t
        for t in ctx.discovered_tools
        if t in ctx.tools_config and not getattr(ctx.tools_config[t], "skip", False)
    )
    running_n = len(running)
    skipping_n = max(0, discovered_n - running_n)
    judges_text = ", ".join(ctx.judges) if ctx.judges else "(none configured)"
    running_text = ", ".join(running) if running else "(none)"
    planned_cases = running_n * CASES_PER_CONTRACT_TOOL

    print("=" * 40, file=file)
    print("MCP Test Framework", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {discovered_n} tools", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    # REVISION: omit "(use --explain to list)" hint when explain=True (the
    # explain block renders right below, so the hint would lie).
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    print(f"Test plan:   {planned_cases} contract cases", file=file)
    # REVISION: --with-framework suffix emits IMMEDIATELY after Test plan line,
    # BEFORE the trailing blank, as a continuation line. 13-space indent matches
    # the label column width so "+ framework self-tests" visually hangs under
    # the contract-cases value.
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)  # blank line before next section
```

Do NOT delete `_render_header` in this task — it stays for now (Task 4 deletes its call site, but the function body may remain as a tested internal helper for renderer-shape regression coverage). Do NOT alter the banner string from 40 equals signs. Do NOT change the `:>2` padding or two-space label-value separator.

REVISION (checker WARNING 3): The `with_framework: bool = False` parameter IS implemented in this task (option (a) from checker), NOT deferred to Plan 02. The suffix emits inline between the `Test plan:` line and the trailing blank when `with_framework=True`. Plan 02 will pass `with_framework=with_framework` through from `cli.py` instead of emitting the suffix separately.

REVISION (checker WARNING 4): The `explain: bool = False` parameter IS implemented in this task. When `explain=True`, the `Skipping:` line omits the `(use --explain to list)` parenthetical. Plan 02 will pass `explain=explain` through from `cli.py`.
  </action>
  <verify>
    <automated>uv run python -c "import io, sys; from mcp_test_framework._runner import _render_pre_run_digest, RenderContext; from types import SimpleNamespace; ctx = RenderContext(server_cmd='uvx hm', discovered_tools=['a','b','c'], tools_config={'a': SimpleNamespace(skip=False)}, judges=['clarity'], total_planned_cases=0); buf = io.StringIO(); _render_pre_run_digest(ctx, file=buf); out = buf.getvalue(); lines = out.split('\n'); assert lines[0] == '=' * 40, lines[0]; assert 'MCP Test Framework' in out; assert 'Discovered:  3 tools' in out; assert 'Running:      1  (a)' in out, repr(out); assert 'Skipping:     2  (use --explain to list)' in out, repr(out); assert 'Test plan:   10 contract cases' in out, repr(out); buf2 = io.StringIO(); _render_pre_run_digest(ctx, with_framework=True, file=buf2); out2 = buf2.getvalue(); l2 = out2.split('\n'); tp_idx = next(i for i,l in enumerate(l2) if l.startswith('Test plan:')); assert l2[tp_idx+1] == '             + framework self-tests', repr(l2[tp_idx+1]); assert l2[tp_idx+2] == '', repr(l2[tp_idx+2]); buf3 = io.StringIO(); _render_pre_run_digest(ctx, explain=True, file=buf3); out3 = buf3.getvalue(); assert '(use --explain to list)' not in out3, repr(out3); assert 'Skipping:' in out3; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "^def _render_pre_run_digest" src/mcp_test_framework/_runner.py` returns exactly one match.
    - `grep -n "Phase 16 D-01" src/mcp_test_framework/_runner.py` returns at least one match (the new function's comment header).
    - `grep -c '"=" \* 40' src/mcp_test_framework/_runner.py` is ≥ 2 (existing `_render_header` + new function each emit the banner).
    - `grep -c "use --explain to list" src/mcp_test_framework/_runner.py` is ≥ 2 (existing + new).
    - `grep -n "running_n \* CASES_PER_CONTRACT_TOOL" src/mcp_test_framework/_runner.py` returns exactly one match.
    - Smoke-print test in the `<automated>` block above passes (asserts banner, 3 discovered, 1 running named 'a', 2 skipping, 10 planned cases).
    - Function uses `if file is None: file = sys.stdout` (NOT `file=sys.stdout` default at signature time).
    - Function signature is `def _render_pre_run_digest(ctx: RenderContext, with_framework: bool = False, explain: bool = False, file=None) -> None:` exactly (`grep -n "def _render_pre_run_digest" src/mcp_test_framework/_runner.py` shows the with_framework + explain parameters).
    - REVISION (WARNING 3) two-line shape under `with_framework=True`: the line immediately after `Test plan:   10 contract cases` is `             + framework self-tests` (NOT a blank line), and the blank line follows that suffix. The verify-block smoke (extended below) asserts this.
    - REVISION (WARNING 4) hint suppression under `explain=True`: `'(use --explain to list)' not in out` and `'Skipping:' in out`. The verify-block smoke (extended below) asserts this.
  </acceptance_criteria>
  <done>`_render_pre_run_digest` exists at module scope, copies `_render_header`'s 8-line layout exactly, computes Test plan as `running_n * CASES_PER_CONTRACT_TOOL`, and stays ≤ 10 lines at all N.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Add _render_skipped_tools_explain function, remove _render_header call from render_domain_ui, and update affected renderer test</name>
  <files>src/mcp_test_framework/_runner.py, tests/framework/test_runner_renderer.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py (lines 667–717 for `_render_per_tool_rows` — the em-dash + ljust pattern being copied; lines 755–775 for `render_domain_ui` whose line 773 is being deleted)
    - .planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md §decisions D-01, D-05, D-13 + §specifics (the "Skipping (N):" block header decision)
  </read_first>
  <behavior>
    - Calling `_render_skipped_tools_explain(ctx)` with 3 discovered tools, 1 in `tools_config` (skip=False), emits:
      - line 1: `Skipping (2):`
      - lines 2–3: `  <tool>  — <reason>` for the 2 skipping tools, sorted alphabetically
      - line 4: blank
    - Reasons come from `_compose_pre_run_skip_reasons(ctx.discovered_tools, ctx.tools_config)`.
    - U+2014 em-dash `—` is the separator (literal in source, NOT ASCII `--`).
    - Tool names are left-justified to `name_width = max(len(t) for t in skipped)` for column-aligned grep-able output.
    - `render_domain_ui` no longer prints the banner / labels — its output is ONLY the per-tool rows + summary line.
  </behavior>
  <action>
**Part A:** Add `_render_skipped_tools_explain` immediately AFTER `_render_pre_run_digest` from Task 2:

```python
def _render_skipped_tools_explain(ctx: RenderContext, file=None) -> None:
    """Phase 16 D-05/D-13: `--explain` expansion of the digest's Skipping hint.

    Lines (alphabetical order):
      Skipping (N):
        <tool>  — <reason>      [N times, sorted alphabetically]
      (blank line)

    Reasons sourced from `_compose_pre_run_skip_reasons` (Phase 14's pure
    composer called with `ran_tools=set()` since pytest hasn't run yet).

    Format invariants (D-13, grep-able at N=70):
      - One tool per line, no wrapping.
      - U+2014 em-dash separator (matches Phase 09 SC-3 / Phase 14 _render_per_tool_rows).
      - Tool name left-justified to width(longest skipped tool name) for visual scan.
      - Output footprint ≤ N+2 lines (header + N tool lines + 1 trailing blank).

    `file=None` -> sys.stdout at call-time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout

    skipped = _compose_pre_run_skip_reasons(ctx.discovered_tools, ctx.tools_config)
    if not skipped:
        # Edge: nothing to explain. Emit a zero-tool header so the operator
        # sees the empty state explicitly rather than silence.
        print("Skipping (0):", file=file)
        print("", file=file)
        return

    name_width = max(len(t) for t in skipped)
    print(f"Skipping ({len(skipped)}):", file=file)
    for tool in sorted(skipped.keys()):
        # U+2014 em-dash; two spaces before + after. Matches the
        # `  ✗ {tag} — {failure_message}` shape in _render_per_tool_rows.
        print(f"  {tool.ljust(name_width)}  — {skipped[tool]}", file=file)
    print("", file=file)
```

**Part B:** In `render_domain_ui` (around lines 755–775), DELETE the single line:

```python
    _render_header(ctx, parsed, file=file)
```

at what is currently line 773. The surrounding lines (composer call above it, `_render_per_tool_rows` / `_render_summary_line` calls below it) STAY. Update the function's docstring `Order: header -> per-tool rows -> summary line.` to `Order: per-tool rows -> summary line. (Header moved pre-run to _render_pre_run_digest per Phase 16 D-01.)`.

Do NOT delete `_render_header` itself — it remains as an internal helper. Do NOT rename it. Do NOT change its body. Tests in Plan 02 will reference it.

The literal `—` character in the f-string MUST be U+2014 em-dash (UTF-8). Do not substitute ASCII hyphen `-`, ASCII double-hyphen `--`, en-dash `–` (U+2013), or HTML entity. Cli.py already reconfigures stdout to utf-8 with errors='replace' (lines 451–461) so this writes safely on Windows.

**Part C (REVISION — checker BLOCKER 1):** Update `tests/framework/test_runner_renderer.py::test_render_domain_ui_full_flow` (currently at lines 265–283) which directly invokes `render_domain_ui(parsed, ctx)` and asserts `"MCP Test Framework" in out` (line 274). After Part B removes the `_render_header` call site, that assertion fails. Replace the banner assertion with assertions that the per-tool rows + summary line still appear AND that the banner is now absent from `render_domain_ui` output:

```python
def test_render_domain_ui_full_flow(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    ctx = _basic_ctx(
        discovered=["alpha", "gamma", "mango", "zoo", "unlisted"],
        judges=["clarity"],
    )
    render_domain_ui(parsed, ctx)
    out = capsys.readouterr().out
    # Phase 16 D-01: render_domain_ui no longer emits the banner / labels;
    # the digest moved pre-run. Assert the banner is GONE here.
    assert "MCP Test Framework" not in out
    assert "=" * 40 not in out  # banner string absent
    # Per-tool rows
    assert "failures:" in out
    assert "skipped:" in out
    assert "passing:" in out
    # State-(a) unlisted tool surfaces as SKIP
    assert "unlisted" in out
    assert "not selected in config" in out
    # Summary
    assert "Result:" in out
```

Also inspect lines `:148` (`test_render_no_pytest_framing_in_default_output`) and `:255` (`test_no_ansi_codes_when_not_tty`) of the same file: BOTH call `render_domain_ui(parsed, ctx)` but neither currently asserts on banner content (`:148` asserts pytest framing absence + tool names; `:255` asserts ANSI absence). Confirm by re-reading both during execution. If either currently asserts `"MCP Test Framework"` in the output, update it the same way. If neither does, leave them unchanged (likely outcome — pre-revision grep shows the banner-asserting calls live at `:54`, `:274`, and inside the verbosity file).

DO NOT touch any other test in `test_runner_renderer.py`. The `_compose_unparametrized_skips_from_config` direct-call tests, the summary-line tests, and the ANSI guard test are all banner-agnostic and remain valid.
  </action>
  <verify>
    <automated>uv run python -c "import io; from types import SimpleNamespace; from mcp_test_framework._runner import _render_skipped_tools_explain, render_domain_ui, RenderContext, ParsedRun, ToolResult; ctx = RenderContext(server_cmd='x', discovered_tools=['alpha','beta','gamma'], tools_config={'beta': SimpleNamespace(skip=False)}, judges=['clarity'], total_planned_cases=0); buf = io.StringIO(); _render_skipped_tools_explain(ctx, file=buf); out = buf.getvalue(); assert 'Skipping (2):' in out, repr(out); assert '—' in out, 'em-dash missing'; assert 'alpha' in out and 'gamma' in out and 'beta' not in out.replace('Skipping','XXX'), repr(out); alpha_idx = out.index('alpha'); gamma_idx = out.index('gamma'); assert alpha_idx < gamma_idx, 'sort order broken'; parsed = ParsedRun(per_tool={'alpha': ToolResult(verdict='PASS', skip_reasons=[], failure_message=None)}, total_cases=10, passed=10, failed=0, skipped=0, summary_text=''); buf2 = io.StringIO(); render_domain_ui(parsed, ctx, file=buf2); out2 = buf2.getvalue(); assert 'MCP Test Framework' not in out2, 'header should be GONE from render_domain_ui: ' + repr(out2); assert 'Result:' in out2, 'summary line should still emit'; print('OK')"</automated>
    <automated>uv run pytest tests/framework/test_runner_renderer.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "^def _render_skipped_tools_explain" src/mcp_test_framework/_runner.py` returns exactly one match.
    - `grep -c "_render_header(ctx, parsed, file=file)" src/mcp_test_framework/_runner.py` returns 0 (the call site is removed from `render_domain_ui`; the function definition itself does not call itself, so the only previous match is gone).
    - `grep -n "^def _render_header" src/mcp_test_framework/_runner.py` STILL returns exactly one match (function body preserved, only the call site removed).
    - `grep -n "Skipping ({len(skipped)}):" src/mcp_test_framework/_runner.py` returns one match (the new explain header line).
    - `python -c "import io; from mcp_test_framework._runner import _render_skipped_tools_explain; ..."` smoke from `<automated>` passes including assertions: (a) em-dash present, (b) only skipped tools listed (running tool 'beta' absent from list), (c) alpha sorts before gamma, (d) render_domain_ui no longer emits "MCP Test Framework".
    - `grep -c "—" src/mcp_test_framework/_runner.py` (em-dash byte count) increased by at least 1 vs pre-task baseline.
    - REVISION (BLOCKER 1): `tests/framework/test_runner_renderer.py::test_render_domain_ui_full_flow` no longer asserts `"MCP Test Framework" in out`; instead asserts `"MCP Test Framework" not in out` AND `"=" * 40 not in out`. The per-tool rows / SKIP-reason / summary assertions are preserved.
    - REVISION (BLOCKER 1): `grep -c "MCP Test Framework" tests/framework/test_runner_renderer.py` equals the pre-change count minus 1 (the assertion at line 274 inverted from positive to negative — net count drops by 1 since the positive `in out` becomes `not in out`, which still contains the string; if implementer keeps the literal in the negative assertion, count stays the same — accept either, the verification is `uv run pytest tests/framework/test_runner_renderer.py -x -q` passes).
    - REVISION (BLOCKER 1): `uv run pytest tests/framework/test_runner_renderer.py -x -q` passes (whole file).
    - REVISION (BLOCKER 1): `test_render_no_pytest_framing_in_default_output` (`:148`) and `test_no_ansi_codes_when_not_tty` (`:255`) inspected during execution; if either asserts on `"MCP Test Framework"`, updated the same way. If neither does, left unchanged.
  </acceptance_criteria>
  <done>Explain renderer exists with the locked shape; `render_domain_ui` no longer emits the banner/labels; `_render_header` itself is preserved for renderer-shape regression coverage in Plan 02; `test_render_domain_ui_full_flow` updated to assert banner ABSENCE from `render_domain_ui` output (REVISION BLOCKER 1).</done>
</task>

</tasks>

<threat_model>
**STRIDE applicability: NONE.** Phase 16 Plan 01 is pure stdout rendering: new functions consume `RenderContext` (already-validated config + already-discovered tool names) and write to a writable file handle. No new trust boundaries, no new input sources, no new privilege boundaries, no new persisted state, no new network or filesystem reads/writes.

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| (none) | n/a | n/a | n/a | This plan adds pure transform functions over existing in-process data. No security-relevant surface change. |

The existing UTF-8 stdout reconfigure at `cli.py:451–461` (Phase 14 GAP-1 fix) protects the em-dash literal under Windows cp1252 consoles; this plan inherits that mitigation without modifying it.
</threat_model>

<verification>
1. `uv run python -c "from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL, _render_pre_run_digest, _render_skipped_tools_explain, _compose_pre_run_skip_reasons; assert CASES_PER_CONTRACT_TOOL == 10; print('symbols ok')"` exits 0.
2. The smoke `python -c "..."` blocks inside each task's `<automated>` field all pass.
3. Existing Phase 14 test suite still passes: `uv run pytest tests/framework/test_runner_verbosity.py -x` exits 0 (the only at-risk test is `test_run_help_does_not_list_explain` at lines 139–147 — but Plan 01 does NOT add the `--explain` flag, so this test still passes; Plan 02 updates that test when adding the flag).
4. `uv run pytest tests/framework/ -x -q` passes with the same pre-Phase-16 count (no test added, no test broken).
5. N=70 sanity: `uv run python -c "import io; from types import SimpleNamespace; from mcp_test_framework._runner import _render_pre_run_digest, RenderContext; ctx = RenderContext(server_cmd='x', discovered_tools=[f't{i}' for i in range(70)], tools_config={'t0': SimpleNamespace(skip=False), 't1': SimpleNamespace(skip=False)}, judges=['clarity'], total_planned_cases=0); buf = io.StringIO(); _render_pre_run_digest(ctx, file=buf); lines = buf.getvalue().split('\n'); assert len(lines) <= 11, len(lines); print('N=70 digest height:', len(lines))"` — digest is ≤ 10 content lines + trailing newline (`split('\n')` yields ≤ 11 elements; the 11th is empty after the trailing `\n`).
</verification>

<success_criteria>
- `CASES_PER_CONTRACT_TOOL = 10` lives at module scope in `_runner.py`.
- `_compose_pre_run_skip_reasons(discovered, tools_config)` exists and delegates to `_compose_unparametrized_skips_from_config(discovered, tools_config, ran_tools=set())`.
- `_render_pre_run_digest(ctx, file=None)` exists, follows the file=None-at-call-time pattern, emits exactly the 8-line label block + 1 trailing blank, and computes Test plan as `running_n * CASES_PER_CONTRACT_TOOL`.
- `_render_skipped_tools_explain(ctx, file=None)` exists, emits `Skipping (N):` header + alphabetically-sorted `  <tool>  — <reason>` lines + trailing blank, uses U+2014 em-dash literal.
- `render_domain_ui` no longer calls `_render_header`; post-run output is per-tool rows + summary line ONLY.
- All existing `tests/framework/` and `tests/contract/` tests still pass (no regression).
- N=70 digest fits in ≤ 10 content lines (D-12 invariant satisfied by construction — the only tool-count-sensitive line is the `Running:` line, which lists ONLY running tools, not all 70).
</success_criteria>

<output>
After completion, create `.planning/phases/16-reporter-ux-overhaul/16-01-SUMMARY.md` per the GSD summary template. Include:
- The four new module-level symbols (constant + 3 functions).
- The one deleted call site (`_render_header(ctx, parsed, file=file)` inside `render_domain_ui`).
- Note that `_render_header` itself is preserved (Plan 02 may exercise it for renderer-shape regression tests).
- Confirmation that no existing test was modified in Plan 01.
</output>
