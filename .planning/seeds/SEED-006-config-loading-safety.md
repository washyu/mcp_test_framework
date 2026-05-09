---
id: SEED-006
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete (between-milestones)
trigger_when: v1.2 milestone framing — surface during /gsd-new-milestone questioning step
scope: Medium
---

# SEED-006: Config loading safety + opt-in tool selection (v1.2)

## Why This Matters

v1.1's tool-selection model is opt-out (discover all tools, run all unless `skip:true`), and config loading has three precedence/discovery bugs that combine into a real safety hazard: a vanilla `mcp-test-framework run` with no `--config`, no `MCPTF_CONFIG_FILE`, and no `.env` produces `target.tool_name=None` + `tools={}` → discover everything, run everything, including destructive operations like `delete_proxmox_vm`. The only protection in v1.1 is "the operator read the README and set the right env var," which is too much trust in RTFM.

Real-world failure modes hit during 2026-05-08 manual UAT:
- Explicit `--config config.example.yaml` silently overridden by a forgotten `.env` (precedence puzzle)
- `MCPTF_CONFIG_FILE` typo silently drops the YAML source (no warning)
- 56 `skip: true` entries in YAML produce 560 `SKIPPED`-at-runtime lines + 691 collected count (a separate v1.1.1 bug; see project memory)

## When to Surface

**Trigger:** v1.2 milestone framing — surface during `/gsd-new-milestone` questioning step

This seed should be presented when the new milestone scope mentions any of:
- Config / configuration / settings
- Tool selection / tool filtering
- Safety / safe-by-default
- Precedence / overlay / env var handling
- Auto-discovery / discovery
- Vibe-coded / generic MCP / black-box

## Scope Estimate

**Medium** — One phase or one tightly-coupled phase pair. The five components below compose into a single coherent "safe by default" config layer; splitting them risks shipping partial migrations.

## Components

### 1. Three-state opt-in tool selection

`tools:` becomes an allowlist:

| In `tools:`? | `skip:` field | Result |
|---|---|---|
| No (unlisted) | n/a | Auto-skip with default reason `"not selected in config"` |
| Yes | `false` (default) | Runs |
| Yes | `true` + non-empty `skip_reason` | Skip with curated reason (preserves v1.1 model_validator) |

The "master config + focus toggle" workflow is preserved by state 3 — flip `skip:true` to disable a tool without deleting its `judges` / `call_arguments`.

See memory: `project_opt_in_tool_selection.md`

### 2. Auto-discover `cwd/config.yaml`

When `MCPTF_CONFIG_FILE` is unset, look for `./config.yaml` automatically. `--config PATH` continues to override (multi-config / focus-config workflow preserved).

See memory: `project_config_discovery_and_safety.md`

### 3. Fail-loud when no config anywhere

Emit a clear error pointing at `mcp-test-framework config-init -o config.yaml` rather than running with destructive defaults. Config becomes mandatory; the framework refuses to guess what to test.

### 4. MCPTF_CONFIG_FILE typo silent fail

`config.py:212` currently uses `Path.is_file()` guard that silently drops a missing path. Should error with exit code 2 mirroring the `--config` CLI behavior (`cli.py:80-83`). Inconsistent treatment of the same "where's the YAML" question.

See memory: `project_mcptf_config_file_silent_fail.md`

### 5. .env precedence reform

Real-world repro 2026-05-08: explicit `--config config.example.yaml` silently overridden by `.env`'s `TARGET_TOOL_NAME=list_keyring_credentials`. Open question: kill `.env` support, kill env-overlay entirely, or invert precedence so file wins over env when `--config` is explicit. **User leans toward dropping `.env` / env-overlay.** Decide explicitly during milestone framing.

See memory: `project_dotenv_silently_beats_config.md`

## Migration Story

Most v1.1 configs that listed every destructive tool with `skip:true` continue to work identically. Only configs that relied on **implicit opt-out behavior** (didn't list a tool but expected it to run) break. Likely warrants a `version: 2` bump in the config schema with a clear migration message that names the change.

## Sequencing Within v1.2

Compounds with SEED-008 (Reporter UX) and SEED-009 (Doc cleanup). Recommended order:

1. v1.1.1 hotfix (skip-doesn't-filter bug) — lands BEFORE v1.2 work so manual UAT becomes tractable
2. SEED-009 (doc + example cleanup) — foundational hygiene
3. **This seed** (semantic core)
4. SEED-008 (reporter UX layer over the new semantics)
5. SEED-007 (persona reframe shapes naming + README copy across all of the above)

## Breadcrumbs

- `src/mcp_test_framework/config.py:150-217` — Config + settings_customise_sources
- `src/mcp_test_framework/config.py:212` — silent-fail Path.is_file() guard
- `src/mcp_test_framework/cli.py:64-89` — _load_config (correctly errors on bad --config)
- `src/mcp_test_framework/models.py:101-159` — ToolConfig (skip / skip_reason / judges / call_arguments)
- `tests/conftest.py:87-124` — _resolve_tool_names (no skip filter — relates to v1.1.1 bug)
- `src/mcp_test_framework/fixtures.py:201-213` — explicit target.tool_name overrides skip:true
- `config.example.yaml` — 56-entry safe-by-default skip pattern (would shrink dramatically under opt-in)

## Related Memories

- project_opt_in_tool_selection.md
- project_config_discovery_and_safety.md
- project_mcptf_config_file_silent_fail.md
- project_dotenv_silently_beats_config.md
- project_v1_1_skip_bug.md (v1.1.1 hotfix dependency)
