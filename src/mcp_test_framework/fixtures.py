"""Session-scoped pytest-asyncio fixtures + ``_preflight`` gate.

Registered via tests/conftest.py:
    pytest_plugins = ["mcp_test_framework.fixtures"]

All fixtures are session-scoped (``loop_scope="session"`` for async ones,
matching the pyproject.toml lock
``asyncio_default_fixture_loop_scope = "session"``). ``mcp_client`` and
``judge`` own their I/O lifecycle through ``AsyncExitStack`` so the
reverse-order unwind happens in the SAME task that did ``__aenter__``.

``_preflight`` is autouse + session-scoped: it runs once before any test and
calls ``pytest.exit(reason, returncode=2)`` if Ollama is unreachable, the
configured model is missing, or the MCP server command does not resolve.
``returncode=2`` distinguishes preflight-abort from pytest's regular
pass/fail (0/1) so a future CI can branch on it.

The ``judge`` fixture is type-annotated against the ``Judge`` Protocol (not
``OllamaJudge`` concrete class) so swapping in a different judge backend is
a one-fixture-body change. Tests use ``judge: Judge``.
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

from mcp_test_framework._isolation import _build_subprocess_env
from mcp_test_framework.config import Config
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import TestCodeConfig, ToolConfig
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
def mcp_config(request: pytest.FixtureRequest) -> Config:  # renamed from `config`; unprefixed alias lives in _plugin.py
    """Return the session's loaded ``Config``.

    Resolution order:
      1. ``session.config._mcp_contracts_config`` -- the stash set by
         ``_plugin.pytest_configure`` when ``[tool.pytest.ini_options]
         mcp_config_file = PATH`` is present (library mode) OR when the CLI
         subprocesses pytest with ``-o "mcp_config_file=PATH"`` (CLI mode).
         This is the canonical path post-Phase-27: one config-resolution
         route end-to-end, no env-var write.
      2. Bare ``Config()`` -- legacy fallback for tests that bypass the
         plugin entirely (e.g. framework self-tests that construct their
         own ``Config`` via ``yaml_file=`` and never hit this fixture).
         v1.5 dropped the env-var path-pointer fallback in
         ``settings_customise_sources``; the only surviving routes are
         ``--config PATH`` (CLI) and ``[tool.pytest.ini_options]
         mcp_config_file = PATH`` (library).
    """
    cfg = getattr(request.session.config, "_mcp_contracts_config", None)
    if cfg is not None:
        return cfg
    # Stash-miss fallback for framework self-tests that bypass the plugin.
    # Config.test_code is REQUIRED (no default) -- bare Config() raises ValidationError,
    # so construct explicitly. host_isolation keeps its 'strict' default. (Phase 34-09)
    return Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))


# ---------------------------------------------------------------------------
# _preflight -- autouse session gate
# ---------------------------------------------------------------------------


# Live-MCP scopes for test-code-author paths: items whose nodeids start
# with these prefixes call the real homelab-mcp / Ollama stack via
# hand-authored scenarios (no `mcp_contract` marker; the marker is
# applied only to framework-injected contract tests). Everything else
# (framework unit / smoke / runner self-tests under tests/framework/...)
# must skip preflight so it runs cleanly on a machine with no
# homelab-mcp / Ollama configured.
#
# The plugin applies the `mcp_contract` marker to every injected
# contract test; `_session_needs_preflight` detects them via marker
# iteration. The test-code-author path (`tests/test_code/`) stays on
# path-prefix detection because items there do NOT carry the contract
# marker.
_LIVE_PREFIXES: tuple[str, ...] = (
    "tests/test_code/",
)


def _session_needs_preflight(request: pytest.FixtureRequest) -> bool:
    """Return True iff any collected item needs the live-MCP preflight gate.

    Two-branch detection (live = needs preflight; pure-data = does not):

      PRIMARY (marker): any item carrying ``pytest.mark.mcp_contract``.
        Covers the plugin's framework-injected contract tests, including
        the synthetic ``<mcp-contracts>::test_*`` nodeids that no
        path-prefix could match. The marker is applied per-item by
        ``_plugin.pytest_collection_modifyitems``.

      SECONDARY (nodeid prefix): any item whose nodeid starts with
        ``_LIVE_PREFIXES``. Covers hand-authored test-code-author
        scenarios under ``tests/test_code/``, which do NOT carry the
        contract marker but still drive a live MCP session.

    Framework-only test suites (``tests/framework/...``) are pure-data and
    must NOT trigger preflight -- a developer with no homelab-mcp /
    Ollama configured can still run them.

    Historical note: an earlier version keyed solely on a path prefix
    (``tests/unit/``) that no longer exists in the current layout. The
    stale check always returned True and forced operators to either
    point the framework at a config file or pass ``--noconftest``. The
    predicate was inverted to a live-scope allowlist, and now hybridized
    with marker detection so plugin-injected synthetic nodeids are
    covered without a brittle nodeid grammar dependency.
    """
    items = getattr(request.session, "items", []) or []
    if not items:
        return False
    for item in items:
        # PRIMARY: framework-injected contract tests carry `mcp_contract`.
        # `iter_markers` may be absent on lightweight test fakes; treat
        # absence as "no marker" rather than crashing the predicate.
        iter_markers = getattr(item, "iter_markers", None)
        if iter_markers is not None and any(iter_markers("mcp_contract")):
            return True
        # SECONDARY: test-code-author paths only. nodeid uses forward
        # slashes on every platform pytest supports.
        if item.nodeid.startswith(_LIVE_PREFIXES):
            return True
    return False


@pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
async def _preflight(request: pytest.FixtureRequest):
    """Three pre-test checks; ``pytest.exit(returncode=2)`` on any failure.

    Order (cheapest first):
      1. shutil.which(mcp_server.command) -- local FS lookup, no network.
      2. Ollama GET /api/tags -- single HTTP call with 10s connect timeout.
      3. MCP brief McpTestClient session -- single subprocess spawn + list_tools.
      4. Target tool membership -- already in step 3's list_tools result.

    Each failure path emits a structured single-line diagnostic naming the
    failed precondition AND the configured value (no ERROR cascade across
    every parametrized test).

    No LLM warmup is performed -- cold-start cost is paid within the locked
    120s httpx.Timeout the first time a judge call fires.

    The session-scope guard ``_session_needs_preflight`` short-circuits when
    no items carry the ``mcp_contract`` marker AND no items live under the
    test-code-author scope (``tests/test_code/``) -- framework self-tests
    under ``tests/framework/...`` have no MCP/Ollama dependency and must
    not be gated by integration preconditions.

    The ``config`` fixture is requested *lazily* via
    ``request.getfixturevalue`` AFTER the live-MCP scope check, instead of
    as a direct parameter. With ``test_code.generated_root`` now required on
    Config, a bare ``Config()`` constructed for framework-only test
    sessions (no operator config) would fail with the canonical
    missing-required-field error (see docs/ERROR-STYLE.md) before the
    short-circuit could run. Fetching the fixture only inside the
    live-MCP branch preserves the missing-config fail-loud behavior where
    it matters (operator-facing live runs) while keeping framework
    self-tests green without requiring every framework test to point at
    a config file.
    """
    if not _session_needs_preflight(request):
        yield
        return

    config: Config = request.getfixturevalue("mcp_config")  # renamed fixture

    # --- Check 1: MCP binary on PATH ---------------------------------------
    if shutil.which(config.mcp_server.command) is None:
        # Enrich the bare "not found on PATH" with a hint pointing users at
        # the canonical two-route config surface + config.example.yaml.
        # Keep in sync with tests/conftest.py:_resolve_tool_names (same hint).
        pytest.exit(
            f"MCP command {config.mcp_server.command!r} not found on PATH"
            f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
            "If you intended to use a different command, set "
            "`[tool.pytest.ini_options] mcp_config_file = PATH` in "
            "pyproject.toml or pass `--config PATH` to `mcp-contracts run`, "
            "pointing at a config.yaml that defines mcp_server.command "
            "(e.g. `command: uvx, args: [homelab-mcp]`). The repo ships "
            "`config.example.yaml` you can copy and edit.",
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
        # Same canonical-two-route / config.example.yaml hint as Check 1
        # above and tests/conftest.py:_resolve_tool_names, in the rare case
        # Check 1's shutil.which passed but McpTestClient's belt-and-
        # suspenders re-check raised FileNotFoundError anyway.
        if isinstance(exc, FileNotFoundError) and str(exc).startswith(
            "MCP server command not on PATH:"
        ):
            msg += (
                f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
                "If you intended to use a different command, set "
                "`[tool.pytest.ini_options] mcp_config_file = PATH` in "
                "pyproject.toml or pass `--config PATH` to "
                "`mcp-contracts run`, pointing at a config.yaml that "
                "defines mcp_server.command (e.g. `command: uvx, args: "
                "[homelab-mcp]`). The repo ships `config.example.yaml` "
                "you can copy and edit."
            )
        pytest.exit(msg, returncode=2)

    # Unknown tool names in `config.tools` -> session-start warning (NOT a
    # load-time error, NOT a hard fail). The discovered list isn't known
    # until the MCP handshake above runs, so this check lives here.
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
    # respawns its own long-lived session. Yield with no value -- autouse
    # fixtures need not yield a value.
    yield


# ---------------------------------------------------------------------------
# _isolated_home -- session-scoped per-run tempdir for HOME/USERPROFILE redirect.
# Single source of truth for the isolation tempdir; cleanup at session exit.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def _isolated_home(mcp_config: Config):
    """Per-session tempdir owning the HOME/USERPROFILE redirect target.

    Single source of truth for the isolation tempdir. Verification tests
    that read the redirected ``.homelab_mcp/`` subdirectory depend on this
    fixture directly rather than reaching into ``mcp_client`` internals.
    Future fixtures that need isolation guarantees depend on the same
    fixture -- no duplicate tempdir creation.

    Mode branching:
      - ``host_isolation='strict'`` (default): allocate a TemporaryDirectory
        and yield its Path. v1.0-v1.4 behavior preserved verbatim.
      - ``host_isolation='passthrough'``: short-circuit; yield ``None``
        without engaging the tempdir machinery. Passthrough disables the
        HOME redirect this tempdir was supporting, so allocating it would
        be dead state.

    Lifecycle (strict branch) owned via ``AsyncExitStack`` -- cleanup is
    automatic on session exit. ``tempfile.TemporaryDirectory`` is a SYNC
    context manager, so we use ``stack.enter_context`` (not
    ``enter_async_context``). This is safe with respect to the
    "no anyio cancel scope across the yield" invariant because
    ``TemporaryDirectory`` is stdlib sync -- it opens no anyio cancel scope.

    Tempdir prefix ``mcp-test-fw-`` so orphaned tempdirs (should cleanup
    ever fail) are debuggable from ``dir %TEMP%`` output.
    """
    if mcp_config.host_isolation == 'passthrough':
        yield None
        return
    async with AsyncExitStack() as stack:
        tmpdir = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mcp-test-fw-")
        )
        yield Path(tmpdir)


# ---------------------------------------------------------------------------
# mcp_client -- session-scoped, pure-asyncio driver + anyio owner task.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(mcp_config: Config, _preflight, _isolated_home: Path | None):  # param `config`→`mcp_config`
    """Long-lived McpTestClient session -- pure-asyncio driver + anyio owner task.

    The fixture body holds NO anyio cancel scopes across the yield. That was
    the failure mode of a prior owner-task + outer ``anyio.create_task_group``
    rewrite (the debug-session fixture-teardown-cancel-scope failure):
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
        command=mcp_config.mcp_server.command,
        args=mcp_config.mcp_server.args,
        # Strict (default): allowlist + HOME redirect to the shared isolation
        # tempdir. Passthrough: full os.environ copy; tempdir unallocated.
        env=_build_subprocess_env(mcp_config.host_isolation, _isolated_home),
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
                    with anyio.fail_after(mcp_config.mcp_server.timeout_seconds):
                        init_result = await session.initialize()
                    # Capture serverInfo so the test-code ``mcp_session`` fixture
                    # can derive the generated-module slug. The mcp SDK
                    # discards ``InitializeResult`` after caching
                    # ``_server_capabilities`` only.
                    client = McpTestClient._wrap(
                        session,
                        mcp_config.mcp_server.timeout_seconds,
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
            timeout=mcp_config.mcp_server.timeout_seconds + 5,
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
# judge -- session-scoped, type-annotated against Judge Protocol
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_judge(mcp_config: Config, _preflight) -> Judge:  # renamed from `judge`; param `config`→`mcp_config`
    """Long-lived ``OllamaJudge`` instance, exposed to tests as ``Judge`` Protocol.

    Internal instantiation of ``OllamaJudge`` stays in this fixture body so
    swapping in a different judge backend is a one-fixture-body change.
    Tests annotate ``judge: Judge``, never ``judge: OllamaJudge``.
    """
    async with AsyncExitStack() as stack:
        instance = await stack.enter_async_context(
            OllamaJudge(
                mcp_config.ollama.base_url,
                mcp_config.ollama.model,
                mcp_config.ollama.timeout_seconds,
            )
        )
        yield instance


# ---------------------------------------------------------------------------
# target_tool -- session-scoped, defense-in-depth membership
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_target_tool(  # renamed from `target_tool`
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly via ``tests/conftest.py``).

    The ``pytest_generate_tests`` hook in ``tests/conftest.py`` populates
    ``request.param`` with each discovered tool name. Test IDs render as
    ``test_<name>[<tool_name>]`` uniformly across the allowlist's selected
    tools.

    Indirect parametrize on a session-scoped fixture creates one fixture
    instance per ``request.param`` value within session scope; ``mcp_client``
    (also session-scoped) is shared -- ONE long-lived MCP session.
    """
    return await mcp_client.get_tool(request.param)


# ---------------------------------------------------------------------------
# tool_config -- per-test ToolConfig resolution
# ---------------------------------------------------------------------------


@pytest.fixture
def tool_config(mcp_config: Config, mcp_target_tool) -> ToolConfig:  # params renamed (fixture name unchanged — not in SC5 collision list)
    """Resolve ``config.tools.get(target_tool.name, ToolConfig())`` per test.

    Default (function) scope is intentional: the fixture must reflect the
    per-test parametrized ``target_tool.name`` -- a session-scoped fixture
    would freeze on the first parameter and serve a stale entry to other
    parametrized cases.

    Tools with no ``tools.<name>`` entry receive a default ``ToolConfig()``
    (``skip=False``, ``call_arguments={}``, ``judges=None`` -> all rubrics).
    Sync fixture (no async resources) -- safe under the cancel-scope
    invariant; no anyio scope is opened across yield.
    """
    return mcp_config.tools.get(mcp_target_tool.name, ToolConfig())


# ---------------------------------------------------------------------------
# Three rubric fixtures -- sync, session-scoped
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mcp_rubric_clarity() -> ClarityRubric:  # renamed from `rubric_clarity`
    return ClarityRubric()


@pytest.fixture(scope="session")
def mcp_rubric_disambiguation() -> DisambiguationRubric:  # renamed from `rubric_disambiguation`
    return DisambiguationRubric()


@pytest.fixture(scope="session")
def mcp_rubric_parameters() -> ParametersRubric:  # renamed from `rubric_parameters`
    return ParametersRubric()
