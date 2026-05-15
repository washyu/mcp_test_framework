---
phase: 18-sdet-test-surface-typed-errors
plan: 07
type: execute
wave: 5
depends_on: [18-04, 18-06]
files_modified:
  - tests/sdet/__init__.py
  - tests/sdet/conftest.py
  - tests/sdet/test_basic_call.py
autonomous: true
requirements: [SDET-01, SDET-03, SDET-04, UI-02]
must_haves:
  truths:
    - "tests/sdet/ is a recognized pytest discovery scope (package marker present)"
    - "tests/sdet/conftest.py installs pytest_exception_interact hook that stashes ToolCallError.code/.message AND a JSON dump of CallToolResult onto report.user_properties (D-09 + D-11)"
    - "tests/sdet/test_basic_call.py exercises tool().call() end-to-end against the synthetic / homelab-mcp registry"
    - "All SDET tests are @pytest.mark.asyncio under strict mode (SDET-04)"
    - "Imports are from the canonical public surface (mcp_test_framework.sdet)"
  artifacts:
    - path: "tests/sdet/__init__.py"
      provides: "Package marker for pytest rootdir resolution"
    - path: "tests/sdet/conftest.py"
      provides: "pytest_exception_interact hook (D-09 JUnit property emission)"
      contains: "pytest_exception_interact, ToolCallError, mcptf_error_code, mcptf_error_message, mcptf_error_raw"
    - path: "tests/sdet/test_basic_call.py"
      provides: "End-to-end sanity scenario exercising the SDET surface"
  key_links:
    - from: "tests/sdet/conftest.py"
      to: "mcp_test_framework.sdet.ToolCallError"
      via: "isinstance check"
      pattern: "isinstance\\(exc, ToolCallError\\)"
    - from: "tests/sdet/test_basic_call.py"
      to: "mcp_test_framework.sdet (mcp_session, tool)"
      via: "import + fixture dependency"
      pattern: "from mcp_test_framework.sdet import"
---

<objective>
Ship the `tests/sdet/` scaffolding: a marker `__init__.py`, the SDET-only `conftest.py` with the `pytest_exception_interact` hook (D-09 — hoist `ToolCallError.code`/`.message` onto `report.user_properties` so pytest's JUnit XML writer surfaces them as `<property>` children of `<testcase>`), and a minimum-viable sanity test (`test_basic_call.py`) that exercises `tool().call()` end-to-end through the `mcp_session` fixture against the existing generated `homelab_mcp` registry.

Purpose: SDET-01 (tests/sdet/ exists as a discovery scope), SDET-04 (`@pytest.mark.asyncio` strict mode), and the D-09 JUnit-property emission that Plan 18-06's parser hook consumes. The sanity test is the verification harness — running `uv run mcp-test-framework run --sdet` after this plan exits 0 (or NN tests passed) demonstrates the whole Phase 18 surface works end-to-end.

Output: Three new files under `tests/sdet/`.
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
@.planning/phases/18-sdet-test-surface-typed-errors/18-04-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-06-SUMMARY.md
@src/mcp_test_framework/sdet/__init__.py
@src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py
@tests/conftest.py

<interfaces>
D-09 + D-11 hook target (extends 18-CONTEXT.md lines 110-117 with the third property mandated by D-11 lines 123-134 — the structured CallToolResult dump must traverse the JUnit XML cycle so the `--debug` appendix can emit `raw: <CallToolResult.model_dump_json(indent=2)>`):

```python
def pytest_exception_interact(node, call, report):
    exc = call.excinfo.value if call.excinfo else None
    if isinstance(exc, ToolCallError):
        report.user_properties.append(("mcptf_error_code", exc.code or ""))
        report.user_properties.append(("mcptf_error_message", exc.message))
        # D-11: serialize the live CallToolResult so --debug can render the
        # raw block. exc.raw is mcp.types.CallToolResult; model_dump_json
        # yields a string that survives JUnit XML attribute serialization.
        report.user_properties.append((
            "mcptf_error_raw",
            exc.raw.model_dump_json(indent=2) if exc.raw is not None else "",
        ))
```

pytest's JUnit XML writer surfaces `report.user_properties` as:

```xml
<testcase ...>
  <properties>
    <property name="mcptf_error_code" value="..."/>
    <property name="mcptf_error_message" value="..."/>
    <property name="mcptf_error_raw" value="{...JSON dump of CallToolResult...}"/>
  </properties>
</testcase>
```

The Plan 18-06 parser reads these to build the FAIL row's failure_message AND the `--debug` appendix `raw:` block.

Sanity test imports (from 18-PATTERNS.md lines 681-682):

```python
from mcp_test_framework.sdet import tool, mcp_session  # noqa: F401  re-export check
```

Generated registry shape (verified in src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py):
- The `_REGISTRY` dict is populated and contains 60+ tools including `list_registered_servers`, `get_proxmox_node_status`, etc.
- For a minimum-viable read-only sanity test, use `list_registered_servers` — already in the dict, takes no required params (verify via reading the generated `ListRegisteredServersParams` class — likely `(BaseModel)` with all optional fields).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/sdet/__init__.py (package marker)</name>
  <files>tests/sdet/__init__.py</files>
  <read_first>
    - tests/__init__.py (existing marker style)
    - tests/contract/__init__.py (sibling scope marker)
    - tests/framework/__init__.py (sibling scope marker)
  </read_first>
  <action>
Create an EMPTY `tests/sdet/__init__.py`. No docstring, no imports, no `pytest_plugins`. The empty file is sufficient — pytest uses it as a package marker for rootdir resolution and to enable `tests/sdet/conftest.py` isolation per CONTEXT line 251 ("the sdet-side conftest at tests/sdet/conftest.py is independent").

If the existing `tests/__init__.py` or sibling `__init__.py` files have a docstring, mirror their style; otherwise keep it empty.
  </action>
  <verify>
    <automated>uv run python -c "import pathlib; assert pathlib.Path('tests/sdet/__init__.py').exists(); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `tests/sdet/__init__.py`
    - File is ≤ 5 lines (empty or just a docstring)
    - `uv run pytest --collect-only tests/sdet/ 2>&1 | head -20` does NOT print rootdir-resolution errors
  </acceptance_criteria>
  <done>
    `tests/sdet/__init__.py` exists; pytest recognizes `tests/sdet/` as a package.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/sdet/conftest.py with pytest_exception_interact hook (D-09)</name>
  <files>tests/sdet/conftest.py</files>
  <read_first>
    - tests/conftest.py (existing top-level conftest — pattern of `pytest_plugins = ["mcp_test_framework.fixtures"]` and the parametrize hook; CRITICAL: SDET conftest must NOT add a parametrize hook because SDET tests are hand-authored, not parametrized over discovered tools — see CONTEXT line 251)
    - src/mcp_test_framework/sdet/__init__.py (Plan 18-04 output — verify `ToolCallError` is re-exported)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-09 lines 109-117)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target conftest body lines 610-643)
  </read_first>
  <behavior>
    - Test: `pytest_exception_interact` is a module-level function (not nested) in `tests/sdet/conftest.py`.
    - Test: when called with a fake `call` whose `.excinfo.value` is a `ToolCallError(tool="x", code="VM_X", message="boom", raw=real_CallToolResult)`, the function appends THREE tuples to `report.user_properties` in order: `("mcptf_error_code", "VM_X")`, `("mcptf_error_message", "boom")`, AND `("mcptf_error_raw", <CallToolResult.model_dump_json(indent=2) string>)`.
    - Test: when `exc.code is None`, the appended tuple is `("mcptf_error_code", "")` (empty string, NOT None — JUnit XML attribute values are strings).
    - Test: when `exc.raw is None`, the appended `mcptf_error_raw` tuple has value `""` (empty string, NOT None — and NOT the literal `"null"` — keeps the JUnit attribute well-formed and lets the renderer detect "no raw" via empty-string check).
    - Test (D-11 round-trip): when `exc.raw` is a real `mcp.types.CallToolResult(isError=True, content=[TextContent(type="text", text="boom")], structuredContent={"code":"X","message":"Y"})`, the emitted `mcptf_error_raw` value is parseable by `json.loads` AND the resulting dict contains keys `isError`, `content`, `structuredContent` (the CallToolResult schema surface).
    - Test: when `call.excinfo is None`, the function returns without raising (no-op path).
    - Test: when `call.excinfo.value` is NOT a `ToolCallError` (e.g. `AssertionError`), the function returns without modifying `report.user_properties` (D-09 strict: ONLY ToolCallError; never enrich other exceptions — that's a v1.4 candidate per CONTEXT.md deferred).
  </behavior>
  <action>
Create `tests/sdet/conftest.py` with the exact shape from 18-PATTERNS.md lines 610-643:

```python
"""Phase 18 SDET-only conftest: ToolCallError -> JUnit user_properties hook.

Per Phase 18 CONTEXT.md D-09: pytest_exception_interact captures
ToolCallError exceptions and stashes (.code, .message) onto
report.user_properties so the pytest JUnit XML writer surfaces them as
<property name="..." value="..."/> children inside <testcase>. The
domain-UI XML parser at _runner.py reads these properties to drive the
em-dash FAIL row's failure_message (D-10).

This conftest is INDEPENDENT of the parametrize hook in tests/conftest.py
-- SDET tests are hand-authored, not parametrized over discovered tools.
The session fixtures still flow in via pytest_plugins inheritance through
the parent tests/conftest.py.
"""
from __future__ import annotations

from mcp_test_framework.sdet import ToolCallError


def pytest_exception_interact(node, call, report):
    """D-09: hoist ToolCallError fields onto report.user_properties.

    pytest emits user_properties into the JUnit XML as <property> children
    of <testcase>. The wrapper-side XML parser reads project-scoped keys
    (mcptf_error_code / mcptf_error_message) to feed the FAIL row.

    Strict: only ToolCallError is enriched. Other exceptions (AssertionError,
    plain RuntimeError, etc.) are passed through to pytest's normal failure
    machinery untouched. Generic exception enrichment is a v1.4 candidate
    (CONTEXT.md Deferred Ideas).
    """
    exc = call.excinfo.value if call.excinfo else None
    if isinstance(exc, ToolCallError):
        report.user_properties.append(("mcptf_error_code", exc.code or ""))
        report.user_properties.append(("mcptf_error_message", exc.message))
        # D-11: serialize the live CallToolResult so the --debug appendix
        # can render the raw block (CONTEXT.md lines 123-134). Empty string
        # when exc.raw is None — keeps the JUnit XML attribute well-formed
        # and lets the renderer detect "no raw" via empty-string check.
        report.user_properties.append((
            "mcptf_error_raw",
            exc.raw.model_dump_json(indent=2) if exc.raw is not None else "",
        ))
```

**Critical conventions:**
- `from __future__ import annotations` is present (matches Phase 17/18 module style).
- Import is `from mcp_test_framework.sdet import ToolCallError` — uses the public surface from Plan 18-04, NOT the internal `from mcp_test_framework.sdet.errors import ToolCallError` (operators reading this conftest see the canonical import).
- The hook function signature is exactly `(node, call, report)` — pytest's pytest_exception_interact API contract; do NOT type-annotate the params (pytest's stub types are not in our dependency tree and adding annotations creates pyright friction).
- The `exc.code or ""` coercion handles `code=None` by emitting empty string into XML (string-only attribute values).
- NO `pytest_plugins` line at the top — the parent `tests/conftest.py:pytest_plugins = ["mcp_test_framework.fixtures"]` propagates down via pytest's plugin inheritance; duplicating it here causes "plugin already registered" warnings.
- NO `pytest_generate_tests` parametrize hook (CONTEXT line 251 — SDET tests are hand-authored).

Do NOT:
- Import `_extract_code_message` or any internal symbol — only `ToolCallError`.
- Generalize the hook to other exception types (deferred).
- Replace `model_dump_json(indent=2)` with `model_dump_json()` (no-indent) — D-11 mandates the indented form because the `--debug` appendix re-emits the dump as `raw:` with 2-space indent per line; emitting an already-indented dump means the renderer can splice it without reflowing.
- Add `pytest_collection_modifyitems` or any other collection-level hook (out of scope).
  </action>
  <verify>
    <automated>uv run python -c "import sys; sys.path.insert(0, 'tests/sdet'); from importlib.util import spec_from_file_location, module_from_spec; spec = spec_from_file_location('sdet_conftest', 'tests/sdet/conftest.py'); m = module_from_spec(spec); spec.loader.exec_module(m); assert callable(m.pytest_exception_interact); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `tests/sdet/conftest.py`
    - `grep -c "def pytest_exception_interact" tests/sdet/conftest.py` returns 1
    - `grep -c "isinstance(exc, ToolCallError)" tests/sdet/conftest.py` returns 1
    - `grep -c "mcptf_error_code" tests/sdet/conftest.py` returns 1
    - `grep -c "mcptf_error_message" tests/sdet/conftest.py` returns 1
    - `grep -c "mcptf_error_raw" tests/sdet/conftest.py` returns 1 (D-11: third property carries CallToolResult dump)
    - `grep -c "model_dump_json(indent=2)" tests/sdet/conftest.py` returns 1 (D-11: indented JSON form)
    - `grep -c "exc.raw is not None" tests/sdet/conftest.py` returns 1 (None-safe coercion)
    - `grep -c "from mcp_test_framework.sdet import ToolCallError" tests/sdet/conftest.py` returns 1
    - `grep -c "pytest_plugins" tests/sdet/conftest.py` returns 0 (inherited from parent conftest; do NOT re-declare)
    - `grep -c "pytest_generate_tests" tests/sdet/conftest.py` returns 0 (no parametrize hook)
    - `grep -c "exc.code or \"\"" tests/sdet/conftest.py` returns 1 (None-to-empty-string coercion)
    - `uv run pyright tests/sdet/conftest.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `tests/sdet/conftest.py` installs the D-09 + D-11 `pytest_exception_interact` hook strictly for `ToolCallError`; emits THREE user_properties (`mcptf_error_code`, `mcptf_error_message`, `mcptf_error_raw` carrying the indented CallToolResult JSON dump); no parametrize hook; imports from the canonical public surface.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/sdet/test_basic_call.py — end-to-end sanity scenario</name>
  <files>tests/sdet/test_basic_call.py</files>
  <read_first>
    - src/mcp_test_framework/sdet/__init__.py (Plan 18-04 — verify mcp_session + tool are re-exported)
    - src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py (verify _REGISTRY contents — pick a tool with no required params, e.g. `list_registered_servers`)
    - src/mcp_test_framework/sdet/generated/homelab_mcp/list_registered_servers.py (verify the Params class has all-optional fields or constructable with no kwargs)
    - For the negative-path test: inspect the Params class for a field with a known non-trivial type (e.g. `vmid: int`, `node: str`) — record the EXACT tool name AND field:type pair you selected. The choice MUST be pinned into a header comment in the test file (acceptance criterion).
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (Claude's Discretion — minimum-viable SDET test lines 143-144; specifics lines 263)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target test body lines 666-700)
  </read_first>
  <behavior>
    - Test: `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse` succeeds (re-export sanity).
    - Test: `test_basic_tool_round_trip` is decorated with `@pytest.mark.asyncio`, depends on `mcp_session` fixture, and asserts the response object is an instance of `tool(name).response_cls` (CODEGEN-04 chain).
    - Test: `test_invalid_params_raises_before_wire` is decorated with `@pytest.mark.asyncio`, demonstrates that Pydantic validation fires at Params CONSTRUCTION (BEFORE any wire call) — uses `pytest.raises(ValidationError)`.
    - Test: invocation `uv run mcp-test-framework run --sdet` (with the homelab-mcp server available) collects this file and runs its tests.
  </behavior>
  <action>
Create `tests/sdet/test_basic_call.py`. The test exercises ONE tool through the SDET wrapper end-to-end against the active MCP server. Pick `list_registered_servers` if its generated `ListRegisteredServersParams` has all-optional fields (read the generated file to verify); otherwise pick another no-required-param tool from the homelab_mcp registry.

```python
"""Phase 18 SDET sanity: tool().call() end-to-end via mcp_session.

Per Phase 18 CONTEXT.md (Claude's Discretion) -- a minimum-viable scenario
exercising one tool through the SDET wrapper. This is the verification
harness that proves the whole Phase 18 surface composes end-to-end:

  1. The mcp_session fixture activates the homelab_mcp registry (D-02).
  2. tool("list_registered_servers") resolves through _ACTIVE_SLUG /
     _REGISTRIES (Phase 17 dispatch).
  3. .call(params) makes a real MCP wire call (D-08 + D-07 wiring from
     Plan 18-02).
  4. The response is constructed via CODEGEN-04's uniform .raw / .data /
     .text / .is_error contract.

Phase 19 will ship the real VM-lifecycle dogfood scenario; Phase 18's
sanity is a single tool call that doesn't require homelab-mcp's stateful
subsystems (Proxmox/Ansible/etc).

The chosen tool MUST be:
  - In the generated homelab_mcp registry.
  - Constructible with no required params (so the test runs without
    homelab-specific setup).
  - Read-only / idempotent (no side effects on real infrastructure).

Picked: list_registered_servers — exists in the registry, takes no
required params, read-only.

# tool: <NAME> chosen for known-typed field <FIELD>:<TYPE>
# (Lock this header comment line in the actual test file so the choice is
# pinned into the test artifact — see acceptance criteria. Replace <NAME>,
# <FIELD>, <TYPE> with the values you actually selected during read_first.)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.sdet import ToolResponse, mcp_session, tool  # noqa: F401


@pytest.mark.asyncio
async def test_basic_tool_round_trip(mcp_session) -> None:
    """SDET-01/03/04 + CODEGEN-05: tool().call() returns a typed response."""
    wrapper = tool("list_registered_servers")
    # Construct params with no required fields (verified against generated class).
    params = wrapper.params_cls()
    response = await wrapper.call(params)
    # CODEGEN-04 uniform surface.
    assert isinstance(response, ToolResponse)
    assert isinstance(response, wrapper.response_cls)
    assert response.is_error is False


@pytest.mark.asyncio
async def test_invalid_params_caught_before_wire(mcp_session) -> None:
    """SDET-04 + CODEGEN-02: Pydantic validation fires at Params construction.

    Constructing the Params class with a type-violating field raises
    Pydantic's ValidationError SYNCHRONOUSLY -- before any await touches
    the wire. This is the contract that lets SDETs trust the typed surface.
    """
    wrapper = tool("list_registered_servers")
    # Find a field with a known type and pass a wrong type. If
    # list_registered_servers has no fields at all, swap to a tool with at
    # least one typed field (e.g. get_proxmox_vm_status with vmid: int).
    with pytest.raises((ValidationError, TypeError)):
        wrapper.params_cls(vmid="not an int")  # type: ignore[call-arg]
```

**Critical implementation notes:**
- READ `src/mcp_test_framework/sdet/generated/homelab_mcp/list_registered_servers.py` FIRST to confirm the actual class shape. If `ListRegisteredServersParams` has no fields at all (`pass` body or only inherited), use a different tool for the `test_invalid_params_caught_before_wire` test that has a typed field — e.g. `get_proxmox_vm_status` with `vmid: int` field, or `register_server` with required string fields.
- If `list_registered_servers` requires fields, swap to whatever read-only tool in the generated registry has all-optional or no-field params. Document the choice in the docstring.
- Both tests use the `mcp_session` fixture (session-scoped — connects once for both tests).
- Use `@pytest.mark.asyncio` (NOT `@pytest_asyncio.fixture` — tests are tests, fixtures are fixtures).
- Use `pytest.raises((ValidationError, TypeError))` for the negative test — Pydantic v2 raises ValidationError, but some shapes raise TypeError; the union is defensive.

**Do NOT:**
- Pick a destructive tool (`create_vm`, `delete_vm`, `purge_devices`, etc.) — Phase 19's dogfood is the right place for those.
- Hard-code expected response content (`assert response.data["name"] == "homelab-mcp"`) — the server's exact response varies. Only assert STRUCTURAL truths (`isinstance`, `is_error is False`).
- Mock `mcp_session` — the whole point is to exercise the real fixture against the real server.
- Add a test that requires homelab-mcp's stateful subsystems (Proxmox unreachable, Ansible not configured, etc.) — Phase 20's `requires_homelab` marker is the right tool for that.
- Add live-stack assertions that depend on Proxmox/Ollama being reachable; this test runs against any homelab-mcp stdio process — even one with no infrastructure backends configured (`list_registered_servers` returns an empty list or registered metadata).
  </action>
  <verify>
    <automated>uv run python -c "import importlib; m = importlib.import_module('tests.sdet.test_basic_call'); assert hasattr(m, 'test_basic_tool_round_trip'); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `tests/sdet/test_basic_call.py`
    - `grep -c "@pytest.mark.asyncio" tests/sdet/test_basic_call.py` returns at least 2 (one per test)
    - `grep -c "mcp_session" tests/sdet/test_basic_call.py` returns at least 2 (fixture import + at-least-one test signature)
    - `grep -c "tool(" tests/sdet/test_basic_call.py` returns at least 2 (one per test using the wrapper)
    - `grep -c "from mcp_test_framework.sdet import" tests/sdet/test_basic_call.py` returns 1 (public surface only)
    - `grep -c "isinstance(response, ToolResponse)" tests/sdet/test_basic_call.py` returns 1
    - `grep -c "is_error is False" tests/sdet/test_basic_call.py` returns 1
    - `grep -c "pytest.raises" tests/sdet/test_basic_call.py` returns 1 (negative-path test)
    - `grep -cE "create_vm|delete_vm|purge_devices|deploy_" tests/sdet/test_basic_call.py` returns 0 (no destructive tools)
    - `grep -cE "^# tool: [a-z_]+ chosen for known-typed field [a-zA-Z_]+:[a-zA-Z_]+" tests/sdet/test_basic_call.py` returns 1 (Warning-4 lock: tool + field:type pinned in file header so it is not silently re-decidable on rerun)
    - `uv run pytest --collect-only tests/sdet/test_basic_call.py 2>&1 | grep -c "test_basic_tool_round_trip"` returns at least 1 (collection works)
    - `uv run pyright tests/sdet/test_basic_call.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `tests/sdet/test_basic_call.py` exists; two `@pytest.mark.asyncio` tests exercise the SDET surface end-to-end via the public `mcp_test_framework.sdet` exports; chosen tool is no-required-param + read-only.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP server -> test | `list_registered_servers` response originates from homelab-mcp; flows into `response.is_error` / `response.data` assertions. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-16 | T (Tampering) | response from server-under-test | accept | Test only asserts structural truths (isinstance, is_error is False); never trusts content beyond structure. |
| T-18-17 | E (Elevation) | tool chosen for sanity test | mitigate | Picked `list_registered_servers` — read-only, idempotent; never mutates real infrastructure even if test repeats. Acceptance criterion bans destructive tools by name. |
</threat_model>

<verification>
- `uv run pytest tests/sdet/test_basic_call.py -x` passes (against the homelab-mcp stdio server reachable via the project config).
- `uv run mcp-test-framework run --sdet` exits 0 (or returns the test pass/fail summary; non-zero only on actual SDET test failures).
- `tests/sdet/conftest.py:pytest_exception_interact` fires when a ToolCallError-raising test runs; verified indirectly through Plan 18-08's renderer tests.
</verification>

<success_criteria>
- `tests/sdet/__init__.py`, `tests/sdet/conftest.py`, `tests/sdet/test_basic_call.py` all exist.
- pytest collects `tests/sdet/` under `--sdet`.
- The D-09 hook is wired correctly (verified via Plan 18-08's renderer integration tests).
- The sanity test exercises `tool().call()` end-to-end through the public API surface.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-07-SUMMARY.md` documenting: the three new files, the chosen sanity-test tool (and why), the D-09 hook's strict-ToolCallError discipline, and the dependency Plan 18-08's renderer tests inherit (JUnit-property emission proves end-to-end via this hook).
</output>
