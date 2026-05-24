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
    assert "### No config found, framework refuses to run" in text
    assert "no config file found: ./config.yaml" in text
    assert "next: run `mcp-test-framework config-init -o config.yaml`" in text


def test_error_style_contains_safe_06_message() -> None:
    text = ERROR_STYLE.read_text(encoding="utf-8")
    assert "### Config uses an older schema version" in text
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


def test_error_style_safe_04_env_var_branch_is_gone() -> None:
    """Phase 31 SHIM-05 D-05 inversion: the env-var-typo branch in cli.py
    was deleted; the resolver no longer has an MCPTF_CONFIG_FILE arm.

    Replaces the legacy ``test_error_style_safe_04_body_matches_cli_wiring``
    which pinned the deleted error wording.
    """
    cli_text = (
        _repo_root() / "src" / "mcp_test_framework" / "cli.py"
    ).read_text("utf-8")
    assert "config file not found via MCPTF_CONFIG_FILE:" not in cli_text
    assert "the path in MCPTF_CONFIG_FILE does not exist" not in cli_text
    assert "unset MCPTF_CONFIG_FILE" not in cli_text


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


def test_error_style_sdet_rejection_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 31 SHIM-04: a `sdet:`-keyed config triggers the D-02 three-part
    operator-tone rejection message via the
    `_emit_operator_error_for_validation` dispatcher branch added in Task 2.

    Pins the verbatim summary/detail/next_step text from CONTEXT D-02.
    Future drift -- in either cli.py or this test -- breaks the assertion."""
    import typer
    from pydantic import ValidationError

    from mcp_test_framework.cli import _emit_operator_error_for_validation
    from mcp_test_framework.config import Config

    cfg = tmp_path / "sdet.yaml"
    cfg.write_text(
        "version: 2\nsdet:\n  generated_root: out\n",
        encoding="utf-8",
    )
    try:
        Config(yaml_file=str(cfg))
    except ValidationError as exc:
        with pytest.raises(typer.Exit) as exit_info:
            _emit_operator_error_for_validation(exc, source=str(cfg))
        assert exit_info.value.exit_code == 2
        captured = capsys.readouterr()
        text = captured.out + captured.err
        # Verbatim D-02 wording (operator-approved during /gsd-discuss-phase).
        assert "unknown config key: sdet" in text
        assert (
            "the `sdet:` key was renamed to `test_code:` in v1.4 and removed in v1.5."
            in text
        )
        assert "your existing block under `sdet:` ports forward unchanged" in text
        assert "rename the `sdet:` key to `test_code:` in your config.yaml" in text
    else:
        raise AssertionError(
            "Config(yaml_file=...) with sdet: key should have raised ValidationError"
        )


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
