---
phase: 18-sdet-test-surface-typed-errors
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/_runner.py
autonomous: true
requirements: [SDET-01, SDET-02, SDET-04]
must_haves:
  truths:
    - "`mcp-test-framework run --sdet` collects only tests/sdet/ (NOT additive over tests/contract/)"
    - "Default `mcp-test-framework run` (no --sdet) still collects tests/contract/ only — zero behavior change"
    - "`--sdet --with-framework` collects tests/sdet/ + tests/framework/"
    - "`--sdet` is NEVER forwarded to pytest's argv (wrapper-owned flag, same pattern as --explain)"
    - "`mcp-test-framework run --help` lists `--sdet` in the output"
    - "_build_pytest_args(sdet=True, with_framework=...) returns the correct discovery paths per D-04/D-05 matrix"
  artifacts:
    - path: "src/mcp_test_framework/cli.py"
      provides: "--sdet flag on run command; threading through to runner"
      contains: "sdet: bool = typer.Option"
    - path: "src/mcp_test_framework/_runner.py"
      provides: "_build_pytest_args gains sdet kwarg; run_pytest_subprocess gains sdet kwarg"
      contains: "sdet: bool = False"
  key_links:
    - from: "cli.py:run command"
      to: "_runner.run_pytest_subprocess"
      via: "sdet=sdet kwarg forwarded"
      pattern: "run_pytest_subprocess\\([^)]*sdet=sdet"
    - from: "_runner._build_pytest_args"
      to: "discovery scope selection (tests/contract/ vs tests/sdet/)"
      via: "if sdet branch selects tests/sdet"
      pattern: "if sdet:"
---

<objective>
Add a `--sdet` flag to the `run` Typer command (D-04: SWAP-not-additive scope; D-05: composes with `--with-framework`). Thread the flag through `_runner.run_pytest_subprocess` and `_runner._build_pytest_args`. The flag is WRAPPER-OWNED — it never appears in the argv handed to pytest (matches Phase 16's `--explain` pattern). Help text documents the four-combination composition matrix per D-05.

Purpose: Wave 1 because CLI plumbing is independent of every other file change. Only the path-building helper `_build_pytest_args` + the subprocess driver `run_pytest_subprocess` are modified in `_runner.py`; the digest renderer + XML parser changes live in Plan 18-06.

Output: Two modified files (`src/mcp_test_framework/cli.py`, `src/mcp_test_framework/_runner.py`).

Note on file overlap: This plan touches `_runner.py:_build_pytest_args` + `_runner.run_pytest_subprocess`. Plan 18-06 touches `_runner.py:parse_junit_xml` + `_render_pre_run_digest` + `--debug` appendix. 18-05 Wave 1, 18-06 Wave 2. 18-06 inherits this plan's signature change for `run_pytest_subprocess(sdet=sdet)`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/_runner.py

<interfaces>
Current `_build_pytest_args` tail (`_runner.py` ~lines 102-109):

```
forwarded = list(pytest_args or [])
args: list[str] = ["tests/contract"]
if with_framework:
    args.append("tests/framework")
if junit_xml is not None:
    args.append(f"--junitxml={junit_xml}")
args.extend(forwarded)
return args
```

Target shape:

```
forwarded = list(pytest_args or [])
if sdet:
    args: list[str] = ["tests/sdet"]   # D-04 swap, not additive
else:
    args = ["tests/contract"]
if with_framework:
    args.append("tests/framework")     # D-05 always additive
if junit_xml is not None:
    args.append(f"--junitxml={junit_xml}")
args.extend(forwarded)
return args
```

Composition matrix (D-05):

| Flag combination          | argv discovery paths                  |
| ------------------------- | ------------------------------------- |
| (default)                 | ["tests/contract"]                    |
| --with-framework          | ["tests/contract", "tests/framework"] |
| --sdet                    | ["tests/sdet"]                        |
| --sdet --with-framework   | ["tests/sdet", "tests/framework"]     |
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add sdet kwarg to _build_pytest_args and run_pytest_subprocess</name>
  <files>src/mcp_test_framework/_runner.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py lines 60-150 (_build_pytest_args full body + run_pytest_subprocess signature)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-04 lines 65; D-05 lines 67-72)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target shapes lines 559-583)
    - .planning/STATE.md lines 78-79 (Phase 16 D-07 pin: --explain wrapper-owned, never forwarded — Phase 18 inherits)
  </read_first>
  <behavior>
    - Test: `_build_pytest_args(sdet=False, with_framework=False, junit_xml=None, pytest_args=[])` returns a list whose first element is `"tests/contract"` AND no element equals `"tests/sdet"`.
    - Test: `_build_pytest_args(sdet=True, with_framework=False, ...)` returns a list whose first element is `"tests/sdet"` AND no element equals `"tests/contract"`.
    - Test: `_build_pytest_args(sdet=True, with_framework=True, ...)` returns a list containing both `"tests/sdet"` and `"tests/framework"` (in that order).
    - Test: `_build_pytest_args(sdet=False, with_framework=True, ...)` returns a list containing `"tests/contract"` then `"tests/framework"` (zero diff from Phase 16 behavior).
    - Test: `--sdet` string is NEVER added to the returned argv (only the discovery path is changed; the wrapper-owned flag itself is consumed by the CLI layer).
    - Test: `run_pytest_subprocess` signature includes `sdet: bool = False` and forwards it to `_build_pytest_args(..., sdet=sdet)`.
  </behavior>
  <action>
Modify `src/mcp_test_framework/_runner.py`:

**Edit A — `_build_pytest_args` signature and discovery-path block:**

1. Add `sdet: bool = False` to the function signature. Place it after `with_framework` (alphabetical-style adjacency by purpose: discovery-scope flags together; preserves call-site readability).
2. Replace the discovery-path block:

Current:
```
args: list[str] = ["tests/contract"]
if with_framework:
    args.append("tests/framework")
```

Replace with:
```
if sdet:
    # Phase 18 D-04: --sdet SWAPS the operator-surface scope (NOT additive).
    args: list[str] = ["tests/sdet"]
else:
    args = ["tests/contract"]
if with_framework:
    # Phase 15 + Phase 18 D-05: --with-framework is ALWAYS additive on top
    # of whichever operator-surface scope is active.
    args.append("tests/framework")
```

Keep the surrounding `forwarded = list(pytest_args or [])` line and the `junit_xml` / `args.extend(forwarded)` / `return args` tail BYTE-IDENTICAL.

**Edit B — `run_pytest_subprocess` signature:**

1. Add `sdet: bool = False` to the function signature (same position as Edit A).
2. Find the `_build_pytest_args(...)` call inside the function body and add `sdet=sdet` to its kwargs.
3. Do NOT modify any other behavior of `run_pytest_subprocess` (raw-mode dispatch, subprocess.run call, exit-code handling, stdout/stderr capture). The function body's only change is forwarding the new kwarg.

**Critical defaults rule:** Both new kwargs default to `False`. The Phase 16 default-path output (no `--sdet`, no `--with-framework`) MUST be byte-identical to current behavior. The existing `tests/framework/unit/test_runner_explain.py` suite asserts this; running it after this edit MUST still pass.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework._runner import _build_pytest_args; a = _build_pytest_args(junit_xml=None, pytest_args=[], with_framework=False, sdet=False); assert 'tests/contract' in a and 'tests/sdet' not in a; b = _build_pytest_args(junit_xml=None, pytest_args=[], with_framework=False, sdet=True); assert 'tests/sdet' in b and 'tests/contract' not in b; c = _build_pytest_args(junit_xml=None, pytest_args=[], with_framework=True, sdet=True); assert 'tests/sdet' in c and 'tests/framework' in c; assert '--sdet' not in c; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "sdet: bool = False" src/mcp_test_framework/_runner.py` returns at least 2 (both functions)
    - `grep -c "if sdet:" src/mcp_test_framework/_runner.py` returns at least 1
    - `grep -c "tests/sdet" src/mcp_test_framework/_runner.py` returns at least 1
    - `grep -c "tests/contract" src/mcp_test_framework/_runner.py` returns at least 1 (preserved else branch)
    - `grep -c "sdet=sdet" src/mcp_test_framework/_runner.py` returns at least 1 (forwarded from run_pytest_subprocess to _build_pytest_args)
    - `uv run pytest tests/framework/unit/test_runner_explain.py -x` passes (Phase 16 default-path regression guard)
    - `uv run pytest tests/framework/test_runner_subprocess.py -x` passes (Phase 14 + 16 subprocess contract guard)
    - `uv run pyright src/mcp_test_framework/_runner.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `_build_pytest_args` and `run_pytest_subprocess` both gain `sdet: bool = False`; the discovery-path block implements D-04 SWAP + D-05 additive correctly; default behavior unchanged.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Register --sdet Typer option on run command + thread to both call sites</name>
  <files>src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/cli.py lines 343-420 (run command signature + flag block, especially `--with-framework` at ~394-405 and `--explain` at ~406-414 for tone-mirror)
    - src/mcp_test_framework/cli.py lines 480-545 (the two `run_pytest_subprocess` call sites — one in --raw branch, one in domain-UI branch)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target Typer option lines 378-390)
    - .planning/STATE.md lines 78-79 (--explain wrapper-owned precedent)
  </read_first>
  <behavior>
    - Test: `CliRunner().invoke(app, ["run", "--help"]).output` contains the literal string `"--sdet"`.
    - Test: `CliRunner().invoke(app, ["run", "--sdet", ...])` with a stubbed `subprocess.run` produces argv whose discovery paths are `["tests/sdet"]` (or `["tests/sdet", "tests/framework"]` if `--with-framework` also present).
    - Test: `--sdet` string never appears in the argv list passed to the stubbed `subprocess.run` (wrapper-owned; same Phase 16 D-07 lock as `--explain`).
    - Test: invoking `run` with no `--sdet` flag at all reproduces the current Phase 16 argv byte-identically.
  </behavior>
  <action>

**Edit A — Register the `--sdet` Typer option in the `run` command signature:**

In the `run` Typer command (in `cli.py`, the block currently containing `--with-framework`, `--explain`, `--raw`, `--debug`, `-q/--quiet` etc. — around lines 349-418), add a new parameter `sdet: bool = typer.Option(...)` immediately AFTER `with_framework` (logical grouping: both flags control discovery scope). Use the help-text VERBATIM:

```
sdet: bool = typer.Option(
    False,
    "--sdet",
    help=(
        "Swap the operator-surface scope from tests/contract/ to "
        "tests/sdet/. Runs SDET-authored scenarios against the active "
        "MCP server. Composes with --with-framework (adds tests/framework/), "
        "--raw (bypass domain UI), --debug (appendix), -q (summary only), "
        "and --explain (per-scenario skip reasons). Default (without "
        "this flag) collects only tests/contract/."
    ),
),
```

**Edit B — Thread `sdet=sdet` into BOTH `run_pytest_subprocess` call sites:**

The `run` command has two call sites for `run_pytest_subprocess`:
1. The `--raw` branch (around line 486) — `raw=True` is passed.
2. The domain-UI branch (around line 541) — captures XML for the renderer.

At BOTH sites, add `sdet=sdet` to the kwargs. Example shape:

```
rc, _tmp, _stdout, _stderr = _runner.run_pytest_subprocess(
    junit_xml=junit_xml,
    pytest_args=pytest_args,
    raw=True,
    with_framework=with_framework,
    sdet=sdet,
)
```

**Wrapper-owned-flag rule (Phase 16 D-07 inherited; STATE.md lines 78-79):**

The `sdet` Typer parameter is consumed by the `run` function — its only effect is to flip the discovery scope inside `_build_pytest_args`. The literal string `--sdet` is NEVER added to `pytest_args` or otherwise forwarded to the subprocess. The test in Plan 18-08 (`test_sdet_cli.py`) will pin this with `assert "--sdet" not in argv`.

**Do NOT touch in this plan:**
- The `_render_pre_run_digest` call site (Plan 18-06 will add scenario-aware dispatch around it).
- The XML parser or renderer (Plan 18-06).
- `tests/sdet/` directory (Plan 18-07).
- Any other Typer command (only `run` changes).
  </action>
  <verify>
    <automated>uv run python -c "from typer.testing import CliRunner; from mcp_test_framework.cli import app; r = CliRunner().invoke(app, ['run', '--help']); assert r.exit_code == 0, r.output; assert '--sdet' in r.output; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '"--sdet"' src/mcp_test_framework/cli.py` returns at least 1 (Typer flag registration)
    - `grep -c "sdet: bool = typer.Option" src/mcp_test_framework/cli.py` returns 1
    - `grep -c "sdet=sdet" src/mcp_test_framework/cli.py` returns 2 (both run_pytest_subprocess call sites)
    - `grep -c "Swap the operator-surface scope from tests/contract/" src/mcp_test_framework/cli.py` returns 1 (help text verbatim)
    - `uv run python -c "from typer.testing import CliRunner; from mcp_test_framework.cli import app; r = CliRunner().invoke(app, ['run', '--help']); assert '--sdet' in r.output, r.output; print('OK')"` exits 0
    - `uv run pytest tests/framework/unit/test_runner_explain.py -x` passes (default-path zero-diff guard)
    - `uv run pyright src/mcp_test_framework/cli.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `--sdet` registered as a Typer boolean option on `run`; help text verbatim from CONTEXT.md; threaded to both `run_pytest_subprocess` call sites via `sdet=sdet`; never appears in pytest argv.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI argv -> Typer | Operator-supplied flag string; Typer parses to bool. No injection vector (boolean flag, no string value). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-11 | T (Tampering) | discovery path string literal | accept | `"tests/sdet"` is a hard-coded source-controlled string; no operator input flows into the path. |
| T-18-12 | I (Info Disclosure) | --help output | accept | Help text contains no secrets; documents composition matrix and discovery scope. |
</threat_model>

<verification>
- `uv run pytest tests/framework/unit/test_runner_explain.py -x` passes (zero-diff guard for default path).
- `uv run pytest tests/framework/test_runner_subprocess.py -x` passes.
- `uv run pytest tests/framework/unit/test_sdet_cli.py -x` passes once Plan 18-08 ships (full D-04/D-05 composition matrix).
- `mcp-test-framework run --help` (or via CliRunner) lists `--sdet` and the composition note.
</verification>

<success_criteria>
- `--sdet` registered as a Typer flag on `run`.
- `_build_pytest_args(sdet=True, ...)` returns `["tests/sdet", ...]`; `sdet=False` returns `["tests/contract", ...]`.
- `--with-framework` is always additive (appended after the operator-surface scope path).
- `--sdet` literal string never appears in argv handed to `subprocess.run`.
- Default behavior (no `--sdet`) is byte-identical to Phase 16.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-05-SUMMARY.md` documenting: the two-function signature change in `_runner.py`, the Typer option registration site, both call-site updates, and the wrapper-owned-flag invariant inherited from Phase 16 D-07.
</output>
