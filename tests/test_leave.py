"""
Tests for Leave and Availability Management.
"""

from datetime import date
import pytest
from app.security.authentication import AuthenticationService
from app.services.leave_service import LeaveService


def test_approved_vs_pending_leave():
    user_hod = AuthenticationService.authenticate_demo("FAC001")
    # Query department approved leave
    leaves = LeaveService.get_department_leave(user_hod, "DEP-CSE", approved_only=True)
    for l in leaves:
        assert l["is_confirmed"] is True
        assert l["approval_status"] == "Approved"


def test_faculty_leave_records():
    user = AuthenticationService.authenticate_demo("FAC004")
    leaves = LeaveService.get_faculty_leave(user, "FAC004")
    assert len(leaves) > 0
    # FAC004 has casual leave
    assert any(l["leave_type"] == "Casual Leave" for l in leaves)

