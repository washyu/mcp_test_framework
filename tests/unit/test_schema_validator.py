"""Unit tests for mcp_test_framework.schema_validator.

Twelve tests:
  - 1 baseline:                  test_clean_tool_returns_empty_list
  - 7 per-check:                 test_check_1..test_check_7_oneof_or_anyof_satisfies_type_check
  - 2 cross-cutting invariants:  test_all_issues_have_severity_error,
                                 test_all_issue_paths_use_json_pointer

The cross-cutting tests guard:
  D-01: every issue's severity is "error" -- no "warning" tier in MVP output
  RESEARCH Pitfall 2: paths are JSON-Pointer style ("/inputSchema/...") and
    NOT JSONPath ("$.inputSchema..."). The regression test enforces this by
    asserting every non-empty path starts with "/" and contains neither "$"
    nor JSONPath dot-separators inside the body.

All tests are synchronous -- no @pytest.mark.asyncio. Tools constructed via
mcp.types.Tool(name=..., description=..., inputSchema=...).
"""
from __future__ import annotations

from mcp.types import Tool

from mcp_test_framework.schema_validator import (
    ValidationIssue,
    validate_tool_schema,
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _clean_tool() -> Tool:
    """A fully valid tool: passes all 7 structural checks."""
    return Tool(
        name="my_tool",
        description="A clean tool with a non-empty description.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )


def _everything_broken_tool() -> Tool:
    """A tool that violates every one of the 7 structural checks.

    - Check 1: empty name
    - Check 2: empty description
    - Check 3: inputSchema is a dict but contains a meta-schema-invalid type
      (we deliberately keep schema as a dict so the dict short-circuit does
      not fire; see test_check_3_invalid_input_schema_not_dict for the
      "not a dict" path). Below we use a dict with valid meta-schema so the
      remaining checks (4..7) run -- the spec's "broken every way" tool
      must surface 4..7 too. We separately test the meta-schema path with
      test_check_3_invalid_meta_schema. So this synthetic tool exercises
      checks 1, 2, 4, 5, 6, 7.

    For check 3 specifically we ALSO build a separate "everything-including-
    meta-schema" tool below and combine the two issue lists in the
    cross-cutting tests.
    """
    return Tool(
        name="",
        description="",
        inputSchema={
            "type": "string",  # check 4: not "object"
            "properties": {
                "foo": {},  # check 6 + check 7 violators
            },
            "required": ["b"],  # check 5: "b" not in properties
        },
    )


# --------------------------------------------------------------------------
# 1. Baseline: clean tool returns empty list
# --------------------------------------------------------------------------

def test_clean_tool_returns_empty_list() -> None:
    """A fully valid tool produces no issues -- the contract Phase 4 TEST-02
    will assert via validate_tool_schema(target_tool) == []."""
    assert validate_tool_schema(_clean_tool()) == []


# --------------------------------------------------------------------------
# 2. Per-check tests (one per spec check)
# --------------------------------------------------------------------------

def test_check_1_empty_name() -> None:
    tool = Tool(
        name="",
        description="ok",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )
    issues = validate_tool_schema(tool)
    matched = [i for i in issues if i.path == "/name"]
    assert matched, f"Expected an issue at /name, got {[i.path for i in issues]}"
    assert "empty" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_2_empty_description() -> None:
    tool = Tool(
        name="ok",
        description="",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )
    issues = validate_tool_schema(tool)
    matched = [i for i in issues if i.path == "/description"]
    assert matched, f"Expected an issue at /description, got {[i.path for i in issues]}"
    assert "empty" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_3_invalid_input_schema_not_dict() -> None:
    """inputSchema=None: the validator must short-circuit with /inputSchema."""
    # mcp.types.Tool requires inputSchema to be a dict per pydantic, so we
    # build the Tool with a placeholder dict and then mutate via model_copy
    # to exercise the "not a dict" branch. Pydantic won't let us set
    # inputSchema=None directly without bypassing validation.
    valid = Tool(
        name="ok",
        description="ok",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )
    # model_construct skips validation, allowing us to inject a non-dict
    # value to test the validator's defensive branch.
    broken = Tool.model_construct(
        name=valid.name,
        description=valid.description,
        inputSchema=None,  # type: ignore[arg-type]
    )
    issues = validate_tool_schema(broken)
    matched = [i for i in issues if i.path == "/inputSchema"]
    assert matched, f"Expected an issue at /inputSchema, got {[i.path for i in issues]}"
    assert "missing or not a json object" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_3_invalid_meta_schema() -> None:
    """inputSchema is a dict but is not a valid JSON Schema document.

    type=12345 (an integer) violates the JSON Schema meta-schema, which
    requires `type` to be a string or array of strings. validator_for +
    check_schema must catch this without the validator raising.
    """
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={"type": 12345},  # type: ignore[dict-item]
    )
    issues = validate_tool_schema(tool)
    matched = [i for i in issues if i.path == "/inputSchema"]
    assert matched, f"Expected an issue at /inputSchema, got {[i.path for i in issues]}"
    assert "not a valid json schema" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_4_type_not_object() -> None:
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={"type": "string"},  # valid JSON Schema, but wrong root type for MCP
    )
    issues = validate_tool_schema(tool)
    matched = [i for i in issues if i.path == "/inputSchema/type"]
    assert matched, f"Expected an issue at /inputSchema/type, got {[i.path for i in issues]}"
    assert "object" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_5_required_not_in_properties() -> None:
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "x"},
            },
            "required": ["b"],  # "b" not in properties
        },
    )
    issues = validate_tool_schema(tool)
    matched = [i for i in issues if i.path == "/inputSchema/required/b"]
    assert matched, (
        f"Expected an issue at /inputSchema/required/b, got {[i.path for i in issues]}"
    )
    assert "not declared in properties" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_6_property_missing_description() -> None:
    """D-04: missing description is an ERROR, not a warning."""
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={
            "type": "object",
            "properties": {
                "foo": {"type": "string"},  # no description
            },
        },
    )
    issues = validate_tool_schema(tool)
    matched = [
        i for i in issues if i.path == "/inputSchema/properties/foo/description"
    ]
    assert matched, (
        f"Expected /inputSchema/properties/foo/description issue, got "
        f"{[i.path for i in issues]}"
    )
    assert "missing a description" in matched[0].message.lower()
    assert matched[0].severity == "error"


def test_check_7_property_missing_type_oneof_anyof() -> None:
    """D-04: missing type/oneOf/anyOf is an ERROR, not a warning."""
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={
            "type": "object",
            "properties": {
                "foo": {"description": "x"},  # no type/oneOf/anyOf
            },
        },
    )
    issues = validate_tool_schema(tool)
    matched = [
        i
        for i in issues
        if i.path == "/inputSchema/properties/foo"
        and "type / oneof / anyof" in i.message.lower()
    ]
    assert matched, (
        f"Expected /inputSchema/properties/foo issue mentioning type/oneOf/anyOf, "
        f"got {[(i.path, i.message) for i in issues]}"
    )
    assert matched[0].severity == "error"


def test_check_7_oneof_or_anyof_satisfies_type_check() -> None:
    """A property with oneOf (and no `type`) is valid -- the disjunction is
    type | oneOf | anyOf, not just `type`."""
    tool = Tool(
        name="ok",
        description="ok",
        inputSchema={
            "type": "object",
            "properties": {
                "foo": {
                    "description": "either string or int",
                    "oneOf": [{"type": "string"}, {"type": "integer"}],
                },
            },
        },
    )
    issues = validate_tool_schema(tool)
    # No type-related issue should fire for this property.
    type_issues_for_foo = [
        i
        for i in issues
        if i.path == "/inputSchema/properties/foo"
        and "type / oneof / anyof" in i.message.lower()
    ]
    assert not type_issues_for_foo, (
        f"oneOf should satisfy the type-disjunction check, but got {type_issues_for_foo}"
    )
    # And in fact the whole tool is valid.
    assert issues == []


# --------------------------------------------------------------------------
# 3. Cross-cutting invariants
# --------------------------------------------------------------------------

def _multi_issue_tool() -> Tool:
    """Construct a tool that triggers ALL 7 checks at once.

    Strategy:
      - name="" -> check 1
      - description="" -> check 2
      - inputSchema is a dict (so check 3a passes), but type=12345 -> check 3b
        meta-schema fails AND short-circuits.

    Because check 3 short-circuits, a single "everything broken" tool can't
    surface all 7 simultaneously. So for the cross-cutting tests we build
    TWO tools and concatenate their issue lists:
      - Tool A: triggers checks 1, 2, 4, 5, 6, 7 (valid meta-schema, broken
        structure)
      - Tool B: triggers check 3b only (meta-schema invalid)
    The union covers all 7 checks.
    """
    raise NotImplementedError  # not used directly -- see helpers below


def _issues_covering_all_seven_checks() -> list[ValidationIssue]:
    """Returns the union of issues from two synthetic tools that together
    exercise all 7 checks. Used by the cross-cutting tests."""
    tool_a = _everything_broken_tool()
    tool_b = Tool(
        name="ok",
        description="ok",
        inputSchema={"type": 12345},  # type: ignore[dict-item]
    )
    return validate_tool_schema(tool_a) + validate_tool_schema(tool_b)


def test_all_issues_have_severity_error() -> None:
    """D-01 regression: every issue is severity='error' -- no 'warning' tier."""
    issues = _issues_covering_all_seven_checks()
    assert issues, "Expected multiple issues across both broken tools"
    bad = [i for i in issues if i.severity != "error"]
    assert not bad, f"Found non-error issues: {[(i.severity, i.path) for i in bad]}"
    # Belt-and-suspenders: equality with the literal string.
    assert all(i.severity == "error" for i in issues)


def test_all_issue_paths_use_json_pointer() -> None:
    """RESEARCH Pitfall 2 regression: paths are JSON-Pointer, not JSONPath.

    JSON-Pointer:  /inputSchema/properties/foo/description  (slash-separated, leading /)
    JSONPath:      $.inputSchema.properties.foo.description (dot-separated, $ root)

    For every issue with a non-empty path:
      - must start with "/"
      - must NOT contain "$" (JSONPath root marker)
      - must NOT contain ".properties." or similar JSONPath dot-separators
    """
    issues = _issues_covering_all_seven_checks()
    assert issues, "Expected multiple issues across both broken tools"
    for issue in issues:
        if not issue.path:
            continue  # empty path = root pointer, allowed
        assert issue.path.startswith("/"), (
            f"Path must start with '/' (JSON-Pointer): {issue.path!r}"
        )
        assert "$" not in issue.path, (
            f"Path must not contain '$' (JSONPath marker): {issue.path!r}"
        )
        # JSONPath uses .properties., .required., etc. JSON-Pointer uses
        # /properties/, /required/. Either separator alone is not a smoking
        # gun (a property literally named "foo.bar" could appear in a path),
        # but ".properties." (the JSONPath idiom for the properties node)
        # never appears in a correctly-built JSON-Pointer because the
        # validator emits "/properties/" instead.
        assert ".properties." not in issue.path, (
            f"Path looks like JSONPath '.properties.' rather than JSON-Pointer "
            f"'/properties/': {issue.path!r}"
        )
        assert ".required." not in issue.path, (
            f"Path looks like JSONPath '.required.' rather than JSON-Pointer "
            f"'/required/': {issue.path!r}"
        )
