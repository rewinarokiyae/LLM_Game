"""
Policy Exception Service.
Handles temporary maximum limit overrides:
- Identifies Approved, Pending, and Rejected exceptions.
- Emphasizes that ONLY Approved exceptions override policy caps during their valid date window.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import PolicyException, Faculty
from app.security.access_control import UserContext, AccessDeniedError


class ExceptionService:
    @classmethod
    def get_faculty_exceptions(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID provided or authenticated.")

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view exceptions for faculty '{target_fid}'.")

            exceptions = session.query(PolicyException).filter(
                PolicyException.faculty_id == target_fid
            ).all()

            return [
                {
                    "exception_id": ex.exception_id,
                    "policy_id": ex.policy_id,
                    "max_hours_override": ex.max_hours_override,
                    "approval_status": ex.approval_status,
                    "is_approved_and_active": ex.approval_status == "Approved",
                    "valid_from": ex.valid_from.isoformat(),
                    "valid_to": ex.valid_to.isoformat(),
                    "reason": ex.reason,
                    "approved_by": ex.approved_by,
                    "notes": ex.notes
                }
                for ex in exceptions
            ]

    @classmethod
    def list_all_exceptions(
        cls,
        user_context: UserContext,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List exceptions institution-wide (Admin/HOD)."""
        if not user_context.is_admin() and not user_context.is_hod():
            raise AccessDeniedError("Access Denied: Only HODs or Administrators can view department/institutional exceptions.")

        with get_db_session() as session:
            query = session.query(PolicyException, Faculty.faculty_name, Faculty.department_id).join(
                Faculty, PolicyException.faculty_id == Faculty.faculty_id
            )

            if user_context.is_hod() and user_context.department_scope != "ALL":
                query = query.filter(Faculty.department_id == user_context.department_scope)

            if status_filter:
                query = query.filter(PolicyException.approval_status.ilike(status_filter.strip()))

            records = query.all()
            return [
                {
                    "exception_id": ex.exception_id,
                    "faculty_id": ex.faculty_id,
                    "faculty_name": fname,
                    "department_id": dept,
                    "policy_id": ex.policy_id,
                    "max_hours_override": ex.max_hours_override,
                    "approval_status": ex.approval_status,
                    "valid_from": ex.valid_from.isoformat(),
                    "valid_to": ex.valid_to.isoformat(),
                    "reason": ex.reason,
                    "approved_by": ex.approved_by,
                    "notes": ex.notes
                }
                for ex, fname, dept in records
            ]

