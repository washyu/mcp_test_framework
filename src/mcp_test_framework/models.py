"""Cross-cutting Pydantic config sub-models.

Per CONTEXT.md D-02: only ``Config`` and its sub-models live here. Domain models
(``ValidationIssue``, ``JudgeResult``) stay in their owning modules.

Each sub-model is independently frozen via ``ConfigDict(frozen=True)`` (Assumption A5
in 01-RESEARCH.md: ``frozen=True`` on a parent ``BaseSettings`` does NOT propagate to
nested ``BaseModel`` fields, so each nested model needs its own marker).

Each spec env-var-mapped field carries an explicit ``validation_alias=AliasChoices(...)``
annotation so that bare env names (per CONTEXT.md "Env var naming convention" lock --
``OLLAMA_BASE_URL``, etc.) route to the correct sub-model field WITHOUT relying on
``env_nested_delimiter`` (which would force ``OLLAMA__BASE_URL`` instead).
See plan-checker iter 1 BLOCKER #1 (resolved Option A) in 01-02-PLAN.md.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OllamaConfig(BaseModel):
    """Ollama judge configuration."""

    model_config = ConfigDict(frozen=True)

    base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL"),
    )
    model: str = Field(
        default="qwen3.6:latest",
        validation_alias=AliasChoices("OLLAMA_MODEL"),
    )
    timeout_seconds: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("OLLAMA_TIMEOUT_SECONDS"),
    )


class McpServerConfig(BaseModel):
    """MCP server subprocess configuration."""

    model_config = ConfigDict(frozen=True)

    command: str = Field(
        default="homelab-mcp",
        validation_alias=AliasChoices("MCP_SERVER_COMMAND"),
    )
    args: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MCP_SERVER_ARGS"),
    )


class TargetConfig(BaseModel):
    """Target tool to run all tests against."""

    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(
        default="list_registered_servers",
        validation_alias=AliasChoices("TARGET_TOOL_NAME"),
    )
