"""mcp_session fixture + registry activation -- Phase 18 SDET-03, Phase 21.1 RELOC-02.

Phase 18 CONTEXT.md decisions (preserved):
  - D-01: alias of the existing session-scoped ``mcp_client`` fixture. No
    duplicate stdio_client / ClientSession lifecycle is introduced.
  - D-02: 5-step registry activation in the fixture body (read serverInfo,
    slugify, load generated module, read ``_REGISTRY``, install slots).
    Restore prior state on teardown.
  - D-03: missing generated module triggers
    ``_pytest_exit_operator_tone(returncode=2)``.

Phase 21.1 changes (RELOC-02):
  - Step 3 (module load) switched from ``importlib.import_module`` against a
    package-namespace path (``mcp_test_framework.sdet.generated.<slug>``) to
    ``importlib.util.spec_from_file_location`` against an on-disk path
    (``<cfg.sdet.generated_root>/<slug>/__init__.py``). The framework no
    longer requires the generated tree to live under its own ``src/``
    package; the operator controls the location via config.yaml.
  - The on-disk path must be a real directory containing a usable
    ``__init__.py``; missing dir or missing init fail loud via
    ``_pytest_exit_operator_tone``.
  - ``submodule_search_locations=[str(slug_dir)]`` is non-negotiable: the
    generated ``__init__.py`` uses RELATIVE imports
    (``from .echo_message import ...``); without this kwarg those raise
    ``ImportError: attempted relative import with no known parent package``.

Phase 04.1 invariant: the D-02 mutations are SYNC (module load via spec
exec + dict + attribute assignments), so no new anyio cancel scope is
opened across the yield. Pinned at
``tests/framework/unit/test_sdet_fixtures.py::test_session_module_opens_no_anyio_cancel_scope``.

Accessor choice for ``serverInfo.name``: the public
``McpTestClient.server_info`` attribute (Plan 18-03 Rule 3 deviation). The
mcp SDK's ``ClientSession`` discards ``InitializeResult.serverInfo`` after
the handshake; the ``mcp_client`` fixture's owner task captures the result
and threads ``server_info`` through ``McpTestClient._wrap``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest_asyncio

from mcp_test_framework.config import Config
from mcp_test_framework.fixtures import _pytest_exit_operator_tone
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.sdet import _tool_factory as _tf
from mcp_test_framework.sdet._slugs import server_slug


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    """Live ClientSession driver + active SDET registry (D-01/D-02/D-03)."""
    # Step 1+2: server name -> slug (single source of truth: _slugs.server_slug).
    assert mcp_client.server_info is not None, (
        "mcp_client.server_info must be populated by the fixture owner task "
        "before mcp_session activates the registry"
    )
    server_name = mcp_client.server_info.name
    slug = server_slug(server_name)

    # Step 3: load the generated package from cfg.sdet.generated_root/<slug>/.
    # Phase 21.1 RELOC-02: config-driven path, file-location loader, no
    # sys.path mutation.
    cfg = Config()
    generated_root = cfg.sdet.generated_root
    if not generated_root.is_absolute():
        generated_root = Path.cwd() / generated_root
    slug_dir = generated_root / slug
    init_py = slug_dir / "__init__.py"

    if not slug_dir.is_dir() or not init_py.is_file():
        _pytest_exit_operator_tone(
            summary=(
                f"No generated SDET classes found for server {slug!r} "
                f"(from serverInfo.name={server_name!r})."
            ),
            detail=[
                f"  The fixture looked for `{init_py}` and it does not exist.",
                f"  Configured `sdet.generated_root`: {cfg.sdet.generated_root}",
                "  This usually means `gen-sdet-classes` has not been run "
                "for this server, or the server's name changed.",
            ],
            next_step=(
                "run `mcp-test-framework gen-sdet-classes` against this "
                "server first, then re-run with --sdet"
            ),
        )

    # Loader pattern lifted verbatim from tests/framework/unit/
    # test_codegen_integration_mock.py:131-151 (_load_generated_init).
    # The synthetic package prefix avoids sys.modules collisions across
    # repeated pytest invocations within the same process.
    pkg_name = f"_mcptf_sdet_generated_{slug}"
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
                f"Failed to construct module spec for generated SDET "
                f"package at {init_py}."
            ),
            detail=[
                f"  importlib.util.spec_from_file_location returned None for "
                f"`{init_py}`.",
                "  This typically means the file exists but is not a valid "
                "Python source file (e.g. a 0-byte file or non-text content).",
            ],
            next_step=(
                "regenerate the package with `mcp-test-framework gen-sdet-classes`"
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
        # Step 7: restore prior state. Pop registry only if we installed it.
        _tf._ACTIVE_SLUG = prior_slug
        _tf._ACTIVE_CLIENT = prior_client
        _tf._REGISTRIES.pop(slug, None)
