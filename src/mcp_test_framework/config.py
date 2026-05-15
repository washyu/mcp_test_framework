"""Top-level layered configuration via pydantic-settings.

Precedence:

    CLI/init kwargs (yaml_file=PATH) > MCPTF_CONFIG_FILE (path pointer)
    > YAML overlay at the resolved PATH > defaults

The resolver in ``cli.py:_load_config`` passes the resolved YAML path as an
explicit ``yaml_file`` kwarg to ``Config(...)``. The custom
``settings_customise_sources`` below reads that kwarg from ``init_settings``
and hands it to ``YamlConfigSettingsSource``. ``MCPTF_CONFIG_FILE`` is read
as a PATH POINTER only -- a fallback for cases where ``Config()`` is
instantiated without the kwarg (notably the in-process pytest session
launched by ``pytest.main`` from ``cli.py:run``). Env vars NEVER inject
scalar values into the model; they only direct the YAML loader to a file.
``--config`` and ``./config.yaml`` autodiscovery are resolved in ``cli.py``
BEFORE ``Config(...)`` is constructed.

``.env`` is dead-letter for the framework's config layer. Sub-model
``validation_alias=AliasChoices(...)`` declarations on ``OllamaConfig`` etc.
survive only for YAML-key matching; the env-routing role is gone.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from mcp_test_framework.models import (
    HomelabConfig,
    McpServerConfig,
    OllamaConfig,
    SdetConfig,
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
    homelab: HomelabConfig = Field(default_factory=HomelabConfig)
    # ``sdet`` is REQUIRED -- no default. Missing key triggers the canonical
    # missing-required-field operator-tone error (see docs/ERROR-STYLE.md)
    # via ``_emit_operator_error_for_validation``'s ``missing`` branch in
    # ``cli.py``. One source of truth -- no env var, no CLI flag override.
    sdet: SdetConfig

    judge_timeout_seconds: int = 120

    version: int = 2

    # Per-tool registry. Runtime semantics are opt-in: only tools listed
    # here (with ``skip != True``) participate in the contract pass.
    tools: dict[str, ToolConfig] = Field(default_factory=dict)

    @field_validator("version", mode="after")
    @classmethod
    def _validate_version(cls, v: int) -> int:
        """Only ``2`` is accepted; v1 configs raise so ``cli.py``'s
        operator-error mapper can render the canonical version-mismatch
        error message (see docs/ERROR-STYLE.md)."""
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
        """Collapse the source pipeline to ``init_kwargs -> YAML -> defaults``.

        ``env_settings`` and ``dotenv_settings`` are accepted as parameters
        (pydantic-settings calls us with them) but intentionally dropped
        from the returned tuple.

        The resolver in ``cli.py:_load_config`` passes the resolved YAML
        path as ``Config(yaml_file=str(path))``. We pop ``yaml_file`` from
        ``init_settings.init_kwargs`` BEFORE the YAML source is constructed
        so it does not reach the model validator (``Config`` has
        ``extra="forbid"`` and no ``yaml_file`` field, so leaving it in
        the init_kwargs would raise ``ExtraForbidden``).
        """
        # Locked pop pattern (probe-verified).
        yaml_file = init_settings.init_kwargs.pop("yaml_file", None)
        # IPC fallback: when no explicit ``yaml_file`` kwarg is given, fall
        # back to ``MCPTF_CONFIG_FILE`` so the in-process pytest session
        # spawned by ``cli.py:run`` picks up the operator's resolved path.
        # This env var is a PATH POINTER, not a value source -- it can only
        # direct the YAML loader to a file, never inject scalar config values.
        if yaml_file is None:
            yaml_file = os.environ.get("MCPTF_CONFIG_FILE")
        sources: list[PydanticBaseSettingsSource] = [init_settings]
        if yaml_file and Path(yaml_file).is_file():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
            )
        sources.append(file_secret_settings)
        return tuple(sources)
