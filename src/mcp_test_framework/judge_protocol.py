"""Pluggable LLM-judge seam.

Defines the runtime-checkable ``Judge`` Protocol with the async
``judge(rubric, subject, context=None) -> JudgeResult`` signature.

Why ``typing.Protocol`` rather than ``abc.ABC``:
- Structural typing matches the project's "result types live in their
  owning module" convention (``ToolNotFoundError`` in ``mcp_client.py``,
  ``ValidationIssue`` in ``schema_validator.py``); a Protocol does not
  force concrete classes to inherit from a framework type.
- ``@typing.runtime_checkable`` lets the judge smoke test assert
  ``isinstance(OllamaJudge(...), Judge)`` without importing the concrete
  class -- the smoke catches the seam regression mechanically.
- The Protocol lives in its own file so a post-MVP agent-loop judge
  implementation can import the Protocol without pulling in the
  rubric-style ``OllamaJudge``. That keeps the alternate judge a 1-file
  addition rather than a rewrite.

Why import ``JudgeResult`` from ``ollama_judge.py`` rather than re-exporting
from ``models.py``:
- ``JudgeResult`` is a domain-local result type (parallels
  ``ToolNotFoundError``); per the "result types in their owning module"
  convention. ``models.py`` holds only cross-cutting Config sub-models.
- One-way dependency: ``judge_protocol.py`` -> ``ollama_judge.py``. The
  concrete module never imports from this file, so there is no circular
  import.

WARNING: ``@runtime_checkable`` only checks attribute presence by name --
it does NOT validate signature compatibility (PEP 544 limitation). A class
exposing ``def judge(self, ...)`` (sync) or ``def judge(self) -> int``
(wrong signature) will still pass ``isinstance(x, Judge)``. The smoke test
is therefore made load-bearing by asserting both ``isinstance(...)`` AND
``inspect.signature`` shape AND ``inspect.iscoroutinefunction``.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from mcp_test_framework.ollama_judge import JudgeResult


@runtime_checkable
class Judge(Protocol):
    """Pluggable LLM-judge seam.

    Implementations evaluate a ``subject`` against a ``rubric`` and return
    a :class:`JudgeResult`. The optional ``context`` is free-form to
    accommodate post-MVP backends (e.g., reflection traces from an
    agent-loop judge) without forcing a typed wrapper.
    """

    async def judge(
        self,
        rubric: str,
        subject: str,
        context: dict | None = None,
    ) -> JudgeResult: ...
