# Phase 12: Doc & persona foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 12-doc-persona-foundation
**Areas discussed:** config-init v1-vs-v2 posture, list-tools UX at N=70, Doc cleanup + examples/ shape, Error message scope + style

---

## config-init v1-vs-v2 posture

### Q1: emitted config shape

| Option | Description | Selected |
|--------|-------------|----------|
| v1 header, v2-style content | Loadable today, Phase 13 conversion = header bump + flip-default | ✓ |
| v2 shape now, bleed runtime forward | Pull Phase 13 runtime work into Phase 12 | |
| Pure v1, fix in Phase 13 | Single migration story for all configs (Phase 12 configs would also error in 13) | |

**User's choice:** v1 header, v2-style content (Recommended)
**Notes:** Configs generated NOW survive Phase 13 with minimal edit; matches "lowest-rework cost" sequencing.

### Q2: tools: block contents

| Option | Description | Selected |
|--------|-------------|----------|
| All discovered, all skip:true + skip_reason | Safe by default; Phase 13 conversion is no per-tool churn | ✓ |
| Skeleton + comment listing names | Smallest file; more operator effort | |
| All discovered, first-tool un-skipped | Heuristic; risky (first tool not necessarily safe) | |
| Empty tools: + comment | Truest opt-in but "loads and runs" criterion ambiguous | |

**User's choice:** All discovered, all skip:true (Recommended)

### Q3: server unreachable behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail loud, no offline mode | PERSONA-03 error style; matches Phase 13 failsafe | ✓ |
| --offline flag emits placeholder | Two paths to a config | |
| Auto-fallback to placeholder | Silent degradation; contradicts PERSONA-03 | |

**User's choice:** Fail loud, no offline mode (Recommended)

### Q4: top-level target: field

| Option | Description | Selected |
|--------|-------------|----------|
| Omit target, comment why | Recommended option as presented | |
| Emit target with tool_name commented out | Literal CLEAN-05 reading | |
| Populate target with first discovered tool | Conflicts with multi-tool default | |
| **(Other) Drop target.tool_name entirely from config & schema** | User-volunteered: "doesn't make sense if we are getting all tools then basically running tools that are not skipped" | ✓ |

**User's choice:** Drop `target.tool_name` entirely (free-text response).
**Notes:** Phase 13 cross-phase task = remove field from Pydantic model + emit deprecation message for v1 configs that still carry it. Confirmed follow-up: focus-one-tool workflow uses separate `focus-toolname.yaml` + `--config`; no `--only TOOL` CLI flag added (would re-introduce a second knob). User confirmed: "there are enough parameter values you will still need the config for a run so having multiple configs for tools is fine."

---

## list-tools UX at N=70

### Q1: default per-tool render shape

| Option | Description | Selected |
|--------|-------------|----------|
| Name + 1-line desc + param signature | ~3-4 lines per tool, ~280 lines at N=70 | ✓ |
| Name + param-count badge | Lightest; requires drill-in command for any detail | |
| Today's shape + --schema flag | Lowest-churn; punts the persona question | |
| Name + required-params-only | Optimizes for minimum-viable-call | |

**User's choice:** Name + 1-line desc + param signature (Recommended)

### Q2: --full flag semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Full description + per-param descriptions | Stays human-readable; PERSONA-02's actual goal | ✓ |
| Raw inputSchema JSON dump | Verbose, JSON-shaped; already available via --json | |
| --full replaces --json (single flag) | Loses human-readable expanded form | |
| Both --full and --json (orthogonal) | Two flags; same end result as Q1 selection | |

**User's choice:** Full description + per-param descriptions (Recommended). `--json` stays separate as the machine-readable surface.

### Q3: drill-in mechanism at N=70

| Option | Description | Selected |
|--------|-------------|----------|
| --name PATTERN substring filter | One flag, composes with --full and --json | ✓ |
| --tool exact + --grep substring | Two ways to do almost the same thing | |
| Defer to v1.3 | Smallest scope; ships a known UX gap | |

**User's choice:** --name PATTERN (Recommended). Case-insensitive substring filter.

### Q4: default sort order

| Option | Description | Selected |
|--------|-------------|----------|
| Keep alphabetical (D-list-4 contract) | Predictable, scriptable, matches today | ✓ |
| Group by safe-to-call heuristic | Persona-friendly but heuristic-fragile | |
| Alphabetical with name-prefix section headers | Helps scanning; adds rendering complexity | |

**User's choice:** Keep alphabetical (Recommended). Sort grouping deferred to v1.3+ if it becomes a pain point.

---

## Doc cleanup + examples/ shape

### Q1: cleanup approach

| Option | Description | Selected |
|--------|-------------|----------|
| Per-section semantic rewrite | Slower; produces operator-grade docs | ✓ |
| Regex strip + manual review pass | Faster initial pass; quality depends on review | |
| Two-phase strip-then-polish | Doubles touch-count on same files | |

**User's choice:** Per-section semantic rewrite (Recommended)

### Q2: examples/ shape

| Option | Description | Selected |
|--------|-------------|----------|
| One-file dir + brief README | Sets the convention without overcommitting | ✓ |
| One-file dir, no README | Convention is implicit | |
| Convention with multiple seeds | Stub examples are unverifiable | |

**User's choice:** One-file dir + brief README (Recommended)

### Q3: PERSONA-01 README placement and depth

| Option | Description | Selected |
|--------|-------------|----------|
| Top-of-README paragraph + link | Visible early; walkthrough lives in EXTENDING | ✓ |
| Dedicated mid-README section with walkthrough | More real-estate; ~30-50 added lines | |
| Top framing + EXTENDING walkthrough split | Same shape as A but split across docs | |

**User's choice:** Top-of-README paragraph + link (Recommended)

### Q4: config.example.yaml entry count

| Option | Description | Selected |
|--------|-------------|----------|
| 3 entries showing pattern variations | Worked template for the YAML's full vocabulary | ✓ |
| 1 minimal entry + comment block | Smallest; relies on operators reading the comment | |
| 5+ entries, every field demonstrated | Most exhaustive; verbose | |

**User's choice:** 3 entries showing pattern variations (Recommended).

### Q5 (follow-up): config.example.yaml vs config-init output

| Option | Description | Selected |
|--------|-------------|----------|
| Different by design | Template (curated, placeholders) vs scaffold (live, real names) | ✓ |
| Same file (config-init verbatim against homelab-mcp) | Loses placeholder generic shape; contradicts CLEAN-02 | |
| Drop config.example.yaml entirely | Single source of truth (config-init) but loses comment-rich docs | |

**User's choice:** Different by design (Recommended).

---

## Error message scope + style

### Q1: which surfaces in scope

| Option | Description | Selected |
|--------|-------------|----------|
| Config load failures | Pydantic ValidationError, --config path missing, MCPTF_CONFIG_FILE typo | ✓ |
| MCP server spawn failures | Command not on PATH, subprocess exits before handshake | ✓ |
| Judge connect failures | Ollama unreachable, model not pulled, connection timeout | ✓ |
| Missing-config / missing-tool errors | Includes future SAFE-03 wording | ✓ |

**User's choice:** All four surfaces in scope (multi-select).

### Q2: style guide upfront vs per-message

| Option | Description | Selected |
|--------|-------------|----------|
| Style guide upfront, codified in EXTENDING.md | Rules locked; future phases inherit | ✓ |
| Per-message judgment, no written guide | Faster but no contract for future phases | |
| Style guide + one-test enforcement | Mechanical regression guard | |

**User's choice:** Style guide upfront, codified in EXTENDING.md (Recommended). Banned-token enforcement test left as a deferred v1.3+ todo.

### Q3: cross-phase wording lock for SAFE-03 / SAFE-06

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-draft both strings in Phase 12 ERROR-STYLE.md | Phase 13 implements verbatim | ✓ |
| Phase 12 locks style only | Phase 13 writes its own messages | |
| Defer all error wording to owning phase | Highest drift risk | |

**User's choice:** Pre-draft both strings in Phase 12 ERROR-STYLE.md (Recommended)

---

## Claude's Discretion

- Plan ordering within Phase 12 (suggested: ERROR-STYLE.md first → config-init rewrite → docs sweep → list-tools work → persona section)
- Specific wording of the persona-framing paragraph and placeholder tool-name suffixes
- Whether `examples/README.md` and `docs/ERROR-STYLE.md` are new files or sections in existing files
- Whether `--name` filter uses glob or pure substring (defaulting to substring case-insensitive)

## Deferred Ideas

### Cross-phase (Phase 13)
- Remove `target.tool_name` from Pydantic Config model; emit deprecation/migration message
- Implement SAFE-03 / SAFE-06 messages verbatim from Phase 12's ERROR-STYLE.md
- v1→v2 schema bump = header + flip-default (NOT regenerate); preserve Phase 12 config compatibility

### v1.3+
- `list-tools` sort grouping (safe-to-call heuristic, name-prefix sections) if N=70 alphabetical scrolls become a pain point
- ERROR-STYLE.md banned-token enforcement test if drift is observed
- `--only TOOL_NAME` CLI flag if focus-one-tool via separate config files becomes painful
