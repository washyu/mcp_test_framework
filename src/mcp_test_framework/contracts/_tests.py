"""Parametrized MCP contract test bodies.

Extracted from the framework's own contract suite per Phase 27. This
module is NOT discovered via filesystem walk -- the framework's pytest
plugin (`mcp_test_framework._plugin`) injects it at collection time
when `[tool.pytest.ini_options] mcp_config_file` is set in the
operator's pyproject.toml.

The plugin synthesizes a `_ContractsModule` collector whose `path`
points at this file (so pytest-asyncio sees `pytestmark` normally) but
whose `nodeid` is overridden to render as
`<mcp-contracts>::test_<name>[<tool>]` per Phase 27.

Test bodies preserve v1.3 assertion semantics verbatim. Fixtures use
the v1.4 `mcp_*` prefixed surface (Phase 26 fixture-prefix convention);
`tool_config` stays unprefixed by design.

Test surface (10 tests across 3 categories):

  Category 1 -- deterministic schema:
    test_target_tool_exists
    test_schema_passes_structural_checks
    test_description_min_length
    test_every_parameter_has_description_and_type
  Category 2 -- LLM-judged (score >= 4):
    test_description_clarity
    test_description_disambiguation
    test_parameters_self_explanatory
  Category 3 -- deterministic output conformance:
    test_empty_args_call_returns_non_error
    test_result_has_content_or_structured
    test_text_content_parses_as_json
"""
from __future__ import annotations

import json

import pytest
from jsonschema.validators import Draft202012Validator

from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import ToolConfig
from mcp_test_framework.schema_validator import validate_tool_schema

# UNMARKED contract tests; the session-scoped autouse preflight fixture is
# the gate that fails fast if Ollama or the MCP server is unreachable.
# loop_scope="session" required so fixtures + tests share the session loop
# (asyncio_default_fixture_loop_scope = "session" in pyproject.toml).
pytestmark = [pytest.mark.asyncio(loop_scope="session")]


# ===========================================================================
# Category 1 -- deterministic schema
# ===========================================================================


async def test_target_tool_exists(mcp_target_tool, tool_config: ToolConfig) -> None:
    """Configured target tool is present in the server tool list.

    Defense in depth: preflight + the target_tool fixture already raised
    ToolNotFoundError if the tool was missing; reaching this body means
    the fixture resolved. The explicit assertion gives a diagnostic name
    to the test in pytest output.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    assert mcp_target_tool.name, f"target_tool.name is empty: {mcp_target_tool!r}"


async def test_schema_passes_structural_checks(mcp_target_tool, tool_config: ToolConfig) -> None:
    """validate_tool_schema returns no errors for the target tool."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    issues = validate_tool_schema(mcp_target_tool)
    assert issues == [], f"schema issues found: {issues!r}"


async def test_description_min_length(mcp_target_tool, tool_config: ToolConfig) -> None:
    """Description is non-empty and >= 20 chars."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    desc = mcp_target_tool.description or ""
    assert len(desc) >= 20, (
        f"description too short ({len(desc)} chars): {desc!r}"
    )


async def test_every_parameter_has_description_and_type(
    mcp_target_tool, tool_config: ToolConfig
) -> None:
    """Every input parameter has a description AND a type/oneOf/anyOf."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    schema = mcp_target_tool.inputSchema or {}
    properties = schema.get("properties") or {}
    for prop_name, prop_schema in properties.items():
        assert prop_schema.get("description"), (
            f"param {prop_name!r} missing description in inputSchema"
        )
        assert any(k in prop_schema for k in ("type", "oneOf", "anyOf")), (
            f"param {prop_name!r} missing type/oneOf/anyOf in inputSchema"
        )


# ===========================================================================
# Category 2 -- LLM-judged (score >= 4 per spec)
# ===========================================================================


async def test_description_clarity(
    mcp_judge: Judge,
    mcp_target_tool,
    mcp_rubric_clarity,
    tool_config: ToolConfig,
) -> None:
    """Clarity score >= 4 against tool description.

    Subject = description; context carries tool_name + inputSchema.
    Skips when `tool_config.skip` is set or when `clarity` is not in
    the configured `judges` subset.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    if tool_config.judges is not None and "clarity" not in tool_config.judges:
        pytest.skip(
            reason=f"judge 'clarity' not selected for tool {mcp_target_tool.name!r}"
        )
    result = await mcp_judge.judge(
        str(mcp_rubric_clarity),
        subject=mcp_target_tool.description,
        context={
            "tool_name": mcp_target_tool.name,
            "inputSchema": mcp_target_tool.inputSchema,
        },
    )
    assert result.score >= 4, (
        f"clarity score {result.score} < 4. "
        f"reasoning={result.reasoning!r} raw_response={result.raw_response!r}"
    )


async def test_description_disambiguation(
    mcp_judge: Judge,
    mcp_target_tool,
    mcp_rubric_disambiguation,
    tool_config: ToolConfig,
) -> None:
    """Disambiguation score >= 4 against tool description.

    Same subject/context shape as the clarity check.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    if tool_config.judges is not None and "disambiguation" not in tool_config.judges:
        pytest.skip(
            reason=f"judge 'disambiguation' not selected for tool {mcp_target_tool.name!r}"
        )
    result = await mcp_judge.judge(
        str(mcp_rubric_disambiguation),
        subject=mcp_target_tool.description,
        context={
            "tool_name": mcp_target_tool.name,
            "inputSchema": mcp_target_tool.inputSchema,
        },
    )
    assert result.score >= 4, (
        f"disambiguation score {result.score} < 4. "
        f"reasoning={result.reasoning!r} raw_response={result.raw_response!r}"
    )


async def test_parameters_self_explanatory(
    mcp_judge: Judge,
    mcp_target_tool,
    mcp_rubric_parameters,
    tool_config: ToolConfig,
) -> None:
    """Parameters score >= 4. Subject = inputSchema JSON, NOT description.

    Rubric ID is `parameters` (the user-facing short form), distinct from
    the prompt `dimension` `parameters_self_explanatory`.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    if tool_config.judges is not None and "parameters" not in tool_config.judges:
        pytest.skip(
            reason=f"judge 'parameters' not selected for tool {mcp_target_tool.name!r}"
        )
    result = await mcp_judge.judge(
        str(mcp_rubric_parameters),
        subject=json.dumps(mcp_target_tool.inputSchema, indent=2),
        context={
            "tool_name": mcp_target_tool.name,
            "description": mcp_target_tool.description,
        },
    )
    assert result.score >= 4, (
        f"parameters score {result.score} < 4. "
        f"reasoning={result.reasoning!r} raw_response={result.raw_response!r}"
    )


# ===========================================================================
# Category 3 -- deterministic output conformance
# ===========================================================================


async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    mcp_target_tool,
    tool_config: ToolConfig,
) -> None:
    """call_tool with configured args returns isError=False.

    Output-category tests use tool_config.call_arguments (default {}).
    With a tool whose inputSchema.required is non-empty, providing args
    via the `tools.<name>.call_arguments` registry block unblocks all three.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    result = await mcp_client.call_tool(mcp_target_tool.name, tool_config.call_arguments)
    assert not result.isError, f"call_tool returned isError=True: {result!r}"


async def test_result_has_content_or_structured(
    mcp_client: McpTestClient,
    mcp_target_tool,
    tool_config: ToolConfig,
) -> None:
    """At least one content block OR non-null structuredContent."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    result = await mcp_client.call_tool(mcp_target_tool.name, tool_config.call_arguments)
    assert result.content or result.structuredContent is not None, (
        f"both content and structuredContent empty: {result!r}"
    )


async def test_text_content_parses_as_json(
    mcp_client: McpTestClient,
    mcp_target_tool,
    tool_config: ToolConfig,
) -> None:
    """At least one TextContent block parses as JSON.

    If structuredContent AND target_tool.outputSchema both present,
    validate via Draft202012Validator. Black-box safe: NO key assertions
    on homelab-mcp internals.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    result = await mcp_client.call_tool(mcp_target_tool.name, tool_config.call_arguments)

    # Step 1 -- attempt json.loads on each TextContent block; >=1 must parse.
    parsed_any = False
    attempts: list[str] = []
    for block in (result.content or []):
        text = getattr(block, "text", None)
        if text is None:
            continue
        attempts.append(text)
        try:
            json.loads(text)
            parsed_any = True
            break
        except json.JSONDecodeError:
            continue
    if not parsed_any:
        # Show all attempts (truncated to 200 chars each) for diagnosis.
        truncated = [a[:200] + ("..." if len(a) > 200 else "") for a in attempts]
        pytest.fail(
            f"No TextContent block parsed as JSON. "
            f"attempts ({len(attempts)} blocks): {truncated!r}"
        )

    # Step 2 -- optional structured-content schema validation.
    output_schema = getattr(mcp_target_tool, "outputSchema", None)
    if result.structuredContent is not None and output_schema:
        # Raises jsonschema.ValidationError on mismatch -- pytest will surface
        # the full path + message in the failure diagnostic.
        Draft202012Validator(output_schema).validate(result.structuredContent)
