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
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    #
    # The ``validation_alias=AliasChoices("test_code", "sdet")`` accepts BOTH
    # the canonical v1.4 YAML key (``test_code:``) and the legacy v1.3 key
    # (``sdet:``). The legacy key is paired with a DeprecationWarning fired by
    # ``_warn_or_reject_legacy_sdet_key`` below; the alias is removed in v1.5.
    test_code: TestCodeConfig = Field(  # noqa: sdet-rename-shim
        ...,
        validation_alias=AliasChoices("test_code", "sdet"),  # noqa: sdet-rename-shim
    )

    judge_timeout_seconds: int = 120

    version: int = 2

    # Per-tool registry. Runtime semantics are opt-in: only tools listed
    # here (with ``skip != True``) participate in the contract pass.
    tools: dict[str, ToolConfig] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _warn_or_reject_legacy_sdet_key(cls, data: Any) -> Any:  # noqa: sdet-rename-shim
        """Defense-in-depth ambiguity check for the v1.4 sdet->test_code alias.

        Per D-13, the parent ``Config`` carries a ``mode='before'``
        model_validator that rejects raw input containing BOTH ``sdet`` and
        ``test_code`` keys simultaneously. In practice the two operator
        entry points each catch this earlier:

        - YAML load (``Config(yaml_file=PATH)``): ``settings_customise_sources``
          pre-scans the raw YAML via ``_check_legacy_sdet_key_in_yaml`` BEFORE
          the pydantic-settings source pipeline collapses alias keys -- so
          a YAML file with both keys raises before this validator runs.
        - Dict validate (``Config.model_validate({...})``): the
          ``model_validate`` override below pre-scans the input dict for
          the same reason -- ``BaseSettings`` strips alias keys via the
          source pipeline before this ``mode='before'`` validator sees them.

        This validator stays as a backstop for any future code path that
        bypasses both interceptors. The legacy-key DeprecationWarning is
        intentionally NOT emitted here -- the two upstream entry points
        each emit exactly one warning, and emitting from here too would
        double-fire on the dict-validate path (which would violate the
        ``one DeprecationWarning per process`` contract in D-13).
        """
        if not isinstance(data, dict):
            return data
        has_legacy = "sdet" in data
        has_new = "test_code" in data
        if has_legacy and has_new:
            raise ValueError(  # noqa: sdet-rename-shim
                "config.yaml contains both 'sdet' and 'test_code' keys -- "
                "remove the legacy 'sdet' key (deprecated since v1.4, removed in v1.5) "
                "and keep only 'test_code'."
            )
        return data

    @classmethod
    def model_validate(  # noqa: sdet-rename-shim
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> "Config":
        """Pre-scan dict input for the v1.4 sdet->test_code alias before
        pydantic-settings strips alias keys.

        ``BaseSettings`` (unlike plain ``BaseModel``) routes ``model_validate``
        through a source-merging pipeline that collapses ``AliasChoices``
        keys into the canonical field name before ``model_validator(mode=
        'before')`` fires. That means the ``_warn_or_reject_legacy_sdet_key``
        validator above cannot observe both keys simultaneously on the
        dict-validate path -- it sees only the post-merge dict. We therefore
        perform the same legacy-key check here, against the raw input dict,
        before delegating to the base implementation.
        """
        if isinstance(obj, dict):
            has_legacy = "sdet" in obj
            has_new = "test_code" in obj
            if has_legacy and has_new:
                # Build a ValidationError so callers grepping for
                # ValidationError on this path (per RENAME-05 acceptance)
                # see the canonical exception type rather than a bare
                # ValueError.
                from pydantic_core import PydanticCustomError
                from pydantic import ValidationError

                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        {
                            "type": PydanticCustomError(
                                "value_error",
                                (
                                    "config.yaml contains both 'sdet' and 'test_code' keys -- "  # noqa: sdet-rename-shim
                                    "remove the legacy 'sdet' key (deprecated since v1.4, removed in v1.5) "  # noqa: sdet-rename-shim
                                    "and keep only 'test_code'."  # noqa: sdet-rename-shim
                                ),
                            ),
                            "loc": ("test_code",),  # noqa: sdet-rename-shim
                            "input": obj,
                        }
                    ],
                )
            if has_legacy:
                import warnings

                warnings.warn(  # noqa: sdet-rename-shim
                    "config.yaml key 'sdet:' is deprecated since v1.4 and will be removed in v1.5 -- "
                    "use 'test_code:' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
        # Forward to BaseSettings/BaseModel default behavior. ``by_alias`` and
        # ``by_name`` are pydantic 2.11+ kwargs; pass them through only when
        # explicitly set so older callsites that omit them stay byte-compatible.
        kwargs: dict[str, Any] = {}
        if strict is not None:
            kwargs["strict"] = strict
        if from_attributes is not None:
            kwargs["from_attributes"] = from_attributes
        if context is not None:
            kwargs["context"] = context
        if by_alias is not None:
            kwargs["by_alias"] = by_alias
        if by_name is not None:
            kwargs["by_name"] = by_name
        return super().model_validate(obj, **kwargs)

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
            # v1.4 sdet->test_code alias: inspect the raw YAML BEFORE the
            # YAML source's alias-aware key resolution collapses ``sdet`` and
            # ``test_code`` into a single top-level field. Pydantic-settings
            # merges alias choices at source-build time, so the
            # ``_warn_or_reject_legacy_sdet_key`` model_validator only sees
            # the post-merge dict on the YAML path. We pre-scan the raw YAML
            # here so the operator-facing ambiguity error and deprecation
            # warning still fire with the YAML file path available.
            _check_legacy_sdet_key_in_yaml(yaml_file)  # noqa: sdet-rename-shim
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=str(yaml_file))
            )
        sources.append(file_secret_settings)
        return tuple(sources)


def _check_legacy_sdet_key_in_yaml(yaml_file: str) -> None:  # noqa: sdet-rename-shim
    """Pre-scan a YAML file for the v1.4 sdet->test_code alias keys.

    Raises a ``pydantic.ValidationError`` (constructed against ``Config``)
    if BOTH ``sdet`` and ``test_code`` top-level keys are present. Emits a
    once-per-process ``DeprecationWarning`` if only the legacy ``sdet``
    key is present.

    Called from ``settings_customise_sources`` so the check runs against
    the raw YAML dict, before pydantic-settings' ``YamlConfigSettingsSource``
    collapses alias choices into a single field key. We raise
    ``ValidationError`` (not ``ValueError``) so the existing
    ``_emit_operator_error_for_validation`` mapper in ``cli.py`` catches
    this on the same code path as every other config-load failure.

    Silently returns on YAML parse error or non-dict root -- the YAML
    source itself will surface those errors with its own diagnostics.
    """
    import yaml as _yaml  # local import keeps top-of-file imports minimal

    try:
        with open(yaml_file, encoding="utf-8") as fp:
            raw = _yaml.safe_load(fp)
    except (OSError, _yaml.YAMLError):
        return
    if not isinstance(raw, dict):
        return
    has_legacy = "sdet" in raw
    has_new = "test_code" in raw
    if has_legacy and has_new:
        from pydantic import ValidationError
        from pydantic_core import PydanticCustomError

        raise ValidationError.from_exception_data(  # noqa: sdet-rename-shim
            title="Config",
            line_errors=[
                {
                    "type": PydanticCustomError(
                        "value_error",
                        (
                            "config.yaml contains both 'sdet' and 'test_code' keys -- "  # noqa: sdet-rename-shim
                            "remove the legacy 'sdet' key (deprecated since v1.4, removed in v1.5) "  # noqa: sdet-rename-shim
                            "and keep only 'test_code'."  # noqa: sdet-rename-shim
                        ),
                    ),
                    "loc": ("test_code",),  # noqa: sdet-rename-shim
                    "input": raw,
                }
            ],
        )
    if has_legacy:
        import warnings

        warnings.warn(  # noqa: sdet-rename-shim
            "config.yaml key 'sdet:' is deprecated since v1.4 and will be removed in v1.5 -- "
            "use 'test_code:' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
