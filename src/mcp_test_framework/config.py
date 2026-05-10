"""Top-level layered configuration via pydantic-settings.

Precedence (Phase 13 D-05):

    CLI/init kwargs (yaml_file=PATH) > YAML overlay at PATH > defaults

The resolver in `cli.py:_load_config` (Phase 13 D-03) passes the resolved
YAML path as an explicit `yaml_file` kwarg to `Config(...)`. The custom
`settings_customise_sources` below reads that kwarg from `init_settings`
and hands it to `YamlConfigSettingsSource`. `MCPTF_CONFIG_FILE`, `--config`,
and `./config.yaml` autodiscovery are all resolved in `cli.py` BEFORE
`Config(...)` is constructed; no env vars influence Config values directly.

`.env` is dead-letter for the framework's config layer (Phase 13 D-07).
Sub-model `validation_alias=AliasChoices(...)` declarations on
`OllamaConfig` etc. survive only for YAML-key matching; the env-routing
role is gone (D-05).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from mcp_test_framework.models import (
    McpServerConfig,
    OllamaConfig,
    ToolConfig,
)


class Config(BaseSettings):
    """Top-level configuration. Frozen for safe session-scoped sharing across async tests."""

    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)

    judge_timeout_seconds: int = 120

    # Phase 13 D-08: v2 schema. Plan 13-02 flipped from v1.
    version: int = 2

    # Phase 08 D-01 / TOOLCFG-01: per-tool registry. Plan 13-03 will flip
    # the runtime semantics from opt-out to opt-in.
    tools: dict[str, ToolConfig] = Field(default_factory=dict)

    @field_validator("version", mode="after")
    @classmethod
    def _validate_version(cls, v: int) -> int:
        """Phase 13 D-08: only `2` is accepted; v1 configs raise so cli.py's
        operator-error mapper can render the SAFE-06 ERROR-STYLE message."""
        if v != 2:
            raise ValueError(
                f"config version {v} not supported by this build, expected 2"
            )
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Phase 13 D-05: collapse the source pipeline to
        init_kwargs -> YAML -> defaults. env_settings and dotenv_settings
        are accepted as parameters (pydantic-settings calls us with them)
        but intentionally dropped from the returned tuple.

        The resolver in cli.py:_load_config passes the resolved YAML
        path as `Config(yaml_file=str(path))`. We pop `yaml_file` from
        init_settings.init_kwargs BEFORE the YAML source is constructed
        so it does not reach the model validator (Config has
        `extra="forbid"` and no `yaml_file` field, so leaving it in
        the init_kwargs would raise `ExtraForbidden`).
        """
        # Locked pop pattern (D-03, revision iteration 1 probe-verified).
        yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
        sources: list[PydanticBaseSettingsSource] = [init_settings]
        if yaml_file and Path(yaml_file).is_file():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
            )
        sources.append(file_secret_settings)
        return tuple(sources)
