---
phase: 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
plan: 05
requirements: [V1DROP-02]
status: complete
executed_inline: true
executed_by: orchestrator (worktree-base-drift workaround)
---

# 31-05 — V1DROP-02 doc cross-ref scrub

## Outcome

Scrubbed every operator-facing `MCPTF_CONFIG_FILE` mention and every
`docs/MIGRATION-v1-to-v2.md` cross-reference from the operator-facing doc
tree (README + ERROR-STYLE + LIBRARY-MODE + EXTENDING). The post-V1DROP doc
story is coherent: operators see a single two-route config story — `--config`
for the CLI, `[tool.pytest.ini_options] mcp_config_file = PATH` for library
mode.

## Tasks

### Task 1 — README.md + docs/EXTENDING.md scrub (commit `df6357f`)

Four sites in `README.md`:
- L73 — removed "migration from `MCPTF_CONFIG_FILE`" from the LIBRARY-MODE link description.
- L329–332 — rewrote the configuration prose to drop the deprecation/migration callout; now describes the two surviving routes directly.
- L343 — removed the `MCPTF_CONFIG_FILE` table row from the env-var table.
- L350 — rewrote the "path must be explicit" sentence to describe the two surviving routes (`--config` for CLI, `mcp_config_file` ini key for library mode).
- L608 — removed "migration from `MCPTF_CONFIG_FILE`" from the LIBRARY-MODE link summary.

One site in `docs/EXTENDING.md`:
- L211 — `MCPTF_CONFIG_FILE / --config` → `--config flag`.

### Task 2 — docs/ERROR-STYLE.md + docs/LIBRARY-MODE.md scrub (commit `06a375e`)

`docs/ERROR-STYLE.md`:
- "Config uses an older schema version" reference message body rewritten
  to the D-11 verbatim wording (Option A per plan; preserves the
  reference-message shape for future editors). Drops the `opt-in tool
  selection`, `in v1 a tool with no entry`, `the difference matters`,
  `migration walkthrough at docs/MIGRATION-v1-to-v2.md` lines and replaces
  the `next:` step with the D-11 `config-init` instruction.

`docs/LIBRARY-MODE.md`:
- L14 — opening paragraph: removed "migration path away from the legacy
  `MCPTF_CONFIG_FILE` environment variable" clause from the doc scope summary.
- L117–118 — removed the "the `MCPTF_CONFIG_FILE` environment variable is
  deprecated in v1.4 and removed in v1.5" note (with its cross-ref to the
  now-deleted migration section).
- L289–319 — deleted the entire `## Migration from MCPTF_CONFIG_FILE env var`
  section (31 lines).

## Acceptance criteria verified

- `grep -rn 'MCPTF_CONFIG_FILE' README.md docs/` → 0 matches ✓
- `grep -rn 'MIGRATION-v1-to-v2' README.md docs/` → 0 matches ✓
- `grep -rn 'opt-in tool selection\|in v1 a tool\|the difference matters\|migration walkthrough' docs/` → 0 matches ✓
- `grep -c 'mcp_config_file' README.md docs/LIBRARY-MODE.md` → 5, 15 (surviving routes still documented) ✓
- `grep -c 'unsupported config version' docs/ERROR-STYLE.md` → 1 (D-11 verbatim present) ✓

## Deviations

None. The plan offered Option A (rewrite to D-11) vs Option B (delete the
reference-message section). Picked Option A as recommended.

## Execution context

Executed inline in the orchestrator after both Wave-3 worktree agents
(`worktree-agent-a7339d888378a0296` for 31-05 and `worktree-agent-a7842d86d2502914c`
for 31-06) hit the recurring Phase-26 worktree-base-drift bug (worktree
spawned at `5e25c1e`, an old v1.1 release merge, instead of the
Phase-31-completed base `2e76214c`) and were denied permission to run the
prescribed `git reset --hard` corrective. User chose inline execution.
