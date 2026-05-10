---
status: complete
phase: 12-doc-persona-foundation
source:
  - 12-01-SUMMARY.md
  - 12-02-SUMMARY.md
  - 12-03-SUMMARY.md
  - 12-04-SUMMARY.md
  - 12-05-SUMMARY.md
  - 12-06-SUMMARY.md
started: 2026-05-10T04:19:28Z
updated: 2026-05-10T04:25:30Z
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
  artifacts: []
  missing: []
  note: "File exists at repo root (807 bytes, ungitignored); failure is discoverability/visibility, not the file itself."

- truth: "An operator with a uvx-installed MCP server can run `mcp-test-framework config-init` against their server out of the box and get a populated scaffold"
  status: failed
  reason: "User reported: config-init failed with `MCP server command not found: 'homelab-mcp'`. The default `mcp_server.command: homelab-mcp` requires the server to be on PATH, but uvx-installed servers are launched via `uvx homelab-mcp`. Operator must hand-write a minimal config.yaml (mcp_server.command: uvx, args: [homelab-mcp]) BEFORE config-init can discover tools — circular onboarding."
  severity: major
  test: 7
  artifacts:
    - src/mcp_test_framework/cli.py  # config-init command + _list_tools_async
    - src/mcp_test_framework/config.py  # mcp_server defaults
    - docs/EXTENDING.md  # walkthrough Step 2 doesn't cover this case
  missing:
    - "config-init CLI flags to override mcp_server.command/args inline (e.g. --command uvx --arg homelab-mcp), OR"
    - "EXTENDING.md walkthrough Step 2 augmented with a 'using uvx/pipx-installed servers' subsection that walks through the minimal pre-config, OR"
    - "config-init falls back to a no-tools scaffold + clear next-step when launch fails, so the operator can fill in command/args from the generated file rather than starting from a blank slate"
  note: "Side benefit: this surfaced positive evidence that the operator-tone error helper (PERSONA-03) works as designed — summary/detail/next: format rendered correctly with an actionable recovery hint."

- truth: "Framework auto-discovers a `config.yaml` at the cwd / repo root without requiring an explicit `--config` flag or `MCPTF_CONFIG_FILE` env var"
  status: failed
  reason: "User created config.yaml at repo root with mcp_server.command/args set, then ran `uv run mcp-test-framework list-tools` (no --config flag). Same `MCP server command not found: 'homelab-mcp'` error fired — proving the framework still loaded defaults instead of the on-disk config.yaml. Adding `--config config.yaml` made it work. Aligns with project memory `project_config_discovery_and_safety` (vanilla v1.1 run with no config silently runs)."
  severity: major
  test: 8
  artifacts:
    - src/mcp_test_framework/config.py  # Settings sources / discovery hook
    - src/mcp_test_framework/cli.py     # _load_config — only triggers on explicit --config
    - docs/EXTENDING.md                  # walkthrough should document --config OR fix discovery
  missing:
    - "Auto-discover config.yaml in cwd (and walk up to repo root) when neither --config nor MCPTF_CONFIG_FILE is set, OR"
    - "EXTENDING.md walkthrough Step 4 (run) explicitly says 'pass --config config.yaml' so the operator isn't blindsided by the silent-defaults behavior"
  note: "Pre-existing v1.2 backlog item per memory; surfaced organically during Phase 12 UAT, confirming the operator-onboarding pain is real."
