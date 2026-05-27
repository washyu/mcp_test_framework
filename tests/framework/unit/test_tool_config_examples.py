"""Unit tests for ToolConfig.examples field validation (GEN-01).

Pins (Phase 999.2):
  - default value is None (no change for configs without examples:)
  - list-of-dicts shape accepted
  - top-level mapping rejected (must be list)
  - non-dict item rejected with operator-tone message naming index
  - D-01b: load-time validation is shape-only; keys NOT checked against
    inputSchema (runtime concern of <ToolName>Params(**example))
  - D-04: examples and skip_buckets are independent; NO cross-field
    validator linking them (SEED-022 -- operator decides pairing)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.models import ToolConfig


def test_examples_default_is_none() -> None:
    assert ToolConfig().examples is None


def test_examples_accepts_list_of_dicts() -> None:
    cfg = ToolConfig(examples=[{"vmid": 9001}, {"vmid": 9002, "name": "vm-min"}])
    assert cfg.examples is not None
    assert len(cfg.examples) == 2


def test_examples_rejects_non_list_top_level() -> None:
    with pytest.raises(ValidationError):
        ToolConfig(examples={"vmid": 9001})


def test_examples_rejects_non_dict_item() -> None:
    with pytest.raises(ValidationError) as ei:
        ToolConfig(examples=[{"ok": 1}, 42])
    # operator-tone message naming the offending index (D-01b)
    assert "examples[1]" in str(ei.value)


def test_examples_does_not_validate_keys_against_inputschema() -> None:
    """D-01b: load-time validation is shape-only.

    A key not in any tool's inputSchema.required validates successfully
    at config load; the runtime <ToolName>Params(**example) construction
    inside the generated scenario is what surfaces missing required keys
    as a Pydantic ValidationError test failure.
    """
    cfg = ToolConfig(examples=[{"unknown_key_not_in_required": "anything"}])
    assert cfg.examples == [{"unknown_key_not_in_required": "anything"}]


def test_examples_compatible_with_skip_buckets() -> None:
    """D-04: no cross-field validator linking examples and skip_buckets.

    SEED-022: framework does no tool-safety reasoning. The recommended
    pairing (examples: + skip_buckets: ['output']) is documented in
    README + docs/LIBRARY-MODE.md but NOT enforced by a cross-field validator.
    """
    cfg = ToolConfig(examples=[{"vmid": 9001}], skip_buckets=["output"])
    assert cfg.examples == [{"vmid": 9001}]
    assert cfg.skip_buckets == ["output"]
