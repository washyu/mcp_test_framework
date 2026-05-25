# Extending mcp_test_framework

This doc describes the two MVP extension seams: subclassing the `Rubric` base
to add new description-quality dimensions, and implementing the `Judge`
Protocol to swap the LLM-judge backend. Both extensions live in your own
`conftest.py` (or any pytest plugin) -- no source changes to the framework
are needed.

The framework's built-in rubrics are session-scoped fixtures wired in
`src/mcp_test_framework/fixtures.py`; the framework's default judge is
`OllamaJudge` (`src/mcp_test_framework/ollama_judge.py`). User overrides
follow the same shape.

## Testing an MCP server you didn't write

The framework is designed for operators testing MCP servers they did not
author. The "black box" rule (no SUT imports, no SUT source reading) is a
feature of the persona, not a test-discipline rule you must obey.

### Step 1 — discover the surface

Run `mcp-contracts list-tools --config config.yaml` against your server's
launch command (if you don't have a `config.yaml` yet, see Step 2 below for the
bootstrap recipe). You will see one block per tool, for example:

```text
list_keyring_credentials(service: str)
  Read the named credential from the user's OS keyring.
```

The parameter signature comes from the tool's declared `inputSchema`. Add
`--full` to see the full description and per-parameter descriptions:
`mcp-contracts list-tools --config config.yaml --full --name keyring`. The `--name PATTERN`
flag substring-matches case-insensitively, useful at large surfaces (~70+
tools).

### Step 2 — scaffold a config

Run `mcp-contracts config-init --command uvx --arg homelab-mcp -o config.yaml`.
The framework will launch the server, list its tools, and write a
self-contained config file with every discovered tool listed as `skip: true`
and a hint to remove the skip from the ones you want to test. No tool will
run until you opt in.

#### Servers installed via `uvx` or `pipx`

If your server isn't on `PATH` directly — for example, you launch it with
`uvx homelab-mcp` or `pipx run my-mcp-server` — pass the launcher as
`--command` and the package (plus any args) as repeated `--arg` flags:

```bash
mcp-contracts config-init --command uvx --arg homelab-mcp -o config.yaml
```

These flags override `mcp_server.command` / `mcp_server.args` for this one
invocation, so the framework can launch the server, list its tools, and
write the scaffold even on a fresh checkout with no pre-existing
`config.yaml`. After the scaffold lands, edit the generated `mcp_server`
block to record the same `command` / `args` values, so subsequent
`mcp-contracts run --config config.yaml` invocations work without the
flags.

If the launch still fails (the launcher itself isn't on `PATH`, or the
package name is wrong), `config-init` will write a fallback scaffold
shell to `--output` containing the four top-level blocks and an empty
`tools:` mapping, alongside an operator-tone error on stderr. Edit the
`mcp_server.command` / `mcp_server.args` lines and re-run `config-init` to
populate the tool list.

### Step 3 — opt in tool-by-tool

Open `config.yaml` and, for each tool you want the framework to call,
remove the `skip: true` and `skip_reason:` lines from its entry. For tools
that require non-empty input, add a `call_arguments:` block (see
`config.example.yaml` for the pattern). For destructive tools you want
the framework to know about but never call, leave `skip: true` and write
a curated `skip_reason:` so the test summary explains why the tool sat
out.

### Step 4 — run

`mcp-contracts run --config config.yaml`. The framework spawns the
server, calls each enabled tool, asks the configured Ollama judge to
evaluate the description against the rubrics you listed, and exits 0 if
every test passed.

### CI secrets

If your judge backend reads a secret from the environment (an HTTP-backed
judge with an API key, for example), set it in `.env` rather than
`config.yaml` — secrets do not belong in version-controlled config. The
framework ships a `.env.example` at the repo root documenting this
CI-secret passthrough convention; copy it to `.env` ONLY if you have such
a secret to set. Env vars do not override `config.yaml` values, and the
example file is not part of normal local setup.

You never read your server's source. You configured the framework against
the surface the server itself declares.

## Add a new description-quality rubric

The `Rubric` base class (`src/mcp_test_framework/rubrics.py`) is a frozen
Pydantic model with two fields: `dimension` (a short label) and
`dimension_criteria` (the question the judge answers). The framework's three
built-in rubrics (`ClarityRubric`, `DisambiguationRubric`, `ParametersRubric`)
are session-scoped fixtures; add yours the same way.

**Where to drop the recipe:** `tests/conftest.py` (or any pytest
plugin / conftest in your test tree).

```python
import pytest
from mcp_test_framework.rubrics import Rubric


class SafetyRubric(Rubric):
    """Does the description name destructive side effects (writes, deletes, network calls)?"""
    dimension: str = "safety"
    dimension_criteria: str = (
        "Does the description clearly identify any destructive side effects "
        "the tool may have (writes, deletes, external network calls)? "
        "If the tool is read-only, does it say so?"
    )


@pytest.fixture(scope="session")
def rubric_safety() -> SafetyRubric:
    return SafetyRubric()


@pytest.mark.asyncio(loop_scope="session")
async def test_description_safety(judge, target_tool, rubric_safety):
    result = await judge.judge(
        rubric=str(rubric_safety),
        subject=target_tool.description,
    )
    assert result.passed, f"safety judge failed: {result.reasoning}\nraw: {result.raw_response}"
```

The framework's `_HARDENING_PREAMBLE` and `_SCORE_ANCHOR_TEMPLATE` (defined in
`rubrics.py`) wrap your `dimension_criteria` automatically via
`Rubric.__str__`, so the judge sees a uniform prompt shape across all
rubrics. Pass threshold is `score >= 4` on the 1-5 scale.

## Swap the judge backend

The `Judge` Protocol (`src/mcp_test_framework/judge_protocol.py`) is the seam
for swapping the LLM judge. Implement a class with the matching async
signature, then override the framework's `judge` fixture in your own
conftest. The framework's tests will use your judge transparently.

**Note on `runtime_checkable`:** the Protocol is `runtime_checkable`, but
`isinstance(x, Judge)` only checks attribute presence -- NOT signature
shape. If you stray from
`async def judge(self, rubric, subject, context=None) -> JudgeResult`, your
tests will fail at call time, not at registration. Match the signature
exactly.

```python
from typing import Any

import pytest_asyncio
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.ollama_judge import JudgeResult


class OpenAIJudge:
    """Example: an OpenAI-compatible-endpoint judge satisfying the `Judge` Protocol."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        # ... wire your HTTP client here ...

    async def judge(
        self,
        rubric: str,
        subject: str,
        context: dict[str, Any] | None = None,
    ) -> JudgeResult:
        # ... call your backend, parse the response into a JudgeResult ...
        return JudgeResult(
            passed=True,
            score=4,
            reasoning="example",
            raw_response="{}",
        )


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def judge() -> Judge:  # overrides framework fixture by name
    return OpenAIJudge(api_key="...", model="...")
```

Pytest's fixture resolution picks up the most specific fixture, so an
override in your `tests/conftest.py` shadows the framework's session-scoped
`judge` fixture (`src/mcp_test_framework/fixtures.py`). All Category 2 tests
(`test_description_clarity`, `test_description_disambiguation`,
`test_parameters_are_self_explanatory`) consume `judge` by name and will
route to your implementation. Do not commit real API keys -- load secrets
from your environment or a secret manager inside `__init__`.

## Add a new MCP tool target

The per-tool config registry (`tools.<tool_name>:` blocks in your config YAML)
is the lightest-weight way to extend coverage: zero code changes. The schema is
`ToolConfig` (`src/mcp_test_framework/models.py`); see
[Per-tool configuration](../README.md#per-tool-configuration) in the README for
the field reference. This section walks the workflow.

**Where to drop the recipe:** `config.yaml` (or whichever YAML overlay your `--config` flag points at). No edits to `tests/conftest.py` or framework source are required.

1. **Discover.** Run `uv run mcp-contracts list-tools --config config.yaml` to see every tool the connected server advertises.
2. **Decide.** For each tool, decide whether to `skip`, restrict the `judges` subset, or pre-fill `call_arguments`. Tools you say nothing about run with all rubrics and an empty argument map (the safe defaults).
3. **Add a `tools.<tool_name>:` block** under the top-level `tools:` key in your config YAML. See [Per-tool configuration](../README.md#per-tool-configuration) for the field reference; the worked example below uses the skip-with-reason pattern.
4. **Verify.** Re-run `uv run mcp-contracts run --config config.yaml`. The per-tool summary printed at the end of the session shows `<tool_name>: PASS|FAIL|SKIP -- <reason>` so you can confirm the new entry took effect.

Replace the placeholder tool name below with one from your `mcp-contracts list-tools` output.

```yaml
# config.yaml -- per-tool config overlay
tools:
  <your_destructive_tool>:
    skip: true
    skip_reason: "Tool performs writes against real hosts; opted out for CI."
```

For the judges-subset pattern (`judges: [clarity]`), see [Block B in the README](../README.md#block-b-judges-subset).

At test-collection time, the `tool_config` fixture
(`src/mcp_test_framework/fixtures.py`) resolves
`config.tools.get(target_tool.name, ToolConfig())` for the active tool. Tools
without an entry receive a default `ToolConfig()` (no skip, no fixed
arguments, all rubrics). Typos in field names are caught at config load by
`extra="forbid"`, so a misspelled `srtip:` does not silently disable the safety
of an explicit `skip: true`.

## Environment passthrough allowlist

The framework spawns the MCP server subprocess with a deliberately narrow
environment. By default `mcp.client.stdio.stdio_client` would inherit the full
parent shell -- your real `~/.homelab_mcp/` registry, OS keyring credentials,
AWS keys, `GITHUB_TOKEN`, and similar -- into the subprocess under test. That
violates the "test runs do not mutate user state" guarantee documented in the
README's [Isolation guarantee](../README.md#isolation-guarantee) section.

Instead, `src/mcp_test_framework/_isolation.py` ships a module-level
`_PASSTHROUGH_ALLOWLIST` of exactly five entries:

- `PATH` -- binary lookup for the MCP server command itself
- `SYSTEMROOT` -- Windows DLL resolution; without it, Python interpreters in
  the spawned subprocess fail to import stdlib modules
- `LANG` -- locale resolution for non-English server output
- `USERNAME` -- informational; some servers log it for diagnostics
- `MCP_*` (prefix match) -- pass-through for framework-set MCP env vars
  (e.g. `MCP_CONNECTION_NONBLOCKING`)

Plus five always-overridden vars (`HOME`, `USERPROFILE`, `TEMP`, `TMP`,
`TMPDIR`) that point at a per-session tempdir, and one keyring null-backend
override (`PYTHON_KEYRING_BACKEND=keyring.backends.null.Null`) that
short-circuits the Python `keyring` library so subprocess credential lookups
become no-ops.

### Do not widen this allowlist without justification

This is the warning living at the top of
`src/mcp_test_framework/_isolation.py`, copied verbatim so contributors
see it before reading source:

> DO NOT widen `_PASSTHROUGH_ALLOWLIST` without updating `EXTENDING.md`
> Each new pass-through is a hole in the isolation
> guarantee and must be justified by a real subprocess need (e.g., locale
> resolution for a non-English server) -- not "the test wouldn't run
> otherwise" without a root cause.

If you find yourself wanting to add an entry to `_PASSTHROUGH_ALLOWLIST`, the
right workflow is:

1. **Identify the real need.** What does the spawned MCP server fail to do
   without the var? Capture a reproducer (`uv run mcp-contracts run -v`
   with the var stripped vs. present).
2. **Try the override path first.** Most "I need X env var" cases are
   actually "I need a redirected `HOME`" -- see the existing `_HOME_OVERRIDES`
   tuple, which already covers `HOME` / `USERPROFILE` / `TEMP` / `TMP` /
   `TMPDIR`.
3. **If pass-through is genuinely required**, propose the change with a
   CONTEXT-style decision record explaining: (a) which subprocess behaviour
   requires it, (b) what threat surface it widens, (c) whether the var ever
   carries secrets (e.g. `AWS_PROFILE` does in some shells, `GITHUB_TOKEN`
   always does). Update this section's allowlist enumeration in the same PR.

### Why POSIX `USER` is NOT in the allowlist

A natural question reading the list above: on Windows the framework passes
`USERNAME` through, but on POSIX (Linux / macOS), `getpass.getuser()`
consults the `USER` env var and `USERNAME` is rarely set. The spawned
subprocess on POSIX therefore sees no user identity at all.

This is intentional and not a bug:

- The current allowlist names exactly `USERNAME`. The
  HOME redirect -- which IS the load-bearing isolation guarantee -- does
  not depend on user identity (it is driven by `HOME` / `USERPROFILE` /
  `TEMP` / `TMP` / `TMPDIR`, none of which the subprocess derives from a
  username).
- `USERNAME` is documented in `_isolation.py` as "informational; some
  servers log it for diagnostics." It is not consulted by any v1.1 code
  path that affects test outcome, and the rubric/judge layer never sees it.
- Widening `_PASSTHROUGH_ALLOWLIST` to include POSIX `USER` would require
  a code change, not just a doc edit. The cross-platform-parity concern is
  documented as informational; the agreed disposition is rationale-only —
  no `USER` is added to `_PASSTHROUGH_ALLOWLIST`, and the parity gap stays
  documented in this section.

If a future MCP server target genuinely needs `USER` for non-diagnostic
reasons (e.g. a server that derives a config path from
`getpass.getuser()`), follow the "Do not widen this allowlist without
justification" workflow above -- the absence of `USER` from
`_PASSTHROUGH_ALLOWLIST` is a deliberate floor, not a forgotten ceiling.

## Further reading

- [`README.md`](../README.md) -- back to setup and usage
- `src/mcp_test_framework/rubrics.py` -- built-in rubric examples
- `src/mcp_test_framework/judge_protocol.py` -- Protocol definition + `JudgeResult` shape
- [`Per-tool configuration`](../README.md#per-tool-configuration) -- README schema reference for the `tools.<name>:` registry
- [`config.example.yaml`](../config.example.yaml) -- complete real-server per-tool config reference
- [`Environment passthrough allowlist`](#environment-passthrough-allowlist) -- what the spawned MCP subprocess inherits, and why widening the list is dangerous
