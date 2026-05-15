"""Regression for SAFE-07: docs/MIGRATION-v1-to-v2.md exists and pins the
load-bearing wording. Parallels tests/unit/test_error_style.py.

The locked operator-error message at src/mcp_test_framework/cli.py references
this doc by exact path. If the doc disappears or the load-bearing substrings
drift, the SAFE-06 UX breaks.
"""
from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


MIGRATION_DOC = _repo_root() / "docs" / "MIGRATION-v1-to-v2.md"


def test_migration_doc_exists() -> None:
    assert MIGRATION_DOC.is_file(), f"missing {MIGRATION_DOC}"


def test_migration_doc_pins_v2_keywords() -> None:
    text = MIGRATION_DOC.read_text(encoding="utf-8")
    assert "version: 2" in text
    assert "config-init -o config.yaml.new" in text
    assert "opt every tool in" in text
    assert "target:" in text  # deletion instruction
    assert "not selected in config" in text  # SAFE-01 reason string
    assert ".env" in text  # the dotenv coda


def test_migration_doc_uses_ascii_dashes_not_emdash() -> None:
    """Match ERROR-STYLE.md tone: two hyphens, not U+2014."""
    text = MIGRATION_DOC.read_text(encoding="utf-8")
    assert "—" not in text, (
        "em-dash detected; use `--` to match ERROR-STYLE.md"
    )


def test_migration_doc_does_not_leak_planning_ids() -> None:
    """Operator-facing doc: same banned tokens as ERROR-STYLE.md."""
    text = MIGRATION_DOC.read_text(encoding="utf-8")
    banned_patterns = [
        r"\bPhase \d",
        r"\bPlan \d-\d",
        r"\b[A-Z]{2,}-\d{2}\b",  # spec IDs like SAFE-01, TOOLCFG-01
        r"\b\d{6}-[a-z0-9]{3}\b",  # quick-task IDs
        r"\bsrc/.*\.py:\d+",
    ]
    for pat in banned_patterns:
        assert re.search(pat, text) is None, (
            f"migration doc leaks planning-artifact pattern {pat!r}; "
            f"see docs/ERROR-STYLE.md banned-tokens checklist"
        )
