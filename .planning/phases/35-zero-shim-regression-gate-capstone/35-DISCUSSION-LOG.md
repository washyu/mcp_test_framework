# Phase 35: Zero-shim regression gate (capstone) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 35-Zero-shim regression gate (capstone)
**Areas discussed:** Sweep semantics per surface, Failure-message granularity, Relationship to existing gates

(Area "False-positive guarding / scope" was offered but not selected — its substance folded into the Sweep semantics decisions D-03.)

---

## Sweep semantics per surface

### Primary detection strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Behavioral-first + regex backstop | Probe each surface, assert it hard-rejects/no-ops; narrow static check for the 2 fully-deleted constructs. Re-adding a functional shim fails the 'assert it rejects' probe. | ✓ |
| Static/regex-first | Sweep src/ for forbidden constructs/tokens, behavioral secondary. | |
| Pure behavioral | Import + invocation probes only, no static sweep. | |

**User's choice:** Behavioral-first + regex backstop.

### Probe depth
| Option | Description | Selected |
|--------|-------------|----------|
| Behavior only — raises/rejects/absent | Assert observable behavior only; do NOT re-assert message text (per-surface tests own that). | ✓ |
| Behavior + pointer substring | Also assert each rejection contains the post-v1.4 pointer. | |
| Behavior + full ERROR-STYLE shape | Assert three-part summary/detail/next_step shape. | |

**User's choice:** Behavior only.

### Backstop implementation
| Option | Description | Selected |
|--------|-------------|----------|
| AST-targeted, narrow | Assert specific deleted constructs absent (no Field(alias="sdet"), no MCPTF_CONFIG_FILE env read). No text-grep for 'sdet'. | ✓ |
| Text regex + noqa exclusion | Reuse `# noqa: sdet-rename-shim` marker; regex-sweep src/. | |
| No static backstop | Behavioral only. | |

**User's choice:** AST-targeted, narrow.
**Notes:** Resolves the "zero matches" vs grandfathered-intercept tension — "zero shims" = no functional shim / every surviving surface hard-rejects, not "the word never appears."

---

## Failure-message granularity

### Test structure
| Option | Description | Selected |
|--------|-------------|----------|
| One parametrized test per surface | 5 parametrized cases id'd by surface name. | |
| Separate test function per surface | 5 named def test_<surface>() functions; surface name in function name. | ✓ |
| One aggregated sweep test | Single function, combined failure report. | |

**User's choice:** Separate test function per surface.

### Failure message content
| Option | Description | Selected |
|--------|-------------|----------|
| Surface + what regressed + why it's pinned | Names surface, failing probe, requirement id, and that the shim stays a hard-reject until v1.6. | ✓ |
| Surface + what regressed only | Names surface + failing probe, no rationale. | |
| Default pytest assert output | Bare assertions, no custom message. | |

**User's choice:** Surface + what regressed + why it's pinned.

---

## Relationship to existing gates

| Option | Description | Selected |
|--------|-------------|----------|
| Coexist + fix its stale docstring | Keep RENAME-06 terminology gate (orthogonal concern); correct its misleading 'removed in v1.5' docstring. | ✓ |
| Coexist, leave entirely as-is | Keep untouched, stale docstring and all. | |
| Fold terminology check into SHIM-09 | Absorb terminology sweep into the capstone. | |

**User's choice:** Coexist + fix its stale docstring.
**Notes:** Per-surface message-text tests from Phases 31/32 stay; SHIM-09 does not duplicate them (reinforced by behavior-only probe-depth decision and Phase 32 D-09).

---

## Claude's Discretion

- Exact test-function names and internal ordering of surface probes.
- Whether the AST backstop lives in a helper or inline.

## Deferred Ideas

- v1.6 clean-deletion of the grandfathered intercepts (probes flip from "assert hard-reject" to "assert absent"; RENAME-06 terminology gate retires then).
- CHANGELOG / milestone footnote for the v1.4→v1.5 shim retirement.
