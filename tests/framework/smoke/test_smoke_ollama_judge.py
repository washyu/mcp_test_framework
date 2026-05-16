"""Live integration smoke test against the real Ollama at OLLAMA_BASE_URL.

Permanent live-marker pytest -- D-02 in CONTEXT.md (NOT a throwaway script).
Skipped by default via pyproject.toml `addopts = "-m 'not live_homelab and not live_ollama'"`.
Opt in with `uv run pytest -m live_ollama`.

Falsifies BOTH Phase 3 success criteria (D-04):
  SC#1 -- Judge Protocol importable, OllamaJudge satisfies the runtime
          isinstance check, AND the signature matches the spec-verbatim
          (rubric, subject, context=None) -> JudgeResult shape (Pitfall 4).
  SC#2 -- judge(rubric, subject) against live Ollama returns a valid
          JudgeResult: passed:bool, score 1-5, non-empty reasoning,
          non-empty raw_response. Cold-start path is exercised because
          this IS the first call (no warmup elsewhere -- D-08).

Pre-req: Ollama reachable at cfg.ollama.base_url with cfg.ollama.model in
/api/tags. The cold-start test fails fast via httpx.ConnectError if
missing (transport error -- D-10 propagates). The Protocol-shape test
does not require a live Ollama and runs independently -- it constructs
an OllamaJudge against a dummy base_url but never enters `async with`,
so it exercises only the Protocol/signature/async-ness invariants.

Subject is canned synthetic (D-04) -- decoupled from homelab-mcp so
live_ollama and live_homelab failures are unambiguous.
"""
from __future__ import annotations

import inspect
import logging

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.models import TestCodeConfig
from mcp_test_framework.ollama_judge import JudgeResult, OllamaJudge

_log = logging.getLogger("mcp_test_framework.ollama_judge")

pytestmark = [
    pytest.mark.live_ollama,
    pytest.mark.asyncio(loop_scope="session"),
]


_CANNED_RUBRIC = (
    "Score whether the tool description clearly explains what the tool does "
    "to an LLM agent. 5 = unambiguous, 1 = useless. Penalize verbosity."
)
_CANNED_SUBJECT = (
    "Tool name: get_weather\n"
    "Description: Returns the current weather for a city. "
    "Takes one parameter `city` (string, required) and returns a JSON "
    "object with `temperature_celsius` (number) and `conditions` (string)."
)


def test_judge_protocol_satisfied_by_ollama_judge() -> None:
    """SC#1: Judge Protocol exists, OllamaJudge satisfies it (name + signature + async)."""
    j = OllamaJudge(base_url="http://unused", model="unused", timeout_seconds=1)

    # Layer 1: name-shape (cheap front-line via runtime_checkable).
    assert isinstance(j, Judge), f"OllamaJudge does not satisfy Judge Protocol: {j!r}"

    # Layer 2: signature (Pitfall 4 -- runtime_checkable does NOT verify this).
    sig = inspect.signature(OllamaJudge.judge)
    params = list(sig.parameters)
    assert params == ["self", "rubric", "subject", "context"], params
    assert sig.parameters["context"].default is None

    # Layer 3: async-ness.
    assert inspect.iscoroutinefunction(OllamaJudge.judge), (
        "OllamaJudge.judge must be `async def` per D-05 / spec"
    )


async def test_cold_start_returns_valid_judge_result() -> None:
    """SC#2: cold-start judge call against live Ollama returns a valid JudgeResult.

    Phase 23 D-01 (Cluster A) Pattern S2: Config.sdet is REQUIRED post Phase
    21.1 RELOC-01; supply an inline TestCodeConfig stub at this single site.
    """
    cfg = Config(test_code=TestCodeConfig(generated_root="tests/sdet/_generated"))
    async with OllamaJudge(
        cfg.ollama.base_url,
        cfg.ollama.model,
        cfg.ollama.timeout_seconds,
    ) as judge:
        result = await judge.judge(_CANNED_RUBRIC, _CANNED_SUBJECT)

    assert isinstance(result, JudgeResult), f"got {type(result).__name__}: {result!r}"
    assert isinstance(result.passed, bool)
    assert 1 <= result.score <= 5, f"score out of range: {result!r}"
    assert result.reasoning.strip(), f"empty reasoning: {result!r}"
    assert result.raw_response.strip(), f"empty raw_response: {result!r}"
    # Diagnostic for cold-start UAT: log at INFO so the verifier can opt in
    # via `--log-cli-level=INFO` to eyeball the score distribution without
    # polluting default pytest output. Mirrors the production module's
    # "never the full body by default" logging policy. Phase 5 README will
    # document the opt-in.
    _log.info("cold-start judge result: %r", result)
