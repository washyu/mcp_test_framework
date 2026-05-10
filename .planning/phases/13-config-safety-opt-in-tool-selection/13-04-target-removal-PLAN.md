---
phase: 13-config-safety-opt-in-tool-selection
plan: 04
type: execute
wave: 3
depends_on: [13-02, 13-03]
files_modified:
  - src/mcp_test_framework/models.py
  - src/mcp_test_framework/config.py
  - src/mcp_test_framework/fixtures.py
  - tests/conftest.py
  - tests/unit/test_config.py
  - tests/unit/test_reporter.py
autonomous: true
requirements: [SAFE-01]
must_haves:
  truths:
    - "The class TargetConfig no longer exists in src/mcp_test_framework/models.py."
    - "The Config model has no `target` field; constructing Config(target={...}) raises (extra=forbid)."
    - "The fixtures.py preflight does not reference config.target.tool_name; the override-warning block at lines 268-289 of the v1.1 file is gone."
    - "tests/conftest.py:_resolve_tool_names has no `if explicit: return [explicit]` short-circuit; it directly returns the allowlist filter from Plan 13-03."
    - "A v2 YAML containing a top-level `target:` block is rejected at load time with an extra-forbid error (no silent ignore)."
  artifacts:
    - path: "src/mcp_test_framework/models.py"
      provides: "Slimmer model module with TargetConfig fully removed"
      contains: "class OllamaConfig"
    - path: "src/mcp_test_framework/config.py"
      provides: "Config without a `target` field"
      contains: "tools: dict[str, ToolConfig]"
    - path: "src/mcp_test_framework/fixtures.py"
      provides: "Preflight without target.tool_name branches"
    - path: "tests/conftest.py"
      provides: "_resolve_tool_names returns the allowlist filter directly"
  key_links:
    - from: "src/mcp_test_framework/config.py"
      to: "src/mcp_test_framework/models.py"
      via: "no TargetConfig import"
      pattern: "from mcp_test_framework.models import"
    - from: "tests/conftest.py:_resolve_tool_names"
      to: "single code path"
      via: "allowlist filter is the only return"
      pattern: "name in config.tools and not"
---

<objective>
Execute Phase 12 D-03 forward-reference and Phase 13 D-11/D-14: remove `TargetConfig`, the `target` field on `Config`, the `target.tool_name` consumers in `fixtures.py` and `tests/conftest.py`, and the override-warning block (now-unreachable code per D-14). After this plan ships, single-tool focus continues to live exclusively in the `focus-<tool>.yaml + --config focus-<tool>.yaml` pattern (Phase 12 D-03) — there is no in-process `target.tool_name` mechanism anywhere.

Purpose: Completes the SAFE-01 surface by collapsing the v1.1 dual selection mechanism (allowlist + target.tool_name override) to a single mechanism (allowlist only). Closes D-11 and D-14. Also makes the `extra="forbid"` on Config catch v1 configs that still carry a top-level `target:` block, providing a defense-in-depth signal alongside SAFE-06's version refusal.

Output: Four source files lose ~50 lines of dead/dual-mechanism code; one test file (test_reporter.py) updates the `_FakeConfig` shapes added by Plan 13-03 to drop the `_Tgt` inner class; one new test asserts Config rejects a v2 YAML with a `target:` block via extra=forbid.
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
@.planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md
@.planning/phases/13-config-safety-opt-in-tool-selection/13-03-SUMMARY.md
@.planning/phases/12-doc-persona-foundation/12-CONTEXT.md
@src/mcp_test_framework/models.py
@src/mcp_test_framework/config.py
@src/mcp_test_framework/fixtures.py
@tests/conftest.py
</context>

<truths>
**Locked decisions implemented by this plan (quoted from 13-CONTEXT.md):**

- **D-11:** "`target.tool_name` removed from the Pydantic model in this phase (executing Phase 12 D-03). When a v1 config still contains `target:` it errors during the v1→v2 refusal anyway (because `version: 1` is rejected first); the MIGRATION doc tells operators to delete the `target:` block when regenerating. No separate deprecation path needed — the version refusal subsumes it."
- **D-14:** "Delete the `target.tool_name` skip-override at `fixtures.py:282-286`. Since D-11 removes `target.tool_name` from the model entirely, the 'overriding tools[target.tool_name].skip=True for this run' override is unreachable code and goes with the field. The new allowlist replaces it: if the operator wants a tool to run, they list it without `skip: true`. Focus-one-tool workflows continue via `focus-toolname.yaml + --config` (Phase 12 D-03)."

**13-PATTERNS.md line-range correction (load-bearing):** the override block named "fixtures.py:282-286" in CONTEXT.md is actually `fixtures.py:268-289` in the current source (the block spans the `if config.target.tool_name is not None:` membership check at 268-275 AND the override-warning block at 277-289). Both subblocks reference `config.target.tool_name`; both are deleted in this plan.

**Note about Plan 13-03's `_FakeConfig` shape:** Plan 13-03's tests instantiate a `_FakeConfig` with an inner `_Tgt: tool_name = None` class to satisfy the `config.target.tool_name` reference at `tests/conftest.py:101`. Once that line is gone, the `_Tgt` inner class is also unnecessary — this plan simplifies those test scaffolds.
</truths>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Delete TargetConfig from models.py and the `target` field from Config</name>
  <files>src/mcp_test_framework/models.py, src/mcp_test_framework/config.py, tests/unit/test_config.py</files>
  <read_first>
    - src/mcp_test_framework/models.py (lines 76-98 — the `TargetConfig` class you are deleting)
    - src/mcp_test_framework/config.py (lines 45-50 for the import, line 166 for the field, plus the docstring/comments mentioning `target`)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §5 (the deletion shape)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-02-SUMMARY.md (the v2 source pipeline; you are removing the `target:` field on top of it)
    - tests/unit/test_config.py (locate any tests referencing `config.target` or `TargetConfig` — they need updating or deletion)
  </read_first>
  <behavior>
    - `from mcp_test_framework.models import TargetConfig` raises `ImportError`.
    - `Config().target` raises `AttributeError` (the field is gone).
    - `Config(yaml_file=<v2 yaml with target: {tool_name: x}>)` raises `ValidationError` due to `extra="forbid"` on Config (v2 has no `target:` key).
    - `Config(yaml_file=<v2 yaml without target: block>)` loads successfully.
    - All sub-models (`OllamaConfig`, `McpServerConfig`, `ToolConfig`) are unchanged.
  </behavior>
  <action>
    Make three edits:

    1. **`src/mcp_test_framework/models.py`:** Delete the `TargetConfig` class entirely. Currently lines 76-98:

       ```python
       class TargetConfig(BaseModel):
           """Target tool to run all tests against. None = discover all tools (Phase 07 D-01)."""

           model_config = ConfigDict(frozen=True, populate_by_name=True)

           tool_name: Optional[str] = Field(
               default=None,
               validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
           )

           @field_validator("tool_name", mode="before")
           @classmethod
           def _empty_to_none(cls, v):
               """Empty string from env -> None (Phase 07 D-02 'empty equivalent to None').
               ...
               """
               if isinstance(v, str) and v.strip() == "":
                   return None
               return v
       ```

       Delete the entire block (lines 76-98). After deletion, check whether the imports `Optional`, `AliasChoices`, `field_validator` are still used elsewhere in the file:
       - `Optional` — still used by `ToolConfig.skip_reason`, `ToolConfig.judges`, `ToolConfig.setup`, `ToolConfig.depends_on`. KEEP.
       - `AliasChoices` — still used by `OllamaConfig` and `McpServerConfig`. KEEP.
       - `field_validator` — still used by `ToolConfig._validate_judge_ids`. KEEP.

       No other deletions needed; the class boundary is clean.

    2. **`src/mcp_test_framework/config.py`:** 
       - Remove `TargetConfig` from the import block (currently lines 45-50). The end state:
         ```python
         from mcp_test_framework.models import (
             McpServerConfig,
             OllamaConfig,
             ToolConfig,
         )
         ```
       - Remove the field declaration at line 166: `target: TargetConfig = Field(default_factory=TargetConfig)`. End state of the field block:
         ```python
         ollama: OllamaConfig = Field(default_factory=OllamaConfig)
         mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)

         # JUDGE_TIMEOUT_SECONDS routes here without an explicit alias because
         # pydantic-settings uppercases top-level field names by default.
         judge_timeout_seconds: int = 120
         ```
         The blank line between `mcp_server` and the `judge_timeout_seconds` comment block stays.

    3. **`tests/unit/test_config.py`:** locate and update test references. Use grep:
       - Any test referencing `config.target.tool_name`, `Config(target=...)`, or `TargetConfig` — either delete the test or invert it.
       - Add one new test pinning the extra=forbid behavior:

       ```python
       def test_phase_13_d_11_target_block_in_yaml_rejected(tmp_path) -> None:
           """Phase 13 D-11: v2 has no `target:` field. A leftover v1 `target:`
           block triggers extra=forbid at load time (defense-in-depth
           alongside the SAFE-06 version refusal)."""
           yaml_path = tmp_path / "leftover.yaml"
           yaml_path.write_text(
               "version: 2\n"
               "target:\n  tool_name: list_registered_servers\n"
               "ollama:\n  base_url: http://x:11434\n  model: m\n"
               "mcp_server:\n  command: /bin/true\n"
               "tools: {}\n",
               encoding="utf-8",
           )
           import pytest
           from pydantic import ValidationError
           with pytest.raises(ValidationError) as exc_info:
               Config(yaml_file=str(yaml_path))
           # extra=forbid surfaces as type "extra_forbidden" with loc=("target",).
           assert any(
               e.get("loc", ()) == ("target",) and e.get("type") == "extra_forbidden"
               for e in exc_info.value.errors()
           )
       ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_config.py -v -k "target or d_11 or safe_06" 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "class TargetConfig" src/mcp_test_framework/models.py` returns ZERO matches.
    - `grep -n "TargetConfig" src/mcp_test_framework/models.py` returns ZERO matches.
    - `grep -n "TargetConfig" src/mcp_test_framework/config.py` returns ZERO matches.
    - `grep -n "target.*TargetConfig\|target: TargetConfig" src/mcp_test_framework/config.py` returns ZERO matches.
    - `uv run python -c "from mcp_test_framework.models import TargetConfig"` exits with `ImportError` (non-zero).
    - `uv run python -c "from mcp_test_framework.config import Config; c = Config(yaml_file='/nonexistent'); print(hasattr(c, 'target'))"` prints `False`.
    - `uv run pytest tests/unit/test_config.py::test_phase_13_d_11_target_block_in_yaml_rejected -x` exits 0.
    - All existing tests in `tests/unit/test_config.py` still pass (or are updated; no `target`-referencing tests remain): `uv run pytest tests/unit/test_config.py -v` exits 0.
    - `grep -rn "TargetConfig" src/` returns ZERO matches anywhere in source.
  </acceptance_criteria>
  <done>
    `TargetConfig` and the `target` field are deleted. A v2 YAML with a stray `target:` block fails at load with extra=forbid. All `models.py` / `config.py` tests still pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Delete target.tool_name consumers in fixtures.py and tests/conftest.py</name>
  <files>src/mcp_test_framework/fixtures.py, tests/conftest.py, tests/unit/test_reporter.py</files>
  <read_first>
    - src/mcp_test_framework/fixtures.py (lines 268-289 — the membership check + override-warning block being deleted in full)
    - tests/conftest.py (lines 100-103 — the `explicit = config.target.tool_name; if explicit: return [explicit]` short-circuit being deleted; also the docstring at lines 88-99 that already mentions Plan 13-04's pending removal per Plan 13-03's docstring rewrite)
    - .planning/phases/13-config-safety-opt-in-tool-selection/13-PATTERNS.md §4 ("the override block spans `if config.target.tool_name is not None:` through the `warnings.warn(...)` call")
    - tests/unit/test_reporter.py (Plan 13-03 added tests with `_FakeConfig` shapes containing inner `_Tgt: tool_name = None` — those become unnecessary)
  </read_first>
  <behavior>
    - `grep -n "config.target" src/mcp_test_framework/fixtures.py` returns ZERO matches.
    - `grep -n "config.target" tests/conftest.py` returns ZERO matches.
    - `grep -n "target.tool_name" src/` returns ZERO matches.
    - The `warnings.warn(...)` UserWarning about "overriding tools.<name>.skip=True for this run" never fires (the code path is gone).
    - `_resolve_tool_names(config)` is a 1-branch function: discover (cached) then return the allowlist filter.
  </behavior>
  <action>
    Three edits:

    1. **`src/mcp_test_framework/fixtures.py`:** Delete lines 268-289 in full (the two blocks below the unknown-tool warning loop). The exact deletion target — confirm by grepping `if config.target.tool_name is not None:` and `overriding tools.` first; both substrings should each return exactly one match before this task, and ZERO after.

       The block to delete starts at:
       ```python
           if config.target.tool_name is not None:
               tool_names = [t.name for t in tools]
               if config.target.tool_name not in tool_names:
                   pytest.exit(
                       f"target tool {config.target.tool_name!r} not in MCP server tool list "
                       f"(available: {tool_names!r})",
                       returncode=2,
                   )

           # Phase 08 D-12: when target.tool_name is set AND that tool's config has
           # skip=True, the explicit single-target intent wins (the run still exercises
           # the tool). Surface the override as a warning so the operator knows the
           # configured skip was deliberately ignored.
           if config.target.tool_name is not None:
               explicit_cfg = config.tools.get(config.target.tool_name)
               if explicit_cfg is not None and explicit_cfg.skip:
                   warnings.warn(
                       f"target.tool_name={config.target.tool_name!r} explicitly set; "
                       f"overriding tools.{config.target.tool_name!r}.skip=True for this run",
                       UserWarning,
                       stacklevel=2,
                   )
       ```

       After deletion, the comment block immediately above (the unknown-tool warning at lines 256-266) ends naturally, and the `# All preflight checks passed;` comment at line 291 should follow directly. Preserve one blank line between them.

       If `warnings` is now unused in `fixtures.py`, remove the `import warnings`. Grep `warnings\\.` in fixtures.py to confirm — the unknown-tool warning still uses it, so the import stays.

    2. **`tests/conftest.py`:** Delete lines 100-103 (the explicit-target short-circuit). The currently-existing block:

       ```python
           global _DISCOVERED_TOOL_NAMES
           explicit = config.target.tool_name
           if explicit:
               return [explicit]
           if _DISCOVERED_TOOL_NAMES is None:
       ```

       Becomes:

       ```python
           global _DISCOVERED_TOOL_NAMES
           if _DISCOVERED_TOOL_NAMES is None:
       ```

       Also update the function docstring (which Plan 13-03 already touched) to remove the trailing paragraph "Single-tool focus continues to live in the explicit-target short-circuit above (config.target.tool_name); Plan 13-04 of Phase 13 removes that field and the short-circuit together." Replace with: "Single-tool focus is handled via `--config focus-<tool>.yaml` (Phase 12 D-03) — there is no in-process target field anymore."

    3. **`tests/unit/test_reporter.py`:** The four Plan 13-03 tests added a `_FakeConfig` with `class _Tgt: tool_name = None; target = _Tgt()`. Simplify those scaffolds — remove the inner `_Tgt` class and the `target` attribute:

       Before (in each of the four `_FakeConfig` definitions added by Plan 13-03):
       ```python
       class _FakeConfig:
           class _Tgt:
               tool_name = None
           target = _Tgt()
           tools = {...}
       ```

       After:
       ```python
       class _FakeConfig:
           tools = {...}
       ```

       The `_resolve_tool_names(config)` function no longer reads `config.target`, so the simplified fakes still pass.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_reporter.py tests/unit/test_config.py -v 2>&amp;1 | tail -25 &amp;&amp; uv run ruff check src/mcp_test_framework/fixtures.py tests/conftest.py 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "config.target\|target.tool_name" src/mcp_test_framework/fixtures.py` returns ZERO matches.
    - `grep -n "config.target\|target.tool_name" tests/conftest.py` returns ZERO matches.
    - `grep -rn "config.target\|target\\.tool_name" src/` returns ZERO matches.
    - `grep -n "overriding tools" src/mcp_test_framework/fixtures.py` returns ZERO matches.
    - `grep -n "explicit = config.target" tests/conftest.py` returns ZERO matches.
    - `grep -n "if explicit:" tests/conftest.py` returns ZERO matches.
    - `grep -n "_Tgt" tests/unit/test_reporter.py` returns ZERO matches (the Plan 13-03 stubs are simplified).
    - `uv run ruff check src/mcp_test_framework/fixtures.py tests/conftest.py` exits 0 (no unused imports left behind).
    - `uv run pytest tests/unit/test_reporter.py -v` exits 0 (allowlist + composition tests still pass with simplified fakes).
    - The unknown-tool warning at `fixtures.py:259-266` is UNCHANGED — `grep -n "configured but not in discovered tool list" src/mcp_test_framework/fixtures.py` still returns one match.
  </acceptance_criteria>
  <done>
    Two source files lose ~30 lines of dead target-tool code. The single-mechanism (allowlist only) lands. Plan 13-03's tests get simpler. The unknown-tool warning (the only useful artifact of the v1.1 preflight target checks) survives.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator YAML → tool execution | Already covered by Plan 13-03; this plan removes a redundant override path |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13-04-01 | Tampering / privilege escalation via override | The v1.1 `target.tool_name` block (`fixtures.py:282-289`) explicitly overrode operator skip=True. An operator setting skip=True for safety could be silently overridden by anyone setting `target.tool_name`. | mitigate | Plan deletes the override entirely. The allowlist becomes the SOLE selection mechanism; an operator's `skip: true` cannot be overridden by a second config field. This is the strongest possible mitigation: removing the dangerous code path. |
| T-13-04-02 | Defense-in-depth / silent v1 acceptance | A v1 config with a `target:` block could theoretically still partially load if SAFE-06 failed | mitigate | Plan 13-02's version validator catches v1 at the validator stage. This plan adds belt-and-suspenders: even IF a config slips past version=1 rejection, the `target:` block triggers `extra="forbid"` (regression `test_phase_13_d_11_target_block_in_yaml_rejected`). Two independent guards. |
| T-13-04-03 | Repudiation | Removing the UserWarning means operators no longer get told "I overrode your skip" | accept | The override no longer exists; nothing to surface. The operator's `skip: true` is now respected unconditionally. |
| T-13-04-04 | Code-deletion regressions | Deleting an import (`warnings`?) or a function the rest of the file uses | mitigate | Acceptance criteria includes `uv run ruff check` exit 0 and `grep` for surviving `warnings.warn` usage in fixtures.py. The unknown-tool warning at lines 259-266 still uses `warnings`, so the import stays. |

No `high` severity threats. Net security improvement: the override path was a foot-gun, and it's gone.
</threat_model>

<verification>
1. `grep -rn "TargetConfig\|target.tool_name\|config.target" src/ tests/` returns only the historical references in test scaffolds that were updated, and ZERO references in production code.
2. The Plan 13-03 allowlist tests (`test_safe_01_*`) still pass with simplified `_FakeConfig` scaffolds.
3. The Plan 13-02 SAFE-06 + SAFE-05 tests still pass.
4. The new `test_phase_13_d_11_target_block_in_yaml_rejected` test passes — `extra="forbid"` catches a stray `target:` block.
5. Running `mcp-test-framework run` end-to-end (with a valid v2 config that opts in one tool) still works; the preflight short-circuit deletion did not break the unknown-tool warning or the AsyncExitStack/mcp_client lifecycle.
6. The unknown-tool warning (the surviving piece of v1.1 preflight) still fires for `tools.<unknown>:` entries.
</verification>

<success_criteria>
- `TargetConfig` does not exist anywhere in `src/`.
- `config.target` and `target.tool_name` references do not exist anywhere in `src/` or `tests/conftest.py`.
- The override-warning block at `fixtures.py:268-289` is deleted.
- The `explicit = config.target.tool_name; if explicit: return [explicit]` short-circuit at `tests/conftest.py` is deleted.
- A v2 YAML with a leftover `target:` block raises `ValidationError(extra_forbidden)`.
- The end-to-end allowlist behavior delivered by Plans 13-02 + 13-03 is preserved.
</success_criteria>

<output>
After completion, create `.planning/phases/13-config-safety-opt-in-tool-selection/13-04-SUMMARY.md`. Include:
- The 4-file deletion summary (models.py, config.py, fixtures.py, tests/conftest.py).
- The line counts removed (~50 LOC total).
- Grep gates confirming `TargetConfig` and `target.tool_name` are gone everywhere.
- Forward ref to Plan 13-05 MIGRATION doc: the doc's "drop the target: block" instruction lands now-truthful (the framework no longer accepts it under v2).
</output>
