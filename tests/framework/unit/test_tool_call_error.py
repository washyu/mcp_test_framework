"""Phase 18 D-07 + D-08 pinning: ToolCallError shape + _extract_code_message chain.

Sibling-module convention (matches test_tool_response.py): pure-sync unit tests
that pin the typed-exception surface shipped by Plan 18-01. No asyncio, no
fixtures, no MCP wire -- ToolCallError is a plain Exception subclass and
_extract_code_message is a pure data extractor over `mcp.types.CallToolResult`.

D-07: ToolCallError shape and string-format symmetry with the renderer FAIL row.
D-08: strict heuristic chain over structuredContent / first TextContent / concat
       fallback. Recognized key set is strictly {"code", "message"}; alternative
       names (errorCode / detail / reason / error) are NOT recognized.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from mcp.types import (
    AudioContent,
    CallToolResult,
    ImageContent,
    TextContent,
)

from mcp_test_framework.test_code import ToolCallError
from mcp_test_framework.test_code.errors import _extract_code_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_result(
    *,
    is_error: bool = True,
    structured: dict | None = None,
    content: list | None = None,
) -> CallToolResult:
    """Build a CallToolResult for heuristic tests."""
    return CallToolResult(
        isError=is_error,
        content=content or [],
        structuredContent=structured,
    )


# ---------------------------------------------------------------------------
# D-07: ToolCallError shape
# ---------------------------------------------------------------------------


class TestToolCallErrorShape:
    def test_args0_is_formatted_default_with_code(self) -> None:
        """D-07: when code is truthy, args[0] is `[code] message`."""
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert e.args[0] == "[X] m"

    def test_args0_is_formatted_default_without_code(self) -> None:
        """D-07: when code is None, args[0] is the bare message (no brackets)."""
        e = ToolCallError(tool="t", code=None, message="m", raw=MagicMock())
        assert e.args[0] == "m"

    def test_str_symmetric_with_renderer_format(self) -> None:
        """D-07: str(e) matches the renderer FAIL row format (CONTEXT.md line 264)."""
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert str(e) == "[X] m"

    def test_str_symmetric_without_code(self) -> None:
        """D-07: str(e) with code=None is the bare message."""
        e = ToolCallError(tool="t", code=None, message="m", raw=MagicMock())
        assert str(e) == "m"

    def test_is_plain_exception_not_pydantic(self) -> None:
        """D-07: ToolCallError is plain Exception subclass, NOT Pydantic."""
        e = ToolCallError(tool="t", code="X", message="m", raw=MagicMock())
        assert isinstance(e, Exception)
        assert not hasattr(e, "model_dump")
        assert not hasattr(e, "model_dump_json")

    def test_attributes_exposed(self) -> None:
        """D-07: .tool / .code / .message / .raw are populated."""
        raw = MagicMock()
        e = ToolCallError(tool="t", code="X", message="m", raw=raw)
        assert e.tool == "t"
        assert e.code == "X"
        assert e.message == "m"
        assert e.raw is raw

    def test_keyword_only_constructor(self) -> None:
        """D-07: constructor is keyword-only; positional args must fail."""
        # __init__ uses (*, tool, code, message, raw) per Plan 18-01.
        import pytest as _pytest

        with _pytest.raises(TypeError):
            ToolCallError("t", "X", "m", MagicMock())  # type: ignore[misc]


# ---------------------------------------------------------------------------
# D-08: heuristic chain
# ---------------------------------------------------------------------------


class TestExtractCodeMessage:
    # --- Step 1: raw.structuredContent dict ---

    def test_step1_structured_content_dict_basic(self) -> None:
        """D-08 step 1: code + message both present in structuredContent."""
        raw = _mk_result(structured={"code": "VM_NAME_TAKEN", "message": "name in use"})
        code, msg = _extract_code_message(raw)
        assert code == "VM_NAME_TAKEN"
        assert msg == "name in use"

    def test_step1_code_coerced_to_string(self) -> None:
        """D-08 step 1: non-string code is coerced via str()."""
        raw = _mk_result(structured={"code": 404, "message": "not found"})
        code, msg = _extract_code_message(raw)
        assert code == "404"
        assert msg == "not found"

    def test_step1_message_only_no_code(self) -> None:
        """D-08 step 1: when code key absent, returns (None, message)."""
        raw = _mk_result(structured={"message": "bare"})
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "bare"

    def test_step1_missing_message_falls_through_to_step3(self) -> None:
        """D-08 step 1: when message key absent, dict is treated as not-a-match,
        falls through to step 2/3."""
        raw = _mk_result(
            structured={"code": "X"},
            content=[TextContent(type="text", text="fallback")],
        )
        code, msg = _extract_code_message(raw)
        # Step 2 inspects first TextContent ("fallback" is not JSON -> falls);
        # step 3 concats -> "fallback".
        assert msg == "fallback"
        assert code is None

    def test_step1_non_string_message_falls_through(self) -> None:
        """D-08 step 1: non-string message in dict is treated as not-a-match."""
        raw = _mk_result(
            structured={"code": "X", "message": ["not", "a", "string"]},
            content=[TextContent(type="text", text="fallback")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "fallback"

    # --- Step 2: first TextContent JSON ---

    def test_step2_first_textcontent_json(self) -> None:
        """D-08 step 2: first TextContent parses to dict with code+message."""
        raw = _mk_result(
            structured=None,
            content=[TextContent(type="text", text='{"code":"X","message":"Y"}')],
        )
        code, msg = _extract_code_message(raw)
        assert code == "X"
        assert msg == "Y"

    def test_step2_non_dict_json_falls_through(self) -> None:
        """D-08 step 2: JSON parses to a list (not a dict). Step 2 still breaks
        after the first TextContent, so step 3 concats that same content."""
        raw = _mk_result(
            structured=None,
            content=[TextContent(type="text", text="[1,2,3]")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "[1,2,3]"

    def test_step2_invalid_json_falls_through(self) -> None:
        """D-08 step 2: malformed JSON -> JSONDecodeError caught -> fall to step 3."""
        raw = _mk_result(
            structured=None,
            content=[TextContent(type="text", text="not { valid json")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "not { valid json"

    def test_step2_break_after_first_textcontent(self) -> None:
        """D-08 step 2: only the FIRST TextContent is inspected for JSON.
        Second TextContent (even if a valid {code,message} JSON) is ignored
        by step 2 -- step 3 takes over via concat."""
        raw = _mk_result(
            structured=None,
            content=[
                TextContent(type="text", text="plaintext first"),
                TextContent(type="text", text='{"code":"X","message":"Y"}'),
            ],
        )
        code, msg = _extract_code_message(raw)
        # Step 2 inspects only the first -- it doesn't parse to a dict-with-message;
        # step 3 concats BOTH TextContent.text values.
        assert code is None
        assert msg == 'plaintext first{"code":"X","message":"Y"}'

    # --- Step 3: concat fallback ---

    def test_step3_plain_text(self) -> None:
        """D-08 step 3: single non-JSON TextContent -> (None, text)."""
        raw = _mk_result(
            structured=None,
            content=[TextContent(type="text", text="boom")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "boom"

    def test_step3_concat_multiple_textcontent(self) -> None:
        """D-08 step 3: multiple TextContent.text are concatenated in order."""
        raw = _mk_result(
            structured=None,
            content=[
                TextContent(type="text", text="a"),
                TextContent(type="text", text="b"),
            ],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "ab"

    def test_step3_pitfall7_mixed_content_skips_non_text(self) -> None:
        """D-08 step 3 + Pitfall 7: only TextContent contributes to concat;
        ImageContent / AudioContent are skipped (no AttributeError)."""
        raw = _mk_result(
            structured=None,
            content=[
                TextContent(type="text", text="a"),
                ImageContent(type="image", data="aGVsbG8=", mimeType="image/png"),
                AudioContent(type="audio", data="aGVsbG8=", mimeType="audio/wav"),
                TextContent(type="text", text="b"),
            ],
        )
        # Step 2 inspects first block (TextContent "a") -- "a" is not JSON;
        # step 3 concats only TextContent blocks -> "ab".
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "ab"

    def test_step3_empty_content_yields_empty_message(self) -> None:
        """D-08 step 3: content=[] -> message is the empty string."""
        raw = _mk_result(structured=None, content=[])
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == ""

    # --- D-08 strict key set ---

    def test_strict_keys_no_synonym_recognition(self) -> None:
        """D-08 strict: errorCode / detail are NOT recognized as code/message."""
        raw = _mk_result(
            structured={"errorCode": "X", "detail": "Y"},
            content=[TextContent(type="text", text="fallback")],
        )
        code, msg = _extract_code_message(raw)
        # structuredContent has no 'message' key -> step 1 falls through;
        # step 2 fails to parse 'fallback' as JSON;
        # step 3 concats -> 'fallback'.
        assert code is None
        assert msg == "fallback"

    def test_strict_keys_reason_synonym_not_recognized(self) -> None:
        """D-08 strict: 'reason' is NOT recognized as a message synonym."""
        raw = _mk_result(
            structured={"code": "X", "reason": "Y"},
            content=[TextContent(type="text", text="z")],
        )
        code, msg = _extract_code_message(raw)
        assert code is None
        assert msg == "z"

    def test_strict_no_recursive_walk(self) -> None:
        """D-08 strict: code/message must be top-level keys; nested dicts are
        NOT walked into."""
        raw = _mk_result(
            structured={"error": {"code": "X", "message": "Y"}},
            content=[TextContent(type="text", text="z")],
        )
        code, msg = _extract_code_message(raw)
        # No top-level 'message' -> step 1 falls through; step 2/3 land on 'z'.
        assert code is None
        assert msg == "z"
