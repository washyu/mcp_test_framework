"""Pin `mcp_session` fixture's stash-lookup-with-fallback for host_isolation.

These tests pin Phase 34 ISOL-05 Plan 34-06 Task 2:

  - The fixture signature gains ``request: pytest.FixtureRequest`` as the
    FIRST positional parameter.
  - The body reads the resolved Config from
    ``request.session.config._mcp_contracts_config`` (the same stash
    populated by ``_plugin.pytest_configure`` for CLI + library modes).
  - The bare ``Config()`` fallback is preserved for the framework-self-test
    path (``test_sdet_fixtures.py``'s ``_install_session_config``
    monkeypatch shim depends on this).

Pattern mirrors ``src/mcp_test_framework/fixtures.py:108-111`` -- the
canonical stash-lookup-with-fallback seam established in Phase 27 /
Phase 31.
"""
from __future__ import annotations

import inspect
import re
from types import SimpleNamespace


def test_mcp_session_signature_takes_request_as_first_param() -> None:
    """The fixture signature must start with ``request: pytest.FixtureRequest``.

    This is the wiring contract for the stash-lookup path: without
    ``request``, the fixture body cannot reach
    ``request.session.config._mcp_contracts_config``.
    """
    from mcp_test_framework.test_code.session import mcp_session

    get_wrapped = getattr(mcp_session, "_get_wrapped_function", None)
    func = get_wrapped() if get_wrapped is not None else mcp_session
    sig = inspect.signature(func)
    params = list(sig.parameters)
    assert params, "mcp_session must take at least one parameter"
    assert params[0] == "request", (
        f"mcp_session must take `request` as the first parameter; "
        f"got params: {params}"
    )
    assert "mcp_client" in params, (
        f"mcp_session must still depend on mcp_client; got params: {params}"
    )


def test_mcp_session_module_source_routes_through_stash() -> None:
    """The fixture body must read from the
    ``_mcp_contracts_config`` stash with an explicit-construction fallback.

    Mirrors ``fixtures.py:108-111``. Source-text pin avoids the
    integration-test cost of spinning up a real session while still
    catching drift (e.g. somebody dropping the fallback line and
    breaking the framework-self-test path).

    Phase 34-09 update: the stash-miss fallback was changed from bare
    ``Config()`` (which raises ValidationError) to explicit
    ``Config(test_code=TestCodeConfig(...))`` construction.
    """
    import inspect as _inspect

    from mcp_test_framework.test_code import session as session_mod

    src = _inspect.getsource(session_mod)
    # The stash-lookup line must be present verbatim (matches fixtures.py:108-111).
    assert re.search(
        r'getattr\(\s*request\.session\.config,\s*"_mcp_contracts_config",\s*None\s*\)',
        src,
    ), (
        "mcp_session must route through the `_mcp_contracts_config` stash "
        "(canonical pattern from fixtures.py:108-111). Stash-lookup line missing."
    )
    # The stash-miss fallback line must use explicit construction (Phase 34-09):
    # bare Config() raises ValidationError (test_code is REQUIRED with no default),
    # so the fallback must use Config(test_code=TestCodeConfig(...)).
    assert re.search(r"cfg\s*=\s*Config\(\s*test_code\s*=\s*TestCodeConfig\(", src), (
        "mcp_session stash-miss fallback must use explicit Config(test_code=TestCodeConfig(...)) "
        "construction (Phase 34-09): bare Config() raises ValidationError because test_code "
        "is a REQUIRED field with no default."
    )


def test_mcp_session_stash_hit_uses_stashed_config_not_bare() -> None:
    """When the stash is populated, the fixture must use the stashed Config.

    This is the operator-real path: ``_plugin.pytest_configure`` stashed
    the resolved Config under ``_mcp_contracts_config``; the fixture
    body must consume it rather than re-constructing a bare ``Config()``
    (which would bypass the operator's YAML ``host_isolation`` field).

    The test runs the fixture against a fake request whose
    ``session.config._mcp_contracts_config`` carries a sentinel
    ``test_code.generated_root``; if the fixture honors the stash, the
    spec loader will look in that directory.
    """
    import asyncio
    import pytest
    from pathlib import Path
    from unittest.mock import MagicMock

    from mcp_test_framework.test_code.session import mcp_session

    get_wrapped = getattr(mcp_session, "_get_wrapped_function", None)
    func = get_wrapped() if get_wrapped is not None else mcp_session

    # Build a fake Config-shaped object exposing the field the fixture reads.
    sentinel_root = Path("__nonexistent_stash_sentinel__")
    stashed_cfg = SimpleNamespace(
        test_code=SimpleNamespace(generated_root=sentinel_root),
    )
    fake_session_config = SimpleNamespace(_mcp_contracts_config=stashed_cfg)
    fake_session = SimpleNamespace(config=fake_session_config)
    fake_request = SimpleNamespace(session=fake_session)

    fake_client = MagicMock()
    fake_client.server_info = SimpleNamespace(name="stash-sentinel-server")

    async def _drive() -> None:
        agen = func(fake_request, fake_client)
        # The fixture should fail at the slug_dir check with a path
        # rooted in the sentinel directory -- proves it read from the stash.
        with pytest.raises(pytest.exit.Exception) as exc_info:
            await agen.__anext__()
        message = str(exc_info.value)
        assert "__nonexistent_stash_sentinel__" in message, (
            "fixture did not route through the stash; the failure path "
            "does not mention the sentinel generated_root from the stashed "
            f"Config. Message: {message!r}"
        )

    asyncio.run(_drive())
