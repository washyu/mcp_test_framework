"""Wave-0 banned-token + reference-message scaffold for Phase 12 PERSONA-03.

Phase 13 reads SAFE-03 and SAFE-06 reference messages from docs/ERROR-STYLE.md
verbatim. This test guarantees they never drift.
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


ERROR_STYLE = _repo_root() / "docs" / "ERROR-STYLE.md"


def test_error_style_md_exists() -> None:
    assert ERROR_STYLE.is_file(), f"missing {ERROR_STYLE}"


def test_error_style_contains_safe_03_message() -> None:
    text = ERROR_STYLE.read_text(encoding="utf-8")
    assert "### SAFE-03 — no config found, framework refuses to run" in text
    assert "no config file found: ./config.yaml" in text
    assert "next: run `mcp-test-framework config-init -o config.yaml`" in text


def test_error_style_contains_safe_06_message() -> None:
    text = ERROR_STYLE.read_text(encoding="utf-8")
    assert "### SAFE-06 — config uses an older schema version" in text
    assert "config file uses an older format:" in text
    assert "schema version 2 (opt-in" in text
    assert "docs/MIGRATION-v1-to-v2.md" in text


def test_error_style_safe_03_body_matches_cli_wiring() -> None:
    """Phase 13 SAFE-03: cli.py's no-config branch must echo the LOCKED
    SAFE-03 body verbatim. Pins the source text so the wording cannot
    drift away from docs/ERROR-STYLE.md:46-55."""
    cli_text = (
        _repo_root() / "src" / "mcp_test_framework" / "cli.py"
    ).read_text("utf-8")
    # Substrings copied verbatim from docs/ERROR-STYLE.md:46-55.
    assert "no config file found: ./config.yaml" in cli_text
    assert "the framework refuses to run without a config file because it would" in cli_text
    assert "otherwise call every tool the server advertises -- including any" in cli_text
    assert "destructive ones. you must explicitly opt in to which tools run." in cli_text
    assert "run `mcp-test-framework config-init -o config.yaml` to generate" in cli_text
    assert "a starter config, then edit it to enable the tools you want to test" in cli_text


def test_error_style_safe_04_body_matches_cli_wiring() -> None:
    """Phase 13 SAFE-04 (env-var branch): cli.py's MCPTF_CONFIG_FILE-typo
    branch lead and detail must match the locked shape verbatim. The
    SAFE-04 surface is not pre-locked in ERROR-STYLE.md (it's the
    parallel-of-SAFE-04-as-defined-for-the-flag-typo), so we pin the
    wording the plan committed to."""
    cli_text = (
        _repo_root() / "src" / "mcp_test_framework" / "cli.py"
    ).read_text("utf-8")
    assert "config file not found via MCPTF_CONFIG_FILE:" in cli_text
    assert "the path in MCPTF_CONFIG_FILE does not exist or is not a file." in cli_text
    assert "check the path or unset MCPTF_CONFIG_FILE and run" in cli_text


def test_error_style_safe_06_body_matches_cli_wiring() -> None:
    """Phase 13 D-08: cli.py's version-mismatch branch must echo the LOCKED
    SAFE-06 body. This test reads cli.py source and pins the verbatim
    substrings so the wording cannot drift away from docs/ERROR-STYLE.md."""
    cli_text = (
        _repo_root() / "src" / "mcp_test_framework" / "cli.py"
    ).read_text("utf-8")
    # These substrings come from docs/ERROR-STYLE.md:57-73 verbatim.
    assert "schema version 2 (opt-in" in cli_text
    assert "your config is version 1 (opt-out)" in cli_text
    assert "in v1 a tool with no entry runs by default, in v2 it skips" in cli_text
    assert "docs/MIGRATION-v1-to-v2.md" in cli_text
    assert "config-init -o config.yaml.new" in cli_text


def test_error_style_no_banned_tokens_outside_checklist() -> None:
    """Operator-facing prose has no spec IDs / phase IDs / file:line refs.

    The "## Banned strings" section is exempt -- it documents the patterns.
    """
    text = ERROR_STYLE.read_text(encoding="utf-8")
    # Split off the Banned strings section (everything from that heading onward).
    parts = text.split("## Banned strings", 1)
    body = parts[0]  # everything BEFORE the banned-strings checklist

    banned = [
        (r"\bPhase \d", "Phase N reference"),
        (r"\bPlan \d-\d", "Plan N-N reference"),
        (r"\bTOOLCFG-\d", "TOOLCFG- spec ID"),
        (r"\bISOL-\d", "ISOL- spec ID"),
        (r"\bOUTPUT-\d", "OUTPUT- spec ID"),
        (r"\d{6}-[a-z0-9]{3}", "quick-task ID"),
    ]
    found: list[str] = []
    for pattern, label in banned:
        for m in re.finditer(pattern, body):
            found.append(f"{label}: {m.group(0)!r} at offset {m.start()}")
    assert not found, "banned tokens in operator-facing prose:\n" + "\n".join(found)
