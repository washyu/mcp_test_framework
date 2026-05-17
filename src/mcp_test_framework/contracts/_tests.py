"""Parametrized MCP contract test bodies (TEST-01..TEST-10).

Extracted from tests/contract/test_mcp_tool_contract.py per Phase 27 D-04.
This module is NOT discovered via filesystem walk — the framework's
pytest plugin (`mcp_test_framework._plugin`) injects it at collection
time when `[tool.pytest.ini_options] mcp_config_file` is set in the
operator's pyproject.toml.

The plugin synthesizes a `_ContractsModule` collector whose `path`
points at this file (so pytest-asyncio sees `pytestmark` normally) but
whose `nodeid` is overridden to render as
`<mcp-contracts>::test_<name>[<tool>]` per CONTEXT.md D-08.

Test bodies preserve v1.3 assertion semantics verbatim. Fixtures use
the v1.4 `mcp_*` prefixed surface (Phase 26 D-15..D-19); `tool_config`
stays unprefixed by design.
"""
from __future__ import annotations

import json

import pytest
from jsonschema.validators import Draft202012Validator

from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import ToolConfig
from mcp_test_framework.schema_validator import validate_tool_schema

# UNMARKED per D-markers-1; preflight is the gate (D-preflight-1..4).
# loop_scope="session" required so fixtures + tests share the session loop.
pytestmark = [pytest.mark.asyncio(loop_scope="session")]


# ===========================================================================
# Category 1 -- deterministic schema (TEST-01..TEST-04)
# ===========================================================================


async def test_target_tool_exists(mcp_target_tool, tool_config: ToolConfig) -> None:
    """TEST-01: configured TARGET_TOOL_NAME present in server tool list.

    Defense in depth: _preflight + the target_tool fixture (FIX-03) already
    raised ToolNotFoundError if the tool was missing; reaching this body
    means the fixture resolved. The explicit assertion gives a diagnostic
    name to the test in pytest output.
    """
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    assert mcp_target_tool.name, f"target_tool.name is empty: {mcp_target_tool!r}"


async def test_schema_passes_structural_checks(mcp_target_tool, tool_config: ToolConfig) -> None:
    """TEST-02: validate_tool_schema returns no errors for the target tool."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    issues = validate_tool_schema(mcp_target_tool)
    assert issues == [], f"schema issues found: {issues!r}"


async def test_description_min_length(mcp_target_tool, tool_config: ToolConfig) -> None:
    """TEST-03: description is non-empty and >= 20 chars."""
    if tool_config.skip:
        pytest.skip(reason=tool_config.skip_reason or "tool skipped via config")
    desc = mcp_target_tool.description or ""
    assert len(desc) >= 20, (
        f"description too short ({len(desc)} chars): {desc!r}"
    )


async def test_every_parameter_has_description_and_type(
    mcp_target_tool, tool_config: ToolConfig
) -> None:
    """TEST-04: every input parameter has a description AND a type/oneOf/anyOf."""
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
# Category 2 -- LLM-judged (TEST-05..TEST-07; score >= 4 per spec)
# ===========================================================================


async def test_description_clarity(
    mcp_judge: Judge,
    mcp_target_tool,
    mcp_rubric_clarity,
    tool_config: ToolConfig,
) -> None:
    """TEST-05: clarity score >= 4 against tool description.

    Subject = description; context carries tool_name + inputSchema (D-rubrics-3).
    Per Phase 08 D-08/D-09: skip when `tool_config.skip` is set or when
    `clarity` is not in the configured `judges` subset.
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
    """TEST-06: disambiguation score >= 4 against tool description.

    Same subject/context shape as TEST-05 (D-rubrics-3).
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
    """TEST-07: parameters score >= 4. Subject = inputSchema JSON, NOT description (D-rubrics-3).

    Rubric ID per D-10 / TOOLCFG-04 is `parameters` (the user-facing short
    form), distinct from the prompt `dimension` `parameters_self_explanatory`.
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
# Category 3 -- deterministic output conformance (TEST-08..TEST-10)
# ===========================================================================


async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    mcp_target_tool,
    tool_config: ToolConfig,
) -> None:
    """TEST-08: call_tool with configured args returns isError=False.

    Per Phase 08 D-11: TEST-08/09/10 use tool_config.call_arguments (default
    {}). With a tool whose inputSchema.required is non-empty, providing args
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
    """TEST-09: at least one content block OR non-null structuredContent."""
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
    """TEST-10: >=1 TextContent block parses as JSON; if structuredContent
    AND target_tool.outputSchema both present, validate via Draft202012Validator
    (D-test10-1, D-test10-2). Black-box safe: NO key assertions on
    homelab-mcp internals.
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
