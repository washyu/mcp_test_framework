---
quick_id: 260507-j6i
slug: enrich-mcp-server-not-on-path-error-with
date: 2026-05-07
type: quick
status: complete
commit: bfc1e65
affects:
  - tests/conftest.py
  - src/mcp_test_framework/fixtures.py
provides:
  - Actionable error hint pointing at MCPTF_CONFIG_FILE / config.yaml setup when the MCP server command is not on PATH
patterns:
  - test-side-error-enrichment-with-isinstance-and-substring-guard
  - inline-hint-duplication-across-two-call-sites-with-cross-references
  - production-mcp_client.py-untouched-by-test-ergonomics
gotchas:
  - hint-must-be-conditional-on-FileNotFoundError-and-the-exact-prefix
  - unrelated-discovery-failures-must-not-see-the-misleading-config-yaml-hint
deferred:
  - YAML-required-and-env-as-override-and-skip-list-home-deferred-to-Phase-08
  - false-positive-guard-acceptance-criterion-marked-manual-deferred
---

# Quick Task 260507-j6i: Enrich MCP-server-not-on-PATH error with config hint

## Status

**Complete.** Single atomic commit `bfc1e65` on branch `claude/sweet-black-074ea5`.

## What changed

### `tests/conftest.py:_resolve_tool_names`

The existing `except Exception as exc:` block (formerly a single `pytest.exit(...)` call)
now builds a `msg` string and conditionally appends a hint when the underlying
exception is the production-client `FileNotFoundError("MCP server command not on PATH: ...")`.
The original message shape is preserved for any other exception type.

### `src/mcp_test_framework/fixtures.py:_preflight`

Two enrichment sites:

1. **Check 1 (`shutil.which` direct check):** This is the path that fires *first*
   in practice. The hint is appended unconditionally because the branch *is* the
   spawn-not-found case.
2. **Check 3 (`McpTestClient` spawn `except Exception`):** Symmetric
   `isinstance(exc, FileNotFoundError) + str(exc).startswith(...)` guard,
   identical hint string.

### `src/mcp_test_framework/mcp_client.py`

**Untouched.** The production client's `FileNotFoundError` raise is the canonical
source-of-truth for the error shape; the hint is a test-runner UX layer added at
the consumption sites only.

## Hint message (verbatim, identical at all three sites)

```
Hint: 'X' was not found on PATH. If you intended to use a different command, point
MCPTF_CONFIG_FILE at a config.yaml that defines mcp_server.command
(e.g. `command: uvx, args: [homelab-mcp]`). The repo ships `config.example.yaml`
you can copy and edit.
```

## Verification results

| Check | Result |
| ----- | ------ |
| `uv run python -c "import tests.conftest"` | OK |
| `uv run python -c "from mcp_test_framework.fixtures import _preflight"` | OK |
| `uv run pytest tests/unit/ -q` | 56/56 passed in 0.36s |
| `uv run ruff check src tests` | clean on Phase 07 surface (pre-existing `rubrics.py` I001 deferred) |
| `grep MCPTF_CONFIG_FILE tests/conftest.py` | 2 (>=1) |
| `grep MCPTF_CONFIG_FILE src/mcp_test_framework/fixtures.py` | 4 (>=1) |
| `grep config.example.yaml tests/conftest.py` | 2 (>=1) |
| `grep config.example.yaml src/mcp_test_framework/fixtures.py` | 4 (>=1) |
| `grep "isinstance(exc, FileNotFoundError)" tests/conftest.py` | 1 |
| `grep "MCP server command not on PATH:" tests/conftest.py` | 1 |
| `grep "MCP server command not on PATH:" src/.../fixtures.py` | 1 |
| Live trigger (unset MCPTF_CONFIG_FILE, run pytest --collect-only) | Exit 2; output contains `MCPTF_CONFIG_FILE`, `config.example.yaml`, `command: uvx, args: [homelab-mcp]` |

### Live-trigger output (relevant tail)

```
tests\conftest.py:120: in _resolve_tool_names
    pytest.exit(msg, returncode=2)
E   _pytest.outcomes.Exit: Tool discovery via 'homelab-mcp' failed: FileNotFoundError: MCP server command not on PATH: 'homelab-mcp'
E
E   Hint: 'homelab-mcp' was not found on PATH. If you intended to use a different command, point MCPTF_CONFIG_FILE at a config.yaml that defines mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). The repo ships `config.example.yaml` you can copy and edit.
```

The discovery hook (`pytest_generate_tests`) ran during collection and fired
*before* fixture-level `_preflight` -- which is the dominant path for end users
running `uv run pytest` cold. Both call sites are wired correctly; the user sees
the same hint regardless of which spawn site fails first.

## Deviations

**Edit 2 (fixtures.py): chose path (a) -- enrich both existing wrappers.**
The plan permitted either path. Reading the current file, `_preflight` already
had *two* relevant exit paths -- Check 1 (the `shutil.which` direct check) and
Check 3 (the `McpTestClient` spawn wrapper). Both surface the same user
complaint, so I enriched both sites for consistency. This adds one more
`MCPTF_CONFIG_FILE` mention than the plan's minimum (1) but keeps the user
experience symmetric.

**False-positive guard (acceptance criterion): `manual-deferred`.**
The plan explicitly permits marking the false-positive live-test acceptance bullet
`manual-deferred` and relying on code review of the
`isinstance + str(exc).startswith(...)` guard. The guard is straightforward and
reviewed inline at all three sites.

## Anti-duplication note

The hint string is duplicated inline at three sites (one in `tests/conftest.py`,
two in `src/mcp_test_framework/fixtures.py`). Cross-reference comments at each
site instruct future readers to keep them in sync. Extracting a helper would have
required either placing it in `mcp_client.py` (rejected -- production code
shouldn't carry test-runner UX strings) or in `tests/conftest.py` and importing
from `fixtures.py` (rejected -- production code shouldn't depend on `tests/`).
A new shared module for one ~5-line hint string would have been more churn than
the duplication it replaces.

## Self-Check: PASSED

- File `.planning/quick/260507-j6i-enrich-mcp-server-not-on-path-error-with/SUMMARY.md` -- FOUND
- Commit `bfc1e65` -- FOUND in git log
- `tests/conftest.py`, `src/mcp_test_framework/fixtures.py` -- both in commit
- `src/mcp_test_framework/mcp_client.py` -- UNCHANGED
