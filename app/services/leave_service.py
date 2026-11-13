"""
Leave and Availability Service.
Handles tracking of faculty leave records and availability status:
- Confirmed absence: ONLY Approved leave records are treated as confirmed leave.
- Pending or Rejected leave records are explicitly flagged and not counted as confirmed absence.
- Identification of substitute teaching arrangements for approved leaves.
- Scope enforcement: Faculty can only view own leave; HOD views department; Admin views all.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import LeaveRecord, Faculty, FacultyAvailability, Timetable
from app.security.access_control import UserContext, AccessDeniedError
from app.engines.workload_engine import DEFAULT_TARGET_WEEK


class LeaveService:
    @classmethod
    def get_faculty_leave(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        approval_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get leave records for a faculty member.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID provided or authenticated.")

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view leave records for faculty '{target_fid}'.")

            query = session.query(LeaveRecord).filter(LeaveRecord.faculty_id == target_fid)
            if approval_status:
                query = query.filter(LeaveRecord.approval_status.ilike(approval_status.strip()))

            records = query.order_by(LeaveRecord.start_date).all()
            results = []
            for r in records:
                rep_name = None
                if r.replacement_faculty_id:
                    rep = session.query(Faculty).filter(Faculty.faculty_id == r.replacement_faculty_id).first()
                    rep_name = rep.faculty_name if rep else r.replacement_faculty_id

                results.append({
                    "leave_id": r.leave_id,
                    "leave_type": r.leave_type,
                    "start_date": r.start_date.isoformat(),
                    "end_date": r.end_date.isoformat(),
                    "approval_status": r.approval_status,
                    "is_confirmed": r.approval_status == "Approved",
                    "replacement_faculty_id": r.replacement_faculty_id,
                    "replacement_faculty_name": rep_name,
                    "reason": r.reason,
                    "approved_by": r.approved_by
                })

            return results

    @classmethod
    def get_department_leave(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None,
        week_start: Optional[date] = None,
        approved_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get leave records across a department for a target week (HOD/Admin only).
        """
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You cannot view leave records for department '{target_dept}'.")

        target_week = week_start or DEFAULT_TARGET_WEEK
        week_end = date(target_week.year, target_week.month, target_week.day + 4)

        with get_db_session() as session:
            query = session.query(LeaveRecord, Faculty.faculty_name, Faculty.department_id).join(
                Faculty, LeaveRecord.faculty_id == Faculty.faculty_id
            )

            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            if approved_only:
                query = query.filter(LeaveRecord.approval_status == "Approved")

            # Date overlap check: start_date <= week_end and end_date >= week_start
            query = query.filter(
                LeaveRecord.start_date <= week_end,
                LeaveRecord.end_date >= target_week
            )

            records = query.all()
            results = []
            for r, fname, dept in records:
                rep_name = None
                if r.replacement_faculty_id:
                    rep = session.query(Faculty).filter(Faculty.faculty_id == r.replacement_faculty_id).first()
                    rep_name = rep.faculty_name if rep else r.replacement_faculty_id

                results.append({
                    "leave_id": r.leave_id,
                    "faculty_id": r.faculty_id,
                    "faculty_name": fname,
                    "department_id": dept,
                    "leave_type": r.leave_type,
                    "start_date": r.start_date.isoformat(),
                    "end_date": r.end_date.isoformat(),
                    "approval_status": r.approval_status,
                    "is_confirmed": r.approval_status == "Approved",
                    "replacement_faculty_id": r.replacement_faculty_id,
                    "replacement_faculty_name": rep_name,
                    "reason": r.reason
                })

            return results

    @classmethod
    def search_leaves(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        department_id: Optional[str] = None,
        target_date: Optional[date] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        approval_status: Optional[str] = None,
        leave_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Versatile search across leave records with flexible temporal and status filters.
        """
        with get_db_session() as session:
            query = session.query(LeaveRecord, Faculty.faculty_name, Faculty.department_id).join(
                Faculty, LeaveRecord.faculty_id == Faculty.faculty_id
            )

            # Faculty filter
            if faculty_id:
                query = query.filter(LeaveRecord.faculty_id == faculty_id)

            # Department filter
            target_dept = department_id or user_context.department_scope
            if target_dept and target_dept != "ALL":
                if not user_context.can_access_department(target_dept) and not user_context.is_admin():
                    raise AccessDeniedError(f"Access Denied: You cannot view leave records for department '{target_dept}'.")
                query = query.filter(Faculty.department_id == target_dept)

            # Status filter (Approved, Pending, Rejected)
            if approval_status:
                query = query.filter(LeaveRecord.approval_status.ilike(approval_status.strip()))

            # Leave type filter (Medical, Casual, Official Duty, Earned)
            if leave_type:
                query = query.filter(LeaveRecord.leave_type.ilike(f"%{leave_type.strip()}%"))

            # Specific date filter
            if target_date:
                query = query.filter(
                    LeaveRecord.start_date <= target_date,
                    LeaveRecord.end_date >= target_date
                )
            elif month:
                target_year = year or 2026
                # Month overlap check
                next_m = 1 if month == 12 else month + 1
                next_y = target_year + 1 if month == 12 else target_year
                m_start = date(target_year, month, 1)
                m_end = date(next_y, next_m, 1)
                query = query.filter(
                    LeaveRecord.start_date < m_end,
                    LeaveRecord.end_date >= m_start
                )

            records = query.order_by(LeaveRecord.start_date).all()
            results = []
            for r, fname, dept in records:
                rep_name = None
                if r.replacement_faculty_id:
                    rep = session.query(Faculty).filter(Faculty.faculty_id == r.replacement_faculty_id).first()
                    rep_name = rep.faculty_name if rep else r.replacement_faculty_id

                results.append({
                    "leave_id": r.leave_id,
                    "faculty_id": r.faculty_id,
                    "faculty_name": fname,
                    "department_id": dept,
                    "leave_type": r.leave_type,
                    "start_date": r.start_date.isoformat(),
                    "end_date": r.end_date.isoformat(),
                    "approval_status": r.approval_status,
                    "is_confirmed": r.approval_status == "Approved",
                    "replacement_faculty_id": r.replacement_faculty_id,
                    "replacement_faculty_name": rep_name,
                    "reason": r.reason
                })

            return results

