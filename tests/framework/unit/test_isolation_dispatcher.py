"""Phase 34-03 dispatcher contract pins for ``_build_subprocess_env``.

Three load-bearing invariants from CONTEXT.md D-05 / D-07 / Open Question 6:

1. ``_build_subprocess_env('passthrough', None)`` returns a literal
   ``dict(os.environ)`` copy -- nothing stripped, nothing injected.
   This is the load-bearing D-05 invariant: operator's mental model is
   "passthrough = what my shell sees."
2. ``_build_subprocess_env('strict', isolated_home)`` is byte-for-byte
   identical to the legacy ``_build_isolated_env(isolated_home)`` --
   regression invariant guarding spawn-site behavior under strict mode.
3. ``_build_subprocess_env('strict', None)`` raises ``AssertionError`` --
   defensive guard per Open Question 6 so caller drift fails fast at
   the spawn-site instead of silently degrading to passthrough.

SEED-022 constraint (memory ``project_framework_primitives_sdet_safety_principle.md``):
``_isolation.py`` does NOT import ``config.py``. The dispatcher takes plain
``Literal[str]`` + ``Path | None`` data; the caller passes the data.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_passthrough_returns_dict_of_os_environ(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: passthrough mode returns ``dict(os.environ)`` verbatim.

    No filter, no allowlist, no keyring backend override. Operator's
    full env reaches the spawned MCP subprocess.
    """
    from mcp_test_framework._isolation import _build_subprocess_env

    monkeypatch.setenv("MCPTF_TEST_PASSTHROUGH_MARKER", "operator-credential")
    monkeypatch.delenv("PYTHON_KEYRING_BACKEND", raising=False)

    env = _build_subprocess_env("passthrough", None)

    # Load-bearing invariant: literal copy of the parent env.
    assert env == dict(os.environ)
    # The operator's seeded marker is reachable.
    assert env.get("MCPTF_TEST_PASSTHROUGH_MARKER") == "operator-credential"
    # No null-keyring override was injected.
    assert env.get("PYTHON_KEYRING_BACKEND") != "keyring.backends.null.Null"


def test_strict_delegates_to_build_isolated_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-07: strict-mode branch is byte-for-byte identical to legacy
    ``_build_isolated_env`` -- regression invariant.

    Any drift between dispatcher's strict branch and the legacy builder
    fails this test, protecting the v1.0-v1.4 always-on-isolation
    behavior under the new opt-in seam.
    """
    from mcp_test_framework._isolation import (
        _build_isolated_env,
        _build_subprocess_env,
    )

    isolated_home = tmp_path / "iso"
    isolated_home.mkdir()
    # Seed a deterministic MCP_* var so the MCP_PREFIX filter path is exercised.
    monkeypatch.setenv("MCP_TEST_VAR", "x")

    legacy = _build_isolated_env(isolated_home)
    new = _build_subprocess_env("strict", isolated_home)

    # Load-bearing invariant: byte-for-byte equivalence.
    assert new == legacy
    # Null keyring override is present (strict-mode hermetic property).
    assert new.get("PYTHON_KEYRING_BACKEND") == "keyring.backends.null.Null"
    # HOME or USERPROFILE redirected to the isolation tempdir (cross-platform).
    assert (
        new.get("HOME") == str(isolated_home)
        or new.get("USERPROFILE") == str(isolated_home)
    )


def test_strict_with_none_isolated_home_raises_assertion_error() -> None:
    """Open Question 6: ``_build_subprocess_env('strict', None)`` raises
    ``AssertionError`` so caller drift fails fast at the spawn-site
    instead of silently degrading to passthrough.
    """
    from mcp_test_framework._isolation import _build_subprocess_env

    with pytest.raises(AssertionError):
        _build_subprocess_env("strict", None)
