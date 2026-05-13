"""mcp_session fixture + registry activation -- Phase 18 SDET-03.

Per Phase 18 CONTEXT.md decisions:
  - D-01: alias of the existing session-scoped ``mcp_client`` fixture. No
    duplicate stdio_client / ClientSession lifecycle is introduced.
  - D-02: 5-step registry activation in the fixture body (read serverInfo,
    slugify, import generated module, read ``_REGISTRY``, install slots).
    Restore prior state on teardown.
  - D-03: missing generated module triggers
    ``_pytest_exit_operator_tone(returncode=2)``.

Phase 04.1 invariant: the D-02 mutations are SYNC (module import + dict and
attribute assignment), so no new anyio cancel scope is opened across the
yield.

Accessor choice for ``serverInfo.name``: the public
``McpTestClient.server_info`` attribute (Plan 18-03 Rule 3 deviation). The
mcp SDK's ``ClientSession`` discards ``InitializeResult.serverInfo`` after
the handshake; the ``mcp_client`` fixture's owner task captures the result
and threads ``server_info`` through ``McpTestClient._wrap``.
"""
from __future__ import annotations

import importlib

import pytest_asyncio

from mcp_test_framework.fixtures import _pytest_exit_operator_tone
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.sdet import _tool_factory as _tf
from mcp_test_framework.sdet._slugs import server_slug


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    """Live ClientSession driver + active SDET registry (D-01/D-02/D-03)."""
    # Step 1+2: server name -> slug (single source of truth: _slugs.server_slug).
    # Public accessor ``McpTestClient.server_info`` (Plan 03 Rule 3 fix); the
    # mcp SDK drops serverInfo after the handshake, so the fixture's owner
    # task captured it and threaded it through ``_wrap(..., server_info=)``.
    assert mcp_client.server_info is not None, (
        "mcp_client.server_info must be populated by the fixture owner task "
        "before mcp_session activates the registry"
    )
    server_name = mcp_client.server_info.name
    slug = server_slug(server_name)

    # Step 3+4: import the generated module; D-03 fail-loud on ModuleNotFoundError.
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

    # Step 5: install registry + active slug + active client. Save priors.
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
