"""
Tests for Assignment Management Service.
"""

import pytest
from app.security.authentication import AuthenticationService
from app.services.assignment_service import AssignmentService


def test_assignment_status_filtering():
    user = AuthenticationService.authenticate_demo("FAC001")
    all_as = AssignmentService.get_faculty_assignments(user, faculty_id="FAC001")
    pending_as = AssignmentService.get_faculty_assignments(user, faculty_id="FAC001", status="Pending")

    assert all_as["total_count"] > 0
    assert pending_as["total_count"] <= all_as["total_count"]
    for a in pending_as["assignments"]:
        assert a["status"] == "Pending"


def test_overdue_assignment_detection():
    user = AuthenticationService.authenticate_demo("FAC001")
    res = AssignmentService.get_faculty_assignments(user, faculty_id="FAC001", overdue_only=True)
    for a in res["assignments"]:
        assert a["is_overdue"] is True

