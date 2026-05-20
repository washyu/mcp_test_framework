"""Phase 23 D-02: test-side override of the session-scoped `config` fixture.

After Phase 21.1 RELOC-01 made Config.sdet REQUIRED, the production fixture
at src/mcp_test_framework/fixtures.py raises pydantic.ValidationError when
constructed bare. tests/framework/ tests don't need a real sdet config -- they
exercise the framework itself, not SDET codegen. This conftest shadows the
fixture with one that supplies the `_SDET_STUB` pattern already established
at tests/framework/unit/test_homelab_config.py.

Production `src/` is intentionally NOT modified -- see Phase 23 CONTEXT.md D-02.
"""
from __future__ import annotations

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.models import TestCodeConfig

_TEST_CODE_STUB = TestCodeConfig(generated_root="tests/sdet/_generated")


@pytest.fixture(scope="session")
def config() -> Config:
    return Config(test_code=_TEST_CODE_STUB)


def pytest_configure(pytestconfig: pytest.Config) -> None:
    """Phase 30 CLOSE-02: register the framework-internal `parity` marker.

    The marker is a recursion guard for `tests/framework/parity/test_cli_vs_pytest_route.py`:
    its outer pytest session selects the test (it carries `pytestmark = [parity, ...]`),
    but the two inner subprocesses it spawns must exclude it via `-m "not parity"` so
    they do not re-collect the parity test inside themselves.

    Registered here (framework-self-test conftest) rather than `pyproject.toml`'s
    `[tool.pytest.ini_options] markers = [...]` so the marker stays framework-internal
    and is NOT surfaced on operator-facing `pytest --markers` output.
    """
    pytestconfig.addinivalue_line(
        "markers",
        "parity: framework-internal recursion guard for the CLI/library "
        "parity test (tests/framework/parity/). Inner subprocesses exclude "
        "this marker with `-m 'not parity'` to prevent infinite recursion.",
    )
