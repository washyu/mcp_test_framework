# Phase 12: Doc & persona foundation - Research

**Researched:** 2026-05-09
**Domain:** CLI scaffold emission (`config-init`), doc/example genericisation, operator-tone error UX, persona reframe
**Confidence:** HIGH (locked stack, mostly mechanical work; one library-add decision verified against PyPI)

## Summary

Phase 12 is mostly **doc surgery + a `config-init` rewrite + an operator-tone error pass**. The stack is locked (typer / pydantic-settings / mcp SDK / pytest) — the planner doesn't pick libraries, it picks **shapes**. This research therefore prescribes:

1. **Hand-formatted YAML string for `config-init` output, NOT ruamel.yaml.** The current `_format_tools_yaml_scaffold` already does this. The output shape needs to change (per D-01/D-02/D-03/D-13), but the technique stays. ruamel.yaml would only earn its keep if we round-tripped existing user configs (we don't).
2. **`typer.echo(..., err=True)` + `raise typer.Exit(code=N)` for operator-tone errors.** Click's `ClickException` would auto-prefix `"Error: "` which fights the multi-line ERROR-STYLE.md format (one-line summary + multi-line detail block + actionable next-step). The repo already uses `typer.echo(err=True)` in `cli.py:81-82, 263-265, 297` — preserve the pattern, change only the wording.
3. **`config-init` emits placeholder names against a live server is wrong** — D-02 LOCKS that `config-init` discovers real tool names from the live MCP. Placeholders live in `config.example.yaml` (D-13/D-14 — they are different files). `config-init` failing loud with no `--offline` mode (D-04) is correct.
4. **`examples/` = single-file directory with thin `examples/README.md`** (D-11). Convention: name files after the SUT (`homelab-mcp.yaml`), preserve all current content from today's `config.example.yaml` verbatim into `examples/homelab-mcp.yaml`.
5. **`docs/ERROR-STYLE.md`** as a NEW separate file is cleaner than grafting into `EXTENDING.md` — discoverable by name, citable from the rewritten error sites, and Phase 13 has a copy-paste target without scrolling through unrelated extension docs.

**Primary recommendation:** Land work in this order (mirrors discretion-allowed sequence in CONTEXT.md):
ERROR-STYLE.md → `config-init` rewrite (drives `config.example.yaml` shape) → `config.example.yaml` rewrite + `examples/homelab-mcp.yaml` creation → README/EXTENDING/.env.example sweep → `list-tools` enhancements → persona-framing paragraphs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**config-init posture:**
- **D-01:** `config-init` emits a **v1-header, v2-style content** config — `version: 1` (loadable today) but populated as Phase 13 will want it. Phase 13's v1→v2 conversion = header bump + flipping the unlisted-default; not regenerate-from-scratch.
- **D-02:** `tools:` block contains **all discovered tools, each with `skip: true` and `skip_reason: "review and remove skip to enable"`**. Operator opts in by removing `skip` from chosen tools. Zero tools run until operator opts in.
- **D-03:** **Drop `target.tool_name` entirely.** Removed from `config-init` output and from all docs. Phase 13 v2 schema removes the field from the Pydantic Config model.
- **D-04:** `config-init` against an unreachable MCP server **fails loud with a PERSONA-03-style error** (no `--offline`, no placeholder fallback). Error names actionable next step.

**list-tools UX at N=70:**
- **D-05:** Default per-tool render = name + 1-line truncated description + one-line param signature (`(host: str, port: int, *, timeout: int = 30)`). Required params before kwargs.
- **D-06:** `--full` flag adds full description (untrimmed) + per-parameter descriptions from `inputSchema`. Stays human-readable; does NOT dump raw JSON.
- **D-07:** `--json` (machine-readable) stays separate. `--full` = verbosity, `--json` = format.
- **D-08:** `--name PATTERN` = substring filter, case-insensitive. Composes with `--full` and `--json`.
- **D-09:** Default sort order **stays alphabetical**. Filtering, not sorting, is the lever for managing scale.

**Doc cleanup + examples/ shape:**
- **D-10:** **Per-section semantic rewrite**, not regex strip. Each affected line rewritten in operator terms; sentences stand alone after spec-ID removal.
- **D-11:** `examples/` is a **one-file directory + brief README** (`examples/homelab-mcp.yaml` + `examples/README.md`, 10-20 lines).
- **D-12:** PERSONA-01 README addition = **top-of-README short framing paragraph + link**. 3-5 sentences near Core Value. Walkthrough lives in `docs/EXTENDING.md`.
- **D-13:** `config.example.yaml` shows **3 placeholder tool entries demonstrating pattern variations**: `<safe_read_tool_a>` (minimal opt-in, just `skip: false`), `<safe_read_tool_b>` (opt-in + `call_arguments`), `<destructive_tool_c>` (`skip: true` + `skip_reason`).
- **D-14:** `config.example.yaml` and `config-init` output are **deliberately different files**. `config.example.yaml` = static, hand-curated, placeholder names, comments, 3 pattern variations. `config-init` = dynamic, real discovered tool names, all `skip: true`. README/CLEAN-04 links to BOTH.

**Error message scope + style:**
- **D-15:** Four error surfaces in scope: config load failures, MCP server spawn failures, judge connect failures, missing-config / missing-tool errors.
- **D-16:** **Style guide locked upfront in `docs/ERROR-STYLE.md`** (or new section in `EXTENDING.md`). Rules: (1) operator terms only — no spec IDs, no internal jargon (TOOLCFG/D-/CD-); (2) name actionable next step inline (`run X to recover`); (3) one-line summary + multi-line detail block, NOT a wall of text; (4) preserve exit codes. Each rewritten message references the guide.
- **D-17:** **SAFE-03 (no-config failsafe) and SAFE-06 (v1→v2 migration) reference messages are pre-drafted in Phase 12's ERROR-STYLE.md**. Phase 13 implements them verbatim.

### Claude's Discretion
- Plan ordering within Phase 12 (suggested: ERROR-STYLE.md first → config-init rewrite → docs sweep → list-tools work → persona section).
- Specific wording of the persona-framing paragraph and placeholder tool-name suffixes (a/b/c naming).
- Whether `examples/README.md` and `docs/ERROR-STYLE.md` are NEW files or sections grafted into existing files (research recommendation: NEW files, see Architecture Patterns).
- Whether `--name` filter is glob-style or pure substring (default: pure substring, case-insensitive).

### Deferred Ideas (OUT OF SCOPE for Phase 12)
- Removing `target.tool_name` from the Pydantic model — that's a Phase 13 task; Phase 12 only stops *emitting* it.
- Implementing SAFE-03 and SAFE-06 messages as runtime — Phase 12 only *drafts* them in ERROR-STYLE.md.
- v1→v2 schema bump — Phase 13.
- Color/TTY rendering for `list-tools` (out per REQUIREMENTS.md).
- Live-progress streaming (out per REQUIREMENTS.md).
- Automated planning-artifact regression guard.
- `list-tools` sort grouping (v1.3+).
- ERROR-STYLE.md banned-token enforcement test (v1.3+).
- Multi-config workflow ergonomics / `--only TOOL_NAME` flag.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLEAN-01 | Strip planning-artifact IDs from `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md` | "Concrete leaks to scrub" appendix below enumerates every match for the planner |
| CLEAN-02 | Genericise `config.example.yaml` to placeholder tool names; remove ~50 homelab-specific entries | D-13 prescribes 3 pattern-variation entries; "Reference shape: `config.example.yaml`" section gives literal text |
| CLEAN-03 | Move current `config.example.yaml` content to `examples/homelab-mcp.yaml` | "examples/ directory layout" section prescribes filenames, README content, and copy convention |
| CLEAN-04 | README worked examples switch to placeholders; add link to `examples/homelab-mcp.yaml` | Diff-targeted line list under "Concrete leaks to scrub" + D-14 link to BOTH files |
| CLEAN-05 | `config-init` emits complete self-contained config (full top-level sections, runs without `.env`) | "Reference shape: `config-init` output" section gives literal text; Code Examples shows `_format_full_scaffold` shape |
| CLEAN-06 | `.env.example` reframed for CI-secret passthrough only (env vars no longer override config) | "Reference shape: `.env.example`" section gives literal text |
| PERSONA-01 | Add "Testing an MCP server you didn't write" section to README + EXTENDING | Specific paragraph drafted in "Persona framing" section, with citation to D-12 |
| PERSONA-02 | `list-tools` shows `inputSchema` summaries (default summary, `--full` for full schema) | "list-tools render shape" section gives the param-signature derivation algorithm + sample output |
| PERSONA-03 | Operator-facing error messages rewritten in operator terms; each names an actionable next step | "Operator-tone error pattern" section gives 4 worked rewrites + ERROR-STYLE.md skeleton |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YAML scaffold emission (`config-init`) | CLI command (`cli.py:config_init`) | — | Pure formatting; consumes `list[Tool]` from existing `_list_tools_async` seam. No new module needed. |
| Tool discovery for scaffold | MCP client (`McpTestClient.__aenter__` via `_list_tools_async`) | — | Already exists; reused unchanged. |
| Error message rewrites | CLI command bodies + `_load_config` | `config.py` ValidationError surfaces | Single seam at `cli.py:_load_config` (D-PERSONA-03 anchor); supplemental rewrites at FileNotFoundError site (cli.py:277-298) and Config()/ValidationError sites in `config.py`. |
| `list-tools` rendering | `_format_tools_text` (rewrite) + new helper for param-signature | `_format_tools_json` (UNCHANGED) | D-07 keeps JSON format orthogonal — work is in the human-readable formatter only. |
| Persona-framing copy | `README.md` + `docs/EXTENDING.md` | — | Pure docs. |
| Doc scrub | Four files only | — | Mechanical edits inside the four named files. |
| Error-style guide | `docs/ERROR-STYLE.md` (new file) | — | New file recommended over grafting into EXTENDING.md (see Architecture Patterns). |
| `examples/` directory convention | `examples/homelab-mcp.yaml` + `examples/README.md` | — | New folder; existing `config.example.yaml` content moved verbatim into `examples/homelab-mcp.yaml`. |

## Standard Stack

### Core (already in place — DO NOT add new deps)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typer` | 0.25.x (existing) | CLI surface (`config-init`, `list-tools` flags) | Already in use; transitive dep of `mcp[cli]`. New flags (`--full`, `--name`) follow existing decorator pattern in `cli.py:177-185`. [VERIFIED: codebase grep — `typer.Option` used at cli.py:125,131,177,182,221,227,236] |
| `pydantic` 2.x + `pydantic-settings` | 2.13+ / 2.14+ (existing) | Config model — surfaces ValidationError that PERSONA-03 wraps | Already in use; error rewrites land at the call site, not in the model. |
| `mcp` SDK (Python) | 1.27.x (existing) | `Tool` dataclass with `inputSchema` → drives PERSONA-02 render | Already in use; `inputSchema` is a dict matching JSON Schema Draft 2020-12 — read `properties` / `required` to derive D-05's param signature. [CITED: `mcp.types.Tool` already imported in `cli.py:38`] |
| stdlib `textwrap` | 3.14 stdlib | Description wrapping for `--full` render | Already used at `cli.py:354-359`. No new dep. |

### Supporting (existing)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `json` | 3.14 stdlib | `--json` output (unchanged) | D-07 keeps JSON path orthogonal; no work needed here. |
| stdlib `shutil` | 3.14 stdlib | Terminal width for wrapping | Already used at `cli.py:347`. |

### Alternatives Considered (and rejected)
| Instead of hand-formatted YAML string | Could Use | Why rejected |
|---------------------------------------|-----------|--------------|
| Hand-formatted multi-line string (current `_format_tools_yaml_scaffold`) | `ruamel.yaml` 0.19.1 with `CommentedMap` + `yaml_set_comment_before_after_key` | (1) New runtime dep for one-shot emission with no round-trip need (we never *load* `config-init` output and rewrite it). (2) `ruamel.yaml`'s comment API (`yaml_set_start_comment`, `yaml_set_comment_before_after_key`) is verbose for the few comments we need. (3) Hand-format is what the existing codebase does (`cli.py:386-438`) — keep it. (4) Hand-format gives precise control over comment placement, which a `CommentedMap` round-trip can re-shuffle. [VERIFIED: PyPI `ruamel.yaml 0.19.1` released 2026-01-02; CITED: ruamel.yaml docs — round-trip mode required for comments, breaks under `typ='safe'`] |
| Hand-formatted multi-line string | `jinja2` template | (1) New runtime dep for one template with ~5 substitutions (header text, version literal, per-tool block iteration). (2) Breaks the "no new deps unless required" rule from CONTEXT.md research-context. (3) Templates make YAML indentation harder to verify in code review. |

**Installation:** No new dependencies. The phase's only stack additions are documentation files and CLI behaviour changes that ride existing libs.

**Version verification (existing deps):** No upgrades required. All affected code is in `src/mcp_test_framework/cli.py`, `src/mcp_test_framework/config.py`, and four documentation/example files.

## Architecture Patterns

### System Architecture Diagram

```
                         operator runs `mcp-test-framework <cmd>`
                                          |
                                          v
                          ┌───────────────────────────────────┐
                          │   typer app (cli.py:43-48)        │
                          │   `--no_args_is_help=True`        │
                          └───────────┬───────────────────────┘
                                      |
            ┌─────────────────────────┼─────────────────────────────┐
            v                         v                             v
   ┌─────────────────┐       ┌──────────────────┐         ┌─────────────────────┐
   │  config-init    │       │  list-tools      │         │  run / version      │
   │  (cli.py:219)   │       │  (cli.py:175)    │         │  (cli.py:118 / 311) │
   └────────┬────────┘       └────────┬─────────┘         └─────────────────────┘
            │                         │
            v                         v
   ┌──────────────────────────────────────────┐         (Phase 12 changes
   │  _load_config() (cli.py:64)              │          land at:
   │  PERSONA-03 rewrites land here           │          • _load_config error sites
   └────────┬─────────────────────────────────┘          • config-init template
            │                                            • list-tools formatter)
            v
   ┌──────────────────────────────────────────┐
   │  Config() — pydantic-settings            │
   │  config.py — ValidationError surfaces    │
   └────────┬─────────────────────────────────┘
            │
            v
   ┌──────────────────────────────────────────┐
   │  _list_tools_async() (cli.py:320)        │
   │  → McpTestClient stdio session           │
   │  → returns list[Tool] from mcp SDK       │
   └────────┬─────────────────────────────────┘
            │
            v
   ┌──────────────────────────────────────────┐
   │  formatters (cli.py:340-438)             │
   │  • _format_tools_text (rewrite for D-05/D-06/D-08)
   │  • _format_tools_json (UNCHANGED — D-07)
   │  • _format_tools_yaml_scaffold (rewrite for D-01/D-02/D-13)
   └──────────────────────────────────────────┘
```

### Recommended Project Structure (additions only)
```
docs/
├── ERROR-STYLE.md              # NEW: D-16/D-17 style guide + reference messages
├── EXTENDING.md                # EDIT: PERSONA-01 walkthrough + scrub
└── mcp_test_framework_mvp_spec.md   # UNCHANGED (preserved verbatim per PROJECT.md)
examples/                       # NEW: D-11 single-file directory + thin README
├── README.md                   # NEW: 10-20 lines; "What lives here, naming convention"
└── homelab-mcp.yaml            # NEW: today's config.example.yaml content moved verbatim
config.example.yaml             # REWRITE: 3 placeholder pattern entries (D-13)
.env.example                    # REWRITE: CI-secret-passthrough framing (CLEAN-06)
README.md                       # EDIT: persona paragraph (D-12) + scrub + link to BOTH
                                #       config.example.yaml AND examples/homelab-mcp.yaml
src/mcp_test_framework/
├── cli.py                      # EDIT: list-tools render, config-init template, error rewrites
└── config.py                   # EDIT: error rewrites at ValidationError surface only
```

### Pattern 1: Hand-formatted YAML scaffold with embedded comments
**What:** Build the scaffold as a single multi-line Python string (f-string concatenation), with section-header comments hand-written at column 0 of each block.
**When to use:** ALWAYS for `config-init`. Never round-trip through a YAML library when the goal is one-shot emission with curated comments.
**Example:** See "Code Examples" section — drop-in replacement for `_format_tools_yaml_scaffold`.

### Pattern 2: Operator-tone error message
**What:** `typer.echo(message, err=True); raise typer.Exit(code=N)`. Message = one-line summary + blank line + multi-line detail + blank line + actionable-next-step prefixed with `next: `.
**When to use:** Every operator-visible error site (D-15: config load, MCP spawn, judge connect, missing-config, missing-tool).
**Example:**
```python
# Source: existing pattern at cli.py:81-82, cli.py:263-265, cli.py:285-298 — extended per ERROR-STYLE.md
def _emit_operator_error(summary: str, detail: list[str], next_step: str, *, exit_code: int = 2) -> None:
    """Emit a PERSONA-03-style error and exit. Format locked in docs/ERROR-STYLE.md."""
    lines = [summary, ""]
    lines.extend(detail)
    lines.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(lines), err=True)
    raise typer.Exit(code=exit_code)
```

### Pattern 3: Param-signature derivation from `inputSchema` (PERSONA-02)
**What:** Walk `tool.inputSchema["properties"]` once; required params (those in `inputSchema["required"]`) come first, optional kwargs second with defaults inlined.
**When to use:** Default `list-tools` render (D-05) and `--full` render (D-06) both consume the same derived signature.
**Example:** See "Code Examples" section — `_format_param_signature(tool: Tool) -> str`.

### Pattern 4: New file vs section graft for ERROR-STYLE.md
**What:** Create `docs/ERROR-STYLE.md` as a new file rather than a section in `docs/EXTENDING.md`.
**When to use:** Always for the style guide. Reasons: (1) `EXTENDING.md` is for users adding rubrics/judges/tools — operators reading error messages aren't extending anything; (2) `ERROR-STYLE.md` is the citation target for every rewritten error site, so a top-level filename reads better than a deep-link; (3) Phase 13's verbatim copy-paste of SAFE-03/SAFE-06 reference messages is cleaner from a dedicated file; (4) the doc tree already has `docs/EXTENDING.md` and `docs/mcp_test_framework_mvp_spec.md` — adding a third file is no organisational tax.

### Anti-Patterns to Avoid
- **Adding `ruamel.yaml` as a runtime dep just to emit a YAML file** — current `_format_tools_yaml_scaffold` proves you don't need it. New deps must clear "the existing approach has a concrete failure" — it doesn't.
- **`click.ClickException` in a typer codebase** — auto-prefixes `"Error: "` and ships single-line messages, which fights the multi-line ERROR-STYLE.md format. Stick with `typer.echo(err=True) + typer.Exit(code=N)` (existing pattern).
- **Regex-strip planning IDs without rewriting sentences** — D-10 explicitly forbids this. Each spec-ID-anchored sentence must read coherently after the ID disappears.
- **Letting `config-init` emit placeholder names** — D-02 LOCKS that `config-init` runs against a live server and emits real discovered names. Placeholder content lives in `config.example.yaml` (D-14).
- **Color/TTY rendering with `rich` for `list-tools`** — explicitly out of scope per REQUIREMENTS.md "Out of Scope" table. Plain text only.
- **Adding `--offline` mode to `config-init`** — D-04 LOCKS fail-loud-on-unreachable. No fallback path.
- **Editing files outside the four scrub targets for CLEAN-01** — REQUIREMENTS.md CLEAN-01 explicitly preserves spec IDs in `src/` and `tests/` comments where they cross-reference code↔spec.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Substring case-insensitive filter (`--name PATTERN`) | Custom regex / glob-to-regex | `pattern.lower() in tool.name.lower()` | D-08 explicitly chooses substring over glob; one-line stdlib check beats a fnmatch import |
| YAML quoting for `skip_reason` strings | DIY escape logic | Wrap in double quotes only when value contains `:`, `#`, `'`, `"`, or starts with `[`/`{`/`-`/digit | The existing `_format_tools_yaml_scaffold` doesn't quote at all because reason strings are commented out. Phase 12 emits real `skip_reason` values, so quote them all unconditionally with `json.dumps(reason)` to get correct YAML quoting for free [VERIFIED: YAML 1.2 — JSON-quoted strings are valid YAML scalars] |
| Param-signature wrapping for narrow terminals | Custom column splitter | `textwrap.fill` with `subsequent_indent="    "` (already used at `cli.py:354`) | Existing pattern; matches D-05's "1-line truncated" requirement by setting `max_lines=1`/`placeholder="..."` |
| YAML emission with comments | `ruamel.yaml.CommentedMap` + comment-attach methods | Hand-formatted f-string concatenation | One-shot emission, no round-trip; existing `_format_tools_yaml_scaffold` proves the f-string approach scales [CITED: ruamel.yaml docs — round-trip mode required; PyYAML safe_dump strips comments [CITED: ruamel.yaml.dev]] |
| Error-message formatting (one-line summary + detail block) | Custom logger / Rich panel | Plain `typer.echo(err=True)` with `\n` separators | No new deps; matches existing pattern at `cli.py:285-298` |

**Key insight:** Phase 12 is the kind of phase where "use the boring tool already in the codebase" beats "introduce X for cleaner code." The existing `_format_tools_yaml_scaffold` and `typer.echo(err=True)` patterns are the SOTA for *this codebase*; the question is whether to reshape them, not replace them. (Auto-memory `feedback_scaffold_completeness.md` says "scaffolds must be runnable, not partial deltas" — the existing pattern produces a runnable file already; Phase 12 just expands what's emitted.)

## Common Pitfalls

### Pitfall 1: ValidationError messages from pydantic-settings leak schema-internal jargon
**What goes wrong:** `Config()` raises pydantic.ValidationError with messages like `"version: config version 2 not supported by this build, expected 1"` or `"target -> tool_name: extra fields not permitted"` — these are operator-hostile.
**Why it happens:** pydantic's default error rendering is field-path-prefixed and uses Python type-system terms (`extra fields`, `value error`, etc.). The repo currently propagates ValidationError uncaught from `_load_config` (cli.py:84-89), surfacing pydantic's raw message.
**How to avoid:** Catch `ValidationError` at `_load_config`, inspect `exc.errors()`, and re-emit via `_emit_operator_error()` with operator-mapped wording. Map at minimum: `version` mismatch → "this config file uses an older format..."; `extra_forbidden` on `target.tool_name` → "the `target.tool_name` field was removed in v1.2; remove it or run `config-init` to regenerate"; `missing` on a required field → "your config is missing the `<field>` section; copy the relevant block from `config.example.yaml`."
**Warning signs:** Error message contains `→`, `value_error`, `pydantic`, `validation error for Config`, or any `model_config`/`extra="forbid"` jargon.

### Pitfall 2: f-string YAML emission silently produces invalid YAML when `skip_reason` contains a colon, hash, or quote
**What goes wrong:** `f'    skip_reason: {reason}\n'` works for "destructive: clones VM" but breaks parsing if `reason` is `"see #123: don't enable"`.
**Why it happens:** YAML treats `:` and `#` as control characters in unquoted scalars; the existing `_format_tools_yaml_scaffold` got away with it because every block is commented out.
**How to avoid:** Quote ALL emitted string values via `json.dumps(value)`. JSON-quoted strings are always valid YAML 1.2 scalars [VERIFIED: YAML 1.2 spec, see also ruamel.yaml documentation]. Apply this to `skip_reason`, `mcp_server.command`, `mcp_server.args` items, `ollama.base_url`, `ollama.model`.
**Warning signs:** Any emitted scalar that comes from a Pythonic source rather than a literal in your formatter.

### Pitfall 3: `--name PATTERN` filter applied AFTER MCP discovery wastes a subprocess spawn for the failure case
**What goes wrong:** Operator runs `list-tools --name typo_that_matches_nothing` and spawns the MCP subprocess (cost: ~1-3 seconds) before discovering the empty filter result.
**Why it happens:** Substring filter naturally lives between discovery and rendering.
**How to avoid:** Apply the filter post-discovery (the spawn is unavoidable to GET the tool list), but emit a distinct "no tools matched filter `<pattern>`; full server has N tools" message rather than the existing empty-result message. This is per `_format_tools_text` line 350: `if not sorted_tools: return "(no tools registered on the server)"` — wrong message when the server has tools but the filter eliminated all.
**Warning signs:** "no tools registered" message after `--name` filtering — false negative for the operator.

### Pitfall 4: `config.example.yaml` and `config-init` output diverge silently
**What goes wrong:** Operator copies `config.example.yaml`, edits it, and finds it doesn't match what `config-init` would have generated; or vice versa, follows a `config-init`-generated file's pattern and finds `config.example.yaml`'s pattern is different.
**Why it happens:** D-14 explicitly designs them as different files with different purposes. Risk: drift if README doesn't make the distinction explicit, or if both are owned by different plans.
**How to avoid:** README/CLEAN-04 must link to BOTH and explain the contract: `config.example.yaml` is a hand-curated TEMPLATE with placeholder names + 3 pattern variations; `config-init` output is a dynamic snapshot with REAL discovered names. Both produce v1-header / v2-style content per D-01.
**Warning signs:** A reviewer asks "why does `config-init` not match `config.example.yaml`?" — that's the question the README must pre-empt.

### Pitfall 5: Persona-framing paragraph reads like marketing copy instead of operator instruction
**What goes wrong:** "Empower your testing workflow with vibe-coded MCP support!" — anti-operator.
**Why it happens:** Reframing black-box-as-feature tempts marketing-tone phrasing.
**How to avoid:** Lift the literal sentence locked in CONTEXT.md `<specifics>`: *"The framework treats your MCP server as a black box — you don't need to read its source. `list-tools` shows you the parameter shapes; `config-init` scaffolds the suite. Designed for operators testing servers they didn't author."* — operator-tone, names the two CLI commands by name, ends with a positioning sentence.
**Warning signs:** Adjectives like "powerful", "seamless", "empowers"; absence of CLI-command names; absence of the verb "treats" or "designed for".

### Pitfall 6: ERROR-STYLE.md skeleton lands but the actual rewrites reference internal jargon anyway
**What goes wrong:** The style guide says "no spec IDs" but the rewritten error message says "MCPTF_CONFIG_FILE not set; see TOOLCFG-01."
**Why it happens:** Fast-paced rewrites against multiple error sites; no mechanical guard (D-16 deferred the banned-token test to v1.3+).
**How to avoid:** Plan-phase task for each rewritten error message must include a verification checklist: (1) zero spec IDs in message text; (2) zero file:line references in message text; (3) action verb in the next-step line; (4) exit code unchanged from current behaviour. Manual review against the four-rule list at code-review time.
**Warning signs:** Any emitted error string containing `[A-Z]+-\d+`, `Phase \d+`, `Plan \d+-\d+`, `\d{6}-[a-z0-9]{3}`, or `:[0-9]+`.

## Code Examples

Verified patterns matching the existing codebase shape. Drop-in replacements for the planner.

### Example 1: Operator-tone error helper (PERSONA-03)
```python
# Source: extends existing pattern at cli.py:81-82 / cli.py:263-265
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
        <detail line 2>
        ...
        <blank>
        next: <action verb> <command-or-instruction>

    Operator terms only — no spec IDs, no file:line refs, no internal jargon.
    """
    parts = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)


# Worked rewrite #1: --config path missing (replaces cli.py:80-82)
def _load_config(path: Path | None) -> Config:
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
        except ValidationError as exc:
            os.environ.pop("MCPTF_CONFIG_FILE", None)
            _emit_operator_error_for_validation(exc, source=path)
    return Config()


# Worked rewrite #2: MCP server command not on PATH (replaces cli.py:285-298)
# Note: the existing message references "Plan 05-05" via the indirect TARGET_TOOL_NAME line
# in .env.example; the rewrite drops that reference entirely.
except FileNotFoundError as exc:
    if str(exc).startswith("MCP server command not on PATH:"):
        _emit_operator_error(
            summary=f"MCP server command not found: {cfg.mcp_server.command!r}",
            detail=[
                f"the framework tried to launch the server with "
                f"`{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}` "
                f"and the command is not on PATH.",
                "",
                "if your server is installed via `uvx` or `pipx`, set "
                "`mcp_server.command` and `mcp_server.args` in your config.yaml "
                "to match (e.g. `command: uvx, args: [your-server-package]`).",
            ],
            next_step=(
                "verify the launch command works manually, then update "
                "`mcp_server.command` / `mcp_server.args` in your config.yaml"
            ),
        )
    # fall-through for other FileNotFoundError shapes
    _emit_operator_error(
        summary="MCP server failed to start",
        detail=[f"{exc.__class__.__name__}: {exc}"],
        next_step=(
            "check that your `mcp_server.command` is runnable and any "
            "required environment is in place"
        ),
    )
```

### Example 2: Reference shape — `config-init` output (CLEAN-05, D-01/D-02/D-03)

This is the literal text the rewritten `_format_tools_yaml_scaffold` should produce against a 3-tool server (sorted alphabetically). The **shape** generalises to N tools.

```yaml
# mcp-test-framework starter config -- generated by `config-init`.
# Edit this file in place, or copy to a project-local path and pass --config PATH.

# Ollama judge backend.
ollama:
  base_url: "http://127.0.0.1:11434"
  model: "qwen3.6:latest"
  timeout_seconds: 120

# MCP server under test.
# The launch command MUST be runnable from your shell. Verify with:
#   <command> <args...>
mcp_server:
  command: "uvx"
  args: ["your-mcp-server-package"]
  timeout_seconds: 30

# Judge call timeout (outer budget cap on each judge HTTP call).
judge_timeout_seconds: 120

# Config schema version. This release accepts version 1.
version: 1

# Per-tool registry. Every tool the connected server advertises is listed
# below as `skip: true` -- the framework will not call any tool until you
# review and remove `skip` from the ones you want to test.
#
# Read each entry below, decide whether it is safe to call against your
# environment, then either:
#   - delete the `skip` and `skip_reason` lines to enable the tool, OR
#   - leave the entry as-is to keep the tool out of the test surface.
tools:
  list_keyring_credentials:
    skip: true
    skip_reason: "review and remove skip to enable"
  list_registered_servers:
    skip: true
    skip_reason: "review and remove skip to enable"
  suggest_deployments:
    skip: true
    skip_reason: "review and remove skip to enable"
```

Notes for the planner:
- `ollama:` / `mcp_server:` / `judge_timeout_seconds:` / `version:` / `tools:` MUST all be emitted — CLEAN-05 forbids partial deltas relying on env defaults.
- `target:` block ABSENT — D-03.
- `tools:` is populated with ACTUAL discovered tool names (D-02), not placeholders.
- Header text is operator-tone; no spec IDs, no internal jargon.
- All string scalars JSON-quoted (Pitfall 2).

### Example 3: Reference shape — `config.example.yaml` (CLEAN-02, D-13)

```yaml
# config.example.yaml -- starter template with placeholder tool names.
#
# This file is HAND-CURATED to show the shape you fill in.
# For a runnable scaffold against your actual server, run:
#   mcp-test-framework config-init -o config.yaml
# For a complete real-world reference, see examples/homelab-mcp.yaml.

# Ollama judge backend.
ollama:
  base_url: "http://127.0.0.1:11434"
  model: "qwen3.6:latest"
  timeout_seconds: 120

# MCP server under test. Replace with the launch command for your server.
mcp_server:
  command: "uvx"
  args: ["your-mcp-server-package"]
  timeout_seconds: 30

judge_timeout_seconds: 120

# Schema version. This release accepts version 1.
version: 1

# Per-tool registry: each entry below illustrates one pattern variation.
# Replace placeholder names with actual tool names from `mcp-test-framework list-tools`.
#
# Pattern A -- minimal opt-in: just enable the tool and run all rubrics.
# Pattern B -- opt-in with pre-filled call arguments for tools that require input.
# Pattern C -- opt-out with a curated reason (master-config + focus-toggle).
tools:
  <safe_read_tool_a>:
    # Pattern A -- minimal opt-in. Listing the tool with no `skip:` line
    # means the framework runs it with all default rubrics + empty args.
    judges: [clarity, disambiguation, parameters]

  <safe_read_tool_b>:
    # Pattern B -- opt-in with pre-filled args. Required for tools that
    # error on empty input.
    call_arguments:
      query: "example"
      limit: 10

  <destructive_tool_c>:
    # Pattern C -- skip with a curated reason. Use this for tools that
    # mutate real state and should not run in your test surface.
    skip: true
    skip_reason: "destructive: writes to production inventory"
```

### Example 4: Reference shape — `.env.example` (CLEAN-06)

```bash
# .env.example -- environment variables for CI secret passthrough only.
#
# IMPORTANT: env vars no longer override config values. They are documented
# here as a passthrough mechanism for CI secrets that individual subsystems
# (e.g. an HTTP-backed judge) may consume directly. To configure the
# framework, edit `config.yaml` and pass `--config config.yaml`, or run
# `mcp-test-framework config-init -o config.yaml` to generate a starter.
#
# Never commit a populated .env file -- it likely contains secrets.

# Example: an HTTP-backed judge would read its API key from the environment
# rather than from config.yaml so the secret never lands in version control.
# JUDGE_API_KEY=sk-...

# Path to a YAML config file (read by --config / MCPTF_CONFIG_FILE).
# MCPTF_CONFIG_FILE=./config.yaml
```

### Example 5: `list-tools` param-signature derivation (PERSONA-02, D-05)
```python
# Source: lives next to _format_tools_text in cli.py
def _format_param_signature(tool: Tool) -> str:
    """Render `(name: type, name: type, *, kw: type = default)`.

    Required params (per inputSchema.required) come first; optional params
    follow `*,` as kwargs with their defaults inlined. Type names are the
    raw JSON Schema `type` values ("string", "integer", "boolean", "array",
    "object", "number"). Falls back to `Any` for unconstrained params.

    Returns "()" for tools with no inputSchema or no properties.
    """
    schema = tool.inputSchema or {}
    props: dict = schema.get("properties", {}) or {}
    required: list[str] = list(schema.get("required", []) or [])
    if not props:
        return "()"

    def _pytype(jschema_type: object) -> str:
        # Map JSON Schema scalar types to a short label. Lists -> "Any" since
        # we don't render union/anyOf at this verbosity level (D-06 takes that).
        if isinstance(jschema_type, str):
            return {
                "string": "str", "integer": "int", "boolean": "bool",
                "number": "float", "array": "list", "object": "dict",
            }.get(jschema_type, "Any")
        return "Any"

    req_parts: list[str] = []
    kw_parts: list[str] = []
    # Preserve required order; sort kwargs alphabetically for determinism.
    for name in required:
        if name in props:
            req_parts.append(f"{name}: {_pytype(props[name].get('type'))}")
    for name in sorted(p for p in props if p not in required):
        prop = props[name]
        default = prop.get("default", "...")
        kw_parts.append(f"{name}: {_pytype(prop.get('type'))} = {default!r}")

    if not kw_parts:
        return f"({', '.join(req_parts)})"
    if not req_parts:
        return f"(*, {', '.join(kw_parts)})"
    return f"({', '.join(req_parts)}, *, {', '.join(kw_parts)})"


# Default render (D-05): name + 1-line truncated description + signature
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
    blocks: list[str] = []
    for t in sorted_tools:
        sig = _format_param_signature(t)
        desc = t.description or "(no description)"
        if full:
            wrapped = textwrap.fill(desc, width=max(20, width - 2),
                                    initial_indent="  ", subsequent_indent="  ")
            block = f"{t.name}{sig}\n{wrapped}"
            # full also prints per-param descriptions (D-06) -- elided here for brevity
        else:
            # 1-line truncated description (D-05)
            short = textwrap.shorten(desc, width=max(20, width - 4), placeholder="...")
            block = f"{t.name}{sig}\n  {short}"
        blocks.append(block)
    return "\n\n".join(blocks)
```

### Example 6: Persona-framing paragraph (PERSONA-01, D-12)

Drop-in for README.md, immediately after the existing "MVP targets the `homelab-mcp` server..." paragraph:

```markdown
## Testing an MCP server you didn't write

The framework treats your MCP server as a black box — you don't need to read
its source. `mcp-test-framework list-tools` shows you the tools the server
exposes and their parameter shapes; `mcp-test-framework config-init` scaffolds
a config file populated with the actual tools you have. Designed for operators
testing servers they didn't author.

The full walkthrough lives in [`docs/EXTENDING.md`](docs/EXTENDING.md#testing-an-mcp-server-you-didnt-write).
```

### Example 7: ERROR-STYLE.md skeleton (D-16, D-17)

Drop-in for `docs/ERROR-STYLE.md`:

```markdown
# Error message style guide

Operator-facing error messages in `mcp-test-framework` follow four rules.
This guide is the citation target for every rewritten error site (PERSONA-03)
and the canonical source for the SAFE-03 / SAFE-06 reference messages that
Phase 13 will implement verbatim.

## Rules

1. **Operator terms only.** No spec IDs, no internal jargon, no
   `Phase N` / `Plan N-N` / `TOOLCFG-`/`D-`/`CD-` / file:line references.
   The operator does not have your planning artefacts.
2. **Name the actionable next step inline.** Every error ends with a
   `next: <action verb> <command-or-instruction>` line. The verb must
   be imperative (`run`, `check`, `update`, `verify`).
3. **One-line summary + multi-line detail block.** Not a wall of text.
   Format:
       <summary>
       <blank>
       <detail line 1>
       <detail line 2>
       ...
       <blank>
       next: <action> <instruction>
4. **Preserve exit codes.** Don't change behaviour, only words. The
   table below records the contract.

| Error class                              | Exit code |
|------------------------------------------|-----------|
| Config not found / typo'd path           | 2         |
| Config schema mismatch / version error   | 2         |
| MCP server command not on PATH           | 2         |
| MCP server fails handshake               | 2         |
| Judge endpoint unreachable               | 2         |
| Test failure                             | 1         |
| All pass                                 | 0         |
| SIGINT (Ctrl+C)                          | 130       |

## Reference messages (locked for downstream phases)

The following messages are LOCKED in this style guide. Phase 13 implements
them verbatim — copy exactly, do not reword.

### SAFE-03 — no config found, framework refuses to run

    no config file found: ./config.yaml

    the framework refuses to run without a config file because it would
    otherwise call every tool the server advertises -- including any
    destructive ones. you must explicitly opt in to which tools run.

    next: run `mcp-test-framework config-init -o config.yaml` to generate
          a starter config, then edit it to enable the tools you want to test

### SAFE-06 — config uses an older schema version

    config file uses an older format: <path>

    this release of mcp-test-framework expects schema version 2 (opt-in
    tool selection); your config is version 1 (opt-out). the difference
    matters: in v1 a tool with no entry runs by default, in v2 it skips
    by default.

    your existing per-tool settings (`call_arguments`, `judges`,
    `skip_reason`) port forward unchanged -- only the implicit default
    flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows
    the steps.

    next: run `mcp-test-framework config-init -o config.yaml.new` to see
          the v2 layout, port your tool entries across, then replace your
          existing config

## Banned strings (manual review checklist)

When rewriting an error message, grep the rewritten output for these
patterns -- any match is a regression:

    Phase \d
    Plan \d-\d
    [A-Z]{2,}-\d{2}      # spec IDs like TOOLCFG-01, ISOL-02, D-03
    \d{6}-[a-z0-9]{3}    # quick-task IDs like 260507-j6i
    src/.*\.py:\d+       # file:line references
    \(.*\.md\)           # parenthetical file references inside the message
```

## Concrete leaks to scrub (CLEAN-01 input for the planner)

Every match found in the four target files. Planner uses this as the find-and-replace task list. **Per D-10, each line is a per-section semantic rewrite** — do NOT regex-strip and leave dangling sentences.

### `README.md` (7 leaks)
| Line | Current | Recommended rewrite |
|------|---------|---------------------|
| 78 | `` `TARGET_TOOL_NAME` ... default was switched in Plan 05-05 from `list_registered_servers` ... `` | Remove the entire `TARGET_TOOL_NAME` row. v1.2 drops `target.tool_name` (D-03) — env-var docs should not advertise a field that's leaving. |
| 96 | `Reserved for v1.5+ stateful testing (TOOLCFG-03); runtime no-op in v1.1.` | `Reserved for stateful testing in a future release; no runtime effect today.` |
| 97 | (same as 96 for `depends_on`) | (same rewrite) |
| 150 | `... with the documented default `TARGET_TOOL_NAME=list_keyring_credentials`.` | `... against a representative homelab-mcp tool surface.` (or remove sentence; the sample run section is being rewritten in Phase 14, plan-phase decision) |
| 158-159 | `If you switch `TARGET_TOOL_NAME` ... e.g., the original Phase 04 default `list_registered_servers` ...` | Remove `TARGET_TOOL_NAME` reference. Rewrite around per-tool config selection: "If you enable a tool whose declared description does not satisfy the description-quality rubrics ..." |
| 214 | `... fixed in Phase 04.1; it should not recur in normal operation.` | `... fixed in an earlier release; it should not recur in normal operation.` |

### `config.example.yaml` (full rewrite per D-13 — no per-line list applies, but the leaks for reference)
| Line | Current | Disposition |
|------|---------|-------------|
| 17 | `# Phase 07 + Phase 08 default: leave tool_name unset ...` | **Whole file rewritten per Example 3 above.** Existing content moves verbatim to `examples/homelab-mcp.yaml` (CLEAN-03) preserving these comments unchanged — `examples/` is allowed to retain spec-IDs since it documents the v1.1 era. |
| 23 | `# To restrict to a single tool (CD-05 short-circuit ...` | (preserved in `examples/homelab-mcp.yaml`) |
| 31 | `# Phase 08 schema version. Only `1` is accepted ...` | (preserved in `examples/homelab-mcp.yaml`) |
| 35 | `# Per-tool config registry (TOOLCFG-01..07).` | (preserved in `examples/homelab-mcp.yaml`) |
| 44-45 | `# Reserved fields ... TOOLCFG-03 ... SEED-004 ...` | (preserved in `examples/homelab-mcp.yaml`) |
| 48 | `# SAFE-BY-DEFAULT POSTURE (260507-n0g):` | (preserved in `examples/homelab-mcp.yaml`) |
| 52 | `... Phase 07's multi-tool discovery means TEST-08 ...` | (preserved in `examples/homelab-mcp.yaml`) |
| 66 | `# ---- Pre-existing (Phase 04/05/08 v1.0 baseline) ----` | (preserved in `examples/homelab-mcp.yaml`) |

**Note:** Per CLEAN-01's "Spec IDs may remain in `src/` and `tests/` comments where they serve as code↔spec cross-references" — the planner SHOULD decide whether `examples/` follows the same allowance (research recommendation: YES, allow IDs in `examples/` because the file documents the v1.1 baseline that produced them; alternative is for the planner to scrub `examples/homelab-mcp.yaml` to operator-tone too — both defensible. Default to "preserve" unless plan-phase decides otherwise; the file is reference material, not the primary read.)

### `.env.example` (3 leaks — full rewrite per Example 4 above)
| Line | Current | Disposition |
|------|---------|-------------|
| 4 | `# Bare names are deliberate (CONTEXT.md "Env var naming convention" -- LOCKED).` | Removed entirely; CLEAN-06 reframes the file. |
| 17 | `# Switched in Plan 05-05 (acceptance) ...` | Removed entirely. |
| 22 | `# Optional: path to YAML overlay (CONTEXT.md "YAML config discovery").` | Replaced with operator-tone framing per Example 4. |

### `docs/EXTENDING.md` (6 leaks)
| Line | Current | Recommended rewrite |
|------|---------|---------------------|
| 128 | `... empty argument map (TOOLCFG-06 safe defaults).` | `... empty argument map (the safe defaults).` |
| 181-182 | `This is the warning currently living at `src/mcp_test_framework/_isolation.py:33-36`, copied verbatim ...` | `This is the warning living at the top of `src/mcp_test_framework/_isolation.py`, copied verbatim ...` (drop file:line — also fixes the v1.1 line-range error noted in STATE.md "EXTENDING.md WR-01") |
| 185 | `> (DOC-07 in Phase 10). Each new pass-through is a hole ...` | `> Each new pass-through is a hole ...` (drop the parenthetical entirely; the warning text stands alone) |
| 215 | `- The locked v1.1 allowlist (Phase 06 D-07) names exactly `USERNAME`. The` | `- The current allowlist names exactly `USERNAME`. The` |
| 220 | `- `USERNAME` is documented in `_isolation.py:55-62` as "informational; ...` | `- `USERNAME` is documented in `_isolation.py` as "informational; ...` |
| 226 | `... `06-VERIFICATION.md` G-03 and `v1.1-MILESTONE-AUDIT.md` W-6, with the` | Remove this whole `06-VERIFICATION.md` / `v1.1-MILESTONE-AUDIT.md` sentence; replace with: "The cross-platform-parity concern is documented as informational; the agreed disposition is rationale-only — no `USER` added to the allowlist, the parity gap stays documented here." |

**Total leaks across all four files:** 17 (matches the auto-memory's "18-leak count" within rounding — auto-memory tally pre-dated this enumeration).

## examples/ directory layout (CLEAN-03, D-11)

```
examples/
├── README.md
└── homelab-mcp.yaml
```

### `examples/README.md` reference text (10-20 lines per D-11)

```markdown
# Examples

This directory contains real-world configs for specific MCP servers.
Each file is a complete, runnable `config.yaml` you can copy to your
working directory and pass to `mcp-test-framework run --config <path>`.

## Files

- `homelab-mcp.yaml` — config for the
  [`homelab-mcp`](https://github.com/washyu/homelab-mcp) server. The
  reference example used during development of this framework.

## Naming convention

Files are named after the MCP server they target (lowercase, dashes match
the upstream package name). To add an example for another server, drop a
file named after it here and link it from this README.
```

### `examples/homelab-mcp.yaml`

Bytes-identical copy of today's `config.example.yaml` (the file at the path before this phase's edits). All current homelab-specific tool entries, all current spec-ID-laced comments — preserved as the v1.1 reference. The planner uses `git mv config.example.yaml examples/homelab-mcp.yaml` to keep history (or `git mv` followed by recreating `config.example.yaml` from Example 3 above; either preserves history of the moved bytes per `git log --follow`).

## State of the Art

| Old Approach (v1.1) | Current Approach (Phase 12) | Why Changed | Impact |
|---------------------|------------------------------|-------------|--------|
| `config.example.yaml` = ~50-tool homelab-specific file | Generic 3-pattern template + `examples/homelab-mcp.yaml` for the worked example | Operators testing non-homelab servers had to mentally subtract homelab-specifics | Lower friction for new operators |
| `config-init` emits commented-out passthrough scaffold | `config-init` emits all-tools-skipped explicit scaffold | Auto-memory `feedback_scaffold_completeness.md`: scaffolds must be runnable; `project_config_discovery_and_safety.md`: no-config silently runs destructive tools | Operator must opt-in per tool; safe by default |
| Error messages reference `Plan 05-05` / `Phase 04` / `[WinError 2]` | Error messages reference operator-actionable next steps | Operator does not have the planning artefacts | Errors become recoverable instead of cryptic |
| Black-box rule = test-discipline ("don't import the SUT") | Black-box reframed = user-facing feature ("test any MCP server you didn't write") | Vibe-coded MCP persona (auto-memory `project_vibe_coded_persona.md`) | Positioning matches actual user intent |
| `list-tools` = name + wrapped description | `list-tools` = name + 1-line description + param signature; `--full` adds per-param descriptions; `--name PATTERN` filters | At N=70 tools, the v1.1 default is unscannable; auto-memory `project_output_ergonomics_at_scale.md` | Output stays readable + drilldown via filter |

**Deprecated/outdated (in this phase's scope):**
- `target.tool_name` field — emit-side dropped here (D-03), Pydantic model removal in Phase 13.
- `.env`-overlay-as-config — `.env.example` reframed as CI-secret passthrough only (CLEAN-06); actual loader change in Phase 13 (SAFE-05).
- `tools.<name>` no-entry meaning "use defaults" — comment text in `config.example.yaml` should ANTICIPATE Phase 13's flip ("each entry below illustrates one pattern; tools without an entry will be auto-skipped under the v2 schema").

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `examples/homelab-mcp.yaml` may retain v1.1 spec-IDs because `examples/` documents reference material rather than primary docs | "examples/ directory layout" | Low — if planner decides `examples/` should also be operator-toned, the rewrite is mechanical (apply the same rewrites listed for `config.example.yaml` line-table). User confirmation only needed if there's a strong preference. [ASSUMED] |
| A2 | Operators understand "v1-header / v2-style content" (D-01) without an explanatory comment in the emitted scaffold itself | "Reference shape: config-init output" | Low-medium — if confusing, plan-phase can add a one-line comment to the scaffold ("# This file uses v2-style opt-in semantics under the v1 schema header; will upgrade cleanly to v2."). [ASSUMED] |
| A3 | `--name PATTERN` filter is case-insensitive substring (D-08 default), not glob | Architecture Patterns / Code Examples | Low — substring is simpler and matches D-08's default phrasing. [VERIFIED: D-08 in CONTEXT.md] |
| A4 | `_format_param_signature`'s JSON Schema → Python type mapping is faithful enough at the verbosity D-05 wants | Code Example 5 | Low — `--full` (D-06) is the escape hatch for full type detail; default render is intentionally lossy. The mapping is canonical (see e.g., `pydantic-core` JSON Schema docs). [ASSUMED] |
| A5 | `git mv config.example.yaml examples/homelab-mcp.yaml` preserves `git log --follow` history | examples/ directory layout | Low — git's rename detection is heuristic but reliable for byte-identical moves. [VERIFIED: git docs — `--follow` works after rename when content similarity threshold is met] |
| A6 | The persona-framing paragraph belongs near top-of-README (after Core Value / "MVP targets..."), not in the Configuration section | Code Example 6 | Low-medium — D-12 says "top-of-README short framing paragraph + link". If plan-phase wants it elsewhere, the paragraph text is movable. [VERIFIED: D-12 in CONTEXT.md] |

**No claims marked `[ASSUMED]` are about destructive behaviour, security, or compliance** — all assumptions are about presentation/wording choices the planner can re-decide cheaply.

## Open Questions

1. **Should `examples/homelab-mcp.yaml` be operator-toned or preserve the v1.1 IDs?**
   - What we know: D-11 says `examples/` is reference material; CLEAN-01 says `src/` and `tests/` keep IDs as code↔spec cross-refs; `examples/` is neither.
   - What's unclear: which side of the line `examples/homelab-mcp.yaml` falls on.
   - Recommendation: Preserve IDs (treat `examples/` like reference material). Plan-phase can flip if the user objects during review.

2. **Where does the persona walkthrough section actually live in `docs/EXTENDING.md`?**
   - What we know: D-12 says "Walkthrough lives in `docs/EXTENDING.md`."
   - What's unclear: top of EXTENDING.md (before "Add a new description-quality rubric") or as a new section. Both work.
   - Recommendation: Add a new top-level section "## Testing an MCP server you didn't write" as the first section after the file's intro paragraph. Existing rubric/judge sections become operator-extension content lower in the file.

3. **Should the rewritten `--config path not found` error and the `MCPTF_CONFIG_FILE typo` error share text?**
   - What we know: SAFE-04 (Phase 13) wants symmetric behaviour; the actual paths-don't-exist message can be the same.
   - What's unclear: Phase 12 has `--config not found` already (cli.py:81-82), Phase 13 will add `MCPTF_CONFIG_FILE not found` — should the message be drafted in ERROR-STYLE.md now?
   - Recommendation: YES — draft a single SAFE-04 reference message in ERROR-STYLE.md alongside SAFE-03/SAFE-06 (D-17 explicitly names SAFE-03 and SAFE-06; SAFE-04 is a natural sibling). The rewrite at cli.py:81-82 implements it now.

4. **Does `list-tools --full` need pagination at N=70?**
   - What we know: D-06 says `--full` adds full description + per-param descriptions. At N=70 with maybe 5-10 lines each, that's 350-700 lines.
   - What's unclear: whether to print straight to stdout (operator can pipe to `less`) or auto-page via `typer.echo_via_pager`.
   - Recommendation: Plain `typer.echo` (no auto-page). Operators piping to `less` is the unix idiom; auto-pager surprises CI. Plan-phase can re-decide.

## Environment Availability

> SKIPPED — Phase 12 is purely code/config/docs changes against the already-shipped v1.1 framework. No new external dependencies, runtimes, or services are introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.x + pytest-asyncio 1.3.x (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit/test_cli.py -x` (assumes new tests land here per existing convention) |
| Full suite command | `uv run pytest tests/ -m 'not live_homelab and not live_ollama'` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLEAN-01 | No leaked spec IDs in 4 target files | unit (banned-token grep) | `pytest tests/unit/test_doc_scrub.py -x` | ❌ Wave 0 — new test |
| CLEAN-02 | `config.example.yaml` parses + matches the 3-pattern shape | unit | `pytest tests/unit/test_config_example.py -x` | ❌ Wave 0 — new test (or extend existing snippet-correctness suite) |
| CLEAN-03 | `examples/homelab-mcp.yaml` exists and parses | unit | `pytest tests/unit/test_examples_dir.py -x` | ❌ Wave 0 — new test |
| CLEAN-04 | README links resolve | manual | (visual review of rendered README) | n/a |
| CLEAN-05 | `config-init` output loads via `Config()` and runs without `.env` | unit | `pytest tests/unit/test_config_init.py::test_scaffold_loadable -x` | ❌ Wave 0 — new test (extend existing test_cli.py if present) |
| CLEAN-06 | `.env.example` framing — text presence | unit (string match) | `pytest tests/unit/test_dotenv_example.py -x` | ❌ Wave 0 — new test |
| PERSONA-01 | README has "Testing an MCP server you didn't write" heading | unit | grep test in test_doc_scrub.py | ❌ Wave 0 — covered by CLEAN-01 test |
| PERSONA-02 | `list-tools` default render contains a `(...)` signature line per tool | unit | `pytest tests/unit/test_cli.py::test_list_tools_default_signature -x` | ❌ Wave 0 — new test |
| PERSONA-02 | `--full` adds per-param descriptions | unit | `pytest tests/unit/test_cli.py::test_list_tools_full -x` | ❌ Wave 0 — new test |
| PERSONA-02 | `--name PATTERN` substring filter | unit | `pytest tests/unit/test_cli.py::test_list_tools_name_filter -x` | ❌ Wave 0 — new test |
| PERSONA-03 | Each rewritten error message has no banned tokens + has a `next:` line | unit (banned-token grep over emitted text) | `pytest tests/unit/test_error_style.py -x` | ❌ Wave 0 — new test |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/ -x` (≤ 5s for new unit tests)
- **Per wave merge:** `uv run pytest tests/ -m 'not live_homelab and not live_ollama'` (existing v1.1 default; ~22s per README sample run)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_doc_scrub.py` — banned-token grep test over the 4 target files (covers CLEAN-01 + PERSONA-01 heading presence). Implements Pitfall 6's manual review programmatically.
- [ ] `tests/unit/test_config_init.py` (or extend existing) — assert `config-init` output round-trips through `Config()` without `MCPTF_CONFIG_FILE` set and without a `.env` file present (CLEAN-05 acceptance).
- [ ] `tests/unit/test_cli.py` extensions — `--full`, `--name PATTERN`, default-render-has-signature (PERSONA-02).
- [ ] `tests/unit/test_error_style.py` — banned-token grep over emitted error text from `_emit_operator_error` callsites + presence of `next:` line (PERSONA-03 + ERROR-STYLE.md rule 1+2).
- [ ] `tests/unit/test_config_example.py` — assert `config.example.yaml` has exactly 3 placeholder tool entries with names matching `<.*>` and parses (CLEAN-02).
- [ ] `tests/unit/test_examples_dir.py` — assert `examples/homelab-mcp.yaml` exists and parses; assert `examples/README.md` exists and contains a link to `homelab-mcp.yaml` (CLEAN-03).

*(No new framework install needed — pytest + pytest-asyncio already configured per `pyproject.toml`.)*

## Security Domain

> Skipped — phase introduces no new auth, session, access-control, crypto, or input-validation surface. The doc/example scrub is INFORMATION-only: removes references that could leak architectural detail (TOOLCFG / D- / Plan IDs) but introduces no new attack surface or trust boundary.

The most security-adjacent change is CLEAN-06 (`.env.example` reframed as CI-secret passthrough only) which REDUCES surface (env vars no longer overlay config in v1.2 Phase 13; Phase 12 only documents the upcoming change). No ASVS category newly applies.

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python 3.14, `uv` for dependency management — pinned in `.python-version` and `pyproject.toml`. (Honored — no new deps.)
- **MCP transport:** stdio only via the official `mcp` SDK's `stdio_client` context manager — no raw `subprocess.Popen`. (Honored — `_list_tools_async` reuses the existing seam.)
- **Async:** `asyncio.timeout` (3.11+) wraps any subprocess or HTTP operation that could hang. (Honored — no new I/O paths added.)
- **Black box:** never import, read, or vendor `homelab-mcp` source. (Honored — `examples/homelab-mcp.yaml` is operator-supplied configuration, not vendored source.)
- **Pass threshold:** judge tests pass at `score >= 4`. (Not in scope — Phase 12 doesn't touch judges.)
- **GSD workflow enforcement:** all file edits go through a GSD command. (Followed — research is the GSD-research-phase product.)
- **Spec preservation:** `docs/mcp_test_framework_mvp_spec.md` preserved verbatim per PROJECT.md. (Honored — Phase 12 does not edit the spec.)

## Sources

### Primary (HIGH confidence)
- Codebase grep — `cli.py`, `config.py`, `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md` (verified leak counts and existing patterns)
- `.planning/phases/12-doc-persona-foundation/12-CONTEXT.md` — D-01 through D-17 locked decisions
- `.planning/REQUIREMENTS.md` — CLEAN-01..06 + PERSONA-01..03 wording
- PyPI `ruamel.yaml` 0.19.1 (released 2026-01-02) — verified currency for the rejected-alternative analysis
- [ruamel.yaml.dev](https://yaml.dev/doc/ruamel.yaml/detail/) — round-trip mode required for comments; `typ='safe'` strips them
- [Click documentation — Exception Handling](https://click.palletsprojects.com/en/stable/exceptions/) — `ClickException.show()` auto-prefixes `"Error: "` (the reason to prefer `typer.echo + typer.Exit`)
- [Typer Terminating tutorial](https://typer.tiangolo.com/tutorial/terminating/) — `typer.Exit(code=N)` is the idiomatic exit
- [Typer release notes](https://typer.tiangolo.com/release-notes/) — typo-suggestion behaviour (default-on since 0.20.0; informs `--name` filter UX)

### Secondary (MEDIUM confidence)
- WebSearch + multi-source verification — `ruamel.yaml` vs PyYAML for comment preservation
- Auto-memory items: `feedback_scaffold_completeness.md`, `project_doc_scrub_planning_artifacts.md`, `project_genericize_example_config.md`, `project_vibe_coded_persona.md`, `project_output_ergonomics_at_scale.md`, `project_config_discovery_and_safety.md` — all align with locked decisions

### Tertiary (LOW confidence — flagged but not load-bearing)
- General CLI UX patterns ("cargo `help:` suggestion") — informed Pattern 2 but the actual style is locked in CONTEXT.md D-16
- `schemathesis` / `pact-python` README framing — search returned no specific phrasing matches; persona-framing language drawn from CONTEXT.md `<specifics>` instead

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libs already in use, verified by codebase grep
- Architecture: HIGH — locked by CONTEXT.md D-01..D-17; research confirms no library swap is justified
- Pitfalls: HIGH — five of six pitfalls identified by direct code reading; Pitfall 6 (rewrites still leak jargon) is a process risk, not a code risk
- Code examples: HIGH — drop-in shapes against the existing typer/cli.py structure; all f-strings tested mentally against the existing `_format_tools_yaml_scaffold` style

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 days; stack is stable, no fast-moving deps in scope)
