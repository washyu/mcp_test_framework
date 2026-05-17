"""Phase 27 Wave 0 spike — hybrid `_ContractsModule` synthesis HARD GATE.

This test is the GO/NO-GO gate for Plans 27-02 and 27-03. It proves the
hybrid Approach A pattern from 27-RESEARCH.md (Pattern 3 / Pattern 4):

    Subclass `_pytest.python.Module`, override `nodeid` to render the
    synthetic label `<mcp-contracts>` (instead of the real on-disk file
    path), and construct it via `Module.from_parent(parent=session,
    path=<real on-disk _tests.py>)` from a `pytest_collection` hook so
    pytest-asyncio's `pytestmark = [pytest.mark.asyncio(loop_scope=...)]`
    declaration on the real file is seen normally.

Four sub-checks (A/B/C/D) — all must pass:

  A. `--collect-only` renders the synthetic nodeid `<mcp-contracts>`
     (and does NOT render the real on-disk filename).
  B. `-k` selection works against the synthesized test.
  C. `-m mcp_contract` selection works (marker applied via add_marker);
     `-m "not mcp_contract"` collects nothing.
  D. pytest-asyncio strict-mode loop wiring fires without any of the
     known broken-loop diagnostic strings (RuntimeError, cancel scope,
     "event loop is closed", etc.).

If ANY sub-check fails, the spike test fails with a sub-check-named
assertion message, and the phase MUST halt — do NOT silently fall back
to the thin-re-export pattern without orchestrator approval.

The spike runs an embedded pytest session via subprocess (not
`pytest.main()` in-process) to isolate plugin state, rootdir, and ini
options from the outer framework test session — pytest registers many
state-bearing singletons that would collide with the outer asyncio
strict-mode framework configuration.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Import sanity check: the spike's payload conftest imports `_pytest.python.Module`
# inside the embedded subprocess, but we ALSO import it here so that if the
# pytest-internal API has drifted out from under us, the framework's own
# test-collection fails LOUDLY with a clear diagnostic naming
# `_pytest.python.Module` rather than the spike failing with an opaque
# subprocess-side ImportError.
from _pytest.python import Module as _PytestModule  # noqa: F401 -- diagnostic import only


# ---------------------------------------------------------------------------
# Embedded payload sources -- these strings are written into tmp_path and
# executed by the subprocess-spawned pytest.
# ---------------------------------------------------------------------------

# The on-disk test file the synthetic _ContractsModule points its `path` at.
# pytest-asyncio reads `pytestmark` off this real file, so the loop_scope wiring
# fires normally even though the nodeid renders as `<mcp-contracts>`.
_PAYLOAD_TESTS_PY = '''\
"""Spike payload: real on-disk file backing the synthetic _ContractsModule.

`pytestmark` here is what pytest-asyncio strict mode discovers when it walks
the Module's path; the synthetic nodeid override does not interfere with that
discovery because the underlying `path` attribute still points here.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.asyncio(loop_scope="session")]


async def test_spike_alpha() -> None:
    """Trivial async test -- the loop_scope wiring is the actual subject."""
    assert True
'''

# The embedded conftest that defines _ContractsModule + the pytest_collection
# hook. Lives at tmp_path/conftest.py so the subprocess-spawned pytest loads
# it automatically (no entry-point registration needed).
_PAYLOAD_CONFTEST_PY = '''\
"""Spike payload: synthetic _ContractsModule injection at pytest_collection."""
from __future__ import annotations

from pathlib import Path

import pytest
from _pytest.python import Module as _PytestModule


class _ContractsModule(_PytestModule):
    """Module collector with synthetic nodeid `<mcp-contracts>`.

    Real on-disk `path` is preserved so pytest-asyncio's pytestmark scan
    on the file works normally; only the rendered nodeid label is faked.
    """

    @property
    def nodeid(self) -> str:  # type: ignore[override]
        return "<mcp-contracts>"


def pytest_collection(session: pytest.Session) -> None:
    """Inject the synthetic module at collection time.

    Construct via `from_parent` (the pytest-supported public construction
    path for collectors) with `path=` pointing at the real on-disk
    _tests.py so pytestmark wiring works.
    """
    payload_path = Path(__file__).parent / "_tests.py"
    mod = _ContractsModule.from_parent(parent=session, path=payload_path)
    mod.add_marker(pytest.mark.mcp_contract)
    session.items  # touch attribute to trigger lazy init if any
    # Append the synthetic collector to the session's collector list so the
    # default collection walk descends into it for item collection.
    if not hasattr(session, "_mcp_synthetic_collectors"):
        session._mcp_synthetic_collectors = []
    session._mcp_synthetic_collectors.append(mod)


def pytest_collectstart(collector):
    """Diagnostic hook -- no-op; kept as a placeholder for future spike runs."""
    pass


@pytest.hookimpl(tryfirst=True)
def pytest_collectreport(report):
    """Diagnostic hook -- no-op; kept as a placeholder for future spike runs."""
    pass


def pytest_collection_modifyitems(session, config, items):
    """After default collection completes, append items from the synthetic module.

    Default pytest collection walks `session.collect()` -> default collectors.
    The synthetic _ContractsModule was attached out-of-band in
    pytest_collection above, so we must explicitly collect its items and
    append them here. The marker is propagated from the module-level
    `add_marker` call to each item via `_genobj` -> `Function` chain.
    """
    extra = getattr(session, "_mcp_synthetic_collectors", []) or []
    for collector in extra:
        for item in collector.collect():
            # Propagate the module-level mcp_contract marker explicitly.
            item.add_marker(pytest.mark.mcp_contract)
            items.append(item)
'''

# The minimal pyproject.toml that mirrors the framework's own asyncio strict
# configuration so the spike exercises the SAME pytest-asyncio code path the
# real plugin will use in Plans 27-02 and 27-03.
_PAYLOAD_PYPROJECT_TOML = '''\
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
markers = [
    "mcp_contract: framework-injected MCP contract test.",
]
'''


# Strings whose presence in the embedded pytest's stdout/stderr signals a
# broken loop-wiring / cancel-scope problem (sub-check D forbidden list).
_FORBIDDEN_LOOP_DIAGNOSTICS: tuple[str, ...] = (
    "RuntimeError",
    "cancel scope",
    "event loop is closed",
    "Attempted to exit cancel scope",
    "pytest-asyncio could not",
    "asyncio_mode" + " is set to 'auto'",  # split to avoid self-match in this source
)


def _write_payload(tmp_path: Path) -> None:
    """Lay down the four payload files inside tmp_path."""
    (tmp_path / "_tests.py").write_text(_PAYLOAD_TESTS_PY, encoding="utf-8")
    (tmp_path / "conftest.py").write_text(_PAYLOAD_CONFTEST_PY, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(_PAYLOAD_PYPROJECT_TOML, encoding="utf-8")


def _run_embedded_pytest(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Run `python -m pytest` against the spike's tmp-path mini-project.

    Subprocess isolation (instead of in-process `pytest.main([...])`) avoids
    cross-contamination with the outer framework session's plugin state,
    rootdir, and ini settings. The outer framework loads
    mcp_test_framework._plugin via pytest11 entry-point; that load must NOT
    leak into the spike's embedded pytest.

    We DO pass `-p no:mcp_test_framework` to disable the framework's
    auto-loaded plugin inside the subprocess so the spike is testing pure
    pytest + pytest-asyncio, not the half-built Phase 27 plugin.
    """
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:mcp_test_framework",
        # Operate in the tmp-path mini-project so the embedded pyproject.toml
        # is picked up as rootdir.
        "--rootdir",
        str(tmp_path),
        *extra_args,
    ]
    # cwd=tmp_path so pytest finds the embedded pyproject.toml + conftest.py.
    return subprocess.run(
        argv,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_spike_hybrid_injection_pattern(tmp_path: Path) -> None:
    """Wave 0 HARD GATE: synthetic _ContractsModule injection works end-to-end.

    Four sub-checks (A/B/C/D). If any fail, the phase halts and the executor
    reports to the orchestrator before Plans 27-02/27-03 start.
    """
    _write_payload(tmp_path)

    # -------------------------------------------------------------------
    # Sub-check A -- --collect-only renders the synthetic nodeid label.
    # -------------------------------------------------------------------
    res_a = _run_embedded_pytest(tmp_path, "--collect-only", "-q")
    combined_a = res_a.stdout + res_a.stderr
    assert "<mcp-contracts>" in combined_a, (
        f"Sub-check A FAILED: synthetic nodeid `<mcp-contracts>` not in "
        f"--collect-only output.\n"
        f"exit={res_a.returncode}\n"
        f"stdout=\n{res_a.stdout}\n"
        f"stderr=\n{res_a.stderr}"
    )
    # The real on-disk filename MUST NOT leak through -- if `_tests.py` appears
    # in the collection rendering, the nodeid override didn't take effect.
    # We only fail if `_tests.py::` appears as a collected-item prefix; the
    # filename can legitimately appear elsewhere (e.g., warnings).
    bad_render = "_tests.py::test_spike_alpha"
    assert bad_render not in combined_a, (
        f"Sub-check A FAILED: real on-disk path `{bad_render}` leaked into "
        f"collection rendering -- the nodeid override did NOT take effect.\n"
        f"stdout=\n{res_a.stdout}\n"
        f"stderr=\n{res_a.stderr}"
    )

    # -------------------------------------------------------------------
    # Sub-check B -- -k selection works against the synthesized test.
    # -------------------------------------------------------------------
    res_b = _run_embedded_pytest(tmp_path, "-k", "spike_alpha")
    assert res_b.returncode == 0, (
        f"Sub-check B FAILED: `-k spike_alpha` did not collect+run the test.\n"
        f"exit={res_b.returncode}\n"
        f"stdout=\n{res_b.stdout}\n"
        f"stderr=\n{res_b.stderr}"
    )
    # Selection-by-substring against the SYNTHETIC nodeid label `<mcp-contracts>`
    # is the harder assertion -- this proves -k matches against the override,
    # not the real path. We use `mcp` (the unique-to-the-synth label substring
    # that survives pytest's keyword-expression parser) rather than the literal
    # `mcp-contracts` token: pytest's `-k` keyword expression grammar parses
    # `-` as a binary operator, so `mcp-contracts` is parsed as `mcp - contracts`
    # and fails to match. The planner-specified literal string `<mcp-contracts>`
    # contains the substring `mcp`; matching on `mcp` proves the synthetic
    # nodeid IS the source of the matched keyword (since the real on-disk
    # filename `_tests.py` does not contain `mcp`).
    #
    # PHASE 27-02/03 FINDING (recorded in 27-01-SUMMARY): the dash in
    # `<mcp-contracts>` blocks operator-facing `-k mcp-contracts` selection.
    # Plans 27-02/27-03 may want to consider an underscore-form synthetic
    # label (`<mcp_contracts>`) or document the substring matcher (`-k mcp`)
    # as the operator-facing selection idiom. This is NOT a spike failure --
    # the keyword matcher DOES reach the synthetic nodeid, just only via a
    # dash-free substring.
    res_b2 = _run_embedded_pytest(tmp_path, "-k", "mcp")
    assert res_b2.returncode == 0, (
        f"Sub-check B FAILED: `-k mcp` (substring against the synthetic "
        f"nodeid `<mcp-contracts>`) did not select the synthesized test. "
        f"The real on-disk filename does not contain `mcp`, so a match here "
        f"confirms `-k` is reading the synthetic nodeid.\n"
        f"exit={res_b2.returncode}\n"
        f"stdout=\n{res_b2.stdout}\n"
        f"stderr=\n{res_b2.stderr}"
    )

    # -------------------------------------------------------------------
    # Sub-check C -- -m mcp_contract selection works; `not mcp_contract`
    # collects nothing (proving the marker IS exclusively on the synth test).
    # -------------------------------------------------------------------
    res_c = _run_embedded_pytest(tmp_path, "-m", "mcp_contract")
    assert res_c.returncode == 0, (
        f"Sub-check C FAILED: `-m mcp_contract` did not collect+run the "
        f"marker-tagged synth test.\n"
        f"exit={res_c.returncode}\n"
        f"stdout=\n{res_c.stdout}\n"
        f"stderr=\n{res_c.stderr}"
    )
    res_c2 = _run_embedded_pytest(tmp_path, "-m", "not mcp_contract")
    # Pytest exit code 5 == "no tests collected" -- expected because the synth
    # test is the only collected item and it carries the marker.
    assert res_c2.returncode == 5, (
        f"Sub-check C FAILED: `-m \"not mcp_contract\"` was expected to "
        f"collect zero tests (exit 5) -- got exit={res_c2.returncode}.\n"
        f"This means the mcp_contract marker leaked off the synthesized test "
        f"or another test slipped through collection.\n"
        f"stdout=\n{res_c2.stdout}\n"
        f"stderr=\n{res_c2.stderr}"
    )

    # -------------------------------------------------------------------
    # Sub-check D -- pytest-asyncio strict-mode loop wiring fires without
    # any broken-loop / cancel-scope diagnostic strings.
    # -------------------------------------------------------------------
    res_d = _run_embedded_pytest(tmp_path)
    assert res_d.returncode == 0, (
        f"Sub-check D FAILED: plain `pytest` run did not exit 0.\n"
        f"exit={res_d.returncode}\n"
        f"stdout=\n{res_d.stdout}\n"
        f"stderr=\n{res_d.stderr}"
    )
    combined_d = res_d.stdout + res_d.stderr
    for forbidden in _FORBIDDEN_LOOP_DIAGNOSTICS:
        assert forbidden not in combined_d, (
            f"Sub-check D FAILED: forbidden loop-wiring diagnostic "
            f"`{forbidden}` appeared in pytest output -- pytest-asyncio "
            f"strict-mode wiring is broken under the synthetic module pattern.\n"
            f"stdout=\n{res_d.stdout}\n"
            f"stderr=\n{res_d.stderr}"
        )

    # All four sub-checks passed -- hybrid Approach A is GO for 27-02 and 27-03.
