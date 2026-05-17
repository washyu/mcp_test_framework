# Phase 28: Codegen output path (CODEGEN) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 28-codegen-output-path-codegen
**Areas discussed:** Default-path shape, Field semantics, Site-packages guard scope, --output-dir precedence

---

## A. Default-path shape

### Q1: Where should `gen-test-classes` write generated classes by default?

| Option | Description | Selected |
|--------|-------------|----------|
| `<cwd>/tests/_generated/<slug>/` | Per REQUIREMENTS CODEGEN-LIB-01 verbatim. Short, clean, no test_code/ nesting. | |
| `<cwd>/tests/test_code/<slug>/_generated/` | Matches today's recommended convention in models.py + config-init scaffold. | |
| `<cwd>/tests/_generated/<slug>/` AND emit hint to pin in config | Use REQUIREMENTS path but train operators toward explicit config via a hint message. | |
| **Other (user free-text)** | "This should fail loudly we can't assume we know where the tests should be in a project." | ✓ |

**User's choice:** Reject all three smart-default options. Fail loud when `generated_root` unset; the framework refuses to invent project layout.
**Notes:** This rewrites CODEGEN-LIB-01. The visionary call is "the framework doesn't guess where the operator's project structure lives." Aligns with the broader v1.4 "kill magic" posture (Phase 27 D-09/D-11).

### Q2: Does `--output-dir` CLI flag still exist?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — `--output-dir PATH` overrides `cfg.test_code.generated_root` | Per-invocation override; flag > config > fail-loud. | |
| **No — only `cfg.test_code.generated_root` sets the path** | One source of truth; matches Phase 27 D-11's one-config-route principle. | ✓ |
| You decide | Researcher/planner picks. | |

**User's choice:** No `--output-dir` flag. Config is the sole source of truth.
**Notes:** Reinforces D-01. Operators who need per-invocation redirection use `--config OTHER_PATH`.

### Q3: When `generated_root` is missing, what does the fail-loud error look like?

| Option | Description | Selected |
|--------|-------------|----------|
| **Operator-tone, names missing field + points at `config-init`** | Follows docs/ERROR-STYLE.md; mirrors today's missing-config-key path. | ✓ |
| Operator-tone + offer one suggested path based on cwd | Helps without committing; operator types it explicitly. | |
| Operator-tone, generic — no path suggestions | Cleanest "framework knows nothing" stance. | |

**User's choice:** Name the missing field + point at `config-init`. No cwd-inspection-based suggestions.
**Notes:** Strikes the balance — fail-loud doesn't mean unhelpful. Suggests next step without inventing a value.

---

## B. `generated_root` field semantics

### Q1: What validation does `generated_root` get beyond "not empty string"?

| Option | Description | Selected |
|--------|-------------|----------|
| Today's behavior — just "not empty string" | Schema stays dumb-pipe; all other checks at command time. | |
| Add: must be relative OR allow both | Forces project-rooted paths; prevents accidents like `/tmp/output`. | |
| Add: must NOT contain '..' segments | Defensive theater since site-packages guard catches the real issue. | |
| You decide | Researcher/planner picks. | |
| **Other (user free-text)** | "we should do todays behaviour and check the folder is empty then ask before creation." | ✓ |

**User's choice:** Schema validation stays at today's "not empty string." NEW: at command time, check if target dir is non-empty; prompt operator before overwrite.
**Notes:** Substantial UX change — today's gen-test-classes is silent wipe-and-write. Operator wants a confirmation gate on destructive writes.

### Q2: When does `gen-test-classes` prompt, and how does CI behave?

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt only if target dir is non-empty; CI requires `--yes` | Empty/missing dir → write silently. CI uses `--yes` to skip prompt. | |
| Always prompt before writing (even empty/missing) | Every run asks. Noisy for iterative authoring. | |
| **Prompt only on non-empty dir; CI auto-detects no-TTY and aborts (no flag needed)** | Heaviest "never destroy data" posture; CI must clean dir manually. | ✓ |
| You decide | Researcher/planner picks. | |

**User's choice:** No `--yes` / `--force` flag. CI in non-TTY contexts aborts on non-empty dir; operators clean manually.
**Notes:** Consistent kill-magic-no-escape-hatches stance.

---

## C. Site-packages guard scope (CODEGEN-LIB-02)

### Q1: How aggressive should the guard be?

| Option | Description | Selected |
|--------|-------------|----------|
| **Strict — refuse any target under `Path(mcp_test_framework.__file__).parent.parent`** | Single robust check; catches site-packages + editable + vendored uniformly; cross-platform. | ✓ |
| Lenient — only refuse paths containing `site-packages` / `dist-packages` segments | Cheap name-based heuristic; misses editable installs. | |
| Strict + a single bypass via `test_code.allow_unsafe_generated_root: true` | Strict default with escape hatch + loud warning. | |
| You decide | Researcher/planner picks. | |

**User's choice:** Strict, no bypass.
**Notes:** Consistent with the "no escape hatches" theme from earlier answers.

### Q2: When does the guard fire — pre-handshake or post?

| Option | Description | Selected |
|--------|-------------|----------|
| **Before handshake — check `out_root` itself, fail fast** | Resolve absolute, check, abort. Server never started. | ✓ |
| After handshake — check `out_root / slug` once slug is known | Later in lifecycle; only useful if slug could rebase (it can't). | |
| Both — pre-handshake + post-handshake | Defense in depth; zero added safety. | |
| You decide | Researcher/planner picks. | |

**User's choice:** Pre-handshake, fail fast. Per REQUIREMENTS literal "at command-start" text.
**Notes:** Cheapest, fastest, no subprocess-died noise.

---

## D. --output-dir precedence + override

D-precedence already closed in Area A Q2 (no `--output-dir` flag). Pivoted to the related open question: how does `gen-test-classes` (a Typer command, not pytest) find the config?

### Q1: How does `gen-test-classes` find the config?

| Option | Description | Selected |
|--------|-------------|----------|
| **Read `[tool.pytest.ini_options] mcp_config_file` from pyproject.toml** | Same single source of truth as pytest. `--config PATH` still overrides. | ✓ |
| Use today's behavior: `--config PATH` > `./config.yaml` autodiscovery > fail-loud | Don't touch ini; keep gen-test-classes resolution chain independent. | |
| Option 1 plus `-o key=value` pytest-style runtime overrides | Full parity; more CLI surface. | |
| You decide | Researcher/planner picks. | |

**User's choice:** Read pyproject.toml's `mcp_config_file` ini value. New precedence: `--config` flag > pyproject.toml ini > `./config.yaml` autodiscovery > fail-loud.
**Notes:** Extends Phase 27's single-config-route principle to the Typer CLI surface.

---

## Claude's Discretion

- **`out_root` relative-path resolution semantics** — today resolves against `Path.cwd()`. Post-D-11, planner picks: cwd-relative (today's convention) vs pyproject.toml-relative (matches Phase 27's `mcp_config_file` resolution). Suggested: pyproject.toml-relative for consistency.
- **`config-init` scaffold copy edits** — likely no change needed; verify D-02 error message references the scaffold's current `tests/test_code/_generated` value sensibly.
- **Non-empty-dir detection mechanism** — `any(out_root.iterdir())` (cheap) vs counting files (operator-friendlier prompt copy). Suggested: count files.
- **Guard error: include framework root in the error?** — useful for editable-install debugging; reveals internal layout. Suggested: include, since this is a developer-facing CLI.

## Deferred Ideas

- **REQUIREMENTS.md CODEGEN-LIB-01 rewrite** + **ROADMAP.md Phase 28 SC1/SC2/SC3 amendments** — handled by planner as either a Phase 28 docs plan or a quick task before Phase 29.
- Smart default for `generated_root`, `--output-dir` flag, `--yes` / `--force` flag, `allow_unsafe_generated_root` bypass — all explicitly REJECTED (see CONTEXT.md `<deferred>` "Explicitly REJECTED" subsection); future phases must not resurrect.
- `MCPTF_CONFIG_FILE` removal stays on v1.5 cleanup list (inherited from Phase 27 D-09; Phase 28 does not extend the deprecation).
- `gen-test-classes -o key=value` pytest-style overrides — deferred; `--config PATH` covers the only real use case for now.
