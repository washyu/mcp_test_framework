---
status: diagnosed
trigger: "config-init fails with 'MCP server command not found: homelab-mcp' when operator's MCP server is uvx-installed (not on PATH)"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — config-init has no inline override flags; Pydantic default `mcp_server.command = "homelab-mcp"` is the only source absent a pre-existing config.yaml/.env, so launch fails on uvx systems before tools can be discovered
test: read cli.py config-init signature + _list_tools_async, models.py defaults, EXTENDING.md walkthrough Step 2, README quickstart
expecting: chicken-and-egg confirmed
next_action: return diagnosis (find_root_cause_only mode)

## Symptoms

expected: An operator with a uvx-installed MCP server can run `mcp-test-framework config-init` against their server out of the box and get a populated scaffold.
actual: Error "MCP server command not found: 'homelab-mcp'" — but `uvx homelab-mcp` works in same shell
errors: |
  MCP server command not found: 'homelab-mcp'
  the framework tried to launch the server with `homelab-mcp `
  if your server is installed via `uvx` or `pipx`, set `mcp_server.command` and `mcp_server.args` in your config.yaml
reproduction: Phase 12 UAT Test 7. Run `uv run mcp-test-framework config-init -o /tmp/test-scaffold.yaml` from a fresh checkout where the MCP server is installed via uvx (not on PATH).
started: Discovered during UAT 2026-05-09

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/models.py:61-68
  found: |
    McpServerConfig.command field default is the literal string "homelab-mcp":
        command: str = Field(
            default="homelab-mcp",
            validation_alias=AliasChoices("MCP_SERVER_COMMAND", "command"),
        )
        args: list[str] = Field(
            default_factory=list,
            ...
        )
    So in the absence of YAML overlay, .env, or env vars, the framework will
    try to launch `homelab-mcp` (no args) — exactly what the user observed.
  implication: The hard-coded "homelab-mcp" default is project-bias from the
    pre-v1.2 spec leaking into a generic framework, AND it ships an empty
    args list (so even if homelab-mcp were on PATH, the .env.example pattern
    of `uvx homelab-mcp` is not the default).

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/cli.py:384-481 (config_init Typer command)
  found: |
    config-init has exactly three CLI options: --config, --output/-o, --force.
    There is no --command, --arg/--args, --mcp-cmd, or any inline override
    of mcp_server.command/args. The launch path is:
        cfg = _load_config(config)             # line 435 -- Config() with defaults if no --config
        ...
        runner.run(_list_tools_async(cfg))     # line 439 -- launches subprocess

    `_list_tools_async` (line 493) reads cfg.mcp_server.command/args/timeout
    and feeds them straight to McpTestClient. There is no opportunity for
    the operator to inject command/args at the CLI surface.
  implication: The ONLY way an operator can change command/args before the
    discovery launch is to (a) hand-write a config.yaml + pass --config, or
    (b) set MCP_SERVER_COMMAND / MCP_SERVER_ARGS env vars, or (c) write a
    .env file. None of these are mentioned in the EXTENDING walkthrough
    Step 2. From a fresh checkout with no .env, the operator is stuck.

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/cli.py:444-471 (config_init FileNotFoundError handler)
  found: |
    On launch failure (FileNotFoundError "MCP server command not on PATH:"),
    config-init calls _emit_operator_error which raises typer.Exit(2). It does
    NOT fall back to writing a stub scaffold with `tools: []` — the operator
    gets a hard error and no file is written.

    The error message (line 446-461) does mention "if your server is installed
    via `uvx` or `pipx`, set `mcp_server.command` and `mcp_server.args` in your
    config.yaml" — but config.yaml doesn't exist yet (that's what config-init
    is supposed to produce). The next-step text says "verify the launch
    command works in your shell, then update mcp_server.command/args in your
    config.yaml" with no instruction on how to bootstrap that file.
  implication: The error message creates a circular reference — telling the
    operator to "update config.yaml" when config-init's job is to PRODUCE
    that file. Aligns exactly with [Scaffolds must be runnable]
    feedback in MEMORY.md.

- timestamp: 2026-05-09
  checked: docs/EXTENDING.md:36-41 (Step 2 — scaffold a config)
  found: |
    Step 2 reads:
        Run `mcp-test-framework config-init -o config.yaml`. The framework
        will launch the server, list its tools, and write a self-contained
        config file with every discovered tool listed as `skip: true` and
        a hint to remove the skip from the ones you want to test.

    No mention of: (a) needing the server to be on PATH, (b) the uvx/pipx
    case, (c) needing to set MCP_SERVER_COMMAND/ARGS first, (d) any pre-step
    to point the framework at the launch command.
  implication: Walkthrough is silent on the bootstrap problem. Operator
    following EXTENDING in order will hit the wall at Step 2 if the server
    isn't on PATH.

- timestamp: 2026-05-09
  checked: README.md:13-25, 85-86, 229-231
  found: |
    README quickstart prerequisite says:
        - `homelab-mcp` runnable via `uvx` (the `.env.example` default) or
          installed on `PATH`
    And the env-var defaults table documents MCP_SERVER_COMMAND="homelab-mcp"
    and notes ".env.example ships uvx for zero-install."

    So the README assumes the operator has a populated .env.example copied to
    .env (or is using homelab-mcp specifically). For a fresh checkout / new
    operator running config-init against a different server, .env.example
    isn't relevant and the homelab-mcp default actively misleads.
  implication: README and EXTENDING both bake in the homelab-mcp/.env.example
    defaults; this works only for the project's own canonical SUT. The
    operator persona ("Vibe-coded MCP" — server author may not know the
    framework's launch defaults) breaks immediately.

- timestamp: 2026-05-09
  checked: src/mcp_test_framework/cli.py:668-733 (_format_tools_yaml_scaffold)
  found: |
    The generated scaffold at line 698-700 hard-codes:
        mcp_server:
          command: "uvx"
          args: ["your-mcp-server-package"]
    So the scaffold output ITSELF acknowledges uvx is the expected pattern,
    but the runtime default in models.py is "homelab-mcp" with no args.
    Inconsistency: scaffold template says "uvx your-package", runtime default
    says "homelab-mcp" alone.
  implication: The scaffold author already knew uvx was the operator-friendly
    default. The same insight wasn't carried back into McpServerConfig
    defaults or into a config-init bootstrap path.

## Resolution

root_cause: |
  Bootstrap chicken-and-egg confirmed. config-init must launch the configured
  MCP server to discover its tools, but its only sources of mcp_server.command/
  args are (in precedence order):
    1. Init kwargs — none, because config-init defines no --command/--arg flags
       (cli.py:384-405)
    2. Env vars (MCP_SERVER_COMMAND / MCP_SERVER_ARGS)
    3. .env file
    4. YAML overlay via --config PATH
    5. Pydantic default — "homelab-mcp" with empty args (models.py:61-68)
  On a fresh checkout with no .env and no pre-existing config.yaml, the only
  source that fires is the Pydantic default. That default is a project-bias
  literal "homelab-mcp" that requires the server be on PATH (not uvx-launched),
  which fails for the documented operator persona. The error message then
  tells the operator to "update config.yaml" — the file config-init exists
  to produce. EXTENDING.md Step 2 doesn't acknowledge any pre-step.

fix: (deferred — find_root_cause_only mode; recommendation in summary below)
verification: (deferred)
files_changed: []
