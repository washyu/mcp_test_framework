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
from mcp_test_framework.models import SdetConfig

_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")


@pytest.fixture(scope="session")
def config() -> Config:
    return Config(sdet=_SDET_STUB)
