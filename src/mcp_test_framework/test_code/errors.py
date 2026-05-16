"""ToolCallError -- typed exception for MCP tool ``isError=True`` responses.

Design choices:
  - Plain ``Exception`` subclass (NOT a Pydantic model) for traceback-friendly
    pytest integration and the standard ``except ToolCallError as e:`` idiom.
    Plain Exception keeps the runtime overhead near zero and avoids
    surprising interactions with pytest's traceback machinery. ``.raw`` is a
    live ``mcp.types.CallToolResult`` (not a Pydantic clone).
  - Strict heuristic chain for code/message extraction, in order:
      1. ``raw.structuredContent`` dict -> read "code" / "message" string keys.
      2. First TextContent.text -> ``json.loads(...)`` -> if it parses to a
         dict, read "code" / "message" string keys.
      3. else: ``message = concat(TextContent.text)``, ``code = None``.
    Only "code" and "message" are recognized -- the recognized key set is
    strictly those two keys; alternative names are NOT accepted, and there is
    NO recursive walk into nested dicts.
    Non-string ``code`` values are coerced via ``str(...)`` (so a server
    returning ``code: 404`` becomes ``"404"``); non-string ``message`` values
    fall through to the next step (the dict is treated as not-a-match, not a
    partial match).

Pitfall: ``CallToolResult.content`` is heterogeneous (``TextContent |
ImageContent | AudioContent | ResourceLink | EmbeddedResource``). Iteration
MUST filter on ``isinstance(block, TextContent)`` -- never
``getattr(block, "text")`` naively, which would AttributeError on
``ImageContent`` / ``AudioContent`` / ``ResourceLink`` / ``EmbeddedResource``.

This module is pyright-strict-clean.
"""
from __future__ import annotations

import json

from mcp.types import CallToolResult, TextContent


class ToolCallError(Exception):
    """Raised by ToolWrapper.call() when result.isError is True.

    Attributes:
        tool: MCP tool name (e.g. "create_vm").
        code: server-supplied error code, or None if absent.
        message: human-readable error prose.
        raw: the live `mcp.types.CallToolResult` (not a Pydantic clone).
    """

    def __init__(
        self,
        *,
        tool: str,
        code: str | None,
        message: str,
        raw: CallToolResult,
    ) -> None:
        self.tool = tool
        self.code = code
        self.message = message
        self.raw = raw
        super().__init__(self._format_default())

    def _format_default(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


def _extract_code_message(raw: CallToolResult) -> tuple[str | None, str]:
    """Strict heuristic chain. Returns (code, message).

    Strict key set: only "code" and "message" are recognized. No synonyms,
    no recursive walk. Non-string `code` coerced via str(); non-string
    `message` falls through to the next step.

    Step order (ORDER is a regression-pinned invariant):
      1. ``raw.structuredContent`` dict -> read "code" / "message" string keys.
      2. First TextContent JSON -> if it parses to a dict, read
         "code" / "message" string keys.
      3. concat fallback: ``message = concat(TextContent.text)``, ``code = None``.
    """
    # Step 1: structuredContent dict
    sc = getattr(raw, "structuredContent", None)
    if isinstance(sc, dict):
        code = sc.get("code")
        message = sc.get("message")
        if isinstance(message, str):
            return (str(code) if code is not None else None, message)

    # Step 2: first TextContent JSON
    for block in raw.content:
        if isinstance(block, TextContent):
            try:
                parsed = json.loads(block.text)
            except (json.JSONDecodeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                code = parsed.get("code")
                message = parsed.get("message")
                if isinstance(message, str):
                    return (str(code) if code is not None else None, message)
            break  # only try the first TextContent

    # Step 3: concat fallback
    concat = "".join(b.text for b in raw.content if isinstance(b, TextContent))
    return (None, concat)
