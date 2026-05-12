---
status: diagnosed
trigger: "Phase 12 UAT gap 3: config.yaml at cwd not auto-discovered; --config flag or MCPTF_CONFIG_FILE required"
created: 2026-05-09
updated: 2026-05-09
---

## Current Focus

hypothesis: CONFIRMED — Config layer only loads YAML when MCPTF_CONFIG_FILE env var is set; --config flag works by setting that env var; no cwd auto-discovery exists; CONTEXT.md "YAML config discovery" explicitly LOCKED "no cwd auto-discovery in MVP"
test: Read config.py settings_customise_sources and cli.py _load_config
expecting: YAML source registration gated on os.environ.get("MCPTF_CONFIG_FILE")
next_action: Return diagnosis (find_root_cause_only)

## Symptoms

expected: Operator drops config.yaml at repo root, runs `uv run mcp-test-framework list-tools` (no flags), framework auto-loads ./config.yaml
actual: Same default-command failure as if no config existed; only --config or MCPTF_CONFIG_FILE makes YAML load
errors: "MCP server command not found: 'homelab-mcp'" (defaults are still in effect despite config.yaml on disk)
reproduction: |
  1. Place config.yaml at repo root with mcp_server.command: uvx, args: [homelab-mcp]
  2. uv run mcp-test-framework list-tools  → fails (defaults loaded)
  3. uv run mcp-test-framework list-tools --config config.yaml  → works
started: Discovered Phase 12 UAT 2026-05-09; v1.2 backlog item per project memory

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/config.py:194-217 (settings_customise_sources)
  found: |
    YAML source is appended to the sources tuple ONLY when both conditions hold:
        yaml_path = os.environ.get("MCPTF_CONFIG_FILE")
        if yaml_path and Path(yaml_path).is_file():
            sources.append(YamlConfigSettingsSource(...))
    No Path.cwd() probe, no default yaml_file argument. If MCPTF_CONFIG_FILE
    is unset, the YAML source is never registered — even when a perfectly valid
    config.yaml is sitting in cwd.
  implication: Auto-discovery is LITERALLY UNIMPLEMENTED, not buggy. It is a
    deliberate design lock, not an oversight.

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/config.py:10-13 (module docstring)
  found: |
    "YAML overlay path comes ONLY from the ``MCPTF_CONFIG_FILE`` env var
     (CONTEXT.md "YAML config discovery" -- no cwd auto-discovery in MVP)."
  implication: The "no cwd auto-discovery" decision was LOCKED in the MVP
    CONTEXT.md, intentionally. Any v1.2 fix is reverting an explicit decision,
    not patching a bug — needs a CONTEXT.md decision-record amendment.

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/cli.py:178-211 (_load_config)
  found: |
    When path is None (no --config flag), _load_config goes straight to:
        return Config()
    No Path.cwd()/"config.yaml" probe, no MCPTF_CONFIG_FILE injection. Config()
    then sees no env var and skips the YAML source per the gate above.
    --config PATH works by doing `os.environ["MCPTF_CONFIG_FILE"] = str(path)`
    on line 199 — the flag is sugar for setting the env var.
  implication: Both code-level surfaces (env-var, --config flag) funnel through
    the same MCPTF_CONFIG_FILE entry point. Adding cwd auto-discovery in either
    layer (config.py or cli.py) closes the gap; the choice is which layer.

- timestamp: 2026-05-09
  checked: README.md lines 45, 60 (quickstart commands) and docs/EXTENDING.md
    Step 1 line 22, Step 2 line 38, Step 4 line 55, "Add a new MCP tool target"
    lines 176, 179
  found: |
    README's first quickstart example is bare:
        uv run mcp-test-framework run                       (line 45)
        uv run mcp-test-framework list-tools                (line 60)
    Only the SECOND example on line 46 shows --config:
        uv run mcp-test-framework run --config ./config.yaml
    EXTENDING.md is internally inconsistent:
        Step 1 (list-tools): no --config           (line 22)
        Step 2 (config-init -o config.yaml): no --config (line 38)  -- correct, config-init writes
        Step 4 (run --config config.yaml): explicit --config (line 55)
        "Add a new MCP tool target" Step 1: no --config (line 176)
        "Add a new MCP tool target" Step 4: no --config (line 179)
    The text on README line 92 says "in a YAML overlay pointed at by
    MCPTF_CONFIG_FILE (or --config)" — explicit pointing required, but the
    code blocks above contradict it.
  implication: The docs ALREADY teach the operator's broken mental model.
    Operators following the README's first quickstart line literally cannot
    reach the YAML overlay — there is no path that auto-binds it.

- timestamp: 2026-05-09
  checked: tests/unit/test_config.py:40-46, lines 88-101, 186-198
  found: |
    test_config.py's autouse `_isolate_cwd` fixture monkeypatches chdir to
    tmp_path on every test specifically to prevent the project's own .env from
    bleeding in (Phase 02.1 follow-up). Crucially:
      - test_yaml_overrides_default (line 88) sets MCPTF_CONFIG_FILE explicitly
      - test_no_yaml_no_env_yields_defaults (line 186) confirms no env = defaults
      - test_missing_yaml_path_doesnt_raise (line 195) confirms missing-file
        path is silently skipped (Path.is_file guard)
    There is NO test that places a config.yaml in cwd without setting any env
    var and asserts it gets loaded — because that behavior does not exist.
  implication: Adding cwd auto-discovery requires a new test asserting
    "config.yaml in cwd + no env var → loaded automatically." Existing tests
    (test_no_yaml_no_env_yields_defaults) would also need careful review:
    `_isolate_cwd` chdirs to a fresh tmp dir so that test still passes after
    the fix, but ANY test that lives under the project root WITHOUT
    `_isolate_cwd` would start picking up the repo-root config.yaml — full
    test-suite audit needed.

- timestamp: 2026-05-09
  checked: .planning/seeds/SEED-006-config-loading-safety.md (lines 53-57)
    and project memory `project_config_discovery_and_safety`
  found: |
    SEED-006 component 2: "Auto-discover cwd/config.yaml — When
    MCPTF_CONFIG_FILE is unset, look for ./config.yaml automatically.
    --config PATH continues to override (multi-config / focus-config workflow
    preserved)." Tagged as v1.2 milestone scope. Component 3 ("Fail-loud when
    no config anywhere") and Component 5 (".env precedence reform") are
    interlocking: solving #2 alone without #5 deepens the precedence puzzle
    (.env can still silently overwrite the auto-discovered YAML, per
    `project_dotenv_silently_beats_config`).
  implication: This UAT gap is the v1.2 SEED-006 component-2 work item
    surfacing through user friction. The fix is already designed; v1.2
    milestone framing is the right place to land it.

## Resolution

root_cause: |
  By design, the YAML config source in `Config.settings_customise_sources`
  (src/mcp_test_framework/config.py:212) is only registered when the
  `MCPTF_CONFIG_FILE` environment variable is set AND the file at that path
  exists. The `--config PATH` flag (cli.py:199) is sugar that sets that env
  var. There is no `Path.cwd() / "config.yaml"` probe anywhere in the config
  or CLI layer. The MVP CONTEXT.md decision-record explicitly LOCKED this
  ("no cwd auto-discovery in MVP"; cited in config.py docstring lines 10-13).

  The operator's expectation is reinforced by docs: README's first quickstart
  shows flagless `uv run mcp-test-framework run` (line 45) and
  `list-tools` (line 60); EXTENDING.md is internally inconsistent (no flag
  on Steps 1/2 and "Add a new MCP tool target" Steps 1/4; explicit --config
  only on Step 4). The runtime behavior and the docs disagree about whether
  flagless invocation should "just work" with a cwd config.yaml.

  This is identified in SEED-006 component 2 as a v1.2 milestone item.

fix:
  - "Option (a) -- config.py: Register YamlConfigSettingsSource with a default
     `yaml_file=Path.cwd() / 'config.yaml'` fallback when MCPTF_CONFIG_FILE is
     unset. Cleanest -- centralizes the discovery rule in one place; CLI and
     direct Config() consumers both benefit. Watch: tests under the repo root
     that don't use `_isolate_cwd` would start picking up the real
     config.yaml; full test-suite audit needed."
  - "Option (b) -- cli.py: In _load_config when path is None, probe
     `Path.cwd() / 'config.yaml'`; if it exists, set `MCPTF_CONFIG_FILE =
     str(probe)` before constructing Config(). Surgical, leaves config.py's
     locked invariant intact, but Config() callers outside the CLI (rare in
     this codebase) keep the old behavior."
  - "Option (c) -- docs only: Update README quickstart and EXTENDING.md
     Steps 1, 2, and 'Add a new MCP tool target' Steps 1, 4 to ALWAYS show
     `--config config.yaml`. Aligns docs with current runtime; no behavior
     change. Lowest cost, but doesn't satisfy SEED-006's safe-by-default
     vision."
  - "Option (d) -- hint on launch failure: When defaults are used and the
     server fails to launch, detect a `config.yaml` next to cwd and emit
     'did you mean to pass --config config.yaml?'. Informational; preserves
     opt-in. Useful as a complement to (a) or (b), not a substitute."
  - "Recommended for v1.2 SEED-006: combine (a) + Component 5 (.env
     precedence reform) so cwd auto-discovery doesn't get silently overridden
     by .env. Combine with Component 3 (fail-loud) so the absence of any
     config still hits a clear stop instead of running with destructive
     defaults. (b) alone leaves Config() consumers in the old state; (c)
     alone fights the user's mental model documented across SEED-006/007."

verification: |
  Diagnosis only (find_root_cause_only). No fix applied. Reproduction is
  Phase 12 UAT Test 8: drop config.yaml at repo root, run
  `uv run mcp-test-framework list-tools` (no flags), observe defaults still
  in effect.
files_changed: []
