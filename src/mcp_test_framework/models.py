"""Cross-cutting Pydantic config sub-models.

Per CONTEXT.md D-02: only ``Config`` and its sub-models live here. Domain models
(``ValidationIssue``, ``JudgeResult``) stay in their owning modules.

Each sub-model is independently frozen via ``ConfigDict(frozen=True)`` (Assumption A5
in 01-RESEARCH.md: ``frozen=True`` on a parent ``BaseSettings`` does NOT propagate to
nested ``BaseModel`` fields, so each nested model needs its own marker).

Each spec env-var-mapped field carries an explicit
``validation_alias=AliasChoices(<bare env name>, <field name>)`` annotation so that
bare env names (per CONTEXT.md "Env var naming convention" lock -- ``OLLAMA_BASE_URL``
etc.) route to the correct sub-model field WITHOUT relying on ``env_nested_delimiter``
(which would force ``OLLAMA__BASE_URL`` instead). The field name is included as a
second alias choice -- with ``populate_by_name=True`` enabled -- so YAML overlays
(emitted as ``ollama.base_url`` etc.) and init kwargs continue to populate the model.
See plan-checker iter 1 BLOCKER #1 (resolved Option A) in 01-02-PLAN.md.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from mcp_test_framework.rubrics import RUBRIC_IDS, resolve_rubric_id


class OllamaConfig(BaseModel):
    """Ollama judge configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url"),
    )
    model: str = Field(
        default="qwen3.6:latest",
        validation_alias=AliasChoices("OLLAMA_MODEL", "model"),
    )
    timeout_seconds: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("OLLAMA_TIMEOUT_SECONDS", "timeout_seconds"),
    )


class McpServerConfig(BaseModel):
    """MCP server subprocess configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    command: str = Field(
        default="homelab-mcp",
        validation_alias=AliasChoices("MCP_SERVER_COMMAND", "command"),
    )
    args: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MCP_SERVER_ARGS", "args"),
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
    )


class ToolConfig(BaseModel):
    """Per-tool config registry entry (TOOLCFG-01..07; Phase 08 D-01/D-04/D-05).

    Keyed off tool name in `Config.tools: dict[str, ToolConfig]`. Tools with no
    entry use defaults (TOOLCFG-06). `extra="forbid"` makes typos (e.g. `srtip:`
    instead of `skip:`) fail at load time per TOOLCFG-05 / D-15.

    `setup` and `depends_on` are reserved Optional fields (TOOLCFG-03 / D-06):
    typed in the model so SEED-004 / v1.5+ stateful-testing can light them up
    additively without a schema migration. They are ignored at runtime in v1.1.

    NOT env-routable (D-19): no `validation_alias=AliasChoices(...)` on any
    field. The dynamic `dict[str, ToolConfig]` shape doesn't generalize cleanly
    through `_BareNameNestedEnvSource`, and YAML/init are sufficient for the
    use case.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    skip: bool = False
    skip_reason: Optional[str] = None
    call_arguments: dict[str, Any] = Field(default_factory=dict)
    judges: Optional[list[str]] = None
    setup: Optional[Any] = None  # reserved per TOOLCFG-03 / D-06; runtime no-op in v1.1
    depends_on: Optional[list[str]] = None  # reserved per TOOLCFG-03 / D-06

    @field_validator("judges", mode="after")
    @classmethod
    def _validate_judge_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Each judge ID must resolve against the rubric registry (D-17 / TOOLCFG-04).

        None (default) is permitted -- means "run all available rubrics" per
        TOOLCFG-06. Empty list [] is also permitted -- means "explicit opt-out,
        run no rubrics on this tool" (D-07: empty-vs-None semantic is meaningful).
        """
        if v is None:
            return v
        for rubric_id in v:
            if rubric_id not in RUBRIC_IDS:
                # Delegate to resolve_rubric_id for the canonical error message
                # (single source per CD-03).
                resolve_rubric_id(rubric_id)
        return v

    @model_validator(mode="after")
    def _skip_requires_reason(self) -> "ToolConfig":
        """skip=True MUST come with non-empty skip_reason (D-16 / TOOLCFG-07).

        TOOLCFG-07 demands the reason surface in pytest output via
        `pytest.skip(reason=...)`. An empty/whitespace-only reason defeats that
        requirement at the source, so we raise at load time rather than letting
        a silent skip propagate.
        """
        if self.skip and not (self.skip_reason and self.skip_reason.strip()):
            raise ValueError(
                "skip=True requires a non-empty skip_reason "
                "(TOOLCFG-07: the reason surfaces in pytest skip output)"
            )
        return self
