# Phase 25: Public-API rename (SEED-023) — `sdet` → `test_code` - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 25-public-api-rename-seed-023-sdet-test-code
**Areas discussed:** Deprecation mechanics, tests/sdet/ migration, Doc + Pydantic shape, Planning-ID sweep scope

---

## Deprecation mechanics

### Warning class

| Option | Description | Selected |
|--------|-------------|----------|
| DeprecationWarning + pytest visibility | Idiomatic Python. Hidden by default in user code; pytest shows it. Framework adds `filterwarnings = always::DeprecationWarning:mcp_test_framework` to its own pyproject so framework tests still show it. Operators running CLI see it because warnings attach to `__main__`. | ✓ |
| FutureWarning | Shown by default everywhere. Maximum operator visibility but louder — CI logs carry it on every run until they migrate. | |
| Custom MCPTFDeprecationWarning | Subclass of DeprecationWarning. Lets operators filter ours specifically without globally silencing all DeprecationWarnings. Slightly more code. | |

**User's choice:** DeprecationWarning + pytest visibility (recommended).
**Notes:** Idiomatic; operators already understand the filter semantics.

### Firing cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Once per process per shim | `warnings.warn(..., stacklevel=2)` with Python's default `default` filter — first hit of each unique (message, category, module) is shown, rest suppressed. | ✓ |
| Every call | Force `simplefilter('always')` for our category. Loud but unambiguous — operator can't miss it. Spams test logs. | |
| Once per process, total | First deprecated symbol triggers; subsequent ones stay silent. Quietest — operators may miss that multiple symbols need migration. | |

**User's choice:** Once per process per shim (recommended).
**Notes:** Standard library idiom; minimal noise.

---

## tests/sdet/ migration

| Option | Description | Selected |
|--------|-------------|----------|
| git mv + dual-scope discovery | Move test_proxmox_vm_lifecycle_readme_sample.py + conftest.py to tests/test_code/ (git mv preserves blame). Discovery scope adds tests/test_code/ FIRST + tests/sdet/ for one milestone with a one-time DeprecationWarning if anything is collected there. README sample path gets updated as part of this phase, not deferred. | ✓ |
| Dual-scope only — don't move files | Leave existing files at tests/sdet/. Discovery scope accepts both paths. Operator's existing setups (and our own dogfood file) keep working unchanged. v1.5 has to do the move. README sample path stays correct until v1.5. | |
| git mv + leave a redirect stub at tests/sdet/README.md | Move files; drop a markdown stub at tests/sdet/README.md pointing operators to tests/test_code/. Discovery scope still accepts tests/sdet/ for compat but the dir is otherwise empty after move. | |

**User's choice:** git mv + dual-scope discovery (recommended).
**Notes:** README sample-path update happens here; the snapshot itself re-captures in Phase 30 carry-forward UAT per existing deferred-item plan.

---

## Doc + Pydantic shape

### Doc rename strategy

| Option | Description | Selected |
|--------|-------------|----------|
| git mv + one-line stub at old path | Preserve blame via git mv. Drop a tiny stub at docs/SDET-AUTHORING.md: 'Renamed to TEST-CODE-AUTHORING.md — removed in v1.5.' Old internal links keep working as a one-hop redirect. | ✓ |
| Hard git mv — no stub | Move the file, period. Old path is 404 immediately. Phase 30 README rewrite catches all internal links; repo is private so no external risk. | |
| Fork (keep both copies in sync for v1.4) | Both files exist with identical content; both have the deprecation banner at the top of the old one. Heaviest maintenance burden — doc edits must touch both. | |

**User's choice:** git mv + one-line stub (recommended).

### Pydantic alias pattern

| Option | Description | Selected |
|--------|-------------|----------|
| AliasChoices + model_validator(mode='before') that warns | Single field `test_code: TestCodeConfig = Field(validation_alias=AliasChoices('test_code','sdet'))`. A model_validator pre-step inspects the raw dict: if 'sdet' is present, emit DeprecationWarning (once per process) and rename the key before validation. | ✓ |
| Two fields + model_validator collapsing old→new | Keep `sdet: TestCodeConfig \| None = None` AND `test_code: TestCodeConfig \| None = None`. Validator: if both, raise; if only sdet, warn + copy to test_code + null out sdet. Two surface fields = more places for mistakes; clearer per-field semantics. | |
| Property shim on the resolved model | Only `test_code` as a real field. Add a `@property` `sdet` on the parent config that returns `test_code` (with a warn). YAML loading does NOT accept the old key — breaks RENAME-05 acceptance. | |

**User's choice:** AliasChoices + model_validator(mode='before') (recommended).
**Notes:** Decision D-13 extends this: if BOTH `sdet:` and `test_code:` keys are present in the same YAML, raise a friendly ValidationError — no silent precedence rule.

---

## Planning-ID sweep scope

### Surface scope

| Option | Description | Selected |
|--------|-------------|----------|
| README + CLAUDE.md + docs/ + src/ docstrings + CLI --help | Exactly what operators see. INCLUDES: README.md, CLAUDE.md, all docs/*.md, all docstrings in src/mcp_test_framework/, Typer --help output, error messages. EXCLUDES: .planning/, tests/, internal _-prefixed names, dunders, git history. Matches v1.3 Phase 22 precedent. | ✓ |
| Above + tests/ docstrings | Same as Recommended plus pytest test names/docstrings. More work; arguably tests/ aren't 'operator-facing'. | |
| Operator-facing surfaces only — README + docs/ + CLI help | Narrowest. Skips CLAUDE.md and src/ docstrings on the theory that those are dev-facing. Phase 22 explicitly included CLI docstrings; narrower would be a regression. | |

**User's choice:** README + CLAUDE.md + docs/ + src/ docstrings + CLI --help (recommended).

### Pattern scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both planning IDs and 'sdet' terminology | Planning IDs regex + `\bsdet\b` (case-insensitive) and `\bSDET\b`. Exclusions allowed via `# noqa: sdet-rename-shim` markers and changelog/migration sections. Zero matches after exclusions = acceptance. | ✓ |
| Planning IDs only — leave 'sdet' terminology to manual review | Search just for `/\b[A-Z]+-\d+\b/` planning IDs. Terminology rewrite happens manually file-by-file. Slower, more human judgement, possible misses. | |
| Custom regex defined per file | No single sweep — each operator-facing file gets its own checklist. Most thorough; most overhead. Probably overkill since the rename is well-bounded. | |

**User's choice:** Both planning IDs and 'sdet' terminology (recommended).
**Notes:** Acceptance ships as a CI-runnable gate (script or pytest test) so Phase 26+ can't reintroduce a leak.

---

## Claude's Discretion

- Exact wording of the six DeprecationWarning message strings (kept parallel; planner picks prose).
- File-order of edits inside the rename plans.
- Typer mechanism for `--test-code` / `--sdet` flag coexistence (alias vs two options that set the same var).
- Whether the alias shim's warning fires from `__init__.py` of the new package or from a lightweight `sdet/` re-export module.

## Deferred Ideas

- `scoped_register()` multi-server context manager — Phase 27 framing if it surfaces there; not Phase 25.
- URL-style judge kwarg (`judge="ollama://..."`) — Phase 28 framing.
- Schema v2→v3 migration (drops `sdet`-key alias entirely) — v1.5.
- Auto-discovery `register(tools=None)` — v1.5.
- Full retirement of `sdet` surface (removing deprecation aliases) — v1.5.
- Per-judge `--debug` breakdown — v1.5 cohort with SEED-003.
