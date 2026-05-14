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
import tempfile
import typing
import warnings
from contextlib import AsyncExitStack
from pathlib import Path

import anyio
import httpx
import pytest
import pytest_asyncio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework._isolation import _build_isolated_env
from mcp_test_framework.config import Config
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import ToolConfig
from mcp_test_framework.ollama_judge import OllamaJudge
from mcp_test_framework.rubrics import (
    ClarityRubric,
    DisambiguationRubric,
    ParametersRubric,
)

# ---------------------------------------------------------------------------
# Operator-tone helper (mirrors cli._emit_operator_error per docs/ERROR-STYLE.md)
# ---------------------------------------------------------------------------


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

    fixtures.py cannot import _emit_operator_error from cli.py because pytest
    collects fixtures.py before the cli command is invoked, so this helper is
    a parallel implementation rendering the same shape via pytest.exit.
    """
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    pytest.exit("\n".join(parts), returncode=returncode)


# ---------------------------------------------------------------------------
# config -- sync, session-scoped (Pattern B)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def config() -> Config:
    """Load YAML config once per session (Phase 13 precedence: init kwarg > MCPTF_CONFIG_FILE path-pointer > YAML > defaults).

    Under `mcp-test-framework run`, the CLI resolver (`cli.py:_load_config`)
    writes the resolved YAML path to `MCPTF_CONFIG_FILE` before launching
    pytest.main(). This bare `Config()` then picks up that path via the
    fallback in `Config.settings_customise_sources` (Phase 13 review
    CR-01 fix). SAFE-05 is preserved: env vars do NOT inject scalar
    config values -- `MCPTF_CONFIG_FILE` is a path pointer only.
    """
    return Config()


# ---------------------------------------------------------------------------
# _preflight -- autouse session gate (FIX-02; D-preflight-1..4)
# ---------------------------------------------------------------------------


# Live-MCP scopes: items under these prefixes call the real homelab-mcp /
# Ollama stack and require the preflight gate. Anything else (framework
# unit / smoke / runner self-tests under tests/framework/...) must skip
# preflight so it runs cleanly on a machine with no homelab-mcp / Ollama
# configured.
#
# Kept in sync with the Phase 18 renderer's scope discrimination
# (tests/contract vs tests/sdet) — single source of truth for live scopes.
_LIVE_PREFIXES: tuple[str, ...] = ("tests/contract/", "tests/sdet/")


def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Return True iff any collected item is under a live-MCP scope.

    Live-MCP scopes (`tests/contract/`, `tests/sdet/`) call into the real
    homelab-mcp subprocess and Ollama HTTP API; everything else
    (`tests/framework/...`) is pure-data and must not be gated by the
    autouse preflight fixture.

    Pre-Phase-15 this keyed on `tests/unit/`, a prefix that no longer
    exists in the current layout (the Phase 15 reorg moved unit tests
    to `tests/framework/unit/`). The stale check always returned True
    and forced operators to either set `MCPTF_CONFIG_FILE` or pass
    `--noconftest` to run framework-only suites. Quick-task 260513-chh
    inverts the predicate to a live-scope allowlist (Option B from the
    originating todo) so the preflight gate keys on "does this item
    need a live MCP server?" rather than on a stale unit-test prefix.
    """
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        # item.nodeid uses forward slashes on every platform pytest supports.
        if item.nodeid.startswith(_LIVE_PREFIXES):
            return True
    return False


@pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
async def _preflight(request: pytest.FixtureRequest):
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
    no items under live-MCP scopes (`tests/contract/`, `tests/sdet/`) are
    collected -- framework self-tests under `tests/framework/...` have no
    MCP/Ollama dependency and must not be gated by integration
    preconditions.

    Phase 21.1 RELOC-01 (Rule 3 deviation, plan 21.1-01): the `config`
    fixture is requested *lazily* via ``request.getfixturevalue`` AFTER
    the live-MCP scope check, instead of as a direct parameter. With
    `sdet.generated_root` now required on Config, a bare ``Config()``
    constructed for framework-only test sessions (no MCPTF_CONFIG_FILE
    set) would fail with the SAFE-03 missing-required-field error before
    the short-circuit could run. Fetching the fixture only inside the
    live-MCP branch preserves the SAFE-03 behavior where it matters
    (operator-facing live runs) while keeping framework self-tests green
    without requiring every framework test to set MCPTF_CONFIG_FILE.
    """
    if not _session_needs_preflight(request):
        yield
        return

    config: Config = request.getfixturevalue("config")

    # --- Check 1: MCP binary on PATH ---------------------------------------
    if shutil.which(config.mcp_server.command) is None:
        # Quick-task 260507-j6i: enrich the bare "not found on PATH" with a
        # hint pointing users at MCPTF_CONFIG_FILE / config.example.yaml.
        # Keep in sync with tests/conftest.py:_resolve_tool_names (same hint).
        pytest.exit(
            f"MCP command {config.mcp_server.command!r} not found on PATH"
            f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
            "If you intended to use a different command, point "
            "MCPTF_CONFIG_FILE at a config.yaml that defines "
            "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
            "The repo ships `config.example.yaml` you can copy and edit.",
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
    except httpx.ConnectError as exc:
        _pytest_exit_operator_tone(
            summary=f"Cannot reach Ollama judge at {config.ollama.base_url}",
            detail=[
                "the framework tried to fetch /api/tags and the connection failed:",
                f"  {exc.__class__.__name__}: {exc}",
                "",
                "Ollama is the local LLM service used to score description quality.",
                "the framework cannot run any judge-graded test without it.",
            ],
            next_step=(
                "verify Ollama is running with `ollama serve`, then re-run "
                "`mcp-test-framework run`"
            ),
        )
    except httpx.TimeoutException as exc:
        _pytest_exit_operator_tone(
            summary=f"Ollama judge at {config.ollama.base_url} timed out",
            detail=[
                "the framework tried to fetch /api/tags and timed out after the "
                "connect window:",
                f"  {exc.__class__.__name__}: {exc}",
                "",
                "the service may be starting, overloaded, or blocked by a firewall.",
            ],
            next_step=(
                "check that `ollama serve` is responsive, then re-run "
                "`mcp-test-framework run`"
            ),
        )
    except Exception as exc:
        _pytest_exit_operator_tone(
            summary=f"Ollama judge at {config.ollama.base_url} returned an error",
            detail=[
                "the framework tried to fetch /api/tags and got an unexpected response:",
                f"  {exc.__class__.__name__}: {exc}",
            ],
            next_step=(
                "verify `ollama serve` is healthy at the configured base URL, "
                "then re-run `mcp-test-framework run`"
            ),
        )

    available_models = [m.get("name", "") for m in (payload.get("models") or [])]
    if config.ollama.model not in available_models:
        _pytest_exit_operator_tone(
            summary=f"Ollama model not installed: {config.ollama.model!r}",
            detail=[
                f"the configured judge model {config.ollama.model!r} is not in the "
                f"local Ollama library at {config.ollama.base_url}.",
                f"installed models: {available_models!r}",
            ],
            next_step=(
                f"run `ollama pull {config.ollama.model}` (or pick a model from the "
                "list above and update `ollama.model` in your config.yaml)"
            ),
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
        msg = (
            f"MCP handshake with {config.mcp_server.command!r} failed: "
            f"{exc.__class__.__name__}: {exc}"
        )
        # Quick-task 260507-j6i: same MCPTF_CONFIG_FILE / config.example.yaml
        # hint as Check 1 above and tests/conftest.py:_resolve_tool_names, in
        # the rare case Check 1's shutil.which passed but McpTestClient's
        # belt-and-suspenders re-check raised FileNotFoundError anyway.
        if isinstance(exc, FileNotFoundError) and str(exc).startswith(
            "MCP server command not on PATH:"
        ):
            msg += (
                f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
                "If you intended to use a different command, point "
                "MCPTF_CONFIG_FILE at a config.yaml that defines "
                "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
                "The repo ships `config.example.yaml` you can copy and edit."
            )
        pytest.exit(msg, returncode=2)

    # Phase 08 D-14 / D-18: unknown tool names in `config.tools` -> session-start
    # warning (NOT load-time error, NOT a hard fail). The discovered list isn't
    # known until the MCP handshake above runs, so this check lives here.
    discovered_names = {t.name for t in tools}
    for unknown_name in sorted(set(config.tools) - discovered_names):
        warnings.warn(
            f"tools.{unknown_name!r} configured but not in discovered tool list "
            f"(available: {sorted(discovered_names)!r}); config entry has no effect",
            UserWarning,
            stacklevel=2,
        )

    # All preflight checks passed; the brief MCP session has been closed by
    # AsyncExitStack on context-manager exit. The mcp_client fixture below
    # respawns its own long-lived session (D-preflight-2). Yield with no
    # value -- autouse fixtures need not yield a value.
    yield


# ---------------------------------------------------------------------------
# _isolated_home -- session-scoped per-run tempdir for HOME/USERPROFILE redirect
# (Phase 06 ISOL-05; D-12 fixture shape, D-14 single source of truth, D-15 cleanup)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def _isolated_home():
    """Per-session tempdir owning the HOME/USERPROFILE redirect target.

    Single source of truth for the isolation tempdir (D-14). Plan 06-03's
    ISOL-03 verification test depends on this fixture directly to read the
    redirected `.homelab_mcp/` subdirectory without reaching into mcp_client
    internals (D-13). Future Phase 07/08 fixtures that need isolation
    guarantees depend on the same fixture -- no duplicate tempdir creation.

    Lifecycle owned via AsyncExitStack -- cleanup is automatic on session
    exit (D-15). tempfile.TemporaryDirectory is a SYNC context manager, so
    we use stack.enter_context (not enter_async_context). This is safe with
    respect to the Phase 04.1 invariant ("no anyio cancel scope across the
    yield") because TemporaryDirectory is stdlib sync -- it opens no anyio
    cancel scope.

    Tempdir prefix `mcp-test-fw-` per CONTEXT.md <specifics> -- orphaned
    tempdirs (should ISOL-05 cleanup ever fail) are debuggable from
    `dir %TEMP%` output.
    """
    async with AsyncExitStack() as stack:
        tmpdir = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mcp-test-fw-")
        )
        yield Path(tmpdir)


# ---------------------------------------------------------------------------
# mcp_client -- session-scoped, pure-asyncio driver + anyio owner task
# (Phase 04.1 DEF-04-03-B follow-up; resolves debug session
# fixture-teardown-cancel-scope)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight, _isolated_home: Path):
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
        # ISOL-02 / ISOL-07 -- Phase 06 (D-14: shared tempdir)
        env=_build_isolated_env(_isolated_home),
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
                        init_result = await session.initialize()
                    # Phase 18 SDET-03 (Plan 03 Rule 3): capture serverInfo
                    # so the mcp_session fixture can derive the generated-
                    # module slug. The mcp SDK discards InitializeResult
                    # after caching _server_capabilities only.
                    client = McpTestClient._wrap(
                        session,
                        config.mcp_server.timeout_seconds,
                        server_info=init_result.serverInfo,
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
async def target_tool(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly via tests/conftest.py).

    The pytest_generate_tests hook in tests/conftest.py populates request.param
    with each discovered tool name. Test IDs render as test_<name>[<tool_name>]
    uniformly across the allowlist's selected tools (Phase 13 SAFE-01).
    Indirect parametrize on a session-scoped fixture
    creates one fixture instance per request.param value within session scope;
    mcp_client (also session-scoped) is shared -- ONE long-lived MCP session.
    """
    return await mcp_client.get_tool(request.param)


# ---------------------------------------------------------------------------
# tool_config -- per-test ToolConfig resolution (Phase 08 D-04 / TOOLCFG-06)
# ---------------------------------------------------------------------------


@pytest.fixture
def tool_config(config: Config, target_tool) -> ToolConfig:
    """Resolve `config.tools.get(target_tool.name, ToolConfig())` per test.

    Default (function) scope is intentional: the fixture must reflect the
    per-test parametrized `target_tool.name` -- a session-scoped fixture
    would freeze on the first parameter and serve a stale entry to other
    parametrized cases.

    Tools with no `tools.<name>` entry receive a default `ToolConfig()`
    (TOOLCFG-06: skip=False, call_arguments={}, judges=None -> all rubrics).
    Sync fixture (no async resources) -- safe under Phase 04.1 cancel-scope
    invariant; no anyio scope is opened across yield.
    """
    return config.tools.get(target_tool.name, ToolConfig())


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
