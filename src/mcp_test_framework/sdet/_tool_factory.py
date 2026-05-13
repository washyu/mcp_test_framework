"""tool(name) factory + ToolWrapper Generic -- the CODEGEN-05 seam.

Per Phase 17 CONTEXT.md decisions:
  - D-09: stringly-typed `tool("name").call(params)` -- single surface, no
    attribute-access namespace (`Tool.create_vm.call(...)` ergonomic deferred
    to v1.4 if SDETs ask).
  - Phase 17 ships the SEAM only: ToolWrapper is constructible, lookup works,
    and the wrapper's .params_cls / .response_cls are correct. The .call()
    wire body raises NotImplementedError pointing at Phase 18.

The module-level _REGISTRIES + _ACTIVE_SLUG slots are populated by Phase 18's
``mcp_session`` fixture: the fixture imports
``mcp_test_framework.sdet.generated.<slug>``, reads its ``_REGISTRY`` attr,
inserts it into ``_REGISTRIES[slug]``, sets ``_ACTIVE_SLUG = slug``, then
yields. On teardown the fixture restores the previous state.

Why ship the seam now (and not roll the whole factory into Phase 18):
  - The generated ``generated/<slug>/__init__.py`` writes ``_REGISTRY`` entries
    keyed against ``(type[BaseModel], type[ToolResponse])``. If Phase 17 didn't
    expose ``ToolWrapper`` / ``tool``, the generated ``_REGISTRY`` would point
    at types with no consumer -- pyright-clean but semantically dangling.
  - Phase 18's only change to this module is the body of ``ToolWrapper.call``.
    The dispatch shape, error messages, and slot contract are LOCKED here.

Module-level state warning: tests MUST reset _ACTIVE_SLUG / _REGISTRIES to
their default in a fixture teardown to avoid bleed.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from mcp_test_framework.sdet.response import ToolResponse


# Phase 18 will mutate these; Phase 17 ships the slots.
_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}
_ACTIVE_SLUG: str | None = None


P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=ToolResponse)


class ToolWrapper(Generic[P, R]):
    """Returned by ``tool(name)``. Phase 17 ships the shape; Phase 18 wires .call().

    Phase 17 contract:
      - Constructed by ``tool(name)`` with the registered ``(params_cls,
        response_cls)`` tuple from the generated ``_REGISTRY``.
      - ``.params_cls`` and ``.response_cls`` are exposed for introspection
        (and for downstream tooling like docs generation).
      - ``.call(params)`` raises NotImplementedError -- the missing piece is
        Phase 18's ``mcp_session`` fixture which owns the ``ClientSession``.

    Phase 18 contract (forward-look only; not implemented here):
      - ``.call(params)`` validates `params` against the inputSchema by virtue
        of being a Pydantic BaseModel (already done at ``CreateVmParams(...)``
        construction), then calls ``ClientSession.call_tool(self.name,
        params.model_dump(mode='python'))``, then constructs
        ``self.response_cls(raw=<result>)``.
    """

    def __init__(self, name: str, params_cls: type[P], response_cls: type[R]) -> None:
        self.name = name
        self.params_cls = params_cls
        self.response_cls = response_cls

    async def call(self, params: P) -> R:
        """Wire body deferred to Phase 18. Raises NotImplementedError.

        Phase 17 ships this stub so generated files are importable + pyright
        sees a coherent return-type chain; Phase 17 tests assert the
        NotImplementedError message is operator-readable.
        """
        raise NotImplementedError(
            "tool().call() requires Phase 18's `mcp_session` fixture which "
            "owns the ClientSession. Phase 17 ships the codegen + dispatch "
            "shape only. See REQUIREMENTS.md SDET-03 (Phase 18) for the "
            "fixture contract."
        )


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
