---
phase: 18-sdet-test-surface-typed-errors
plan: 06
type: execute
wave: 2
depends_on: [18-01, 18-05]
files_modified:
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/cli.py
autonomous: true
requirements: [SDET-02, UI-02]
must_haves:
  truths:
    - "JUnit XML parser reads mcptf_error_code / mcptf_error_message properties and uses them as failure_message when present (D-09)"
    - "Absence of those properties preserves the existing <failure message=...> extraction (Phase 16 regression guard)"
    - "FAIL row format is '[code] message' when code present, bare message otherwise (D-10)"
    - "_render_scenario_pre_run_digest exists with the same line-budget as _render_pre_run_digest (D-06)"
    - "Under --sdet, the digest dispatch routes to the scenario-aware builder; without --sdet the existing tool-aware builder still fires unchanged"
    - "--debug appendix emits '--- ToolCallError dump ---' block BEFORE '--- raw pytest output ---' when any failure carried mcptf_error_* properties (D-11)"
    - "--debug appendix raw: section emits the full CallToolResult.model_dump_json(indent=2) string carried by the mcptf_error_raw user_property; emits 'raw: (none)' only when that property is empty (D-11)"
    - "When NO ToolCallError-attached failures present, --debug appendix is byte-identical to Phase 14 baseline"
  artifacts:
    - path: "src/mcp_test_framework/_runner.py"
      provides: "XML parser extension (D-09); _render_scenario_pre_run_digest (D-06); --debug appendix block (D-11); FAIL row uses [code] message via D-09 (D-10)"
      contains: "mcptf_error_code, mcptf_error_message, mcptf_error_raw, _render_scenario_pre_run_digest, --- ToolCallError dump ---"
    - path: "src/mcp_test_framework/cli.py"
      provides: "Dispatch around digest call site: if sdet -> scenario digest, else tool digest"
      contains: "if sdet:"
  key_links:
    - from: "_runner.parse_junit_xml"
      to: "XML <property> children with name='mcptf_error_code' / 'mcptf_error_message'"
      via: "tc.find('properties') + iter('property') filter"
      pattern: 'name="mcptf_error_code"|name="mcptf_error_message"|name="mcptf_error_raw"'
    - from: "_runner._render_scenario_pre_run_digest"
      to: "scenario module stems (test_X.py -> X)"
      via: "sorted(scenarios) bucketing analogous to _render_pre_run_digest"
      pattern: "_render_scenario_pre_run_digest"
    - from: "_runner debug appendix builder"
      to: "ToolCallError dumps"
      via: "structured block before raw pytest output"
      pattern: "--- ToolCallError dump ---"
---

<objective>
Land the four `_runner.py` integrations that close the renderer side of Phase 18:

1. **D-09 JUnit-property hookup** — extend `parse_junit_xml` (lines ~422-519) to read `<property name="mcptf_error_code" value="..."/>` and `<property name="mcptf_error_message" value="..."/>` children of `<testcase>`. When present, build `failure_message = f"[{code}] {message}"` (or bare `message` when code empty) and use it INSTEAD of the raw `<failure message="...">` attr. When absent, fall through to existing extraction (Phase 16 regression guard).
2. **D-10 FAIL row format** — the row composer already uses `failure_message` verbatim from D-09; no shape change to `_render_per_tool_rows`. This plan just feeds it the new content through the parser hookup. The em-dash separator at `_runner.py:537` (U+2014) stays LOCKED.
3. **D-06 scenario-aware pre-run digest** — new function `_render_scenario_pre_run_digest` alongside `_render_pre_run_digest`. Buckets keyed on scenario MODULE stems (`tests/sdet/test_proxmox_vm_lifecycle.py` -> `proxmox_vm_lifecycle`). Same height budget as the existing digest (≤ 10 lines).
4. **D-11 --debug appendix ToolCallError block** — emits `--- ToolCallError dump ---` block(s) BEFORE `--- raw pytest output ---`. Carries `tool`, `code`, `message`, indented `raw: <CallToolResult.model_dump_json(indent=2)>` for each failure with `mcptf_error_*` properties.

Also: small dispatch in `cli.py` — around the existing digest call site (~line 532-539), route to the scenario builder under `--sdet`, else to the existing tool builder.

Purpose: Wave 2 because of `_runner.py` file overlap with Plan 18-05. Inherits the `sdet=sdet` kwarg thread Plan 18-05 added. All four integrations live in `_runner.py` so they ship in one plan; the cli.py dispatch is a 5-line if/else around the existing call site.

Output: Two modified files.
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
@.planning/phases/18-sdet-test-surface-typed-errors/18-01-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-05-SUMMARY.md
@src/mcp_test_framework/_runner.py
@src/mcp_test_framework/cli.py

<interfaces>
D-09 JUnit XML structure pytest emits when `report.user_properties.append(("mcptf_error_code", ...))` fires (Plan 18-07's hook):

```xml
<testcase classname="tests.sdet.test_basic" name="test_create_vm">
  <failure message="raw failure message" type="ToolCallError">...</failure>
  <properties>
    <property name="mcptf_error_code" value="VM_NAME_TAKEN"/>
    <property name="mcptf_error_message" value="name already in use"/>
    <property name="mcptf_error_raw" value="{indented JSON dump of CallToolResult — D-11}"/>
  </properties>
</testcase>
```

The third property `mcptf_error_raw` (added by Plan 18-07 Task 2) carries `exc.raw.model_dump_json(indent=2)` so the D-11 `--debug` appendix can render the structured CallToolResult dump per CONTEXT.md lines 123-134. Empty string when `exc.raw` is None.

Existing parser block (D-09 hook site, `_runner.py` ~lines 487-501):

```
failure = tc.find("failure")
error = tc.find("error")
skipped = tc.find("skipped")

if failure is not None or error is not None:
    bucket.verdict = "FAIL"
    elem = failure if failure is not None else error
    msg = elem.get("message")
    if msg and bucket.failure_message is None:
        bucket.failure_message = msg
    body = (elem.text or "").strip()
    if body and bucket.failure_body is None:
        bucket.failure_body = body
    continue
```

D-09 hook patch (insert BEFORE the `bucket.failure_message = msg` assignment):

```
# Phase 18 D-09: ToolCallError-attached JUnit properties (set by
# tests/sdet/conftest.py:pytest_exception_interact) win over the
# raw <failure message="..."> attr when present.
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
        # D-10: "[code] message" when code present; else bare message.
        prop_msg = f"[{code}] {msg_field}" if code else msg_field

msg = elem.get("message")
if prop_msg is not None and bucket.failure_message is None:
    bucket.failure_message = prop_msg
elif msg and bucket.failure_message is None:
    bucket.failure_message = msg
```

D-06 scenario digest target (analog `_render_pre_run_digest` ~lines 732-802):

```
def _render_scenario_pre_run_digest(
    ctx: RenderContext,
    scenarios: list[str],
    skipped_scenarios: dict[str, str],
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    if file is None:
        file = sys.stdout
    running = sorted(scenarios)
    running_n = len(running)
    skipping_n = len(skipped_scenarios)
    judges_text = "(none — SDET scope)"
    running_text = ", ".join(running) if running else "(none)"

    print("=" * 40, file=file)
    print("MCP Test Framework (SDET)", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {running_n + skipping_n} scenarios", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
        for stem in sorted(skipped_scenarios):
            print(f"  {stem}  — {skipped_scenarios[stem]}", file=file)
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)
```

D-11 --debug appendix block (emitted BEFORE `--- raw pytest output ---`):

```
--- ToolCallError dump ---
tool: <name>
code: <code or "(none)">
message: <message>
raw:
  <CallToolResult.model_dump_json(indent=2) — each line indented 2 spaces>
---
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend parse_junit_xml to read mcptf_error_* properties (D-09 + D-10)</name>
  <files>src/mcp_test_framework/_runner.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py lines 374-396 (ToolVerdict dataclass — check current fields; if a new field is needed for D-11, add it here)
    - src/mcp_test_framework/_runner.py lines 422-519 (parse_junit_xml — full body, especially the failure/error branch at ~487-501)
    - src/mcp_test_framework/_runner.py line 537 (em-dash separator U+2014 lock — DO NOT touch)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-09 lines 109-117; D-10 lines 121)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (parser hook target lines 444-465)
  </read_first>
  <behavior>
    - Test: XML with `<testcase>` containing both `<failure message="raw_msg"/>` AND `<properties><property name="mcptf_error_code" value="VM_NAME_TAKEN"/><property name="mcptf_error_message" value="name already in use"/></properties>` -> `bucket.failure_message == "[VM_NAME_TAKEN] name already in use"` (NOT `"raw_msg"`).
    - Test: XML with `<failure message="raw_msg"/>` and NO `<properties>` block -> `bucket.failure_message == "raw_msg"` (Phase 16 regression guard).
    - Test: XML with `mcptf_error_message` only (no code property) -> `bucket.failure_message == "name already in use"` (bare; no brackets).
    - Test: XML with `mcptf_error_code` set but `mcptf_error_message` empty/missing -> falls back to `<failure message="...">` extraction (code alone is insufficient).
    - Test: XML with empty-string `mcptf_error_code` (value="") -> treated as `None` (code missing); message used bare.
    - Test: contract-test XML (existing Phase 16 fixtures) is parsed byte-identically — no `<properties>` block, current behavior preserved.
  </behavior>
  <action>
**Edit A — `parse_junit_xml` in `src/mcp_test_framework/_runner.py` (~lines 422-519):**

Find the failure-extraction branch:

```
if failure is not None or error is not None:
    bucket.verdict = "FAIL"
    elem = failure if failure is not None else error
    msg = elem.get("message")
    if msg and bucket.failure_message is None:
        bucket.failure_message = msg
```

Replace the `msg = elem.get("message")` + assignment block with the D-09 hook (from `<interfaces>` above):

```
# Phase 18 D-09: ToolCallError-attached JUnit properties (set by
# tests/sdet/conftest.py:pytest_exception_interact) win over the
# raw <failure message="..."> attr when present.
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
        # D-10: "[code] message" when code present; else bare message.
        prop_msg = f"[{code}] {msg_field}" if code else msg_field

msg = elem.get("message")
if prop_msg is not None and bucket.failure_message is None:
    bucket.failure_message = prop_msg
elif msg and bucket.failure_message is None:
    bucket.failure_message = msg
```

PRESERVE the `body = (elem.text or "").strip(); if body and bucket.failure_body is None: bucket.failure_body = body; continue` tail BYTE-IDENTICAL — only the message-assignment is changed.

**Edit B — `ToolVerdict` dataclass: NO CHANGE.**

The D-11 `--debug` appendix builder (Task 3) re-parses the JUnit XML to scan for `mcptf_error_*` properties — including the new `mcptf_error_raw` property emitted by Plan 18-07 Task 2 which carries `exc.raw.model_dump_json(indent=2)` (the full structured CallToolResult dump). The dump string survives the JUnit XML attribute serialization cycle (XML attribute values are arbitrary-length strings; realistic CallToolResult dumps are a few KB).

Re-parsing the XML in the appendix builder (vs adding fields to ToolVerdict and threading them through `parse_junit_xml`):
- Zero dataclass churn.
- The property set already lives in the XML, written by pytest's JUnit writer.
- O(N) extra pass over testcases is negligible at MVP scale.

Do NOT add `tool_call_error_*` fields to `ToolVerdict`. Document in the docstring of the failure-branch that the appendix builder owns the second pass.

**Edit C — `_render_per_tool_rows` (D-10) — NO CODE CHANGE:**

The row composer at `_runner.py:845-895` already builds `✗ {tag} — {failure_message}` using whatever `failure_message` is set on the bucket. Because D-09 now puts `"[code] message"` into `failure_message`, the row automatically renders `"✗ FAIL — [VM_NAME_TAKEN] name already in use"`. DO NOT touch the row composer. The em-dash separator at line 537 stays LOCKED (U+2014).
  </action>
  <verify>
    <automated>uv run pytest tests/framework/unit/test_runner_parser.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "mcptf_error_code" src/mcp_test_framework/_runner.py` returns at least 1
    - `grep -c "mcptf_error_message" src/mcp_test_framework/_runner.py` returns at least 1
    - `grep -c 'tc.find("properties")' src/mcp_test_framework/_runner.py` returns at least 1
    - `grep -c 'f.\[\{code\}\] \{msg_field\}.' src/mcp_test_framework/_runner.py` returns at least 1 (D-10 format string)
    - `grep -c "Phase 18 D-09" src/mcp_test_framework/_runner.py` returns at least 1 (decision-trace comment)
    - existing `tests/framework/unit/test_runner_parser.py` still passes (regression guard)
    - `grep -c "tool_call_error_code\\|tool_call_error_raw_dump" src/mcp_test_framework/_runner.py` returns 0 (Strategy 1: no dataclass fields added)
    - `uv run pyright src/mcp_test_framework/_runner.py` returns 0 errors
  </acceptance_criteria>
  <done>
    Parser reads `mcptf_error_*` properties when present; uses them for `failure_message` per D-09/D-10; falls back to existing `<failure message="...">` extraction when absent; ToolVerdict dataclass unchanged.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add _render_scenario_pre_run_digest + dispatch from cli.py (D-06)</name>
  <files>src/mcp_test_framework/_runner.py, src/mcp_test_framework/cli.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py lines 604-731 (_compose_pre_run_skip_reasons + sibling helpers — note their signatures and how RenderContext flows)
    - src/mcp_test_framework/_runner.py lines 732-841 (_render_pre_run_digest — the existing tool-keyed builder; PRESERVE byte-identical for non-sdet path)
    - src/mcp_test_framework/_runner.py line 758-759 (digest height ≤ 10 lines lock — match in scenario builder)
    - src/mcp_test_framework/_runner.py near line 544 (RenderContext constructor — REQUIRED args vs defaults). Confirmed shape: `RenderContext(server_cmd: str, discovered_tools=[], tools_config={}, judges=[], total_planned_cases=0)`. Only `server_cmd` is required; all other fields default to empty.
    - src/mcp_test_framework/cli.py lines 530-545 (existing digest call site around `_runner._render_pre_run_digest(...)`)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-06 lines 74)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target builder lines 473-509; bucket-naming rule line 511)
  </read_first>
  <behavior>
    - Test: `_render_scenario_pre_run_digest(ctx, scenarios=["proxmox_vm_lifecycle", "basic_call"], skipped_scenarios={})` emits a header containing `"Running:     2"` AND `"basic_call, proxmox_vm_lifecycle"` (alphabetical order).
    - Test: with `skipped_scenarios={"flaky_thing": "skip-reason text"}` and `explain=True`, output contains a line matching pattern `flaky_thing  — skip-reason text` (em-dash U+2014, two-space hang).
    - Test: with `explain=False`, the per-scenario expansion line is NOT emitted; instead `"Skipping:     1  (use --explain to list)"` is shown.
    - Test: with `with_framework=True`, output contains `"+ framework self-tests"`.
    - Test: output height (line count) is ≤ 10 regardless of N — matches `_render_pre_run_digest` lock.
    - Test: `judges_text == "(none — SDET scope)"` is in the output (em-dash, signals SDET runs don't grade with Ollama).
    - Test: existing `_render_pre_run_digest` unchanged — call with the same args produces byte-identical output to before this plan.
    - Test: `cli.py` dispatches to scenario digest when `sdet=True`, to tool digest when `sdet=False`.
  </behavior>
  <action>

**Edit A — Add `_render_scenario_pre_run_digest` adjacent to `_render_pre_run_digest` in `_runner.py`:**

Define a NEW function (do NOT modify or reshape `_render_pre_run_digest`). Place it directly after `_render_pre_run_digest` ends. Body verbatim from `<interfaces>` D-06 target:

```python
def _render_scenario_pre_run_digest(
    ctx: RenderContext,
    scenarios: list[str],
    skipped_scenarios: dict[str, str],
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    """Phase 18 D-06: scenario-aware variant of _render_pre_run_digest.

    Buckets are scenario MODULE stems (tests/sdet/test_proxmox_vm_lifecycle.py
    -> 'proxmox_vm_lifecycle'). Same line-budget as _render_pre_run_digest
    (≤ 10 lines). Em-dash separator U+2014 reused per Phase 16 / Phase 09
    SC-3 lock.

    Args:
        ctx: shared RenderContext (server_cmd field consumed).
        scenarios: list of scenario module stems to run (alphabetized on emit).
        skipped_scenarios: dict[stem, reason] for scenarios pytest collected
            but skipped (pytest.mark.skip / parametrize skip / preflight skip).
        with_framework: if True, append the framework-self-tests breadcrumb.
        explain: if True, expand the Skipping line into one-per-stem rows
            with em-dash + reason; else show the (use --explain to list) hint.
        file: stream to write to; defaults to sys.stdout (matches sibling).
    """
    if file is None:
        file = sys.stdout
    running = sorted(scenarios)
    running_n = len(running)
    skipping_n = len(skipped_scenarios)
    judges_text = "(none — SDET scope)"   # em-dash U+2014
    running_text = ", ".join(running) if running else "(none)"

    print("=" * 40, file=file)
    print("MCP Test Framework (SDET)", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {running_n + skipping_n} scenarios", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
        for stem in sorted(skipped_scenarios):
            print(f"  {stem}  — {skipped_scenarios[stem]}", file=file)   # em-dash U+2014
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)
```

The em-dash literal `—` (U+2014, NOT ASCII hyphen `-`, NOT en-dash `–`) appears in:
1. `judges_text = "(none — SDET scope)"`
2. The `--explain` expansion line `f"  {stem}  — {skipped_scenarios[stem]}"`

Pin both in Plan 18-08's renderer tests with `assert "—" in output`.

**Edit B — Dispatch from `cli.py` around the existing digest call site (~lines 532-539):**

Find the existing `_runner._render_pre_run_digest(...)` call inside the `run` command's `if not quiet:` block. Wrap with `if sdet:` dispatch.

**RenderContext data-flow decision (PINNED):** The scenario digest builder only consumes `ctx.server_cmd` (the only required RenderContext field). Under `--sdet`, the contract-scope `pre_run_ctx` may be empty/wrong-shaped because `tests/conftest.py:pytest_generate_tests` parametrize does not run. **Construct a fresh sdet-only RenderContext inside the SDET dispatch branch carrying ONLY `server_cmd`** — reuse the same `server_cmd` value the contract-scope `pre_run_ctx` was built from (resolved Config). This avoids any cross-coupling to discovered_tools / tools_config / judges fields that have no meaning under SDET scope.

```python
if not quiet:
    if sdet:
        # Phase 18 D-06: scenario-aware digest under --sdet.
        # Scenario list + skip-reason map come from a new collector helper
        # analogous to _compose_pre_run_skip_reasons but reading
        # tests/sdet/ module stems instead of tool config.
        # Fresh sdet-only RenderContext — only server_cmd is consumed by the
        # scenario digest; contract-scope discovered_tools / tools_config /
        # judges fields have no meaning under SDET scope.
        sdet_ctx = _runner.RenderContext(server_cmd=pre_run_ctx.server_cmd)
        scenarios, skipped_scenarios = _runner._collect_sdet_scenarios(sdet_ctx)
        _runner._render_scenario_pre_run_digest(
            sdet_ctx,
            scenarios,
            skipped_scenarios,
            with_framework=with_framework,
            explain=explain,
        )
    else:
        _runner._render_pre_run_digest(
            pre_run_ctx,
            with_framework=with_framework,
            explain=explain,
        )
```

**Edit C — Add `_collect_sdet_scenarios` helper in `_runner.py`:**

A small helper that returns `(scenarios: list[str], skipped_scenarios: dict[str, str])`. For Phase 18 (no real scenarios shipping yet — the dogfood VM-lifecycle is Phase 19), this helper can:
- Walk `tests/sdet/` for `test_*.py` files.
- Compute stem = `path.stem.removeprefix("test_")`.
- Return `(stems, {})` (empty skipped — Phase 19 will add preflight-skip detection).

Concrete shape:

```python
def _collect_sdet_scenarios(ctx: "RenderContext") -> tuple[list[str], dict[str, str]]:
    """Phase 18 D-06 helper: enumerate scenario module stems under tests/sdet/.

    Phase 19 will extend this with preflight-skip detection (PREFLIGHT-01..02
    skipped scenarios feed the skipped_scenarios return dict). Phase 18 ships
    the discovery side only; skipped dict is always empty in this phase.

    Returns:
        (scenario_stems: list[str] sorted alphabetically, skipped: dict[str, str])
    """
    from pathlib import Path
    sdet_dir = Path("tests/sdet")
    if not sdet_dir.is_dir():
        return ([], {})
    stems: list[str] = []
    for p in sdet_dir.glob("test_*.py"):
        stems.append(p.stem.removeprefix("test_"))
    return (sorted(stems), {})
```

**Do NOT modify `_render_pre_run_digest` itself.** All non-sdet behavior is byte-identical.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework._runner import _render_scenario_pre_run_digest, _collect_sdet_scenarios; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def _render_scenario_pre_run_digest" src/mcp_test_framework/_runner.py` returns 1
    - `grep -c "def _collect_sdet_scenarios" src/mcp_test_framework/_runner.py` returns 1
    - `grep -c "MCP Test Framework (SDET)" src/mcp_test_framework/_runner.py` returns 1
    - `grep -c "none — SDET scope" src/mcp_test_framework/_runner.py` returns 1 (em-dash U+2014)
    - `grep -c "if sdet:" src/mcp_test_framework/cli.py` returns at least 1 (dispatch added)
    - `grep -c "_render_scenario_pre_run_digest" src/mcp_test_framework/cli.py` returns 1 (called from dispatch)
    - `grep -c "sdet_ctx = _runner.RenderContext(server_cmd=" src/mcp_test_framework/cli.py` returns 1 (Warning-3 lock: fresh sdet-only ctx, not contract-scope pre_run_ctx)
    - existing `tests/framework/unit/test_runner_pre_run_digest.py` passes (regression guard for non-sdet path)
    - `uv run pyright src/mcp_test_framework/_runner.py src/mcp_test_framework/cli.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `_render_scenario_pre_run_digest` shipped; `_collect_sdet_scenarios` helper enumerates `tests/sdet/test_*.py` stems; cli.py dispatches under `--sdet`; non-sdet path byte-identical to Phase 16.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add --debug ToolCallError dump block to appendix (D-11)</name>
  <files>src/mcp_test_framework/_runner.py</files>
  <read_first>
    - src/mcp_test_framework/_runner.py lines 998-1048 (current --debug appendix block — find the lead-in `--- raw pytest output ---` and other named sections like `--- captured stderr ---` / `--- failure tracebacks ---`)
    - src/mcp_test_framework/_runner.py near RenderContext (line 544) — constructor signature; relevant only insofar as the appendix builder receives no RenderContext, just the xml_path
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-11 lines 123-134 — the locked raw: <CallToolResult.model_dump_json(indent=2)> output format)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-07-tests-sdet-scaffolding-PLAN.md (Plan 18-07 Task 2 — the `pytest_exception_interact` hook emits THREE user_properties: `mcptf_error_code`, `mcptf_error_message`, AND `mcptf_error_raw` carrying `exc.raw.model_dump_json(indent=2)`. The parser in this task reads ALL THREE.)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target block lines 534-548; triple-dash named-section aesthetic lines 899-901)
  </read_first>
  <behavior>
    - Test: when the JUnit XML contains a failure with `<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>`, `<property name="mcptf_error_message" value="name already in use"/>`, AND `<property name="mcptf_error_raw" value="{...JSON dump...}"/>`, the `--debug` appendix output contains `"--- ToolCallError dump ---"` BEFORE `"--- raw pytest output ---"`.
    - Test: the dump block contains the lines `tool: <test_name>` (the testcase name or tool inferred from classname), `code: VM_NAME_TAKEN`, `message: name already in use`.
    - Test (D-11 raw rendering): the dump block contains a `raw:` line followed by the indented `mcptf_error_raw` JSON content. Each line of the JSON dump is prefixed with `  ` (two spaces) when emitted.
    - Test (D-11 raw rendering — JSON-shape check): when `mcptf_error_raw` carries a real CallToolResult dump containing `"isError": true`, the emitted appendix output contains the substring `"isError"` (and any other CallToolResult schema keys present in the dump).
    - Test: when `code` is empty/missing, the line is `code: (none)` (literal "(none)" sentinel).
    - Test: when `mcptf_error_raw` is empty (or absent — test didn't raise ToolCallError OR exc.raw was None), the dump block emits `raw: (none)` (literal "(none)" sentinel) INSTEAD of an empty indented block. NO `re-run with --raw` fallback message — D-11 mandates the dump or the explicit sentinel.
    - Test: when NO `mcptf_error_*` properties are present in the XML at all, the appendix is byte-identical to the Phase 14 baseline — no `--- ToolCallError dump ---` block appears at all (D-13 invariant: each rung adds info; none re-shapes the layer below).
    - Test: the block terminator line is `---` (three dashes alone on a line), matching the 18-PATTERNS.md line 547 aesthetic.
  </behavior>
  <action>
**Edit — Add D-11 ToolCallError dump block to the `--debug` appendix builder in `_runner.py` (around lines 998-1048):**

Find the current appendix builder that emits `--- raw pytest output ---` (around line 1024 per 18-PATTERNS.md lines 515-530). BEFORE that lead-in, insert a new block that:

1. Re-parses the JUnit XML (or uses the already-parsed `ParsedRun` if it's in scope) to find all `<testcase>` entries with `<properties>` containing `mcptf_error_*` keys.
2. For each such testcase, emits the D-11 block. Concrete shape (use either a new helper `_extract_tool_call_errors_from_xml(xml_path) -> list[_ToolCallErrorRecord]` OR iterate inline — planner's call; favor the helper for testability).

Helper definition (place near the other private helpers in `_runner.py`):

```python
@dataclasses.dataclass(frozen=True)
class _ToolCallErrorRecord:
    """D-11 appendix record. tool/code/message/raw all reconstructed from JUnit
    user_properties (set by tests/sdet/conftest.py:pytest_exception_interact —
    see Plan 18-07 Task 2).

    raw carries the CallToolResult.model_dump_json(indent=2) string that
    pytest_exception_interact emits as the `mcptf_error_raw` property. Empty
    string when the test did not raise ToolCallError, OR when exc.raw was None.
    """
    tool: str
    code: str | None
    message: str
    raw: str  # the mcptf_error_raw user_property value; "" when absent / None


def _extract_tool_call_errors_from_xml(xml_path: Path) -> list[_ToolCallErrorRecord]:
    """Phase 18 D-11: scan a JUnit XML file for ToolCallError-attached
    testcases (testcases with mcptf_error_message user_property — code/raw
    optional). Returns one record per such testcase. Returns [] when none
    present (D-13 invariant: --debug appendix unchanged when no ToolCallError
    failures occurred).

    Reads ALL THREE user_properties emitted by Plan 18-07's
    pytest_exception_interact:
      - mcptf_error_code    -> .code  (None if missing or value="")
      - mcptf_error_message -> .message (required — testcase skipped if absent)
      - mcptf_error_raw     -> .raw  (""  if missing or exc.raw was None;
                                       otherwise the CallToolResult JSON dump)
    """
    if not xml_path.is_file():
        return []
    try:
        tree = ElementTree.parse(xml_path)
    except ElementTree.ParseError:
        return []
    out: list[_ToolCallErrorRecord] = []
    root = tree.getroot()
    for tc in root.iter("testcase"):
        props = tc.find("properties")
        if props is None:
            continue
        code: str | None = None
        message: str | None = None
        raw_dump: str = ""
        for prop in props.iter("property"):
            n = prop.get("name", "")
            v = prop.get("value", "")
            if n == "mcptf_error_code":
                code = v or None
            elif n == "mcptf_error_message":
                message = v
            elif n == "mcptf_error_raw":
                # D-11: full CallToolResult.model_dump_json(indent=2) string.
                # Empty value means exc.raw was None — render as "(none)".
                raw_dump = v
        if message is None:
            continue
        tool_name = tc.get("name", "(unknown)")
        out.append(_ToolCallErrorRecord(
            tool=tool_name, code=code, message=message, raw=raw_dump,
        ))
    return out
```

Then in the existing appendix builder, BEFORE the `--- raw pytest output ---` lead-in, add:

```python
# Phase 18 D-11: ToolCallError dump block emits BEFORE raw pytest output so
# operators get a parseable summary they can grep first. The raw: section
# carries the full CallToolResult.model_dump_json(indent=2) string emitted
# by Plan 18-07's pytest_exception_interact as the mcptf_error_raw property.
tool_call_errors = _extract_tool_call_errors_from_xml(xml_path)
for err in tool_call_errors:
    print("--- ToolCallError dump ---", file=file)
    print(f"tool: {err.tool}", file=file)
    print(f"code: {err.code or '(none)'}", file=file)
    print(f"message: {err.message}", file=file)
    if err.raw:
        # D-11: render the indented JSON dump. Each line of the dump string
        # (which already comes back from model_dump_json(indent=2) with its
        # own 2-space internal indent) gets an ADDITIONAL 2-space prefix so
        # the appendix layout matches CONTEXT.md lines 129-130.
        print("raw:", file=file)
        for line in err.raw.splitlines():
            print(f"  {line}", file=file)
    else:
        # exc.raw was None OR mcptf_error_raw property absent — explicit
        # sentinel per CONTEXT.md "raw: <CallToolResult.model_dump_json>"
        # contract; no '(unavailable — re-run with --raw...)' fallback
        # because the dump is supposed to traverse the JUnit cycle.
        print("raw: (none)", file=file)
    print("---", file=file)
    print("", file=file)
```

**Invariants:**
- The lead-in `--- ToolCallError dump ---` and terminator `---` strings are LOCKED (match the aesthetic of `--- raw pytest output ---` / `--- captured stderr ---` / `--- failure tracebacks ---` at lines 1024/1033/1043).
- When `tool_call_errors` is empty (no SDET ToolCallError failures, no `mcptf_error_*` properties in XML), this code emits ZERO bytes — appendix is byte-identical to Phase 14 baseline (D-13 invariant).
- The block emits BEFORE `--- raw pytest output ---` — order matters per CONTEXT.md line 133.
- Multiple ToolCallError failures emit multiple consecutive blocks; each ends with `---` + blank line.

**Do NOT:**
- Reshape the existing `--- raw pytest output ---` / `--- captured stderr ---` / `--- failure tracebacks ---` sections.
- Add the dump block when no ToolCallError properties are present (D-13 invariant).
- Substitute pytest's `<failure>.text` body for the `raw:` content. The dump string MUST come from the `mcptf_error_raw` user_property (set by Plan 18-07 Task 2 from `exc.raw.model_dump_json(indent=2)`). The `<failure>.text` is pytest's traceback rendering of `ToolCallError.__str__` (which is `[code] message` per D-07) — it does NOT contain the structured CallToolResult.
- Print "(unavailable — re-run with --raw to see full traceback)" or any other workaround — when `err.raw` is empty, print the explicit `raw: (none)` sentinel per CONTEXT.md.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework._runner import _extract_tool_call_errors_from_xml, _ToolCallErrorRecord; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_ToolCallErrorRecord" src/mcp_test_framework/_runner.py` returns at least 2 (dataclass + helper return type)
    - `grep -c "def _extract_tool_call_errors_from_xml" src/mcp_test_framework/_runner.py` returns 1
    - `grep -c "mcptf_error_raw" src/mcp_test_framework/_runner.py` returns at least 1 (D-11: third property read in helper)
    - `grep -cE -- "--- ToolCallError dump ---" src/mcp_test_framework/_runner.py` returns 1 (block lead-in)
    - `grep -c "raw: (none)" src/mcp_test_framework/_runner.py` returns at least 1 (explicit sentinel when err.raw empty)
    - `grep -v "^[[:space:]]*#" src/mcp_test_framework/_runner.py | grep -cE "re-run.*--raw|unavailable"` returns 0 (no fallback workaround language outside comments — D-11 mandates dump OR explicit sentinel only)
    - `grep -c "(none)" src/mcp_test_framework/_runner.py` returns at least 2 (code-missing + raw-missing sentinels)
    - existing Phase 14 / Phase 16 `--debug` baseline tests still pass (D-13 invariant — appendix unchanged when no ToolCallError)
    - `uv run pyright src/mcp_test_framework/_runner.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `_extract_tool_call_errors_from_xml` helper added; reads all three user_properties (`mcptf_error_code`, `mcptf_error_message`, `mcptf_error_raw`); `--debug` appendix emits `--- ToolCallError dump ---` blocks BEFORE `--- raw pytest output ---` when properties present; `raw:` section renders the full indented CallToolResult JSON dump (or `raw: (none)` sentinel when empty); empty when no properties present (D-13 invariant preserved).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| JUnit XML on disk -> renderer | XML file written by pytest; property values originate from `report.user_properties` which originate from `ToolCallError` fields populated by `_extract_code_message` (D-08 strict heuristic). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-13 | T (Tampering) | XML parsing in `_extract_tool_call_errors_from_xml` | mitigate | `ElementTree.parse` catches `ParseError` and returns empty list; no exception propagates to the renderer. Property values are read with `.get("value", "")` (string default) — no eval/exec; no XML external entity exposure via `defusedxml` not needed since pytest writes the XML locally. |
| T-18-14 | D (DoS) | Re-parsing XML in appendix builder | accept | Same XML already parsed by `parse_junit_xml`; second pass is O(N) over testcases. Could be optimized by caching but not for this phase. |
| T-18-15 | I (Info Disclosure) | --debug ToolCallError dump | accept | --debug is opt-in; dumps message/code/raw deliberately for operator debugging. Same trust posture as existing `--- captured stderr ---` section. |
</threat_model>

<verification>
- `uv run pytest tests/framework/unit/test_runner_parser.py -x` passes.
- `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -x` passes (regression guard for non-sdet path).
- `uv run pytest tests/framework/unit/test_sdet_renderer.py -x` passes once Plan 18-08 ships (full D-06/D-09/D-10/D-11 pinning).
- Module is pyright-strict-clean.
</verification>

<success_criteria>
- D-09 hookup: XML `mcptf_error_*` properties override `<failure message="...">` extraction; absence preserves Phase 16 behavior byte-identically.
- D-10 FAIL row: `failure_message` field auto-formats to `[code] message` via D-09; row composer untouched (em-dash U+2014 lock preserved).
- D-06 scenario digest: `_render_scenario_pre_run_digest` ships; dispatched by `cli.py` under `--sdet`.
- D-11 appendix: `--- ToolCallError dump ---` block emitted BEFORE `--- raw pytest output ---` when applicable; empty otherwise (D-13 invariant).
- Default-path (non-sdet) behavior is byte-identical to Phase 16.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-06-SUMMARY.md` documenting: the four sub-changes (D-09 parser hook, D-10 row format via parser, D-06 scenario digest, D-11 appendix block), the dispatch site in cli.py, and Strategy-1 (no ToolVerdict extension; re-parse XML for D-11).
</output>
