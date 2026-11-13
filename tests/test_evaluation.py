"""
Tests for Automated Evaluation Suite.
"""

import os
import pytest
from app.evaluation.test_runner import TestRunner


def test_test_runner_execution():
    runner = TestRunner()
    summary = runner.run_all_evaluations()

    assert summary["total_tests"] == 35
    assert summary["passed"] == 35
    assert summary["failed"] == 0
    assert summary["pass_rate_percent"] == 100.0

    assert os.path.exists("reports/evaluation/evaluation_report.json")
    assert os.path.exists("reports/evaluation/evaluation_report.csv")
    assert os.path.exists("reports/evaluation/evaluation_report.md")

