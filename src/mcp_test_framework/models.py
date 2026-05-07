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

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


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


class TargetConfig(BaseModel):
    """Target tool to run all tests against. None = discover all tools (Phase 07 D-01)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
    )

    @field_validator("tool_name", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        """Empty string from env -> None (Phase 07 D-02 'empty equivalent to None').

        The project's custom _BareNameNestedEnvSource (config.py:91-146) reads
        an env var as present when membership-check passes, regardless of value.
        TARGET_TOOL_NAME='' would land as '' (not None) without this coercion.
        See 07-RESEARCH §Pitfall 2.
        """
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
