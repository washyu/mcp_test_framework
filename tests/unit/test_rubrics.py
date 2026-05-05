"""Unit tests for src/mcp_test_framework/rubrics.py.

Locks the hardening invariants that downstream Plans 02 and 03 depend on:
  - <<<SUBJECT>>> / <<<END SUBJECT>>> marker contract with ollama_judge.py
  - Anti-verbosity preamble present (Pitfall 6)
  - Score-of-5 caution present (Pitfall 6)
  - Frozen behavior (Phase 1 ConfigDict(frozen=True) discipline)
  - __str__ section order (hardening -> dimension -> anchors)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_test_framework.rubrics import (
    ClarityRubric,
    DisambiguationRubric,
    ParametersRubric,
    Rubric,
)


def test_subject_markers_present_in_clarity_rubric() -> None:
    s = str(ClarityRubric())
    assert "<<<SUBJECT>>>" in s, "marker contract with ollama_judge.py:90 broken"
    assert "<<<END SUBJECT>>>" in s, "marker contract with ollama_judge.py:91 broken"


def test_anti_verbosity_clause_present() -> None:
    s = str(DisambiguationRubric())
    assert "Anti-verbosity" in s, "Pitfall 6 anti-verbosity hardening missing"


def test_score_of_5_caution_present() -> None:
    s = str(ParametersRubric())
    assert "default to 4" in s, "Pitfall 6 score-of-5 caution missing from anchor template"


def test_str_section_order() -> None:
    """hardening preamble -> DIMENSION block -> score anchors (CONTEXT D-discretion)."""
    s = str(ClarityRubric())
    i_hardening = s.index("Anti-verbosity")
    i_dimension = s.index("DIMENSION:")
    i_anchors = s.index("Score 1-5")
    assert i_hardening < i_dimension < i_anchors, (
        f"section order broken: hardening={i_hardening} dim={i_dimension} anchors={i_anchors}"
    )


def test_rubric_is_frozen() -> None:
    r = ClarityRubric()
    with pytest.raises(ValidationError):
        r.dimension = "mutated"  # type: ignore[misc]


def test_subclass_dimension_defaults() -> None:
    assert ClarityRubric().dimension == "clarity"
    assert DisambiguationRubric().dimension == "disambiguation"
    assert ParametersRubric().dimension == "parameters_self_explanatory"


def test_subclass_dimension_criteria_non_empty() -> None:
    assert len(ClarityRubric().dimension_criteria) > 0
    assert len(DisambiguationRubric().dimension_criteria) > 0
    assert len(ParametersRubric().dimension_criteria) > 0


def test_base_rubric_requires_dimension_and_criteria() -> None:
    """Bare Rubric() requires both fields -- locks the contract for new subclasses."""
    with pytest.raises(ValidationError):
        Rubric()  # type: ignore[call-arg]


def test_double_newline_section_separator() -> None:
    """CONTEXT D-discretion: sections joined by double-newline."""
    s = str(ClarityRubric())
    # The hardening preamble ends, then \n\n, then 'DIMENSION:'.
    assert "\n\nDIMENSION:" in s, "expected double-newline before DIMENSION block"
