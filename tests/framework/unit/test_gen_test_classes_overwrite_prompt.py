"""Unit tests for the non-empty-dir overwrite prompt on gen-test-classes.

Behavior decision tree:
    target dir missing            -> return silently (caller creates)
    target dir empty              -> return silently
    target dir non-empty in TTY   -> typer.confirm prompt; decline aborts exit 2
    target dir non-empty non-TTY  -> operator-tone error exit 2 (no --yes flag)

Strongest "never silently destroy data" posture: the framework does not
expose a --yes / --force escape hatch; operators in CI clean the directory
manually and re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from mcp_test_framework.cli import _confirm_or_abort_non_empty_target, app


def test_missing_target_dir_returns_silently(tmp_path: Path) -> None:
    target = tmp_path / "does_not_exist"
    # Must not raise. Must not touch typer.confirm or sys.stdin.
    assert _confirm_or_abort_non_empty_target(target) is None


def test_empty_target_dir_returns_silently(tmp_path: Path) -> None:
    target = tmp_path / "empty"
    target.mkdir()
    assert _confirm_or_abort_non_empty_target(target) is None


def test_non_empty_dir_in_tty_accept_returns_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch(
        "mcp_test_framework.cli.typer.confirm", return_value=True
    ) as mock_confirm:
        assert _confirm_or_abort_non_empty_target(target) is None
    assert mock_confirm.call_count == 1


def test_non_empty_dir_in_tty_decline_aborts_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("mcp_test_framework.cli.typer.confirm", return_value=False):
        with pytest.raises(typer.Exit) as exc_info:
            _confirm_or_abort_non_empty_target(target)
    assert exc_info.value.exit_code == 2


def test_non_empty_dir_in_non_tty_aborts_with_exit_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    (target / "a.py").write_text("# placeholder", encoding="utf-8")
    (target / "b.py").write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(typer.Exit) as exc_info:
        _confirm_or_abort_non_empty_target(target)
    assert exc_info.value.exit_code == 2
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    # Names the non-interactive / non-empty condition:
    assert "non-interactive" in combined or "non-empty" in combined
    # Names the target path:
    assert str(target) in combined
    # Does NOT advertise a --yes / --force flag (no escape hatch):
    assert "--yes" not in combined
    assert "--force" not in combined


def test_file_count_appears_in_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "populated"
    target.mkdir()
    for i in range(3):
        (target / f"f{i}.py").write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch(
        "mcp_test_framework.cli.typer.confirm", return_value=True
    ) as mock_confirm:
        _confirm_or_abort_non_empty_target(target)
    call_args = mock_confirm.call_args
    prompt_text = (
        call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
    )
    assert "3" in prompt_text  # file count appears
    assert str(target) in prompt_text  # target path appears


def test_gen_test_classes_command_has_no_yes_or_force_flag() -> None:
    """Regression guard: no --yes / --force ever sneaks back into the command."""
    runner = CliRunner()
    result = runner.invoke(app, ["gen-test-classes", "--help"])
    assert result.exit_code == 0
    assert "--yes" not in result.stdout
    assert "--force" not in result.stdout
