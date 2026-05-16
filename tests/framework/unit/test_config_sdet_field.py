"""Phase 21.1 RELOC-01: top-level Config wires `test_code: TestCodeConfig` as required.

(Originally named `sdet: SdetConfig`; Phase 25 RENAME-05 renamed the field and
class as part of the v1.4 sdet -> test_code public-API freeze.)

Pins the integration contract:
  - A valid YAML with test_code.generated_root loads cleanly and exposes Path.
  - A YAML missing the test_code block raises ValidationError with
    type=missing at loc=("test_code",).
  - That ValidationError routes through the existing
    _emit_operator_error_for_validation `missing` branch and produces the
    SAFE-03 operator-tone output (exit code 2).
  - Schema version stays at 2 (additive required field; SAFE-03 message
    is sufficient guidance per CONTEXT.md <deferred>).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from mcp_test_framework.config import Config


def _write_yaml(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return p


def test_valid_config_loads_test_code_field(tmp_path: Path) -> None:
    yaml_path = _write_yaml(tmp_path, {
        "version": 2,
        "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
        "test_code": {"generated_root": str(tmp_path / "_generated")},
    })
    cfg = Config(yaml_file=str(yaml_path))
    assert isinstance(cfg.test_code.generated_root, Path)
    assert cfg.test_code.generated_root == Path(str(tmp_path / "_generated"))


def test_missing_test_code_block_raises_validation_error(tmp_path: Path) -> None:
    yaml_path = _write_yaml(tmp_path, {
        "version": 2,
        "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
        # no test_code key at all
    })
    with pytest.raises(ValidationError) as exc_info:
        Config(yaml_file=str(yaml_path))
    errs = exc_info.value.errors()
    # Phase 25 RENAME-05: field name is `test_code`; missing-field loc reports
    # the canonical field name (the legacy `sdet` is a validation_alias only).
    assert any(
        e["type"] == "missing" and e["loc"] == ("test_code",)
        for e in errs
    ), f"expected `missing` error at loc=('test_code',); got {errs!r}"


def test_missing_test_code_routes_through_safe03_mapper(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """RELOC-01: existing _emit_operator_error_for_validation `missing`
    branch handles the new field automatically with no new code path.

    The mapper raises ``typer.Exit`` (which is ``click.exceptions.Exit``)
    with exit_code=2, mirroring the SAFE-03 fail-loud contract used by
    every other missing-required-field path in cli._emit_operator_error.
    """
    import typer

    from mcp_test_framework.cli import _emit_operator_error_for_validation

    yaml_path = _write_yaml(tmp_path, {
        "version": 2,
        "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
    })
    with pytest.raises(ValidationError) as exc_info:
        Config(yaml_file=str(yaml_path))
    with pytest.raises(typer.Exit) as exit_info:
        _emit_operator_error_for_validation(exc_info.value, source=str(yaml_path))
    assert exit_info.value.exit_code == 2
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "config file is missing a required field" in out
    assert "test_code" in out


def test_version_2_still_accepted(tmp_path: Path) -> None:
    yaml_path = _write_yaml(tmp_path, {
        "version": 2,
        "mcp_server": {"command": "uvx", "args": ["x"], "timeout_seconds": 30},
        "test_code": {"generated_root": str(tmp_path / "_generated")},
    })
    cfg = Config(yaml_file=str(yaml_path))
    assert cfg.version == 2
