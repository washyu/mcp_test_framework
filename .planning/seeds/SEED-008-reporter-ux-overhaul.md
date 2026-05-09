---
id: SEED-008
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete (between-milestones)
trigger_when: v1.2 milestone framing — surface during /gsd-new-milestone questioning step
scope: Medium
---

# SEED-008: Reporter UX overhaul — pre-run digest + --explain flag

## Why This Matters

Pytest's "121 collected, 15 deselected" framing is misleading for this framework's audience. After loading `config.example.yaml` with 56 `skip: true` entries, the v1.1 user sees:

```
================== 691/706 tests collected (15 deselected) in 11.05s ==================
```

A user trying to manually verify their config sees **691 selected** and reasonably concludes the framework is going to run hundreds of destructive tools. The `15 deselected` count refers ONLY to pytest marker filters (`live_homelab` / `live_ollama`), not to the 56 config skips. This is unparseable without internal knowledge.

User refined the desired output shape on 2026-05-08: a **verbosity-aware** digest by default, with full per-tool / per-judge breakdown only behind a flag.

This composes with the vibe-coded persona (SEED-007) — an operator testing a server they didn't write needs the digest to confirm "what did my config actually do?" before running anything destructive.

## When to Surface

**Trigger:** v1.2 milestone framing — surface during `/gsd-new-milestone` questioning step

This seed should be presented when the new milestone scope mentions any of:
- Reporter / output / terminal UX
- Verbosity / verbose / quiet
- CI integration (since CI consumers also want clean summaries)
- Output ergonomics / scale / N=70

## Scope Estimate

**Medium** — One phase. The reporter changes are localized to `_reporter.py`, but the `--explain` flag also needs to flow through Typer (CLI layer), and the design needs to handle quiet mode and JUnit XML interaction.

## Proposed Output Shape

Default (always shown, even at default verbose):

```
========================================
MCP Test Framework
========================================
MCP server:  uvx homelab-mcp
Discovered:  58 tools

Running:     2  (list_keyring_credentials, suggest_deployments)
Skipping:   56  (use --explain to list)
Defaulting:  0

Judges per tool:
  list_keyring_credentials  →  clarity
  suggest_deployments       →  clarity, disambiguation, parameters

Test plan: 20 tool cases + 107 framework cases = 127
========================================
```

With `--explain`:

```
Skipped (56):
  bulk_discover_and_map     — side effects on homelab inventory: bulk discovery writes
  clone_proxmox_vm          — destructive: clones Proxmox VM image
  control_vm                — destructive: changes VM power/run state
  ...
```

## Open Design Questions

### Flag naming
- **Pytest `-v` passthrough:** familiar, but conflates with pytest's per-test progress verbosity. Confusing.
- **Framework flag (`--explain` / `--verbose-config` / `--show-config`):** cleaner separation, but new flag to learn. **User lean: this option.** Likely `--explain` since it's short and reads naturally next to a digest output.

The flag sits at the framework CLI layer (Typer), not forwarded to pytest. Pytest's own `-v` keeps controlling live test output independently.

### Quiet mode
`-q` (quiet) should suppress the digest, mirroring the existing post-run summary's quiet behavior.

### JUnit XML
Should the pre-run digest also emit to JUnit XML as `<system-out>` or similar? Probably yes for CI consumers, but needs explicit decision.

## Constraint: N=70 ergonomics

Whatever lands here MUST scale gracefully at homelab-mcp's ~70 tool surface. The digest works at any N (10 lines regardless). The `--explain` mode produces 70 lines max — still readable, still grep-able.

See memory: `project_output_ergonomics_at_scale.md` — "evaluate v1.2 designs at N=70, not N=1"

## Dependency on SEED-006 + v1.1.1 Hotfix

The pre-run digest's "Skipping: N" count only tells the truth if skip:true entries actually filter the parametrize list. v1.1.1 hotfix (`project_v1_1_skip_bug.md`) lands that filter; SEED-006's opt-in selection makes the filter the *primary* mechanism. Either lands before SEED-008.

## Sequencing Within v1.2

Land AFTER SEED-006 (semantics) and SEED-009 (doc cleanup), since this is the UX layer over the new semantics. Without the bugfix + opt-in already in place, the digest would lie about counts.

## Breadcrumbs

- `src/mcp_test_framework/_reporter.py` — current post-run per-tool summary plugin (Phase 09)
- `src/mcp_test_framework/cli.py:118-172` — `run` Typer command (where `--explain` would land)
- `tests/conftest.py:127-139` — pytest_generate_tests hook (where the discovered/selected/skipped counts would be derived)
- `tests/test_reporter.py` — existing reporter test patterns
- `src/mcp_test_framework/fixtures.py:_preflight` — already prints session-start warnings

## Related Memories

- project_pre_run_tool_summary.md
- project_output_ergonomics_at_scale.md
- project_v1_1_skip_bug.md (dependency)
