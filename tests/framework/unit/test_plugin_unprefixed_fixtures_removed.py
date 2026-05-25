"""Regression test for the six unprefixed fixture aliases removed in v1.5.

Each parametrized case synthesizes a `def test_x({legacy}): pass` test
inside `pytester`, runs pytest, and asserts the failure surfaces as an
ERROR-at-setup carrying the operator-tone three-part text pointing at
the `mcp_*`-prefixed equivalent. Future text drift breaks this test.
"""
from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]


_ALIAS_PAIRS = [
    ("config", "mcp_config"),
    ("judge", "mcp_judge"),
    ("target_tool", "mcp_target_tool"),
    ("rubric_clarity", "mcp_rubric_clarity"),
    ("rubric_disambiguation", "mcp_rubric_disambiguation"),
    ("rubric_parameters", "mcp_rubric_parameters"),
]


@pytest.mark.parametrize(
    "legacy,prefixed",
    _ALIAS_PAIRS,
    ids=[f"{legacy}->{prefixed}" for legacy, prefixed in _ALIAS_PAIRS],
)
def test_unprefixed_fixture_removed(
    pytester: pytest.Pytester,
    legacy: str,
    prefixed: str,
) -> None:
    """Requesting a legacy unprefixed fixture name resolves to a
    pytest.fail with the prefixed name surfaced in the error."""
    # The plugin auto-loads via the project's pytest11 entry point, so no
    # explicit `-p mcp_test_framework._plugin` is needed (and doing so under
    # the entry-point load triggers a "Plugin already registered" conflict).
    pytester.makefile(
        ".toml",
        pyproject=("[tool.pytest.ini_options]\n"),
    )
    pytester.makepyfile(f"def test_x({legacy}): pass")
    result = pytester.runpytest_subprocess()
    # Fixture-resolution failure surfaces as ERROR (not FAILED).
    result.assert_outcomes(errors=1)
    combined = "\n".join(result.outlines + result.errlines)
    assert f"the `{legacy}` fixture was removed in v1.5" in combined, combined
    assert prefixed in combined, combined
    assert "next:" in combined, combined
