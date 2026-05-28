"""mcp_session fixture + registry activation.

The fixture is an alias of the existing session-scoped ``mcp_client`` fixture
-- no duplicate stdio_client / ClientSession lifecycle is introduced. Its
body performs a 5-step registry activation against the generated test-code
package for the connected server:

  1. read ``serverInfo.name`` off the live client
  2. derive a directory slug via ``server_slug``
  3. locate the generated package at
     ``<cfg.test_code.generated_root>/<slug>/__init__.py``
  4. load that module via ``importlib.util.spec_from_file_location`` and read
     its ``_REGISTRY`` attribute
  5. install ``_REGISTRY`` / ``_ACTIVE_SLUG`` / ``_ACTIVE_CLIENT`` slots on
     ``_tool_factory`` and restore prior state on teardown

The on-disk path must be a real directory containing a usable ``__init__.py``;
missing dir or missing init fail loud via ``_pytest_exit_operator_tone`` so
the operator gets an actionable next-step (run ``gen-test-classes``).

``submodule_search_locations=[str(slug_dir)]`` is non-negotiable: the
generated ``__init__.py`` uses RELATIVE imports
(``from .echo_message import ...``); without this kwarg those raise
``ImportError: attempted relative import with no known parent package``. The
framework no longer requires the generated tree to live under its own
``src/`` package; the operator controls the location via ``config.yaml``.

Invariant: the registry-activation mutations are SYNC (module load via
``spec_from_file_location`` + dict + attribute assignments), so no new anyio
cancel scope is opened across the yield. Pinned at
``tests/framework/unit/test_sdet_fixtures.py::test_session_module_opens_no_anyio_cancel_scope``.

Accessor choice for ``serverInfo.name``: the public
``McpTestClient.server_info`` attribute. The mcp SDK's ``ClientSession``
discards ``InitializeResult.serverInfo`` after the handshake; the
``mcp_client`` fixture's owner task captures the result and threads
``server_info`` through ``McpTestClient._wrap``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import pytest_asyncio

from mcp_test_framework.config import Config
from mcp_test_framework.fixtures import _pytest_exit_operator_tone
from mcp_test_framework.models import TestCodeConfig
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.test_code import _tool_factory as _tf
from mcp_test_framework.test_code._slugs import server_slug


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
):
    """Live ClientSession driver + active test-code registry."""
    # Step 1+2: server name -> slug (single source of truth: _slugs.server_slug).
    assert mcp_client.server_info is not None, (
        "mcp_client.server_info must be populated by the fixture owner task "
        "before mcp_session activates the registry"
    )
    server_name = mcp_client.server_info.name
    slug = server_slug(server_name)

    # Step 3: load the generated package from cfg.test_code.generated_root/<slug>/.
    # Audit: route through the plugin stash so the operator's resolved Config
    # (and its host_isolation setting) reaches the fixture. Bare-Config fallback
    # preserved for framework self-tests + the test_sdet_fixtures
    # `_install_session_config` monkeypatch shim. Mirrors fixtures.py:108-111.
    cfg = getattr(request.session.config, "_mcp_contracts_config", None)
    if cfg is None:
        # Explicit construction -- bare Config() raises ValidationError (test_code is REQUIRED
        # with no default). Mirrors fixtures.py stash-miss fallback. (Phase 34-09)
        cfg = Config(test_code=TestCodeConfig(generated_root="tests/test_code/_generated"))
    generated_root = cfg.test_code.generated_root
    if not generated_root.is_absolute():
        generated_root = Path.cwd() / generated_root
    slug_dir = generated_root / slug
    init_py = slug_dir / "__init__.py"

    if not slug_dir.is_dir() or not init_py.is_file():
        _pytest_exit_operator_tone(
            summary=(
                f"No generated test-code classes found for server {slug!r} "
                f"(from serverInfo.name={server_name!r})."
            ),
            detail=[
                f"  The fixture looked for `{init_py}` and it does not exist.",
                f"  Configured `test_code.generated_root`: {cfg.test_code.generated_root}",
                "  This usually means `gen-test-classes` has not been run "
                "for this server, or the server's name changed.",
            ],
            next_step=(
                "run `mcp-test-framework gen-test-classes` against this "
                "server first, then re-run with --test-code"
            ),
        )

    # The synthetic package prefix avoids sys.modules collisions across
    # repeated pytest invocations within the same process.
    pkg_name = f"_mcptf_test_code_generated_{slug}"
    for k in [k for k in list(sys.modules) if k == pkg_name or k.startswith(pkg_name + ".")]:
        del sys.modules[k]
    spec = importlib.util.spec_from_file_location(
        pkg_name,
        init_py,
        submodule_search_locations=[str(slug_dir)],
    )
    if spec is None or spec.loader is None:
        _pytest_exit_operator_tone(
            summary=(
                f"Failed to construct module spec for generated test-code "
                f"package at {init_py}."
            ),
            detail=[
                f"  importlib.util.spec_from_file_location returned None for "
                f"`{init_py}`.",
                "  This typically means the file exists but is not a valid "
                "Python source file (e.g. a 0-byte file or non-text content).",
            ],
            next_step=(
                "regenerate the package with `mcp-test-framework gen-test-classes`"
            ),
        )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)

    # Step 4+5: install registry + active slug + active client. Save priors.
    registry = getattr(mod, "_REGISTRY")
    prior_slug = _tf._ACTIVE_SLUG
    prior_client = _tf._ACTIVE_CLIENT
    _tf._REGISTRIES[slug] = registry
    _tf._ACTIVE_SLUG = slug
    _tf._ACTIVE_CLIENT = mcp_client

    try:
        yield mcp_client
    finally:
        # Restore prior state. Pop registry only if we installed it.
        _tf._ACTIVE_SLUG = prior_slug
        _tf._ACTIVE_CLIENT = prior_client
        _tf._REGISTRIES.pop(slug, None)
