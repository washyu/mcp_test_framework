---
phase: 16-reporter-ux-overhaul
plan: 05
type: execute
wave: 1
depends_on: []
gap_closure: true
autonomous: true
files_modified:
  - src/mcp_test_framework/cli.py
  - src/mcp_test_framework/_runner.py
  - tests/framework/unit/test_runner_pre_run_digest.py
requirements: [UX-01]
commit_message: "feat(16-05): expand digest judges union to honor TOOLCFG-06 None default"

must_haves:
  truths:
    - "`cli.py:run` does NOT contain `getattr(tool_cfg, 'judges', []) or []`-style union loop; instead it calls `_compose_judges_from_tool_configs(cfg.tools)` from `_runner`."
    - "`_runner.py` exports `_compose_judges_from_tool_configs(tools_config) -> list[str]` that returns `RUBRIC_IDS` ∪ explicit-list judges, expanding `None` (TOOLCFG-06 default) to all rubrics and treating `[]` as explicit opt-out (contributes nothing)."
    - "Three unit tests in `test_runner_pre_run_digest.py` pin the None / [] / subset semantics of the digest's `Judges:` line by exercising the helper and `_render_pre_run_digest` end-to-end."
    - "Running `mcp-test-framework run --config config.yaml` (the UAT repro recipe: two tools, both with `judges` unset) emits `Judges:      clarity, disambiguation, parameters` instead of `(none configured)`."
  artifacts:
    - path: "src/mcp_test_framework/_runner.py"
      provides: "Pure helper `_compose_judges_from_tool_configs(tools_config) -> list[str]` that honors TOOLCFG-06's None-means-all-rubrics semantic"
      contains: "_compose_judges_from_tool_configs"
    - path: "src/mcp_test_framework/cli.py"
      provides: "RenderContext.judges sourced from the new helper at both build sites (pre-run digest ctx + post-run summary ctx rebuild)"
      contains: "_compose_judges_from_tool_configs"
    - path: "tests/framework/unit/test_runner_pre_run_digest.py"
      provides: "Regression tests pinning Judges-line behavior across None / [] / subset"
      contains: "test_judges_line_lists_all_rubrics_when_judges_unset"
  key_links:
    - from: "src/mcp_test_framework/cli.py:run"
      to: "_runner._compose_judges_from_tool_configs"
      via: "direct call replacing the local union loop at lines ~512-516"
      pattern: "_compose_judges_from_tool_configs\\(cfg\\.tools\\)"
    - from: "src/mcp_test_framework/_runner.py:_compose_judges_from_tool_configs"
      to: "src/mcp_test_framework/rubrics.RUBRIC_IDS"
      via: "import at module top + set.update(RUBRIC_IDS) when ToolConfig.judges is None"
      pattern: "from \\.rubrics import RUBRIC_IDS"
---

<objective>
Close the gap recorded in `16-VERIFICATION.md` `gaps_remaining[0]` (live UAT 2026-05-12): the pre-run digest's `Judges:` line reports `(none configured)` when judges actually fire at runtime, violating UX-01 / SC-1's "unambiguous pre-run digest of what will execute" contract.

Root cause: `cli.py:512-516` builds the judges union via `getattr(tool_cfg, "judges", []) or []`. When `tool_cfg.judges is None` (the TOOLCFG-06 default in `models.py:98`, semantically meaning "run all rubrics"), this evaluates to `[]` and contributes nothing — so a config where every tool defaults gives an empty union, and the renderer (correctly) prints `(none configured)`.

Fix: extract the union into a pure helper `_compose_judges_from_tool_configs(tools_config)` in `_runner.py` that expands `None` to `RUBRIC_IDS` before unioning, leaves `[]` as a no-op (explicit opt-out per the model validator's TOOLCFG-06 contract), and passes literal subsets through. Replace the two `cli.py` call sites (pre-run digest ctx at ~line 512 + post-run summary ctx rebuild's reuse at ~line 577) with one helper call (the upstream `judges` variable is reused by both, so a single computation site changes).

Purpose: restore truthfulness between digest and runtime, honoring the three-way `judges` semantic that the runtime contract gates at `tests/contract/test_mcp_tool_contract.py:124,154,185` already enforce.

Output: 1 new helper (~6 LOC + docstring), 1 modified call site in `cli.py` (5-line loop → 1-line call), 3 new unit tests (~40 LOC), `RUBRIC_IDS` import added to `_runner.py`. Total surface: ~25 LOC of production change + ~40 LOC of tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/16-reporter-ux-overhaul/16-CONTEXT.md
@.planning/phases/16-reporter-ux-overhaul/16-VERIFICATION.md
@.planning/phases/16-reporter-ux-overhaul/16-HUMAN-UAT.md
@.planning/phases/16-reporter-ux-overhaul/16-02-explain-flag-and-cli-wiring-SUMMARY.md
@src/mcp_test_framework/cli.py
@src/mcp_test_framework/_runner.py
@src/mcp_test_framework/models.py
@src/mcp_test_framework/rubrics.py
@tests/contract/test_mcp_tool_contract.py
@tests/framework/unit/test_runner_pre_run_digest.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->
<!-- Use these directly — no codebase exploration needed. -->

From src/mcp_test_framework/models.py (ToolConfig — lines 93-118):
```python
class ToolConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")
    skip: bool = False
    skip_reason: Optional[str] = None
    call_arguments: dict[str, Any] = Field(default_factory=dict)
    judges: Optional[list[str]] = None   # TOOLCFG-06: None = run all rubrics; [] = explicit opt-out
    setup: Optional[Any] = None
    depends_on: Optional[list[str]] = None

    @field_validator("judges", mode="after")
    @classmethod
    def _validate_judge_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        # None is permitted; means "run all available rubrics" per TOOLCFG-06.
        # Empty list [] is permitted; means "explicit opt-out — run no rubrics on this tool".
        # Non-empty list: each ID must resolve via resolve_rubric_id.
        ...
```

From src/mcp_test_framework/rubrics.py (lines 103-105):
```python
RUBRIC_IDS: frozenset[str] = frozenset(
    {ClarityRubric.id, DisambiguationRubric.id, ParametersRubric.id}
)
# Concrete values: {"clarity", "disambiguation", "parameters"}
```

From src/mcp_test_framework/_runner.py (RenderContext — lines 541-557):
```python
@dataclass
class RenderContext:
    server_cmd: str
    discovered_tools: list[str] = field(default_factory=list)
    tools_config: dict = field(default_factory=dict)  # name -> ToolConfig
    judges: list[str] = field(default_factory=list)
    total_planned_cases: int = 0
```

From src/mcp_test_framework/_runner.py (existing pure composer pattern, lines 602-628):
```python
def _compose_pre_run_skip_reasons(
    discovered_tools: list[str],
    tools_config: dict,
) -> dict[str, str]:
    """Phase 16 D-05/D-14: pre-run skip-reason map for `--explain`. ..."""
    running: set[str] = {
        name
        for name in discovered_tools
        if name in tools_config and not getattr(tools_config[name], "skip", False)
    }
    return _compose_unparametrized_skips_from_config(
        discovered_tools, tools_config, ran_tools=running
    )
```
The new `_compose_judges_from_tool_configs` follows the same shape: pure function, same neighbourhood, no side effects.

Current buggy union in src/mcp_test_framework/cli.py (lines 510-516):
```python
# Judges: derive from the union of every configured tool's `judges`
# list, de-duplicated and sorted.
judges_set: set[str] = set()
for tool_cfg in cfg.tools.values():
    for judge_name in getattr(tool_cfg, "judges", []) or []:
        judges_set.add(judge_name)
judges = sorted(judges_set)
```

Downstream consumers (single `judges` variable feeds two RenderContext builds):
- `cli.py:522` — `pre_run_ctx = _runner.RenderContext(..., judges=judges, ...)` (pre-run digest)
- `cli.py:577` — `ctx = _runner.RenderContext(..., judges=judges, ...)` (post-run summary)

Renderer call site (no change needed — correctly handles empty input):
- `_runner.py:749` — `judges_text = ", ".join(ctx.judges) if ctx.judges else "(none configured)"`
- `_runner.py:765` — `print(f"Judges:      {judges_text}", file=file)`

Existing test file shape (tests/framework/unit/test_runner_pre_run_digest.py):
- Uses `from types import SimpleNamespace` to build lightweight ToolConfig stand-ins (`SimpleNamespace(skip=False)`).
- Uses `_ctx(...)` helper at lines 37-51 that wraps `RenderContext(...)`.
- Uses `capsys` to capture `_render_pre_run_digest` stdout.
- Imports: `from mcp_test_framework._runner import (CASES_PER_CONTRACT_TOOL, RenderContext, _compose_pre_run_skip_reasons, _render_pre_run_digest,)`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add `_compose_judges_from_tool_configs` pure helper to `_runner.py`</name>
  <files>src/mcp_test_framework/_runner.py</files>

  <read_first>
    1. src/mcp_test_framework/_runner.py lines 1-50 (module docstring + imports — confirm where to add the `from .rubrics import RUBRIC_IDS` import; module is currently stdlib-only at top + `import typer`).
    2. src/mcp_test_framework/_runner.py lines 600-630 (`_compose_pre_run_skip_reasons` — the neighbour pure composer this helper sits next to; mirror its shape and docstring style).
    3. src/mcp_test_framework/models.py lines 93-119 (ToolConfig.judges Optional[list[str]] field + validator that pins the None/[]/subset semantic).
    4. src/mcp_test_framework/rubrics.py lines 103-105 (`RUBRIC_IDS: frozenset[str]` definition).
    5. tests/contract/test_mcp_tool_contract.py lines 120-190 (the three contract gates at lines 124, 154, 185 that establish the runtime None/[]/subset behavior this helper mirrors at digest time).
  </read_first>

  <action>
Step 1 — Add the import. Find the existing import block at the top of `src/mcp_test_framework/_runner.py` (lines 28-41). After the `import typer` line, add this import. The import is intra-package and follows the existing pattern (this module is the only one in `mcp_test_framework/` that doesn't yet import from siblings, so a new sibling import goes after the stdlib + third-party block):

```python
from .rubrics import RUBRIC_IDS
```

Step 2 — Add the helper function. Locate `_compose_pre_run_skip_reasons` (currently ends at line 628 with the call to `_compose_unparametrized_skips_from_config(...)`). Immediately after it, BEFORE the `# --- ANSI guard helpers (D-06 ...)` section header at line 631, insert this function VERBATIM:

```python
def _compose_judges_from_tool_configs(tools_config: dict) -> list[str]:
    """Phase 16 plan 05: build the digest's `Judges:` union, honoring TOOLCFG-06.

    ToolConfig.judges semantics (locked at models.py:98 + contract gates at
    tests/contract/test_mcp_tool_contract.py:124,154,185):
      - None  (default, unset)      -> run ALL rubrics in RUBRIC_IDS
      - []    (explicit empty list) -> explicit opt-out, run no rubrics on this tool
      - [...] (subset list)         -> run literally these rubrics

    The pre-run digest must reflect what will actually execute. Pre-plan-05,
    cli.py's union loop used `getattr(tool_cfg, "judges", []) or []`, which
    silently collapsed the None default to [] and produced an empty union
    even when every tool was running all three rubrics at runtime.

    Returns: sorted list of rubric IDs that will fire for at least one
    configured tool. Empty list iff every tool explicitly opts out via [].
    """
    judges_set: set[str] = set()
    for tool_cfg in tools_config.values():
        declared = getattr(tool_cfg, "judges", None)
        if declared is None:
            judges_set.update(RUBRIC_IDS)  # TOOLCFG-06: None = run all rubrics
        else:
            judges_set.update(declared)    # [] is a no-op; subset passes through
    return sorted(judges_set)
```

The function is pure (no I/O, no module state mutation), takes `dict` (matching the existing `RenderContext.tools_config: dict` field type), and returns `list[str]` sorted alphabetically (matching the prior `sorted(judges_set)` shape that cli.py emitted).
  </action>

  <verify>
    <automated>uv run python -c "from mcp_test_framework._runner import _compose_judges_from_tool_configs; from mcp_test_framework.models import ToolConfig; assert _compose_judges_from_tool_configs({'a': ToolConfig(), 'b': ToolConfig()}) == ['clarity', 'disambiguation', 'parameters']; assert _compose_judges_from_tool_configs({'a': ToolConfig(judges=[])}) == []; assert _compose_judges_from_tool_configs({'a': ToolConfig(judges=['clarity'])}) == ['clarity']; print('OK')"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c '_compose_judges_from_tool_configs' src/mcp_test_framework/_runner.py` >= 2 (def + docstring mention)
    - `grep -c 'from .rubrics import RUBRIC_IDS' src/mcp_test_framework/_runner.py` == 1
    - `grep -c 'RUBRIC_IDS' src/mcp_test_framework/_runner.py` >= 2 (import + usage in the helper)
    - `uv run python -c "from mcp_test_framework._runner import _compose_judges_from_tool_configs"` exits 0
    - Function returns `['clarity', 'disambiguation', 'parameters']` for `{'a': ToolConfig(), 'b': ToolConfig()}` (both judges=None default)
    - Function returns `[]` for `{'a': ToolConfig(judges=[])}` (explicit opt-out)
    - Function returns `['clarity']` for `{'a': ToolConfig(judges=['clarity'])}` (subset passthrough)
  </acceptance_criteria>

  <done>
`_compose_judges_from_tool_configs` is exported from `mcp_test_framework._runner`, sits next to `_compose_pre_run_skip_reasons` for code locality, imports `RUBRIC_IDS` from `.rubrics`, and behaves correctly across all three TOOLCFG-06 cases (None/[]/subset) as verified by the inline Python smoke check above.
  </done>
</task>

<task type="auto">
  <name>Task 2: Replace the buggy union loop in `cli.py:run` with a single helper call</name>
  <files>src/mcp_test_framework/cli.py</files>

  <read_first>
    1. src/mcp_test_framework/cli.py lines 1-50 (module imports — confirm `_runner` is imported as a module alias so `_runner._compose_judges_from_tool_configs(...)` is the right call shape).
    2. src/mcp_test_framework/cli.py lines 490-600 (the full `run` command body around the union loop — see the buggy block at 510-516, the pre-run RenderContext build at 518-524, the post-run RenderContext rebuild at 570-579; confirm `judges` is computed ONCE and reused by both RenderContext constructions).
    3. src/mcp_test_framework/_runner.py around the new helper added in Task 1 (confirm signature `_compose_judges_from_tool_configs(tools_config) -> list[str]`).
    4. src/mcp_test_framework/models.py lines 93-99 (ToolConfig.judges default reminder).
    5. tests/framework/unit/test_runner_pre_run_digest.py (existing tests must keep passing — the helper preserves the empty-list-on-empty-tools and subset behaviors that `test_pre_run_digest_handles_empty_judges` relies on).
  </read_first>

  <action>
Step 1 — Locate the buggy block. In `src/mcp_test_framework/cli.py`, find lines 510-516 (inside the `run` function, between the `server_cmd = ...` line and the `pre_run_ctx = _runner.RenderContext(...)` construction).

Step 2 — Replace the block. The BEFORE block (5 lines of bug, with the leading comment line 510-511) is:

```python
    # Judges: derive from the union of every configured tool's `judges`
    # list, de-duplicated and sorted.
    judges_set: set[str] = set()
    for tool_cfg in cfg.tools.values():
        for judge_name in getattr(tool_cfg, "judges", []) or []:
            judges_set.add(judge_name)
    judges = sorted(judges_set)
```

Replace it with this AFTER block (preserving the comment intent + adding the TOOLCFG-06 explanation, since the bug stemmed from missing that semantic at this call site):

```python
    # Judges: derive from the union of every configured tool's `judges`
    # list, de-duplicated and sorted. ToolConfig.judges semantics per
    # TOOLCFG-06 (models.py:98): None default => run ALL rubrics; []
    # => explicit opt-out; subset => literal. The helper honors this
    # three-way contract; a prior loop using `or []` silently collapsed
    # None to [] and produced an empty union (16-VERIFICATION.md gap G-1).
    judges = _runner._compose_judges_from_tool_configs(cfg.tools)
```

Step 3 — Verify the downstream wiring is unchanged. The `judges` local is consumed at TWO RenderContext build sites (no second edit needed; both pick up the helper's output via the single `judges` variable):
  - Line ~522 (pre-run): `pre_run_ctx = _runner.RenderContext(..., judges=judges, ...)`
  - Line ~577 (post-run rebuild): `ctx = _runner.RenderContext(..., judges=judges, ...)`

Do NOT touch lines 518-524 or 570-579. Do NOT touch the `_render_pre_run_digest` call at line 533. The renderer correctly emits `", ".join(ctx.judges) if ctx.judges else "(none configured)"` at `_runner.py:749`; with the helper returning the populated list, the digest's `Judges:` line now reads `Judges:      clarity, disambiguation, parameters` for the UAT repro.

Step 4 — No new import needed at the top of `cli.py`. The call goes through the existing `import mcp_test_framework._runner as _runner` (or equivalent module-alias pattern already used at line 533: `_runner._render_pre_run_digest(...)` and line 539: `_runner._render_skipped_tools_explain(...)`). Confirm during the Read pass; if the import is `from . import _runner` or `import mcp_test_framework._runner as _runner`, both expose `_runner._compose_judges_from_tool_configs` without further work.
  </action>

  <verify>
    <automated>uv run python -c "import re, pathlib; src = pathlib.Path('src/mcp_test_framework/cli.py').read_text(encoding='utf-8'); assert '_compose_judges_from_tool_configs(cfg.tools)' in src, 'helper call missing'; assert 'getattr(tool_cfg, \"judges\", []) or []' not in src, 'old buggy loop still present'; assert 'judges_set: set[str] = set()' not in src, 'old union loop still present'; print('OK')"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c '_compose_judges_from_tool_configs' src/mcp_test_framework/cli.py` >= 1
    - `grep -c 'getattr(tool_cfg, "judges", \[\]) or \[\]' src/mcp_test_framework/cli.py` == 0 (old buggy pattern eradicated)
    - `grep -c 'judges_set: set\[str\] = set()' src/mcp_test_framework/cli.py` == 0 (old union loop variable eradicated)
    - `grep -c 'for tool_cfg in cfg.tools.values():' src/mcp_test_framework/cli.py` == 0 (old loop header eradicated)
    - `grep -c 'judges = _runner._compose_judges_from_tool_configs(cfg.tools)' src/mcp_test_framework/cli.py` == 1
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -q` exits 0 (existing 7 tests still pass — no regression)
    - `uv run python -c "from mcp_test_framework.cli import run; print('importable')"` exits 0 (no import error from the edit)
  </acceptance_criteria>

  <done>
The 5-line union loop at `cli.py:512-516` is replaced by a single helper call `judges = _runner._compose_judges_from_tool_configs(cfg.tools)`. The pre-run digest's `Judges:` line now reflects what runs at runtime for the UAT repro config. No other cli.py logic changes; both RenderContext build sites pick up the fix transparently via the unchanged `judges` variable.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add three unit tests pinning the Judges-line semantic (None / [] / subset)</name>
  <files>tests/framework/unit/test_runner_pre_run_digest.py</files>

  <read_first>
    1. tests/framework/unit/test_runner_pre_run_digest.py (full — 212 lines; locate the import block at lines 18-23, the `_ctx` helper at lines 37-51, the existing `test_pre_run_digest_handles_empty_judges` at lines 164-172, and the trailing `_compose_pre_run_skip_reasons` block at lines 175-211 — new tests append at end of file).
    2. src/mcp_test_framework/_runner.py — the `_compose_judges_from_tool_configs` helper added in Task 1, plus the `_render_pre_run_digest` function at lines 703-773 (these new tests must drive the helper AND the renderer to confirm the integrated behavior, not just helper-level unit logic).
    3. src/mcp_test_framework/models.py lines 93-119 (ToolConfig — needed to instantiate real ToolConfig objects rather than SimpleNamespace stubs, because the helper distinguishes `judges=None` (TOOLCFG-06 default) from `judges=[]` (explicit opt-out) and SimpleNamespace's `getattr` returns the literal attribute or AttributeError — using ToolConfig is the more honest fixture and matches how `cli.py` constructs the live dict).
    4. src/mcp_test_framework/rubrics.py lines 103-105 (RUBRIC_IDS — confirm test assertions for "all rubrics" reference the canonical set: `{"clarity", "disambiguation", "parameters"}`).
  </read_first>

  <action>
Step 1 — Extend the imports at the top of `tests/framework/unit/test_runner_pre_run_digest.py`. Find the import block at lines 18-23. Replace it with this expanded version that adds `_compose_judges_from_tool_configs` and brings in the real `ToolConfig` model (the SimpleNamespace stubs the existing tests use don't distinguish "attribute is None" from "attribute is absent" cleanly enough for this gap's semantics):

```python
from mcp_test_framework._runner import (
    CASES_PER_CONTRACT_TOOL,
    RenderContext,
    _compose_judges_from_tool_configs,
    _compose_pre_run_skip_reasons,
    _render_pre_run_digest,
)
from mcp_test_framework.models import ToolConfig
```

Step 2 — Append three new test functions at the END of the file (after `test_compose_pre_run_skip_reasons_state_c_custom_reason` at line 206-211). Add this section header comment first, then the three test bodies VERBATIM:

```python


# ---------------------------------------------------------------------------
# Phase 16 plan 05: digest `Judges:` line honors TOOLCFG-06 None semantic
# (gap G-1 from 16-VERIFICATION.md, live UAT 2026-05-12).
# Tests drive both the helper and the renderer to pin end-to-end behavior.
# ---------------------------------------------------------------------------


def test_judges_line_lists_all_rubrics_when_judges_unset(capsys) -> None:
    """TOOLCFG-06: ToolConfig.judges default `None` semantically means
    'run all rubrics'. The digest's `Judges:` line MUST reflect that.

    Pre-plan-05 bug: cli.py's union loop used `getattr(tool_cfg, 'judges',
    []) or []` which collapsed None -> [] and rendered `(none configured)`
    while the runtime contract gates at test_mcp_tool_contract.py:124,154,185
    fired all three rubrics anyway. The digest was lying about runtime.
    """
    # Both tools have judges field unset (TOOLCFG-06 default = None).
    tools_config = {
        "list_keyring_credentials": ToolConfig(),
        "suggest_deployments": ToolConfig(),
    }
    # Verify helper output directly.
    assert _compose_judges_from_tool_configs(tools_config) == [
        "clarity",
        "disambiguation",
        "parameters",
    ]
    # Verify end-to-end via the renderer (the operator-facing surface).
    ctx = RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=["list_keyring_credentials", "suggest_deployments"],
        tools_config=tools_config,
        judges=_compose_judges_from_tool_configs(tools_config),
        total_planned_cases=0,
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "Judges:      clarity, disambiguation, parameters" in out, repr(out)
    assert "(none configured)" not in out, (
        "digest must NOT report '(none configured)' when judges field defaults "
        "to None (TOOLCFG-06 means 'run all rubrics'). G-1 regression."
    )


def test_judges_line_reports_none_configured_when_judges_explicitly_empty(
    capsys,
) -> None:
    """TOOLCFG-06: `judges: []` (explicit empty list) means 'explicit
    opt-out, run no rubrics on this tool'. With every tool opting out,
    the union is empty and the renderer correctly emits '(none configured)'.

    This is the ONLY path that should produce '(none configured)' — the
    default-None path covered by the test above must NOT.
    """
    tools_config = {"list_keyring_credentials": ToolConfig(judges=[])}
    assert _compose_judges_from_tool_configs(tools_config) == []
    ctx = RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=["list_keyring_credentials"],
        tools_config=tools_config,
        judges=_compose_judges_from_tool_configs(tools_config),
        total_planned_cases=0,
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "Judges:      (none configured)" in out, repr(out)


def test_judges_line_lists_subset_when_judges_explicit(capsys) -> None:
    """TOOLCFG-06: explicit subset lists pass through literally and the
    union de-duplicates + sorts alphabetically. With tool A: ['clarity']
    and tool B: ['parameters'], the digest shows 'clarity, parameters'
    (sorted, deduped, no 'disambiguation' since neither tool runs it).
    """
    tools_config = {
        "tool_a": ToolConfig(judges=["clarity"]),
        "tool_b": ToolConfig(judges=["parameters"]),
    }
    assert _compose_judges_from_tool_configs(tools_config) == [
        "clarity",
        "parameters",
    ]
    ctx = RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=["tool_a", "tool_b"],
        tools_config=tools_config,
        judges=_compose_judges_from_tool_configs(tools_config),
        total_planned_cases=0,
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "Judges:      clarity, parameters" in out, repr(out)
    # Disambiguation must NOT appear — neither tool opted into it.
    assert "disambiguation" not in out, (
        f"'disambiguation' leaked into digest despite no tool requesting it: {out!r}"
    )
```

Step 3 — Do NOT modify any existing test in the file. The existing `test_pre_run_digest_handles_empty_judges` at lines 164-172 already pins the renderer's behavior given an empty `ctx.judges` list — it's still correct and still passes. The new tests pin the upstream computation that PRODUCES that list (and which the gap exposed was broken).
  </action>

  <verify>
    <automated>uv run pytest tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_lists_all_rubrics_when_judges_unset tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_reports_none_configured_when_judges_explicitly_empty tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_lists_subset_when_judges_explicit -q</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c 'test_judges_line_lists_all_rubrics_when_judges_unset' tests/framework/unit/test_runner_pre_run_digest.py` == 1
    - `grep -c 'test_judges_line_reports_none_configured_when_judges_explicitly_empty' tests/framework/unit/test_runner_pre_run_digest.py` == 1
    - `grep -c 'test_judges_line_lists_subset_when_judges_explicit' tests/framework/unit/test_runner_pre_run_digest.py` == 1
    - `grep -c 'from mcp_test_framework.models import ToolConfig' tests/framework/unit/test_runner_pre_run_digest.py` == 1
    - `grep -c '_compose_judges_from_tool_configs' tests/framework/unit/test_runner_pre_run_digest.py` >= 4 (import + 3 test bodies)
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_lists_all_rubrics_when_judges_unset -q` exits 0
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_reports_none_configured_when_judges_explicitly_empty -q` exits 0
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py::test_judges_line_lists_subset_when_judges_explicit -q` exits 0
    - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -q` exits 0 (full file — pre-existing 11 tests + 3 new = 14 tests, all passing, no regression)
  </acceptance_criteria>

  <done>
Three new tests live at the end of `tests/framework/unit/test_runner_pre_run_digest.py`, each exercising both the new `_compose_judges_from_tool_configs` helper directly AND the `_render_pre_run_digest` renderer end-to-end via capsys. They pin the None / [] / subset cases of TOOLCFG-06 against the digest's `Judges:` line. The full digest test file passes (existing 11 + new 3 = 14).
  </done>
</task>

</tasks>

<verification>
**Automated phase-level checks (run after all three tasks complete):**

1. **Full new-test suite:**
   - `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -q` exits 0 (14 tests pass: 11 pre-existing + 3 new).

2. **No regression in adjacent test files (Phase 16 surface):**
   - `uv run pytest tests/framework/unit/test_runner_explain.py -q` exits 0.
   - `uv run pytest tests/framework/test_runner_verbosity.py -q` exits 0.

3. **Old buggy pattern fully eradicated:**
   - `grep -c 'getattr(tool_cfg, "judges", \[\]) or \[\]' src/mcp_test_framework/cli.py` returns `0`.
   - `grep -c 'judges_set: set\[str\] = set()' src/mcp_test_framework/cli.py` returns `0`.
   - `grep -c 'for tool_cfg in cfg.tools.values():' src/mcp_test_framework/cli.py` returns `0`.

4. **New helper wired both sides:**
   - `grep -c '_compose_judges_from_tool_configs' src/mcp_test_framework/_runner.py` >= 2 (def + RUBRIC_IDS reference in body).
   - `grep -c '_compose_judges_from_tool_configs' src/mcp_test_framework/cli.py` == 1 (single call site replacing the loop).
   - `grep -c 'from .rubrics import RUBRIC_IDS' src/mcp_test_framework/_runner.py` == 1.

5. **Optional operator-recipe smoke (manual, mirrors the UAT repro):**
   - With a `config.yaml` containing only the two-tool fixture (`tools: {list_keyring_credentials: {}, suggest_deployments: {}}`):
     - `MCPTF_CONFIG_FILE=config.yaml uv run python -c "from mcp_test_framework.config import _load_config; from mcp_test_framework._runner import _compose_judges_from_tool_configs; cfg = _load_config('config.yaml'); print(_compose_judges_from_tool_configs(cfg.tools))"` prints `['clarity', 'disambiguation', 'parameters']` (NOT `[]`).
   - The corresponding `mcp-test-framework run --config config.yaml` digest line reads `Judges:      clarity, disambiguation, parameters` (not `(none configured)`).
</verification>

<success_criteria>
The gap recorded in `16-VERIFICATION.md` `gaps_remaining[0]` is closed when ALL of the following hold:

1. **Source fix lands at the right layer.** `_runner.py` exports a pure `_compose_judges_from_tool_configs(tools_config) -> list[str]` helper that expands `ToolConfig.judges=None` (TOOLCFG-06 default) to `RUBRIC_IDS`, treats `[]` as opt-out (no-op), and passes literal subsets through. `cli.py` calls this helper instead of the old `getattr(..., 'judges', []) or []` loop.

2. **Three tests pin the semantic.** The three new tests in `tests/framework/unit/test_runner_pre_run_digest.py` exercise None / [] / subset cases via both the helper and the renderer, and all pass. The pre-existing 11 tests in that file continue to pass (no regression).

3. **The lying digest stops lying.** A config with only default-`judges` tools (the UAT repro) no longer emits `Judges:      (none configured)` — it emits the canonical `Judges:      clarity, disambiguation, parameters` (alphabetically sorted, comma-separated, matching `RUBRIC_IDS`). The empty-output case `(none configured)` is now reachable ONLY via explicit `judges: []` on every tool.

4. **Three-way semantic preserved.** The fix does NOT collapse the three runtime states the contract gates at `test_mcp_tool_contract.py:124,154,185` already enforce. Tests prove all three states (None, [], subset) produce distinct, correct digest output.

5. **No collateral damage.** `git diff --stat` after the plan shows exactly three files touched: `src/mcp_test_framework/cli.py`, `src/mcp_test_framework/_runner.py`, `tests/framework/unit/test_runner_pre_run_digest.py`. No README change (README's existing sample already documents the corrected post-fix output). No CONTEXT.md churn (the TOOLCFG-06 semantic is already locked in models.py; the gap was purely an upstream wiring bug, not a missing decision).

6. **UX-01 / SC-1 contract restored.** The phase's load-bearing success criterion ("unambiguous pre-run digest of what will execute") holds again — the digest now matches runtime for the homelab-mcp default-judges config that triggered the gap.
</success_criteria>

<output>
After completion, create `.planning/phases/16-reporter-ux-overhaul/16-05-SUMMARY.md` following the standard SUMMARY template. The summary should record:
- The three files changed + LOC delta
- Confirmation of the three eradication grep gates returning 0
- Confirmation of the three new tests passing
- A 2-3 line note on why the fix sits in `_runner.py` (next to `_compose_pre_run_skip_reasons`) rather than `cli.py` (pure composer next to its sibling; testable without spinning the Typer wrapper; mirrors the Phase 16 D-14 "no new module file" stance)
- Pointer back to `16-VERIFICATION.md` gap G-1 as the closure target so the next verification run can mark it resolved
</output>
