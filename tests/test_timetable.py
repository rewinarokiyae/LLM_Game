"""
Tests for Timetable Service and Conflict Detection.
"""

from datetime import date
import pytest
from app.security.authentication import AuthenticationService
from app.services.timetable_service import TimetableService
from app.engines.conflict_detector import ConflictDetector


def test_timetable_lookup_by_day():
    user = AuthenticationService.authenticate_demo("FAC001")
    res = TimetableService.get_faculty_timetable(user, faculty_id="FAC001", day="Wednesday")
    assert res["faculty_id"] == "FAC001"
    assert res["day_filter"] == "Wednesday"
    assert res["session_count"] > 0
    for s in res["sessions"]:
        assert s["day"] == "Wednesday"


def test_conflict_detection_intervals():
    target_week = date(2026, 11, 9)
    conflicts = ConflictDetector.detect_conflicts(week_start=target_week)

    # In synthetic dataset: 0 faculty double bookings, 11 room conflicts, 70 section conflicts
    assert conflicts["faculty_conflicts_count"] == 0
    assert conflicts["room_conflicts_count"] == 11
    assert conflicts["section_conflicts_count"] == 70
    assert conflicts["has_conflicts"] is True

