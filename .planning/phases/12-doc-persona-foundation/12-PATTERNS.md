# Phase 12: Doc & persona foundation - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 9 (5 modified, 3 created, 1 supporting)
**Analogs found:** 9 / 9 (every file has a strong in-repo analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/cli.py` (`list-tools`) | CLI command + formatter | request-response (stdio discovery → text render) | itself (in-place rewrite of `_format_tools_text` at `cli.py:340-361` + new `--full` / `--name` flags) | exact (rewrite of existing function) |
| `src/mcp_test_framework/cli.py` (`config-init`) | CLI command + YAML emitter | request-response (stdio discovery → YAML emit) | itself (in-place rewrite of `_format_tools_yaml_scaffold` at `cli.py:386-438`) | exact (rewrite of existing function) |
| `src/mcp_test_framework/cli.py` (`_load_config` + error sites) | CLI helper + error UX | request-response (path → Config or exit) | existing pattern at `cli.py:80-82, 263-266, 285-298` (typer.echo(err=True) + typer.Exit(2)) | exact (extend, do not replace) |
| `src/mcp_test_framework/config.py` | config model + ValidationError surface | request-response (env/YAML → Config) | itself (no structural change; add catch + re-emit in `_load_config` caller, NOT in the model) | role-match (error rewrites land at the call site) |
| `config.example.yaml` (rewrite) | docs / example config | static template | existing `config.example.yaml` (3 sections kept; ~50 tool entries removed; placeholder names per D-13) | exact (full rewrite preserving section ordering) |
| `.env.example` (rewrite) | docs / example config | static template | existing `.env.example` (CI-secret-passthrough framing per D-12 / Example 4) | exact (full rewrite of the same file) |
| `README.md` (sweep + persona paragraph) | docs | static prose | existing `README.md` (per-line scrub + new section after Core Value) | exact (in-place edits per RESEARCH.md "Concrete leaks to scrub") |
| `docs/EXTENDING.md` (sweep + persona walkthrough) | docs | static prose | existing `docs/EXTENDING.md` (6 leaks scrubbed + new top-level section) | exact (in-place edits) |
| `examples/homelab-mcp.yaml` (NEW) | docs / reference | static template | byte-identical move of today's `config.example.yaml` (per `git mv`) | exact (move, then `config.example.yaml` rewritten in place) |
| `examples/README.md` (NEW) | docs | static prose | RESEARCH.md Example reference text (10-20 lines) — no in-repo prior, but the shape mirrors `docs/EXTENDING.md` intro paragraph + `## Files` table | role-match (new doc, follows existing doc-tree intro convention) |
| `docs/ERROR-STYLE.md` (NEW) | docs / style guide | static prose | `docs/EXTENDING.md` (existing operator-grade docs in `docs/`; same doc tree, same audience) | role-match (new file, follows EXTENDING.md doc convention) |

## Pattern Assignments

### `src/mcp_test_framework/cli.py` `list-tools` (CLI command, request-response)

**Analog:** itself — `_format_tools_text` at `cli.py:340-361` and command body at `cli.py:175-216`.

**Imports pattern** (`cli.py:26-41`) — preserve verbatim; `textwrap` and `shutil` are already imported and reused for the new param-signature wrapping:
```python
from __future__ import annotations

import asyncio
import json
import os
import shutil
import textwrap
from contextlib import AsyncExitStack
from importlib import metadata
from pathlib import Path

import typer
from mcp.types import Tool

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
```

**Typer flag-add pattern** (extend `cli.py:175-186`) — copy the existing `as_json: bool = typer.Option(...)` decorator shape verbatim for the two new flags `full` and `name`:
```python
@app.command("list-tools")
def list_tools(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML config overlay (sets MCPTF_CONFIG_FILE).",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit tools as a JSON array of full MCP tool records.",
    ),
    # NEW per D-06 / D-08 — same Option shape:
    full: bool = typer.Option(
        False,
        "--full",
        help="Include the full description and per-parameter descriptions.",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Substring filter on tool name (case-insensitive).",
    ),
) -> None:
```

**Sort + filter pattern** (rewrite `cli.py:340-361`) — preserve the existing `sorted(tools, key=lambda t: t.name)` + `shutil.get_terminal_size((80, 20)).columns` lines verbatim. Apply the `--name` filter post-sort, pre-render (RESEARCH.md Pitfall 3 — emit a distinct empty-after-filter message). Use `textwrap.shorten(..., placeholder="...")` for D-05 truncation; reuse `textwrap.fill(..., subsequent_indent="  ")` for `--full` description wrap (matches `cli.py:354-359`):
```python
def _format_tools_text(tools: list[Tool], *, full: bool = False, name_filter: str | None = None) -> str:
    width = max(40, shutil.get_terminal_size((80, 20)).columns)
    sorted_tools = sorted(tools, key=lambda t: t.name)
    if name_filter:
        needle = name_filter.lower()
        sorted_tools = [t for t in sorted_tools if needle in t.name.lower()]
    if not sorted_tools:
        if name_filter:
            return f"(no tools matched filter {name_filter!r}; server has {len(tools)} tools total)"
        return "(no tools registered on the server)"
    # ... per-tool render (see RESEARCH.md Code Example 5)
```

**JSON path stays untouched** (`cli.py:213-216`) — D-07 keeps `--json` orthogonal. `_format_tools_json` (`cli.py:364-383`) is NOT modified.

---

### `src/mcp_test_framework/cli.py` `config-init` (CLI command, request-response)

**Analog:** itself — `_format_tools_yaml_scaffold` at `cli.py:386-438` and command body at `cli.py:219-307`.

**Discovery pattern stays unchanged** (`cli.py:268-298`) — `_load_config` → `asyncio.Runner` → `_list_tools_async`. Only the FORMATTER (`_format_tools_yaml_scaffold`) and the `FileNotFoundError` rewrite (cli.py:277-298) change.

**Hand-formatted YAML emit pattern** (rewrite `cli.py:386-438`) — keep the multi-line f-string shape; replace header text + per-tool block per D-01/D-02/D-13. Existing structure (header string, `if not sorted_tools: return header + "  {}\n"`, per-tool loop building blocks, `header + "\n".join(blocks) + "\n"`) is preserved:
```python
# Existing structure to preserve (cli.py:386-438):
def _format_tools_yaml_scaffold(tools: list[Tool]) -> str:
    sorted_tools = sorted(tools, key=lambda t: t.name)
    header = (
        "# mcp-test-framework starter config -- generated by `config-init`.\n"
        "# Edit this file in place, or copy to a project-local path and pass --config PATH.\n"
        # ... full ollama / mcp_server / judge_timeout_seconds / version blocks per RESEARCH.md Example 2
        "tools:\n"
    )
    if not sorted_tools:
        return header + "  {}\n"
    blocks: list[str] = []
    for tool in sorted_tools:
        block = (
            f"  {tool.name}:\n"
            f"    skip: true\n"
            f"    skip_reason: {json.dumps('review and remove skip to enable')}\n"
        )
        blocks.append(block)
    return header + "\n".join(blocks) + "\n"
```

**JSON-quoting pattern (NEW)** (RESEARCH.md Pitfall 2) — wrap every emitted scalar in `json.dumps(value)` for free YAML quoting. `json` is already imported at `cli.py:29`.

**Refuse-to-overwrite gate** (`cli.py:259-266`) — preserve verbatim; rewrite only the error string per ERROR-STYLE.md:
```python
# Source: cli.py:259-266 — STRUCTURE preserved, MESSAGE rewritten via _emit_operator_error
if output is not None and output.exists() and not force:
    typer.echo(
        f"error: refusing to overwrite existing file: {output} (use --force)",
        err=True,
    )
    raise typer.Exit(code=2)
```

---

### `src/mcp_test_framework/cli.py` `_load_config` + error sites (CLI helper, request-response)

**Analog:** existing pattern at three sites — `cli.py:80-82` (path-not-found), `cli.py:263-266` (refuse-overwrite), `cli.py:285-298` (FileNotFoundError enrichment).

**Existing typer-echo+exit pattern** (`cli.py:80-82`):
```python
# Source: cli.py:80-82 — PRESERVE pattern, REWRITE message body via _emit_operator_error
if path is not None:
    if not path.is_file():
        typer.echo(f"error: --config path not found: {path}", err=True)
        raise typer.Exit(code=2)
```

**Existing FileNotFoundError enrichment** (`cli.py:285-298`) — already does multi-line "Hint:" — the closest in-repo precedent for the operator-tone format. Phase 12 generalizes this to `_emit_operator_error` per RESEARCH.md Code Example 1:
```python
# Source: cli.py:285-298 — the de-facto template for ERROR-STYLE.md
msg = (
    f"MCP discovery via {cfg.mcp_server.command!r} failed: "
    f"{exc.__class__.__name__}: {exc}"
)
if str(exc).startswith("MCP server command not on PATH:"):
    msg += (
        f"\n\nHint: {cfg.mcp_server.command!r} was not found on PATH. "
        "If you intended to use a different command, point "
        "MCPTF_CONFIG_FILE at a config.yaml that defines "
        "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
        "The repo ships `config.example.yaml` you can copy and edit."
    )
typer.echo(msg, err=True)
raise typer.Exit(code=2)
```

**ValidationError catch+re-emit (NEW seam)** — wrap `Config()` construction in `_load_config`. The current `cli.py:84-88` swallows-then-reraises:
```python
# Source: cli.py:84-88 — current shape lets pydantic.ValidationError propagate raw
os.environ["MCPTF_CONFIG_FILE"] = str(path)
try:
    return Config()
except Exception:
    os.environ.pop("MCPTF_CONFIG_FILE", None)
    raise
```
Phase 12 catches `ValidationError` specifically, inspects `exc.errors()`, and re-emits via `_emit_operator_error`. Mapping rules per RESEARCH.md Pitfall 1 (version mismatch, extra_forbidden on `target.tool_name`, missing required field). Pop `MCPTF_CONFIG_FILE` before exit (preserve existing safety).

**SIGINT / KeyboardInterrupt handling** (`cli.py:206-212`, repeated `cli.py:273-276`) — preserve verbatim; D-15 explicitly preserves exit codes, and 130 is locked.

---

### `src/mcp_test_framework/config.py` (config model, request-response)

**Analog:** itself — no structural change required. Phase 12's error rewrites land at the CALLER (`_load_config`), not in the model (per RESEARCH.md Architectural Responsibility Map).

**field_validator already names version explicitly** (`config.py:184-192`):
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
The string `"config version 2 not supported by this build, expected 1"` is what `ValidationError` will surface. The CLI-side rewrite intercepts this and re-renders per ERROR-STYLE.md SAFE-06 reference message (no edit to the validator itself).

**`extra="forbid"` posture stays** (`config.py:157-162`) — the `target.tool_name` field is NOT removed in Phase 12 (Phase 13 task per CONTEXT.md `<deferred>`). Phase 12 only stops *emitting* `target:` from `config-init` output.

---

### `config.example.yaml` (full rewrite, static template)

**Analog:** existing `config.example.yaml` (preserve top section structure: ollama → mcp_server → judge_timeout_seconds → version → tools).

**Existing top-of-file convention to PRESERVE** (`config.example.yaml:1-14`):
```yaml
# config.example.yaml -- copy to config.yaml and set MCPTF_CONFIG_FILE=./config.yaml.
# YAML overlay sits BELOW env in precedence: CLI > env > .env > YAML > defaults.

ollama:
  base_url: http://127.0.0.1:11434
  model: qwen3.6:latest
  timeout_seconds: 120
```
Phase 12 keeps the file-header-comment + section-header-comment style; rewrites the header text per D-13 (point at `config-init` for runnable scaffold + `examples/homelab-mcp.yaml` for full reference). Drops the `target:` block entirely (D-03).

**Tool-entry shape to ADAPT** (`config.example.yaml:59-69` — pre-existing pattern):
```yaml
# Source pattern: config.example.yaml:59-62 (pattern A — minimal opt-in via judges-only)
list_keyring_credentials:
  judges: [clarity]

# Source pattern: config.example.yaml:67-69 (pattern C — skip with reason)
list_registered_servers:
  skip: true
  skip_reason: "Description does not pass disambiguation rubric; tracked for upstream homelab-mcp doc fix."
```
Phase 12 builds three placeholder entries (D-13: `<safe_read_tool_a>` minimal opt-in, `<safe_read_tool_b>` opt-in with `call_arguments`, `<destructive_tool_c>` skip + reason) — all three patterns already exist in the source file; just rename + adjust comments.

**Reference output text** — RESEARCH.md Code Example 3 (lines 425-476) is the literal text to write.

---

### `.env.example` (full rewrite, static template)

**Analog:** existing `.env.example` (just 25 lines — full rewrite per RESEARCH.md Code Example 4).

**Existing comment-style to PRESERVE** (`.env.example:1-5`):
```bash
# .env.example -- copy to .env and edit. Never commit .env.
#
# Spec env vars (docs/mcp_test_framework_mvp_spec.md Section Configuration).
# Bare names are deliberate (CONTEXT.md "Env var naming convention" -- LOCKED).
# Precedence: CLI flags > env > .env > YAML > defaults.
```
Phase 12 preserves the leading-`#` comment style + section-blank-line-spacing convention. Replaces the body per CLEAN-06 (CI-secret-passthrough framing only). Drops the `TARGET_TOOL_NAME` and `MCP_SERVER_*` declarations (their ROLE in v1.2 is "config goes in config.yaml, not env").

**Reference output text** — RESEARCH.md Code Example 4 (lines 479-497).

---

### `README.md` (per-line sweep + persona paragraph)

**Analog:** existing `README.md`. Per-line edits per RESEARCH.md "Concrete leaks to scrub" table (7 leaks).

**Existing markdown table convention** (`README.md:70-80`) — preserve table column shape; remove the `TARGET_TOOL_NAME` row entirely; rewrite the `setup` / `depends_on` reserved-field cells:
```markdown
# Source: README.md:96-97 — the two leak lines
| `setup` | `null` | Reserved for v1.5+ stateful testing (TOOLCFG-03); runtime no-op in v1.1. |
| `depends_on` | `null` | Reserved for v1.5+ stateful testing (TOOLCFG-03); runtime no-op in v1.1. |
```
Rewrite to (per RESEARCH.md leak table):
```markdown
| `setup` | `null` | Reserved for stateful testing in a future release; no runtime effect today. |
| `depends_on` | `null` | Reserved for stateful testing in a future release; no runtime effect today. |
```

**Persona-paragraph section convention** — match the existing `## Per-tool configuration` and `## Sample green run` H2-section style at `README.md:86, 126`. New section "## Testing an MCP server you didn't write" goes immediately after Core Value paragraph (before/around `README.md:70` per D-12). Reference text from RESEARCH.md Code Example 6 is the literal copy.

**Existing "Further reading" link list** (`README.md:225-231`) — append link to `examples/homelab-mcp.yaml` (D-14: link BOTH `config.example.yaml` AND `examples/homelab-mcp.yaml`):
```markdown
# Source: README.md:225-231 — pattern to extend
- [`config.example.yaml`](config.example.yaml) -- complete real-server per-tool config reference
```
Becomes (split into hand-curated TEMPLATE + worked EXAMPLE):
```markdown
- [`config.example.yaml`](config.example.yaml) -- starter template with placeholder names + 3 pattern variations
- [`examples/homelab-mcp.yaml`](examples/homelab-mcp.yaml) -- complete worked example for the homelab-mcp server
```

---

### `docs/EXTENDING.md` (per-line sweep + persona walkthrough)

**Analog:** existing `docs/EXTENDING.md`. 6 leaks scrubbed per RESEARCH.md leak table; new top-level "## Testing an MCP server you didn't write" section added after intro per RESEARCH.md Open Question 2 recommendation.

**Existing leak-rewrite shape** — pure prose substitution per RESEARCH.md leak table for `EXTENDING.md` (lines 128, 181-182, 185, 215, 220, 226). Rewrites listed verbatim in RESEARCH.md.

---

### `examples/homelab-mcp.yaml` (NEW, byte-identical move)

**Analog:** today's `config.example.yaml` (the file at the path BEFORE this phase's edits) — bytes preserved as the v1.1 reference.

**Move command** (RESEARCH.md "examples/ directory layout"):
```bash
git mv config.example.yaml examples/homelab-mcp.yaml
```
Then re-create `config.example.yaml` from RESEARCH.md Code Example 3 (placeholder template).

**Spec-IDs preserved** per RESEARCH.md Open Question 1 recommendation — `examples/` is reference material, not primary docs; spec IDs from the v1.1 era stay.

---

### `examples/README.md` (NEW, doc tree convention)

**Analog:** doc-tree intro convention from `docs/EXTENDING.md` opening prose + `## Files` table style.

**Reference text** — RESEARCH.md Code Example for `examples/README.md` (10-20 lines per D-11). Naming convention paragraph mirrors `README.md`'s "## Further reading" link list shape.

---

### `docs/ERROR-STYLE.md` (NEW, style guide)

**Analog:** `docs/EXTENDING.md` doc convention (top-level doc in `docs/`, audience: operators + future-phase implementers).

**Existing doc-tree pattern** (Phase 12 adds 3rd file under `docs/`):
```
docs/
├── EXTENDING.md                # existing — operator extension guide
├── mcp_test_framework_mvp_spec.md   # existing — design spec (preserved verbatim)
└── ERROR-STYLE.md              # NEW — style guide + SAFE-03/SAFE-06 reference messages
```

**Reference text** — RESEARCH.md Code Example 7 (lines 590-678) is the literal skeleton. Rules section + exit-code table + reference messages (SAFE-03 / SAFE-06) + banned-strings checklist.

---

## Shared Patterns

### Operator-tone error helper (PERSONA-03)

**Source:** RESEARCH.md Code Example 1 (extends `cli.py:80-82`, `cli.py:263-266`, `cli.py:285-298`).
**Apply to:** Every operator-visible error site (D-15: config load, MCP spawn, judge connect, missing-config, missing-tool).

```python
# Lives in cli.py near _load_config; cited from docs/ERROR-STYLE.md
def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> None:
    """Render an operator-grade error and exit.

    Format (per docs/ERROR-STYLE.md):
        <one-line summary>
        <blank>
        <detail line 1>
        ...
        <blank>
        next: <action verb> <command-or-instruction>
    """
    parts = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)
```

**Exit-code preservation rule** (D-16 rule 4): every rewrite keeps the existing exit code from the call site (2 for config / spawn / overwrite; 130 for SIGINT; 1 for test failure; 0 for success).

### Hand-formatted YAML emission

**Source:** existing `_format_tools_yaml_scaffold` at `cli.py:386-438`.
**Apply to:** `config-init` rewrite + (no other emission sites in scope).

Convention: multi-line f-string concatenation, header text first as a single triple-quoted/concatenated string, per-tool blocks built as `list[str]`, joined with `"\n".join(blocks) + "\n"`. Empty case returns `header + "  {}\n"`. JSON-quote every string scalar via `json.dumps(value)` (NEW per Pitfall 2 — `json` already imported at `cli.py:29`).

### Typer Option + Exit pattern

**Source:** existing decorator usage at `cli.py:125-145, 175-186, 219-239`.
**Apply to:** new `--full` and `--name` flags on `list-tools`.

```python
flag: bool = typer.Option(False, "--flag-name", help="...")
arg: str | None = typer.Option(None, "--arg-name", help="...")
```

### asyncio.Runner + AsyncExitStack lifecycle

**Source:** `cli.py:202-212` (`list-tools` body), `cli.py:271-276` (`config-init` body), `cli.py:320-337` (`_list_tools_async`).
**Apply to:** preserve verbatim — Phase 12 makes ZERO changes to async lifecycle (out of scope; Phase 04.1 hardened pattern).

### Test pattern (Typer CliRunner)

**Source:** `tests/test_config_init_cli.py:22-25`.
**Apply to:** any new tests for `list-tools --full` / `list-tools --name PATTERN` / config-init scaffold shape.

```python
from typer.testing import CliRunner
from mcp_test_framework.cli import app

def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))
```

Live-MCP tests gate behind `@pytest.mark.live_homelab` (RESEARCH.md / `tests/test_config_init_cli.py:63`). Unit-level tests (pure path/format checks) run without the marker.

## No Analog Found

None — every Phase 12 file has a strong in-repo analog. The two new docs (`examples/README.md`, `docs/ERROR-STYLE.md`) follow the existing `docs/EXTENDING.md` doc-tree convention; their content is fully prescribed by RESEARCH.md Code Examples 7 and the examples/README reference text.

## Metadata

**Analog search scope:**
- `src/mcp_test_framework/cli.py` (full, 443 lines)
- `src/mcp_test_framework/config.py` (full, 218 lines)
- `config.example.yaml` (full, 243 lines)
- `.env.example` (full, 25 lines)
- `README.md` (lines 70-231, the affected ranges per RESEARCH.md leak table)
- `docs/EXTENDING.md` (line counts only; content rewrites scripted by RESEARCH.md leak table)
- `tests/test_config_init_cli.py` (first 80 lines for the CliRunner pattern)

**Files scanned:** 7
**Pattern extraction date:** 2026-05-09
