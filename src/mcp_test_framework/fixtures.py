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

import httpx
import pytest
import pytest_asyncio

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


@pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
async def _preflight(config: Config):
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
    """
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
# mcp_client -- session-scoped, AsyncExitStack-owned (FIX-01; Pattern A)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight):
    """Long-lived McpTestClient session for the test run.

    AsyncExitStack ownership inside the fixture body satisfies Pitfall 1
    "reverse-order unwind in the SAME task that did __aenter__".
    Depends on _preflight so the session only spawns after preflight has
    confirmed binary + Ollama + target tool.
    """
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            McpTestClient(
                config.mcp_server.command,
                config.mcp_server.args,
                config.mcp_server.timeout_seconds,
            )
        )
        yield client


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
