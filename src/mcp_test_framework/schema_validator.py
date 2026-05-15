"""Pure-data schema validator for MCP tool schemas.

Implements 7 deterministic structural checks from the MVP spec:

    1. Tool name is non-empty.
    2. Tool description is non-empty.
    3. inputSchema is a dict and is itself a valid JSON Schema document
       (verified via jsonschema.validators.validator_for + check_schema).
    4. inputSchema.type == "object".
    5. Every name in inputSchema.required appears in inputSchema.properties.
    6. Every property has a non-empty description.
    7. Every property declares one of {type, oneOf, anyOf}.

Design rules:
- All issues carry ``severity="error"`` -- there is no "warning" tier in the
  MVP output. The ``Literal["error"]`` typing keeps adding "warning" later
  a typed schema migration.
- ``ValidationIssue.path`` is a JSON-Pointer string (RFC 6901), e.g.
  ``"/inputSchema/properties/foo/description"``. This matches jsonschema's
  ``absolute_path`` representation, NOT JSONPath (``json_path``).
- The empty list is the contract for "structurally valid" -- the contract
  pass asserts ``validate_tool_schema(target_tool) == []``.

This module is pure-data: no I/O, no subprocess, no network. It accepts an
``mcp.types.Tool`` instance (the SDK's pydantic model) and returns a list of
``ValidationIssue`` records.
"""
from __future__ import annotations

from typing import Any, Literal

from jsonschema.validators import Draft202012Validator, validator_for
from mcp.types import Tool
from pydantic import BaseModel


class ValidationIssue(BaseModel):
    """A single structural-validation finding for an MCP tool schema.

    ``severity`` is typed ``Literal["error"]`` (not bare ``str``) so that
    adding a "warning" tier post-MVP becomes a typed schema migration. The
    field has NO default -- callers must construct severity explicitly to
    honor that forward-compat intent.
    """

    severity: Literal["error"]
    path: str
    message: str


def _pointer_from_deque(absolute_path: Any) -> str:
    """Convert jsonschema's absolute_path (a collections.deque) to a JSON Pointer.

    Per RFC 6901, components are joined by "/" with a leading "/", and the
    escape sequences "~0" (for "~") and "~1" (for "/") are applied to each
    component. Returns the empty string for an empty deque (root pointer).

    NOTE: ``validate_tool_schema`` does not currently use this helper
    because the 7 structural checks are hand-coded (not
    ``iter_errors``-driven), so the paths are constructed inline with
    literal f-strings. This helper is retained as the canonical way to
    convert jsonschema's path output -- if a future check switches to
    ``iter_errors``, it can use this helper directly without re-deriving
    the RFC 6901 escaping.
    """
    if not absolute_path:
        return ""
    parts = [str(p).replace("~", "~0").replace("/", "~1") for p in absolute_path]
    return "/" + "/".join(parts)


def validate_tool_schema(tool: Tool) -> list[ValidationIssue]:
    """Run the 7 deterministic structural checks against an MCP tool.

    Returns an empty list iff the tool's schema is structurally valid.
    Never raises on a malformed tool -- malformed schemas surface as
    ``ValidationIssue`` entries.

    The contract pass asserts ``validate_tool_schema(target_tool) == []``.
    """
    issues: list[ValidationIssue] = []

    # Check 1: Tool name is non-empty.
    if not getattr(tool, "name", None):
        issues.append(
            ValidationIssue(
                severity="error",
                path="/name",
                message="Tool name is empty",
            )
        )

    # Check 2: Tool description is non-empty.
    if not getattr(tool, "description", None):
        issues.append(
            ValidationIssue(
                severity="error",
                path="/description",
                message="Tool description is empty",
            )
        )

    schema: Any = getattr(tool, "inputSchema", None)

    # Check 3a: inputSchema is a dict.
    if not isinstance(schema, dict):
        issues.append(
            ValidationIssue(
                severity="error",
                path="/inputSchema",
                message="inputSchema is missing or not a JSON object",
            )
        )
        # Cannot continue without a schema dict -- short-circuit.
        return issues

    # Check 3b: inputSchema is itself a valid JSON Schema document.
    # validator_for auto-detects the draft via $schema; falls back to
    # Draft202012Validator (the MCP-native dialect) when $schema is absent.
    # Draft202012Validator is the FALLBACK default, NOT a hardcoded choice
    # -- validator_for is what actually runs.
    validator_cls = validator_for(schema, default=Draft202012Validator)
    try:
        validator_cls.check_schema(schema)
    except Exception as exc:  # noqa: BLE001 -- jsonschema raises SchemaError but be defensive
        issues.append(
            ValidationIssue(
                severity="error",
                path="/inputSchema",
                message=f"inputSchema is not a valid JSON Schema: {exc}",
            )
        )
        # Cannot continue without a valid schema -- short-circuit.
        return issues

    # Check 4: inputSchema.type == "object".
    schema_type = schema.get("type")
    if schema_type != "object":
        issues.append(
            ValidationIssue(
                severity="error",
                path="/inputSchema/type",
                message=f'inputSchema.type must be "object" (got {schema_type!r})',
            )
        )

    # Check 5: required ⊆ properties.
    required = schema.get("required", []) or []
    properties = schema.get("properties", {}) or {}
    for name in required:
        if name not in properties:
            issues.append(
                ValidationIssue(
                    severity="error",
                    path=f"/inputSchema/required/{name}",
                    message=(
                        f'Required field "{name}" is not declared in properties'
                    ),
                )
            )

    # Checks 6 + 7: per-property description AND (type | oneOf | anyOf).
    # Both checks emit errors, not warnings. The full-sweep and focused-
    # diagnostic tests intentionally overlap on these checks -- do NOT
    # deduplicate or weaken them.
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            issues.append(
                ValidationIssue(
                    severity="error",
                    path=f"/inputSchema/properties/{prop_name}",
                    message=(
                        f'Property "{prop_name}" schema must be an object'
                    ),
                )
            )
            continue

        # Check 6: every property has a non-empty description.
        if not prop_schema.get("description"):
            issues.append(
                ValidationIssue(
                    severity="error",
                    path=f"/inputSchema/properties/{prop_name}/description",
                    message=(
                        f'Property "{prop_name}" is missing a description'
                    ),
                )
            )

        # Check 7: every property declares one of {type, oneOf, anyOf}.
        if not any(k in prop_schema for k in ("type", "oneOf", "anyOf")):
            issues.append(
                ValidationIssue(
                    severity="error",
                    path=f"/inputSchema/properties/{prop_name}",
                    message=(
                        f'Property "{prop_name}" has no type / oneOf / anyOf'
                    ),
                )
            )

    return issues
