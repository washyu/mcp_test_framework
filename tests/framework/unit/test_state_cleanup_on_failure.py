"""Phase 19: cleanup-on-failure self-test (one of the v1.3 STATE pins).

Pins the pytest-native semantics that a yield-fixture's teardown body
runs even when an intervening consumer test fails. The fixture below
increments a module-global counter on teardown; the consumer test is
marked xfail with the strict flag set so its deliberate failure flips
green in pytest's accounting, and the trailing test asserts the teardown
counter == 1.

Per the phase context decision block (D-06/D-07): one self-test file,
no MCP, no subprocess, no pytester. Subprocess + JUnit-XML assertion
variant rejected -- 50x cost for the same proof, and downstream
runner-rendering breakage is already caught by the renderer plan's
tests.

xfail strict-mode rationale:
  - xfail + test failing as expected -> XFAIL (green-equivalent).
  - xfail + test passing -> XPASS -> FAILS the suite. This is the
    desired regression guard: if pytest ever started letting the
    consumer test pass, we'd want to know immediately.
"""
from __future__ import annotations

import pytest

_teardown_count = 0


@pytest.fixture
def stateful_resource():
    yield "resource"
    global _teardown_count
    _teardown_count += 1


@pytest.mark.xfail(strict=True, reason="deliberate failure to trigger teardown path")
def test_consumer_fails_deliberately(stateful_resource):
    assert False, "intentional failure to trigger teardown path"


def test_teardown_ran_despite_failure():
    # Ordered AFTER the failing test (pytest collects in file order).
    # If teardown did NOT run on failure, this assertion fires and the
    # whole suite goes red -- catching a pytest-semantics regression
    # the moment it lands.
    assert _teardown_count == 1
