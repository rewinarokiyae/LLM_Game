"""
Faculty Service.
Provides faculty profile retrieval, department listings, and subject allocation lookups
with strict role-based access control.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Faculty, Department, FacultySubjectAllocation, Subject
from app.security.access_control import UserContext, AccessDeniedError


class FacultyService:
    @classmethod
    def get_faculty_details(cls, user_context: UserContext, faculty_id: str) -> Dict[str, Any]:
        """Retrieve faculty profile details with RBAC enforcement."""
        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == faculty_id).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{faculty_id}' not found.")

            # RBAC Check
            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You are not authorized to view records for faculty '{faculty_id}'.")

            dept = session.query(Department).filter(Department.department_id == fac.department_id).first()
            dept_name = dept.department_name if dept else fac.department_id

            allocations = session.query(FacultySubjectAllocation, Subject).join(
                Subject, FacultySubjectAllocation.subject_id == Subject.subject_id
            ).filter(FacultySubjectAllocation.faculty_id == faculty_id).all()

            alloc_list = [
                {
                    "allocation_id": a.allocation_id,
                    "subject_id": a.subject_id,
                    "subject_name": s.subject_name,
                    "section_id": a.section_id,
                    "allocation_type": a.allocation_type,
                    "term": a.term
                }
                for a, s in allocations
            ]

            return {
                "faculty_id": fac.faculty_id,
                "faculty_name": fac.faculty_name,
                "department_id": fac.department_id,
                "department_name": dept_name,
                "designation": fac.designation,
                "faculty_category": fac.faculty_category,
                "qualification": fac.qualification,
                "specialization": fac.specialization,
                "joining_date": fac.joining_date.isoformat() if fac.joining_date else None,
                "employment_status": fac.employment_status,
                "allocations": alloc_list
            }

    @classmethod
    def list_department_faculty(cls, user_context: UserContext, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List faculty members in a department (HOD/Admin only, scoped)."""
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You are not authorized to view department '{target_dept}'.")

        with get_db_session() as session:
            query = session.query(Faculty)
            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            faculty_list = query.all()
            return [
                {
                    "faculty_id": f.faculty_id,
                    "faculty_name": f.faculty_name,
                    "department_id": f.department_id,
                    "designation": f.designation,
                    "specialization": f.specialization,
                    "employment_status": f.employment_status
                }
                for f in faculty_list
            ]

