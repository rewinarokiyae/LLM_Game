"""
Tests for Database Models, Connections, and Integrity.
"""

import pytest
from app.database.connection import get_db_session
from app.database.models import Faculty, Department, Timetable, WorkloadPolicy, UserRole


def test_database_connection_and_counts():
    with get_db_session() as session:
        fac_count = session.query(Faculty).count()
        dept_count = session.query(Department).count()
        tt_count = session.query(Timetable).count()
        pol_count = session.query(WorkloadPolicy).count()
        user_count = session.query(UserRole).count()

        assert fac_count == 18
        assert dept_count == 3
        assert tt_count == 281
        assert pol_count == 4
        assert user_count == 19


def test_faculty_department_relationship():
    with get_db_session() as session:
        fac = session.query(Faculty).filter(Faculty.faculty_id == "FAC001").first()
        assert fac is not None
        assert fac.faculty_name == "Dr. Meera Nair"
        assert fac.department is not None
        assert fac.department.department_id == "DEP-CSE"
        assert fac.department.department_code == "CSE"

