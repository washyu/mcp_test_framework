# Phase 16: Reporter UX overhaul - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 6 (2 modify, 2 create, 2 doc verify)
**Analogs found:** 6 / 6 (all in-repo; this phase polishes Phase 14's renderer)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/_runner.py` (MODIFY: add `_render_pre_run_digest`, `_render_skipped_tools_explain`, `CASES_PER_CONTRACT_TOOL`, `_compose_pre_run_skip_reasons`; remove `_render_header` call at line 773) | renderer | transform (RenderContext -> stdout text) | `_render_header` @ `_runner.py:622-659` and `_render_per_tool_rows` @ `_runner.py:667-717` | exact (same file, same function family) |
| `src/mcp_test_framework/cli.py` (MODIFY: add `--explain` Typer Option; call pre-run renderers before subprocess; gate on `not quiet`) | controller (Typer command) | request-response (CLI args -> orchestrated subprocess) | `--with-framework` flag block @ `cli.py:394-403` + `run` command body @ `cli.py:486-560` | exact (same command, same flag idiom) |
| `tests/framework/unit/test_runner_pre_run_digest.py` (CREATE) | test | request-response (call renderer -> capsys assert) | `tests/framework/test_runner_verbosity.py:48-71` (`render_summary_only` capsys tests) + `tests/framework/unit/test_runner_parser.py:39-47` (locked-constant pin) | exact (same renderer family, same capsys idiom) |
| `tests/framework/unit/test_runner_explain.py` (CREATE) | test | request-response | `tests/framework/test_runner_verbosity.py:139-147` (`--explain` not-in-help test) + the same file's CliRunner end-to-end pattern @ lines 183-219 | exact (same flag family, same CLI test idiom) |
| `tests/framework/test_runner_verbosity.py` (MODIFY: extend with `-q` parity + `-q --explain` no-op tests) | test | request-response | self - existing tests in same file | exact (extension in place) |
| `README.md` (verify "Run the test suite" section), `docs/mcp_test_framework_mvp_spec.md` (verify) | docs | (n/a) | (existing prose sections) | doc-only |

## Pattern Assignments

### `src/mcp_test_framework/_runner.py` (renderer additions)

**Analog 1:** `_render_header` at `src/mcp_test_framework/_runner.py:622-659` — the existing header that Phase 16 splits/repurposes into `_render_pre_run_digest`.

**Imports / module conventions** (`_runner.py:301-306`):
```python
_SKIP_REASON_CAP: int = 3

# Phase 13 D-12 / SAFE-01: two distinct skip-reason strings for opt-in
# tool selection. Module-level constants so they cannot drift silently.
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default
```
Pattern: module-level locked constants with a comment naming the phase decision that locks them and a pointer to the regression test. Phase 16 follows the same shape for `CASES_PER_CONTRACT_TOOL: int = 10` (D-03) and optionally for the banner string.

**`file=None -> sys.stdout at call time` pattern** (`_runner.py:622-642`):
```python
def _render_header(ctx: RenderContext, parsed: ParsedRun, file=None) -> None:
    """...
    `file=None` defaults to sys.stdout resolved at call-time so pytest
    `capsys` capture works (capsys replaces sys.stdout per-test; a
    `file=sys.stdout` default would capture the pre-test stdout at function
    definition time and bypass the fixture).
    """
    if file is None:
        file = sys.stdout
    ran = sorted(parsed.per_tool.keys())
    ...
```
**Copy verbatim.** Every renderer in this module uses it (lines 622, 670, 728, 759, 796, 838). The new `_render_pre_run_digest` and `_render_skipped_tools_explain` MUST start with the same `if file is None: file = sys.stdout` line. Do NOT change the signature to `file=sys.stdout`.

**Banner + label-column layout** (`_runner.py:650-659`):
```python
print("=" * 40, file=file)
print("MCP Test Framework", file=file)
print("=" * 40, file=file)
print(f"MCP server:  {ctx.server_cmd}", file=file)
print(f"Discovered:  {discovered_n} tools", file=file)
print(f"Running:     {running_n:>2}  ({running_text})", file=file)
print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
print(f"Judges:      {judges_text}", file=file)
print(f"Test plan:   {parsed.total_cases} contract cases", file=file)
print("", file=file)  # blank line before per-tool rows
```
**Copy structure exactly.** The 40-equals banner, two-space label-value separator, `:>2` numeric padding, and trailing blank line are all locked by SEED-011 §2 / Phase 14 D-07. The only Phase-16 diffs:
- `parsed.total_cases` -> `running_n * CASES_PER_CONTRACT_TOOL` (pre-run; no JUnit yet)
- Under `--explain`, drop the `(use --explain to list)` parenthetical (Specifics line 181 — render `Skipping:    56` plain when the list follows inline)
- Optionally swap the wallpaper banner string for a module constant (D-Discretion bullet on `"=" * 40`)

**Analog 2:** `_compose_unparametrized_skips_from_config` at `_runner.py:553-592` — the pure composer reused for `--explain`.

**Pure-composer reuse pattern** (call-site to copy from `_runner.py:769-772`):
```python
ran_tools = set(parsed.per_tool.keys())
unparam_skips = _compose_unparametrized_skips_from_config(
    ctx.discovered_tools, ctx.tools_config, ran_tools
)
```
Pre-run analog (D-05 + D-14 thin wrapper):
```python
def _compose_pre_run_skip_reasons(
    discovered_tools: list[str],
    tools_config: dict,
) -> dict[str, str]:
    """Phase 16 D-05/D-14: pre-run skip-reason map for `--explain`.
    Thin wrapper that makes the `ran_tools=set()` pre-run intent explicit
    at the call site (pytest hasn't run yet, so no tool has 'ran')."""
    return _compose_unparametrized_skips_from_config(
        discovered_tools, tools_config, ran_tools=set()
    )
```

**Sorted alphabetical iteration** (`_runner.py:679-684`):
```python
fails = sorted(t for t, v in parsed.per_tool.items() if v.verdict == "FAIL")
skips_xml = {t for t, v in parsed.per_tool.items() if v.verdict == "SKIP"}
passes = sorted(t for t, v in parsed.per_tool.items() if v.verdict == "PASS")
# ...
all_skips = sorted(skips_xml | set(unparam_skips.keys()))
```
**Copy this pattern** for `--explain` line order: `for name in sorted(skipped.keys()): ...`.

**Em-dash separator + column-aligned tool name** (`_runner.py:686-711`):
```python
all_names = list(parsed.per_tool.keys()) + list(unparam_skips.keys())
name_width = max((len(n) for n in all_names), default=0)
# ...
print(f"  {tool.ljust(name_width)}  – {tag} — {reasons_text}", file=file)
```
**U+2014 (`—`) literal** is the separator — NOT ASCII hyphen, NOT `&mdash;`. `--explain` lines should mirror: `  {tool.ljust(name_width)}  — {reason}`. The `ljust(name_width)` column-alignment is the established pattern; copy it. The two-space-before / two-space-after spacing around the em-dash is the convention (see line 696's `  ✗ {tag} — {v.failure_message}`).

**ANSI guard helpers** (`_runner.py:600-614`):
```python
def _ansi_enabled(file) -> bool:
    """Phase 14 D-06: ANSI codes only when file is a TTY. Piped output stays plain."""
    return hasattr(file, "isatty") and file.isatty()


def _green(s: str, file) -> str:
    return f"\x1b[32m{s}\x1b[0m" if _ansi_enabled(file) else s


def _red(s: str, file) -> str:
    return f"\x1b[31m{s}\x1b[0m" if _ansi_enabled(file) else s


def _dim(s: str, file) -> str:
    return f"\x1b[2m{s}\x1b[0m" if _ansi_enabled(file) else s
```
Pre-run digest does not currently colorize anything; if Phase 16 chooses to bold the banner under TTY (Claude's discretion in CONTEXT.md line 129), wrap with `_dim`/equivalent — never call `\x1b[...]` directly.

---

### `src/mcp_test_framework/cli.py` (Typer command edits)

**Analog 1:** Existing `--with-framework` flag block at `cli.py:394-403`:
```python
with_framework: bool = typer.Option(
    False,
    "--with-framework",
    help=(
        "Also collect tests/framework/ (the framework's own self-tests) "
        "in addition to the operator-default tests/contract/. Use this for "
        "maintainer runs and CI jobs that need the full suite. The default "
        "(without this flag) collects only the SUT-contract surface."
    ),
),
```
**Copy this idiom for `--explain`** (per D-08, registered AFTER `--with-framework`):
```python
explain: bool = typer.Option(
    False,
    "--explain",
    help=(
        "Expand the pre-run digest's 'Skipping (N)' hint into one line "
        "per skipped tool with its skip reason. Renders inline before the "
        "subprocess; ignored under --raw and under -q."
    ),
),
```
Position: between `with_framework` and `pytest_args` in the `run` signature (lines 394-407). Help text must mention `--raw` and `-q` interactions per D-08.

**Analog 2:** The existing `run` body flow at `cli.py:486-560`. Insertion points:

**Discovery already runs pre-subprocess** (`cli.py:490`):
```python
discovered_tools = _discover_tools_for_run(cfg)
```
Phase 16 adds `_render_pre_run_digest(ctx)` and `_render_skipped_tools_explain(ctx)` calls AFTER discovery (which already gives the wrapper everything the digest needs) and BEFORE the existing `run_pytest_subprocess` call at line 492.

**RenderContext construction** (`cli.py:522-538`):
```python
server_cmd = f"{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}".strip()
judges_set: set[str] = set()
for tool_cfg in cfg.tools.values():
    for judge_name in getattr(tool_cfg, "judges", []) or []:
        judges_set.add(judge_name)
judges = sorted(judges_set)

ctx = _runner.RenderContext(
    server_cmd=server_cmd,
    discovered_tools=discovered_tools,
    tools_config=cfg.tools,
    judges=judges,
    total_planned_cases=parsed.total_cases,
)
```
**Move this block BEFORE the subprocess** (per D-01 integration flow in CONTEXT.md §code_context lines 162-172). Two options for `total_planned_cases`:
- (i) pre-compute as `len([t for t in discovered_tools if t in cfg.tools and not cfg.tools[t].skip]) * _runner.CASES_PER_CONTRACT_TOOL` and pass to ctx (then digest reads `ctx.total_planned_cases`);
- (ii) leave the field as today and have the digest function compute on the fly.
Pick (i) for symmetry with Phase 14's RenderContext invariant; either works.

**Quiet-mode gating pattern** (`cli.py:545-548`):
```python
if quiet:
    _runner.render_summary_only(parsed, ctx)
else:
    _runner.render_domain_ui(parsed, ctx)
```
**Mirror for pre-run gating** (D-09):
```python
if not quiet:
    _runner._render_pre_run_digest(ctx)
    if explain:
        _runner._render_skipped_tools_explain(ctx)
```
Place BEFORE the `run_pytest_subprocess` call at `cli.py:492`. The post-run `if quiet: render_summary_only else: render_domain_ui` block stays — `render_domain_ui` will be edited in `_runner.py` to drop its `_render_header(ctx, parsed, file=file)` call at line 773 (per D-01).

**`--raw` short-circuit** (`cli.py:470-484`) — leave UNCHANGED. `--raw` bypass at line 470 returns before the digest/explain block ever runs; D-08's "`--raw` ignores `--explain`" composition rule is enforced by ordering alone, no extra code needed.

---

### `tests/framework/unit/test_runner_pre_run_digest.py` (CREATE)

**Analog 1:** `tests/framework/test_runner_verbosity.py:48-71` — capsys-based renderer tests in the same family.

**Test fixture builder pattern** (`test_runner_verbosity.py:34-41`):
```python
def _ctx(discovered=None) -> RenderContext:
    return RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=discovered or ["alpha", "beta", "gamma"],
        tools_config={},
        judges=["clarity"],
        total_planned_cases=0,
    )
```
**Copy verbatim.** Phase 16's tests reuse the same builder shape. May add a `tools_config=` overlay arg for state-(c) coverage.

**capsys assertion pattern** (`test_runner_verbosity.py:48-61`):
```python
def test_render_summary_only_prints_only_summary_line(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    render_summary_only(parsed, _ctx(discovered=["alpha", "gamma", "mango", "zoo"]))
    out = capsys.readouterr().out
    assert "Result:" in out
    assert "MCP Test Framework" not in out
    # ...
```
**Copy this idiom** for `_render_pre_run_digest` tests:
- positive: banner string + `MCP server:` + `Discovered: N tools` + `Running:` + `Skipping:` + `Judges:` + `Test plan:`
- negative: `Result:` NOT in output (pre-run, no JUnit yet); `failures:`/`passing:` NOT in output

**Analog 2:** `tests/framework/unit/test_runner_parser.py:39-47` — locked-constant pin idiom.
```python
def test_runner_skip_reason_constants_locked() -> None:
    """Phase 13 D-12: two reason strings must not drift silently."""
    assert _REASON_NOT_SELECTED == "not selected in config"
    assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"


def test_skip_reason_cap_locked_at_3() -> None:
    """Phase 09 D-05: dedup + cap stays at 3."""
    assert _SKIP_REASON_CAP == 3
```
**Copy this idiom** for the cases-per-tool constant test (D-03):
```python
def test_cases_per_contract_tool_constant_locked() -> None:
    """Phase 16 D-03: pre-run test-plan count = running × CASES_PER_CONTRACT_TOOL."""
    from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL
    assert CASES_PER_CONTRACT_TOOL == 10
```
Plus the drift-guard test that counts parametrized cases in `tests/contract/test_mcp_tool_contract.py` (10 `async def test_…` functions per CONTEXT.md D-03) and asserts equality:
```python
def test_cases_per_contract_tool_matches_actual_parametrize_count() -> None:
    """D-03: constant must equal the number of parametrized cases per tool."""
    import ast
    source = (Path(__file__).resolve().parents[3] / "tests/contract/test_mcp_tool_contract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    test_funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]
    assert len(test_funcs) == CASES_PER_CONTRACT_TOOL
```

**Test fixtures location:**
```python
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
```
(from `test_runner_parser.py:31` — note the `.parent.parent` because the file lives in `tests/framework/unit/`). New tests under `tests/framework/unit/test_runner_pre_run_digest.py` use the same path.

---

### `tests/framework/unit/test_runner_explain.py` (CREATE)

**Analog 1:** `tests/framework/test_runner_verbosity.py:139-147` — flag-in-help / flag-not-in-help test idiom:
```python
def test_run_help_does_not_list_explain() -> None:
    """D-14: --explain is owned by Phase 16, not Phase 14."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--explain " not in result.output
    assert "--explain\n" not in result.output
```
**Phase 16 inverts this:** assert `--explain` IS in help. The Phase 14 negative test at lines 139-147 MUST also be updated/removed in Phase 16 (since `--explain` now registers); flag this in the Phase 16 plan so a passing Phase-14 regression isn't broken silently.

**Analog 2:** End-to-end CliRunner pattern at `test_runner_verbosity.py:183-219`:
```python
def test_run_quiet_renders_summary_only(monkeypatch, tmp_path) -> None:
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
    assert "Result:" in result.output
    assert "MCP Test Framework" not in result.output
```
**Copy this pattern** for `--explain` end-to-end:
- `test_run_explain_lists_skipped_tools_alphabetically` (D-05 sort order)
- `test_run_explain_with_quiet_is_noop` (D-09: quiet wins)
- `test_run_explain_with_raw_is_bypassed` (D-08: `--raw` skips wrapper output)
- `test_run_explain_with_with_framework_is_orthogonal` (D-08)
- `test_run_explain_drops_use_explain_hint_in_digest` (Specifics line 181)

**Stub helpers to copy from `test_runner_verbosity.py:154-180`:**
```python
def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")
    def _fake(argv, **kwargs):
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        return SimpleNamespace(returncode=returncode, stdout="...", stderr="", args=argv)
    return _fake


def _make_valid_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "version: 2\nollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\ntools: {}\n",
        encoding="utf-8",
    )
    return cfg
```
**Reuse / duplicate.** Either import from the existing file or duplicate locally. Duplication is fine for a unit-test module (precedent: `test_runner_parser.py` does its own setup).

---

### `tests/framework/test_runner_verbosity.py` (MODIFY)

**Extension pattern** — append new tests in the existing `# CLI end-to-end` section after line 219. Use the existing `_invoke` / `_stub_subprocess_writing_xml` / `_make_valid_config` helpers (already in the file). Tests to add:
- `test_run_quiet_emits_exactly_one_line` (D-09 + UX-05 parity — single `Result:` line)
- `test_run_quiet_with_explain_is_noop` (D-09)
- Update or remove `test_run_help_does_not_list_explain` at lines 139-147 to reflect Phase 16's registration of `--explain`.

---

## Shared Patterns

### `file=None -> sys.stdout at call time` (capsys-friendly)
**Source:** `_runner.py:641-642, 677-678, 728, 759, 796-797, 838-840`
**Apply to:** Both new renderer functions (`_render_pre_run_digest`, `_render_skipped_tools_explain`)
```python
def _render_X(ctx: RenderContext, ..., file=None) -> None:
    if file is None:
        file = sys.stdout
    ...
```
Why: pytest's `capsys` fixture replaces `sys.stdout` per-test. Default `file=sys.stdout` at signature-time captures the pre-test stdout and bypasses capture. This is documented at `_runner.py:636-639` and reaffirmed in CONTEXT.md §code_context line 153.

### U+2014 em-dash (`—`) as in-line separator
**Source:** `_runner.py:696` (`f"  {tool.ljust(name_width)}  ✗ {tag} — {v.failure_message}"`)
**Apply to:** `--explain` per-line output AND any FAIL/SKIP-shaped extension (e.g., D-11 per-judge breakdown if implemented)
```python
print(f"  {tool.ljust(name_width)}  — {reason}", file=file)
```
Literal `—` in source — UTF-8 encoded. Locked by Phase 09 SC-3 and CONTEXT.md §code_context line 156. `cli.py:451-461` reconfigures stdout to utf-8 with `errors="replace"` so the literal always writes safely on Windows.

### Sorted-alphabetical output for grouped tools
**Source:** `_runner.py:679-684`
**Apply to:** `--explain` line order, any tool-keyed iteration in new code
```python
for tool in sorted(skipped.keys()):
    print(f"  {tool.ljust(name_width)}  — {skipped[tool]}", file=file)
```

### Locked module-level constants with phase-decision comment
**Source:** `_runner.py:301-306` and the regression test at `test_runner_parser.py:39-47`
**Apply to:** `CASES_PER_CONTRACT_TOOL` and (optional) the 40-equals banner string
```python
# Phase 16 D-03: pre-run test-plan count multiplier.
# Pinned by tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_constant_locked.
CASES_PER_CONTRACT_TOOL: int = 10
```

### Typer flag declaration idiom
**Source:** `cli.py:365-403` (any of `--raw`, `--debug`, `-q`, `--with-framework`)
**Apply to:** the new `--explain` flag
```python
explain: bool = typer.Option(
    False,
    "--explain",
    help="<one operator-readable paragraph describing the surface and composition rules>",
),
```
Help text mentions `--raw` and `-q` interactions per D-08.

### Quiet-mode gating idiom in `run`
**Source:** `cli.py:545-548`
**Apply to:** pre-run digest + explain blocks (gate on `not quiet`)
```python
if not quiet:
    _runner._render_pre_run_digest(ctx)
    if explain:
        _runner._render_skipped_tools_explain(ctx)
```

### Reuse of the pure composer
**Source:** `_runner.py:553-592` (`_compose_unparametrized_skips_from_config`) and call sites at `_runner.py:769-772`, `_runner.py:809-812`
**Apply to:** the new `_compose_pre_run_skip_reasons` wrapper and `_render_skipped_tools_explain`
```python
unparam_skips = _compose_unparametrized_skips_from_config(
    discovered_tools, tools_config, ran_tools=set()
)
```
Pre-run call passes `ran_tools=set()` since pytest hasn't run yet.

## No Analog Found

None. Every file targeted by Phase 16 has a strong in-file analog (the phase is a UX polish, not a new module). RESEARCH.md fallback patterns are not needed.

## Metadata

**Analog search scope:** `src/mcp_test_framework/_runner.py`, `src/mcp_test_framework/cli.py`, `tests/framework/`, `tests/framework/unit/`, `tests/contract/test_mcp_tool_contract.py`
**Files scanned:** 7
**Pattern extraction date:** 2026-05-11
