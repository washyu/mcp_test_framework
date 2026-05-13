"""Regression test for `_session_needs_preflight` live-MCP scope predicate.

Pins the Option B allowlist behavior fixed in quick-task 260513-chh:
preflight fires iff at least one collected item lives under a live-MCP
scope (`tests/contract/` or `tests/sdet/`); everything else
(`tests/framework/...`, legacy `tests/unit/`) must NOT trigger the
preflight gate, so a developer with no `homelab-mcp` / Ollama on the
machine can run framework-only suites cleanly.

Pre-fix bug (Phase 15 reorg fallout, surfaced repeatedly in Phase 18):
the predicate keyed on `tests/unit/`, a prefix that does not exist in
the current layout. The check therefore always returned True and forced
operators to either set `MCPTF_CONFIG_FILE` or pass `--noconftest`.

These tests use `types.SimpleNamespace` fakes for `request.session.items`
so they import the predicate directly with no pytest fixture
infrastructure — pure-data unit test, safe under the autouse preflight
gate (the gate itself is what's under test).
"""
from __future__ import annotations

from types import SimpleNamespace

from mcp_test_framework.fixtures import _session_needs_preflight


def _fake_request(*nodeids: str) -> SimpleNamespace:
    """Build a stub `pytest.FixtureRequest` exposing only `.session.items[*].nodeid`."""
    items = [SimpleNamespace(nodeid=n) for n in nodeids]
    return SimpleNamespace(session=SimpleNamespace(items=items))


def test_empty_items_returns_false():
    """No collected items -> nothing to preflight for."""
    assert _session_needs_preflight(_fake_request()) is False


def test_only_framework_unit_items_returns_false():
    """Pre-fix this returned True (the regression). Framework unit tests
    are pure-data and must not be gated by the autouse preflight."""
    assert (
        _session_needs_preflight(
            _fake_request(
                "tests/framework/unit/test_foo.py::test_x",
                "tests/framework/unit/test_bar.py::test_y",
            )
        )
        is False
    )


def test_only_framework_smoke_items_returns_false():
    """Framework smoke tests don't touch live MCP either."""
    assert (
        _session_needs_preflight(
            _fake_request("tests/framework/smoke/test_foo.py::test_x")
        )
        is False
    )


def test_only_framework_runner_items_returns_false():
    """tests/framework/test_runner_renderer.py and friends are self-tests."""
    assert (
        _session_needs_preflight(
            _fake_request("tests/framework/test_runner_renderer.py::test_x")
        )
        is False
    )


def test_one_contract_item_returns_true():
    """tests/contract/ items hit the live homelab-mcp + Ollama stack."""
    assert (
        _session_needs_preflight(
            _fake_request("tests/contract/test_homelab.py::test_y")
        )
        is True
    )


def test_one_sdet_item_returns_true():
    """tests/sdet/ items hit the live homelab-mcp + Ollama stack (Phase 18)."""
    assert (
        _session_needs_preflight(
            _fake_request("tests/sdet/test_scenario.py::test_z")
        )
        is True
    )


def test_mixed_unit_plus_contract_returns_true():
    """Live scope wins — any contract item in the collection arms preflight."""
    assert (
        _session_needs_preflight(
            _fake_request(
                "tests/framework/unit/test_foo.py::test_x",
                "tests/framework/unit/test_bar.py::test_y",
                "tests/contract/test_homelab.py::test_live",
            )
        )
        is True
    )


def test_mixed_unit_plus_sdet_returns_true():
    """Live scope wins — any sdet item in the collection arms preflight."""
    assert (
        _session_needs_preflight(
            _fake_request(
                "tests/framework/unit/test_foo.py::test_x",
                "tests/sdet/test_scenario.py::test_live",
            )
        )
        is True
    )


def test_legacy_tests_unit_prefix_is_not_live_scope():
    """Defensive: the pre-Phase-15 `tests/unit/` prefix is retired, NOT
    silently re-honored as a live scope. If someone ever recreates that
    directory it should default to "not live" (the safe behavior for a
    pure-data unit-test path) rather than re-arming preflight."""
    assert (
        _session_needs_preflight(
            _fake_request("tests/unit/test_old.py::test_x")
        )
        is False
    )
