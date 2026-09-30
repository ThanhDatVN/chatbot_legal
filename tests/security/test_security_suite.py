"""The 30-case security suite on the synthetic corpus (runs in CI without models)."""

import pytest

from evaluation.security_cases import DOCUMENT_CASES, MODEL_OUTPUT_CASES, QUESTION_CASES, TOOL_CASES, TOTAL
from evaluation.security_eval import _document, _model_output, _question, _tool


def test_suite_has_thirty_cases_and_five_indirect_injections():
    assert TOTAL == 30
    assert len(DOCUMENT_CASES) >= 5


@pytest.mark.parametrize("case", QUESTION_CASES, ids=[c[0] for c in QUESTION_CASES])
def test_question_cases(runtime, case):
    result = _question(runtime, case)
    assert result["passed"], result["problems"]


@pytest.mark.parametrize("case", TOOL_CASES, ids=[c[0] for c in TOOL_CASES])
def test_tool_cases(runtime, case):
    result = _tool(runtime, case)
    assert result["passed"], result["problems"]


@pytest.mark.parametrize("case", MODEL_OUTPUT_CASES, ids=[c[0] for c in MODEL_OUTPUT_CASES])
def test_model_output_cases(runtime, case):
    result = _model_output(runtime, case)
    assert result["passed"], result["problems"]


@pytest.mark.parametrize("case", DOCUMENT_CASES, ids=[c[0] for c in DOCUMENT_CASES])
def test_document_cases(runtime, case):
    result = _document(runtime, case)
    assert result["passed"], result["problems"]
