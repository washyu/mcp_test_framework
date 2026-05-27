# Phase 34: Opt-in host isolation passthrough (999.3) - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator can opt into `host_isolation: passthrough` so live-UAT + SDET scenarios reach the operator's real credentials, HOME, and keyring — at the explicit cost of pytest-xdist parallelism — while every bare `Config()` caller in `src/` + `tests/` is audited so neither mode silently leaks env across the spawn seam.

**In scope (ISOL-01..06):**
- New top-level `host_isolation: Literal['strict','passthrough'] = 'strict'` field on `Config`
- `passthrough` mode bypasses allowlist + HOME-redirect + null-keyring injection at the spawn site (literal `os.environ` copy)
- `passthrough` clamps pytest-xdist worker count to 1 with operator-tone explanation; `strict` unchanged
- Bare `Config()` caller audit across `src/` + `tests/` — every site documented; routed through the resolved-config seam where leakage matters
- README + `docs/LIBRARY-MODE.md` document the trade-off, cite SEED-022 safety delegation, surface the no-keyring-faking lock, call out xdist incompatibility

**Out of scope (different phases / backlog):**
- Renaming `_build_isolated_env` (covered by the dispatcher rename; not a separate cleanup pass)
- Selective passthrough (per-tool or per-env-var) — `passthrough` is all-or-nothing for v1.5
- Credential-mock / keyring virtualization — locked off-table per memory `project_isolation_blocks_live_uat.md` (no keyring faking)
- SEED-002 (xdist resource markers) — referenced by ISOL-04 UX framing but not delivered; deferred v1.6+
- Phase 999.5 (framework self-test pollution when `MCPTF_CONFIG_FILE` set) — env-var route already gone post-Phase-31; the bare-caller audit here MAY surface a residual class-of-bug but does not commit to a fix in this phase
- Phase 35 SHIM-09 regression gate (separate capstone phase that asserts the new top-level field exists and the legacy always-on-isolation surface is gone)

</domain>

<decisions>
## Implementation Decisions

### Config field shape & placement (ISOL-01)

- **D-01:** Field placement is **top-level** `Config.host_isolation`. Sits next to `mcp_server`, `ollama`, `tools`, `test_code`. Operator-visible in `config-init` scaffolds. No new `runtime:` container — keeps the config surface flat and the Phase 35 capstone's grep target trivial.
- **D-02:** Field type is **`Literal['strict','passthrough']`** (not a custom Enum, not a `bool`). Matches the `skip_buckets: list[Literal[...]]` precedent set by Phase 33 BUCKET-01. `extra='forbid'` is already on `Config`; Pydantic surfaces a stock `literal_error` on typo with the valid values named.
- **D-03:** Default is **explicit on the model**: `host_isolation: Literal['strict','passthrough'] = 'strict'`. Operator who omits the key gets v1.0–v1.4 always-on isolation behavior automatically. Bare `Config()` returns a complete, valid config. Phase 35 capstone can assert `Config().host_isolation == 'strict'` directly.
- **D-04:** Typo rejection follows the **Phase 31 D-01/D-02 operator-tone mapper pattern**. Let Pydantic produce its stock `literal_error` for `host_isolation` with an unknown value; extend `cli.py:_emit_operator_error_for_validation_error` (and the shared error mapper used by `_plugin.py` per Phase 31 D-04) with a branch keyed on `(err_type='literal_error', loc=('host_isolation',))`. Three-part message: summary names the bad value; detail names the two valid modes + cites the trade-off in one line; next_step points at `docs/LIBRARY-MODE.md` §host-isolation. Pinned by a new assertion under `tests/framework/unit/test_error_style.py` so future shim-style edits don't drift it.

### Passthrough env shape at the spawn site (ISOL-02 + ISOL-03)

- **D-05:** Under `passthrough`, the env passed to `StdioServerParameters(env=...)` is a **literal `dict(os.environ)` copy** — nothing stripped, nothing injected. No allowlist filter, no `MCP_*` re-injection (operator already has those if they care), no `PYTHON_KEYRING_BACKEND=...null...` override, no HOME/USERPROFILE/TEMP redirect. Operator's mental model: "passthrough is what `uvx homelab-mcp` would see from my shell." The hermetic property is explicitly traded for credential reachability.
- **D-06:** Under `passthrough`, the per-session `_isolated_home` fixture **short-circuits** — no tempdir allocated, no cleanup machinery engaged. The tempdir's sole consumer was the HOME redirect that passthrough disables; allocating it would be dead state. The fixture yields `None` (or equivalent) in passthrough mode; the spawn site never reads it.
- **D-07:** Mode-branching lives **inside `_isolation.py`** as a new dispatcher. Add `_build_passthrough_env() -> dict[str,str]` as a sibling to the existing `_build_isolated_env(isolated_home)`. Export a single `_build_subprocess_env(mode: Literal['strict','passthrough'], isolated_home: Path | None) -> dict[str,str]` dispatcher that picks the right builder. Spawn sites (`fixtures.py:432`, `mcp_client.py:189`) call the dispatcher only. The existing `_build_isolated_env` keeps its name (no rename churn); the dispatcher is the new public-internal API. Single-file maintainer story; `_isolation.py` stays the canonical isolation surface and grows linearly with future modes.
- **D-08:** The caller **passes the mode explicitly** to the dispatcher; `_isolation.py` does not import `config.py`. Both spawn sites already have `cfg` in scope (`fixtures.py` via the `mcp_config` fixture, `mcp_client.py` via constructor) and pass `cfg.host_isolation` as the `mode` arg. Keeps the isolation primitive Config-agnostic, testable with a plain string, and SEED-022-clean (framework primitive takes data, not a Config blob).

### Claude's Discretion (recommended defaults — planner free to revisit with research)

The following were surfaced but the user did NOT select them for discussion. Recorded defaults below; flag during planning if a deviation is needed.

- **xdist clamp UX (ISOL-04).** When operator runs `-n>1` with `host_isolation: passthrough`: **silent clamp to 1 + one-shot red `[mcp-contracts]` banner** following the Phase 31 D-08 visibility-upgrade pattern (the formatwarning override / domain-UI banner integration already lands there). Banner text follows the operator-tone three-part shape: what happened ("xdist worker count clamped to 1") → why ("host_isolation=passthrough serializes subprocess spawns so operator credentials remain a single-owner resource") → next_step ("switch to host_isolation=strict for parallel xdist runs"). Hook target: `pytest_configure` mutates `config.option.numprocesses` to 1 BEFORE pytest-xdist's own `pytest_configure_node` runs. Research-for-plan: verify the hook ordering / `tryfirst` requirement against pytest-xdist's plugin-load sequence; fall back to `pytest_xdist_setupnodes` if the early mutation doesn't take. Hard error rejected — operator opting into passthrough has already accepted the trade-off; loud-but-recoverable beats fail-loud.
- **Bare `Config()` audit scope + remediation (ISOL-05).** Three call sites in `src/`: `fixtures.py:111` (the `mcp_config` fixture's legacy fallback when no plugin stash is present — framework self-test path), `test_code/session.py:67` (test-code generated_root lookup), `cli.py:15` (docstring reference only — no behavior). Dozens more in `tests/framework/` (test-doubles / construction patterns inside the framework's own unit + smoke suites). Audit remediation default: **document inline + route through the plugin stash where it matters**. For each `src/` site, add a 2-line comment block stating (a) which mode it implicitly assumes and (b) why bare construction is correct here OR plumb through `request.session.config._mcp_contracts_config` (the Phase 31 D-10 stash). `test_code/session.py:67` is the highest-risk site — when operator runs test-code scenarios under `passthrough`, a bare `Config()` re-read at fixture-resolution time could miss the resolved YAML's `host_isolation` value. Research-for-plan: confirm whether `test_code/session.py:67` runs after or before the plugin's stash population (likely after — it's a `pytest_asyncio.fixture`); if after, route it through the stash. For `tests/framework/`, the audit produces a categorized inventory (which sites assume strict, which test the mode directly, which are mode-agnostic) committed alongside the implementation, not a refactor of every site.
- **Docs worked example.** Use the **real homelab-mcp Proxmox credential repro** from memory `project_isolation_blocks_live_uat.md` (2026-05-19 Phase 30 UAT-1): operator runs `uvx homelab-mcp credentials list` and sees their Proxmox credential; under default `strict` the framework's spawned subprocess gets `No Proxmox credentials found`; flipping `host_isolation: passthrough` in `config.yaml` restores credential reachability. Same example in README + `docs/LIBRARY-MODE.md` (parity with Phase 33 D-03). Doc block follows Phase 33 D-03 shape: YAML config snippet + the `mcp-contracts run` output before+after + the xdist-clamp banner verbatim. ~30–50 lines per doc. SEED-022 + no-keyring-faking lock cited in the same section, not a separate sidebar.
- **`config-init` scaffold emission.** New scaffolds emit `host_isolation: strict  # 'strict' (default, isolated) or 'passthrough' (operator creds reachable, xdist=1)` — uncommented, default value spelled, mode trade-off in a single-line inline comment. Operator who runs `config-init` after Phase 34 ships sees the knob immediately without reading the docs first.
- **Bumping `Config.model_config` constraints.** No changes needed — `extra='forbid'` is already on `Config`, the new `Literal` field inherits the validation behavior automatically. No new `@model_validator` required (D-02 + D-04 are sufficient).

### Folded Todos

None — `gsd-sdk todo.match-phase 34` returned `todo_count: 0`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + locked requirements
- `.planning/ROADMAP.md` §"Phase 34" — Goal + 5 success criteria (passthrough env shape, strict-unchanged baseline, xdist clamp + operator-tone explanation, bare-Config audit scope, docs trade-off + SEED-022 + no-keyring-faking lock + xdist callout).
- `.planning/REQUIREMENTS.md` §"ISOL" L37–46, L98–103 — ISOL-01 (config field), ISOL-02 (env shape), ISOL-03 (keyring), ISOL-04 (xdist clamp), ISOL-05 (bare-Config audit), ISOL-06 (docs).
- `.planning/STATE.md` §"Deferred Items" — SEED-002 + 999.5 cross-references that bound this phase's scope.

### Memory (lock entries the design MUST respect)
- Memory `project_isolation_blocks_live_uat.md` — origin of the phase. The 2026-05-19 Proxmox credential repro is the canonical worked example (Claude's Discretion). Locks: no keyring faking; opt-in `passthrough` direction; bare-Config audit must cover all `Config()`-at-host-env callers together.
- Memory `project_framework_primitives_sdet_safety_principle.md` — SEED-022. Framework does no SUT-safety reasoning; operator decides what to call. Cite if any planner proposal drifts toward "auto-detect dangerous tools under passthrough" or "warn before destructive tool calls when passthrough is on" — that direction is off-table.
- Memory `feedback_phase_scope_intent.md` — phase scope = phase title. Resist sub-agent reframing of ISOL-05 (bare-Config audit) as cross-cutting / defer. The audit lands in Phase 34, period.

### Existing isolation surface (the code being extended)
- `src/mcp_test_framework/_isolation.py` — full file. The locked allowlist constants (`_PASSTHROUGH_ALLOWLIST`, `_MCP_PREFIX`, `_HOME_OVERRIDES`, `_KEYRING_OVERRIDES`) and `_build_isolated_env(isolated_home)` are the existing surface. D-07 + D-08 add `_build_passthrough_env()` and `_build_subprocess_env(mode, isolated_home)` siblings here. Module-level docstring already documents the "isolation is ALWAYS-ON; no toggle" constraint — UPDATE the docstring to reflect the new opt-in passthrough seam.
- `src/mcp_test_framework/fixtures.py` L40 (import), L359–395 (`_isolated_home` session fixture — D-06 short-circuit landing site), L397–~432 (`mcp_client` fixture; L432 is the `env=_build_isolated_env(...)` spawn call — D-07/D-08 plumbing site).
- `src/mcp_test_framework/mcp_client.py` L48 (import), L180 (`isolated_home = Path(...)`), L189 (`env=_build_isolated_env(...)` spawn call — second D-07/D-08 plumbing site).
- `src/mcp_test_framework/models.py` (or wherever `Config` lives — research must locate current home post-Phase-31; the `extra='forbid'` model_config and the existing top-level fields are the template for D-01 / D-02 / D-03).

### Operator-error mapper (the rewrite shape D-04 must match)
- `docs/ERROR-STYLE.md` — operator-tone three-part error shape (summary / detail / next_step), pinned by source-text regression tests under `tests/framework/unit/test_error_style.py`.
- `src/mcp_test_framework/cli.py:_emit_operator_error_for_validation_error` — existing dispatcher with branches per `(err_type, loc)` pair. D-04 adds a new branch keyed on `('literal_error', ('host_isolation',))`. Same `_emit_operator_error(summary=, detail=, next_step=)` shape.
- `src/mcp_test_framework/_plugin.py:pytest_configure` — the library-mode error-mapper hook (factored out in Phase 31 D-04 if research confirms; same mapper renders the new branch in both CLI and library mode).

### Phase 31 patterns this phase mirrors
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md` — D-01/D-02 (Pydantic `extra='forbid'` + targeted CLI mapper branch + operator-tone three-part error) is the template for D-04 here. D-08 (formatwarning override / `[mcp-contracts]` red banner) is the visibility surface the xdist-clamp banner reuses (Claude's Discretion).
- `.planning/phases/33-per-bucket-skip-granularity-in-toolconfig-999-1/33-CONTEXT.md` — D-03 (~25–40 lines per doc, YAML + expected output + digest slice, real homelab-mcp tool not synthetic) is the template for the README + `docs/LIBRARY-MODE.md` worked example (Claude's Discretion).

### Operator-facing docs to update
- `README.md` — ISOL-06 worked example using the homelab Proxmox credential repro (Claude's Discretion).
- `docs/LIBRARY-MODE.md` — ISOL-06 worked example + the canonical anchor `cli.py:_emit_operator_error_for_validation_error`'s next_step points at.
- `docs/ERROR-STYLE.md` — register the new `host_isolation` `literal_error` operator-tone message.
- `docs/EXTENDING.md` — light pass to confirm no stale references to "isolation is ALWAYS-ON".

### Live external context worth re-reading at plan time
- `src/mcp_test_framework/test_code/session.py` L67 — the highest-risk bare `Config()` site under passthrough (Claude's Discretion D-05's bare-Config audit). Verify whether this fixture runs after the plugin's stash population during plan-phase research.
- pytest-xdist plugin hooks documentation — research-for-plan: confirm the hook ordering for the xdist worker-count clamp (Claude's Discretion ISOL-04). Likely `pytest_configure(tryfirst=True)` mutating `config.option.numprocesses`, with `pytest_xdist_setupnodes` as the fallback.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_build_isolated_env(isolated_home)` in `_isolation.py`** — keeps its name and behavior; D-07 adds a sibling `_build_passthrough_env()` and a dispatcher `_build_subprocess_env(mode, isolated_home)` rather than renaming. Module-level constants (`_PASSTHROUGH_ALLOWLIST`, `_HOME_OVERRIDES`, `_KEYRING_OVERRIDES`) stay unchanged under strict.
- **`cli.py:_emit_operator_error_for_validation_error` dispatcher** — D-04 adds one new `(err_type, loc)` branch. Phase 31 D-04 already factored (or will factor) the helper into a shared module so `_plugin.py` reuses it in library mode — same factoring covers Phase 34's new branch without duplication.
- **`_isolated_home` session-scoped fixture (`fixtures.py:359–395`)** — D-06 short-circuit landing site. The fixture already yields a Path; under passthrough it yields None (or a sentinel the dispatcher accepts as "no redirect needed").
- **Phase 31 D-08 formatwarning override / `[mcp-contracts]` red-banner surface** — the xdist-clamp banner (Claude's Discretion ISOL-04) reuses this surface rather than introducing a parallel output channel.
- **`pytest_configure` hook in `_plugin.py`** — already runs before pytest-xdist's node setup; D-04 error-mapper trigger AND the xdist clamp (Claude's Discretion) both ride this hook.

### Established Patterns
- **`extra='forbid'` on every operator-facing model** — `Config` already enforces it. D-01/D-02 inherit automatically; typos at load time, not runtime.
- **Operator-tone three-part error contract** — summary / detail / next_step, pinned by `tests/framework/unit/test_error_style.py`. D-04 conforms; new pinned test added for the `host_isolation` typo case.
- **Caller-passes-data primitives (SEED-022)** — `_isolation.py` does not import `config.py`. D-07/D-08 keep this; the dispatcher takes a `mode: Literal[...]` arg, not a `cfg: Config` arg.
- **Single-mapper-surface across CLI + library modes** — Phase 31 D-04 established that `cli.py` and `_plugin.py` share one error-mapper helper. D-04 inherits this; the new branch is visible to both personas.
- **Capstone-friendly single grep target** — top-level `Config.host_isolation` (D-01) means Phase 35 SHIM-09 regression-gate sweeps for the field name with one regex; no nested-path grammar to maintain.

### Integration Points
- **`Config` model** — new top-level field lands here (D-01). No new sub-model, no new `model_validator`.
- **`_isolation.py` `_build_subprocess_env` dispatcher** — the new public-internal API. Two spawn sites (`fixtures.py:432`, `mcp_client.py:189`) call it.
- **`_isolated_home` fixture** — D-06 branch yields `None` under passthrough; spawn-site dispatcher accepts None as "no redirect".
- **`cli.py:_emit_operator_error_for_validation_error` + shared mapper helper** — D-04 branch.
- **`pytest_configure` (in `_plugin.py`)** — Claude's Discretion ISOL-04 clamp; runs `tryfirst` to mutate `config.option.numprocesses = 1` before xdist's own setup.
- **`config-init` scaffold emitter** — Claude's Discretion; new scaffolds emit the `host_isolation:` line with the strict default + inline trade-off comment.

</code_context>

<specifics>
## Specific Ideas

- **Field name + values are locked** by REQUIREMENTS.md ISOL-01: `host_isolation: strict | passthrough`, default `strict`. Do NOT propose alternatives (e.g. `isolate: true/false`, `mode: hermetic | live`); ROADMAP + REQUIREMENTS + docs all pin these strings.
- **D-05 (literal `os.environ` copy under passthrough)** is operator-aligned with the 2026-05-19 Phase 30 UAT-1 repro: operator's mental model is "passthrough = what my shell sees." Anything less (allowlist + denylist hybrid) drifts from that model and re-creates the SEED-022 violation of the framework reasoning about which env vars are "dangerous."
- **No keyring faking — locked.** If any planner / research / fixer proposal proposes a credential-mock layer, virtualized keyring backend, or "test-only keyring backend env-var injection" — STOP and cite memory `project_isolation_blocks_live_uat.md`. That direction is off-table.
- **xdist clamp banner wording draft (Claude's Discretion ISOL-04)** — not operator-approved yet, but the structural shape is locked: three-part operator-tone, lives on the Phase 31 D-08 banner surface, fires once at session start (not per-tool, not per-test). Planner pins the exact text against `tests/framework/unit/test_error_style.py`.
- **Phase 30 UAT-1 worked example (Claude's Discretion docs)** — the homelab-mcp Proxmox credential repro from memory is the canonical example. Do NOT substitute a synthetic example; the value proposition is the real-world repro.
- **The bare-Config audit is a Phase 34 in-scope deliverable.** Memory `feedback_phase_scope_intent.md` locks this. If a sub-agent proposes deferring ISOL-05 to a separate "audit-only" phase, cite the memory and pull it back into scope.

</specifics>

<deferred>
## Deferred Ideas

- **Selective per-env-var passthrough** — operator declares an allowlist of env vars to inherit (`host_isolation_allowlist: [HOMELAB_TOKEN, AWS_*]`) instead of all-or-nothing. Tempting but expands the public config surface and forces the framework to reason about which vars are "safe" — drifts back toward the SEED-022 violation. Defer to v1.6+ if real demand surfaces; v1.5 ships the binary `strict | passthrough` only.
- **Per-tool isolation mode** — `tools.create_proxmox_vm.host_isolation: passthrough` so individual tools opt in without flipping the whole session. Would re-introduce xdist resource-marker complexity (SEED-002) and inflate the test matrix. Defer.
- **`_build_isolated_env` rename to `_build_strict_env`** — symmetric naming with `_build_passthrough_env`, but a pure-renaming churn that Phase 35 SHIM-09 grep targets would also need to track. Defer; the dispatcher `_build_subprocess_env` is the new public surface, the legacy name stays internal.
- **Phase 999.5 (framework self-test pollution when env-var path-pointers leak into bare `Config()`)** — STATE.md flags this for re-assessment after Phase 31. The env-var route is already gone post-Phase-31; the underlying class-of-bug (pydantic-settings deep-merge interactions for bare-construction patterns) MAY surface during the ISOL-05 audit. If it does, plan a separate hotfix phase; the audit is in-scope but the class-of-bug fix is not.
- **xdist resource markers (SEED-002)** — would let `passthrough` mode keep xdist worker count >1 by serializing per-resource (e.g. one worker per MCP-server resource). Referenced by ISOL-04 framing but not delivered; v1.6+ cohort.
- **Operator-facing `mcp-contracts diag host-isolation`** subcommand that prints "current mode = X; subprocess will see HOME=Y, USERPROFILE=Z, keyring backend=W". Diagnostic value, especially for debugging credential-reachability surprises. Out of v1.5 scope; backlog candidate.

### Reviewed Todos (not folded)

None — `gsd-sdk todo.match-phase 34` returned `todo_count: 0`; no todos to review.

</deferred>

---

*Phase: 34-Opt-in host isolation passthrough (999.3)*
*Context gathered: 2026-05-26*
