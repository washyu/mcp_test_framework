---
phase: 13-config-safety-opt-in-tool-selection
plan: 03
type: execute
wave: 2
depends_on: [13-01]
files_modified:
  - tests/conftest.py
  - src/mcp_test_framework/_reporter.py
  - tests/unit/test_reporter.py
autonomous: true
requirements: [SAFE-01]
must_haves:
  truths:
    - "D-12: An operator who lists exactly two tools in `tools:` with skip:false sees those two parametrized; every other discovered tool drops out of pytest collection (not runtime-SKIPPED)."
    - "D-12: An operator who lists a tool with skip:true sees the tool absent from parametrize; the reporter renders a SKIP row whose reason is the operator's `skip_reason` if non-empty, else `\"explicit skip in config\"`."
    - "D-12: An operator whose discovered tools include names absent from `tools:` sees those tools rendered with reason `\"not selected in config\"` in the per-tool summary."
    - "D-13: An empty `tools: {}` (or absent) means zero tools are selected; every discovered tool renders as state (a) with reason `\"not selected in config\"`."
    - "D-12: The two reporter reason strings (`not selected in config` and `explicit skip in config`) are module-level constants in _reporter.py so they cannot drift silently."
  artifacts:
    - path: "tests/conftest.py"
      provides: "Allowlist filter at _resolve_tool_names — `name in config.tools and not config.tools[name].skip`"
      contains: "name in config.tools and not"
    - path: "src/mcp_test_framework/_reporter.py"
      provides: "Two distinct skip-reason constants + state-a/state-c composition at terminal-summary time"
      contains: "not selected in config"
    - path: "tests/unit/test_reporter.py"
      provides: "Regression tests pinning the two reason strings and the state-a/state-c composition"
  key_links:
    - from: "tests/conftest.py:_resolve_tool_names"
      to: "src/mcp_test_framework/_reporter.py:_PER_TOOL"
      via: "the un-parametrized tool names are reported as state (a) via the new composition path"
      pattern: "name in config.tools and not"
    - from: "src/mcp_test_framework/_reporter.py reason constants"
      to: "SAFE-01 reporter wording"
      via: "module-level _REASON_NOT_SELECTED / _REASON_EXPLICIT_DEFAULT constants"
      pattern: "_REASON_NOT_SELECTED|_REASON_EXPLICIT_DEFAULT"
---

<objective>
Invert `tools:` from a skip-list (every-tool-runs-by-default) to an opt-in allowlist (every-tool-skips-by-default) by changing the parametrize-time filter at `tests/conftest.py:135-138` to `name in config.tools and not config.tools[name].skip`, and update the per-tool reporter at `src/mcp_test_framework/_reporter.py` to render the two distinct SAFE-01 reason strings — `"not selected in config"` for state (a) (unlisted) and `tool_cfg.skip_reason or "explicit skip in config"` for state (c) (listed with skip:true). The reporter learns to compose state-a/state-c rows from `Config.tools` + the discovered-tools cache rather than waiting for `pytest.skip()` calls that never fire (per the v1.1.1 hotfix lesson — filter at parametrize, do not runtime-skip).

This plan does NOT touch `TargetConfig` removal — Plan 13-04 owns that. To keep this plan parallel-safe with Plan 13-02 (which only touches `config.py`), we MUST keep `tests/conftest.py:101-103`'s `if explicit: return [explicit]` short-circuit alive for now. The short-circuit still references `config.target.tool_name`, which still exists. Plan 13-04 will delete it.

Purpose: SAFE-01 (opt-in three-state allowlist; the 56-entry skip-list pattern collapses to a 2-entry allowlist).

Output: A `tests/conftest.py` whose filter is `name in config.tools and not config.tools[name].skip`; an `_reporter.py` whose `pytest_terminal_summary` composes state-a/state-c SKIP rows from `Config` + discovered names; two module-level constants pinned by a regression test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-01-SUMMARY.md
@tests/conftest.py
@src/mcp_test_framework/_reporter.py
@src/mcp_test_framework/fixtures.py

<interfaces>
Key interfaces in scope:

From `tests/conftest.py` (current state; the load-bearing v1.1.1 filter is at the END of `_resolve_tool_names`). NOTE: this revision moves `_DISCOVERED_TOOL_NAMES` OUT of `tests/conftest.py` and INTO `src/mcp_test_framework/_reporter.py` (revision iteration 1):
```python
# Pre-revision state shown for context; this plan deletes the local
# declaration and reads/writes via `_reporter._DISCOVERED_TOOL_NAMES`.
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None

def _resolve_tool_names(config: Config) -> list[str]:
    global _DISCOVERED_TOOL_NAMES
    explicit = config.target.tool_name
    if explicit:
        return [explicit]                      # <-- KEEP for Wave 2 (Plan 13-04 removes)
    if _DISCOVERED_TOOL_NAMES is None:
        # ... handshake / spawn / pytest.exit on failure ...
        _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
    # CURRENT (v1.1.1 skip-list):
    return [
        name for name in _DISCOVERED_TOOL_NAMES
        if not config.tools.get(name, ToolConfig()).skip
    ]
```

**Phase 13 post-revision target shape for `tests/conftest.py`:**
```python
from mcp_test_framework import _reporter as _rep

def _resolve_tool_names(config: Config) -> list[str]:
    explicit = config.target.tool_name
    if explicit:
        return [explicit]                      # Plan 13-04 removes this short-circuit
    if _rep._DISCOVERED_TOOL_NAMES is None:
        _rep._DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
    # Phase 13 D-13 / SAFE-01 allowlist (set in Task 1 below):
    return [
        name for name in _rep._DISCOVERED_TOOL_NAMES
        if name in config.tools and not config.tools[name].skip
    ]
```

From `src/mcp_test_framework/_reporter.py`:
- `_PER_TOOL: dict[str, dict] = {}` — per-tool aggregation populated by `pytest_runtest_logreport`.
- `pytest_terminal_summary(terminalreporter, exitstatus, config) -> None` — already iterates `_PER_TOOL`. Phase 13 adds a pre-step: synthesize SKIP entries for tools that did not parametrize (state-a) and for listed-skipped tools (state-c).

From `src/mcp_test_framework/_reporter.py` (module-level state that tests/conftest.py writes and _reporter.py reads — POST-revision iteration 1):
- `_DISCOVERED_TOOL_NAMES: list[str] | None` — declared in `_reporter.py`, written by `tests/conftest.py:_resolve_tool_names`, read by `_reporter._compose_unparametrized_skips`. Single-direction dependency.

Two reason-string constants (NEW — module-level in `_reporter.py`):
```python
_REASON_NOT_SELECTED = "not selected in config"   # SAFE-01 state (a) verbatim
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"  # SAFE-01 state (c) fallback
```
</interfaces>
</context>

<truths>
**Locked decisions implemented by this plan (quoted from 13-CONTEXT.md):**

- **D-12:** "Two distinct reason strings. State (a) unlisted → reporter reason: `\"not selected in config\"` (exact SAFE-01 wording). State (c) listed with `skip: true` → reporter reason: the operator's curated `skip_reason` if non-empty, else default `\"explicit skip in config\"` (covers the legal-but-unhelpful empty-string case)."
- **D-13:** "Empty `tools:` (`{}` or unset) auto-skips every tool. Consistent with the unlisted rule: zero tools listed → zero tools selected → every discovered tool renders as state (a). The run succeeds with 0 contract tests executed and a clear reporter line saying nothing was opted in."
- **(NOT D-14 in this plan):** Plan 13-04 owns the `target.tool_name` override deletion. This plan leaves the `explicit` short-circuit at `tests/conftest.py:101-103` in place to remain parallel-safe with Plan 13-02.

**13-PATTERNS.md correction (load-bearing):** The CONTEXT.md "Files affected" line for the three-state allowlist runtime lists `fixtures.py:262, 282-286, 482-494` — VERIFIED OFF BY FILE. The actual three-state filter lives in `tests/conftest.py:88-138` (`_resolve_tool_names`). `fixtures.py:259-266` is the unknown-tool warning loop (survives); `fixtures.py:482-494` is `tool_config` (survives with a docstring update only). This plan touches `tests/conftest.py` and `_reporter.py`, NOT `fixtures.py`. (Plan 13-04 touches `fixtures.py` for the override deletion.)

**Revision iteration 1 fix — import direction inversion:** The pre-revision plan had `_DISCOVERED_TOOL_NAMES` living in `tests/conftest.py` and `_reporter.py` doing a lazy `from tests import conftest` to read it. That coupling reverses the natural dependency (production reading from test tree) and pre-empts Phase 15's `tests/contract/` vs `tests/framework/` split. This revision moves `_DISCOVERED_TOOL_NAMES` (and its setter) into `mcp_test_framework._reporter` so the dependency runs one way only: production exports state, tests read it.
</truths>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Flip the parametrize filter from skip-list to allowlist</name>
  <files>tests/conftest.py, tests/unit/test_reporter.py</files>
  <read_first>
    - tests/conftest.py (read in full; you are surgically replacing the return statement at lines 135-138 and updating the docstring at lines 88-99)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §4 (the v1.1.1 hotfix context and the exact replacement snippet)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-12, D-13
    - Memory: `project_v1_1_skip_bug.md` (the lesson — filter at parametrize, do not runtime-skip) — already loaded via auto-memory
    - tests/unit/test_reporter.py (read in full to see the existing terminal-summary tests; you will add allowlist regression tests in Task 2)
  </read_first>
  <behavior>
    - When config has `tools: {tool_a: {}, tool_b: {}}` and the server discovers `[tool_a, tool_b, tool_c]`: parametrize input is `[tool_a, tool_b]`.
    - When config has `tools: {tool_a: {skip: true, skip_reason: "x"}}` and discovery is `[tool_a, tool_b]`: parametrize input is `[]` (a is skipped, b is unlisted).
    - When config has `tools: {}` and discovery is `[tool_a, tool_b]`: parametrize input is `[]`.
    - When config has `tools: {tool_a: {}}` but discovery is `[tool_b]`: parametrize input is `[]` (unknown-tool warning at `fixtures.py:259-266` still fires for `tool_a` — leave that loop alone).
    - The `explicit = config.target.tool_name; if explicit: return [explicit]` short-circuit at lines 101-103 is unchanged (Plan 13-04 removes).
  </behavior>
  <action>
    In `tests/conftest.py`, locate the `_resolve_tool_names` function (currently lines 88-138). Make two changes:

    1. **Replace the return statement at lines 135-138 (the v1.1.1 skip-list filter):**

       OLD (delete exactly):
       ```python
       # v1.1.1 hotfix (260508-p0b): filter parametrize input by
       # config.tools[name].skip so skip:true tools are absent from collection
       # rather than runtime-SKIPPED 10x each. Tools with no `tools.<name>` entry
       # use ToolConfig() defaults (skip=False) and pass through unchanged. The
       # explicit-target short-circuit above still bypasses this filter (D-12 /
       # fixtures.py:_preflight warning path preserved).
       return [
           name for name in _DISCOVERED_TOOL_NAMES
           if not config.tools.get(name, ToolConfig()).skip
       ]
       ```

       NEW (paste exactly — note `_rep._DISCOVERED_TOOL_NAMES` to read from the production module post-revision-1):
       ```python
       # Phase 13 D-13 / SAFE-01: opt-in allowlist semantics. Three states:
       #   (a) unlisted          -> excluded here; reporter renders
       #                            "not selected in config" at terminal summary.
       #   (b) listed + skip=False -> included in parametrize (this branch).
       #   (c) listed + skip=True  -> excluded here; reporter renders
       #                            tool_cfg.skip_reason or "explicit skip in config".
       # Both (a) and (c) drop out of pytest collection -- the v1.1.1 hotfix
       # invariant (no 560 runtime-SKIPPED rows). The reporter composes the
       # SKIP rows from Config.tools + _reporter._DISCOVERED_TOOL_NAMES at
       # terminal-summary time. Revision iteration 1: state lives in
       # production (_reporter), not the test tree.
       return [
           name for name in _rep._DISCOVERED_TOOL_NAMES
           if name in config.tools and not config.tools[name].skip
       ]
       ```

       Critical: the imported `ToolConfig` symbol at the top of `tests/conftest.py` may become unused after this change. If ruff reports `F401`, remove the `from mcp_test_framework.models import ToolConfig` import (line 25). If it is still used elsewhere in the file, keep it.

       Also REQUIRED (revision iteration 1): add `from mcp_test_framework import _reporter as _rep` to the imports at the top of `tests/conftest.py`, and DELETE the local declaration `_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None` from `tests/conftest.py` (that state lives in `_reporter.py` now). Update the body of `_resolve_tool_names` to read `_rep._DISCOVERED_TOOL_NAMES` and write `_rep._DISCOVERED_TOOL_NAMES = ...` instead of using a local `global` declaration. The `global _DISCOVERED_TOOL_NAMES` statement is also deleted.

    2. **Update the function docstring at lines 88-99** to remove the v1.1.1 hotfix prose and describe the new opt-in semantics:

       ```python
       def _resolve_tool_names(config: Config) -> list[str]:
           """Resolve the parametrize tool-name list under SAFE-01 opt-in semantics.

           States:
             (a) discovered but unlisted in config.tools         -> excluded
             (b) listed with skip=False                          -> included
             (c) listed with skip=True                           -> excluded

           The reporter composes SKIP rows for states (a) and (c) at
           terminal-summary time using Config.tools + _DISCOVERED_TOOL_NAMES.
           This site never calls pytest.skip() -- filtering at parametrize
           time avoids the v1.1.1 runtime-SKIP explosion (260508-p0b).

           Single-tool focus continues to live in the explicit-target
           short-circuit above (config.target.tool_name); Plan 13-04 of
           Phase 13 removes that field and the short-circuit together.
           """
       ```

    Add focused regression tests in `tests/unit/test_reporter.py` (or a new `tests/unit/test_conftest_resolve.py` if the existing test_reporter.py is purely about the plugin — choose based on what's cleaner; example uses `test_reporter.py` for parallel co-location):

    ```python
    def test_safe_01_allowlist_includes_listed_unskipped(tmp_path) -> None:
        """Phase 13 SAFE-01 state (b): listed + skip=False -> included."""
        from mcp_test_framework.models import ToolConfig
        from tests.conftest import _resolve_tool_names

        class _FakeConfig:
            class _Tgt:
                tool_name = None
            target = _Tgt()
            tools = {"tool_a": ToolConfig(), "tool_b": ToolConfig()}
            mcp_server = None  # not reached because _DISCOVERED_TOOL_NAMES is primed

        from mcp_test_framework import _reporter as _rep
        _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b", "tool_c"]
        try:
            assert _resolve_tool_names(_FakeConfig()) == ["tool_a", "tool_b"]
        finally:
            _rep._DISCOVERED_TOOL_NAMES = None

    def test_safe_01_allowlist_excludes_unlisted_and_skipped() -> None:
        """Phase 13 SAFE-01 states (a) and (c): unlisted + skipped both excluded."""
        from mcp_test_framework.models import ToolConfig
        from tests.conftest import _resolve_tool_names

        class _FakeConfig:
            class _Tgt:
                tool_name = None
            target = _Tgt()
            tools = {
                "tool_a": ToolConfig(skip=True, skip_reason="dangerous"),
                # tool_b is unlisted -> state (a) -> excluded
            }

        from mcp_test_framework import _reporter as _rep
        _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b"]
        try:
            assert _resolve_tool_names(_FakeConfig()) == []
        finally:
            _rep._DISCOVERED_TOOL_NAMES = None

    def test_safe_01_empty_tools_means_zero_selection() -> None:
        """Phase 13 D-13: tools: {} -> every discovered tool drops out."""
        from tests.conftest import _resolve_tool_names

        class _FakeConfig:
            class _Tgt:
                tool_name = None
            target = _Tgt()
            tools = {}

        from mcp_test_framework import _reporter as _rep
        _rep._DISCOVERED_TOOL_NAMES = ["x", "y", "z"]
        try:
            assert _resolve_tool_names(_FakeConfig()) == []
        finally:
            _rep._DISCOVERED_TOOL_NAMES = None
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_reporter.py -v -k "safe_01 or allowlist or empty_tools" --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "name in config.tools and not" tests/conftest.py` returns one match (the new filter).
    - `grep -n "_DISCOVERED_TOOL_NAMES" tests/conftest.py` returns matches ONLY in the form `_rep._DISCOVERED_TOOL_NAMES` (reading/writing via the _reporter module); a bare local `_DISCOVERED_TOOL_NAMES = None` declaration MUST NOT remain.
    - `grep -n "from mcp_test_framework import _reporter" tests/conftest.py` returns one match.
    - `grep -n "_DISCOVERED_TOOL_NAMES" src/mcp_test_framework/_reporter.py` returns at least one match (the module-level declaration).
    - `grep -n "config.tools.get(name, ToolConfig()).skip" tests/conftest.py` returns ZERO matches (the v1.1.1 line is gone).
    - `grep -n "SAFE-01" tests/conftest.py` returns at least one match (the new docstring/comment block).
    - `uv run pytest tests/unit/test_reporter.py::test_safe_01_allowlist_includes_listed_unskipped tests/unit/test_reporter.py::test_safe_01_allowlist_excludes_unlisted_and_skipped tests/unit/test_reporter.py::test_safe_01_empty_tools_means_zero_selection -x` exits 0.
    - The existing `tests/conftest.py:_resolve_tool_names` lines 101-103 explicit-target short-circuit is UNCHANGED (Plan 13-04 owns its removal); `grep -n "if explicit:" tests/conftest.py` returns one match.
    - `grep -nE "ruff.*F401" /dev/null; uv run ruff check tests/conftest.py 2>&amp;1` returns no F401 errors for ToolConfig (either it's still used or the import was removed).
  </acceptance_criteria>
  <done>
    The single-line filter change inverts opt-out → opt-in. Three regression tests lock the three states (b included, a/c excluded, empty selection). The v1.1.1 invariant (no runtime-SKIP explosion) is preserved.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Compose state-a/state-c SKIP rows in _reporter.py from Config + discovered names</name>
  <files>src/mcp_test_framework/_reporter.py, tests/unit/test_reporter.py</files>
  <read_first>
    - src/mcp_test_framework/_reporter.py (read in full; you are adding two module-level constants and one new pre-step inside `pytest_terminal_summary`)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §6 (Option A — Reporter-side composition; Option B explicitly rejected — do NOT re-introduce synthetic pytest.skip calls)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md §decisions D-12, D-13
    - tests/conftest.py (you'll read `_DISCOVERED_TOOL_NAMES` from this module at terminal-summary time)
    - tests/unit/test_reporter.py (existing reporter tests — extend with state-a/state-c composition assertions)
  </read_first>
  <behavior>
    - At terminal-summary time, for every tool in `_DISCOVERED_TOOL_NAMES` that did NOT parametrize (i.e., not in `_PER_TOOL`):
        - If the tool is in `Config.tools` and `Config.tools[tool].skip == True`: render a SKIP row with reason = `tool_cfg.skip_reason or _REASON_EXPLICIT_DEFAULT` (state c).
        - Else (tool unlisted): render a SKIP row with reason = `_REASON_NOT_SELECTED` (state a).
    - Tools that DID parametrize (present in `_PER_TOOL`) continue to render via the existing PASS/FAIL/SKIP path with whatever reasons `_extract_skip_reason` captured. Do not double-render.
    - `_REASON_NOT_SELECTED = "not selected in config"` and `_REASON_EXPLICIT_DEFAULT = "explicit skip in config"` are module-level constants.
    - The reason strings appear in the rendered terminal output VERBATIM (no truncation in the cap-of-3 logic, which only applies to multi-reason joined strings from `_format_skip_reasons`).
    - When `_DISCOVERED_TOOL_NAMES` is None (e.g., a pure-unit-test pytest invocation that never parametrized any tools), the new composition step is a no-op.
  </behavior>
  <action>
    Edit `src/mcp_test_framework/_reporter.py`:

    1. **Add module-level constants** near the existing `_SKIP_REASON_CAP` constant (line 57). After line 57, add:

       ```python
       # Phase 13 D-12 / SAFE-01: two distinct skip-reason strings for opt-in
       # tool selection. Module-level constants so they cannot drift silently;
       # tests/unit/test_reporter.py pins both verbatim.
       _REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
       _REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default

       # Phase 13 revision iteration 1: the discovered-tools cache lives
       # HERE (production code), not in tests/conftest.py. tests/conftest.py
       # writes to this attribute; _compose_unparametrized_skips reads it.
       # Single-direction dependency: production exports state, tests read.
       # Pre-empts Phase 15's tests/contract/ vs tests/framework/ split.
       _DISCOVERED_TOOL_NAMES: "list[str] | None" = None
       ```

    2. **Add a helper function** above `pytest_terminal_summary` (currently line 156):

       ```python
       def _compose_unparametrized_skips(config) -> dict[str, str]:
           """Phase 13 D-12/D-13: return {tool_name: reason} for every discovered
           tool that did NOT parametrize -- i.e., tools that dropped out of
           collection via tests/conftest.py:_resolve_tool_names' allowlist filter.

           State (c) wins over state (a) when a tool is listed-with-skip:true:
           we emit the operator's `skip_reason` if non-empty, else the default
           `_REASON_EXPLICIT_DEFAULT`. State (a) (unlisted): `_REASON_NOT_SELECTED`.

           Returns {} when discovery never ran (e.g., a pure-unit-test pytest
           session that never hit pytest_generate_tests for `target_tool`).
           """
           # Phase 13 revision iteration 1: read from this module's own
           # state, not from tests/conftest.py. This inverts the previous
           # reverse-import (`from tests import conftest`) so production
           # code never depends on the test tree. tests/conftest.py is the
           # WRITER of _DISCOVERED_TOOL_NAMES on this module; _reporter is
           # the READER. Pre-empts Phase 15's `tests/contract/` split.
           discovered = _DISCOVERED_TOOL_NAMES
           if not discovered:
               return {}

           tools_cfg = getattr(config, "tools", {}) or {}
           result: dict[str, str] = {}
           for name in discovered:
               if name in _PER_TOOL:
                   continue  # parametrized -- the standard path handles it.
               cfg_entry = tools_cfg.get(name)
               if cfg_entry is not None and getattr(cfg_entry, "skip", False):
                   # state (c)
                   reason = (cfg_entry.skip_reason or "").strip()
                   result[name] = reason or _REASON_EXPLICIT_DEFAULT
               else:
                   # state (a)
                   result[name] = _REASON_NOT_SELECTED
           return result
       ```

       Notes:
       - `_DISCOVERED_TOOL_NAMES` lives at module scope in `_reporter.py` (revision iteration 1). `tests/conftest.py` WRITES it during collection; `_compose_unparametrized_skips` READS it at terminal-summary time. The reporter never imports from `tests/` — single-direction dependency, production code stays decoupled from the test tree (pre-empts Phase 15 SURFACE-01 split).
       - Pass `config` as a Pydantic Config (or anything quacking `.tools`). pytest passes the Config object as the third arg to `pytest_terminal_summary` — actually it passes the pytest `Config`, NOT our framework `Config`. So at the call site we need to load our framework `Config()` directly via the same import path the conftest uses. See call-site edit below.

    3. **Wire the composition into `pytest_terminal_summary`**. After the existing early returns (lines 165-168 — the verbose<0 check and the `if not _PER_TOOL: return` check) WAIT — that early return must change. Phase 13 may have ZERO parametrized tools (state (a)-only run, D-13 empty `tools: {}` case) and we still want to print the SKIP rows. Replace the early return logic:

       Replace EXACTLY (lines 165-168):
       ```python
           if terminalreporter.config.option.verbose < 0:
               return  # D-04b
           if not _PER_TOOL:
               return  # No tool-affined tests collected; nothing to summarize.
       ```

       With (note: load framework Config here):
       ```python
           if terminalreporter.config.option.verbose < 0:
               return  # D-04b

           # Phase 13 D-12/D-13: even with _PER_TOOL empty, we may have state-a/c
           # skips to render (the operator's `tools: {}` run, or every tool
           # listed with skip:true). Load the framework Config to compose them.
           try:
               from mcp_test_framework.config import Config as _FwConfig
               _fw_cfg = _FwConfig()
           except Exception:  # noqa: BLE001 -- under unit-only runs Config() may
               # fail (SAFE-03 fail-loud, no config in cwd). The terminal-summary
               # path is best-effort; absence of Config means we cannot compose
               # state-a/c rows.
               _fw_cfg = None
           unparam_skips: dict[str, str] = (
               _compose_unparametrized_skips(_fw_cfg) if _fw_cfg is not None else {}
           )
           if not _PER_TOOL and not unparam_skips:
               return  # Nothing to summarize.
       ```

       Then, inside the SKIP rendering block (currently lines 186-196), MERGE the new dict's entries. Find:

       ```python
           if skips:
               terminalreporter.write_line("skipped:")
               for tool in skips:
                   reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
                   ...
       ```

       Adapt to render BOTH the existing `_PER_TOOL` SKIP rows AND the new `unparam_skips`. Replace the SKIP block with:

       ```python
           all_skips = sorted(set(skips) | set(unparam_skips.keys()))
           if all_skips:
               # Phase 13: recompute name_width to account for state-a/c additions.
               name_width = max(name_width, *(len(n) for n in unparam_skips), default=0)
               terminalreporter.write_line("skipped:")
               for tool in all_skips:
                   if tool in _PER_TOOL and _PER_TOOL[tool]["verdict"] == "SKIP":
                       reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
                   else:
                       reasons_text = unparam_skips[tool]
                   if reasons_text:
                       terminalreporter.write_line(
                           f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"
                       )
                   else:
                       terminalreporter.write_line(f"  {tool.ljust(name_width)}  SKIP")
       ```

       Be careful: `name_width` is computed at line 171 over `_PER_TOOL` alone. The `max(...)` call above must guard against `unparam_skips` being empty (`default=0`) and against `_PER_TOOL` being empty (recompute name_width first or use the new guarded form). The simplest correct shape:

       ```python
           all_names = list(_PER_TOOL.keys()) + list(unparam_skips.keys())
           name_width = max((len(n) for n in all_names), default=0)
       ```

       Place this name_width computation BEFORE the `fails`/`skips`/`passes` partitioning lines (currently lines 173-175) so all subsequent renders use it.

    4. **Add a regression test** to `tests/unit/test_reporter.py` (or new `tests/unit/test_reporter_safe_01.py` — choose what is cleaner).

       ```python
       def test_safe_01_reporter_constants_locked() -> None:
           """Phase 13 D-12: the two reason strings cannot drift silently."""
           from mcp_test_framework._reporter import (
               _REASON_NOT_SELECTED,
               _REASON_EXPLICIT_DEFAULT,
           )
           assert _REASON_NOT_SELECTED == "not selected in config"
           assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"

       def test_safe_01_compose_state_a_for_unlisted_tool() -> None:
           """Phase 13 D-12 state (a): unlisted discovered tool -> not selected."""
           from mcp_test_framework._reporter import (
               _compose_unparametrized_skips,
               _PER_TOOL,
           )
           from mcp_test_framework import _reporter as _rep
           _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b"]
           _PER_TOOL.clear()  # parametrize ran nothing.
           class _Cfg:
               tools: dict = {}
           try:
               out = _compose_unparametrized_skips(_Cfg())
           finally:
               _rep._DISCOVERED_TOOL_NAMES = None
           assert out == {"tool_a": "not selected in config",
                          "tool_b": "not selected in config"}

       def test_safe_01_compose_state_c_with_curated_reason() -> None:
           """Phase 13 D-12 state (c) with non-empty skip_reason -> echoed."""
           from mcp_test_framework._reporter import _compose_unparametrized_skips, _PER_TOOL
           from mcp_test_framework.models import ToolConfig
           from mcp_test_framework import _reporter as _rep
           _rep._DISCOVERED_TOOL_NAMES = ["dangerous_tool"]
           _PER_TOOL.clear()
           class _Cfg:
               tools = {"dangerous_tool": ToolConfig(skip=True, skip_reason="hits prod")}
           try:
               out = _compose_unparametrized_skips(_Cfg())
           finally:
               _rep._DISCOVERED_TOOL_NAMES = None
           assert out == {"dangerous_tool": "hits prod"}

       def test_safe_01_compose_state_c_default_when_skip_reason_empty() -> None:
           """Phase 13 D-12 state (c) fallback: empty skip_reason -> default."""
           # ToolConfig's model_validator forbids skip=True + empty skip_reason
           # at construction time (TOOLCFG-07). The "legal-but-unhelpful empty"
           # case happens when YAML-loaded reason is a whitespace-only string
           # that ToolConfig accepted at load. Construct via
           # model_construct() to bypass the validator for this edge case test.
           from mcp_test_framework._reporter import (
               _compose_unparametrized_skips,
               _PER_TOOL,
               _REASON_EXPLICIT_DEFAULT,
           )
           from mcp_test_framework.models import ToolConfig
           from mcp_test_framework import _reporter as _rep
           _rep._DISCOVERED_TOOL_NAMES = ["x"]
           _PER_TOOL.clear()
           # Bypass validator to simulate a whitespace-stripped-to-empty edge.
           tcfg = ToolConfig.model_construct(skip=True, skip_reason="   ")
           class _Cfg:
               tools = {"x": tcfg}
           try:
               out = _compose_unparametrized_skips(_Cfg())
           finally:
               _rep._DISCOVERED_TOOL_NAMES = None
           assert out == {"x": _REASON_EXPLICIT_DEFAULT}
       ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_reporter.py -v -k "safe_01 or compose" --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "_REASON_NOT_SELECTED = \"not selected in config\"" src/mcp_test_framework/_reporter.py` returns one match.
    - `grep -n "_REASON_EXPLICIT_DEFAULT = \"explicit skip in config\"" src/mcp_test_framework/_reporter.py` returns one match.
    - `grep -n "_compose_unparametrized_skips" src/mcp_test_framework/_reporter.py` returns at least two matches (definition + call site in `pytest_terminal_summary`).
    - `grep -n "from tests import conftest" src/mcp_test_framework/_reporter.py` returns ZERO matches (revision iteration 1: the reverse-import is gone; state lives in `_reporter._DISCOVERED_TOOL_NAMES` and is read directly without re-importing the test tree).
    - `grep -n "from mcp_test_framework.config import Config" src/mcp_test_framework/_reporter.py` returns one match (inside `pytest_terminal_summary`).
    - `uv run pytest tests/unit/test_reporter.py::test_safe_01_reporter_constants_locked tests/unit/test_reporter.py::test_safe_01_compose_state_a_for_unlisted_tool tests/unit/test_reporter.py::test_safe_01_compose_state_c_with_curated_reason tests/unit/test_reporter.py::test_safe_01_compose_state_c_default_when_skip_reason_empty -x` exits 0.
    - All existing tests in `tests/unit/test_reporter.py` still pass: `uv run pytest tests/unit/test_reporter.py -v` exits 0.
    - The reporter does NOT synthesize `pytest.skip()` calls anywhere: `grep -n "pytest.skip\|pytest\\.skip" src/mcp_test_framework/_reporter.py` returns ZERO matches (Option B explicitly rejected per 13-PATTERNS.md §6).
  </acceptance_criteria>
  <done>
    Two module-level constants are pinned; `_compose_unparametrized_skips` derives state-a/c rows from Config + cached discovery; `pytest_terminal_summary` merges those rows with the existing `_PER_TOOL` SKIP rows; four regression tests lock the constants and the three states. No synthetic `pytest.skip()` calls anywhere — the v1.1.1 invariant holds.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator YAML → tool selection | The `tools:` allowlist governs which subprocess calls fire against the MCP server under test |
| Operator → discovery output | The reporter renders skip reasons (operator-supplied strings via `skip_reason`) — risk of injection-into-terminal |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13-03-01 | Tampering / privilege | The allowlist semantics ARE the mitigation against the v1 "destructive defaults" bug class | mitigate | Plan delivers the inversion. Regression tests `test_safe_01_*` and the v1.1.1 "no runtime SKIP explosion" invariant are the guards. Operator cannot accidentally call a destructive tool by forgetting to skip it; they must explicitly opt it in. |
| T-13-03-02 | Information disclosure | `skip_reason` strings render verbatim in terminal output | accept | Operator-supplied; ERROR-STYLE.md does NOT govern these (they are operator notes, not framework messages). The `_format_skip_reasons` already renders VERBATIM (D-05a). No new disclosure. |
| T-13-03-03 | Terminal injection via skip_reason | A malicious YAML editor injecting ANSI escape sequences into `skip_reason` | accept | Same operator-trust boundary as Plan 13-01: the operator authored the YAML themselves. pydantic-settings' `yaml.safe_load` does not interpret escape sequences; the string reaches the terminal as-is. The terminal trust boundary is the operator's own concern. No code-side mitigation; documented as accepted. |
| T-13-03-04 | Race / fixture-ordering | `tests/conftest.py` writes `_reporter._DISCOVERED_TOOL_NAMES` during collection; `_compose_unparametrized_skips` reads it at terminal-summary time | mitigate | The write happens during `pytest_generate_tests` (collection phase); the read happens at `pytest_terminal_summary` (post-execution). pytest guarantees collection completes before terminal summary, so no race. The composition function returns `{}` when the cache is `None` (pure-unit-test runs). |

No `high` severity threats; this plan is the central security mitigation for v1.2 (SAFE-01 = the SEED-006 destructive-default fix).
</threat_model>

<verification>
1. Allowlist behavior: operator with `tools: {tool_a: {}, tool_b: {skip: true, skip_reason: "x"}}` and discovery `[tool_a, tool_b, tool_c]` → parametrize returns `[tool_a]`; reporter SKIP rows show `tool_b: SKIP — x` and `tool_c: SKIP — not selected in config`.
2. Empty allowlist: `tools: {}` + discovery `[tool_a, tool_b]` → parametrize returns `[]`; reporter shows two SKIP rows with reason `not selected in config`.
3. The two locked constants exist exactly once each in `_reporter.py`.
4. The Plan 13-01 SAFE-03 fail-loud is unaffected (no shared files; verified via files_modified non-overlap).
5. No `pytest.skip()` calls in `_reporter.py` (Option B explicitly rejected).
6. All existing reporter tests still pass.
</verification>

<success_criteria>
- The five `must_haves.truths` are observable: allowlist inversion, state (c) reason precedence, state (a) reason, empty-tools zero selection, constants pinned.
- The v1.1.1 invariant holds: no parametrize entry exists for an unlisted/skipped tool; the reporter composes its skip rows from Config + cache, not from `pytest.skip()`.
- Files modified by this plan (`tests/conftest.py`, `src/mcp_test_framework/_reporter.py`, `tests/unit/test_reporter.py`) do NOT overlap with Plan 13-02's files (`src/mcp_test_framework/config.py`) — parallel-safe in Wave 2.
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-03-SUMMARY.md`. Include:
- The one-line filter delta at `tests/conftest.py`.
- The reporter's new composition path (helper + call site).
- Note that `tests/conftest.py:101-103` explicit-target short-circuit is intentionally preserved — Plan 13-04 owns its removal.
- Forward refs: Plan 13-04 deletes `TargetConfig` everywhere; once that lands, the explicit short-circuit in `_resolve_tool_names` is also gone.
</output>
