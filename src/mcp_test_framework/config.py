"""Top-level layered configuration via pydantic-settings.

Precedence (CONTEXT.md "Decisions > config precedence" -- LOCKED):

    CLI/init kwargs > env vars > .env > YAML overlay > defaults

In ``pydantic-settings`` the leftmost source in the tuple returned by
``settings_customise_sources`` wins (Pitfall 1 in 01-RESEARCH.md).

YAML overlay path comes ONLY from the ``MCPTF_CONFIG_FILE`` env var (CONTEXT.md
"YAML config discovery" -- no cwd auto-discovery in MVP). Phase 5 will inject
the ``--config PATH`` CLI flag value via ``Config(...)`` kwargs which arrive as
``init_settings`` -- the highest-precedence source.

NOTE on bare-name env routing:
    CONTEXT.md "Env var naming convention" LOCKS bare env-var names (``OLLAMA_BASE_URL``
    rather than ``OLLAMA__BASE_URL``). pydantic-settings' default ``EnvSettingsSource``
    only inspects top-level fields of the settings class; it does NOT walk sub-model
    ``validation_alias`` annotations. To honor the locked decision without setting
    ``env_nested_delimiter``, we ship a tiny custom source (``_BareNameNestedEnvSource``)
    that scans each sub-model's ``validation_alias`` choices against ``os.environ`` and
    emits a nested dict like ``{"ollama": {"base_url": "..."}, ...}``. This source is
    inserted alongside the standard env source so top-level bare names
    (``JUDGE_TIMEOUT_SECONDS``) keep flowing through the standard path. See plan-checker
    iter 1 BLOCKER #1 (resolved Option A) in 01-02-PLAN.md.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic.fields import FieldInfo
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


def _alias_env_names(field: FieldInfo) -> list[str]:
    """Return the list of bare env-var names declared on a sub-model field via
    ``validation_alias=AliasChoices(...)``."""
    alias = field.validation_alias
    if isinstance(alias, AliasChoices):
        return [str(c) for c in alias.choices if isinstance(c, str)]
    if isinstance(alias, str):
        return [alias]
    return []


class _BareNameNestedEnvSource(PydanticBaseSettingsSource):
    """Custom env source that walks sub-model ``BaseModel`` fields and reads bare env
    names declared via ``validation_alias=AliasChoices(...)`` on each sub-field, emitting
    a nested dict for the parent ``BaseSettings`` to merge with other sources.

    Only sub-fields whose annotation is a ``BaseModel`` subclass are walked; top-level
    primitive fields are left to the standard ``EnvSettingsSource``.
    """

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        # Required override; this source does not use the per-field path. Sentinel.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        from pydantic import BaseModel  # local import to avoid leaking at module scope

        result: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            annotation = field.annotation
            if not (isinstance(annotation, type) and issubclass(annotation, BaseModel)):
                continue
            sub_data: dict[str, Any] = {}
            for sub_name, sub_field in annotation.model_fields.items():
                for env_name in _alias_env_names(sub_field):
                    if env_name in os.environ:
                        sub_data[sub_name] = os.environ[env_name]
                        break
            if sub_data:
                result[field_name] = sub_data
        return result


class Config(BaseSettings):
    """Top-level configuration. Frozen for safe session-scoped sharing across async tests."""

    # NOTE: nested-env delimiter intentionally NOT set -- bare env names (per CONTEXT.md
    # lock) are routed to sub-model fields via the custom _BareNameNestedEnvSource below,
    # which honors the validation_alias choices on each sub-model field.
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
            init_settings,                           # CLI flags arrive as kwargs to Config(...)
            _BareNameNestedEnvSource(settings_cls),  # bare env names -> sub-model fields
            env_settings,                            # OS environment (top-level fields)
            dotenv_settings,                         # .env file
        ]
        if yaml_path and Path(yaml_path).is_file():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path)
            )
        sources.append(file_secret_settings)  # docker secrets etc -- below YAML
        return tuple(sources)
