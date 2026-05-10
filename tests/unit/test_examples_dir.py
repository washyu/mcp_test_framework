"""Wave-0 scaffold for Phase 12 CLEAN-03.

Plan 01 creates examples/README.md; Plan 03 creates examples/homelab-mcp.yaml
via `git mv`. This test asserts both surface for operator browsing.
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


EXAMPLES_DIR = _repo_root() / "examples"


def test_examples_readme_exists() -> None:
    readme = EXAMPLES_DIR / "README.md"
    assert readme.is_file(), f"missing {readme}"


def test_examples_readme_links_to_homelab_mcp_yaml() -> None:
    readme = (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")
    assert "homelab-mcp.yaml" in readme
    assert "## Naming convention" in readme


def test_examples_readme_no_spec_ids() -> None:
    """examples/README.md is operator-facing -- no planning artefacts."""
    import re
    body = (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")
    banned = [r"\bPhase \d", r"\bPlan \d-\d", r"\bTOOLCFG-\d", r"\bD-\d{2}"]
    for p in banned:
        assert not re.search(p, body), f"banned pattern {p!r} in examples/README.md"


@pytest.mark.skipif(
    not (EXAMPLES_DIR / "homelab-mcp.yaml").is_file(),
    reason="Plan 03 lands examples/homelab-mcp.yaml; until then this skips.",
)
def test_examples_homelab_mcp_yaml_exists() -> None:
    """Asserts Plan 03's git-mv landed. Skips until the move happens."""
    yaml_file = EXAMPLES_DIR / "homelab-mcp.yaml"
    assert yaml_file.is_file()
    assert yaml_file.stat().st_size > 100, "yaml looks empty/truncated"


@pytest.mark.skipif(
    not (EXAMPLES_DIR / "homelab-mcp.yaml").is_file(),
    reason="examples/homelab-mcp.yaml absent; nothing to scrub.",
)
def test_homelab_mcp_yaml_no_banned_tokens() -> None:
    """Operator-facing example must carry zero spec/phase/quick-task IDs."""
    import re
    text = (EXAMPLES_DIR / "homelab-mcp.yaml").read_text(encoding="utf-8")
    banned = [
        r"\bPhase \d", r"\bPlan \d-\d", r"\bTOOLCFG-\d", r"\bISOL-\d",
        r"\bOUTPUT-\d", r"\bCD-\d", r"\bD-\d{2}",
        r"\b\d{6}-[a-z0-9]{3}", r"\bSEED-\d", r"\bTEST-\d",
    ]
    for p in banned:
        assert not re.search(p, text), (
            f"banned pattern {p!r} in examples/homelab-mcp.yaml"
        )


@pytest.mark.skipif(
    not (EXAMPLES_DIR / "homelab-mcp.yaml").is_file(),
    reason="examples/homelab-mcp.yaml absent; nothing to inspect.",
)
def test_homelab_mcp_yaml_no_target_block() -> None:
    """The deprecated `target:` block must not appear in the worked reference."""
    import yaml
    data = yaml.safe_load(
        (EXAMPLES_DIR / "homelab-mcp.yaml").read_text(encoding="utf-8")
    )
    assert "target" not in data, (
        "examples/homelab-mcp.yaml must not advertise the leaving target: block"
    )
