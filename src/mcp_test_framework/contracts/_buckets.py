"""Source-of-truth mapping from test bucket name to contract test functions.

Single explicit constant rather than @pytest.mark.bucket decorators or
name-prefix regex so:
  - Phase 33 collection-time filter (plan 33-03) iterates this dict.
  - Phase 33 --explain renderer (plan 33-04) iterates this dict.
  - Phase 35 zero-shim capstone can grep-assert one constant.
  - Renaming a contract test in _tests.py also requires a paired edit
    here -- caught immediately by tests/framework/test_bucket_map.py.
"""
from __future__ import annotations

from typing import Literal

BucketName = Literal["schema", "judge", "output"]

TEST_FUNCTION_BUCKETS: dict[BucketName, frozenset[str]] = {
    "schema": frozenset({
        "test_target_tool_exists",
        "test_schema_passes_structural_checks",
        "test_description_min_length",
        "test_every_parameter_has_description_and_type",
    }),
    "judge": frozenset({
        "test_description_clarity",
        "test_description_disambiguation",
        "test_parameters_self_explanatory",
    }),
    "output": frozenset({
        "test_empty_args_call_returns_non_error",
        "test_result_has_content_or_structured",
        "test_text_content_parses_as_json",
    }),
}

__all__ = ["BucketName", "TEST_FUNCTION_BUCKETS"]
