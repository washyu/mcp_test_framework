"""Top-level layered configuration via pydantic-settings.

Precedence (CONTEXT.md "Decisions > config precedence" -- LOCKED):

    CLI/init kwargs > env vars > .env > YAML overlay > defaults

In ``pydantic-settings`` the leftmost source in the tuple returned by
``settings_customise_sources`` wins (Pitfall 1 in 01-RESEARCH.md).

YAML overlay path comes ONLY from the ``MCPTF_CONFIG_FILE`` env var (CONTEXT.md
"YAML config discovery" -- no cwd auto-discovery in MVP). Phase 5 will inject
the ``--config PATH`` CLI flag value via ``Config(...)`` kwargs which arrive as
``init_settings`` -- the highest-precedence source.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from mcp_test_framework.models import (
    McpServerConfig,
    OllamaConfig,
    TargetConfig,
)


class Config(BaseSettings):
    """Top-level configuration. Frozen for safe session-scoped sharing across async tests."""

    # NOTE: nested-env delimiter intentionally NOT set -- bare env names (per CONTEXT.md
    # lock) are routed to sub-model fields via validation_alias on each sub-model field.
    # See plan-checker iter 1 BLOCKER #1 (resolved Option A) in 01-02-PLAN.md.
    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)

    # JUDGE_TIMEOUT_SECONDS routes here without an explicit alias because
    # pydantic-settings uppercases top-level field names by default.
    judge_timeout_seconds: int = 120

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Precedence: CLI/init > env > .env > YAML > default.
        # In pydantic-settings, leftmost source wins.
        yaml_path = os.environ.get("MCPTF_CONFIG_FILE")
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,        # CLI flags arrive as kwargs to Config(...)
            env_settings,         # OS environment
            dotenv_settings,      # .env file
        ]
        if yaml_path and Path(yaml_path).is_file():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path)
            )
        sources.append(file_secret_settings)  # docker secrets etc -- below YAML
        return tuple(sources)
