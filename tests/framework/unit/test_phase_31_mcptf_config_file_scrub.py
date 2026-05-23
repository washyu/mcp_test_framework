"""Phase 31 SHIM-05 scrub regression guards.

Locks the post-Phase-31 invariant: ``MCPTF_CONFIG_FILE`` is mentioned in
``src/mcp_test_framework/`` EXACTLY ONCE -- inside the grandfathered
detection block in ``_plugin.py:pytest_configure``. Every other
operator-facing mention (``fixtures.py`` error hints, ``models.py`` docstring,
``.env.example``, ``examples/homelab-mcp.yaml`` header) is scrubbed.

These tests fail-loud the moment any future contributor reintroduces a
mention -- the env var is deliberately INVISIBLE on the operator-facing
surface from v1.5 onward.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()


@pytest.mark.parametrize(
    "rel_path",
    [
        "src/mcp_test_framework/fixtures.py",
        "src/mcp_test_framework/models.py",
        "examples/homelab-mcp.yaml",
    ],
)
def test_no_mcptf_config_file_mention(rel_path: str) -> None:
    """The Task 3 scrub set must contain ZERO mentions."""
    text = (REPO / rel_path).read_text(encoding="utf-8")
    assert "MCPTF_CONFIG_FILE" not in text, (
        f"{rel_path} still references MCPTF_CONFIG_FILE; Phase 31 "
        f"SHIM-05 Task 3 scrub regression."
    )


def test_plugin_is_sole_remaining_mention_in_src() -> None:
    """Lock: ``src/mcp_test_framework/_plugin.py`` is the ONLY file under
    ``src/mcp_test_framework/`` that may mention MCPTF_CONFIG_FILE
    (grandfathered detection block; EOL Phase 35 SHIM-09 / v1.6)."""
    src_root = REPO / "src" / "mcp_test_framework"
    offenders = []
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "_plugin.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        if "MCPTF_CONFIG_FILE" in text:
            offenders.append(str(py_file.relative_to(REPO)))
    assert offenders == [], (
        f"unexpected MCPTF_CONFIG_FILE mentions outside _plugin.py: "
        f"{offenders}; only the grandfathered detection block in "
        f"_plugin.py:pytest_configure is allowed in src/ as of Phase 31."
    )


def test_homelab_example_header_points_at_canonical_routes() -> None:
    """The examples/homelab-mcp.yaml header must point at the two
    surviving routes (``--config`` and the ``mcp_config_file`` ini key)
    instead of the deprecated env var."""
    text = (REPO / "examples" / "homelab-mcp.yaml").read_text(encoding="utf-8")
    # The header should now reference at least one canonical route.
    assert "--config" in text or "mcp_config_file" in text, (
        "examples/homelab-mcp.yaml header must point at one of the two "
        "canonical routes (`--config` or `[tool.pytest.ini_options] "
        "mcp_config_file`)."
    )


def test_fixtures_operator_hints_still_reference_canonical_routes() -> None:
    """The Task 3 scrub does not silently delete operator guidance --
    fixtures.py's preflight error hints must still cite at least one of
    the two canonical routes (``--config`` or ``mcp_config_file`` ini)."""
    text = (REPO / "src" / "mcp_test_framework" / "fixtures.py").read_text(encoding="utf-8")
    assert "mcp_config_file" in text or "--config" in text, (
        "fixtures.py operator-tone hints lost their guidance pointer; "
        "the scrub must REPLACE MCPTF_CONFIG_FILE with the canonical "
        "two-route guidance, not delete it."
    )
