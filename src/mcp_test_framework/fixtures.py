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

import shutil
from contextlib import AsyncExitStack

import anyio
import anyio.abc
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
# mcp_client -- session-scoped, owner-task + anyio.Event (Phase 04.1; D-01)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight):
    """Long-lived McpTestClient session -- owner-task + anyio.Event (Pitfall 1 fix; D-01).

    The owner task opens stdio_client + ClientSession, signals readiness via
    anyio's task_status.started(), parks on an anyio.Event until teardown,
    then unwinds the contextmanagers. Cancel scope enter+exit happen inside
    the SAME owner task -- anyio's task-pinning rule satisfied. Replaces the
    Phase 4 AsyncExitStack-owned shape that triggered DEF-04-03-B.

    Rationale: pytest-asyncio's session-finalizer drives this generator's
    `__anext__` from a different task than the per-test task that first
    triggered fixture setup. By moving the cancel scope into a long-lived
    owner task that we deterministically signal via anyio.Event, both the
    enter and exit of stdio_client's internal anyio.create_task_group()
    happen on the owner task -- never the finalizer task.
    """
    shutdown = anyio.Event()
    params = StdioServerParameters(
        command=config.mcp_server.command,
        args=config.mcp_server.args,
    )

    async def _owner_task(*, task_status: anyio.abc.TaskStatus[McpTestClient]) -> None:
        # Cancel scope opens AND closes inside this owner task -> no Pitfall 1.
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            with anyio.fail_after(config.mcp_server.timeout_seconds):
                await session.initialize()
            client = McpTestClient._wrap(session, config.mcp_server.timeout_seconds)
            task_status.started(client)  # unblocks tg.start; returns `client` to fixture body
            await shutdown.wait()         # park until teardown signals shutdown

    async with anyio.create_task_group() as tg:
        # tg.start() awaits task_status.started() OR re-raises owner errors here
        # (RESEARCH Pitfall A: owner task raising before started() propagates cleanly).
        client = await tg.start(_owner_task)
        try:
            yield client
        finally:
            shutdown.set()  # owner wakes, unwinds stdio_client + ClientSession on its own task
        # Implicit on leaving `async with`: task_group.__aexit__ waits for owner to drain.


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
