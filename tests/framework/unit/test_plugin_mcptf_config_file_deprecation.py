"""Phase 31 SHIM-05 D-06/D-07/D-08/D-09 regression guards.

Locks the post-Phase-31 deprecation surface for ``MCPTF_CONFIG_FILE``:

- D-06: the surviving DeprecationWarning emitted from
  ``_plugin.pytest_configure`` carries the operator-tone "no longer
  honored as of v1.5" wording (verbatim).
- D-07: ``_plugin.pytest_configure`` is the SOLE emission site (the
  legacy emission inside ``settings_customise_sources`` is gone).
- D-08: the warning is rendered with a ``[mcp-contracts]`` prefix via a
  scoped ``warnings.formatwarning`` override that is restored via
  ``try/finally`` before ``pytest_configure`` returns.
- D-09: a grandfathering marker comment cites Phase 35 SHIM-09 / v1.6 so
  the EOL planner can find the detection site.

These tests are pure synchronous tests -- no asyncio markers.
"""
from __future__ import annotations

import types
import warnings
from pathlib import Path

import pytest

from mcp_test_framework import _plugin


def _make_fake_config() -> types.SimpleNamespace:
    """Minimal pytest.Config stand-in that satisfies ``pytest_configure``.

    ``pytest_configure`` exercises ``getini``, ``getoption``,
    ``addinivalue_line``, ``rootpath``, and ``pluginmanager``; provide
    no-ops + an empty string for the ``mcp_config_file`` ini key so the
    function short-circuits after the DeprecationWarning block.
    """
    return types.SimpleNamespace(
        getini=lambda k: "",
        getoption=lambda *a, **k: None,
        addinivalue_line=lambda *a, **k: None,
        rootpath=Path.cwd(),
        pluginmanager=types.SimpleNamespace(
            register=lambda *a, **k: None,
            hasplugin=lambda *a, **k: False,
        ),
    )


def test_mcptf_config_file_env_emits_one_d06_deprecation_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-06 + D-07: env var set -> exactly one DeprecationWarning with the
    verbatim "no longer honored as of v1.5" wording."""
    monkeypatch.setenv("MCPTF_CONFIG_FILE", "/tmp/whatever.yaml")
    fake_config = _make_fake_config()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            _plugin.pytest_configure(fake_config)
        except Exception:
            # Plugin may raise (e.g. on subsequent ini reads), but we only
            # care that the warning fired BEFORE any raise.
            pass
    deprecation = [
        w for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "no longer honored as of v1.5" in str(w.message)
    ]
    assert len(deprecation) == 1, (
        f"expected exactly one D-06 DeprecationWarning, got "
        f"{len(deprecation)}; all captured warnings: "
        f"{[str(w.message) for w in caught]}"
    )
    msg = str(deprecation[0].message)
    # Spot-check the actionable next steps are present.
    assert "mcp_config_file" in msg
    assert "--config" in msg


def test_no_env_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the env var is NOT set, no DeprecationWarning fires."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    fake_config = _make_fake_config()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            _plugin.pytest_configure(fake_config)
        except Exception:
            pass
    relevant = [
        w for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "MCPTF_CONFIG_FILE" in str(w.message)
    ]
    assert relevant == []


def test_formatwarning_is_restored_after_pytest_configure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08: the ``warnings.formatwarning`` override is scoped to the
    single ``warnings.warn`` call window via ``try/finally``. After
    ``pytest_configure`` returns, the stdlib formatter is active."""
    monkeypatch.setenv("MCPTF_CONFIG_FILE", "/tmp/whatever.yaml")
    original_fw = warnings.formatwarning
    fake_config = _make_fake_config()
    try:
        _plugin.pytest_configure(fake_config)
    except Exception:
        pass
    assert warnings.formatwarning is original_fw, (
        "formatwarning override leaked beyond pytest_configure scope; "
        "the try/finally restore is missing or broken"
    )


def test_d06_wording_present_in_source() -> None:
    """D-06 source-side lock: the verbatim phrase lives in _plugin.py.

    Catches a future refactor that accidentally reverts the wording to
    the v1.4 "deprecated since v1.4" copy.
    """
    plugin_src = Path(_plugin.__file__).read_text(encoding="utf-8")
    assert "no longer honored as of v1.5" in plugin_src
    # And the v1.4 wording is gone.
    assert "is deprecated since v1.4 and will be" not in plugin_src or (
        # The fixture-deprecation warnings also use "deprecated since v1.4";
        # the env-var deprecation must NOT use that phrasing in combination
        # with "MCPTF_CONFIG_FILE" anymore.
        "MCPTF_CONFIG_FILE env var is deprecated since v1.4" not in plugin_src
    )


def test_d09_grandfathering_marker_present_in_source() -> None:
    """D-09 source-side lock: a Phase-35 / v1.6 marker comment lives near
    the detection site so the future EOL planner can find it."""
    plugin_src = Path(_plugin.__file__).read_text(encoding="utf-8")
    assert "Phase 35 SHIM-09" in plugin_src or "v1.6" in plugin_src, (
        "grandfathering marker for the MCPTF_CONFIG_FILE detection EOL "
        "is missing from _plugin.py; Phase 35 SHIM-09 author needs it"
    )


def test_formatwarning_renders_with_mcp_contracts_prefix() -> None:
    """D-08 rendering lock: the override produces a [mcp-contracts]-
    prefixed render block, not pytest's default
    ``<file>:<line>: DeprecationWarning: <msg>`` shape.

    Exercises the override directly via a one-shot warn under the scoped
    override; does not depend on pytest's own captured output.
    """
    import os
    os.environ["MCPTF_CONFIG_FILE"] = "/tmp/whatever.yaml"
    try:
        # We capture stderr-side rendering by calling formatwarning manually
        # under the same conditions pytest_configure uses. Use the public
        # warnings module to invoke whichever formatter is currently active.
        from mcp_test_framework import _plugin as plugin_module

        fake_config = _make_fake_config()
        original_fw = warnings.formatwarning
        captured_render: list[str] = []

        # Swap in a stub original that records what gets called inside the
        # override window. We rely on the scoped override calling the
        # configured prefixer; we sniff the prefix via formatwarning side
        # effects in a wrapper.
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            # Snapshot before/after to make sure the override installed a
            # different formatter while running.
            installed_fw_holder: list = []

            real_warn = warnings.warn

            def _spy_warn(message, category=UserWarning, stacklevel=1, source=None):
                # While inside _plugin.pytest_configure's warn call window,
                # warnings.formatwarning should be the scoped override.
                installed_fw_holder.append(warnings.formatwarning)
                return real_warn(message, category=category, stacklevel=stacklevel + 1, source=source)

            warnings.warn = _spy_warn  # type: ignore[assignment]
            try:
                plugin_module.pytest_configure(fake_config)
            except Exception:
                pass
            finally:
                warnings.warn = real_warn  # type: ignore[assignment]

        assert installed_fw_holder, "plugin did not call warnings.warn"
        scoped_fw = installed_fw_holder[0]
        assert scoped_fw is not original_fw, (
            "expected a scoped formatwarning override during warn; got the "
            "stdlib default"
        )
        # Invoke the scoped formatter directly to confirm the [mcp-contracts]
        # prefix appears in its render output.
        rendered = scoped_fw(
            "MCPTF_CONFIG_FILE is set in your environment but no longer "
            "honored as of v1.5; configure via `[tool.pytest.ini_options] "
            "mcp_config_file = PATH` in pyproject.toml or pass `--config "
            "PATH` to `mcp-contracts run`.",
            DeprecationWarning,
            "<test>",
            1,
            None,
        )
        captured_render.append(rendered)
        assert "[mcp-contracts]" in rendered, (
            f"scoped formatwarning did not include the [mcp-contracts] "
            f"prefix; rendered: {rendered!r}"
        )
        # And it should NOT carry the default <file>:<line>: shape.
        assert "<test>:1:" not in rendered, (
            f"scoped formatwarning still uses pytest/stdlib default shape; "
            f"rendered: {rendered!r}"
        )
    finally:
        os.environ.pop("MCPTF_CONFIG_FILE", None)
