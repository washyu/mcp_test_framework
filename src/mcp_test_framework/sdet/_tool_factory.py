"""tool(name) factory + ToolWrapper Generic.

Locked invariants:
  - stringly-typed ``tool("name").call(params)`` -- single surface, no
    attribute-access namespace (``Tool.create_vm.call(...)`` ergonomic deferred
    until SDETs ask for it).
  - ``ToolWrapper`` is Generic over ``(P, R)`` so an IDE can complete the
    typed response on ``await tool("create_vm").call(params)``.

The module-level ``_REGISTRIES`` + ``_ACTIVE_SLUG`` + ``_ACTIVE_CLIENT`` slots
are populated by the ``mcp_session`` fixture: the fixture loads the generated
``__init__.py`` from the operator-configured ``sdet.generated_root`` via
``importlib.util.spec_from_file_location``, reads its ``_REGISTRY`` attr,
inserts it into ``_REGISTRIES[slug]``, sets ``_ACTIVE_SLUG = slug`` and
``_ACTIVE_CLIENT = <client>``, then yields. On teardown the fixture restores
the previous state.

Why the registry-keyed-by-types shape was chosen: the generated
``generated/<slug>/__init__.py`` writes ``_REGISTRY`` entries keyed against
``(type[BaseModel], type[ToolResponse])``. Exposing ``ToolWrapper`` / ``tool``
here means the generated ``_REGISTRY`` entries always have a live consumer --
the wrapper's ``.params_cls`` / ``.response_cls`` are the registered types
themselves.

Module-level state warning: tests MUST reset ``_ACTIVE_SLUG`` /
``_ACTIVE_CLIENT`` / ``_REGISTRIES`` to their default in a fixture teardown to
avoid bleed across runs.
"""
from __future__ import annotations

from typing import Generic, TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from mcp_test_framework.sdet.response import ToolResponse

if TYPE_CHECKING:
    from mcp_test_framework.mcp_client import McpTestClient


_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}
_ACTIVE_SLUG: str | None = None
# Mutated ONLY by mcp_session in src/mcp_test_framework/sdet/session.py.
_ACTIVE_CLIENT: "McpTestClient | None" = None


P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=ToolResponse)


class ToolWrapper(Generic[P, R]):
    """Returned by ``tool(name)``.

    Contract:
      - Constructed by ``tool(name)`` with the registered ``(params_cls,
        response_cls)`` tuple from the generated ``_REGISTRY``.
      - ``.params_cls`` and ``.response_cls`` are exposed for introspection
        (and for downstream tooling like docs generation).
      - ``.call(params)`` validates ``params`` against the inputSchema by
        virtue of being a Pydantic BaseModel (already done at
        ``CreateVmParams(...)`` construction), then serializes via
        ``params.model_dump(mode='json')``, awaits
        ``McpTestClient.call_tool(self.name, arguments)`` on the active
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

        Behavior:
          - Resolves the active McpTestClient via the module-level
            ``_ACTIVE_CLIENT`` slot (set/cleared by the ``mcp_session``
            fixture). Raises RuntimeError if unset (naming the missing
            fixture so the operator can fix it).
          - Serializes ``params`` via Pydantic with ``mode="json"`` (MCP wire
            format expects JSON-serializable dicts; preserves int/str/list/None
            as-is).
          - Awaits ``McpTestClient.call_tool`` (which already enforces
            ``asyncio.timeout`` internally).
          - On ``result.isError=True``: extracts code+message via the strict
            heuristic chain in ``errors._extract_code_message`` and raises
            ``ToolCallError(tool, code, message, raw)``.
          - On ``result.isError=False``: constructs ``self.response_cls(raw=result)``
            -- the uniform ``.raw / .data / .text / .is_error`` accessors come
            from the ``ToolResponse`` base class.
        """
        if _ACTIVE_CLIENT is None:
            raise RuntimeError(
                "no active MCP client. tool().call() requires the `mcp_session` "
                "fixture. Use it in an SDET test under `tests/sdet/`."
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
    """Look up the typed wrapper for an MCP tool by name.

    Returns a ToolWrapper whose ``params_cls`` and ``response_cls`` were
    registered by ``gen-sdet-classes``.

    Raises:
      RuntimeError: no active registry (the ``mcp_session`` fixture has not
        been entered). Names the missing fixture so the operator can fix it.
      KeyError: the active registry exists but ``name`` is not in it. Lists
        the available names + the active slug.
    """
    if _ACTIVE_SLUG is None:
        raise RuntimeError(
            "no MCP server registry is active. The `mcp_session` fixture is "
            "what activates a registry. If you are running an SDET test "
            "outside of `tests/sdet/` or without `--sdet`, that is the cause."
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
