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

## Further reading

- [`README.md`](../README.md) -- back to setup and usage
- `src/mcp_test_framework/rubrics.py` -- built-in rubric examples
- `src/mcp_test_framework/judge_protocol.py` -- Protocol definition + `JudgeResult` shape
