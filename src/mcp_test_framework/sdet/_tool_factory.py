"""tool(name) factory + ToolWrapper Generic -- the CODEGEN-05 seam.

Per Phase 17 CONTEXT.md decisions:
  - D-09: stringly-typed `tool("name").call(params)` -- single surface, no
    attribute-access namespace (`Tool.create_vm.call(...)` ergonomic deferred
    to v1.4 if SDETs ask).
  - Phase 17 shipped the SEAM only: ToolWrapper is constructible, lookup
    works, and the wrapper's .params_cls / .response_cls are correct. Phase
    17 also shipped a stub `.call()` body that pointed at Phase 18.

Phase 18 SDET-03 (this module's current state):
  - The `.call()` body is fully wired. It serializes params via Pydantic
    (`mode="json"`), routes through the active McpTestClient stashed in
    `_ACTIVE_CLIENT`, raises `ToolCallError` (UI-02) on `result.isError`, and
    constructs `self.response_cls(raw=result)` on success.
  - A new module slot `_ACTIVE_CLIENT` is set/cleared by the `mcp_session`
    fixture body (sibling to `_ACTIVE_SLUG`).

The module-level _REGISTRIES + _ACTIVE_SLUG + _ACTIVE_CLIENT slots are
populated by Phase 18's ``mcp_session`` fixture: the fixture imports
``mcp_test_framework.sdet.generated.<slug>``, reads its ``_REGISTRY`` attr,
inserts it into ``_REGISTRIES[slug]``, sets ``_ACTIVE_SLUG = slug`` and
``_ACTIVE_CLIENT = <client>``, then yields. On teardown the fixture restores
the previous state.

Why the seam was shipped in Phase 17 (and not rolled into Phase 18):
  - The generated ``generated/<slug>/__init__.py`` writes ``_REGISTRY`` entries
    keyed against ``(type[BaseModel], type[ToolResponse])``. If Phase 17 didn't
    expose ``ToolWrapper`` / ``tool``, the generated ``_REGISTRY`` would point
    at types with no consumer -- pyright-clean but semantically dangling.
  - Phase 18's only change to this module is the body of ``ToolWrapper.call``
    (plus the `_ACTIVE_CLIENT` slot). The dispatch shape, error messages, and
    slot contract are LOCKED here.

Module-level state warning: tests MUST reset _ACTIVE_SLUG / _ACTIVE_CLIENT /
_REGISTRIES to their default in a fixture teardown to avoid bleed.
"""
from __future__ import annotations

from typing import Generic, TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from mcp_test_framework.sdet.response import ToolResponse

if TYPE_CHECKING:
    from mcp_test_framework.mcp_client import McpTestClient


# Phase 18 will mutate these; Phase 17 ships the slots.
_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}
_ACTIVE_SLUG: str | None = None
# Phase 18 SDET-03: active McpTestClient injected by the mcp_session fixture.
# Mutated ONLY by mcp_session in src/mcp_test_framework/sdet/session.py.
_ACTIVE_CLIENT: "McpTestClient | None" = None


P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=ToolResponse)


class ToolWrapper(Generic[P, R]):
    """Returned by ``tool(name)``. Phase 18 wires the full call path.

    Phase 17 contract (still in force):
      - Constructed by ``tool(name)`` with the registered ``(params_cls,
        response_cls)`` tuple from the generated ``_REGISTRY``.
      - ``.params_cls`` and ``.response_cls`` are exposed for introspection
        (and for downstream tooling like docs generation).

    Phase 18 SDET-03 contract (now live in this module):
      - ``.call(params)`` validates `params` against the inputSchema by virtue
        of being a Pydantic BaseModel (already done at ``CreateVmParams(...)``
        construction), then serializes via ``params.model_dump(mode='json')``,
        awaits ``McpTestClient.call_tool(self.name, arguments)`` on the active
        ``_ACTIVE_CLIENT`` slot, and either raises ``ToolCallError`` (when
        ``result.isError`` is True) or constructs
        ``self.response_cls(raw=result)``.
    """

    def __init__(self, name: str, params_cls: type[P], response_cls: type[R]) -> None:
        self.name = name
        self.params_cls = params_cls
        self.response_cls = response_cls

    async def call(self, params: P) -> R:
        """Make the MCP wire call; raise ToolCallError on isError; else return response_cls.

        Phase 18 SDET-03 + UI-02 wiring:
          - Resolves the active McpTestClient via the module-level _ACTIVE_CLIENT
            slot (set/cleared by the mcp_session fixture). Raises RuntimeError if
            unset (naming the missing fixture so the operator can fix it).
          - Serializes `params` via Pydantic with mode="json" (MCP wire format
            expects JSON-serializable dicts; preserves int/str/list/None as-is).
          - Awaits McpTestClient.call_tool (which already enforces asyncio.timeout
            per mcp_client.py:207-210).
          - On result.isError=True: extracts code+message via the D-08 strict
            heuristic chain and raises ToolCallError(tool, code, message, raw).
          - On result.isError=False: constructs self.response_cls(raw=result) per
            CODEGEN-04's uniform .raw/.data/.text/.is_error contract.
        """
        if _ACTIVE_CLIENT is None:
            raise RuntimeError(
                "no active MCP client. tool().call() requires the `mcp_session` "
                "fixture (Phase 18). Use it in an SDET test under `tests/sdet/`."
            )
        arguments = params.model_dump(mode="json")
        result = await _ACTIVE_CLIENT.call_tool(self.name, arguments)
        if result.isError:
            from mcp_test_framework.sdet.errors import (
                ToolCallError,
                _extract_code_message,
            )
            code, message = _extract_code_message(result)
            raise ToolCallError(
                tool=self.name,
                code=code,
                message=message,
                raw=result,
            )
        return self.response_cls(raw=result)


def tool(name: str) -> ToolWrapper:
    """Look up the typed wrapper for an MCP tool by name (D-09).

    Phase 17 contract: returns a ToolWrapper whose ``params_cls`` and
    ``response_cls`` were registered by ``gen-sdet-classes``. Phase 18 wires
    the ``.call()`` body.

    Raises:
      RuntimeError: no active registry (Phase 18's mcp_session fixture not
        entered). Names the missing fixture so the operator can fix it.
      KeyError: the active registry exists but ``name`` is not in it. Lists
        the available names + the active slug (mirrors ToolNotFoundError at
        mcp_client.py:51-65).
    """
    if _ACTIVE_SLUG is None:
        raise RuntimeError(
            "no MCP server registry is active. Phase 17 ships the dispatch "
            "shape only; the `mcp_session` fixture (Phase 18) is what "
            "activates a registry. If you are running an SDET test outside "
            "of `tests/sdet/` or without `--sdet`, that is the cause."
        )
    registry = _REGISTRIES.get(_ACTIVE_SLUG, {})
    if name not in registry:
        raise KeyError(
            f"tool {name!r} is not in the generated registry for server "
            f"{_ACTIVE_SLUG!r}. Available tools: {sorted(registry.keys())!r}. "
            f"Re-run `mcp-test-framework gen-sdet-classes` if the server's "
            f"tool set changed."
        )
    params_cls, response_cls = registry[name]
    return ToolWrapper(name, params_cls, response_cls)
