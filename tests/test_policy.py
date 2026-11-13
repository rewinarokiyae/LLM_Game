"""
Tests for Policy Validation Engine.
"""

from datetime import date
import pytest
from app.engines.policy_validator import PolicyValidator


def test_standard_policy_violation():
    target_week = date(2026, 11, 9)
    # FAC001: Professor (max 12), actual 15 -> violation excess 3
    res_fac001 = PolicyValidator.evaluate_faculty_workload("FAC001", target_week)
    assert res_fac001["actual_teaching_hours"] == 15.0
    assert res_fac001["effective_max_hours"] == 12.0
    assert res_fac001["excess_hours"] == 3.0
    assert res_fac001["is_violation"] is True


def test_approved_exception_overrides_max_hours():
    target_week = date(2026, 11, 9)
    # FAC009: Assistant Professor (std max 16), has Approved PEX001 override = 20. Actual = 19.
    res_fac009 = PolicyValidator.evaluate_faculty_workload("FAC009", target_week)
    assert res_fac009["actual_teaching_hours"] == 19.0
    assert res_fac009["standard_policy_max_hours"] == 16.0
    assert res_fac009["effective_max_hours"] == 20.0
    assert res_fac009["excess_hours"] == 0.0
    assert res_fac009["is_violation"] is False


def test_pending_exception_does_not_override_max_hours():
    target_week = date(2026, 11, 9)
    # FAC016: Assistant Professor (std max 16), has Pending PEX002 override = 19. Effective must remain 16.
    res_fac016 = PolicyValidator.evaluate_faculty_workload("FAC016", target_week)
    assert res_fac016["standard_policy_max_hours"] == 16.0
    assert res_fac016["effective_max_hours"] == 16.0
    assert len(res_fac016["pending_exceptions"]) > 0


def test_rejected_exception_does_not_override_max_hours():
    target_week = date(2026, 11, 9)
    # FAC012: Lecturer (std max 18), has Rejected PEX003 override = 19. Effective must remain 18.
    res_fac012 = PolicyValidator.evaluate_faculty_workload("FAC012", target_week)
    assert res_fac012["effective_max_hours"] == 18.0
    assert len(res_fac012["rejected_exceptions"]) > 0


def test_exemption_relief_reduces_minimum_only():
    target_week = date(2026, 11, 9)
    # FAC001 has HOD exemption EX001 of 4 relief hours
    res_fac001 = PolicyValidator.evaluate_faculty_workload("FAC001", target_week)
    assert res_fac001["applied_exemption"] is not None
    assert res_fac001["applied_exemption"]["relief_hours_per_week"] == 4.0
    # Minimum reduces from 6 to 2, but max cap remains 12
    assert res_fac001["effective_min_hours"] == 2.0
    assert res_fac001["effective_max_hours"] == 12.0

