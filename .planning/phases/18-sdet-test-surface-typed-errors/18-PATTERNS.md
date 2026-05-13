# Phase 18: SDET test surface + typed errors - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 13 (4 modify, 9 new)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/sdet/__init__.py` (MODIFY) | barrel/exports | static | `src/mcp_test_framework/sdet/__init__.py` (current) | exact (extend in place) |
| `src/mcp_test_framework/sdet/_tool_factory.py` (MODIFY) | factory/runtime | request-response | `src/mcp_test_framework/mcp_client.py:207-210` (`call_tool`) | exact |
| `src/mcp_test_framework/sdet/errors.py` (NEW) | exception type | data model | `src/mcp_test_framework/sdet/response.py` (sibling module convention) | role-match (no existing typed-exception module) |
| `src/mcp_test_framework/sdet/session.py` (NEW) | pytest-asyncio fixture | event-driven (yield) | `src/mcp_test_framework/fixtures.py:324-410` (`mcp_client`) | exact |
| `src/mcp_test_framework/cli.py` (MODIFY) | CLI command | request-response | `src/mcp_test_framework/cli.py:343-540` (existing `run` Typer command) | exact (extend in place) |
| `src/mcp_test_framework/_runner.py` (MODIFY) | XML parser + renderer | transform | `_runner.py:422-519` (`parse_junit_xml`) + `_runner.py:732-841` (digest builders) + `_runner.py:998-1048` (debug appendix) | exact |
| `tests/sdet/__init__.py` (NEW) | marker package | static | (none — empty marker) | n/a (one-line file) |
| `tests/sdet/conftest.py` (NEW) | pytest hook | event-driven | `tests/conftest.py` (pytest_plugins + hook pattern) | role-match |
| `tests/sdet/test_basic_call.py` (NEW) | integration test | request-response | `tests/framework/unit/test_tool_factory.py` (wrapper exercise) | role-match (async test using ToolWrapper) |
| `tests/framework/unit/test_sdet_fixtures.py` (NEW) | unit test (fixture surface) | event-driven | `tests/framework/unit/test_tool_factory.py` (registry state reset) | exact |
| `tests/framework/unit/test_tool_call_error.py` (NEW) | unit test (exception shape) | data model | `tests/framework/unit/test_tool_response.py` (sibling — `.data`/`.text` accessor pins) | exact |
| `tests/framework/unit/test_sdet_cli.py` (NEW) | unit test (CLI flag) | request-response | `tests/framework/unit/test_runner_explain.py` (CliRunner-based Typer invocation + subprocess stub) | exact |
| `tests/framework/unit/test_sdet_renderer.py` (NEW) | unit test (XML parser + render) | transform | `tests/framework/unit/test_runner_parser.py` + `test_runner_pre_run_digest.py` | exact |

## Pattern Assignments

---

### `src/mcp_test_framework/sdet/__init__.py` (barrel/exports, static)

**Analog:** itself (current shape locks the export contract).

**Current file (verbatim, lines 1-15):**
```python
"""mcp_test_framework.sdet -- SDET test surface (Phase 17 onwards).

Phase 17 (CODEGEN-01..06) ships:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class
    that every generated <Tool>Response inherits from (CODEGEN-04, D-07).

Phases 18-20 will extend this re-export with `mcp_session`, `tool`,
`requires_homelab`. Do not add those here -- they are out of scope per
CONTEXT.md "Out of scope (deliberate)".
"""
from __future__ import annotations

from mcp_test_framework.sdet.response import ToolResponse

__all__ = ["ToolResponse"]
```

**Phase 18 extension shape (target):**
```python
from mcp_test_framework.sdet.response import ToolResponse
from mcp_test_framework.sdet._tool_factory import tool
from mcp_test_framework.sdet.errors import ToolCallError
from mcp_test_framework.sdet.session import mcp_session

__all__ = ["ToolResponse", "tool", "ToolCallError", "mcp_session"]
```

Header docstring updates to remove the "out of scope" sentence about Phase 18 and add the new symbols. Underscore-prefixed internals (`_tool_factory`) stay internal; the public name `tool` is what re-exports.

---

### `src/mcp_test_framework/sdet/_tool_factory.py` (factory/runtime, request-response)

**Analog:** `src/mcp_test_framework/mcp_client.py:207-210` for the wire-call shape; the file itself for the seam contract.

**Current `.call()` body (lines 70-82) — the seam to replace:**
```python
async def call(self, params: P) -> R:
    """Wire body deferred to Phase 18. Raises NotImplementedError."""
    raise NotImplementedError(
        "tool().call() requires Phase 18's `mcp_session` fixture which "
        "owns the ClientSession. Phase 17 ships the codegen + dispatch "
        "shape only. See REQUIREMENTS.md SDET-03 (Phase 18) for the "
        "fixture contract."
    )
```

**Wire-call pattern from `mcp_client.py:207-210` (the `call_tool` wrapper Phase 18 mirrors):**
```python
async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
    assert self._session is not None, "McpTestClient not entered"
    async with asyncio.timeout(self._timeout):
        return await self._session.call_tool(name, arguments)
```

**Phase 18 `.call()` body shape (assembled from D-08 heuristic + D-07 raise pattern):**
```python
async def call(self, params: P) -> R:
    # 1. Resolve the active client (the McpTestClient yielded by mcp_session).
    #    Module-local state: a single _ACTIVE_CLIENT slot set by the fixture
    #    body (analogous to _ACTIVE_SLUG). The fixture is responsible for
    #    setting/clearing this around the yield.
    if _ACTIVE_CLIENT is None:
        raise RuntimeError(
            "no active MCP client. tool().call() requires the `mcp_session` "
            "fixture (Phase 18). Use it in an SDET test under `tests/sdet/`."
        )

    # 2. Serialize params via Pydantic — mode="json" because MCP wire format
    #    expects JSON-serializable dicts (Claude's-discretion default).
    arguments = params.model_dump(mode="json")

    # 3. Make the wire call through the existing wrapper (asyncio.timeout
    #    already enforced inside McpTestClient.call_tool).
    result = await _ACTIVE_CLIENT.call_tool(self.name, arguments)

    # 4. D-07 + D-08: surface errors as ToolCallError, success as response_cls.
    if result.isError:
        from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message
        code, message = _extract_code_message(result)
        raise ToolCallError(tool=self.name, code=code, message=message, raw=result)

    return self.response_cls(raw=result)
```

**Module-state slot to add (alongside lines 38-39):**
```python
_ACTIVE_CLIENT: "McpTestClient | None" = None  # set by mcp_session fixture body
```

The slot contract + dispatch shape stay LOCKED — only the `.call()` body and the new `_ACTIVE_CLIENT` slot are touched. The `tool(name)` factory at lines 85-115 is unchanged.

---

### `src/mcp_test_framework/sdet/errors.py` (NEW — exception type, data model)

**Analog:** `src/mcp_test_framework/sdet/response.py` (sibling-module convention: one operator-visible class per file, no underscore prefix because operators write `from mcp_test_framework.sdet import ToolCallError`).

**Module-header pattern (from `response.py:1-26`):**
```python
"""ToolResponse base -- uniform .raw / .data / .text / .is_error per CODEGEN-04.

Per Phase 17 CONTEXT.md decisions:
  - D-07: ...
  - D-04: pyright is the static-type-check verifier; this module must be
    pyright-strict-clean.
...
"""
from __future__ import annotations
```

**Phase 18 `errors.py` shape (assembled from D-07 + D-08):**
```python
"""ToolCallError -- typed exception for MCP tool isError=True responses (UI-02).

Per Phase 18 CONTEXT.md decisions:
  - D-07: plain Exception subclass (NOT Pydantic) for traceback-friendly
    pytest integration and standard `except ToolCallError as e:` idiom.
  - D-08: strict heuristic chain for code/message extraction:
      1. raw.structuredContent dict -> read "code"/"message" string keys
      2. first TextContent.text -> json.loads -> dict -> read same keys
      3. else: message=concat(TextContent.text), code=None
    Only "code" and "message" are recognized — no synonyms, no recursion.
    Non-string `code` is coerced via str(); non-string `message` falls through.
"""
from __future__ import annotations

import json
from mcp.types import CallToolResult, TextContent


class ToolCallError(Exception):
    """Raised by ToolWrapper.call() when result.isError is True.

    Attributes:
        tool: MCP tool name (e.g. "create_vm").
        code: server-supplied error code, or None if absent.
        message: human-readable error prose.
        raw: the live mcp.types.CallToolResult (not a Pydantic clone).
    """

    def __init__(
        self,
        *,
        tool: str,
        code: str | None,
        message: str,
        raw: CallToolResult,
    ) -> None:
        self.tool = tool
        self.code = code
        self.message = message
        self.raw = raw
        super().__init__(self._format_default())

    def _format_default(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


def _extract_code_message(raw: CallToolResult) -> tuple[str | None, str]:
    """D-08 heuristic chain. Returns (code, message)."""
    # Step 1: structuredContent dict
    sc = getattr(raw, "structuredContent", None)
    if isinstance(sc, dict):
        code = sc.get("code")
        message = sc.get("message")
        if isinstance(message, str):
            return (str(code) if code is not None else None, message)

    # Step 2: first TextContent JSON
    for block in raw.content:
        if isinstance(block, TextContent):
            try:
                parsed = json.loads(block.text)
            except (json.JSONDecodeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                code = parsed.get("code")
                message = parsed.get("message")
                if isinstance(message, str):
                    return (str(code) if code is not None else None, message)
            break  # only try the first TextContent

    # Step 3: concat fallback
    concat = "".join(b.text for b in raw.content if isinstance(b, TextContent))
    return (None, concat)
```

**Why filter on `isinstance(block, TextContent)` (from `response.py:60-69` Pitfall 7 comment):**
> Pitfall 7 (17-RESEARCH.md): CallToolResult.content is heterogeneous (TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource). .text MUST filter on isinstance(block, TextContent) -- never .getattr('text') naively.

---

### `src/mcp_test_framework/sdet/session.py` (NEW — pytest-asyncio fixture, event-driven)

**Analog:** `src/mcp_test_framework/fixtures.py:324-410` (`mcp_client` fixture — D-01 explicitly aliases it).

**Fixture decorator + signature pattern (fixtures.py:324-355):**
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight, _isolated_home: Path):
    """Long-lived McpTestClient session -- pure-asyncio driver + anyio owner task.

    The fixture body holds NO anyio cancel scopes across the yield. ...
    """
```

**D-03 fail-loud helper pattern (fixtures.py:57-81):**
```python
def _pytest_exit_operator_tone(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    returncode: int = 2,
) -> typing.NoReturn:
    """Render an operator-tone message and call pytest.exit.

    Mirrors cli._emit_operator_error's format (docs/ERROR-STYLE.md):
        <summary>
        <blank>
        <detail line 1>
        ...
        <blank>
        next: <action verb> <command>
    """
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    pytest.exit("\n".join(parts), returncode=returncode)
```

**Phase 18 `session.py` shape (assembled from D-01 + D-02 + D-03):**
```python
"""mcp_session fixture + registry activation -- Phase 18 SDET-03.

Per Phase 18 CONTEXT.md decisions:
  - D-01: alias / re-export of the existing session-scoped `mcp_client`
    fixture. No duplicate stdio_client/ClientSession lifecycle introduced.
  - D-02: registry activation lives in the fixture body. Reads
    serverInfo.name from the live session, slugifies via _slugs.server_slug,
    imports mcp_test_framework.sdet.generated.<slug>, populates _REGISTRIES
    and _ACTIVE_SLUG, yields, restores prior state on teardown.
  - D-03: ModuleNotFoundError during step 4 -> _pytest_exit_operator_tone
    with the operator-readable message.

The D-02 mutations are SYNC (importlib.import_module + dict mutation), so
no new anyio cancel scope is opened across the yield (Phase 04.1 invariant
preserved).
"""
from __future__ import annotations

import importlib
import pytest_asyncio

from mcp_test_framework.fixtures import _pytest_exit_operator_tone, mcp_client
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.sdet import _tool_factory as _tf
from mcp_test_framework.sdet._slugs import server_slug


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    """Live ClientSession driver + active SDET registry (D-01/D-02/D-03)."""
    # Step 1+2: server name from the initialized session.
    server_name = mcp_client._session.server_info.name  # or cached initialize result
    slug = server_slug(server_name)

    # Step 3+4: import the generated module, fail loud on ModuleNotFoundError.
    try:
        mod = importlib.import_module(
            f"mcp_test_framework.sdet.generated.{slug}"
        )
    except ModuleNotFoundError:
        _pytest_exit_operator_tone(
            summary=(
                f"No generated SDET classes found for server {slug!r} "
                f"(from serverInfo.name={server_name!r})."
            ),
            detail=[
                f"  The fixture tried to `import "
                f"mcp_test_framework.sdet.generated.{slug}` and the module "
                "does not exist.",
                "  This usually means `gen-sdet-classes` has not been run "
                "for this server, or the server's name changed.",
            ],
            next_step=(
                "run `mcp-test-framework gen-sdet-classes` against this "
                "server first, then re-run with --sdet"
            ),
        )

    # Step 5: install the registry + active slug + active client.
    registry = getattr(mod, "_REGISTRY")
    prior_slug = _tf._ACTIVE_SLUG
    prior_client = _tf._ACTIVE_CLIENT
    _tf._REGISTRIES[slug] = registry
    _tf._ACTIVE_SLUG = slug
    _tf._ACTIVE_CLIENT = mcp_client

    try:
        yield mcp_client
    finally:
        # Step 7: restore prior state. Pop registry only if we installed it.
        _tf._ACTIVE_SLUG = prior_slug
        _tf._ACTIVE_CLIENT = prior_client
        _tf._REGISTRIES.pop(slug, None)
```

**Critical pattern lock from fixtures.py:241-242 / 277-280:**
> autouse fixtures need not yield a value.

Here `mcp_session` is NOT autouse (it's depended on explicitly by SDET tests). It yields `mcp_client` so tests can `async def test_x(mcp_session): result = await mcp_session.call_tool(...)`.

---

### `src/mcp_test_framework/cli.py` (MODIFY — CLI command, request-response)

**Analog:** `cli.py:343-540` (existing `run` Typer command).

**Flag registration pattern (cli.py:394-414, the closest sibling — `--with-framework` + `--explain`):**
```python
with_framework: bool = typer.Option(
    False,
    "--with-framework",
    help=(
        "Also collect tests/framework/ (the framework's own self-tests) "
        "in addition to the operator-default tests/contract/. ..."
    ),
),
explain: bool = typer.Option(
    False,
    "--explain",
    help=(
        "Expand the pre-run digest's 'Skipping (N)' hint into one line "
        "per skipped tool with its skip reason, sorted alphabetically. ..."
    ),
),
```

**Phase 18 `--sdet` flag (D-04/D-05):**
```python
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

**Threading pattern (cli.py:486-491 — flag flows into runner):**
```python
rc, _tmp, _stdout, _stderr = _runner.run_pytest_subprocess(
    junit_xml=junit_xml,
    pytest_args=pytest_args,
    raw=True,
    with_framework=with_framework,
)
```

Phase 18 adds `sdet=sdet` kwarg to both `run_pytest_subprocess(...)` call sites (lines 486 and 541) and threads it through `_build_pytest_args` (see `_runner.py` patterns below).

**Pre-run digest dispatch (cli.py:532-539) — D-06 scenario-aware variant:**
```python
if not quiet:
    _runner._render_pre_run_digest(
        pre_run_ctx,
        with_framework=with_framework,
        explain=explain,
    )
```

Phase 18 adds an `if sdet:` branch around this block that calls the new `_render_scenario_pre_run_digest(...)` instead (planner picks the dispatch shape — either a new function or a parameter on the existing one; CONTEXT D-06 leans toward a new function).

---

### `src/mcp_test_framework/_runner.py` (MODIFY — XML parser + renderer, transform)

**Analog A — JUnit XML parser at lines 422-519 (D-09 hookup site):**

Current bucket-fill pattern (lines 487-501):
```python
failure = tc.find("failure")
error = tc.find("error")
skipped = tc.find("skipped")

if failure is not None or error is not None:
    # D-03 rule 1: any failed/error -> FAIL (sticky).
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

**Phase 18 D-09 hook (read JUnit `<property>` children — pytest's `report.user_properties` surface):**

Inside the same `if failure is not None or error is not None:` branch, BEFORE the `bucket.failure_message = msg` assignment:
```python
# Phase 18 D-09: ToolCallError-attached JUnit properties (set by
# tests/sdet/conftest.py:pytest_exception_interact) win over the
# raw <failure message="..."> attr when present.
props = tc.find("properties")
if props is not None:
    code = None
    message = None
    for prop in props.iter("property"):
        n = prop.get("name", "")
        if n == "mcptf_error_code":
            code = prop.get("value", "") or None
        elif n == "mcptf_error_message":
            message = prop.get("value", "")
    if message is not None:
        # D-10: "[code] message" when code present; else bare message.
        if code:
            msg = f"[{code}] {message}"
        else:
            msg = message
```

`ToolVerdict` dataclass at lines 374-396 may need a new optional field `tool_call_error_raw: str | None = None` for D-11's `--debug` appendix block; planner decides whether to extend the dataclass or scan the XML on demand inside `render_debug_appendix`.

**Analog B — pre-run digest at lines 732-802 (D-06 scenario-aware variant):**

The new function (planner places it adjacent to `_render_pre_run_digest`):
```python
def _render_scenario_pre_run_digest(
    ctx: RenderContext,
    scenarios: list[str],
    skipped_scenarios: dict[str, str],  # module_stem -> reason
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    """Phase 18 D-06: scenario-aware variant.

    Buckets are scenario MODULE names (e.g. 'proxmox_vm_lifecycle' from
    'tests/sdet/test_proxmox_vm_lifecycle.py') instead of tool names.
    Layout / line count / em-dash semantics match _render_pre_run_digest.
    """
    if file is None:
        file = sys.stdout
    running = sorted(scenarios)
    running_n = len(running)
    skipping_n = len(skipped_scenarios)
    judges_text = "(none — SDET scope)"  # SDET tests are not judge-graded
    running_text = ", ".join(running) if running else "(none)"

    print("=" * 40, file=file)
    print("MCP Test Framework (SDET)", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {running_n + skipping_n} scenarios", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)
```

Bucket-naming rule (CONTEXT specifics, line 262): `tests/sdet/test_proxmox_vm_lifecycle.py` -> `proxmox_vm_lifecycle` (strip `test_` prefix + `.py` suffix).

**Analog C — debug appendix at lines 998-1048 (D-11 ToolCallError block):**

Current pattern (lines 1036-1048 — block emission with named separator):
```python
failures_with_bodies = [
    (name, v.failure_body)
    for name, v in parsed.per_tool.items()
    if v.verdict == "FAIL" and v.failure_body
]
if failures_with_bodies:
    print("", file=file)
    print("--- failure tracebacks ---", file=file)
    for name, body in sorted(failures_with_bodies):
        print(f"{name}:", file=file)
        for line in body.splitlines():
            print(f"  {line}", file=file)
        print("", file=file)
```

**Phase 18 D-11 block (emitted BEFORE pytest's raw stdout, per CONTEXT line 133):**
```python
# Phase 18 D-11: ToolCallError dumps emit BEFORE raw pytest output so
# operators get a parseable summary to grep first. Re-parse the JUnit XML
# (or read pre-stashed dataclass fields) for the structured CallToolResult.
tool_call_errors = _extract_tool_call_errors_from_xml(xml_path)  # planner names
if tool_call_errors:
    for err in tool_call_errors:
        print("--- ToolCallError dump ---", file=file)
        print(f"tool: {err.tool}", file=file)
        print(f"code: {err.code or '(none)'}", file=file)
        print(f"message: {err.message}", file=file)
        print("raw:", file=file)
        for line in err.raw_dump.splitlines():
            print(f"  {line}", file=file)
        print("---", file=file)
        print("", file=file)

# (existing) raw pytest output, captured stderr, failure tracebacks ...
print("--- raw pytest output ---", file=file)
```

The triple-dash fence (`--- ... ---`) matches the existing aesthetic at lines 1024, 1033, 1043 — pin in tests as grep-able regression material.

**Analog D — `_build_pytest_args` at lines 81-110 (D-04 / D-05 path selection):**

Current (lines 102-109):
```python
forwarded = list(pytest_args or [])
args: list[str] = ["tests/contract"]
if with_framework:
    args.append("tests/framework")
if junit_xml is not None:
    args.append(f"--junitxml={junit_xml}")
args.extend(forwarded)
return args
```

**Phase 18 extension (D-04 swap + D-05 framework addition):**
```python
forwarded = list(pytest_args or [])
if sdet:
    args: list[str] = ["tests/sdet"]  # D-04: swap, not additive
else:
    args = ["tests/contract"]
if with_framework:
    args.append("tests/framework")  # D-05: always additive
if junit_xml is not None:
    args.append(f"--junitxml={junit_xml}")
args.extend(forwarded)
return args
```

`run_pytest_subprocess(...)` at line 136 grows a `sdet: bool = False` kwarg that forwards to `_build_pytest_args(..., sdet=sdet)`.

---

### `tests/sdet/__init__.py` (NEW — marker package)

**Analog:** n/a — empty file. Make the file empty (no docstring needed); the package marker is what matters for pytest's rootdir resolution and the `tests/sdet/conftest.py` isolation per the existing split (CONTEXT line 251: "the sdet-side conftest at tests/sdet/conftest.py is independent").

---

### `tests/sdet/conftest.py` (NEW — pytest hook, event-driven)

**Analog:** `tests/conftest.py` (the framework-wide conftest — pattern of top-level `pytest_plugins` + module-level hook functions).

**Module header pattern (tests/conftest.py:1-18):**
```python
"""Pytest session-level configuration.
... docstring ...
"""
from __future__ import annotations

pytest_plugins = ["mcp_test_framework.fixtures"]
```

**Phase 18 `tests/sdet/conftest.py` shape (CONTEXT D-09):**
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

import pytest

from mcp_test_framework.sdet import ToolCallError


def pytest_exception_interact(node, call, report):
    """D-09: hoist ToolCallError fields onto report.user_properties.

    pytest emits user_properties into the JUnit XML as <property> children
    of <testcase>. The wrapper-side XML parser reads project-scoped keys
    (mcptf_error_code / mcptf_error_message) to feed the FAIL row.
    """
    exc = call.excinfo.value if call.excinfo else None
    if isinstance(exc, ToolCallError):
        report.user_properties.append(("mcptf_error_code", exc.code or ""))
        report.user_properties.append(("mcptf_error_message", exc.message))
```

---

### `tests/sdet/test_basic_call.py` (NEW — integration test, request-response)

**Analog:** `tests/framework/unit/test_tool_factory.py` (the only existing file exercising `ToolWrapper.call()`, though it pins the NotImplementedError stub).

**Async test pattern (test_tool_factory.py:84-96):**
```python
@pytest.mark.asyncio
async def test_call_raises_not_implemented_with_phase18_reference() -> None:
    """Phase 17 ships only the seam: .call() must raise NotImplementedError
    naming the missing Phase 18 fixture."""
    tf._ACTIVE_SLUG = "homelab_mcp"
    tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}
    wrapper = tool("create_vm")
    with pytest.raises(NotImplementedError) as exc:
        await wrapper.call(_FakeParams(name="x"))
```

**Phase 18 minimum-viable sanity test (CONTEXT line 143 + specifics §"Minimum viable SDET test"):**
```python
"""Phase 18 SDET sanity: tool().call() end-to-end against the synthetic server.

Per Phase 18 CONTEXT.md (Claude's Discretion) -- a minimum-viable scenario
that exercises one tool through the wrapper without requiring live
homelab-mcp. Asserts:
  1. await tool("basic_tool").call(BasicToolParams(...)) returns a
     BasicToolResponse instance (CODEGEN-04 chain).
  2. .raw.isError is False.
  3. .data resolves through the fallback chain.
  4. Invalid Params raises Pydantic ValidationError BEFORE the wire call.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.sdet import tool, mcp_session  # noqa: F401  re-export check


@pytest.mark.asyncio
async def test_basic_tool_round_trip(mcp_session) -> None:
    # mcp_session activates the registry; tool() lookup works now.
    wrapper = tool("basic_tool")
    response = await wrapper.call(wrapper.params_cls(input="hello"))
    assert response.is_error is False
    assert response.data is not None


@pytest.mark.asyncio
async def test_invalid_params_raises_before_wire(mcp_session) -> None:
    wrapper = tool("basic_tool")
    with pytest.raises(ValidationError):
        wrapper.params_cls(input=12345)  # wrong type
```

Note: this test depends on a "synthetic fixture server from Phase 17" referenced in CONTEXT line 143 — planner verifies that fixture is reachable, or substitutes a small in-tree stdio server / mocks `_tf._ACTIVE_CLIENT.call_tool`.

---

### `tests/framework/unit/test_sdet_fixtures.py` (NEW — unit test, fixture surface)

**Analog:** `tests/framework/unit/test_tool_factory.py` (registry-state reset fixture; exercises `_tf._ACTIVE_SLUG` and `_tf._REGISTRIES` mutation directly).

**State-reset fixture pattern (test_tool_factory.py:30-38):**
```python
@pytest.fixture(autouse=True)
def _reset_module_state():
    """Tests mutate module-level state; reset on teardown to prevent bleed."""
    saved_active = tf._ACTIVE_SLUG
    saved_registries = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_active
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)
```

Phase 18 extends this fixture to also save/restore `_tf._ACTIVE_CLIENT` (the new slot).

**Tests to pin (D-01/D-02/D-03):**
- D-01: `mcp_session` is importable from `mcp_test_framework.sdet`; introspection (e.g., `inspect.getsourcefile`) shows it is in `session.py` and shares the `mcp_client` dependency.
- D-02: with `mcp_client` mocked to return a session whose `serverInfo.name == "fake-server"`, entering `mcp_session` populates `_tf._REGISTRIES["fake_server"]` and sets `_tf._ACTIVE_SLUG = "fake_server"`; on teardown both revert.
- D-03: when `importlib.import_module` raises `ModuleNotFoundError`, the fixture calls `pytest.exit` with returncode=2 and the message contains all four signal phrases: "No generated SDET classes", the slug, `gen-sdet-classes`, and `--sdet`.

---

### `tests/framework/unit/test_tool_call_error.py` (NEW — unit test, exception shape)

**Analog:** `tests/framework/unit/test_tool_response.py` (sibling — pins `.data` fallback chain on `ToolResponse`, same module style).

**Patterns to pin (D-07 + D-08):**

D-07 shape:
- `ToolCallError("..." ).args[0]` == `"[CODE] msg"` when code present.
- `str(ToolCallError(...))` == `"[CODE] msg"` (symmetric with renderer per CONTEXT line 264).
- `isinstance(e, Exception)` True; `isinstance(e, BaseModel)` False.
- Attributes `.tool`, `.code`, `.message`, `.raw` exposed (use `dataclasses.fields` analogue via attribute checks).

D-08 heuristic chain (one test per step):
- Step 1: `raw.structuredContent = {"code": "VM_NAME_TAKEN", "message": "name in use"}` → `code == "VM_NAME_TAKEN"`, `message == "name in use"`.
- Step 1 coercion: `{"code": 404, "message": "x"}` → `code == "404"`.
- Step 1 missing message: `{"code": "X"}` (no message) → fall through to step 2/3.
- Step 2: structuredContent None, content = `[TextContent(text='{"code":"X","message":"Y"}')]` → `("X", "Y")`.
- Step 2 list/scalar non-dict: `content[0].text == "[1,2,3]"` → fall through.
- Step 3: content = `[TextContent(text="boom")]` only → `(None, "boom")`.
- Step 3 multi-text: two TextContent blocks → concatenated.
- Step 3 mixed types: TextContent + ImageContent → only TextContent.text contributes (Pitfall 7).
- Strict key set: `{"errorCode": "X", "detail": "Y"}` → falls all the way through to step 3 (no synonym recognition).

---

### `tests/framework/unit/test_sdet_cli.py` (NEW — unit test, CLI flag)

**Analog:** `tests/framework/unit/test_runner_explain.py` (CliRunner-based Typer invocation + subprocess stub via monkeypatch of `subprocess.run`).

**CliRunner invocation pattern (test_runner_explain.py:21-24):**
```python
def _invoke(*args: str):
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app
    return CliRunner().invoke(app, list(args))
```

**Subprocess stub pattern (test_runner_explain.py:27-43):**
```python
def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")

    def _fake(argv, **kwargs):
        junit_args = [
            a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")
        ]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        assert "--explain" not in argv, "--explain leaked to pytest argv"
        return SimpleNamespace(
            returncode=returncode, stdout="...", stderr="", args=argv
        )

    return _fake
```

**Help-registration negative-test pattern (test_runner_explain.py:83-88):**
```python
def test_run_help_lists_explain_flag() -> None:
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--explain" in result.output
```

**Phase 18 tests to pin (D-04/D-05 composition matrix):**

| Combination | Expected `argv` to subprocess |
|-------------|-------------------------------|
| (default) | `[..., "tests/contract"]` |
| `--with-framework` | `[..., "tests/contract", "tests/framework"]` |
| `--sdet` | `[..., "tests/sdet"]` (NOT contract) |
| `--sdet --with-framework` | `[..., "tests/sdet", "tests/framework"]` |
| `--sdet --raw` | argv has `tests/sdet`; domain UI NOT invoked |
| `--sdet -q` | argv has `tests/sdet`; pre-run digest NOT printed |
| `--sdet` (registered) | `run --help` output contains `--sdet` |
| `--sdet` (forwarded) | `--sdet` NEVER appears in `argv` (wrapper-owned flag) |

Stub `subprocess.run` via monkeypatch in `_runner.run_pytest_subprocess`'s call site; assert the `argv` passed to it.

---

### `tests/framework/unit/test_sdet_renderer.py` (NEW — unit test, XML parser + render)

**Analog A — XML parser tests:** `tests/framework/unit/test_runner_parser.py` (existing tests for `parse_junit_xml`; reuses XML-fixture pattern with files in `tests/framework/fixtures/`).

**Analog B — digest tests:** `tests/framework/unit/test_runner_pre_run_digest.py` (the `_render_pre_run_digest` pinning; uses `capsys` + a hand-constructed `RenderContext`).

**Tests to pin (D-06/D-09/D-10/D-11):**

D-09 hookup:
- Given a JUnit XML with `<testcase><failure message="raw"/><properties><property name="mcptf_error_code" value="VM_NAME_TAKEN"/><property name="mcptf_error_message" value="name already in use"/></properties></testcase>`, the parser sets `bucket.failure_message == "[VM_NAME_TAKEN] name already in use"` (NOT `"raw"`).
- Given the same XML without the `<properties>` block, falls back to `bucket.failure_message == "raw"` (existing behavior preserved — Phase 16 regression guard).
- Given `mcptf_error_message` only (no code), `failure_message == "name already in use"` (bare).

D-10 FAIL row format:
- With `failure_message = "[VM_NAME_TAKEN] name already in use"`, `_render_per_tool_rows` produces a line containing `"✗ FAIL — [VM_NAME_TAKEN] name already in use"` (em-dash U+2014; brackets first).
- With `failure_message = "name already in use"` (code None), produces `"✗ FAIL — name already in use"`.

D-06 scenario digest:
- With `scenarios=["proxmox_vm_lifecycle", "basic_call"]`, `_render_scenario_pre_run_digest` emits a header containing `"Running:      2  (basic_call, proxmox_vm_lifecycle)"` (alphabetical).
- With `skipped_scenarios={"flaky_thing": "skip-reason text"}` and `explain=True`, the explain-expansion variant emits `"flaky_thing  — skip-reason text"` (em-dash, two-space hang).
- The digest height stays ≤ 10 lines regardless of N (matches `_render_pre_run_digest` lock at `_runner.py:758-759`).

D-11 `--debug` appendix block:
- When a ToolCallError-attached failure is present, the rendered appendix contains the block lead-in `"--- ToolCallError dump ---"` BEFORE `"--- raw pytest output ---"`.
- The block contains `tool: <name>`, `code: <code or "(none)">`, `message: <message>`, and a `raw:` section whose body is indented 2 spaces and contains a JSON-shaped CallToolResult dump.
- When NO ToolCallError-attached failures are present, the appendix is byte-identical to the Phase 14 baseline (D-13 invariant: each rung adds info; none re-shapes the layer below).

---

## Shared Patterns

### Operator-tone fail-loud helper
**Source:** `src/mcp_test_framework/fixtures.py:57-81` (`_pytest_exit_operator_tone`)
**Apply to:** `src/mcp_test_framework/sdet/session.py` (D-03 fail-loud on missing generated module)
```python
def _pytest_exit_operator_tone(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    returncode: int = 2,
) -> typing.NoReturn:
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    pytest.exit("\n".join(parts), returncode=returncode)
```
Mirrors `cli._emit_operator_error`'s format (`docs/ERROR-STYLE.md`). Reused verbatim — do not parallel-implement.

### Session-scoped pytest-asyncio fixture with loop_scope
**Source:** `src/mcp_test_framework/fixtures.py:324` decorator
**Apply to:** `src/mcp_test_framework/sdet/session.py:mcp_session`
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    ...
```
Matches `pyproject.toml` lock `asyncio_default_fixture_loop_scope = "session"`. Phase 04.1 invariant: no anyio CancelScope opened across the `yield` (D-02's `importlib.import_module` + dict mutation are sync; no cancel-scope risk).

### Module-state reset autouse fixture (test isolation)
**Source:** `tests/framework/unit/test_tool_factory.py:30-38`
**Apply to:** `tests/framework/unit/test_sdet_fixtures.py`, `tests/framework/unit/test_sdet_renderer.py` (anywhere that pokes `_tf._ACTIVE_SLUG` / `_tf._REGISTRIES` / new `_tf._ACTIVE_CLIENT`)
```python
@pytest.fixture(autouse=True)
def _reset_module_state():
    saved_active = tf._ACTIVE_SLUG
    saved_client = tf._ACTIVE_CLIENT  # NEW Phase 18 slot
    saved_registries = dict(tf._REGISTRIES)
    yield
    tf._ACTIVE_SLUG = saved_active
    tf._ACTIVE_CLIENT = saved_client
    tf._REGISTRIES.clear()
    tf._REGISTRIES.update(saved_registries)
```

### CliRunner-based Typer flag tests
**Source:** `tests/framework/unit/test_runner_explain.py:21-43`
**Apply to:** `tests/framework/unit/test_sdet_cli.py`
Use `from typer.testing import CliRunner; CliRunner().invoke(app, [...])`. Stub `subprocess.run` via monkeypatch so no real pytest is launched; inspect captured `argv` for path-selection assertions.

### Em-dash separator U+2014
**Source:** `src/mcp_test_framework/_runner.py:537` (locked at Phase 09 SC-3)
**Apply to:** `_runner.py` scenario digest (D-06), `_runner.py` FAIL row (D-10 — already in place), `_runner.py` ToolCallError appendix block (D-11)
Literal `—` (U+2014) in source. NOT ASCII hyphen, NOT en-dash. `tests/framework/unit/test_sdet_renderer.py` should byte-pin the codepoint.

### Triple-dash named appendix sections
**Source:** `src/mcp_test_framework/_runner.py:1024 / 1033 / 1043` (existing `--- raw pytest output ---` / `--- captured stderr ---` / `--- failure tracebacks ---`)
**Apply to:** D-11 `--- ToolCallError dump ---` lead-in. Match the aesthetic exactly: triple-dash, space, name, space, triple-dash. Pin as grep-able regression material.

### CallToolResult content iteration with `isinstance(block, TextContent)` filter
**Source:** `src/mcp_test_framework/sdet/response.py:60-69, 88-100` (Pitfall 7 mitigation)
**Apply to:** `src/mcp_test_framework/sdet/errors.py:_extract_code_message` (steps 2 + 3)
Never `getattr(b, 'text')` — heterogeneous content types (ImageContent/AudioContent/ResourceLink/EmbeddedResource) lack `.text` and would AttributeError on naive access.

## No Analog Found

All 13 files have at least a role-match analog. The closest gaps:

| File | Gap | Mitigation |
|------|-----|------------|
| `src/mcp_test_framework/sdet/errors.py` | No existing typed-exception module in `src/mcp_test_framework/sdet/`. The framework's other typed exceptions (`ToolNotFoundError` in `mcp_client.py`) live inline rather than in a dedicated module. | The sibling-module convention (`response.py` for the response base, one operator-visible class per file, no underscore prefix) is the strongest local analog. CONTEXT line 243 explicitly mandates the one-module-per-concern pattern. |
| `tests/sdet/test_basic_call.py` | The synthetic fixture server from Phase 17 (CONTEXT line 143) is referenced but its location is not pinned. | Planner confirms via Phase 17 artifacts or substitutes a small in-tree fixture; `test_tool_factory.py`'s `_FakeParams` / `_FakeResponse` pattern is a degraded-mode fallback. |

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/sdet/` (4 files)
- `src/mcp_test_framework/fixtures.py` (session fixture, fail-loud helper, preflight)
- `src/mcp_test_framework/_runner.py` (XML parser, renderer, subprocess dispatch)
- `src/mcp_test_framework/cli.py` (Typer command, flag registration)
- `src/mcp_test_framework/mcp_client.py` (call_tool wire shape)
- `tests/framework/unit/test_tool_factory.py` (registry-state reset, async test pattern)
- `tests/framework/unit/test_runner_explain.py` (Typer + subprocess stub)
- `tests/framework/unit/test_runner_parser.py` / `test_runner_pre_run_digest.py` (XML parser + renderer pinning)
- `tests/framework/unit/test_tool_response.py` (sibling-module exception pinning style)
- `tests/conftest.py` (pytest_plugins inheritance, hook function shape)
- `src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py` (_REGISTRY dict shape)

**Files scanned:** 13 (within the targeted analog set; no broader Grep sweep needed — CONTEXT.md `<canonical_refs>` named all the analogs)
**Pattern extraction date:** 2026-05-12
