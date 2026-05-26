"""Cross-cutting Pydantic config sub-models.

Only ``Config`` and its sub-models live here. Domain models
(``ValidationIssue``, ``JudgeResult``) stay in their owning modules.

Each sub-model is independently frozen via ``ConfigDict(frozen=True)``:
``frozen=True`` on a parent ``BaseSettings`` does NOT propagate to nested
``BaseModel`` fields, so each nested model needs its own marker.

Each env-var-mapped field carries an explicit
``validation_alias=AliasChoices(<bare env name>, <field name>)`` annotation
so that bare env names (e.g. ``OLLAMA_BASE_URL``) route to the correct
sub-model field WITHOUT relying on ``env_nested_delimiter`` (which would
force ``OLLAMA__BASE_URL`` instead). The field name is included as a second
alias choice -- with ``populate_by_name=True`` enabled -- so YAML overlays
(emitted as ``ollama.base_url`` etc.) and init kwargs continue to populate
the model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from mcp_test_framework.contracts._buckets import BucketName
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
    """Per-tool config registry entry.

    Keyed off tool name in ``Config.tools: dict[str, ToolConfig]``. Tools
    with no entry use defaults. ``extra="forbid"`` makes typos (e.g.
    ``srtip:`` instead of ``skip:``) fail at load time.

    ``setup`` and ``depends_on`` are reserved ``Optional`` fields: typed in
    the model so stateful-testing extensions can light them up additively
    without a schema migration. They are ignored at runtime today.

    NOT env-routable: no ``validation_alias=AliasChoices(...)`` on any
    field. The dynamic ``dict[str, ToolConfig]`` shape doesn't generalize
    cleanly through a bare-env-name source, and YAML/init are sufficient
    for the use case.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    skip: bool = False
    skip_reason: Optional[str] = None
    call_arguments: dict[str, Any] = Field(default_factory=dict)
    judges: Optional[list[str]] = None
    setup: Optional[Any] = None  # reserved; runtime no-op
    depends_on: Optional[list[str]] = None  # reserved; runtime no-op
    skip_buckets: list[BucketName] = Field(
        default_factory=list,
        description=(
            "Test buckets to opt out of for this tool. Valid values: "
            "'schema', 'judge', 'output'. Skipped buckets are filtered "
            "at parametrize collection time (matches v1.1.1 whole-tool "
            "skip pattern) -- they do not appear in `pytest --collect-only` "
            "output and are not rendered as runtime SKIPPED rows. "
            "Empty list (default) = no per-bucket skipping; use `skip: true` "
            "for whole-tool skip. Setting both `skip: true` and a non-empty "
            "`skip_buckets` is rejected at load time as redundant."
        ),
    )

    @field_validator("skip_buckets", mode="after")
    @classmethod
    def _no_duplicate_buckets(cls, v: list[BucketName]) -> list[BucketName]:
        """Reject duplicate bucket names in ``skip_buckets``.

        Pydantic's ``Literal`` validation accepts duplicates by default
        (each element passes the per-element check). Downstream consumers
        (``_count_bucket_skips``, ``--explain`` renderer) treat the field
        as a multiset, so ``skip_buckets=["output", "output"]`` would
        silently inflate ``Bucket skips: N`` and emit duplicate
        ``bucket=output: ...`` rows. A duplicate is almost certainly a
        typo, not deliberate intent; fail loud at config load with an
        operator-tone message (matches docs/ERROR-STYLE.md).
        """
        if len(set(v)) != len(v):
            raise ValueError(
                "skip_buckets contains duplicate bucket name(s); each "
                "bucket may appear at most once. valid values: "
                "'schema', 'judge', 'output'."
            )
        return v

    @field_validator("judges", mode="after")
    @classmethod
    def _validate_judge_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Each judge ID must resolve against the rubric registry.

        None (default) is permitted -- means "run all available rubrics".
        Empty list ``[]`` is also permitted -- means "explicit opt-out, run
        no rubrics on this tool". The empty-vs-None distinction is
        meaningful and tested.
        """
        if v is None:
            return v
        for rubric_id in v:
            if rubric_id not in RUBRIC_IDS:
                # Delegate to resolve_rubric_id for the canonical error
                # message (single source).
                resolve_rubric_id(rubric_id)
        return v

    @model_validator(mode="after")
    def _skip_buckets_not_with_whole_tool_skip(self) -> "ToolConfig":
        """``skip=True`` and a non-empty ``skip_buckets`` are mutually exclusive.

        ``skip: true`` is whole-tool: every bucket is already skipped, so
        layering an additional per-bucket opt-out is redundant intent and
        leaves the operator unsure which lever the framework honored. Fail
        loud at config load with an operator-tone three-part message rather
        than silently picking precedence.

        WR-06 (phase 33 review): this validator runs BEFORE
        ``_skip_requires_reason``. When an operator writes
        ``skip=True, skip_buckets=["output"]`` with no skip_reason, both
        rules are violated; surfacing the mutual-exclusion message first
        steers the operator to drop one of the two levers in one round
        trip rather than two (drop skip_buckets first, then -- if they
        kept ``skip: true`` -- supply skip_reason on the next attempt).
        """
        if self.skip and self.skip_buckets:
            raise ValueError(
                "skip=true and skip_buckets are mutually exclusive\n"
                "\n"
                "skip=true is whole-tool: every bucket is already skipped.\n"
                "layering skip_buckets on top is redundant intent and the "
                "framework will not silently pick which lever wins.\n"
                "\n"
                "next: keep skip=true to disable every bucket, OR remove "
                "skip and use skip_buckets alone to disable named buckets."
            )
        return self

    @model_validator(mode="after")
    def _skip_requires_reason(self) -> "ToolConfig":
        """``skip=True`` MUST come with non-empty ``skip_reason``.

        The reason surfaces in pytest output via ``pytest.skip(reason=...)``.
        An empty/whitespace-only reason defeats that requirement at the
        source, so we raise at load time rather than letting a silent skip
        propagate.
        """
        if self.skip and not (self.skip_reason and self.skip_reason.strip()):
            raise ValueError(
                "skip=True requires a non-empty skip_reason "
                "(the reason surfaces in pytest skip output)"
            )
        return self


class HomelabProxmoxConfig(BaseModel):
    """Proxmox-specific knobs for test-code dogfood scenarios.

    Currently exposes only ``dogfood_vmid_range`` -- the reserved VMID
    window the framework's VM-lifecycle dogfood scenario allocates
    from. Default avoids collision with typical operator-owned ranges.
    Override in ``config.yaml`` if your cluster reserves 9990-9999 for
    something else.

    Not env-routable (mirrors ToolConfig): no
    ``validation_alias=AliasChoices(...)``. ``extra="forbid"`` makes
    typos (e.g. ``dogfood_vmd_range``) fail loudly at config load.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    dogfood_vmid_range: tuple[int, int] = Field(
        default=(9990, 9999),
        description=(
            "Reserved VMID range for dogfood scenario VMs as (lo, hi). "
            "The framework only creates / deletes VMs within this range."
        ),
    )

    @field_validator("dogfood_vmid_range", mode="after")
    @classmethod
    def _validate_dogfood_vmid_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        lo, hi = v
        if lo > hi:
            raise ValueError(
                f"dogfood_vmid_range {v!r} must be (lo, hi) with lo <= hi"
            )
        if lo < 100 or hi > 999_999_999:
            raise ValueError(
                f"dogfood_vmid_range {v!r} out of Proxmox bounds [100, 999999999]"
            )
        return v


class HomelabConfig(BaseModel):
    """Container for homelab-specific scenario config domains.

    v1.3 ships only ``proxmox``; future homelab.* domains (ansible,
    terraform, etc.) extend this model additively.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    proxmox: HomelabProxmoxConfig = Field(default_factory=HomelabProxmoxConfig)


class TestCodeConfig(BaseModel):
    """test-code codegen + fixture surface knobs.

    Currently exposes only ``generated_root`` -- the on-disk directory the
    framework writes generated test-code classes into (via ``gen-test-classes``)
    and loads them from (via the ``mcp_session`` fixture). The field is
    REQUIRED with no default: the framework refuses to silently invent a
    path to write Python code into or load Python code from, matching the
    fail-loud posture on config absence (see docs/ERROR-STYLE.md).

    No env routing (mirrors HomelabProxmoxConfig): no
    ``validation_alias=AliasChoices(...)``. ``MCPTF_GENERATED_ROOT`` is
    deliberately NOT a recognized env var -- one source of truth is
    ``config.yaml``.

    Path resolution: if the value is not absolute, it is interpreted
    relative to the current working directory at the time the config is
    loaded. Operators using a worktree should set an absolute path or
    change directory before invoking the CLI.
    """

    # ``__test__ = False`` tells pytest NOT to collect this Pydantic config
    # model as a test class. Without it, pytest's default discovery sees the
    # leading ``Test`` in the class name and emits
    # ``PytestCollectionWarning: cannot collect test class 'TestCodeConfig'
    # because it has a __init__ constructor`` for every module that imports
    # it. The flag is a no-op for non-pytest callers.
    __test__ = False

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    generated_root: Path = Field(
        ...,
        description=(
            "On-disk directory the framework writes generated test-code "
            "classes into and loads them from. REQUIRED -- the framework "
            "will not silently invent a path. Recommended convention: "
            "tests/test_code/_generated/ (the framework recommends this in "
            "docs but does not enforce it)."
        ),
    )

    @field_validator("generated_root", mode="before")
    @classmethod
    def _reject_empty_generated_root(cls, v: object) -> object:
        """Reject empty-string values explicitly so the operator-tone error
        path distinguishes 'forgot to set the key' (missing) from 'set the
        key to nothing' (invalid value). Both end up as exit 2 operator-tone
        errors (see docs/ERROR-STYLE.md), but the field-validator path lets
        the operator see which mistake they made.
        """
        if isinstance(v, str) and v.strip() == "":
            raise ValueError(
                "test_code.generated_root must not be an empty string; "
                "set it to a directory path such as 'tests/test_code/_generated' "
                "or remove the key entirely to get the missing-required-field error"
            )
        return v
