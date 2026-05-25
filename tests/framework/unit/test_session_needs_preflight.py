"""Regression test for `_session_needs_preflight` live-MCP scope predicate.

Phase 27 hybridizes the predicate from a pure nodeid-prefix check to
a marker-OR-prefix check, then drops the transitional `tests/contract/`
prefix in Plan 27-05 once the legacy on-disk collection wiring is
deleted:

  - PRIMARY: items carrying `pytest.mark.mcp_contract` (applied by
    the plugin's `pytest_collection_modifyitems` to every
    framework-injected contract test, including the synthetic
    `<mcp-contracts>::test_*` nodeids that no path-prefix could match).
  - SECONDARY: items whose nodeid starts with `tests/test_code/` —
    test-code-author scenarios that do NOT carry the contract marker
    but still drive a live MCP session. The legacy `tests/sdet/`
    prefix was dropped from the predicate in v1.5; operators see the
    SHIM-06 warn-on-presence detector from `pytest_collection`
    instead.

Pre-flip behavior pinned the path-prefix-only check fixed in
quick-task 260513-chh. The marker branch covers the plugin's
synthetic-nodeid contract tests; the path-prefix branch covers
test-code-author paths only.

These tests use `types.SimpleNamespace` fakes for `request.session.items`
so they import the predicate directly with no pytest fixture
infrastructure — pure-data unit test, safe under the autouse preflight
gate (the gate itself is what's under test).
"""
from __future__ import annotations

from types import SimpleNamespace

from mcp_test_framework.fixtures import _session_needs_preflight


def _fake_item(nodeid: str, *, markers: tuple[str, ...] = ()) -> SimpleNamespace:
    """Stub pytest Item with `.nodeid` and `.iter_markers(name)`.

    `iter_markers(name)` returns a list-of-1-truthy iff `name` is in
    `markers`; the predicate uses `any(item.iter_markers("mcp_contract"))`
    which is True when at least one Mark is returned.
    """
    def iter_markers(name: str):
        if name in markers:
            return [object()]
        return []
    return SimpleNamespace(nodeid=nodeid, iter_markers=iter_markers)


def _fake_request(*items: SimpleNamespace) -> SimpleNamespace:
    """Build a stub `pytest.FixtureRequest` from prebuilt fake items."""
    return SimpleNamespace(session=SimpleNamespace(items=list(items)))


def _fake_request_nodeids(*nodeids: str) -> SimpleNamespace:
    """Build a stub request from raw nodeids (no markers)."""
    return _fake_request(*(_fake_item(n) for n in nodeids))


def test_empty_items_returns_false():
    """No collected items -> nothing to preflight for."""
    assert _session_needs_preflight(_fake_request()) is False


def test_only_framework_unit_items_returns_false():
    """Pre-fix this returned True (the regression). Framework unit tests
    are pure-data and must not be gated by the autouse preflight."""
    assert (
        _session_needs_preflight(
            _fake_request_nodeids(
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
            _fake_request_nodeids("tests/framework/smoke/test_foo.py::test_x")
        )
        is False
    )


def test_only_framework_runner_items_returns_false():
    """tests/framework/test_runner_renderer.py and friends are self-tests."""
    assert (
        _session_needs_preflight(
            _fake_request_nodeids("tests/framework/test_runner_renderer.py::test_x")
        )
        is False
    )


def test_legacy_tests_contract_prefix_is_not_live_scope():
    """Plan 27-05: the transitional `tests/contract/` prefix is removed
    from `_LIVE_PREFIXES`. Any item under that path now relies on the
    `mcp_contract` marker branch (which the plugin auto-applies to every
    injected contract test); a bare nodeid with no marker MUST NOT arm
    preflight, otherwise the path-prefix would silently re-introduce the
    transitional behavior."""
    assert (
        _session_needs_preflight(
            _fake_request_nodeids("tests/contract/test_homelab.py::test_y")
        )
        is False
    )


def test_legacy_tests_sdet_path_no_longer_arms_preflight():
    """tests/sdet/ was dropped from _LIVE_PREFIXES in v1.5; a stale legacy
    nodeid no longer arms preflight. Operators see the SHIM-06 warn-on-
    presence detector from pytest_collection instead."""
    assert (
        _session_needs_preflight(
            _fake_request_nodeids("tests/sdet/test_scenario.py::test_z")
        )
        is False
    )


def test_mixed_unit_plus_marked_contract_returns_true():
    """Live scope wins — any item carrying the `mcp_contract` marker
    arms preflight, even when path-prefix items don't match (the
    transitional `tests/contract/` entry was dropped in Plan 27-05; the
    marker is the load-bearing channel for contract tests now)."""
    assert (
        _session_needs_preflight(
            _fake_request(
                _fake_item("tests/framework/unit/test_foo.py::test_x"),
                _fake_item("tests/framework/unit/test_bar.py::test_y"),
                _fake_item(
                    "<mcp-contracts>::test_schema[alpha]",
                    markers=("mcp_contract",),
                ),
            )
        )
        is True
    )


def test_mixed_unit_plus_test_code_returns_true():
    """Live scope wins — any tests/test_code/ item in the collection arms
    preflight (legacy tests/sdet/ no longer participates in the live
    detection set as of v1.5)."""
    assert (
        _session_needs_preflight(
            _fake_request_nodeids(
                "tests/framework/unit/test_foo.py::test_x",
                "tests/test_code/test_scenario.py::test_live",
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
            _fake_request_nodeids("tests/unit/test_old.py::test_x")
        )
        is False
    )


# ---------------------------------------------------------------------------
# Phase 27: marker-branch coverage.
# ---------------------------------------------------------------------------


def test_marker_armed_synthetic_nodeid_returns_true():
    """The plugin's framework-injected contract tests render under the
    synthetic `<mcp-contracts>::test_*` nodeid which no path-prefix could
    match. The `mcp_contract` marker is the load-bearing detection
    channel."""
    item = _fake_item(
        "<mcp-contracts>::test_schema[list_registered_servers]",
        markers=("mcp_contract",),
    )
    assert _session_needs_preflight(_fake_request(item)) is True


def test_marker_armed_off_path_item_returns_true():
    """A marker on any item arms the gate -- nodeid prefix is irrelevant
    to the marker branch."""
    item = _fake_item(
        "tests/framework/unit/test_foo.py::test_x",
        markers=("mcp_contract",),
    )
    assert _session_needs_preflight(_fake_request(item)) is True


def test_unrelated_marker_does_not_arm_gate():
    """Only `mcp_contract` arms the marker branch. An unrelated marker on
    a pure-data item must NOT trigger preflight."""
    item = _fake_item(
        "tests/framework/unit/test_foo.py::test_x",
        markers=("slow",),
    )
    assert _session_needs_preflight(_fake_request(item)) is False


def test_mixed_marker_plus_framework_returns_true():
    """One marker item alongside framework-only items still arms preflight."""
    request = _fake_request(
        _fake_item("tests/framework/unit/test_foo.py::test_x"),
        _fake_item(
            "<mcp-contracts>::test_schema[alpha]",
            markers=("mcp_contract",),
        ),
    )
    assert _session_needs_preflight(request) is True
