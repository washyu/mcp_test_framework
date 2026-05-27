# Phase 34: Opt-in host isolation passthrough (999.3) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 34-Opt-in host isolation passthrough (999.3)
**Areas discussed:** Config field shape & placement, Passthrough env shape at the spawn site
**Areas skipped (Claude's discretion):** xdist clamp UX, Bare `Config()` audit remediation

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Config field shape & placement | Top-level vs nested; Literal vs Enum vs bool; default semantics; typo rejection | ✓ |
| xdist clamp UX when operator typed `-n>1` + passthrough | Silent clamp + banner vs hard error vs Phase 31 D-08 red banner | |
| Bare `Config()` audit remediation (ISOL-05) | Shared `Config.resolved()` classmethod vs document-and-sweep vs deprecate | |
| Passthrough env shape at the spawn site | Literal `os.environ` copy vs denylist-strip hybrid vs ANC injection | ✓ |

**User's choice:** Two areas selected (multiSelect). The two skipped areas inherit Claude's recommended defaults captured under "Claude's Discretion" in CONTEXT.md.

---

## Config field shape & placement

### Q1: Where should `host_isolation` live on the Config model?

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `Config.host_isolation` (Recommended) | Sits next to `mcp_server`, `ollama`, `tools`, `test_code`. Operator-visible in scaffolds. Single grep target for Phase 35 capstone. | ✓ |
| Nested under a new `runtime:` block | Leaves room for future runtime knobs; one more YAML indent level. | |
| Nested under existing `mcp_server:` | Co-located with the thing it affects; risk that it conceptually belongs to the operator's host, not the server config. | |

**User's choice:** Top-level `Config.host_isolation`.

### Q2: How should the field be typed?

| Option | Description | Selected |
|--------|-------------|----------|
| `Literal['strict','passthrough']` with default 'strict' (Recommended) | Pydantic-native, `extra='forbid'`-friendly, error message names valid values on typo. Matches Phase 33 `skip_buckets: list[Literal[...]]`. | ✓ |
| Custom `HostIsolation` Enum class | Python-side handle for branching; slightly more code. | |
| Boolean `isolate: bool = True` | Simpler config; loses the 'mode name' vocabulary the spec, docs, and SEED-022 lock all use. ROADMAP/REQUIREMENTS pin the strings. | |

**User's choice:** `Literal['strict','passthrough']` with default 'strict'.

### Q3: How should the default be declared?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit default in the model (Recommended) | `host_isolation: Literal[...] = 'strict'`. Bare `Config()` returns a complete, valid config. Phase 35 capstone can assert `Config().host_isolation == 'strict'`. | ✓ |
| Optional with None default + spawn-site fallback | Distinguishes 'never set' from 'explicitly strict'; duplicates the None→strict fallback in every consumer. | |
| No default, required field | Forces explicit decision; backwards-incompatible with v1.0–v1.4 implicit-strict behavior. | |

**User's choice:** Explicit default `'strict'` on the model.

### Q4: How should an unknown value (e.g. `host_isolation: passthru` typo) be rejected?

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic stock literal_error + operator-tone CLI mapper branch (Recommended) | Matches Phase 31 D-01/D-02 pattern. Same message in CLI mode and library mode via shared mapper. Pinned by `test_error_style.py`. | ✓ |
| Stock Pydantic error, no mapper branch | Simpler; inconsistent with how `sdet:` and `version:` rejections got operator-tone wrappers in Phase 31. | |
| Custom `@field_validator` with bespoke message | More code, drift risk; lets us include cross-references in the message. Over-engineered for a 2-value Literal. | |

**User's choice:** Pydantic stock literal_error + operator-tone CLI mapper branch.

---

## Passthrough env shape at the spawn site

### Q1: Under `passthrough`, what env does the spawned subprocess get?

| Option | Description | Selected |
|--------|-------------|----------|
| Literal `os.environ` copy — nothing stripped, nothing injected (Recommended) | `StdioServerParameters(env=dict(os.environ))`. Operator's full shell env reaches the subprocess unchanged. Matches operator's mental model: "passthrough = what `uvx homelab-mcp` would see from my shell." | ✓ |
| `os.environ` minus a small framework-internal denylist | Strip `PYTEST_*`, `_MCPTF_*`, `PYTHONPATH`. Cost: another spec surface; debatable membership; SEED-022-adjacent (framework reasoning about which vars are "safe"). | |
| `os.environ` + explicitly inject MCP_CONNECTION_NONBLOCKING and friends | Masks operator shell state with framework defaults. | |

**User's choice:** Literal `os.environ` copy.

### Q2: Under `passthrough`, does the per-session tempdir (`_isolated_home`) still get allocated?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip tempdir allocation entirely — fixture short-circuits in passthrough (Recommended) | `_isolated_home` yields None when `cfg.host_isolation == 'passthrough'`. Simpler; dead-state if allocated. | ✓ |
| Allocate tempdir but don't bind HOME/USERPROFILE to it | Preserves any latent dependency on the path; dead allocation in common case. | |
| Allocate tempdir AND set TEMP/TMP/TMPDIR to it (but leave HOME/USERPROFILE on real home) | Hybrid: scratch redirected, credentials reachable. Surprising semantics; confuses the trade-off description. | |

**User's choice:** Skip tempdir allocation entirely.

### Q3: Where does the mode-branching live — inside `_isolation.py` or at the call site?

| Option | Description | Selected |
|--------|-------------|----------|
| Inside `_isolation.py` — new `_build_passthrough_env()` sibling, dispatcher picks (Recommended) | `_build_subprocess_env(mode, isolated_home)` dispatcher; single isolation surface. Future maintainer reads one file. | ✓ |
| Branch at the call site — spawn sites inline `if mode == 'strict': ...` | Duplicates branch in 2 places; drift risk; Phase 35 grep harder. | |
| Replace `_build_isolated_env()` entirely — takes a mode arg | Symmetric, but the name "isolated" no longer fits the passthrough branch; rename churn. | |

**User's choice:** Dispatcher inside `_isolation.py` with sibling builders.

### Q4: How does the spawn site KNOW the mode — does the dispatcher read Config, or does the caller pass the mode?

| Option | Description | Selected |
|--------|-------------|----------|
| Caller passes the mode explicitly; dispatcher takes a `mode` arg (Recommended) | `_isolation.py` Config-agnostic; testable with a plain string; SEED-022-clean (framework primitive takes data, not a Config blob). | ✓ |
| Dispatcher imports Config internally and reads `cfg.host_isolation` | Single source of truth; couples low-level primitive to high-level model; bigger refactor blast radius. | |
| Mode passed via env var or module-level global | Reintroduces `_MCPTF_*` env-var IPC that Phase 31 just removed. | |

**User's choice:** Caller passes the mode explicitly to a Config-agnostic dispatcher.

---

## Final loop

### Q: We've discussed Config field shape and Passthrough env shape. Where to from here?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Locked decisions; Claude's discretion covers xdist clamp UX + bare-Config audit + docs example. Write CONTEXT.md. | ✓ |
| Explore more gray areas | E.g. mcp_client standalone CLI Config-construction path, config-init scaffold emission shape. | |

**User's choice:** Ready for context.

---

## Claude's Discretion

The following gray areas were surfaced but the user did NOT select them for discussion. Recorded defaults in CONTEXT.md `<decisions>` § "Claude's Discretion"; planner is free to revisit with research:

- **xdist clamp UX (ISOL-04)** — Default: silent clamp to 1 + one-shot `[mcp-contracts]` red banner via Phase 31 D-08 surface. Hook at `pytest_configure(tryfirst=True)` mutating `config.option.numprocesses`. Research-for-plan: verify hook ordering vs pytest-xdist; fall back to `pytest_xdist_setupnodes` if needed.
- **Bare `Config()` audit remediation (ISOL-05)** — Default: document inline for each `src/` site (3 known: `fixtures.py:111`, `test_code/session.py:67`, `cli.py:15`); plumb `test_code/session.py:67` through the plugin stash if research confirms it runs after stash population; for `tests/framework/` produce a categorized inventory committed alongside the implementation, not a per-site refactor.
- **Docs worked example (ISOL-06)** — Default: real homelab-mcp Proxmox credential repro from memory `project_isolation_blocks_live_uat.md` (2026-05-19 Phase 30 UAT-1). Same example in README + `docs/LIBRARY-MODE.md` for parity (Phase 33 D-03 pattern).
- **`config-init` scaffold emission** — Default: emit `host_isolation: strict  # 'strict' (default, isolated) or 'passthrough' (operator creds reachable, xdist=1)` uncommented, default value spelled, inline single-line trade-off comment.

## Deferred Ideas

Captured under CONTEXT.md `<deferred>` section. Summary:

- Selective per-env-var passthrough (allowlist) — v1.6+ if real demand surfaces.
- Per-tool isolation mode — re-introduces SEED-002 complexity; defer.
- `_build_isolated_env` → `_build_strict_env` rename — symmetric but pure-churn; defer.
- Phase 999.5 (bare-Config self-test pollution class-of-bug) — re-assess if it re-surfaces during the audit.
- xdist resource markers (SEED-002) — referenced by ISOL-04 framing; v1.6+.
- `mcp-contracts diag host-isolation` diagnostic subcommand — backlog candidate.
