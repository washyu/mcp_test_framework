# Phase 1: Foundation & Pure-Data Core — Research

**Researched:** 2026-05-04
**Domain:** Python project bootstrap (uv + pyproject.toml), pytest-asyncio strict-mode config, ruff import-ban enforcement, `pydantic-settings` layered config with YAML + frozen model, `jsonschema` Draft 2020-12 structural validation
**Confidence:** HIGH on stack/versions (pre-validated in `.planning/research/STACK.md`), HIGH on pytest-asyncio + jsonschema usage, MEDIUM-HIGH on `pydantic-settings` precedence customization, **MEDIUM** on the ruff `banned-api` enforcement story (a documented gap requires a belt-and-suspenders approach — see Pitfall section).

## Summary

This phase has **zero I/O** — only project skeleton + two pure-data modules (`config.py`/`models.py` and `schema_validator.py`) plus their unit tests. Every dependency choice and version was already locked by `.planning/research/STACK.md`; the user's Phase 1 CONTEXT.md narrowed the implementation surface further (frozen `Config`, JSON-Pointer-style `path`, ruff `TID251` for the black-box rule, no YAML auto-discovery, `tests/unit/` for Phase 1 unit tests). This research therefore focuses on **usage patterns and exact code shapes** the planner can lift verbatim into tasks — not version selection.

Three findings deserve flagging up-front because they are the load-bearing facts that change how Phase 1 should be planned:

1. **`pydantic-settings`'s `settings_customise_sources` precedence is "leftmost in the returned tuple wins."** To get `CLI > env > .env > YAML > defaults` the tuple must be `(init_settings, env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls), file_secret_settings)`. CONTEXT.md's lock that env > YAML inverts the spec text — this matches `pydantic-settings`'s native ordering when env is placed before the YAML source.
2. **`jsonschema.ValidationError.json_path`** returns a JSONPath-style string (e.g., `$.properties.foo.description`) — **NOT** the JSON-Pointer-style string the user locked in CONTEXT.md (`/properties/foo/description`). To honor that decision, the `path` field on `ValidationIssue` must be built by `"/".join(str(p) for p in error.absolute_path)` with a leading `/`, NOT by reading `error.json_path` directly. This is a one-line consequence but a non-obvious one.
3. **Ruff's `TID251` `banned-api` does NOT recursively cover submodules.** Banning `"homelab_mcp"` will catch `import homelab_mcp` and `from homelab_mcp import X` but **NOT** `from homelab_mcp.client import X` or `from homelab_mcp.server import Y`. Since `homelab-mcp`'s internal layout is a moving target the framework deliberately doesn't know, a single-key `banned-api` entry is insufficient. Recommendation: pair `banned-api` with a tiny `conftest.py`-level `sys.modules` guard as belt-and-suspenders (see Common Pitfalls #4).

**Primary recommendation:** Plan Phase 1 as **6 tasks** (one per success criterion) with the bootstrap (`pyproject.toml` + `uv sync`) as task 1, the lint enforcement as task 2, the pure-data modules + tests as tasks 3–5, and the example config files as task 6. Every code excerpt in this research is citation-backed and can be referenced verbatim from plan tasks.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Dependency declaration & lockfile | Build/Tooling (`pyproject.toml` + `uv.lock`) | — | uv 0.11.x is canonical; `[project.dependencies]` for runtime, `[dependency-groups].dev` (PEP 735) for tooling |
| Test discovery + async loop policy | Build/Tooling (`[tool.pytest.ini_options]`) | — | pytest-asyncio strict mode is configured at the build layer; tests opt-in via marker |
| Black-box import enforcement | Build/Tooling (ruff config) | Runtime (conftest sys.modules guard, optional) | ruff covers static analysis; conftest covers dynamic imports |
| Configuration loading | Library code (`config.py` + `models.py`) | — | `pydantic-settings.BaseSettings` subclass; sub-models in `models.py` |
| Schema structural validation | Library code (`schema_validator.py`) | — | Pure function over `mcp.types.Tool`; uses `jsonschema.validators.validator_for` |
| Validation issue model | Library code (`schema_validator.py`) | — | Per CONTEXT.md D-02: `ValidationIssue` is domain-local, not in `models.py` |
| Example config docs | Documentation (`.env.example`, `config.example.yaml`) | — | Static text files at repo root |

## Standard Stack

> All versions pre-validated in `.planning/research/STACK.md` (researched 2026-05-04 against PyPI). This phase declares the runtime + dev deps; Phase 2/3 add `mcp`, `httpx` is already pulled in by `mcp` but should be declared explicitly.

### Phase 1 Runtime Dependencies (declare in `[project.dependencies]`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | `>=1.27` | Provides the `mcp.types.Tool` shape that `validate_tool_schema(tool: Tool)` accepts as input — Phase 1 imports the type even though no I/O happens here `[VERIFIED: STACK.md]` | Per CONTEXT.md "Integration Points": Phase 1 should accept the SDK type now so Phase 4 needs no translation layer |
| `pydantic` | `>=2.13,<3` | `BaseModel` for `ValidationIssue`, sub-models `OllamaConfig`/`McpServerConfig`/`TargetConfig` | `mcp` already requires `pydantic>=2.11,<3` (transitive constraint) `[CITED: STACK.md]` |
| `pydantic-settings[yaml]` | `>=2.14` | `BaseSettings` for `Config`, `YamlConfigSettingsSource` for the YAML overlay | The `[yaml]` extra pulls `pyyaml` automatically — do **not** declare `pyyaml` directly `[CITED: STACK.md]` |
| `jsonschema` | `>=4.26` | `validator_for` + `Draft202012Validator` + `iter_errors` for the 7 structural checks | Reference Python implementation; pre-validated in STACK.md `[CITED: STACK.md]` |

### Phase 1 Dev Dependencies (declare in `[dependency-groups].dev`)

| Library | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=9.0` | Test runner |
| `pytest-asyncio` | `>=1.3` | Async test integration (no async tests in Phase 1, but configured here so Phase 4 inherits the policy) |
| `ruff` | `>=0.8` | Linter + formatter; carries `flake8-tidy-imports` `TID251` for SETUP-03 |

**Deferred to later phases (do NOT declare in Phase 1):** `httpx` (Phase 3), `typer` (Phase 5), `homelab-mcp` (per CONTEXT.md decision: never a dep — the lint rule ships even with it absent).

### Build System

`hatchling` (whatever `uv init` produced — already in the existing `pyproject.toml`). Don't switch backends.

### Installation Commands (verified)

```bash
# Runtime deps
uv add "mcp>=1.27" "pydantic>=2.13,<3" "pydantic-settings[yaml]>=2.14" "jsonschema>=4.26"

# Dev deps -- writes to [dependency-groups].dev (PEP 735, the canonical 2026 location)
uv add --dev "pytest>=9.0" "pytest-asyncio>=1.3" "ruff>=0.8"
```

`[VERIFIED: docs.astral.sh/uv/concepts/projects/dependencies — "uv uses the [dependency-groups] table (as defined in PEP 735) for declaration of development dependencies." `tool.uv.dev-dependencies` is "explicitly marked as legacy"]`

### Alternatives Considered (rejected for Phase 1)

| Instead of | Could Use | Tradeoff (and why rejected) |
|------------|-----------|-----------------------------|
| `pydantic-settings` YAML | Hand-rolled `yaml.safe_load` overlay | More code, more bugs, no precedence story — STACK.md's recommendation supersedes the spec's hand-roll |
| ruff `TID251` | flake8 `flake8-tidy-imports` plugin | We need ruff anyway for format/lint; running two linters is redundant `[CITED: CONTEXT.md decision]` |
| `[project.optional-dependencies]` `dev` | `[dependency-groups].dev` | `optional-dependencies` is for **published** library extras (e.g. `pandas[plot]`) — leaks dev tools into PyPI metadata when this package is eventually published `[VERIFIED: uv docs]` |

## Architecture Patterns

### Recommended Project Structure (after Phase 1 lands)

```
mvp_test_framework/
├── .python-version              # exists -- 3.14
├── pyproject.toml               # rewritten in Phase 1
├── uv.lock                      # generated by `uv sync` -- COMMIT it
├── .env.example                 # NEW (Phase 1, DOCS-02)
├── config.example.yaml          # NEW (Phase 1, DOCS-02)
├── .gitignore                   # add .env, .venv, __pycache__, etc.
├── src/
│   └── mcp_test_framework/
│       ├── __init__.py          # NEW (empty or version export)
│       ├── config.py            # NEW (Phase 1, CORE-01)
│       ├── models.py            # NEW (Phase 1, CORE-01)
│       └── schema_validator.py  # NEW (Phase 1, CORE-02)
└── tests/
    ├── __init__.py              # NEW (empty)
    ├── conftest.py              # NEW -- minimal in Phase 1; grows in Phase 4
    └── unit/
        ├── __init__.py          # NEW (empty)
        ├── test_config.py       # NEW (Phase 1)
        └── test_schema_validator.py  # NEW (Phase 1)
```

**NOT created in Phase 1** (per CONTEXT.md scope and roadmap):
- `src/mcp_test_framework/cli.py` (Phase 5)
- `src/mcp_test_framework/mcp_client.py` (Phase 2)
- `src/mcp_test_framework/ollama_judge.py` (Phase 3)
- `src/mcp_test_framework/judge_protocol.py` (Phase 3)
- `src/mcp_test_framework/fixtures.py` (Phase 4)
- `tests/test_homelab_list_registered_servers.py` (Phase 4)

**Delete during Phase 1:** `main.py` (existing hello-world stub — nothing depends on it, see CONTEXT.md "Reusable Assets").

### Pattern 1: `pyproject.toml` — Complete Phase 1 Shape

Code shape verified against `.planning/research/STACK.md` (uv installation block) + uv.docs (dependency-groups) + `concepts.html` of pytest-asyncio.

```toml
# pyproject.toml -- Phase 1 target shape
[project]
name = "mvp-test-framework"           # existing -- hyphen, distinct from package dir
version = "0.1.0"
description = "Pytest framework for testing MCP servers end-to-end."
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "mcp>=1.27",
    "pydantic>=2.13,<3",
    "pydantic-settings[yaml]>=2.14",
    "jsonschema>=4.26",
]

[project.scripts]
# Wired in Phase 5 -- harmless to register the entry point now.
# Lands during Phase 5; remove this line in Phase 1 if you want to defer.
# mcp-test-framework = "mcp_test_framework.cli:app"

[dependency-groups]                   # PEP 735 -- canonical 2026 location
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.3",
    "ruff>=0.8",
]

[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]                 # picks up tests/unit/ AND future tests/

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "I", "TID"]       # TID = flake8-tidy-imports

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"homelab_mcp" = { msg = "Do not import homelab_mcp -- it is a black-box subprocess under test (see PROJECT.md). Drive it via mcp.client.stdio.stdio_client only." }

[build-system]
# Whatever `uv init` produced. Leave as-is.
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Sources:**
- pytest-asyncio config keys: STACK.md §"Pytest-asyncio Configuration" + Context7 `/pytest-dev/pytest-asyncio` (cited in STACK.md sources)
- `[dependency-groups]` is canonical: `[VERIFIED: docs.astral.sh/uv/concepts/projects/dependencies]`
- ruff `TID251` configuration syntax: `[VERIFIED: docs.astral.sh/ruff/settings/#lint_flake8-tidy-imports_banned-api]`

### Pattern 2: `models.py` — Cross-Cutting Config Sub-Models

Per CONTEXT.md D-02: only `Config` and its sub-models live in `models.py`. `ValidationIssue` and `JudgeResult` stay domain-local.

```python
# src/mcp_test_framework/models.py
from pydantic import BaseModel, Field, ConfigDict


class OllamaConfig(BaseModel):
    """Ollama judge configuration."""
    model_config = ConfigDict(frozen=True)

    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3.6:latest"
    timeout_seconds: int = Field(default=120, ge=1)


class McpServerConfig(BaseModel):
    """MCP server subprocess configuration."""
    model_config = ConfigDict(frozen=True)

    command: str = "homelab-mcp"
    args: list[str] = Field(default_factory=list)


class TargetConfig(BaseModel):
    """Target tool to run all tests against."""
    model_config = ConfigDict(frozen=True)

    tool_name: str = "list_registered_servers"
```

`[CITED: pydantic.dev/docs/validation/latest/api/pydantic/config — "frozen": "Whether models are faux-immutable, i.e. whether __setattr__ is allowed, and also generates a __hash__() method for the model."]`

### Pattern 3: `config.py` — `BaseSettings` with Layered Precedence

The user-locked precedence is `CLI > env > YAML > default` (CONTEXT.md decisions), and `pydantic-settings` source ordering is **leftmost in tuple wins**. To support the env-var-driven YAML path (CONTEXT.md "YAML config discovery": `MCPTF_CONFIG_FILE` env var), the YAML source instantiation reads the env var inside `settings_customise_sources`.

```python
# src/mcp_test_framework/config.py
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from mcp_test_framework.models import (
    OllamaConfig,
    McpServerConfig,
    TargetConfig,
)


class Config(BaseSettings):
    """Top-level configuration. Frozen for safe session-scoped sharing."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",   # OLLAMA__BASE_URL etc, plus flat aliases
        extra="ignore",
    )

    # Spec-verbatim env var names (CONTEXT.md "Env var naming convention")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)

    judge_timeout_seconds: int = 120  # spec env var; mirrors ollama.timeout_seconds for compat

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
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path))
        sources.append(file_secret_settings)  # docker secrets etc -- below YAML
        return tuple(sources)
```

**Sources for the precedence pattern:**
- `[VERIFIED: pydantic.dev/docs/validation/latest/concepts/pydantic_settings — "Position matters: leftmost sources win."]`
- `[VERIFIED: github.com/pydantic/pydantic-settings/issues/259 — runtime YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file) pattern]`
- `[VERIFIED: pydantic v2 ConfigDict frozen field — pydantic.dev/docs/validation/latest/api/pydantic/config — frozen makes the model faux-immutable and hashable]`

**Per CONTEXT.md "YAML config discovery":** No cwd auto-discovery in MVP. The `MCPTF_CONFIG_FILE` env var is the only way Phase 1 receives a YAML path; the `--config PATH` CLI flag arrives in Phase 5 and gets injected via `Config(...)` kwargs which `init_settings` picks up as the highest-precedence source.

### Pattern 4: `schema_validator.py` — The 7 Structural Checks

Spec §`schema_validator.py` lists 7 checks. CONTEXT.md D-01 locks every issue at `severity="error"`; D-02 keeps the field for forward-compat; CONTEXT.md "ValidationIssue.path representation" locks JSON-Pointer-style strings.

**Critical:** `error.json_path` returns JSONPath syntax (`$.properties.foo`), NOT JSON-Pointer syntax. To produce `/properties/foo/description`, build the path from `error.absolute_path` (a `collections.deque` of components).

```python
# src/mcp_test_framework/schema_validator.py
from __future__ import annotations

from typing import Any, Literal

from jsonschema.validators import validator_for, Draft202012Validator
from mcp.types import Tool
from pydantic import BaseModel


class ValidationIssue(BaseModel):
    """A single structural-validation finding for an MCP tool schema."""

    severity: Literal["error"]   # D-02: typed literal so adding "warning" is a typed change
    path: str                    # JSON-Pointer-style: "" for root, "/inputSchema/properties/foo" otherwise
    message: str


def _pointer_from_deque(absolute_path) -> str:
    """Convert jsonschema's absolute_path (collections.deque) to a JSON Pointer string."""
    if not absolute_path:
        return ""
    # JSON Pointer per RFC 6901: components joined by "/" with leading "/"
    parts = [str(p).replace("~", "~0").replace("/", "~1") for p in absolute_path]
    return "/" + "/".join(parts)


def validate_tool_schema(tool: Tool) -> list[ValidationIssue]:
    """Run the 7 deterministic structural checks from spec §schema_validator.py.

    Returns an empty list if the tool's schema is structurally valid.
    """
    issues: list[ValidationIssue] = []

    # Check 1: non-empty name
    if not getattr(tool, "name", None):
        issues.append(ValidationIssue(severity="error", path="/name", message="Tool name is empty"))

    # Check 2: non-empty description
    if not getattr(tool, "description", None):
        issues.append(ValidationIssue(severity="error", path="/description", message="Tool description is empty"))

    schema: dict[str, Any] | None = getattr(tool, "inputSchema", None)

    # Check 3: inputSchema is a valid JSON Schema document
    if not isinstance(schema, dict):
        issues.append(ValidationIssue(
            severity="error",
            path="/inputSchema",
            message="inputSchema is missing or not a JSON object",
        ))
        return issues  # cannot continue without a schema dict

    # validator_for auto-detects draft from $schema; falls back to latest if absent.
    ValidatorCls = validator_for(schema, default=Draft202012Validator)
    try:
        ValidatorCls.check_schema(schema)
    except Exception as exc:
        issues.append(ValidationIssue(
            severity="error",
            path="/inputSchema",
            message=f"inputSchema is not a valid JSON Schema: {exc}",
        ))
        return issues

    # Check 4: inputSchema.type == "object"
    if schema.get("type") != "object":
        issues.append(ValidationIssue(
            severity="error",
            path="/inputSchema/type",
            message=f'inputSchema.type must be "object" (got {schema.get("type")!r})',
        ))

    # Check 5: required ⊆ properties
    required = schema.get("required", []) or []
    properties = schema.get("properties", {}) or {}
    for name in required:
        if name not in properties:
            issues.append(ValidationIssue(
                severity="error",
                path=f"/inputSchema/required/{name}",
                message=f'Required field "{name}" is not declared in properties',
            ))

    # Checks 6 + 7: every property has description AND (type | oneOf | anyOf)
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            issues.append(ValidationIssue(
                severity="error",
                path=f"/inputSchema/properties/{prop_name}",
                message="Property schema must be an object",
            ))
            continue
        if not prop_schema.get("description"):
            issues.append(ValidationIssue(
                severity="error",
                path=f"/inputSchema/properties/{prop_name}/description",
                message=f'Property "{prop_name}" is missing a description',
            ))
        if not any(k in prop_schema for k in ("type", "oneOf", "anyOf")):
            issues.append(ValidationIssue(
                severity="error",
                path=f"/inputSchema/properties/{prop_name}",
                message=f'Property "{prop_name}" has no type / oneOf / anyOf',
            ))

    return issues
```

**Sources:**
- `validator_for(schema, default=...)` returns the correct draft based on `$schema`, falls back to `default`: `[VERIFIED: python-jsonschema.readthedocs.io/en/latest/api/jsonschema/validators]`
- `error.absolute_path` is a `collections.deque` of path components; `error.json_path` is JSONPath ($-prefixed): `[VERIFIED: python-jsonschema.readthedocs.io/en/stable/errors]`
- `Draft202012Validator.check_schema(schema)` validates that the schema itself is a well-formed JSON Schema (used for check #3): `[VERIFIED: jsonschema docs, Draft202012Validator class]`
- 7 checks list: `[CITED: docs/mcp_test_framework_mvp_spec.md §schema_validator.py]`

### Pattern 5: `tests/conftest.py` — Belt-and-Suspenders Black-Box Guard (optional)

Recommended belt for Pitfall #4 (ruff `TID251` does not catch submodule imports):

```python
# tests/conftest.py
import sys


def pytest_configure(config) -> None:
    """Fail-fast if anything importable from homelab_mcp leaks into the test process."""
    leaked = [name for name in sys.modules if name == "homelab_mcp" or name.startswith("homelab_mcp.")]
    if leaked:
        raise RuntimeError(
            f"Black-box rule violated: homelab_mcp modules in sys.modules at test start: {leaked}. "
            f"The framework must drive homelab-mcp via stdio_client only -- never import."
        )
```

This is a runtime check at test-session start. It is cheap, catches the submodule-import gap that `TID251` misses, and produces a clear diagnostic. **Recommendation:** ship this as a planner task for SETUP-03 belt-and-suspenders coverage.

### Anti-Patterns to Avoid

- **Anti-pattern: declaring `pyyaml` directly.** Already pulled in by `pydantic-settings[yaml]`; declaring it twice risks version drift. `[CITED: STACK.md "What NOT to Use"]`
- **Anti-pattern: `[project.optional-dependencies]` `dev = [...]`.** Leaks dev deps into PyPI metadata. Use `[dependency-groups].dev` instead. `[VERIFIED: docs.astral.sh/uv]`
- **Anti-pattern: hand-rolling YAML overlay over env vars.** `pydantic-settings`'s `settings_customise_sources` is the supported precedence mechanism — hand-rolling is more code, more bugs, no help. `[CITED: STACK.md alternatives]`
- **Anti-pattern: using `error.json_path` for the `path` field.** Returns `$.properties.foo` (JSONPath), not the JSON-Pointer string the user locked. Use `_pointer_from_deque(error.absolute_path)`.
- **Anti-pattern: applying `@pytest.mark.asyncio` to Phase 1 tests.** `test_config.py` and `test_schema_validator.py` test pure synchronous functions — strict mode does NOT require any marker on sync tests, only on async ones. `[VERIFIED: pytest-asyncio.readthedocs.io/en/stable/concepts.html — "Test functions and fixtures without these markers and decorators will not be handled by pytest-asyncio."]`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Layered config (env + .env + YAML + defaults + CLI override) | Manual `os.environ` reads + `yaml.safe_load` + dict-merge | `pydantic-settings.BaseSettings` + `settings_customise_sources` | Precedence is configurable, types are validated, `.env` is built-in, no merge bugs |
| Frozen / hashable config model | `frozen=True` `dataclass` + manual `__hash__` | Pydantic `ConfigDict(frozen=True)` | `__hash__` is auto-generated; validation runs on construction; works with Pydantic features (`.model_dump()`, `.model_validate_json()`) `[CITED: pydantic config docs]` |
| JSON Schema draft selection | Hardcode `Draft202012Validator` everywhere | `jsonschema.validators.validator_for(schema, default=Draft202012Validator)` | Auto-detects draft from `$schema`; falls back gracefully `[VERIFIED: jsonschema validators API]` |
| Error path formatting | Compose `path` strings by hand inside each check | `error.absolute_path` (deque) → join with `/` | jsonschema gives you the path for free; hand-rolled paths drift |
| Black-box import guard | Custom AST walker / grep / git pre-commit | `ruff` `TID251` (`flake8-tidy-imports.banned-api`) + `sys.modules` belt | ruff is the project's lint anyway; one-line config; documented msg surfaces in lint output `[VERIFIED: docs.astral.sh/ruff]` |
| Dev-dependency declaration | `[tool.uv].dev-dependencies` (legacy) or `[project.optional-dependencies].dev` (wrong purpose) | `[dependency-groups].dev` (PEP 735) | Canonical, future-proof, what `uv add --dev` writes `[VERIFIED: docs.astral.sh/uv]` |

**Key insight:** Phase 1 is small enough that hand-rolling each piece would compile. The cost is in **Phase 4+** when 8 tests share a Config and one of them mutates it, or when a tool ships a `$schema: "draft-07"` and your hardcoded `Draft202012Validator` rejects it. Use the libraries — they exist precisely for this kind of phase.

## Common Pitfalls

### Pitfall 1: `pydantic-settings` Source Ordering Inverted

**What goes wrong:** Developer writes `return (YamlConfigSettingsSource(...), env_settings, init_settings, ...)` thinking that order matches the spec text "YAML overlays env." YAML now wins over env AND CLI.

**Why it happens:** The spec's prose ("YAML overlays env vars") sounds like "YAML is on top" — but `pydantic-settings`'s tuple is leftmost-wins, and the user-locked precedence is `CLI > env > YAML > default`. The ordering must be `(init_settings, env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls), file_secret_settings)`.

**How to avoid:**
- Plan a **dedicated `test_config_precedence` unit test** that sets the same field via init kwarg, env var, .env, and a YAML file, and asserts each higher-priority source wins (CONTEXT.md success criterion 4 essentially mandates this).
- Document the source ordering with a comment in `config.py` matching the precedence statement.

**Warning signs:** A YAML value appears in `Config(...)` even when the same name is set in `os.environ`. Test that does `monkeypatch.setenv("OLLAMA_MODEL", "X")` doesn't see "X" in `Config().ollama.model`.

`[VERIFIED: pydantic.dev concepts/pydantic_settings -- "leftmost sources win"]`

### Pitfall 2: `error.json_path` vs `error.absolute_path` Confusion

**What goes wrong:** `path` field on `ValidationIssue` ends up as `$.properties.foo` (JSONPath) when the user locked `/properties/foo` (JSON-Pointer).

**Why it happens:** `jsonschema` gives both. `json_path` is the friendlier string, but it's JSONPath, not JSON-Pointer.

**How to avoid:** Use `error.absolute_path` (a `collections.deque`) and join components with `/`. See `_pointer_from_deque` in Pattern 4.

**Warning signs:** Test asserts `issue.path == "/inputSchema/properties/foo/description"` and gets `$.inputSchema.properties.foo.description`.

`[VERIFIED: python-jsonschema.readthedocs.io/en/stable/errors]`

### Pitfall 3: pytest-asyncio Default `loop_scope` Drift

**What goes wrong:** Phase 1 ships `asyncio_default_fixture_loop_scope = "session"` but Phase 4 forgets to mark async tests with `@pytest.mark.asyncio(loop_scope="session")` — fixtures in session loop, tests in function loop, anyio cancel-scope error on teardown.

**Why it happens:** This is Pitfall 1 from the project-level `PITFALLS.md`. Phase 1 sets up the *fixture* default but tests need explicit marker scope too.

**How to avoid:**
- Phase 1 sets up the **config** correctly (`asyncio_default_fixture_loop_scope = "session"`) — this is a Phase 1 deliverable.
- Document for Phase 4: **every** `@pytest.mark.asyncio` MUST include `(loop_scope="session")`.
- Phase 1 has zero async tests, so this pitfall doesn't bite Phase 1 directly — it's a deferred concern.

**Warning signs:** Tests fail in Phase 4 with `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` even though the config block looks right.

`[CITED: PITFALLS.md Pitfall 1; STACK.md Pytest-asyncio Configuration]`

### Pitfall 4: Ruff `TID251` Does Not Recursively Ban Submodules

**What goes wrong:** `banned-api: { "homelab_mcp" = {...} }` catches `import homelab_mcp` and `from homelab_mcp import X` but NOT `from homelab_mcp.client import X` or `from homelab_mcp.server.tools import Y`. A developer can bypass the lint by importing a submodule.

**Why it happens:** ruff's `banned-api` requires explicit per-module entries; there is no wildcard. `[VERIFIED: github.com/astral-sh/ruff/issues/1614 — parent-module bans don't catch submodule imports]`

**How to avoid:** Belt-and-suspenders:
1. **Belt:** ship the `tests/conftest.py` `sys.modules` guard (Pattern 5). Catches every submodule at runtime.
2. **Suspenders:** add a CI / pre-commit `grep` check: `! git grep -E 'from homelab_mcp(\.|\s+import)|^import homelab_mcp' src/ tests/`. Static, zero-runtime-cost, catches at commit time.
3. The ruff `banned-api` entry stays — it's the human-readable signal in lint output and catches the most common case.

**Recommendation:** Plan a single Phase 1 task that ships **both** the ruff config AND the `conftest.py` guard. Treat them as one SETUP-03 deliverable. Document the limitation in a comment in `pyproject.toml`.

**Warning signs:** A developer's IDE auto-imports `from homelab_mcp.types import ToolSchema` and `ruff check` is green. The test still passes. The `conftest.py` guard catches it.

`[VERIFIED: github.com/astral-sh/ruff/issues/1614]`

### Pitfall 5: `uv.lock` Not Committed

**What goes wrong:** `uv.lock` is `.gitignore`d or never committed. `uv sync` produces different versions on each machine. Subtle test-version drift.

**How to avoid:** Phase 1 task includes:
- `git add uv.lock` (CONTEXT.md success criterion 1: "`uv.lock` committed")
- `.gitignore` includes `.venv`, `__pycache__`, `.env`, `*.pyc`, **but NOT** `uv.lock`
- README (Phase 5) documents `uv sync --frozen` as the reproducible install command

`[CITED: PITFALLS.md Pitfall 18]`

### Pitfall 6: `mcp.types.Tool` Import in a Pure-Data Module

**What goes wrong:** `schema_validator.py` imports `from mcp.types import Tool` — but `mcp` is a runtime dep. A developer reading "Phase 1 has no I/O" might delete the `mcp` runtime dep, breaking the module.

**Why it happens:** "No I/O" ≠ "no runtime deps." The framework needs the *type* now so Phase 4 doesn't need a translation layer (CONTEXT.md "Integration Points").

**How to avoid:**
- Declare `mcp>=1.27` in `[project.dependencies]`, not in `[dependency-groups]`. (See Pattern 1 — already correct there.)
- Optional: use `from typing import TYPE_CHECKING; if TYPE_CHECKING: from mcp.types import Tool` and accept any duck-typed object at runtime — but this is over-engineering for MVP. Just import it.

**Warning signs:** `uv sync` in production / CI fails with `ModuleNotFoundError: No module named 'mcp'`.

### Pitfall 7: `frozen=True` Models and Default Mutables

**What goes wrong:** A frozen `BaseModel` with a `list` field gets mutated through the reference (frozen blocks `__setattr__`, NOT mutation of mutable values).

**How to avoid:** All mutable defaults use `Field(default_factory=list)`, not `default=[]`. This is already in Pattern 2 (`McpServerConfig.args`). Note: even with `default_factory`, the resulting `list` is mutable — tests/code MUST NOT mutate `config.mcp_server.args.append(...)`. If users need to override args, build a new `McpServerConfig`.

**Warning signs:** `config.mcp_server.args.append("--debug")` succeeds (does NOT raise) and the change is visible to all consumers — defeats the "frozen for safe sharing" intent.

`[CITED: pydantic v2 frozen semantics — pydantic.dev/docs/validation/latest/api/pydantic/config]`

## Code Examples (verified, planner can lift verbatim)

### Example A: Declaring `Config` and reading it

```python
from mcp_test_framework.config import Config

# Reads env + optional .env + optional YAML (via MCPTF_CONFIG_FILE) + defaults
cfg = Config()
print(cfg.ollama.base_url, cfg.target.tool_name)

# CLI flag override (Phase 5):
cfg = Config(target=TargetConfig(tool_name="some_other_tool"))
```

### Example B: Running schema validation

```python
from mcp_test_framework.schema_validator import validate_tool_schema

issues = validate_tool_schema(tool)
if issues:
    for issue in issues:
        print(f"[{issue.severity}] {issue.path}: {issue.message}")
```

### Example C: Authoritative `iter_errors` pattern (for reference; not Phase 1's idiom)

The 7 checks in spec are *structural* (dict shape), not full JSON Schema validation — Pattern 4 hand-codes them. `iter_errors` is reserved for Phase 4's optional response-schema validation. Documented here in case the planner finds a check that's better expressed as a meta-schema validation.

```python
# Source: python-jsonschema.readthedocs.io/en/stable/errors
from jsonschema.validators import Draft202012Validator

v = Draft202012Validator(meta_schema_for_input_schemas)
for error in v.iter_errors(tool.inputSchema):
    # error.message, error.absolute_path (deque), error.validator
    ...
```

`[VERIFIED: python-jsonschema.readthedocs.io/en/stable/errors -- iter_errors yields ValidationError objects with .message, .absolute_path, .json_path, .validator, etc.]`

### Example D: `.env.example` (Phase 1, DOCS-02)

```bash
# .env.example -- copy to .env and edit. Never commit .env.

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.6:latest
OLLAMA_TIMEOUT_SECONDS=120

MCP_SERVER_COMMAND=homelab-mcp
MCP_SERVER_ARGS=

TARGET_TOOL_NAME=list_registered_servers

JUDGE_TIMEOUT_SECONDS=120

# Optional: path to YAML overlay (CONTEXT.md "YAML config discovery")
# MCPTF_CONFIG_FILE=./config.yaml
```

### Example E: `config.example.yaml` (Phase 1, DOCS-02)

```yaml
# config.example.yaml -- copy to config.yaml and set MCPTF_CONFIG_FILE=./config.yaml.
# YAML overlay sits BELOW env in precedence: CLI > env > .env > YAML > defaults.

ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
  timeout_seconds: 120

mcp_server:
  command: homelab-mcp
  args: []

target:
  tool_name: list_registered_servers

judge_timeout_seconds: 120
```

`[CITED: docs/mcp_test_framework_mvp_spec.md §Configuration -- env var list and YAML schema]`

## State of the Art

| Old Approach | Current Approach (2026) | Why Changed |
|--------------|-------------------------|-------------|
| `[tool.uv].dev-dependencies` | `[dependency-groups].dev` (PEP 735) | Standardized; uv `add --dev` writes the new shape; old shape "explicitly marked as legacy" `[VERIFIED: docs.astral.sh/uv]` |
| `python-dotenv` as direct dep | `pydantic-settings`'s built-in dotenv source via `SettingsConfigDict(env_file=".env")` | Already a `pydantic-settings` capability; declaring both creates two ways to load .env `[CITED: STACK.md]` |
| `pyyaml` as direct dep | `pydantic-settings[yaml]` extra | Pulls `pyyaml` automatically; using YAML without `pydantic-settings`'s source means hand-rolling overlay logic `[CITED: STACK.md]` |
| `jsonschema.RefResolver` | `jsonschema.validators.validator_for` + `referencing` library | `RefResolver` deprecated in jsonschema 4.18+; will be error in 5.x `[CITED: PITFALLS.md Pitfall 16]` |
| `pytest-asyncio` `auto` mode | strict mode (default in 1.x) | Strict avoids collisions with other plugins; matches spec mandate `[CITED: STACK.md]` |
| Pydantic v1 | Pydantic v2 (`>=2.13,<3`) | v1 EOL; doesn't classify Python 3.14; `mcp` requires v2 `[CITED: STACK.md]` |

## Validation Architecture

> **SKIPPED.** `.planning/config.json` has `workflow.nyquist_validation: false`. Per RESEARCH.md spec, this section is not produced when nyquist_validation is explicitly disabled.

## Security Domain

Phase 1 has effectively zero attack surface:
- No network I/O (Phase 3+).
- No subprocess spawning (Phase 2+).
- No untrusted user input (config is local files + env).
- No secrets handling (no API keys; Ollama is unauthenticated; `.env` is dev-local).

| ASVS Category | Applies to Phase 1 | Standard Control |
|---------------|--------------------|------------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (low-risk) | Pydantic v2 validation on all `Config` fields; `int` fields use `Field(ge=1)` |
| V6 Cryptography | no | — |
| V7 Error Handling | yes (low-risk) | Don't log full config (forward-compat for any future API key) — `[CITED: PITFALLS.md security mistakes]` |
| V8 Data Protection | yes (low-risk) | `.env` in `.gitignore` from day one — `[CITED: PITFALLS.md security mistakes]` |
| V14 Configuration | yes | Layered config with explicit precedence; frozen Config model; `.env.example` documents all fields |

**Phase 1 security checklist:**
- `.gitignore` includes `.env`
- `Config` model rejects extra unknown keys (`extra="ignore"` in `SettingsConfigDict` per Pattern 3 — alternative: `extra="forbid"` if stricter is desired; `ignore` is fine for MVP since we don't expect adversarial input)
- All config logging in future phases must elide value (`"OLLAMA_BASE_URL set: True"`), not print value — Phase 1 doesn't log, but document this constraint for Phase 3+

## Open Questions

1. **Ruff `target-version = "py314"` support.**
   - What we know: STACK.md pins ruff `>=0.8`; ruff has historically added `target-version` literals well before the corresponding Python release (e.g., `py313` shipped in 2024).
   - What's unclear: whether ruff 0.8+ (current as of 2026-05) accepts `py314` literally without warnings. `[ASSUMED]`
   - Recommendation: when running `uv sync` in Phase 1 task 1, verify `uv run ruff check` exits cleanly with `target-version = "py314"`. If ruff complains, fall back to `py313` — semantically identical for our lint rules.

2. **`mcp` 1.27 wheel availability for Python 3.14.**
   - What we know: STACK.md lists this as MEDIUM confidence — `mcp` classifies through 3.13. Pure-Python at the SDK layer.
   - What's unclear: whether transitive deps (`pyjwt[crypto]`, `pywin32`) have 3.14 wheels.
   - Recommendation: Phase 1 task 1 is `uv sync` — if any wheel fails to build, surface immediately and document. No code workaround in Phase 1; the failure is in `uv sync`'s lock resolution, not in our code.

3. **`extra="ignore"` vs `extra="forbid"` on `Config`.**
   - What we know: spec doesn't mandate either. `ignore` is permissive (extra env vars don't crash); `forbid` is stricter (catches typos in config.yaml).
   - Recommendation: ship `extra="ignore"` for MVP — env namespaces in shells are noisy and hard to predict. `forbid` adds a non-MVP failure mode for negligible benefit. Revisit if a YAML typo bites someone.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SETUP-01 | `uv sync` produces a clean install on a fresh checkout (Python 3.14); `uv.lock` committed | Pattern 1 (full pyproject.toml shape); STACK.md installation block; Pitfall 5 (commit lockfile) |
| SETUP-02 | `pyproject.toml` configures `pytest-asyncio` strict + session loop scope | Pattern 1 `[tool.pytest.ini_options]` block; STACK.md §"Pytest-asyncio Configuration"; Pitfall 3 |
| SETUP-03 | Lint rule prevents `import homelab_mcp` under `src/` and `tests/` | Pattern 1 `[tool.ruff.lint.flake8-tidy-imports.banned-api]`; Pattern 5 conftest.py belt; Pitfall 4 (submodule gap) |
| CORE-01 | `config.py` + `models.py` load config with precedence `CLI > env > YAML > defaults`; frozen `Config` | Pattern 2 (`models.py`); Pattern 3 (`config.py` with `settings_customise_sources`); Pitfall 1 |
| CORE-02 | `schema_validator.py` performs the 7 deterministic checks; auto-detects draft via `validator_for`; returns `list[ValidationIssue]` | Pattern 4 (`validate_tool_schema` with all 7 checks coded); Pitfall 2 (json_path vs absolute_path) |
| DOCS-02 | `.env.example` and `config.example.yaml` enumerate every configurable setting | Examples D + E above; CONTEXT.md "Env var naming convention" |

## Project Constraints (from CLAUDE.md)

- **Python 3.14** pinned (don't downgrade) — `.python-version` and `pyproject.toml` `requires-python = ">=3.14"`
- **uv** for dep management (no pip / poetry / hatch deps directly)
- **No `import homelab_mcp` anywhere** — black-box mechanically enforced (SETUP-03)
- **`pytest-asyncio` strict mode** with `asyncio_default_fixture_loop_scope = "session"`
- **`asyncio.timeout`** for any async I/O — N/A for Phase 1 (no I/O), but configure pytest-asyncio now so Phase 4 inherits
- **Session-scoped fixtures** — no Phase 1 fixtures, but `[tool.pytest.ini_options]` settles this in Phase 1
- **GSD workflow enforcement** (CLAUDE.md "GSD Workflow Enforcement" section) — Phase 1 work happens through `/gsd-execute-phase`; no direct Edit/Write outside the workflow

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 through D-05; reproduced verbatim)

- **D-01:** All 7 schema checks return `severity="error"`. There is no `warning` tier in MVP output.
- **D-02:** The `severity` field stays on the `ValidationIssue` Pydantic model so a `warning` tier can be added post-MVP without a schema migration. Use `Literal["error"]` (not bare `str`) to make adding `"warning"` a typed change.
- **D-03:** Phase 4 `TEST-02` (`test_tool_schema_is_structurally_valid`) asserts `validate_tool_schema(tool) == []` (empty list) — equivalent to "no errors" because errors are the only severity.
- **D-04:** Check #6 (every property has a `description`) and check #7 (every property has `type`/`oneOf`/`anyOf`) are both errors. Rationale: the framework's whole pitch is judging an MCP tool's contract quality — a tool that ships unannotated parameters fails the contract by design. For the MVP target `list_registered_servers`, these checks are likely vacuous (no input parameters), so this stricture has zero observable cost in Phase 4.
- **D-05:** Note for Phase 4: TEST-02 (full schema validity) and TEST-04 (`test_input_schema_properties_are_documented`) overlap on checks #6 and #7. This is intentional redundant coverage, not a bug — TEST-04 is a focused diagnostic, TEST-02 is the full sweep.

### Claude's Discretion (researched and recommended in this RESEARCH.md)

- **Env var naming convention:** Default to spec-verbatim bare names (`OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, `MCP_SERVER_ARGS`, `TARGET_TOOL_NAME`, `JUDGE_TIMEOUT_SECONDS`, plus `OLLAMA_MODEL` and `OLLAMA_TIMEOUT_SECONDS` to match the YAML schema in spec §Configuration). Document in README that for collision-prone shells, users can use a `.env` file scoped to the project. Revisit if collisions bite in practice.
- **`models.py` contents:** Lives in `src/mcp_test_framework/models.py`. Contains `Config` and its sub-models (`OllamaConfig`, `McpServerConfig`, `TargetConfig`) — the cross-cutting data layer. `ValidationIssue` stays in `schema_validator.py` (domain-local) and `JudgeResult` stays in `ollama_judge.py` (domain-local). Rationale: only `Config` is consumed by *every* module; domain models stay next to their producers.
  - **Research recommendation:** keep `Config` itself in `config.py` (where `settings_customise_sources` is implemented) and only put the *sub-models* in `models.py`. Pattern 2 + Pattern 3 split this way.
- **`tests/` directory structure:** Use `tests/unit/` for the Phase 1 pure-data unit tests (`tests/unit/test_config.py`, `tests/unit/test_schema_validator.py`) and reserve flat `tests/` for Phase 4's integration tests (`tests/test_homelab_list_registered_servers.py`). Single `conftest.py` at `tests/conftest.py` owns the session-scoped fixtures from Phase 4. `pyproject.toml` `[tool.pytest.ini_options]` `testpaths = ["tests"]` picks up both. No marker-based separation needed for MVP.
- **Lint enforcement mechanism (SETUP-03):** Use ruff's `flake8-tidy-imports` rule `TID251` (`banned-api`) configured in `[tool.ruff.lint.flake8-tidy-imports.banned-api]` to ban `homelab_mcp` and `homelab_mcp.*`. Scope to `src/` and `tests/` (the spec's wording) — repo-tooling and `docs/` are unaffected. Verify with a deliberately-failing fixture file or a doctest of the rule itself.
  - **Research finding (CRITICAL):** `TID251` does NOT recursively cover submodules — see Common Pitfalls #4. The decision to use `TID251` is honored, but it must be paired with a `tests/conftest.py` `sys.modules` belt-and-suspenders guard (Pattern 5). Without the belt, `from homelab_mcp.client import X` slips past lint.
- **YAML config discovery:** No auto-discovery in MVP. Path comes from `--config PATH` CLI flag (Phase 5) or the `MCPTF_CONFIG_FILE` env var (Phase 1 needs to support env-var-driven path so unit tests can exercise the YAML overlay without a CLI). If neither is set, no YAML overlay is applied. Defaults + env vars suffice. Revisit if users complain.
- **`Config` immutability:** `model_config = SettingsConfigDict(frozen=True)` on the top-level `Config` model. Sub-models inherit via the same config. Required for safe session-scoped fixture sharing across async tests in Phase 4.
  - **Research note:** Sub-models are plain `BaseModel`, not `BaseSettings`, so they need their own `ConfigDict(frozen=True)` — `SettingsConfigDict(frozen=True)` on the parent does NOT propagate to nested `BaseModel` fields. Pattern 2 sets `frozen` on every sub-model explicitly.
- **`ValidationIssue.path` representation:** JSON-Pointer-style string (e.g., `/inputSchema/properties/foo/description`) — matches `jsonschema`'s native error path output, easiest to surface in `pytest` failure diagnostics.
  - **Research finding (CRITICAL):** `jsonschema`'s `error.json_path` returns JSONPath (`$.foo.bar`), NOT JSON-Pointer (`/foo/bar`). The user's locked decision matches `error.absolute_path` (a deque) joined with `/`, NOT `error.json_path`. See Common Pitfalls #2.

### Deferred Ideas (OUT OF SCOPE for Phase 1)

- **Add `warning`/`info` severity tiers** — `ValidationIssue.severity` is typed `Literal["error"]` for now. Add new literal values (and `Draft202012Validator`-derived softer checks) in a post-MVP phase if real tools surface non-blocking quality issues that deserve their own tier.
- **Auto-discover `config.yaml` in cwd** — MVP requires `--config` or `MCPTF_CONFIG_FILE`. Add cwd auto-discovery if users complain in practice.
- **Prefixed env vars (`MCPTF_*`)** — Stay with spec-verbatim bare names. Reconsider if collisions with co-installed Ollama/MCP tooling bite users.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ruff 0.8+ accepts `target-version = "py314"` | Pattern 1, Open Question 1 | Low — fallback to `py313` is one-line edit; semantically identical |
| A2 | `mcp` 1.27 builds & installs cleanly on Python 3.14 (its classifiers stop at 3.13 but it's pure-Python) | Standard Stack, Open Question 2 | Medium — if `uv sync` fails on 3.14, Phase 1 task 1 surfaces it immediately. No code-level mitigation; would need to either (a) downgrade Python (rejected — pinned in `.python-version`) or (b) wait for an mcp release that classifies 3.14 |
| A3 | `pydantic-settings.YamlConfigSettingsSource` accepts a runtime `yaml_file=` kwarg (overriding `model_config.yaml_file`) | Pattern 3 | Low — the issue #259 example confirms it; if it doesn't, the fallback is to set `yaml_file` via `model_config` only and skip the env-var-driven path until Phase 5 (CLI flag handles it) |
| A4 | `error.absolute_path` is a `collections.deque` (per docs); `list(deque)` and `"/".join(map(str, deque))` work as expected | Pattern 4, `_pointer_from_deque` | Low — verified against jsonschema 4.26 docs; behavior is stable |
| A5 | Sub-models declared as `BaseModel` (not `BaseSettings`) need their own `ConfigDict(frozen=True)` — `frozen=True` on the parent `BaseSettings` does NOT propagate | Pattern 2, CONTEXT.md "`Config` immutability" | Medium — if pydantic v2 *does* propagate, the `ConfigDict(frozen=True)` lines on sub-models are redundant but harmless. If it doesn't propagate (most likely — `frozen` is per-model in pydantic), Pattern 2 is correct as written. Verify with a unit test that asserts `with pytest.raises(ValidationError): config.ollama.model = "X"` |

## Sources

### Primary (HIGH confidence)

- **Project canon:**
  - `docs/mcp_test_framework_mvp_spec.md` §Configuration, §`schema_validator.py`, §Implementation Notes
  - `.planning/REQUIREMENTS.md` §Project Setup, §Core Modules, §Documentation
  - `.planning/ROADMAP.md` §Phase 1
  - `.planning/research/STACK.md` (recommended versions, installation block, "What NOT to Use")
  - `.planning/research/PITFALLS.md` (Pitfalls 1, 3, 10, 11, 13, 16, 18 are Phase 1-relevant)
  - `.planning/STATE.md` ("Decisions" — config precedence locked as `CLI > env > YAML > defaults`)
  - `.planning/phases/01-foundation-pure-data-core/01-CONTEXT.md` (locked Phase 1 decisions)
  - `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout

- **Authoritative external docs (verified 2026-05-04 in this research session):**
  - https://docs.astral.sh/uv/concepts/projects/dependencies/ — `[dependency-groups]` is canonical, `tool.uv.dev-dependencies` is legacy
  - https://docs.astral.sh/ruff/settings/#lint_flake8-tidy-imports_banned-api — `banned-api` configuration syntax under `[tool.ruff.lint.flake8-tidy-imports.banned-api]`
  - https://pytest-asyncio.readthedocs.io/en/stable/concepts.html — strict mode does not require markers on sync tests; `@pytest.mark.asyncio` required only for async tests
  - https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ — `settings_customise_sources` returns leftmost-wins tuple
  - https://pydantic.dev/docs/validation/latest/api/pydantic/config/ — `frozen` semantics: faux-immutable, generates `__hash__`
  - https://python-jsonschema.readthedocs.io/en/latest/api/jsonschema/validators/ — `validator_for` signature, `iter_errors` method
  - https://python-jsonschema.readthedocs.io/en/stable/errors/ — `ValidationError` attributes (`message`, `validator`, `path`, `absolute_path`, `json_path`)

### Secondary (MEDIUM confidence — third-party but credible)

- https://github.com/pydantic/pydantic-settings/issues/259 — runtime `YamlConfigSettingsSource(settings_cls, yaml_file=...)` pattern (community-confirmed, maintainer-acknowledged)
- https://github.com/pydantic/pydantic-settings/issues/366 — full `settings_customise_sources` with YAML example (matches docs idiom)
- https://github.com/astral-sh/ruff/issues/1614 — confirmation that `banned-api` does not recursively cover submodules

### Tertiary (LOW confidence — flagged for verification)

- ruff `target-version = "py314"` literal acceptance — A1 above. Verify by running `uv run ruff check` once after `uv sync` lands.

## Metadata

**Confidence breakdown:**
- Standard stack & versions: **HIGH** — pre-validated in STACK.md against PyPI 2026-05-04
- Architecture / project structure: **HIGH** — consistent across spec, CONTEXT.md, STACK.md
- pytest-asyncio configuration: **HIGH** — verified against current docs
- `pydantic-settings` precedence pattern: **MEDIUM-HIGH** — official docs confirm tuple ordering; `YamlConfigSettingsSource(settings_cls, yaml_file=...)` runtime kwarg confirmed via community examples but not the primary docs page
- jsonschema `validator_for` + `iter_errors`: **HIGH** — verified against current jsonschema docs
- ruff `TID251` submodule gap: **HIGH** — issue #1614 documents the limitation; recommendation to add belt-and-suspenders is sound
- pitfalls: **HIGH** for items already in PITFALLS.md, **MEDIUM** for the two new ones surfaced here (json_path vs absolute_path; sub-model frozen propagation)

**Research date:** 2026-05-04
**Valid until:** 2026-06-03 (30-day window for stable libraries; flag for re-verification if a major version of `pydantic-settings`, `pydantic`, `pytest-asyncio`, or `ruff` ships in that window)
