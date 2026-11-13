"""
Tests for Role-Based Access Control and Scope Enforcement.
"""

import pytest
from app.security.authentication import AuthenticationService
from app.security.access_control import AccessDeniedError
from app.services.faculty_service import FacultyService
from app.services.workload_service import WorkloadService
from app.services.assignment_service import AssignmentService


def test_faculty_cannot_access_other_faculty_details():
    faculty_user = AuthenticationService.authenticate_demo("FAC002")  # Arjun Menon
    # Can access own details
    details = FacultyService.get_faculty_details(faculty_user, "FAC002")
    assert details["faculty_id"] == "FAC002"

    # Cannot access another faculty's details
    with pytest.raises(AccessDeniedError):
        FacultyService.get_faculty_details(faculty_user, "FAC001")


def test_faculty_cannot_access_other_faculty_assignments():
    faculty_user = AuthenticationService.authenticate_demo("FAC002")
    with pytest.raises(AccessDeniedError):
        AssignmentService.get_faculty_assignments(faculty_user, "FAC001")


def test_hod_cannot_access_other_department_workload():
    hod_cse = AuthenticationService.authenticate_demo("FAC001")  # HOD DEP-CSE
    # Can access own department
    summary = WorkloadService.get_department_workload_summary(hod_cse, "DEP-CSE")
    assert summary["department_id"] == "DEP-CSE"

    # Cannot access another department
    with pytest.raises(AccessDeniedError):
        WorkloadService.get_department_workload_summary(hod_cse, "DEP-AIML")


def test_admin_can_access_all_departments():
    admin_user = AuthenticationService.authenticate_demo("ADMIN")
    sum_cse = WorkloadService.get_department_workload_summary(admin_user, "DEP-CSE")
    sum_aiml = WorkloadService.get_department_workload_summary(admin_user, "DEP-AIML")
    assert sum_cse["department_id"] == "DEP-CSE"
    assert sum_aiml["department_id"] == "DEP-AIML"

