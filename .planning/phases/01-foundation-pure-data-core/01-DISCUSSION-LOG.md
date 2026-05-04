# Phase 1: Foundation & Pure-Data Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 01-foundation-pure-data-core
**Areas discussed:** ValidationIssue severity usage

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Env var naming convention | Bare spec names vs. MCPTF_* prefix for collision-safety. | |
| models.py contents | What lives in models.py vs. domain modules. | |
| tests/ directory structure | Flat vs. unit/integration split. | |
| ValidationIssue severity usage | Are missing-property-description / missing-property-type warnings or errors? | ✓ |

**User's choice:** ValidationIssue severity usage (sole selection)
**Notes:** All other areas implicitly delegated to Claude's discretion. See CONTEXT.md "Claude's Discretion" subsection for the chosen defaults.

---

## ValidationIssue Severity Usage

| Option | Description | Selected |
|--------|-------------|----------|
| Errors only — drop warning (Recommended) | All 7 checks return severity='error'. Keep `severity` field on the model so warnings can be added later without migration. Phase 4 TEST-02 = 'returns empty list'. Strict but defensible. | ✓ |
| Mixed: #6 is warning, rest are errors | Check #6 (property description missing) returns 'warning'; checks 1-5 and 7 return 'error'. Adds a 'pass-with-warnings' state. | |
| Add an `info` tier too | error / warning / info. None of the 7 spec'd checks naturally land in info today. | |

**User's choice:** Errors only — drop warning (Recommended)
**Notes:** Severity field stays on the model (`Literal["error"]`) so post-MVP can add `"warning"` as a typed change with no schema migration. Phase 4 TEST-02 asserts `validate_tool_schema(tool) == []`. Check #6 missing → vacuously passes for `list_registered_servers` (no input parameters), so the strictness has no observable cost in MVP scope.

---

## Claude's Discretion

The user passed on the following gray areas; Claude chose defaults and recorded them in CONTEXT.md `<decisions>` `Claude's Discretion`:

- **Env var naming convention** — Spec-verbatim bare names (`OLLAMA_BASE_URL`, etc.). Document `.env` workaround in README. Revisit if collisions bite.
- **`models.py` contents** — `Config` + sub-models only. `ValidationIssue` stays in `schema_validator.py`, `JudgeResult` stays in `ollama_judge.py`.
- **`tests/` directory structure** — `tests/unit/` for Phase 1 pure-data tests; flat `tests/` for Phase 4 integration tests; single `conftest.py` at `tests/`.
- **Lint enforcement mechanism (SETUP-03)** — ruff `flake8-tidy-imports` `TID251` (`banned-api`) banning `homelab_mcp` and `homelab_mcp.*`, scoped to `src/` and `tests/`.
- **YAML config discovery** — No auto-discovery; path comes from `--config` flag (Phase 5) or `MCPTF_CONFIG_FILE` env var.
- **`Config` immutability** — `frozen=True` for safe session-scoped fixture sharing.
- **`ValidationIssue.path` representation** — JSON-Pointer-style strings to match `jsonschema`'s native error path output.

## Deferred Ideas

- Add `warning`/`info` severity tiers post-MVP if real tools surface non-blocking quality issues.
- Auto-discover `config.yaml` in cwd if users complain about manual `--config`.
- Prefixed env vars (`MCPTF_*`) if collisions with co-installed Ollama/MCP tooling become a problem.
