"""Phase 33 plan 01: bucket-name -> contract test function source-of-truth mapping.

Self-tests that pin the TEST_FUNCTION_BUCKETS constant in
mcp_test_framework.contracts._buckets against the actual async def names
in mcp_test_framework.contracts._tests.

If a contract test in _tests.py is renamed, test_every_contract_test_function_belongs_to_exactly_one_bucket
fails immediately on the next CI run, preventing silent bucket drift.
"""
from __future__ import annotations

import inspect

from mcp_test_framework.contracts import _tests
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS, BucketName


def _all_contract_test_names() -> set[str]:
    """Return all callable names starting with 'test_' from contracts._tests."""
    return {
        name
        for name, member in inspect.getmembers(_tests, callable)
        if name.startswith("test_")
    }


def test_every_contract_test_function_belongs_to_exactly_one_bucket() -> None:
    """Every async def test_* in contracts._tests appears in exactly one bucket.

    The union of all frozenset values must exactly equal the set of test
    function names discovered via inspect. A name appearing in zero buckets
    (new test not yet mapped) or two buckets (accidental duplicate) both fail.
    """
    actual_names = _all_contract_test_names()
    bucket_union: set[str] = set()
    for names in TEST_FUNCTION_BUCKETS.values():
        bucket_union |= names

    assert actual_names == bucket_union, (
        f"Mismatch between contracts._tests test functions and TEST_FUNCTION_BUCKETS.\n"
        f"  In _tests but NOT in any bucket: {actual_names - bucket_union!r}\n"
        f"  In a bucket but NOT in _tests:   {bucket_union - actual_names!r}"
    )


def test_buckets_are_disjoint() -> None:
    """No test function name appears in two buckets simultaneously."""
    bucket_names = list(TEST_FUNCTION_BUCKETS.keys())
    for i, name_a in enumerate(bucket_names):
        for name_b in bucket_names[i + 1:]:
            intersection = TEST_FUNCTION_BUCKETS[name_a] & TEST_FUNCTION_BUCKETS[name_b]
            assert intersection == frozenset(), (
                f"Buckets '{name_a}' and '{name_b}' share test function(s): "
                f"{intersection!r}. Each test must belong to exactly one bucket."
            )


def test_bucket_names_are_literal_schema_judge_output() -> None:
    """TEST_FUNCTION_BUCKETS has exactly the three keys: schema, judge, output."""
    assert set(TEST_FUNCTION_BUCKETS.keys()) == {"schema", "judge", "output"}, (
        f"Expected exactly keys {{'schema', 'judge', 'output'}}; "
        f"got {set(TEST_FUNCTION_BUCKETS.keys())!r}"
    )
