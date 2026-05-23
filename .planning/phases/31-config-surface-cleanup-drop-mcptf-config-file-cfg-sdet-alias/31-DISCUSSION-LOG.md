# Phase 31: Config-surface cleanup — drop `MCPTF_CONFIG_FILE` + `cfg.sdet.*` alias + v1-schema decommission - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias
**Areas discussed:** `sdet:` key rejection error shape; Leftover `MCPTF_CONFIG_FILE` env in shell

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| CLI→pytest IPC after env-var removal | How does `mcp-contracts run --config PATH` hand the resolved path to the in-process pytest session it spawns? | |
| `sdet:` key rejection error shape | Mechanism + message text for rejecting a top-level `sdet:` key after the alias is removed. | ✓ |
| v1 rejection: message + self-test handling | New generic message replacing the v1→v2 walkthrough + how to handle pinned-text self-tests. | |
| Leftover `MCPTF_CONFIG_FILE` env in shell | Operator runs pytest with stale env var set — silent vs warn vs hard error. | ✓ |

**User's choice:** Two areas selected (`sdet:` + leftover env). Other two fall to Claude's discretion.

---

## `sdet:` key rejection error shape

### Q1 — Rejection mechanism after alias removal

| Option | Description | Selected |
|--------|-------------|----------|
| Bare `extra='forbid'` + cli.py error mapper | Remove alias + pre-scan + model_validator. Pydantic raises ExtraForbidden; cli.py mapper adds a targeted branch for `loc==('sdet',)`. | ✓ |
| Custom `model_validator(mode='before')` retained, upgraded to reject | Keep the existing pre-scan validator, flip from warn-on-sdet-alone to reject-on-sdet-presence. | |
| Targeted `ValueError` from a `sdet` field stub | Add a sentinel `sdet:` field with a validator that always raises. | |
| You decide | Defer to Claude. | |

**User's choice:** Bare `extra='forbid'` + cli.py error mapper.
**Notes:** Symmetric with how the version-rejection branch already works in `_emit_operator_error_for_validation_error`. Minimal surviving code post-removal (Phase 35 SHIM-09 zero-shim gate has less to grandfather).

### Q2 — Operator-tone error message text

| Option | Description | Selected |
|--------|-------------|----------|
| Direct rename pointer (three-part) | summary='unknown config key: sdet' + detail naming v1.4 rename + v1.5 removal + next_step='rename to test_code:'. | ✓ |
| Generic extra-forbidden + breadcrumb | Doesn't name `test_code:` directly; points at config.example.yaml / config-init scaffold. | |
| Direct pointer, no rename history | Shortest form; drops the v1.4-renamed/v1.5-removed history breadcrumb. | |

**User's choice:** Direct rename pointer (three-part).
**Notes:** Operator-approved verbatim wording. Pin in `tests/framework/unit/test_error_style.py` so future shim-style edits don't drift the text.

### Q3 — Scope of the `sdet:` branch in cli.py

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `sdet:` only (loc==('sdet',)) | Pydantic stops at the first extra-forbidden on the outer key, so nested errors never reach. | ✓ |
| Any loc starting with 'sdet' | Defensive against nested misuse; mostly dead code under `extra='forbid'`. | |
| Top-level only + separate `tools.<name>.sdet:` check | Only relevant if nested `sdet:` references exist; grep shows they don't. | |

**User's choice:** Top-level `sdet:` only.

### Q4 — Library-mode rejection (plugin path)

| Option | Description | Selected |
|--------|-------------|----------|
| Same targeted message via the plugin | Plugin catches Config ValidationError at pytest_configure and routes through the same error mapper. One canonical operator-error surface. | ✓ |
| Plugin catches but emits a thinner library-mode-flavored message | Two divergent message variants per persona. | |
| Plugin doesn't catch; raw Pydantic error surfaces | Simpler implementation, breaks operator-tone story in library mode. | |

**User's choice:** Same targeted message via the plugin.
**Notes:** Research-for-plan flag: verify whether `_plugin.py` already has such a mapper path or whether it needs to be factored out of `cli.py` into a shared module. Refactor preferred over duplication.

---

## Leftover `MCPTF_CONFIG_FILE` env in shell

### Q1 — What does the operator see when the stale env var is set?

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot DeprecationWarning at session start | Fire once at pytest_configure; never read the path; point at `mcp_config_file` ini + `--config`. | ✓ |
| Truly silent — no detection | Phase 31 removes every reference; operator with stale env hits 'no config found' if nothing else is set. | |
| Hard refuse-to-start error | pytest.UsageError forcing the operator to unset. | |
| You decide | Defer to Claude. | |

**User's choice:** One-shot DeprecationWarning at session start.
**Notes:** Directly addresses the Memory-flagged silent-footgun pattern (`project_mcptf_config_file_silent_fail.md`) without punishing operators who have non-mcptf reasons to keep the env around.

### Q2 — Where does the warning fire from?

| Option | Description | Selected |
|--------|-------------|----------|
| pytest plugin `pytest_configure` | Reuses the existing trigger point at `_plugin.py:148-150`; just flip the wording. | ✓ |
| Plugin + cli.py `run` command | Two emission sites; covers the CLI surface explicitly before spawning pytest. | |
| Plugin only — cli.py stays silent | Same outcome as plugin-only since cli.py spawns pytest which loads the plugin. | |

**User's choice:** pytest plugin `pytest_configure`.

### Q3 — Visibility upgrade scope

| Option | Description | Selected |
|--------|-------------|----------|
| In scope — `warnings.warn` + custom formatwarning (red `[mcp-contracts]` prefix, separated from pytest noise) | Phase 31 is the right vehicle since this is the last DeprecationWarning standing post-v1.5. | ✓ |
| Out of scope — fire as plain DeprecationWarning, log as backlog | Keep Phase 31 strict to the minimum success criteria. | |
| In scope but minimal — stderr print instead of `warnings.warn` | Always-visible bypass of the warnings system. | |

**User's choice:** In scope — `warnings.warn` + custom formatwarning.
**Notes:** Research-for-plan flag: locate any pre-existing formatwarning override (likely partial from Phase 25) before adding a new one. Decide between formatwarning override (broader, captures all package warnings) vs domain-UI banner integration (narrow, just this warning).

### Q4 — EOL for the surviving detection

| Option | Description | Selected |
|--------|-------------|----------|
| v1.6 capstone — delete the warning entirely | Operators get one full milestone of loud notification before evaporation. Phase 35 grandfathers the single match for v1.5. | ✓ |
| Stays forever — cheap kindness | 3-line detection left indefinitely; gate excludes one reference forever. | |
| Decide at v1.5 close | Punt to RETROSPECTIVE.md and revisit at v1.6 scoping. | |

**User's choice:** v1.6 capstone — delete the warning entirely.

---

## Claude's Discretion

- **CLI→pytest IPC after env-var removal** — recommended: forward via `-o mcp_config_file=PATH` (same channel as library-mode operator). Falls back to a private `_MCPTF_RESOLVED_CONFIG_FILE` env var if `-o` quoting or plugin-load-order issues surface during research.
- **v1 rejection message text (V1DROP-03)** — recommended: minimal three-part shape, no `docs/MIGRATION-v1-to-v2.md` reference, no v1→v2 history acknowledgment. Aligned with REQUIREMENTS literal text.
- **V1DROP-04 self-test handling** — recommended: per-test judgement defaulting to relax-not-delete; delete only when the test pins migration-walkthrough-specific content, relax when it asserts the structural operator-tone shape.

## Deferred Ideas

- MCPTF_CONFIG_FILE DeprecationWarning detection EOL → v1.6 capstone deletion; captured as v1.5 close deferred item.
- Backlog 999.5 re-assessment → after Phase 31 ships; the underlying pydantic-settings deep-merge class-of-bug survives env-var removal and likely resurfaces at Phase 34 ISOL-05 bare-caller audit.
- `docs/MIGRATION-v1-to-v2.md` content archival → optional one-line note in `.planning/MILESTONES.md` v1.2 entry or `CHANGELOG.md`; nice-to-have, out of Phase 31 scope.
