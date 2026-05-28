---
phase: 260508-p0b
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/conftest.py
  - tests/test_tool_config.py
autonomous: true
requirements:
  - "v1.1.1-SKIP-FILTER: tools.<name>.skip:true must remove the tool from parametrize, not just runtime-skip its 10 tests"
  - "v1.1.1-EXPLICIT-OVERRIDE: target.tool_name=X short-circuits before the new filter (preserves D-12 explicit-override-of-skip warning in fixtures.py:_preflight)"

must_haves:
  truths:
    - "Tools with tools.<name>.skip:true are absent from `pytest --collect-only` output"
    - "Test collection count drops from ~691 to ~127 with config.example.yaml's 56 skip entries"
    - "Tools with tools.<name>.skip:false (or no entry) still appear in collection unchanged"
    - "Explicit target.tool_name=X returns [X] even when X has skip:true (D-12 override path preserved)"
    - "All existing tests in tests/test_tool_config.py still pass (no regressions in ToolConfig schema surface)"
    - "Runtime guards `if tool_config.skip: pytest.skip(...)` in test_mcp_tool_contract.py remain in place untouched (defense-in-depth for the explicit-override branch)"
  artifacts:
    - path: "tests/conftest.py"
      provides: "_resolve_tool_names with skip filter applied AFTER the explicit-target short-circuit, BEFORE returning the discovered list"
      contains: "config.tools.get"
    - path: "tests/test_tool_config.py"
      provides: "Sync regression test(s) covering the new filter and the explicit-override branch; no live markers, no @pytest.mark.asyncio"
      contains: "_resolve_tool_names"
  key_links:
    - from: "tests/conftest.py:_resolve_tool_names"
      to: "src/mcp_test_framework/models.py:ToolConfig"
      via: "import + config.tools.get(name, ToolConfig()).skip"
      pattern: "from mcp_test_framework.models import .*ToolConfig"
    - from: "tests/conftest.py:pytest_generate_tests"
      to: "_resolve_tool_names"
      via: "names = _resolve_tool_names(config); metafunc.parametrize(...)"
      pattern: "_resolve_tool_names\\(config\\)"
    - from: "tests/test_tool_config.py (new test)"
      to: "tests.conftest._DISCOVERED_TOOL_NAMES + _resolve_tool_names"
      via: "direct module-attribute set + finally-reset to None"
      pattern: "_DISCOVERED_TOOL_NAMES"
---

<objective>
Fix the v1.1 `tools.<name>.skip:true` semantic mismatch shipped in Phase 08. The flag was implemented at runtime (10 SKIPPED-per-tool lines via `pytest.skip` in test bodies) instead of at parametrize time. Result: with `config.example.yaml`'s 56 skip entries, `pytest --collect-only` shows 691 tests (560 of them dead-on-arrival SKIPs) instead of the ~127 the user expects.

Purpose: Realign the implementation with the user-facing promise — `skip:true` means "don't test this tool", which means it should not appear in collection at all.

Output:
- One added filter line in `tests/conftest.py:_resolve_tool_names` (after the explicit-target short-circuit, before returning the discovered list)
- 2 sync regression tests in `tests/test_tool_config.py` proving the filter works and the explicit-override path is preserved
- Verification commands run against `config.example.yaml` confirming collection drops from ~691 to ~127

Out of scope (locked by task spec, do NOT touch in this plan):
- Removing the runtime `if tool_config.skip: pytest.skip(...)` guards in `tests/test_mcp_tool_contract.py` (kept as defense-in-depth)
- CHANGELOG / ROADMAP updates (no v1.1.1 tag yet)
- `config.example.yaml` content (genericization is SEED-009)
- Reporter changes in `_reporter.py` (its SKIPPED count drops to zero naturally)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/seeds/SEED-006-config-loading-safety.md

@tests/conftest.py
@src/mcp_test_framework/models.py
@src/mcp_test_framework/fixtures.py

<interfaces>
<!-- Key types extracted from the codebase. The executor should use these directly — no exploration needed. -->

From `src/mcp_test_framework/models.py`:
```python
class ToolConfig(BaseModel):
    """Per-tool config registry entry. extra='forbid', frozen."""
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")
    skip: bool = False
    skip_reason: Optional[str] = None
    call_arguments: dict[str, Any] = Field(default_factory=dict)
    judges: Optional[list[str]] = None
    setup: Optional[Any] = None       # reserved, runtime no-op
    depends_on: Optional[list[str]] = None  # reserved
    # validator: skip=True requires non-empty skip_reason (TOOLCFG-07)
```

From `src/mcp_test_framework/config.py`:
```python
class Config(BaseSettings):
    ollama: OllamaConfig
    mcp_server: McpServerConfig
    target: TargetConfig          # target.tool_name: Optional[str]
    judge_timeout_seconds: int = 120
    version: int = 1
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
```

From `tests/conftest.py` (CURRENT shape — what we modify):
```python
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None

def _resolve_tool_names(config: Config) -> list[str]:
    global _DISCOVERED_TOOL_NAMES
    explicit = config.target.tool_name
    if explicit:
        return [explicit]                 # short-circuit: no filter applied here
    if _DISCOVERED_TOOL_NAMES is None:
        try:
            _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
        except Exception as exc:
            ...  # FileNotFoundError hint preserved verbatim
            pytest.exit(msg, returncode=2)
    return _DISCOVERED_TOOL_NAMES         # <-- NEW filter goes immediately before this return
```

The two existing imports in conftest.py we need to know about:
```python
from mcp_test_framework.config import Config            # already imported
from mcp_test_framework.mcp_client import McpTestClient # already imported
# ToolConfig is NOT yet imported in conftest.py — must be added.
```

From `src/mcp_test_framework/fixtures.py:_preflight` (lines 200-213, UNCHANGED by this plan):
```python
# D-12: when target.tool_name is set AND that tool's config has skip=True,
# the explicit single-target intent wins. Surface as warning.
if config.target.tool_name is not None:
    explicit_cfg = config.tools.get(config.target.tool_name)
    if explicit_cfg is not None and explicit_cfg.skip:
        warnings.warn(
            f"target.tool_name={config.target.tool_name!r} explicitly set; "
            f"overriding tools.{config.target.tool_name!r}.skip=True for this run",
            UserWarning, stacklevel=2,
        )
```
This branch is REACHED ONLY because `_resolve_tool_names`'s explicit-target short-circuit returns `[explicit]` BEFORE the new filter — so the explicit tool reaches `_preflight` and the warning fires. Verify both tasks preserve this.
</interfaces>

Existing test pattern to mirror (from `tests/test_tool_config.py`):
- Sync tests at the top of the file (no `@pytest.mark.asyncio`, no `live_*` markers — they run under default `addopts = "-m 'not live_homelab and not live_ollama'"`)
- `test_yaml_overlay_loads_tools_block(tmp_path, monkeypatch)` shows the YAML-overlay-via-MCPTF_CONFIG_FILE pattern if YAML is preferred over direct kwargs construction
- Direct kwargs construction (`Config(tools={...})`) is also fine and simpler for this case
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add regression tests covering the parametrize-time skip filter</name>
  <files>tests/test_tool_config.py</files>
  <behavior>
    Add 2 sync tests to the schema-tests block of tests/test_tool_config.py (under the existing `# Schema tests` header, before the `# AsyncMock-based call_arguments threading proof` header). Both tests:
    - Are sync (no `@pytest.mark.asyncio`)
    - Carry no `live_homelab` / `live_ollama` markers (must run under default `addopts = "-m 'not live_homelab and not live_ollama'"`)
    - Set `tests.conftest._DISCOVERED_TOOL_NAMES` directly to a list and reset to `None` in a try/finally block (no monkeypatching the async `_discover_tools` — the cache short-circuits the async path)
    - Use `Config(tools={...})` direct kwargs (NOT YAML overlay) for brevity — the YAML path is already covered by `test_yaml_overlay_loads_tools_block`

    Test 1 — `test_resolve_tool_names_filters_out_skip_true_tools`:
      - Build `config = Config(tools={"a": ToolConfig(), "b": ToolConfig(skip=True, skip_reason="x"), "c": ToolConfig()})`
      - Set `tests.conftest._DISCOVERED_TOOL_NAMES = ["a", "b", "c"]`
      - Call `_resolve_tool_names(config)`
      - Assert returned list is `["a", "c"]` (b filtered)
      - finally: reset `_DISCOVERED_TOOL_NAMES = None`

    Test 2 — `test_resolve_tool_names_explicit_target_overrides_skip_true`:
      - Build `config = Config(tools={"b": ToolConfig(skip=True, skip_reason="x")}, target={"tool_name": "b"})`
      - Do NOT set `_DISCOVERED_TOOL_NAMES` (the explicit-target short-circuit returns BEFORE the cache is consulted, proving D-12)
      - Call `_resolve_tool_names(config)`
      - Assert returned list is `["b"]` (explicit override wins)

    Test 1 must fail BEFORE Task 2's filter is added (RED). Test 2 must pass both before AND after Task 2 (it covers the unchanged short-circuit branch — included as a regression guard against accidentally moving the filter above the short-circuit).
  </behavior>
  <action>
    Edit `tests/test_tool_config.py`. Add an import at the top (alongside the existing `from mcp_test_framework.config import Config` and `from mcp_test_framework.models import ToolConfig`):

    ```python
    import tests.conftest as _conftest_module  # for _DISCOVERED_TOOL_NAMES + _resolve_tool_names
    ```

    Then add the two tests in the schema-tests block (after `test_yaml_overlay_loads_tools_block`, before the `# AsyncMock-based call_arguments threading proof` separator):

    ```python
    def test_resolve_tool_names_filters_out_skip_true_tools() -> None:
        """v1.1.1-SKIP-FILTER: tools.<name>.skip:true removes the tool from
        the parametrize input list (not just runtime-skips its 10 tests).

        Sets the module cache directly so the async _discover_tools path is
        not exercised — keeps the test sync and offline.
        """
        config = Config(
            tools={
                "a": ToolConfig(),
                "b": ToolConfig(skip=True, skip_reason="testing the filter"),
                "c": ToolConfig(),
            }
        )
        _conftest_module._DISCOVERED_TOOL_NAMES = ["a", "b", "c"]
        try:
            names = _conftest_module._resolve_tool_names(config)
            assert names == ["a", "c"], (
                f"expected skip:true tool 'b' filtered out; got {names!r}"
            )
        finally:
            _conftest_module._DISCOVERED_TOOL_NAMES = None


    def test_resolve_tool_names_explicit_target_overrides_skip_true() -> None:
        """v1.1.1-EXPLICIT-OVERRIDE: target.tool_name=X short-circuits before
        the new filter, so an explicit single-target run still includes a
        skip:true tool. Preserves the D-12 _preflight warning path
        (fixtures.py:200-213).
        """
        config = Config(
            tools={"b": ToolConfig(skip=True, skip_reason="testing override")},
            target={"tool_name": "b"},
        )
        # Deliberately do NOT touch _DISCOVERED_TOOL_NAMES — the explicit-target
        # branch must return before the cache is consulted.
        names = _conftest_module._resolve_tool_names(config)
        assert names == ["b"], (
            f"explicit target.tool_name='b' should win over skip:true; got {names!r}"
        )
    ```

    Run the test file once BEFORE Task 2 to confirm Test 1 fails (RED — `["a", "b", "c"]` returned instead of `["a", "c"]`) and Test 2 passes (the short-circuit branch already exists). Do NOT proceed to Task 2 until you observe Test 1 RED with the expected diff.
  </action>
  <verify>
    <automated>uv run pytest tests/test_tool_config.py::test_resolve_tool_names_filters_out_skip_true_tools tests/test_tool_config.py::test_resolve_tool_names_explicit_target_overrides_skip_true -v</automated>
    Expected before Task 2:
      - test_resolve_tool_names_filters_out_skip_true_tools: FAILED (got ["a", "b", "c"], expected ["a", "c"])
      - test_resolve_tool_names_explicit_target_overrides_skip_true: PASSED
  </verify>
  <done>
    Two tests added to tests/test_tool_config.py in the schema-tests block. Test 1 RED, Test 2 GREEN. The diff against tests/test_tool_config.py shows only added lines (no edits to existing tests). No new files created.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Apply the skip filter in _resolve_tool_names and verify collection count drops</name>
  <files>tests/conftest.py</files>
  <behavior>
    After this task, `_resolve_tool_names` filters the discovered list by `config.tools[name].skip` before returning. Tools with no `tools.<name>` entry default to `ToolConfig()` (skip=False) and pass through unchanged.

    Specifically:
    - Both regression tests from Task 1 PASS
    - `uv run pytest tests/` exits 0 (no collateral breakage; the runtime guards in `test_mcp_tool_contract.py` continue to compile and import even though they no longer fire for the filtered path)
    - With `config.example.yaml` (56 skip entries), collection drops from ~691 to ~127 (within ±5 to absorb future tool-list churn)
    - Skip:true tools (e.g. `delete_proxmox_vm`) absent from collection
    - Skip:false / unconfigured tools (e.g. `list_keyring_credentials`, `suggest_deployments`) still present
  </behavior>
  <action>
    Edit `tests/conftest.py`:

    1. Add `ToolConfig` to the existing models import block (line ~24, alongside `from mcp_test_framework.mcp_client import McpTestClient`):

       Before:
       ```python
       from mcp_test_framework.config import Config  # noqa: E402
       from mcp_test_framework.mcp_client import McpTestClient  # noqa: E402
       ```

       After:
       ```python
       from mcp_test_framework.config import Config  # noqa: E402
       from mcp_test_framework.mcp_client import McpTestClient  # noqa: E402
       from mcp_test_framework.models import ToolConfig  # noqa: E402
       ```

    2. In `_resolve_tool_names`, replace the bare `return _DISCOVERED_TOOL_NAMES` at the end with a filter expression. The full target shape (post-edit) for the function body's tail:

       ```python
       def _resolve_tool_names(config: Config) -> list[str]:
           """... (existing docstring, extend with filter note) ..."""
           global _DISCOVERED_TOOL_NAMES
           explicit = config.target.tool_name
           if explicit:
               return [explicit]   # explicit-target short-circuit (D-12 preserved)
           if _DISCOVERED_TOOL_NAMES is None:
               try:
                   _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
               except Exception as exc:  # noqa: BLE001
                   # ... existing FileNotFoundError hint block UNCHANGED ...
                   pytest.exit(msg, returncode=2)
           # v1.1.1 hotfix (260508-p0b): filter parametrize input by
           # config.tools[name].skip so skip:true tools are absent from
           # collection rather than runtime-SKIPPED 10x each. Tools with no
           # `tools.<name>` entry use ToolConfig() defaults (skip=False) and
           # pass through unchanged. The explicit-target short-circuit above
           # still bypasses this filter (D-12 / fixtures.py:_preflight warning
           # path preserved).
           return [
               name for name in _DISCOVERED_TOOL_NAMES
               if not config.tools.get(name, ToolConfig()).skip
           ]
       ```

       Update the docstring's bullet list to mention the filter:
       - "discovered list, cached module-level for this pytest invocation, **filtered by config.tools[name].skip**"

    3. Do NOT touch the `# Quick-task 260507-j6i` FileNotFoundError hint block — it stays verbatim.
    4. Do NOT touch `pytest_generate_tests` — it consumes whatever `_resolve_tool_names` returns, no change needed.
    5. Do NOT remove or modify the runtime `if tool_config.skip: pytest.skip(...)` guards in `tests/test_mcp_tool_contract.py` — they remain as defense-in-depth.

    Run all four verification gates from the task spec in order. If any fails, do not proceed — report the failure for diagnosis.
  </action>
  <verify>
    <automated>uv run pytest tests/test_tool_config.py -v</automated>
    Gate 1: Both regression tests from Task 1 PASS; all existing test_tool_config.py tests still PASS (no regressions in ToolConfig schema surface).

    <automated>uv run pytest tests/ --co -q 2>&1 | tail -5</automated>
    Gate 2: Full suite collects without errors (no import-time breakage from the new ToolConfig import).

    <automated>uv run pytest tests/</automated>
    Gate 3: Full default suite passes (exits 0). Default addopts excludes live markers, so this runs sync schema/regression tests only.

    <automated>$env:MCPTF_CONFIG_FILE="config.example.yaml"; uv run pytest tests/ --collect-only -q 2>&1 | Select-String -Pattern "tests collected|test_" | Measure-Object -Line</automated>
    Gate 4 (manual numeric check, PowerShell): Lines reported by `--collect-only` should be ~127 (±5), down from ~691. If the number is still in the 600s, the filter did not apply. Unset env var after with `$env:MCPTF_CONFIG_FILE=""`.

    <automated>$env:MCPTF_CONFIG_FILE="config.example.yaml"; uv run pytest tests/test_mcp_tool_contract.py --collect-only -q 2>&1 | Select-String -Pattern "delete_proxmox_vm|list_keyring_credentials|suggest_deployments"</automated>
    Gate 5: Output contains `list_keyring_credentials` and/or `suggest_deployments` (skip:false tools — still in collection). Output does NOT contain `delete_proxmox_vm` (skip:true tool — filtered out).
  </verify>
  <done>
    All 5 verification gates pass. `tests/conftest.py:_resolve_tool_names` returns a filtered list (the new comprehension is the last statement). `ToolConfig` import added. The runtime `pytest.skip` guards in `tests/test_mcp_tool_contract.py` are untouched. The explicit-target short-circuit returns before the filter (verified by Gate 1 Test 2). Collection count under `config.example.yaml` is ~127, not ~691.
  </done>
</task>

</tasks>

<verification>
Phase-level gates (must all pass before declaring the quick task done):

1. **Regression tests pass:** `uv run pytest tests/test_tool_config.py -v` — both new tests GREEN, all existing tests still GREEN.
2. **No collateral breakage:** `uv run pytest tests/` — exit 0.
3. **Collection-count drops:** With `MCPTF_CONFIG_FILE=config.example.yaml`, `pytest tests/ --collect-only -q` reports ~127 tests (±5), down from ~691.
4. **Selective filtering verified:**
   - skip:true tools (e.g. `delete_proxmox_vm`) absent from `--collect-only` output
   - skip:false / unconfigured tools (e.g. `list_keyring_credentials`, `suggest_deployments`) present in `--collect-only` output
5. **Defense-in-depth preserved:** `tests/test_mcp_tool_contract.py` line-by-line diff against pre-fix shows ZERO changes (the runtime `if tool_config.skip: pytest.skip(...)` guards remain untouched).
6. **Explicit-override branch preserved:** Test 2 from Task 1 passing proves `target.tool_name="b"` returns `["b"]` even when `b.skip=True`, so `fixtures.py:_preflight`'s D-12 warning at lines 205-213 still fires for that path.

Manual UAT (after automation passes — user will perform):
- `uv run mcp-test-framework run --config .\config.example.yaml -- --collect-only -q` shows ~127 tests
- A live run against a configured homelab-mcp produces no `SKIPPED [tool_config.skip=True]` lines (those tests are no longer collected)
- Removing a tool from `config.example.yaml`'s `tools:` block (or flipping its `skip:` to `false`) brings it back into collection
</verification>

<success_criteria>
- `tests/conftest.py:_resolve_tool_names` filters by `config.tools[name].skip` after the explicit-target short-circuit and after discovery, returning the filtered list
- `tests/test_tool_config.py` has 2 new sync tests covering the filter and the explicit-override branch; both GREEN
- `uv run pytest tests/` exits 0; no existing tests regress
- Collection count under `config.example.yaml` drops from ~691 to ~127
- `tests/test_mcp_tool_contract.py` is byte-identical to its pre-fix state (defense-in-depth guards preserved)
- No CHANGELOG / ROADMAP / config.example.yaml edits
</success_criteria>

<output>
After completion, create `.planning/quick/260508-p0b-fix-v1-1-skip-doesnt-filter-parametrize-/260508-p0b-SUMMARY.md` documenting:
- The single-line filter added (and the import that supported it)
- The 2 regression tests added (names + what they cover)
- Verification gate results (the 5 gates above, with numeric collection counts before/after)
- Confirmation that fixtures.py:_preflight (lines 200-213) and test_mcp_tool_contract.py runtime guards are byte-identical to pre-fix
- A note pointing to SEED-006 / SEED-008 / SEED-009 as the v1.2 follow-up scope (NOT addressed by this hotfix)
</output>
