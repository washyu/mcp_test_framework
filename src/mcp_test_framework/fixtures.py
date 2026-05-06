"""Session-scoped pytest-asyncio fixtures + _preflight gate (Phase 4 FIX-01/02/03).

Registered via tests/conftest.py:
    pytest_plugins = ["mcp_test_framework.fixtures"]

All fixtures are session-scoped (loop_scope="session" for async ones, matching
the pyproject.toml lock `asyncio_default_fixture_loop_scope = "session"`).
mcp_client and judge own their I/O lifecycle through AsyncExitStack so the
reverse-order unwind happens in the SAME task that did __aenter__
(PITFALLS Pitfall 1).

_preflight is autouse + session-scoped: it runs once before any test and
calls pytest.exit(reason, returncode=2) if Ollama is unreachable, the
configured model is missing, or the MCP server command does not resolve.
returncode=2 distinguishes preflight-abort from pytest's regular pass/fail
(0/1) so a future CI can branch on it.

The judge fixture is type-annotated against the Judge Protocol (not
OllamaJudge concrete class) -- D-layout-2 / SEED-001 enabler. The fixture
body internally instantiates OllamaJudge; tests use `judge: Judge`.
"""
from __future__ import annotations

import asyncio
import contextlib
import shutil
from contextlib import AsyncExitStack

import anyio
import httpx
import pytest
import pytest_asyncio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework.config import Config
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.ollama_judge import OllamaJudge
from mcp_test_framework.rubrics import (
    ClarityRubric,
    DisambiguationRubric,
    ParametersRubric,
)

# ---------------------------------------------------------------------------
# config -- sync, session-scoped (Pattern B)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def config() -> Config:
    """Load env + YAML config once per session (Phase 1 precedence: CLI > env > YAML > default)."""
    return Config()


# ---------------------------------------------------------------------------
# _preflight -- autouse session gate (FIX-02; D-preflight-1..4)
# ---------------------------------------------------------------------------


def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Skip preflight if every collected test lives under tests/unit/.

    Unit tests are pure-data sync tests with no MCP/Ollama dependency. The
    integration tests (tests/test_*.py) are the consumers preflight is
    designed to gate -- D-preflight-1 / FIX-02. This guard preserves
    `autouse=True` semantics for integration runs while letting
    `uv run pytest tests/unit/` pass on a machine without homelab-mcp /
    Ollama (Plan 04-02 Task 3 acceptance).
    """
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        # item.nodeid uses forward slashes on every platform pytest supports
        if not item.nodeid.startswith("tests/unit/"):
            return True
    return False


@pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
async def _preflight(request: pytest.FixtureRequest, config: Config):
    """Three pre-test checks; pytest.exit(returncode=2) on any failure.

    Recommended order (CONTEXT D-discretion, cheapest first):
      1. shutil.which(mcp_server.command) -- local FS lookup, no network.
      2. Ollama GET /api/tags -- single HTTP call with 10s connect timeout.
      3. MCP brief McpTestClient session -- single subprocess spawn + list_tools.
      4. Target tool membership -- already in step 3's list_tools result.

    Each failure path emits a structured single-line diagnostic naming the
    failed precondition AND the configured value (D-preflight-4). No ERROR
    cascade across 10 tests (Pitfall 3 mitigation).

    NO LLM warmup -- deferred per CONTEXT Deferred Ideas. Cold-start cost is
    paid by TEST-05 within the locked 120s httpx.Timeout.

    The session-scope guard `_session_needs_preflight` short-circuits when
    only `tests/unit/` items are collected -- unit tests have no MCP/Ollama
    dependency and must not be gated by integration preconditions.
    """
    if not _session_needs_preflight(request):
        yield
        return

    # --- Check 1: MCP binary on PATH ---------------------------------------
    if shutil.which(config.mcp_server.command) is None:
        pytest.exit(
            f"MCP command {config.mcp_server.command!r} not found on PATH",
            returncode=2,
        )

    # --- Check 2: Ollama /api/tags reachable + model present ----------------
    try:
        async with httpx.AsyncClient(
            base_url=config.ollama.base_url,
            timeout=httpx.Timeout(10.0, connect=10.0),
        ) as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        pytest.exit(
            f"Ollama at {config.ollama.base_url} not reachable: "
            f"{exc.__class__.__name__}: {exc}",
            returncode=2,
        )

    available_models = [m.get("name", "") for m in (payload.get("models") or [])]
    if config.ollama.model not in available_models:
        pytest.exit(
            f"model {config.ollama.model!r} not in /api/tags "
            f"(available: {available_models!r})",
            returncode=2,
        )

    # --- Check 3 + 4: MCP brief handshake + target tool membership ----------
    try:
        async with McpTestClient(
            config.mcp_server.command,
            config.mcp_server.args,
            config.mcp_server.timeout_seconds,
        ) as brief_client:
            tools = await brief_client.list_tools()
    except Exception as exc:
        pytest.exit(
            f"MCP handshake with {config.mcp_server.command!r} failed: "
            f"{exc.__class__.__name__}: {exc}",
            returncode=2,
        )

    tool_names = [t.name for t in tools]
    if config.target.tool_name not in tool_names:
        pytest.exit(
            f"target tool {config.target.tool_name!r} not in MCP server tool list "
            f"(available: {tool_names!r})",
            returncode=2,
        )

    # All preflight checks passed; the brief MCP session has been closed by
    # AsyncExitStack on context-manager exit. The mcp_client fixture below
    # respawns its own long-lived session (D-preflight-2). Yield with no
    # value -- autouse fixtures need not yield a value.
    yield


# ---------------------------------------------------------------------------
# mcp_client -- session-scoped, pure-asyncio driver + anyio owner task
# (Phase 04.1 DEF-04-03-B follow-up; resolves debug session
# fixture-teardown-cancel-scope)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight):
    """Long-lived McpTestClient session -- pure-asyncio driver + anyio owner task.

    The fixture body holds NO anyio cancel scopes across the yield. That was
    the failure mode of the prior owner-task + outer ``anyio.create_task_group``
    rewrite (DEF-04-03-B; debug session fixture-teardown-cancel-scope):
    pytest-asyncio's session-scoped finalizer drives the generator's
    ``__anext__`` from a different asyncio.Task than the one that ran setup,
    and any anyio CancelScope spanning the yield is task-pinned to the setup
    task -> ``RuntimeError: Attempted to exit cancel scope in a different
    task than it was entered in`` at teardown.

    Fix shape: all anyio scopes (``stdio_client``, ``ClientSession``,
    ``anyio.fail_after``) live exclusively inside the owner task, which runs
    as a stdlib ``asyncio.Task``. The fixture body coordinates with the owner
    via an ``asyncio.Future`` (handoff of the ready ``McpTestClient``) and an
    ``asyncio.Event`` (shutdown signal). Setup and teardown of the fixture
    run on different ``asyncio.Task`` instances under pytest-asyncio's
    session-scoped finalizer model -- tolerated here because no anyio
    CancelScope is opened on one task and closed on another.

    Cancellation semantics:
    - If the owner crashes during setup before resolving the ready future,
      the owner sets the future's exception, preserving the original error.
    - The fixture body bounds the ready-await with ``asyncio.wait_for`` to
      avoid hangs if the owner never sets the future.
    - On teardown, the shutdown event is set; the owner is awaited with a
      timeout. If still running, it is cancelled and the CancelledError is
      swallowed so the owner's anyio scopes can unwind cleanly inside the
      owner task.
    """
    params = StdioServerParameters(
        command=config.mcp_server.command,
        args=config.mcp_server.args,
    )
    loop = asyncio.get_running_loop()
    ready: asyncio.Future[McpTestClient] = loop.create_future()
    shutdown = asyncio.Event()

    async def _owner_task() -> None:
        # All anyio cancel scopes enter AND exit on this single owner task.
        try:
            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write) as session,
            ):
                try:
                    with anyio.fail_after(config.mcp_server.timeout_seconds):
                        await session.initialize()
                    client = McpTestClient._wrap(
                        session, config.mcp_server.timeout_seconds
                    )
                except BaseException as exc:
                    if not ready.done():
                        ready.set_exception(exc)
                    raise
                ready.set_result(client)
                await shutdown.wait()
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc)
            raise

    owner = asyncio.create_task(_owner_task(), name="mcp_client_owner")
    try:
        client = await asyncio.wait_for(
            asyncio.shield(ready),
            timeout=config.mcp_server.timeout_seconds + 5,
        )
    except BaseException:
        owner.cancel()
        with contextlib.suppress(BaseException):
            await owner
        raise
    try:
        yield client
    finally:
        shutdown.set()
        try:
            await asyncio.wait_for(owner, timeout=10)
        except asyncio.TimeoutError:
            owner.cancel()
            with contextlib.suppress(BaseException):
                await owner


# ---------------------------------------------------------------------------
# judge -- session-scoped, type-annotated against Judge Protocol (FIX-01; D-layout-2)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def judge(config: Config, _preflight) -> Judge:
    """Long-lived OllamaJudge instance, exposed to tests as Judge Protocol.

    Internal instantiation of OllamaJudge stays in this fixture body so
    swapping in AgenticJudge (SEED-001) post-MVP is a one-fixture-body
    change. Tests annotate `judge: Judge`, never `judge: OllamaJudge`.
    """
    async with AsyncExitStack() as stack:
        instance = await stack.enter_async_context(
            OllamaJudge(
                config.ollama.base_url,
                config.ollama.model,
                config.ollama.timeout_seconds,
            )
        )
        yield instance


# ---------------------------------------------------------------------------
# target_tool -- session-scoped, defense-in-depth membership (FIX-03; Pattern D)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):
    """Resolve target tool by name; raises ToolNotFoundError if absent.

    Defense in depth alongside _preflight's check (D-preflight-3). Phase 2's
    McpTestClient.get_tool already raises ToolNotFoundError with the
    candidate list in the message -- re-raise unchanged.
    """
    return await mcp_client.get_tool(config.target.tool_name)


# ---------------------------------------------------------------------------
# Three rubric fixtures -- sync, session-scoped (D-rubrics-1; Pattern E)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rubric_clarity() -> ClarityRubric:
    return ClarityRubric()


@pytest.fixture(scope="session")
def rubric_disambiguation() -> DisambiguationRubric:
    return DisambiguationRubric()


@pytest.fixture(scope="session")
def rubric_parameters() -> ParametersRubric:
    return ParametersRubric()
