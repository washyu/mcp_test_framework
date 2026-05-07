---
quick_id: 260507-j6i
slug: enrich-mcp-server-not-on-path-error-with
date: 2026-05-07
type: quick
files_modified:
  - tests/conftest.py
  - src/mcp_test_framework/fixtures.py
---

<objective>
Enrich the cryptic `FileNotFoundError: MCP server command not on PATH: 'X'` so a user running pytest without a `config.yaml` gets a clear, actionable hint pointing at `MCPTF_CONFIG_FILE` and `config.example.yaml`. Currently this surfaces as a wall of pytest internals; the user has no idea their config wasn't loaded.

Two test-side call sites raise this error indirectly:

1. `tests/conftest.py:_resolve_tool_names` — the discovery hook's `except Exception as exc:` block calls `pytest.exit(f"Tool discovery via {config.mcp_server.command!r} failed: {exc.__class__.__name__}: {exc}", returncode=2)`. When `exc` is `FileNotFoundError` from `McpTestClient.__aenter__`, append the hint.
2. `src/mcp_test_framework/fixtures.py:_preflight` — has the same MCP spawn that can hit the same `FileNotFoundError`. Apply the same hint pattern.

DO NOT modify `src/mcp_test_framework/mcp_client.py`. The production client stays clean of test-ergonomics concerns; the hint is a test-runner UX layer.

DO NOT refactor config loading or add a CLI doctor command. Larger config-shape questions (YAML required + env-as-override + skip-list home) are deferred to Phase 08.
</objective>

<context>
@CLAUDE.md
@tests/conftest.py
@src/mcp_test_framework/fixtures.py
@src/mcp_test_framework/mcp_client.py
@.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-01-multi-tool-discovery-PLAN.md
@config.example.yaml

<interfaces>
The error origin (production code, do NOT modify):

From `src/mcp_test_framework/mcp_client.py:__aenter__` (around line 144):
```python
raise FileNotFoundError(
    f"MCP server command not on PATH: {self._command!r}"
)
```

The current discovery hook failure path in `tests/conftest.py:_resolve_tool_names` (around line 99):
```python
try:
    _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
except Exception as exc:  # noqa: BLE001
    pytest.exit(
        f"Tool discovery via {config.mcp_server.command!r} failed: "
        f"{exc.__class__.__name__}: {exc}",
        returncode=2,
    )
```

The current `_preflight` body in `src/mcp_test_framework/fixtures.py` (lines ~86-170) does its own MCP spawn via `McpTestClient(...)` and can raise the same `FileNotFoundError`. There may already be an `except` wrapper there or the error may bubble — read the current state and adapt.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add a shared `_command_not_on_path_hint` helper + enrich both error paths</name>
  <files>
    - tests/conftest.py
    - src/mcp_test_framework/fixtures.py
  </files>
  <read_first>
    - tests/conftest.py (full)
    - src/mcp_test_framework/fixtures.py (lines 1-200, including any existing pytest.exit / preflight try/except wrappers)
    - src/mcp_test_framework/mcp_client.py (lines 130-160, confirm exact FileNotFoundError shape)
    - config.example.yaml (one line — confirm filename for the hint message)
  </read_first>
  <action>
**Detection logic:** Use `isinstance(exc, FileNotFoundError)` AND check that the error message starts with `"MCP server command not on PATH:"`. The `isinstance` check is the primary guard; the substring check disambiguates from unrelated `FileNotFoundError`s (e.g. from a missing config file later in the chain).

**Hint message** (use this verbatim, formatted as a multi-line string with leading newline so it appends cleanly under the existing "Tool discovery via 'X' failed: ..." line):

```
\n\nHint: '{cmd}' was not found on PATH. If you intended to use a different command, point MCPTF_CONFIG_FILE at a config.yaml that defines mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). The repo ships `config.example.yaml` you can copy and edit.
```

Where `{cmd}` is `config.mcp_server.command` (or the equivalent in `_preflight`).

**Edit 1: `tests/conftest.py`**

In the `_resolve_tool_names` function's existing `except Exception as exc:` block (around lines 99-104), enrich the `pytest.exit` message conditionally:

OLD:
```python
        try:
            _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
        except Exception as exc:  # noqa: BLE001 -- mirrors _preflight failure-mode parity
            # Match _preflight failure shape (fixtures.py:149-154) for exit-code parity.
            # See 07-RESEARCH §Pitfall 5.
            pytest.exit(
                f"Tool discovery via {config.mcp_server.command!r} failed: "
                f"{exc.__class__.__name__}: {exc}",
                returncode=2,
            )
```

NEW:
```python
        try:
            _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
        except Exception as exc:  # noqa: BLE001 -- mirrors _preflight failure-mode parity
            # Match _preflight failure shape (fixtures.py:149-154) for exit-code parity.
            # See 07-RESEARCH §Pitfall 5.
            msg = (
                f"Tool discovery via {config.mcp_server.command!r} failed: "
                f"{exc.__class__.__name__}: {exc}"
            )
            if isinstance(exc, FileNotFoundError) and str(exc).startswith(
                "MCP server command not on PATH:"
            ):
                msg += (
                    f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
                    "If you intended to use a different command, point "
                    "MCPTF_CONFIG_FILE at a config.yaml that defines "
                    "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
                    "The repo ships `config.example.yaml` you can copy and edit."
                )
            pytest.exit(msg, returncode=2)
```

**Edit 2: `src/mcp_test_framework/fixtures.py`**

Read the current `_preflight` body to understand how it invokes `McpTestClient` and where the `FileNotFoundError` would surface. Two cases to handle:

(a) If `_preflight` already wraps the spawn in a `try/except` and calls `pytest.exit(...)`: enrich that existing message the same way as Edit 1 above (substitute `config.mcp_server.command` for the `{cmd}` placeholder).

(b) If `_preflight` lets the error bubble (i.e. no current `try/except` around the `McpTestClient` enter): add a minimal try/except around just the `async with McpTestClient(...) as client:` block — preserve all assertions inside the body — and emit the same enriched `pytest.exit` message. Do NOT swallow other exceptions; only intercept the specific spawn-not-found case and re-raise everything else (so existing failure modes still propagate as today).

The hint text and detection logic must be identical to Edit 1 (so users see the same message regardless of which spawn site fails first).

**Anti-duplication:** Do NOT extract a helper into `mcp_client.py` or a new module — that would couple production code to test ergonomics. Either:
- Inline the same string in both files (simplest; ~5 lines duplicated; acceptable for a 2-site quick fix), OR
- Define a private helper `_format_command_not_on_path_hint(cmd: str) -> str` at module-top in `tests/conftest.py` and import it from `fixtures.py` — but only if `fixtures.py` already imports from `tests/`. Most likely it does NOT (production code shouldn't depend on tests/), so default to inline duplication. Add a brief one-line comment at each site referencing the other so future readers know to keep them in sync: `# keep in sync with src/mcp_test_framework/fixtures.py:_preflight (or vice versa)`.
  </action>
  <verify>
    <automated>uv run pytest --collect-only -q tests/test_mcp_tool_contract.py 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "MCPTF_CONFIG_FILE" tests/conftest.py` returns at least 1
    - `grep -c "MCPTF_CONFIG_FILE" src/mcp_test_framework/fixtures.py` returns at least 1
    - `grep -c "config.example.yaml" tests/conftest.py` returns at least 1
    - `grep -c "config.example.yaml" src/mcp_test_framework/fixtures.py` returns at least 1
    - `grep -c "isinstance(exc, FileNotFoundError)" tests/conftest.py` returns 1
    - `grep -c "MCP server command not on PATH:" tests/conftest.py` returns 1 (the substring guard)
    - `grep -c "MCP server command not on PATH:" src/mcp_test_framework/fixtures.py` returns 1 (the substring guard) — only if Edit 2 path (b) was taken; if path (a) and an existing wrapper had a different guard, document the deviation in SUMMARY.md
    - `uv run python -c "import tests.conftest"` runs without error
    - `uv run python -c "from mcp_test_framework.fixtures import _preflight"` runs without error
    - `uv run pytest tests/unit/ -q` passes (56/56 from prior baseline)
    - `uv run ruff check src tests` returns 0 errors on Phase 07 surface (pre-existing rubrics.py I001 stays deferred)
    - **Live trigger** (manual confirmation, on the worktree where homelab-mcp is NOT on PATH and no config.yaml is configured): `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py` exits non-zero AND the output contains the substring `MCPTF_CONFIG_FILE`
    - **False-positive guard:** the hint must NOT appear when discovery fails for a non-spawn reason. To validate, simulate by editing the config to point at a real but error-emitting binary (e.g. a script that prints to stderr and exits non-zero). Confirm the `MCPTF_CONFIG_FILE` hint substring is absent. (If this is impractical to set up, document the assertion as code-review-only and mark this acceptance criterion `manual-deferred`.)
  </acceptance_criteria>
  <done>
    - Both call sites enriched with consistent hint pointing at `MCPTF_CONFIG_FILE` and `config.example.yaml`
    - Hint only appears for `FileNotFoundError` with the `"MCP server command not on PATH:"` prefix — not for unrelated discovery failures
    - `mcp_client.py` is untouched
    - `tests/unit/` still 56/56; ruff still clean on Phase 07 surface
    - Live trigger reproduced and the new hint visible in the exit message
  </done>
</task>

</tasks>

<success_criteria>

Quick task complete when:

- [ ] `tests/conftest.py:_resolve_tool_names` `except` block emits the `MCPTF_CONFIG_FILE` hint when `exc` is `FileNotFoundError` with the production-client prefix
- [ ] `src/mcp_test_framework/fixtures.py:_preflight` emits the same hint at its spawn site
- [ ] Hint message references `config.example.yaml` and an example `command: uvx, args: [homelab-mcp]`
- [ ] `mcp_client.py` is unchanged
- [ ] Hint is conditional — non-spawn-not-found errors get the original message only
- [ ] `uv run pytest tests/unit/ -q` passes
- [ ] `uv run ruff check src tests` clean on Phase 07 surface
- [ ] Live trigger confirms the hint appears in the user-facing pytest exit output
- [ ] Single atomic commit on `claude/sweet-black-074ea5`

</success_criteria>

<output>

After completion, create `.planning/quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/SUMMARY.md` with:

- **status**: complete (or incomplete with reason)
- **affects**: `tests/conftest.py`, `src/mcp_test_framework/fixtures.py`
- **provides**: Actionable error hint pointing at `MCPTF_CONFIG_FILE` / `config.yaml` setup when the MCP server command is not on PATH
- **patterns**: Test-side error enrichment via `isinstance` + substring guard; inline hint duplication across two test-side call sites with cross-references; deliberate decision to NOT pollute production `mcp_client.py` with test ergonomics
- **gotchas**: Hint must be conditional on the specific `FileNotFoundError` shape — unrelated discovery failures (server starts but errors, JSON parse failures, etc.) must NOT see the misleading config-yaml hint
- **deferred**: Larger config-shape question (YAML required + env-as-override + skip-list home) deferred to Phase 08

</output>
