"""Unit tests for mcp_test_framework.sdet.response.ToolResponse (CODEGEN-04, D-07).

Pins the .data fallback chain (structuredContent -> JSON-parse first TextContent
-> {"text": <concat>} fallback -> None), .text concatenation across mixed
content blocks (Pitfall 7 in 17-RESEARCH.md: must skip non-TextContent), and
.is_error mirror semantics.

Pure-sync (no asyncio) -- ToolResponse is a pure-data Pydantic model.
"""
from __future__ import annotations

from mcp.types import CallToolResult, TextContent

from mcp_test_framework.sdet import ToolResponse


def _result(
    *,
    content: list | None = None,
    structured: dict | None = None,
    is_error: bool = False,
) -> CallToolResult:
    return CallToolResult(
        content=content or [],
        structuredContent=structured,
        isError=is_error,
    )


def test_is_error_mirrors_raw() -> None:
    assert ToolResponse(raw=_result(is_error=False)).is_error is False
    assert ToolResponse(raw=_result(is_error=True)).is_error is True


def test_data_prefers_structured_content() -> None:
    """Step 1 of fallback chain: structuredContent wins even if text is also present."""
    raw = _result(
        content=[TextContent(type="text", text='{"ignored": true}')],
        structured={"foo": 1},
    )
    assert ToolResponse(raw=raw).data == {"foo": 1}


def test_data_parses_first_text_content_when_no_structured() -> None:
    """Step 2: JSON-parse first TextContent if structuredContent is absent."""
    raw = _result(content=[TextContent(type="text", text='{"foo": 1}')])
    assert ToolResponse(raw=raw).data == {"foo": 1}


def test_data_falls_back_to_text_dict_when_json_parse_fails() -> None:
    """Step 3: malformed JSON -> {"text": <concat>}."""
    raw = _result(content=[TextContent(type="text", text="not json at all")])
    assert ToolResponse(raw=raw).data == {"text": "not json at all"}


def test_data_falls_back_when_first_text_parses_to_non_dict() -> None:
    """Step 3: a JSON list / scalar at first TextContent does not count
    as structured -- falls through to {"text": ...}.
    CODEGEN-04 specifies dict-or-fallback explicitly."""
    raw = _result(content=[TextContent(type="text", text="[1, 2, 3]")])
    assert ToolResponse(raw=raw).data == {"text": "[1, 2, 3]"}


def test_data_returns_none_when_no_content_and_no_structured() -> None:
    """Step 4: empty content and no structuredContent -> None."""
    assert ToolResponse(raw=_result()).data is None


def test_text_concatenates_text_blocks() -> None:
    raw = _result(content=[
        TextContent(type="text", text="hello "),
        TextContent(type="text", text="world"),
    ])
    assert ToolResponse(raw=raw).text == "hello world"


def test_text_skips_non_text_blocks_pitfall_7() -> None:
    """Pitfall 7 (17-RESEARCH.md): naive iteration would AttributeError on
    ImageContent / AudioContent / ResourceLink / EmbeddedResource. .text
    MUST filter via isinstance(block, TextContent)."""
    from mcp.types import ImageContent
    raw = _result(content=[
        TextContent(type="text", text="hi"),
        ImageContent(type="image", data="aGVsbG8=", mimeType="image/png"),
        TextContent(type="text", text=" there"),
    ])
    # No AttributeError; image block is skipped, text blocks concatenate.
    assert ToolResponse(raw=raw).text == "hi there"


def test_data_does_not_check_is_error_pitfall_8() -> None:
    """Pitfall 8: .data returns whatever payload the server sent, even when
    is_error=True. Phase 18's ToolCallError surfaces the error; Phase 17 keeps
    .data spec-literal (no early return on error)."""
    raw = _result(
        content=[TextContent(type="text", text='{"error": "bad input"}')],
        is_error=True,
    )
    response = ToolResponse(raw=raw)
    assert response.is_error is True
    assert response.data == {"error": "bad input"}
