"""
Tests for Workload Calculation Engine.
"""

from datetime import date
import pytest
from app.engines.workload_engine import WorkloadEngine


def test_workload_hours_accuracy_all_faculty():
    # Expected hours from Workload_Summary sheet
    expected = {
        "FAC001": 15.0, "FAC002": 17.0, "FAC003": 13.0, "FAC004": 17.0,
        "FAC005": 17.0, "FAC006": 14.0, "FAC007": 14.0, "FAC008": 15.0,
        "FAC009": 19.0, "FAC010": 15.0, "FAC011": 13.0, "FAC012": 17.0,
        "FAC013": 11.0, "FAC014": 15.0, "FAC015": 18.0, "FAC016": 16.0,
        "FAC017": 14.0, "FAC018": 19.0
    }

    target_week = date(2026, 11, 9)
    for fid, exp_hours in expected.items():
        data = WorkloadEngine.get_faculty_teaching_hours(fid, target_week)
        assert data["actual_teaching_hours"] == exp_hours, f"Mismatch for {fid}: expected {exp_hours}, got {data['actual_teaching_hours']}"


def test_cancelled_session_exclusion_and_substitution():
    target_week = date(2026, 11, 9)

    # FAC004 has cancelled class TT0053 substituted by FAC005 (TT0280)
    data_fac004 = WorkloadEngine.get_faculty_teaching_hours("FAC004", target_week)
    assert len(data_fac004["cancelled_sessions"]) > 0

    # FAC005 received substitute credit
    data_fac005 = WorkloadEngine.get_faculty_teaching_hours("FAC005", target_week)
    assert data_fac005["breakdown_hours"]["Substituted"] > 0

