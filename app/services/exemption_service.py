"""
Workload Exemption Service.
Provides lookup and management of administrative workload exemptions (teaching relief hours):
- Relief reduces minimum expected hours; does NOT raise maximum cap.
- Enforces validity dates and approval status (Approved vs Pending vs Rejected).
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import WorkloadExemption, Faculty
from app.security.access_control import UserContext, AccessDeniedError


class ExemptionService:
    @classmethod
    def get_faculty_exemptions(
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
                raise AccessDeniedError(f"Access Denied: You cannot view exemptions for faculty '{target_fid}'.")

            exemptions = session.query(WorkloadExemption).filter(
                WorkloadExemption.faculty_id == target_fid
            ).all()

            return [
                {
                    "exemption_id": e.exemption_id,
                    "responsibility": e.responsibility,
                    "relief_hours_per_week": e.relief_hours_per_week,
                    "period": e.period,
                    "approval_status": e.approval_status,
                    "valid_from": e.valid_from.isoformat(),
                    "valid_to": e.valid_to.isoformat(),
                    "reason": e.reason,
                    "approved_by": e.approved_by
                }
                for e in exemptions
            ]

    @classmethod
    def get_department_exemptions(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None,
        approved_only: bool = True
    ) -> List[Dict[str, Any]]:
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You cannot view exemptions for department '{target_dept}'.")

        with get_db_session() as session:
            query = session.query(WorkloadExemption, Faculty.faculty_name, Faculty.department_id).join(
                Faculty, WorkloadExemption.faculty_id == Faculty.faculty_id
            )

            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            if approved_only:
                query = query.filter(WorkloadExemption.approval_status == "Approved")

            records = query.all()
            return [
                {
                    "exemption_id": e.exemption_id,
                    "faculty_id": e.faculty_id,
                    "faculty_name": fname,
                    "department_id": dept,
                    "responsibility": e.responsibility,
                    "relief_hours_per_week": e.relief_hours_per_week,
                    "approval_status": e.approval_status,
                    "valid_from": e.valid_from.isoformat(),
                    "valid_to": e.valid_to.isoformat(),
                    "reason": e.reason,
                    "approved_by": e.approved_by
                }
                for e, fname, dept in records
            ]

