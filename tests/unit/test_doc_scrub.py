"""Wave-0 banned-token regression guard for Phase 12 CLEAN-01 + PERSONA-01 + CLEAN-04.

Asserts the four user-facing files (README, config.example.yaml, .env.example,
docs/EXTENDING.md) carry zero spec IDs / phase IDs / quick-task IDs / file:line
refs after Phase 12. Asserts the PERSONA-01 framing section exists in README and
EXTENDING. Asserts CLEAN-04's "link to BOTH" contract.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
README = ROOT / "README.md"
EXTENDING = ROOT / "docs" / "EXTENDING.md"
CFG_EXAMPLE = ROOT / "config.example.yaml"
DOTENV = ROOT / ".env.example"


BASE_BANNED = [
    r"\bPhase \d",
    r"\bPlan \d-\d",
    r"\bTOOLCFG-\d",
    r"\bISOL-\d",
    r"\bOUTPUT-\d",
    r"\bD-\d{2}",
    r"\b\d{6}-[a-z0-9]{3}",
]


def _scan(text: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if re.search(p, text)]


def test_readme_exists_and_no_banned_tokens() -> None:
    assert README.is_file()
    text = README.read_text(encoding="utf-8")
    patterns = BASE_BANNED + [r"src/[\w/.]+\.py:\d+"]
    bad = _scan(text, patterns)
    assert not bad, f"banned tokens in README.md: {bad}"


def test_extending_exists_and_no_banned_tokens() -> None:
    assert EXTENDING.is_file()
    text = EXTENDING.read_text(encoding="utf-8")
    patterns = BASE_BANNED + [
        r"\bDOC-\d",
        r"_isolation\.py:\d+",
        r"06-VERIFICATION",
        r"MILESTONE-AUDIT",
    ]
    bad = _scan(text, patterns)
    assert not bad, f"banned tokens in docs/EXTENDING.md: {bad}"


def test_config_example_no_banned_tokens() -> None:
    text = CFG_EXAMPLE.read_text(encoding="utf-8")
    bad = _scan(text, BASE_BANNED + [r"\bCD-\d"])
    assert not bad, f"banned tokens in config.example.yaml: {bad}"


def test_dotenv_example_no_banned_tokens() -> None:
    text = DOTENV.read_text(encoding="utf-8")
    bad = _scan(text, BASE_BANNED)
    assert not bad, f"banned tokens in .env.example: {bad}"


def test_readme_has_persona_heading_once() -> None:
    text = README.read_text(encoding="utf-8")
    assert text.count("## Testing an MCP server you didn't write") == 1


def test_extending_has_persona_heading_once() -> None:
    text = EXTENDING.read_text(encoding="utf-8")
    assert text.count("## Testing an MCP server you didn't write") == 1


def test_readme_links_both_example_files() -> None:
    text = README.read_text(encoding="utf-8")
    assert "config.example.yaml" in text
    assert "examples/homelab-mcp.yaml" in text


def test_readme_no_target_tool_name() -> None:
    """D-03: TARGET_TOOL_NAME env var is leaving in Phase 13; do not advertise."""
    text = README.read_text(encoding="utf-8")
    assert "TARGET_TOOL_NAME" not in text


def test_readme_persona_section_has_locked_phrase() -> None:
    """Pitfall 5: the locked persona-framing sentence must be verbatim."""
    text = README.read_text(encoding="utf-8")
    assert "treats your MCP server as a black box" in text


def test_readme_persona_section_has_no_marketing_words() -> None:
    """Pitfall 5: anti-marketing tone in operator-facing prose."""
    text = README.read_text(encoding="utf-8")
    # Extract the persona section: from heading to next H2 (or EOF)
    m = re.search(
        r"## Testing an MCP server you didn't write\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    assert m, "persona section not found"
    section = m.group(1)
    for word in ("powerful", "seamless", "empowers", "leverage", "cutting-edge"):
        assert word.lower() not in section.lower(), f"marketing word in persona section: {word!r}"
