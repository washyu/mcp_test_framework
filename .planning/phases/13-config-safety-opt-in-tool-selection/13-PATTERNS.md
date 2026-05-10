# Phase 13: Config safety & opt-in tool selection — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 7 modified + 1 created = 8
**Analogs found:** 8 / 8 (all in-repo; this phase is pure surgery on Phase 12 scaffolding)

## File Classification

| Modified/Created File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/mcp_test_framework/cli.py` (`_load_config` resolver) | cli-resolver | request-response | itself, `cli.py:178-211` (existing skeleton) + `_emit_operator_error` (lines 67-94) | exact (in-place expansion) |
| `src/mcp_test_framework/cli.py` (`config-init` body, version literal) | cli-emitter | transform | itself, `cli.py:771-772` (`version: 1` literal) | exact |
| `src/mcp_test_framework/config.py` | pydantic-settings-config | config-load | itself, `config.py:184-192` (`_validate_version`) + `config.py:194-217` (`settings_customise_sources`) | exact (deletion + one-line flips) |
| `src/mcp_test_framework/fixtures.py` | pytest-fixture | event-driven (preflight + tool-selection) | itself, `fixtures.py:268-289` (target.tool_name override) + `fixtures.py:480-494` (`tool_config`) + `tests/conftest.py:88-138` (`_resolve_tool_names`) | exact |
| `src/mcp_test_framework/models.py` | pydantic-model | (data definition) | itself, `models.py:76-98` (`TargetConfig` — to be removed) | exact (deletion) |
| `src/mcp_test_framework/_reporter.py` | pytest-plugin (terminal reporter) | event-driven (logreport hook) | itself, `_reporter.py:127-134` + `_format_skip_reasons` (lines 137-153) | exact |
| `pyproject.toml` | dependency-manifest | static metadata | itself, `pyproject.toml:7-16` (`[project] dependencies`) | exact (deletion check; `python-dotenv` is currently transitive via `mcp[cli]`, not a direct dep) |
| `docs/MIGRATION-v1-to-v2.md` (NEW) | docs | static reference | `docs/ERROR-STYLE.md` (Phase 12, lock-file-style markdown referenced verbatim from a regression test) | role-match |

> **NOTE on `python-dotenv`:** the current `pyproject.toml` (lines 7-16) does NOT declare `python-dotenv` directly — it arrives only via `mcp[cli]`'s transitive cone. CONTEXT.md D-05 says "remove `python-dotenv` from direct `pyproject.toml` deps." There is nothing to remove from `[project].dependencies` itself; the verifiable Phase 13 action is (a) deleting the `from dotenv import dotenv_values` line at `config.py:35` and (b) confirming no other `import dotenv` site exists across `src/`. Recommend the planner reframe this sub-task as "drop the `dotenv` import from `config.py` and verify no `python-dotenv` direct-dep entry exists."

---

## Pattern Assignments

### 1. `cli.py` — promote `_load_config` into the full resolver (D-01..D-04)

**Analog:** existing `_load_config` at `src/mcp_test_framework/cli.py:178-211` — already validates `--config` and raises `typer.Exit(2)` via `_emit_operator_error`. ~80% of the scaffolding exists.

**Existing skeleton to extend** (lines 178-211):

```python
def _load_config(path: Path | None) -> Config:
    """..."""
    if path is not None:
        if not path.is_file():
            _emit_operator_error(
                summary=f"config file not found: {path}",
                detail=[
                    "the path passed to --config does not exist or is not a file.",
                ],
                next_step=(
                    "check the path or run "
                    "`mcp-test-framework config-init -o config.yaml` "
                    "to generate a starter config"
                ),
            )
        os.environ["MCPTF_CONFIG_FILE"] = str(path)
        try:
            return Config()
        ...
    try:
        return Config()
    except ValidationError as exc:
        _emit_operator_error_for_validation(exc, source="(default sources)")
```

**Operator-error emit pattern** (lines 67-94 — copy verbatim into the new resolver branches; do NOT prefix with `raise`):

```python
def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Render an operator-grade error and exit (citation: docs/ERROR-STYLE.md)."""
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)
```

**SAFE-03 verbatim message body** (copy from `docs/ERROR-STYLE.md:46-55` — Phase 12 LOCKED text):

```
no config file found: ./config.yaml

the framework refuses to run without a config file because it would
otherwise call every tool the server advertises -- including any
destructive ones. you must explicitly opt in to which tools run.

next: run `mcp-test-framework config-init -o config.yaml` to generate
      a starter config, then edit it to enable the tools you want to test
```

**Resolver shape** (Phase 13 net new — D-03 single resolver):

1. If `path` (from `--config`) is given → existence check (already exists) → pass to `Config(yaml_file=path)`.
2. Else if `os.environ.get("MCPTF_CONFIG_FILE")` is set → existence check → pass to `Config(yaml_file=...)`. SAFE-04 lead sentence: "the path in `MCPTF_CONFIG_FILE` does not exist".
3. Else if `Path.cwd() / "config.yaml"` exists → pass to `Config(yaml_file=<path>)`.
4. Else → emit SAFE-03 verbatim and `typer.Exit(2)`.

**Critical change vs existing**: stop using `os.environ["MCPTF_CONFIG_FILE"] = str(path)` as the IPC channel (lines 199, 203, 206). Instead pass the resolved path as a kwarg `Config(yaml_file=...)` so `settings_customise_sources` reads it from `init_settings`, not from env.

---

### 2. `cli.py` — `config-init` body version-literal flip (D-08, scaffold change only)

**Analog:** `cli.py:769-772` (already emits a complete v2-shape scaffold per Phase 12 D-02; only the literal version number changes).

**Existing literal** (lines 771-772):

```python
"# Schema version. This release accepts version 1.\n"
"version: 1\n"
```

**Phase 13 surgery:**

```python
"# Schema version. This release accepts version 2.\n"
"version: 2\n"
```

Also update the docstring at line 429 (`"document containing 'version: 1'..."` → `'version: 2'`) and at line 739 (`'version: 1' literal` comment → `'version: 2'`).

---

### 3. `config.py` — env-overlay strip + version flip (D-05, D-08)

**Analog:** `config.py:184-217` (existing `_validate_version` + `settings_customise_sources`).

**Surgery 1 — `_validate_version` flip** (lines 184-192):

Existing:
```python
@field_validator("version", mode="after")
@classmethod
def _validate_version(cls, v: int) -> int:
    """Only `1` is accepted by this build (Phase 08 D-02 / CD-01)."""
    if v != 1:
        raise ValueError(
            f"config version {v} not supported by this build, expected 1"
        )
    return v
```

Phase 13 (one-line change `1 → 2`; the operator-tone wrapper at `cli.py:129-143` already maps version-mismatch ValidationErrors to the SAFE-06 ERROR-STYLE message — keep that wrapper, but update its `summary` and `detail` to match the new locked SAFE-06 text from `ERROR-STYLE.md:57-73`):

```python
@field_validator("version", mode="after")
@classmethod
def _validate_version(cls, v: int) -> int:
    if v != 2:
        raise ValueError(
            f"config version {v} not supported by this build, expected 2"
        )
    return v
```

**Surgery 2 — `settings_customise_sources` collapse** (lines 194-217):

Existing tuple builds: `init_settings → _BareNameNestedEnvSource → env_settings → dotenv_settings → YamlConfigSettingsSource(yaml_file=os.environ.get(...)) → file_secret_settings`.

Phase 13 target tuple: `init_settings → YamlConfigSettingsSource(yaml_file=<from init kwargs>) → file_secret_settings`. Read `yaml_file` from kwargs (passed by `_load_config` via `Config(yaml_file=...)`), not from `os.environ`.

Pydantic-settings idiom for reading kwargs inside `settings_customise_sources`:
```python
yaml_file = init_settings.init_kwargs.get("yaml_file")
sources: list[PydanticBaseSettingsSource] = [init_settings]
if yaml_file and Path(yaml_file).is_file():
    sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file))
sources.append(file_secret_settings)
return tuple(sources)
```

**Surgery 3 — full deletions** (preserves the rest of `config.py` unchanged):

- Delete `_BareNameNestedEnvSource` class (lines 92-147).
- Delete `_alias_env_names` helper (lines 53-61).
- Delete `_maybe_json_decode` helper (lines 64-89).
- Delete `from dotenv import dotenv_values` import (line 35).
- Delete `from pydantic.fields import FieldInfo` import (line 37, used only by deleted helpers).
- Drop `env_file` and `env_file_encoding` from `model_config` (lines 159-160). Keep `frozen=True` and `extra="forbid"`.
- Remove `target: TargetConfig = Field(...)` field declaration (line 166).
- Remove `TargetConfig` from `from mcp_test_framework.models import (...)` (line 48).

---

### 4. `fixtures.py` — three-state allowlist runtime + override deletion (D-12, D-14)

**Analog 1:** `fixtures.py:268-289` — `target.tool_name` membership + override warning. **Deleted in full** (D-14, ~22 lines):

```python
    if config.target.tool_name is not None:
        tool_names = [t.name for t in tools]
        if config.target.tool_name not in tool_names:
            pytest.exit(
                f"target tool {config.target.tool_name!r} not in MCP server tool list "
                f"(available: {tool_names!r})",
                returncode=2,
            )

    # Phase 08 D-12: when target.tool_name is set AND that tool's config has
    # skip=True, the explicit single-target intent wins ...
    if config.target.tool_name is not None:
        explicit_cfg = config.tools.get(config.target.tool_name)
        if explicit_cfg is not None and explicit_cfg.skip:
            warnings.warn(
                f"target.tool_name={config.target.tool_name!r} explicitly set; "
                f"overriding tools.{config.target.tool_name!r}.skip=True for this run",
                UserWarning,
                stacklevel=2,
            )
```

**Analog 2:** the unknown-tool warning at `fixtures.py:259-266` — **keep**. It's harmless under opt-in semantics (still surfaces typos in `tools:` keys against discovered names).

**Analog 3 — selection seam #1** in `tests/conftest.py:88-138` (NOT `fixtures.py:262` — the CONTEXT.md line numbers off by file). This is the v1.1.1 hotfix that filters parametrize input. The Phase 13 three-state semantics replaces the skip-list filter with an allowlist:

Existing (`tests/conftest.py:135-138`):
```python
return [
    name for name in _DISCOVERED_TOOL_NAMES
    if not config.tools.get(name, ToolConfig()).skip
]
```

Phase 13 surgery (D-13 — empty/unset `tools:` ⇒ zero selection; unlisted ⇒ unselected; listed-and-not-skipped ⇒ selected):

```python
# State (b): listed AND skip=False -> include in parametrize.
# State (a): unlisted -> excluded (reporter renders "not selected in config").
# State (c): listed with skip=True -> excluded (reporter renders skip_reason).
# Both (a) and (c) drop out of parametrize; the reporter distinguishes them
# from the ToolConfig presence/absence at render time.
return [
    name for name in _DISCOVERED_TOOL_NAMES
    if name in config.tools and not config.tools[name].skip
]
```

Also delete the explicit-target short-circuit at `tests/conftest.py:101-103` (`if explicit: return [explicit]`) — `target.tool_name` is gone.

**Analog 4 — selection seam #2:** `fixtures.py:480-494` — `tool_config` fixture. Phase 13 keeps this fixture but its consumers are guaranteed-listed (parametrize already filtered):

```python
@pytest.fixture
def tool_config(config: Config, target_tool) -> ToolConfig:
    # Tools reaching this fixture are listed in config.tools (parametrize
    # already filtered states (a) and (c) out); the .get(...) fallback
    # is now defensive only.
    return config.tools.get(target_tool.name, ToolConfig())
```

**State-a / state-c emission** — the reporter (next section) renders the two distinct reason strings; fixtures.py needs to inject a `pytest.skip(reason=...)` only if a future code path collects unlisted-and-skip-marked tools. Per D-13, parametrize-time filtering means neither state reaches `target_tool`, so no `pytest.skip()` call lands in `fixtures.py` — the reporter constructs the SKIP rows from `config.tools` membership directly.

---

### 5. `models.py` — drop `TargetConfig` (D-11 / executes Phase 12 D-03)

**Analog:** `models.py:76-98` — `TargetConfig` class. **Delete entirely** (~22 lines):

```python
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
        ...
```

**Sub-model alias treatment** (D-05 + Claude's-discretion bullet 5): the `validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url")` style on `OllamaConfig`/`McpServerConfig` survives unchanged — env-routing role is gone, but the YAML-key role still works because pydantic's alias resolution accepts any of the choices on the YAML input. **Recommendation for the planner:** leave the AliasChoices entries as-is for Phase 13 (matches Claude's-discretion guidance "safe to leave them in place"); the simplification to plain `Field(alias="base_url")` is a v1.3+ deferred cleanup.

---

### 6. `_reporter.py` — two distinct skip reason strings (D-12)

**Analog:** `_reporter.py:127-134` (skip reason capture) + `_format_skip_reasons` (lines 137-153) + `pytest_terminal_summary` SKIP block (lines 186-196).

**Existing capture** — reasons come from `report.longrepr` via `_extract_skip_reason` (lines 73-91). Today, every SKIP comes from `pytest.skip(reason=...)` so the reason is whatever the framework / test wrote.

**Phase 13 net new constraint:** under opt-in semantics, the two skip rows that operators see for a given tool DO NOT come through `pytest.skip()` — they come from the absence of any test parametrize entry for that tool. This means the per-tool reporter cannot rely on `report.longrepr` alone; it has to compose the SKIP rows from a different source: `Config.tools` + the discovered tool list.

**Two design options for the planner to pick:**

**Option A — Reporter-side composition (recommended).** Add a new function in `_reporter.py` invoked from `pytest_terminal_summary` that walks `discovered_tools - parametrized_tools` and renders one SKIP row per unlisted tool with reason `"not selected in config"`, plus one SKIP row per listed-with-skip tool with reason `tool_cfg.skip_reason or "explicit skip in config"`. Requires the reporter to read the discovered list (already cached in `tests/conftest.py:_DISCOVERED_TOOL_NAMES`) and the loaded `Config()` at terminal-summary time.

**Option B — Synthetic `pytest.skip()` calls during collection.** Re-introduce the v1.1 model where every tool generates a parametrize entry, and unlisted/state-c tools call `pytest.skip(reason=...)` at fixture time. Avoids the cross-module read but resurrects the v1.1.1 skip-bug hotfix's complaint (the 560 SKIPPED-at-runtime regression). **Reject Option B** — the v1.1.1 hotfix memory note (`project_v1_1_skip_bug.md`) is explicit: filter at parametrize time.

**Reason-string constants** (D-12 verbatim — bake into the reporter as module constants so the regression test at `tests/unit/test_error_style.py` style can lock them):

```python
# Phase 13 D-12: two distinct skip-reason strings for opt-in tool selection.
_REASON_NOT_SELECTED = "not selected in config"   # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"  # state (c) fallback
```

**Existing SKIP row render** (lines 186-196 — keep verbatim; the row builder doesn't care where the reason came from):

```python
if skips:
    terminalreporter.write_line("skipped:")
    for tool in skips:
        reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
        if reasons_text:
            terminalreporter.write_line(
                f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"
            )
        else:
            terminalreporter.write_line(f"  {tool.ljust(name_width)}  SKIP")
```

---

### 7. `pyproject.toml` — drop `python-dotenv` direct dep (D-05)

**Analog:** `pyproject.toml:7-16` — `[project] dependencies` block.

**Note** (also in the file-classification table above): the current dependencies block does NOT name `python-dotenv` directly. The actual cleanup is the import-removal in `config.py:35`; verify with a grep across `src/` that no other `import dotenv` exists. The pyproject change reduces to a comment update at most.

```toml
dependencies = [
    "mcp[cli]>=1.27",
    "pydantic>=2.13,<3",
    "pydantic-settings[yaml]>=2.14",
    "jsonschema>=4.26",
]
```

If the planner finds a `python-dotenv` line had crept in via a Phase 12 wave, delete it. Otherwise this sub-task is a no-op + a `uv sync` rerun to confirm `dotenv` is no longer in `uv.lock` paths reachable by `mcp_test_framework`.

---

### 8. `docs/MIGRATION-v1-to-v2.md` — new SAFE-07 doc

**Analog:** `docs/ERROR-STYLE.md` (Phase 12) — short, verbatim-locked markdown referenced from a code site (`cli.py:67-94`'s docstring) and from a regression test (`tests/unit/test_error_style.py`).

**Pattern to copy from ERROR-STYLE.md:**

1. Lock-file-style sections that downstream code copies verbatim (ERROR-STYLE has "Reference messages (locked for downstream phases)").
2. A regression test (`tests/unit/test_error_style.py`) asserts headings + key strings exist via `Path.read_text` + `in` checks (see lines 25-42 of that file).
3. Keep file < 100 lines, plain markdown, no external links beyond in-repo doc paths.

**Suggested MIGRATION-v1-to-v2.md skeleton** (CONTEXT.md D-10 + Phase 12 ERROR-STYLE locked SAFE-06 message):

```markdown
# Migrating config from schema v1 → v2

This release of mcp-test-framework expects schema version 2. v1 configs no
longer load. This page walks an existing operator through the port.

## Why this matters

In v1, a tool with no `tools.<name>` entry ran by default — including any
destructive tools the server advertised. In v2, a tool with no entry skips
by default. You explicitly opt every tool in.

## What stays the same

Per-tool fields port forward unchanged: `call_arguments`, `judges`,
`skip_reason`. Top-level `ollama:`, `mcp_server:`, `judge_timeout_seconds:`
blocks port forward unchanged.

## What changes

- `version: 1` → `version: 2` (top-level header).
- `target:` block → DELETE. Single-tool focus is now done via a focus config
  passed to `--config` (e.g. `--config focus-list_tools.yaml`).
- `.env` files no longer override config. If you had any framework config in
  `.env` (`OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, etc.), move it into your
  YAML.

## Step-by-step port

1. Run `mcp-test-framework config-init -o config.yaml.new` from your repo
   root. This emits a complete v2 scaffold with every discovered tool listed
   as `skip: true`.
2. Open both your old `config.yaml` and the new `config.yaml.new` side by side.
3. For each tool you want to keep testing:
   - Find the tool's block in `config.yaml.new`.
   - Delete the `skip: true` and `skip_reason:` lines.
   - Copy your `call_arguments:` / `judges:` blocks across.
4. Delete the top-level `target:` block from your old config (do not copy it
   into the new file).
5. Replace `config.yaml` with `config.yaml.new`.
6. Re-run `mcp-test-framework run`.

## Side-by-side per-tool example

[v1 → v2 diff for ONE example tool]

## What about `.env`?

The framework no longer reads `.env` for config values. CI-secret patterns
(API keys for future HTTP-backed judges) still pass through `.env` as a
process-env convention, but the framework's config layer ignores it.
```

**Regression test** (write a sibling to `tests/unit/test_error_style.py`):

```python
# tests/unit/test_migration_doc.py
def test_migration_doc_exists() -> None:
    assert (_repo_root() / "docs" / "MIGRATION-v1-to-v2.md").is_file()

def test_migration_doc_pins_v2_keywords() -> None:
    text = (_repo_root() / "docs" / "MIGRATION-v1-to-v2.md").read_text("utf-8")
    assert "version: 2" in text
    assert "config-init -o config.yaml.new" in text
    assert "opt every tool in" in text or "opt-in" in text
    assert "target:" in text  # the deletion instruction
```

---

## Shared Patterns

### Operator-tone error emission (`typer.Exit(2)`)

**Source:** `src/mcp_test_framework/cli.py:67-94` — `_emit_operator_error` helper.
**Apply to:** all SAFE-* error sites in the new resolver branches (SAFE-03 / SAFE-04 / SAFE-06 ValidationError mapper).

```python
def _emit_operator_error(summary, detail, next_step, *, exit_code=2) -> typing.NoReturn:
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)
```

**Critical caveat** (`cli.py:75-77` docstring): "This function never returns; it raises typer.Exit internally. Callers MUST NOT prefix calls with `raise`." Phase 13 callsites must follow the same convention.

### Pytest-side operator-tone parallel

**Source:** `src/mcp_test_framework/fixtures.py:57-81` — `_pytest_exit_operator_tone`.
**Apply to:** any new fixture-time error path (Phase 13 mostly removes paths, but the unknown-tool warning at `fixtures.py:259-266` should stay).

### Banned-token / snippet-correctness regression test pattern

**Source:** `tests/unit/test_error_style.py:44-66` (banned tokens) + `tests/test_readme_snippets.py:57-...` (yaml.safe_load + model-field assertions).
**Apply to:**
- `tests/unit/test_migration_doc.py` (new) — lock SAFE-07 doc keywords
- `tests/unit/test_error_style.py` (extend) — add SAFE-06 verbatim assertions for the new "schema version 2" / "opt-in" wording
- A new SAFE-01 reason-string test that asserts the two literal constants appear in `_reporter.py` so the operator-facing strings can't drift silently

```python
# Pattern from test_error_style.py:29-33:
def test_error_style_contains_safe_03_message() -> None:
    text = ERROR_STYLE.read_text(encoding="utf-8")
    assert "### SAFE-03 — no config found, framework refuses to run" in text
    assert "no config file found: ./config.yaml" in text
    assert "next: run `mcp-test-framework config-init -o config.yaml`" in text
```

### Pydantic-v2 frozen sub-model preservation

**Source:** `src/mcp_test_framework/models.py:39, 59, 79, 118` — `model_config = ConfigDict(frozen=True, populate_by_name=True[, extra="forbid"])`.
**Apply to:** all surviving sub-models (`OllamaConfig`, `McpServerConfig`, `ToolConfig`). `TargetConfig` deletion does not affect this pattern; the others are untouched.

### Top-level `Config(BaseSettings)` frozen contract

**Source:** `src/mcp_test_framework/config.py:157-162` — `model_config = SettingsConfigDict(frozen=True, env_file=".env", env_file_encoding="utf-8", extra="forbid")`.
**Apply to:** Phase 13 strips `env_file` + `env_file_encoding`; **preserves** `frozen=True` and `extra="forbid"` (D-05 explicit).

```python
# Phase 13 target:
model_config = SettingsConfigDict(frozen=True, extra="forbid")
```

---

## No Analog Found

None — this phase is entirely surgery on Phase 12-completed scaffolding plus one new doc whose template (verbatim-locked markdown referenced by a regression test) is a one-to-one mirror of `docs/ERROR-STYLE.md`.

---

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/` (all files)
- `tests/` (focusing on `tests/unit/` and `tests/conftest.py`)
- `docs/` (ERROR-STYLE.md as the migration-doc template)
- `pyproject.toml`

**Files scanned:** 12 (cli.py, config.py, fixtures.py, models.py, _reporter.py, mcp_client.py via grep, conftest.py, pyproject.toml, ERROR-STYLE.md, test_error_style.py, test_readme_snippets.py, test_banned_imports.py via glob)

**Pattern extraction date:** 2026-05-10

**Off-by-one note for the planner:** CONTEXT.md "files affected" lists `fixtures.py:262, 282-286, 482-494` for the three-state allowlist runtime. Verified line numbers in current source: 262 falls inside the unknown-tool warning loop (lines 259-266) which **survives** Phase 13; 282-286 is the override-warning block — line range is **268-289** in the current file (the override block spans `if config.target.tool_name is not None:` through the `warnings.warn(...)` call); 482-494 is the `tool_config` fixture which **survives** with a docstring update only. **The actual three-state filter lives in `tests/conftest.py:88-138` (`_resolve_tool_names`)** — recommend the planner correct the line refs in plan-level documents.
