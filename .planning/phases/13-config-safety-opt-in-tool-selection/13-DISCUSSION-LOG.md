# Phase 13: Config safety & opt-in tool selection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 13-config-safety-opt-in-tool-selection
**Areas discussed:** Auto-discovery + error precedence, Env-overlay drop depth, v1→v2 migration UX, Allowlist three-state semantics

---

## Auto-discovery + error precedence (SAFE-02, SAFE-03, SAFE-04)

### Q1: How wide should the cwd auto-discovery search be?

| Option | Description | Selected |
|--------|-------------|----------|
| cwd-only, single name (Recommended) | Probe only `./config.yaml` in cwd. No walk-up, no alternate filenames. | ✓ |
| cwd-only, two names | Probe `./config.yaml` then `./mcp-test-framework.yaml`. | |
| Walk-up from cwd | Walk up to nearest ancestor containing the file (ruff/pyproject style). | |

**User's choice:** cwd-only, single name.
**Notes:** Predictability beats ergonomics here. An operator in the wrong directory gets the same loud SAFE-03 error as one with no config at all — preferable to silent "picked the wrong file" surprises.

### Q2: Where does the config-resolution + path-validation logic live?

| Option | Description | Selected |
|--------|-------------|----------|
| New resolver in cli.py / _load_config (Recommended) | Promote _load_config; pass resolved path as init_settings kwarg to Config(). | ✓ |
| Keep the env-var trick, harden config.py | _load_config keeps stuffing MCPTF_CONFIG_FILE; config.py raises loudly on missing file. | |
| Split: discovery in cli.py, validation in config.py | Two seams, two error sites. | |

**User's choice:** Single resolver in `_load_config`.
**Notes:** Kills the env-var-as-IPC pattern that caused the SAFE-04 silent-fail bug. Single error site means SAFE-03 and SAFE-04 share wording naturally.

---

## Env-overlay drop depth (SAFE-05)

### Q3: How aggressive should the surgery be?

| Option | Description | Selected |
|--------|-------------|----------|
| Full strip (Recommended) | Delete _BareNameNestedEnvSource, env_settings, dotenv_settings, env_file, python-dotenv dep. | ✓ |
| Strip overlay, keep MCPTF_CONFIG_FILE | Same as full strip but MCPTF_CONFIG_FILE survives as pointer-to-config. | |
| Minimal: keep dotenv loader, deactivate overlay | Keep python-dotenv + .env loading mechanics, just disconnect from Config(). | |

**User's choice:** Full strip.
**Notes:** Confirmed (in CONTEXT.md D-06) that MCPTF_CONFIG_FILE survives as a pointer read by `_load_config` — "full strip" applies to env-overlay-as-config-source, not to the pointer mechanism SAFE-04 requires. .env.example (Phase 12) already documents this end state; code now has to match the doc.

---

## v1→v2 migration UX (SAFE-06, SAFE-07)

### Q4: What happens when an operator loads a v1 config under v2?

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse + doc-driven manual port (Recommended) | Load fails loud; operator reruns config-init + ports per docs/MIGRATION-v1-to-v2.md. | ✓ |
| Ship `config-migrate` subcommand | Add one-shot command for in-place migration. | |
| Refuse + emit a migrated draft, don't write | Print suggested YAML on stdout / sidecar. | |

**User's choice:** Refuse + doc-driven manual port.
**Notes:** The unlisted-default flip (opt-out → opt-in) is consequential enough that operators must re-read every per-tool entry. Auto-migration that silently keeps old `call_arguments` while flipping the default is the silent-destructive class v1.2 is fighting.

### Q5: What shape should docs/MIGRATION-v1-to-v2.md take?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone, before/after diff-driven (Recommended) | New file with plain-English summary + side-by-side YAML diff + drop-.env section. | ✓ |
| Section grafted into docs/EXTENDING.md | Add 'Migrating from v1 to v2' section to walkthrough. | |
| Standalone + skeleton port-script | Standalone doc + yq/Python snippet for re-emitting per-tool blocks. | |

**User's choice:** Standalone, diff-driven.
**Notes:** Standalone makes the SAFE-06 error message linkable to a stable path. The skeleton port-script option was rejected because it's effectively a `config-migrate` command we said we wouldn't build.

---

## Allowlist three-state semantics (SAFE-01)

### Q6: How does the reporter render auto-skip vs explicit-skip?

| Option | Description | Selected |
|--------|-------------|----------|
| Two distinct reason strings (Recommended) | (a) unlisted → "not selected in config"; (c) listed skip:true → curated skip_reason or default. | ✓ |
| Single reason string | Both states render as a generic "skipped" reason. | |

**User's choice:** Two distinct reason strings.
**Notes:** Matches SAFE-01 verbatim. Lets operators distinguish "forgot this tool" from "deliberately skipped" in the report.

### Q7: What happens when `tools:` is empty (`tools: {}` or unset)?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-skip every tool (Recommended) | Zero tools listed → every discovered tool renders as state (a). | ✓ |
| Error: 'no tools selected' | Exit 2 with a message telling operator to add at least one tool. | |
| Warn + continue | Reporter banner says "nothing will run" but exits 0. | |

**User's choice:** Auto-skip every tool.
**Notes:** Consistent with the unlisted rule; preserves "config-init then opt in" workflow without a special case. Phase 16's pre-run digest will surface the "nothing selected" state at the digest layer.

### Q8: What happens to the existing `target.tool_name` skip-override in fixtures.py:282-286?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it (Recommended) | Since Phase 12 D-03 removes target.tool_name, the override is unreachable. | ✓ |
| Keep an override seam | Preserve some mechanism (e.g., --only TOOL flag). | |

**User's choice:** Delete it.
**Notes:** Phase 12 D-03 already rejected `--only TOOL` for v1.2; focus pattern is `focus-toolname.yaml + --config`.

---

## Claude's Discretion

- Plan ordering within Phase 13 (suggested sequence in CONTEXT.md decisions).
- Exact wording of the default skip-reason for state (c) when `skip_reason` is empty (currently `"explicit skip in config"`).
- Whether the resolver prints the resolved config path on a verbose flag (deferred to Phase 16).
- Test surface location (under `tests/` until Phase 15 splits).
- Whether to refactor `validation_alias=AliasChoices(...)` to plain `Field(alias=...)` once env-var routing is gone (cleanup opportunity, not required).

## Deferred Ideas

- Walk-up autodiscovery (v1.3+; explicitly rejected for v1.2).
- `config-migrate` subcommand (v1.3+; explicitly rejected for v1.2).
- `--only TOOL_NAME` CLI flag (v1.3+; Phase 12 D-03 rejection upheld).
- Pre-flight "no config" check during runner startup (Phase 14 — reuse D-03's error site).
- `--explain` flag rendering long-form skip reasons (Phase 16).
- Verbose-flag printing of resolved config path (Phase 16).
- Refactor `AliasChoices` → `Field(alias=...)` once env-var routing gone (v1.3+ cleanup).
