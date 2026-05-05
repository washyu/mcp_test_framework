"""Unit tests for mcp_test_framework.ollama_judge — Plan 03-02.

Pure-data unit tests on the module-level helpers shipped by Plan 03-01:
``_strip_decorations``, ``_extract_first_json_object``, ``_parse_judge_response``,
``_build_request_body``, and the ``_SYSTEM_PROMPT`` constant.

The tests fall into two slices:

1. **D-09 parser branches (CONTEXT D-09 four-step contract):**
   - Step 1 (``_strip_decorations``): removes ``<think>...</think>`` blocks
     non-greedily so multiple think blocks are independently stripped.
     Falsifies a future "regex with .*" greedy mistake.
   - Step 3 (``_extract_first_json_object``): brace-balanced state machine
     correctly recovers a balanced ``{...}`` from prose-prefixed text and
     handles braces inside JSON string literals (PITFALLS Pitfall 5 — a
     regex cannot do this; this test guards against a future "let's just
     use a regex" refactor).
   - Step 4 (``_parse_judge_response`` fallback): on malformed JSON,
     out-of-range score, or missing required field, returns the locked
     fallback ``JudgeResult(passed=False, score=1, reasoning="malformed
     judge response", raw_response=<original>)``. Every branch preserves
     ``raw_response`` verbatim (DOCS-03).
   - Happy + brace-recovery paths overwrite ``raw_response`` to the full
     original input string (proving the ``_validate_with_raw`` raw-injection
     step in Plan 03-01).

2. **D-07 / CORE-04 locked request-body shape (``_build_request_body``):**
   ``stream:False``, ``format:"json"``, ``think:False``, ``keep_alive:"30m"``,
   ``options:{temperature:0, num_predict:256}``, system message is
   ``_SYSTEM_PROMPT`` verbatim, user message contains the delimited subject
   block, and the optional ``Context: <json>`` line appears only when
   context is provided.

Test corpus is enumerated in ``.planning/phases/03-ollama-judge/03-RESEARCH.md``
§Common Pitfalls 5. All strings are pre-verified against the parser
implementation. No HTTP mocking, no AsyncClient, no event loop — these are
pure synchronous tests on module-level helpers (CONTEXT.md "Phase 3
unit-test scope" Discretion).
"""
from __future__ import annotations

from mcp_test_framework.ollama_judge import (
    _SYSTEM_PROMPT,
    JudgeResult,
    _build_request_body,
    _extract_first_json_object,
    _parse_judge_response,
    _strip_decorations,
)

# --------------------------------------------------------------------------
# Test corpus (literally pre-verified against the Plan 03-01 parser impl)
# --------------------------------------------------------------------------

_HAPPY = '{"passed": true, "score": 5, "reasoning": "ok", "raw_response": ""}'
_THINK_HAPPY = (
    '<think>reasoning here</think>\n'
    '{"passed": true, "score": 5, "reasoning": "ok", "raw_response": ""}'
)
_MULTI_THINK = (
    '<think>a</think> middle <think>b</think>'
    '{"passed": true, "score": 5, "reasoning": "ok", "raw_response": ""}'
)
_THINK_FENCE = (
    '<think>x</think>\n```json\n'
    '{"passed": true, "score": 5, "reasoning": "ok", "raw_response": ""}\n```'
)
_PROSE_PREFIX = (
    'Sure! {"passed": true, "score": 4, "reasoning": "good", "raw_response": ""}'
)
_OUT_OF_RANGE = '{"passed": true, "score": 7, "reasoning": "x", "raw_response": ""}'
_MISSING_FIELD = '{"passed": true, "score": 4}'
_UNBALANCED_THINK = '<think>only think tag, no closing'
_BRACE_IN_STRING = (
    '{"reasoning": "score = }5{ here", "passed": true, '
    '"score": 4, "raw_response": ""}'
)
_GARBAGE = 'not json at all'


# --------------------------------------------------------------------------
# D-09 step 1: _strip_decorations
# --------------------------------------------------------------------------

def test_strip_decorations_removes_single_think_block() -> None:
    """D-09 step 1: a single <think>...</think> block is removed; trailing JSON intact."""
    out = _strip_decorations(_THINK_HAPPY)
    assert "<think>" not in out
    assert "</think>" not in out
    assert out.startswith("{")
    assert out.endswith("}")
    # The remainder must still be valid JSON-shaped text.
    assert '"passed": true' in out


def test_strip_decorations_removes_multiple_think_blocks_non_greedy() -> None:
    """D-09 step 1: two <think>...</think> blocks are stripped INDEPENDENTLY.

    Falsifies a greedy-regex mistake that would consume everything between
    the first <think> and the last </think>, deleting the middle text and
    JSON between them.
    """
    out = _strip_decorations(_MULTI_THINK)
    assert "<think>" not in out
    assert "</think>" not in out
    # The literal " middle " text between the two think blocks must survive.
    assert "middle" in out
    # The JSON object must still be present.
    assert '"passed": true' in out


# --------------------------------------------------------------------------
# D-09 step 2/3 happy paths: _parse_judge_response success branches
# --------------------------------------------------------------------------

def test_parse_judge_response_happy_path_overwrites_raw_response() -> None:
    """D-09 step 2 + DOCS-03: clean JSON yields a JudgeResult with raw_response = original input."""
    result = _parse_judge_response(_HAPPY)
    assert isinstance(result, JudgeResult)
    assert result.passed is True
    assert result.score == 5
    assert result.reasoning == "ok"
    # raw_response must be the FULL original input string, not the model's emitted "" value.
    assert result.raw_response == _HAPPY


def test_parse_judge_response_think_block_then_fenced_json() -> None:
    """D-09 steps 1 + 2: <think> + ```json``` fence is stripped, JSON parses cleanly."""
    result = _parse_judge_response(_THINK_FENCE)
    assert isinstance(result, JudgeResult)
    assert result.passed is True
    assert result.score == 5
    assert result.reasoning == "ok"
    # raw_response preserved verbatim including the <think> block and fences.
    assert result.raw_response == _THINK_FENCE


def test_parse_judge_response_brace_recovery_from_prose_prefix() -> None:
    """D-09 step 3: prose-prefixed JSON is recovered by the brace-balanced extractor.

    Falsifies removal of the brace-balanced extractor; without step 3 this
    input would fall through to the malformed-fallback branch.
    """
    result = _parse_judge_response(_PROSE_PREFIX)
    assert isinstance(result, JudgeResult)
    assert result.passed is True
    assert result.score == 4
    assert result.reasoning == "good"
    # raw_response is the FULL original input — including the "Sure! " prefix.
    assert result.raw_response == _PROSE_PREFIX


# --------------------------------------------------------------------------
# D-09 step 4 fallback branches: malformed → locked JudgeResult
# --------------------------------------------------------------------------

def test_parse_judge_response_malformed_returns_fallback_with_raw_preserved() -> None:
    """D-09 step 4: garbage input yields the locked fallback JudgeResult.

    OPS-01 + DOCS-03 falsifier: passed=False, score=1, the literal reasoning
    string, and raw_response equal to the verbatim input.
    """
    result = _parse_judge_response(_GARBAGE)
    assert isinstance(result, JudgeResult)
    assert result.passed is False
    assert result.score == 1
    assert result.reasoning == "malformed judge response"
    assert result.raw_response == _GARBAGE


def test_parse_judge_response_out_of_range_score_returns_fallback() -> None:
    """D-09 step 4: score=7 violates Field(ge=1, le=5); ValidationError → fallback.

    Falsifies removal of the Field(ge=1, le=5) bound on JudgeResult.score
    (T-03-05 prompt-injection / model-misbehavior mitigation).
    """
    result = _parse_judge_response(_OUT_OF_RANGE)
    assert result.passed is False
    assert result.score == 1
    assert result.reasoning == "malformed judge response"
    assert result.raw_response == _OUT_OF_RANGE


def test_parse_judge_response_missing_required_field_returns_fallback() -> None:
    """D-09 step 4: missing 'reasoning' triggers Pydantic ValidationError → fallback."""
    result = _parse_judge_response(_MISSING_FIELD)
    assert result.passed is False
    assert result.score == 1
    assert result.reasoning == "malformed judge response"
    assert result.raw_response == _MISSING_FIELD


def test_parse_judge_response_unbalanced_think_no_json_returns_fallback() -> None:
    """PITFALLS Pitfall 6: unbalanced <think> with no JSON falls to step 4 fallback.

    The non-greedy think-strip regex requires a closing tag, so an
    unbalanced <think> is left in the content; with no '{' present, the
    brace-extractor returns None and the parser falls to the fallback.
    """
    result = _parse_judge_response(_UNBALANCED_THINK)
    assert result.passed is False
    assert result.score == 1
    assert result.reasoning == "malformed judge response"
    assert result.raw_response == _UNBALANCED_THINK


# --------------------------------------------------------------------------
# D-09 step 3: _extract_first_json_object brace-in-string edge case
# --------------------------------------------------------------------------

def test_extract_first_json_object_handles_braces_inside_strings() -> None:
    """PITFALLS Pitfall 5: braces inside JSON string literals do NOT mis-balance the scanner.

    Falsifies a future "let's just use a regex" refactor (T-03-02-01). The
    state machine MUST track in_string and escape so that '}' inside a
    quoted string does not decrement the depth counter.
    """
    extracted = _extract_first_json_object(_BRACE_IN_STRING)
    # The full balanced object — including the brace-laden string value — is returned.
    assert extracted == _BRACE_IN_STRING
    # And it round-trips through the parser.
    result = _parse_judge_response(_BRACE_IN_STRING)
    assert result.passed is True
    assert result.score == 4
    assert result.reasoning == "score = }5{ here"
    assert result.raw_response == _BRACE_IN_STRING


# --------------------------------------------------------------------------
# CORE-04 / D-07: _build_request_body locked invariants
# --------------------------------------------------------------------------

def test_build_request_body_locks_stream_false_format_json_think_false() -> None:
    """CORE-04 / ROADMAP SC#2: every locked field of the /api/chat body is asserted.

    Falsifies any change to: stream, format, think, keep_alive,
    options.temperature, options.num_predict, model echo, system role,
    system content (= _SYSTEM_PROMPT), user role, or the delimited subject
    block in the user message.
    """
    body = _build_request_body("qwen3.6:latest", "rubric text", "subject text", None)

    # Locked transport / mode fields.
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["think"] is False
    assert body["keep_alive"] == "30m"

    # Locked options.
    assert body["options"] == {"temperature": 0, "num_predict": 256}

    # Model passthrough.
    assert body["model"] == "qwen3.6:latest"

    # Messages structure: [system, user].
    assert isinstance(body["messages"], list)
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"] == _SYSTEM_PROMPT
    assert body["messages"][1]["role"] == "user"

    # Delimited subject block appears verbatim in the user message.
    user_content = body["messages"][1]["content"]
    assert "<<<SUBJECT>>>\nsubject text\n<<<END SUBJECT>>>" in user_content


def test_build_request_body_with_context_includes_json_context_line() -> None:
    """CORE-04: when context is provided, the user message contains 'Context: <json>'.

    json.dumps with sort_keys=True so the context interpolation is stable
    across runs and across dict insertion order (test repeatability).
    """
    body = _build_request_body("m", "r", "s", {"tool_name": "x"})
    user_content = body["messages"][1]["content"]
    # Exact substring: json.dumps({"tool_name": "x"}, sort_keys=True) == '{"tool_name": "x"}'.
    assert 'Context: {"tool_name": "x"}' in user_content


def test_build_request_body_without_context_omits_context_line() -> None:
    """CORE-04: when context is None, the user message has no 'Context:' substring.

    Prevents accidental literal 'Context: None' or empty-context noise from
    leaking into the prompt.
    """
    body = _build_request_body("m", "r", "s", None)
    user_content = body["messages"][1]["content"]
    assert "Context:" not in user_content


# --------------------------------------------------------------------------
# D-07: _SYSTEM_PROMPT invariants
# --------------------------------------------------------------------------

def test_system_prompt_contains_no_think_and_subject_markers_and_ignore_clause() -> None:
    """D-07 + T-03-01: prompt-injection mitigation invariants.

    - /no_think directive (qwen3 belt-and-braces, PITFALLS Pitfall 2)
    - <<<SUBJECT>>> / <<<END SUBJECT>>> delimited-subject markers
    - Explicit instruction to ignore instructions inside the SUBJECT block
      (T-03-01 prompt-injection mitigation)
    """
    assert "/no_think" in _SYSTEM_PROMPT
    assert "<<<SUBJECT>>>" in _SYSTEM_PROMPT
    assert "<<<END SUBJECT>>>" in _SYSTEM_PROMPT
    # Case-insensitive check per plan acceptance criteria.
    assert "ignore" in _SYSTEM_PROMPT.lower()
