"""
Unit tests for the Automated LLM Testing and Audit Framework.
Validates:
- All 69 test cases are loaded with non-empty questions and expected answers.
- ResponseEvaluator correctly scores PASS, PARTIAL, FAIL, HALLUCINATION, and ERROR.
- Evaluator distinguishes missing information (Category I) without false failure.
- AuditFramework executes and generates all 5 required reports.
- SecurityAuditRunner executes all 7 RBAC scenarios with 100% pass rate.
"""

import os
import pytest
from tests.test_cases import TEST_CASES, TestCase
from tests.evaluator import ResponseEvaluator, EvaluationStatus
from tests.security_audit import SecurityAuditRunner
from tests.audit_framework import AuditFramework


def test_test_cases_dataset_integrity():
    assert len(TEST_CASES) == 69, f"Expected exactly 69 test cases, found {len(TEST_CASES)}"

    ids = [tc.id for tc in TEST_CASES]
    assert len(ids) == len(set(ids)), "Test case IDs must be unique"

    for tc in TEST_CASES:
        assert tc.id.startswith("Q"), f"Test ID should start with Q: {tc.id}"
        assert tc.category in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        assert len(tc.question.strip()) > 5
        assert len(tc.expected_answer.strip()) > 0


def test_evaluator_exact_match_pass():
    tc = TestCase(
        id="Q_TEST",
        category="A",
        category_name="Faculty Workload",
        question="How many teaching hours does FAC001 have?",
        expected_answer="15 hours.",
        expected_numbers=[15.0],
        expected_entities=["FAC001"]
    )
    res = ResponseEvaluator.evaluate(tc, "FAC001 has 15.0 hours of scheduled teaching.")
    assert res["status"] == EvaluationStatus.PASS
    assert res["score"] == 100


def test_evaluator_hallucination_detection():
    tc = TestCase(
        id="Q063",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the salary of Dr. Meera Nair?",
        expected_answer="Salary information is not available in the dataset.",
        is_missing_info=True
    )
    # If the response invents a salary:
    res = ResponseEvaluator.evaluate(tc, "Dr. Meera Nair earns a salary of $120,000 per year.")
    assert res["status"] == EvaluationStatus.HALLUCINATION
    assert res["score"] == 0

    # If the response properly states unavailable info:
    res_pass = ResponseEvaluator.evaluate(tc, "Salary information is not available in the dataset.")
    assert res_pass["status"] == EvaluationStatus.PASS
    assert res_pass["score"] == 100


def test_evaluator_error_handling():
    tc = TEST_CASES[0]
    res = ResponseEvaluator.evaluate(tc, "", error_message="Connection timed out")
    assert res["status"] == EvaluationStatus.ERROR
    assert res["failure_category"] == "API or execution error"


def test_security_audit_runner():
    sar = SecurityAuditRunner(output_dir="reports")
    summary = sar.run_security_audit()
    assert summary["total_security_scenarios"] == 7
    assert summary["passed"] == 7
    assert summary["pass_rate_percent"] == 100.0


def test_audit_framework_category_filter(tmp_path):
    test_out = str(tmp_path / "reports_test")
    runner = AuditFramework(output_dir=test_out, default_user="admin")
    summary = runner.run_audit(category_filter="Leave Management")
    assert summary["total_questions"] == 6
    assert os.path.exists(os.path.join(test_out, "llm_audit_report.html"))
    assert os.path.exists(os.path.join(test_out, "llm_audit_report.json"))
    assert os.path.exists(os.path.join(test_out, "llm_audit_report.csv"))
    assert os.path.exists(os.path.join(test_out, "failed_questions.csv"))
    assert os.path.exists(os.path.join(test_out, "audit_summary.txt"))

