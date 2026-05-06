# Phase 5: CLI, README & Acceptance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 05-cli-readme-acceptance
**Areas discussed:** Pytest flag forwarding, list-tools output format, Ctrl+C teardown strategy, README depth/structure

---

## Pytest Flag Forwarding

User asked a clarifying question first: "Are we just talking about being able to allow users to use the other pytest CLI arguments? what arguments are we tacking on that are custom?" Reframed the question after surfacing that only `--config PATH` is genuinely custom; `-k` and `-v` already exist in pytest and would work for free via forwarding.

### Question 1: What's the framework-owned flag surface for `run`?

| Option | Description | Selected |
|--------|-------------|----------|
| Just --config + forward | Typer owns only `--config PATH`. Everything else goes to pytest.main(). -k/-v/-x/--lf all work for free via forwarding. Config-value overrides via env vars on command line. | ✓ |
| + Per-setting overrides | Add --ollama-url, --ollama-model, --mcp-command, --target-tool. Honors PROJECT.md's "CLI flags = highest precedence" literally. | |
| + Debug toggles only | Just --config + small debug set (--no-preflight, --verbose-logging). | |

**User's choice:** "Just --config + forward" + plant a Plant-Seed for re-evaluating pytest as the runner post-MVP (custom runner / wrap + ship pytest.ini / leave as-is).
**Notes:** User's verbatim instruction: "Lets do 1 and add a seed to revalue pytest or just wrap it and add a pytest config file or go with our own or just leave it." Captured in Deferred Ideas with explicit trigger conditions.

### Question 2: How should pytest flags reach pytest?

| Option | Description | Selected |
|--------|-------------|----------|
| After `--` separator | `mcp-test-framework run --config foo.yaml -- -x --lf -k pattern`. Explicit boundary; future-proof against CLI flag collisions. Matches git/cargo/npm convention. | ✓ |
| allow_extra_args | `mcp-test-framework run --config foo.yaml -x --lf`. No separator needed; future CLI flag with same name as pytest one would silently shadow. | |

**User's choice:** After `--` separator.
**Notes:** Locked the canonical invocation as `mcp-test-framework run --config foo.yaml -- -x --lf -k pattern`.

---

## list-tools Output Format

### Question 1: What's the default `list-tools` output?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text, two columns | `name  description-first-line` per row, aligned. Pipe-friendly via awk/cut. | |
| Indented blocks | Tool name on its own line, indented description below. Easier multi-line description rendering. | ✓ |
| rich-formatted table | Pretty boxed table with rich. Adds dependency. | |

**User's choice:** Indented blocks.
**Notes:** Rendered preview swayed the choice — readable for multi-line tool descriptions, no extra dependency.

### Question 2: Add a --json flag for machine consumption?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, --json flag | `list-tools --json` emits JSON array of {name, description, inputSchema, outputSchema} per tool. | ✓ |
| No, human-only | Plain text only. | |
| Plant Seed for later | Plain text now; capture --json as deferred. | |

**User's choice:** Yes, --json flag.

### Question 3: What goes in the indented-block default output?

| Option | Description | Selected |
|--------|-------------|----------|
| Name + full description | Two-section output per tool: name (one line), full description (wrapped, indented). No schemas. | ✓ |
| + Parameter list | Name + description + indented parameter names with types. | |
| + Full schema | Name + description + full inputSchema (pretty-printed JSON). | |

**User's choice:** Name + full description.

### Question 4: What goes in --json output?

| Option | Description | Selected |
|--------|-------------|----------|
| Full tool spec | Array of {name, description, inputSchema, outputSchema} — raw MCP tool record. | ✓ |
| Name + description only | Just {name, description}. | |
| Configurable via --json-fields | Default to full spec, allow filter. | |

**User's choice:** Full tool spec.
**Notes:** SEED-001 (LLM-test-generator) directly consumes the inputSchema/outputSchema fields — shipping the full record now means the seam is in place.

---

## Ctrl+C Teardown Strategy

### Question 1: How should `list-tools` handle Ctrl+C?

| Option | Description | Selected |
|--------|-------------|----------|
| asyncio.Runner + AsyncExitStack | Reuse Phase 04.1's pure-asyncio fixture-body pattern at the CLI surface. | ✓ |
| Custom signal handler | Install SIGINT handler that explicitly cancels the running task and runs the AsyncExitStack. | |
| Rely on stdio_client only | Just `async with stdio_client(...)` and trust the SDK. | |

**User's choice:** asyncio.Runner + AsyncExitStack.
**Notes:** Reuses the proven pattern from the resolved DEF-04-03-B fix; avoids re-introducing the cancel-scope teardown bug at a new surface.

### Question 2: How do we PROVE OPS-03 is satisfied?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual UAT in /gsd-verify-work | Verifier runs `mcp-test-framework list-tools`, hits Ctrl+C, runs `Get-Process homelab-mcp` and asserts no matches. | ✓ |
| Automated regression test | Spawn CLI as subprocess from a test, send SIGINT, enumerate processes. | |
| Both | Manual UAT + automated regression test under tests/smoke/. | |

**User's choice:** Manual UAT in /gsd-verify-work.
**Notes:** Cross-platform process-enumeration flakiness was the deciding factor; matches Phase 04.1's manual-verification pattern.

### Question 3: Does `run` need any extra teardown wiring beyond pytest.main()?

| Option | Description | Selected |
|--------|-------------|----------|
| No — pytest + Phase 04.1 covers it | pytest.main() handles SIGINT itself; Phase 04.1's AsyncExitStack-owned fixture unwinds; stdio_client kills homelab-mcp. CLI just calls pytest.main() and returns its code. | ✓ |
| Wrap pytest.main() in a try/except | Catch KeyboardInterrupt at the CLI layer and explicitly handle. | |
| Run preflight in the CLI | Before delegating to pytest, run a CLI-side reachability check. | |

**User's choice:** No — pytest + Phase 04.1 covers it.

### Question 4: What happens to partial `list-tools` output on Ctrl+C?

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing — just clean exit | No interrupt message. Exit code 130 (standard SIGINT). | ✓ |
| Print 'interrupted' message | Catch KeyboardInterrupt at CLI top level, print friendly message, exit 130. | |

**User's choice:** Nothing — just clean exit.

---

## README Depth/Structure

### Question 1: What depth should the README target?

| Option | Description | Selected |
|--------|-------------|----------|
| Quickstart-focused | Setup, run, env-var table, precedence rule, Windows troubleshooting, links to spec. ~150 lines. | ✓ |
| Minimum viable | Setup + run + Windows troubleshoot bullet. ~50 lines. | |
| Reference-grade | Full env var table + YAML schema sample + precedence diagram + FAQ + how-to-extend + troubleshooting. ~300 lines. | |

**User's choice:** Quickstart-focused.

### Question 2: Where do extension recipes live?

| Option | Description | Selected |
|--------|-------------|----------|
| Out of README — plant seed | Defer extension docs entirely. | |
| Brief section in README | Short 'Extending the framework' section with one rubric subclass + one judge swap pointer. | |
| Separate docs/EXTENDING.md | Sibling doc; README links to it. | ✓ |

**User's choice:** Separate docs/EXTENDING.md.
**Notes:** Cleanest path if extension docs grow over time; keeps the first-run README readable in one sitting.

### Question 3: Should README include a sample test output snippet?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — green-run example | Include 10-15 lines of typical green pytest terminal output. | ✓ |
| No — just instructions | Don't show output samples. | |

**User's choice:** Yes — green-run example.
**Notes:** Disambiguates SC#6 ("standard pytest terminal output and exits 0").

### Question 4: Env var documentation source of truth?

| Option | Description | Selected |
|--------|-------------|----------|
| README table + .env.example | Markdown table (var, default, purpose) in README; .env.example as copy-paste starter. | ✓ |
| .env.example only, README points to it | Keep canonical list in .env.example only. | |
| Generate from Pydantic model | Auto-generate env var list from Config schema at build/CI time. | |

**User's choice:** README table + .env.example.

---

## Claude's Discretion

User passed on these — captured in CONTEXT.md `<decisions>` Claude's Discretion section. Highlights:
- `version` source (recommend `importlib.metadata.version("mvp-test-framework")`)
- `--config` error handling (propagate Pydantic / file-not-found errors with clean diagnostics; exit code 2 on config failure)
- Typer app shape (`no_args_is_help=True, add_completion=False`)
- `_load_config(config_path)` shared helper between `run` and `list-tools`
- Sort order for `list-tools` output (alphabetical by name)
- Text wrapping for default output (`textwrap.indent` + `textwrap.fill`, terminal-width or 80-column fallback; no `rich` dependency)
- `--json` formatting (`json.dumps(tools, indent=2, default=str)`)
- `docs/EXTENDING.md` structure (two H2 sections, ~80–120 lines)
- Sample-green-output capture (real run, not synthetic)
- README badge row (skipped — no CI yet)

## Deferred Ideas

- Re-evaluate the test runner post-MVP (custom executor / wrap + pytest.ini / leave as-is) — explicitly seeded during this discussion, captured with trigger conditions.
- Per-config-field CLI overrides (`--ollama-url`, `--mcp-command`, etc.).
- Auto-generated env-var docs from the Pydantic Config model.
- `--json-fields` filter on `list-tools --json`.
- `rich`-formatted `list-tools` output / colored CLI output.
- Automated regression test for OPS-03.
- CI badges / PyPI publish + badge row in README.
- `mcp-test-framework lint` / schema-only command (Category 1 deterministic checks without Ollama).
- `docs/EXTENDING.md` deeper recipes (custom transport, multi-tool parametrization, non-homelab-mcp servers).
- Interrupt message on Ctrl+C for `list-tools` (cheap retrofit if silent exit confuses users).
