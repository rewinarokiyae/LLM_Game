"""
Tests for Demo Authentication Service.
"""

import pytest
from app.security.authentication import AuthenticationService
from app.security.access_control import RoleEnum, AccessDeniedError


def test_authenticate_demo_faculty():
    user = AuthenticationService.authenticate_demo("FAC002")
    assert user.faculty_id == "FAC002"
    assert user.role == RoleEnum.FACULTY
    assert user.department_scope == "DEP-CSE"
    assert user.faculty_name == "Arjun Menon"


def test_authenticate_demo_hod():
    user = AuthenticationService.authenticate_demo("FAC001")
    assert user.faculty_id == "FAC001"
    assert user.role == RoleEnum.HOD
    assert user.department_scope == "DEP-CSE"
    assert user.faculty_name == "Dr. Meera Nair"


def test_authenticate_demo_admin():
    user = AuthenticationService.authenticate_demo("admin")
    assert user.role == RoleEnum.ADMIN
    assert user.department_scope == "ALL"
    assert user.faculty_id is None


def test_authenticate_invalid_user_raises():
    with pytest.raises(AccessDeniedError):
        AuthenticationService.authenticate_demo("NON_EXISTENT_USER_123")

