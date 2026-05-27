"""Top-level layered configuration via pydantic-settings.

Precedence:

    CLI/init kwargs (yaml_file=PATH) > YAML overlay at PATH > defaults

The resolver in ``cli.py:_load_config`` passes the resolved YAML path as an
explicit ``yaml_file`` kwarg to ``Config(...)``. The custom
``settings_customise_sources`` below reads that kwarg from ``init_settings``
and hands it to ``YamlConfigSettingsSource``. ``--config`` and
``./config.yaml`` autodiscovery are resolved in ``cli.py`` BEFORE
``Config(...)`` is constructed. The library-mode entry point
(``[tool.pytest.ini_options] mcp_config_file = PATH``) is resolved in
``_plugin.py:pytest_configure``. Env vars NEVER inject scalar values into
the model and -- as of v1.5 -- never direct the YAML loader to a file
either; the previously honored ``*_CONFIG_FILE`` env-var path-pointer
fallback is gone. A loud DeprecationWarning fires from the plugin when
the deprecated env var is set in the environment so operators are not
silently confused.

``.env`` is dead-letter for the framework's config layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

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
    TestCodeConfig,
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
    # ``test_code`` is REQUIRED -- no default. Missing key triggers the canonical
    # missing-required-field operator-tone error (see docs/ERROR-STYLE.md)
    # via ``_emit_operator_error_for_validation``'s ``missing`` branch in
    # ``cli.py``. One source of truth -- no env var, no CLI flag override.
    test_code: TestCodeConfig = Field(...)

    judge_timeout_seconds: int = 120

    version: int = 2

    host_isolation: Literal['strict', 'passthrough'] = 'strict'

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
        # v1.5: the previous env-var
        # path-pointer fallback was deleted. The env var is inert as a
        # value source. The CLI route threads its resolved path through
        # ``-o mcp_config_file=PATH`` (see ``_runner._build_pytest_args``);
        # the library route reads it from ``[tool.pytest.ini_options]
        # mcp_config_file = PATH`` (see ``_plugin.pytest_configure``).
        # Both routes pass ``yaml_file=`` here; no env var detour.
        sources: list[PydanticBaseSettingsSource] = [init_settings]
        if yaml_file and Path(yaml_file).is_file():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
            )
        sources.append(file_secret_settings)
        return tuple(sources)
