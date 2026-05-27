"""pytest_configure clamp pins.

Load-bearing invariant: passthrough mode mutates BOTH
``config.option.numprocesses`` AND ``config.option.tx`` -- xdist's
``NodeManager.setup_nodes()`` reads ``tx``, not ``numprocesses``, so the two
attributes must be mutated together. Mutating only ``numprocesses`` would
leave N workers spawning despite the operator-visible "clamped to 1" banner.

Strict mode leaves both attributes untouched and emits no banner.

The fake ``pytest.Config`` is hand-rolled (SimpleNamespace) -- following the
pattern in ``test_mcp_config_fixture.py`` -- so these tests exercise the
plugin's option-mutation side effects without standing up a live pytest
session.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework import _plugin
from mcp_test_framework.config import Config
from mcp_test_framework.models import TestCodeConfig


_TEST_CODE_STUB = TestCodeConfig(generated_root=Path("tests/test_code/_generated"))


def _make_fake_config(
    host_isolation: str,
    numprocesses: int,
    tmp_path: Path,
) -> SimpleNamespace:
    """Construct a SimpleNamespace fake matching the surface pytest_configure
    reads: ``addinivalue_line`` method, ``getini`` returning ``""`` (no
    ini-path arm), ``option`` carrying numprocesses + tx, and the
    ``_mcp_contracts_config`` stash pre-populated with a Config in the
    requested isolation mode.

    The pre-populated stash short-circuits the function's YAML-load arm --
    the clamp block reads the stash directly, not the local ``cfg`` set by
    the ini-arm.
    """
    cfg = Config(test_code=_TEST_CODE_STUB, host_isolation=host_isolation)
    # ``tx`` mirrors what xdist's ``pytest_cmdline_main(tryfirst=True)`` would
    # have already populated when the operator passed ``-n N``.
    tx_list = ["popen"] * numprocesses if numprocesses else []
    option = SimpleNamespace(numprocesses=numprocesses, tx=tx_list)
    fake = SimpleNamespace(
        option=option,
        rootpath=tmp_path,
        addinivalue_line=lambda *args, **kwargs: None,
        getini=lambda key: "",
        _mcp_contracts_config=cfg,
    )
    return fake


def test_passthrough_clamps_xdist_numprocesses_and_tx(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Passthrough mode + ``-n 4`` clamps BOTH ``numprocesses`` and ``tx``.

    The dual-mutation invariant is load-bearing: xdist's NodeManager reads
    ``tx``, not ``numprocesses``, so leaving ``tx`` as ``["popen"]*4`` would
    spawn 4 workers regardless of the ``numprocesses=1`` clamp.

    Banner-text pin asserts the three operator-tone locked phrases survive
    in captured stderr.
    """
    fake = _make_fake_config(
        host_isolation="passthrough",
        numprocesses=4,
        tmp_path=tmp_path,
    )
    assert fake.option.numprocesses == 4
    assert len(fake.option.tx) == 4

    _plugin.pytest_configure(fake)

    assert fake.option.numprocesses == 1, (
        "passthrough mode must clamp numprocesses to 1"
    )
    assert fake.option.tx == ["popen"], (
        "passthrough mode must overwrite tx to a single-entry list -- "
        "load-bearing because xdist's NodeManager reads tx, not numprocesses"
    )

    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "xdist worker count clamped to 1" in text
    assert "single-owner resource" in text
    assert "host_isolation=strict for parallel" in text


def test_strict_mode_does_not_clamp_xdist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Strict mode + ``-n 4`` leaves both attributes untouched.

    Operator running the default isolation surface gets full xdist
    parallelism; the clamp guard's ``host_isolation == 'passthrough'``
    check short-circuits.
    """
    fake = _make_fake_config(
        host_isolation="strict",
        numprocesses=4,
        tmp_path=tmp_path,
    )

    _plugin.pytest_configure(fake)

    assert fake.option.numprocesses == 4, (
        "strict mode must NOT clamp -- operator gets full xdist parallelism"
    )
    assert fake.option.tx == ["popen"] * 4, (
        "strict mode must NOT overwrite tx -- xdist runs with all workers"
    )

    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "xdist worker count clamped" not in text


def test_passthrough_with_no_xdist_flag_does_not_emit_banner(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Passthrough mode with ``numprocesses=0`` (operator did not pass -n)
    fires no banner. The clamp guard's ``and config.option.numprocesses``
    short-circuits because there are no workers to clamp.
    """
    fake = _make_fake_config(
        host_isolation="passthrough",
        numprocesses=0,
        tmp_path=tmp_path,
    )

    _plugin.pytest_configure(fake)

    assert fake.option.numprocesses == 0
    assert fake.option.tx == []

    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "xdist worker count clamped" not in text
