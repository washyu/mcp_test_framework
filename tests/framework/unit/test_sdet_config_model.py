"""Unit tests for TestCodeConfig Pydantic sub-model (Phase 21.1 RELOC-01).

Pins the contract that downstream plans (consumer wiring, test rework,
deletion) build on:

  - generated_root is REQUIRED (no default; missing => SAFE-03)
  - empty-string is explicitly rejected (field validator, distinct error)
  - extra="forbid" catches typos
  - frozen model (no mutation after construction)
  - NOT env-routable (no validation_alias on the field)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_test_framework.models import TestCodeConfig


def test_constructs_with_required_path() -> None:
    cfg = TestCodeConfig(generated_root=Path("tests/sdet/_generated"))
    assert cfg.generated_root == Path("tests/sdet/_generated")
    assert isinstance(cfg.generated_root, Path)


def test_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TestCodeConfig()  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    assert any(
        e["type"] == "missing" and e["loc"] == ("generated_root",) for e in errors
    ), f"expected missing-required error at loc=('generated_root',); got {errors!r}"


def test_empty_string_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TestCodeConfig(generated_root="")  # type: ignore[arg-type]
    msg = str(exc_info.value)
    assert "must not be an empty string" in msg


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        TestCodeConfig(generated_root=Path("x"), unknown_extra="boom")  # type: ignore[call-arg]


def test_frozen() -> None:
    cfg = TestCodeConfig(generated_root=Path("x"))
    with pytest.raises(ValidationError):
        cfg.generated_root = Path("/other")  # type: ignore[misc]


def test_not_env_routable() -> None:
    """RELOC-01 D-02: no AliasChoices => not reachable from env var routing."""
    field = TestCodeConfig.model_fields["generated_root"]
    assert field.validation_alias is None
