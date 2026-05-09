---
id: SEED-009
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete (between-milestones)
trigger_when: v1.2 milestone framing — surface during /gsd-new-milestone questioning step. Should land EARLY in v1.2 so other phases operate on clean docs
scope: Small
---

# SEED-009: Doc & example cleanup phase (v1.2)

## Why This Matters

User-facing artifacts in v1.1 carry three classes of leakage that a vibe-coded-MCP user (SEED-007) would find baffling or homelab-specific:

1. **GSD planning provenance** — phase numbers, plan IDs, quick-task IDs leaking into README / config.example.yaml / .env.example / EXTENDING.md
2. **Internal spec IDs** — `TOOLCFG-01..07`, `D-cli-flags-3`, `ISOL-04`, `OUTPUT-01`, `CD-05` — load-bearing in source code as code↔spec cross-references but cryptic to users
3. **Homelab-mcp branding** — `config.example.yaml` has ~50 homelab-specific tool names; defaults reference `uvx homelab-mcp`; README's worked example is `list_keyring_credentials`

Audit count at flag time (2026-05-08): **18 phase/plan/spec ID occurrences** across `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md`. Plus the homelab-mcp saturation throughout `config.example.yaml`.

User flagged the homelab branding believing v1.1 Phase 11 had scrubbed it — actually false: Phase 11 closed verification audit gaps (W-1..W-6), and the homelab scrub was a **v1.0 deferred item** ("open-source pre-flight scrub: homelab IP from README + homelab-specific captures from `.planning/`") that was never executed because it was gated on "if/when the repo goes public."

Also folded in: **scaffold completeness.** `mcp-test-framework config-init` currently emits only `version: 1` + a `tools:` block — missing the top-level `ollama:` / `mcp_server:` / `target:` / `judge_timeout_seconds:` sections. The result loads only because env defaults backfill — a "starter config" should be self-contained.

## When to Surface

**Trigger:** v1.2 milestone framing — surface during `/gsd-new-milestone` questioning step. **Should land EARLY in v1.2** so other phases operate on clean docs and aren't churned twice.

This seed should be presented when the new milestone scope mentions any of:
- Documentation / docs / README
- Examples / config.example / scaffold
- Open-source / public release / generic / vibe-coded
- Cleanup / hygiene / paperwork

## Scope Estimate

**Small** — One phase, mechanical work. The cleanup is read-restate-delete; no design decisions, no algorithmic changes. Mirrors the v1.1 Phase 11 "cleanup" model.

## Components

### 1. Strip planning-artifact references

Two classes, handled differently:

- **Phase / Plan / quick-task IDs** (`Phase 04.1`, `Plan 05-05`, `260507-n0g`, `FINDINGS-260506-qxs`) — pure planning provenance. Zero value to a framework user. **Delete or restate as prose.**
- **Spec IDs** (`TOOLCFG-01..07`, `D-cli-flags-3`, `ISOL-04`, `OUTPUT-01`, `CD-05`) — load-bearing in source code as code↔spec cross-references, but cryptic to users. **Keep in `src/` and `tests/` comments where they help maintainers; strip from user-facing docs.**

### 2. Genericize examples

- `config.example.yaml` → generic placeholders (`<safe_read_tool_a>`, `<your_tool_name>`, etc.). Already the pattern the README's per-tool config section uses — propagate to the live example file.
- `examples/homelab-mcp.yaml` (new file) → the current `config.example.yaml` verbatim, moved into an `examples/` directory as a reference for operators using homelab-mcp specifically.
- README worked examples → switch to generic placeholders; add a "real-world example" link pointing at `examples/homelab-mcp.yaml`.
- `.env.example` → keep `uvx homelab-mcp` as a runnable default? Or make it `<your-mcp-command>`? **Open question** — probably keep as-is so `uv run mcp-test-framework list-tools` works first-time, but add a comment pointing at `examples/`.
- `Config()` defaults in `models.py` — keep `mcp_server.command="homelab-mcp"` for now; the field is overrideable and changing the runtime default has a bigger blast radius than docs.

### 3. Scaffold completeness

`mcp-test-framework config-init` should emit a complete, self-contained starter config:

- Dump the resolved current `Config()` as a populated preamble (commented sections matching defaults; live values for non-defaults).
- Add the `tools:` block underneath.
- Add a header comment warning if env-resolved values (e.g. base URLs) get serialized — caller's responsibility to scrub before commit.

If SEED-006 lands first, `config-init` should reflect the opt-in model — emit a small allowlist of recommended starter tools rather than the v1.1 minimal scaffold.

### 4. Regression guard (optional)

Add a CI / lint check (or a doc-snippet test, mirroring `tests/test_readme_snippets.py`) that fails if `Phase \d|Plan \d|TOOLCFG-|D-\w|CD-\w|ISOL-\w|OUTPUT-\w|\d{6}-\w{3}|FINDINGS-` matches inside `README.md|config.example.yaml|.env.example|docs/EXTENDING.md`. Prevents regression.

## Tradeoff: zero-config homelab UX

Operators currently using `cp config.example.yaml config.yaml` and getting a working homelab setup zero-config lose that flow — they'd need `cp examples/homelab-mcp.yaml config.yaml` instead. Acceptable cost for the repositioning per SEED-007.

## Sequencing Within v1.2

**FIRST** in v1.2 (or first phase pair). Reasons:

- Cheapest item — pure mechanical work
- Foundational hygiene that other phases benefit from (clean docs, generic examples)
- Avoids churning docs twice if they shift mid-milestone
- The `config-init` scaffold-completeness work feeds directly into SEED-006's failsafe error message (the failsafe should reference `config-init` as the recovery action; the scaffold therefore needs to actually be runnable)

## Breadcrumbs

- `README.md` (~5 phase/plan refs)
- `config.example.yaml` (~9 phase/plan/spec refs + ~50 homelab-specific tool entries)
- `docs/EXTENDING.md` (~3 refs)
- `.env.example` (~1 ref + `uvx homelab-mcp` defaults)
- `src/mcp_test_framework/cli.py:_format_tools_yaml_scaffold` (config-init scaffold builder — line 386)
- `src/mcp_test_framework/models.py` (`mcp_server.command="homelab-mcp"` default)
- `tests/test_readme_snippets.py` (existing snippet-correctness regression test pattern; extend for the planning-artifact regex)

## Related Memories

- project_doc_scrub_planning_artifacts.md
- project_genericize_example_config.md
- feedback_scaffold_completeness.md
