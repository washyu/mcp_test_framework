---
status: diagnosed
phase: 12-doc-persona-foundation
source:
  - 12-01-SUMMARY.md
  - 12-02-SUMMARY.md
  - 12-03-SUMMARY.md
  - 12-04-SUMMARY.md
  - 12-05-SUMMARY.md
  - 12-06-SUMMARY.md
started: 2026-05-10T04:19:28Z
updated: 2026-05-10T04:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. README persona-first framing
expected: Open README.md. Near the top there's a section titled "Testing an MCP server you didn't write" that frames the framework's black-box stance as a feature for vibe-coded servers, with a deep-link into docs/EXTENDING.md for the walkthrough. No internal spec IDs (Phase N, Plan N-N, TOOLCFG-, D-N, CLEAN-, PERSONA-, SAFE-) appear anywhere in the README.
result: pass

### 2. EXTENDING walkthrough is the operator's first stop
expected: Open docs/EXTENDING.md. The first section after the intro is "Testing an MCP server you didn't write" with a 4-step walkthrough — discover via list-tools, scaffold via config-init, opt-in tool-by-tool, run. No file:line citations, no Phase/Plan IDs.
result: pass

### 3. config.example.yaml is a generic placeholder template
expected: Open config.example.yaml. It's ~50–80 lines of generic template — three placeholder tool entries (<safe_read_tool_a>, <safe_read_tool_b>, <destructive_tool_c>) demonstrating three opt-in patterns (judges-subset, call_arguments, skip-with-reason). No homelab-mcp tool names, no `target:` block, no spec IDs. Comments at the top point at `mcp-test-framework config-init` and `examples/homelab-mcp.yaml`.
result: pass

### 4. examples/homelab-mcp.yaml exists as a worked reference
expected: examples/homelab-mcp.yaml exists alongside examples/README.md. The README explains the one-server-per-file convention and links to homelab-mcp.yaml as the worked reference.
result: pass

### 5. .env.example is CI-secret passthrough, not config overlay
expected: Open .env.example. It's ~12–20 lines framed as "env vars are CI-secret passthrough only" — JUDGE_API_KEY shown commented out as the canonical example, MCPTF_CONFIG_FILE hint preserved, and the reader is pointed at `mcp-test-framework config-init -o config.yaml` for actual configuration. No TARGET_TOOL_NAME / MCP_SERVER_COMMAND / OLLAMA_* declarations from v1.1.
result: issue
reported: "i don't see the .env.example file in the file browser for this workspace"
severity: minor
note: "File exists at repo root (807 bytes, not gitignored); finding is discoverability, not absence — operator can't locate the file from the workspace UI."

### 6. ERROR-STYLE.md style guide locked
expected: docs/ERROR-STYLE.md exists. Contains the 4-rule operator-tone style guide, an exit-code contract table, and the SAFE-03 + SAFE-06 reference message bodies locked verbatim for downstream config-safety work. No "Phase 13" mentions outside the banned-strings checklist.
result: pass

### 7. config-init produces a runnable, self-contained scaffold
expected: Run `uv run mcp-test-framework config-init -o /tmp/test-scaffold.yaml` (or any writable path) against the configured MCP server. The generated file has top-level `ollama:`, `mcp_server:`, `judge_timeout_seconds:`, `version: 1`, and `tools:` blocks all populated with literal values. Every discovered tool is emitted with `skip: true` + a curated `skip_reason`. No `target:` block. The file loads without an `.env` present.
result: issue
reported: "config-init failed with `MCP server command not found: 'homelab-mcp'` — operator-tone error fired correctly, but `uvx homelab-mcp` works fine from the same shell, so the default `mcp_server.command: homelab-mcp` is wrong for uvx-installed servers. Operator can't bootstrap a scaffold without first hand-writing a minimal config.yaml."
severity: major
note: "Bootstrap chicken-and-egg: config-init exists to discover tools and write config, but it needs a working mcp_server.command to launch the server, which the operator can only set by writing a config first. EXTENDING.md walkthrough Step 2 (scaffold via config-init) doesn't cover this. Side observation: operator-tone error message itself worked perfectly — counts as positive evidence for Tests 11/12."

### 8. list-tools default render shows signatures
expected: Run `uv run mcp-test-framework list-tools`. Each tool shows a signature-first block — name + `(host: str, *, timeout: int = 30)`-style signature derived from inputSchema, plus a one-line shortened description. Useful at N=70 tools (compact, scannable).
result: pass
note: "Required `--config config.yaml` workaround — bare `list-tools` failed because framework does not auto-discover config.yaml in cwd (separate gap logged)."

### 9. list-tools --full shows per-parameter detail
expected: Run `uv run mcp-test-framework list-tools --full`. Each tool block expands with wrapped description and a `parameters:` block listing per-param descriptions from inputSchema.
result: pass

### 10. list-tools --name PATTERN filters by substring
expected: Run `uv run mcp-test-framework list-tools --name list` (or any substring matching some of your tools). Output is restricted to tools whose names contain the substring (case-insensitive). If the filter matches nothing, the message names both the filter and the unfiltered server total so the operator knows the filter (not the server) caused the empty result.
result: pass

### 11. config-not-found error is operator-tone
expected: Run `uv run mcp-test-framework run --config /does/not/exist.yaml`. Stderr shows a short summary line, a detail block, and a `next:` line with an actionable recovery step (e.g., "run mcp-test-framework config-init -o config.yaml"). Exit code is non-zero. No stack trace, no spec IDs, no Phase/Plan references.
result: pass

### 12. config-init refuse-overwrite is operator-tone
expected: Run `uv run mcp-test-framework config-init -o config.yaml` twice (the second invocation against the same path that already exists). The second run refuses to overwrite, prints an operator-tone summary/detail/next-step, and exits non-zero. The recovery step names a concrete action (e.g., `--force`, or pick another path).
result: pass

## Summary

total: 12
passed: 9
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: ".env.example is visible/discoverable to the operator opening the workspace"
  status: failed
  reason: "User reported: i don't see the .env.example file in the file browser for this workspace"
  severity: minor
  test: 5
  root_cause: "Documentation disconnect, not a code defect. (1) docs/EXTENDING.md PERSONA-01 walkthrough never mentions .env.example — operator following the canonical entry point is never told the file exists or when they would touch it. (2) README.md mentions .env.example 4x as imperative `cp .env.example .env` setup, contradicting the file's own v1.1 framing ('env vars no longer override config values'). (3) Editor dotfile-hiding defaults are a contributing environmental factor; repo ships no .vscode/settings.json to override."
  artifacts:
    - path: docs/EXTENDING.md
      issue: "PERSONA-01 walkthrough (Steps 1–4) has zero mentions of .env.example, .env, environment variables, or CI secrets"
    - path: README.md
      issue: "Lines 25, 32, 85–86, 91 reference .env.example as imperative setup, contradicting v1.1 CI-secret-passthrough framing"
    - path: .env.example
      issue: "Content is correct; framing is orphaned because no operator-facing doc points operators here for the right reason"
  missing:
    - "Brief mention in docs/EXTENDING.md (post Step 4 or in a 'CI secrets' subsection) that .env.example exists for CI-secret passthrough only and is NOT part of normal local configuration"
    - "Reconcile README.md — drop the `cp .env.example .env` imperative and reference the file once with the same CI-secret framing the file uses internally"
    - "(Optional) ship a tracked .vscode/settings.json with `files.exclude: {}` to defeat default dotfile-hiding in VSCode/Cursor — would need a .gitignore carve-out"
  debug_session: .planning/debug/dotenv-example-invisible.md
  note: "File exists at repo root (807 bytes, ungitignored); failure is discoverability/visibility, not the file itself. Doc-only fix is in Phase 12 scope."

- truth: "An operator with a uvx-installed MCP server can run `mcp-test-framework config-init` against their server out of the box and get a populated scaffold"
  status: failed
  reason: "User reported: config-init failed with `MCP server command not found: 'homelab-mcp'`. The default `mcp_server.command: homelab-mcp` requires the server to be on PATH, but uvx-installed servers are launched via `uvx homelab-mcp`. Operator must hand-write a minimal config.yaml (mcp_server.command: uvx, args: [homelab-mcp]) BEFORE config-init can discover tools — circular onboarding."
  severity: major
  test: 7
  root_cause: "Bootstrap chicken-and-egg confirmed. config-init must launch the MCP server to discover tools, but exposes only --config / --output / --force flags (cli.py:384-405) — no inline override for mcp_server.command/args. On a fresh checkout with no .env / no pre-existing config.yaml, the only source firing for mcp_server.command is the Pydantic default `command='homelab-mcp', args=[]` (models.py:61-68). That default is project-bias from the pre-v1.2 spec — it requires PATH-installation and fails for uvx/pipx-launched servers. The operator-tone error then directs them to 'update mcp_server.command/args in your config.yaml' — the file config-init exists to PRODUCE. Notably, the scaffold OUTPUT itself (cli.py:698-700) hard-codes `command: 'uvx', args: ['your-mcp-server-package']` — proving the scaffold author already understood uvx is the operator-friendly default, but that insight never made it back into McpServerConfig defaults or a bootstrap path."
  artifacts:
    - path: src/mcp_test_framework/models.py
      issue: "Lines 61-68: McpServerConfig.command default is the literal 'homelab-mcp' and args default is empty list — leaks project-bias into a generic framework"
    - path: src/mcp_test_framework/cli.py
      issue: "Lines 384-481: config_init Typer command defines no override flags; on FileNotFoundError raises typer.Exit(2) with no fallback (does NOT write a stub scaffold the operator can fill in)"
    - path: docs/EXTENDING.md
      issue: "Lines 36-41: Walkthrough Step 2 says 'the framework will launch the server' with zero acknowledgement of needing the server on PATH or pre-setting mcp_server.command for uvx/pipx-installed servers"
  missing:
    - "PRIMARY: Add `--command` / `--arg` override flags to config-init Typer command. One-line invocation gets the operator unstuck: `mcp-test-framework config-init --command uvx --arg homelab-mcp -o config.yaml`. Mechanically clean — Pydantic init kwargs are highest-precedence per config.py:202-217."
    - "SECONDARY: On launch failure, write a partial scaffold with `tools: []` and a header comment ('# Could not discover tools — fill mcp_server.command/args below and re-run config-init'). Aligns with memory `feedback_scaffold_completeness` ('Scaffolds must be runnable')."
    - "DOC-ONLY: Update EXTENDING.md Step 2 with a 'using uvx/pipx-installed servers' subsection. Necessary regardless of code fix; on its own forces a contradictory two-step (hand-write yaml THEN config-init --config) that defeats the scaffold's purpose."
    - "DEFERRED: Make mcp_server.command default to None — strictly correct (kills homelab-mcp project-bias) but a breaking change; v1.2 redesign per memory `project_genericize_example_config`."
  debug_session: .planning/debug/config-init-bootstrap-egg.md
  note: "Recommended package: PRIMARY + SECONDARY + DOC-ONLY. Side benefit: the operator-tone error helper (PERSONA-03) rendered correctly with an actionable recovery hint — positive evidence in disguise."

- truth: "Framework auto-discovers a `config.yaml` at the cwd / repo root without requiring an explicit `--config` flag or `MCPTF_CONFIG_FILE` env var"
  status: failed
  reason: "User created config.yaml at repo root with mcp_server.command/args set, then ran `uv run mcp-test-framework list-tools` (no --config flag). Same `MCP server command not found: 'homelab-mcp'` error fired — proving the framework still loaded defaults instead of the on-disk config.yaml. Adding `--config config.yaml` made it work."
  severity: major
  test: 8
  root_cause: "Locked-by-design behavior, not a bug. config.py:205-215 settings_customise_sources reads MCPTF_CONFIG_FILE env var; if unset, the YamlConfigSettingsSource is never appended. The module docstring (config.py:10-13) explicitly cites the MVP CONTEXT.md decision: 'YAML overlay path comes ONLY from the MCPTF_CONFIG_FILE env var (no cwd auto-discovery in MVP).' README.md and docs/EXTENDING.md actively teach the broken mental model — README lines 45 / 60 show flagless `mcp-test-framework run` and `list-tools` as the FIRST quickstart examples; EXTENDING.md is internally inconsistent (4 of 5 walkthrough invocations omit --config; only Step 4 line 55 includes it). SEED-006 in .planning/seeds/ already designs the v1.2 fix (Component 2 = cwd auto-discovery, Component 3 = fail-loud no-config, Component 5 = .env precedence reform)."
  artifacts:
    - path: src/mcp_test_framework/config.py
      issue: "Lines 205-215: YAML source gated entirely on MCPTF_CONFIG_FILE; no cwd fallback. Lines 10-13 cite the locked CONTEXT.md decision needing amendment for any code fix."
    - path: src/mcp_test_framework/cli.py
      issue: "Lines 178-211: _load_config(None) returns Config() without probing cwd. The path-None branch is the natural insertion point for a surgical fix."
    - path: README.md
      issue: "Lines 45, 60: quickstart code blocks teach flagless invocation as 'should just work'; line 92 prose contradicts the code blocks above."
    - path: docs/EXTENDING.md
      issue: "Internal inconsistency: lines 22, 38, 176, 179 omit --config; only line 55 (Step 4) includes it. Even the canonical walkthrough doesn't agree with itself."
    - path: tests/unit/test_config.py
      issue: "Lines 40-46: _isolate_cwd autouse fixture is the right pattern for any new cwd-discovery test isolation; existing 'no env = defaults' tests (186, 195) need re-review under any new behavior."
  missing:
    - "OPTION A (Code fix): Register `YamlConfigSettingsSource(yaml_file=Path.cwd() / 'config.yaml')` in config.py:settings_customise_sources as the default fallback when MCPTF_CONFIG_FILE is unset. Combine with SEED-006 Components 3 (fail-loud) and 5 (.env precedence reform) to avoid deepening the precedence puzzle (memory `project_dotenv_silently_beats_config`). Requires CONTEXT.md decision-record amendment."
    - "OPTION C (Doc-only, zero-risk interim): Always show `--config config.yaml` in README quickstart and EXTENDING.md Steps 1/2 + 'Add a new MCP tool target' Steps 1/4. Stops actively teaching the broken mental model. Does not require touching the locked decision."
    - "TEST: Add a test that asserts current behavior (no auto-discovery) so future work picks it up deliberately, OR (if Option A taken) a test asserting cwd/config.yaml is auto-loaded."
  debug_session: .planning/debug/config-yaml-auto-discovery-missing.md
  note: "Per memory `project_config_discovery_and_safety` and SEED-006: Option A is the v1.2 redesign target and is OUT of phase 12 scope (would reopen a locked decision). Option C (doc-only) is in scope and high-leverage for phase 12 — fixes the actively-misleading docs without touching runtime."
