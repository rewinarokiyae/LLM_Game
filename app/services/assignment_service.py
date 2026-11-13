"""
Assignment Management Service.
Handles tracking of non-teaching academic responsibilities:
- Question Paper Preparation, Internal Assessment Evaluation, Project Supervision, Exam Invigilation.
- Filter by status: Pending, In Progress, Completed.
- Filter by priority, due date, deadlines, and overdue tasks.
- Enforces strict RBAC (Faculty only views own assignments).
- Assignments are kept separate from teaching-hour calculations.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Assignment, Faculty, Subject
from app.security.access_control import UserContext, AccessDeniedError


class AssignmentService:
    @classmethod
    def get_faculty_assignments(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        status: Optional[str] = None,
        assignment_type: Optional[str] = None,
        overdue_only: bool = False,
        reference_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Retrieve assignments for a faculty member.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID provided or authenticated.")

        ref_date = reference_date or date(2026, 11, 14)  # Default reference date within semester

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view assignments for faculty '{target_fid}'.")

            query = session.query(Assignment, Subject.subject_name).outerjoin(
                Subject, Assignment.subject_id == Subject.subject_id
            ).filter(Assignment.faculty_id == target_fid)

            if status:
                query = query.filter(Assignment.status.ilike(status.strip()))
            if assignment_type:
                query = query.filter(Assignment.assignment_type.ilike(f"%{assignment_type.strip()}%"))
            if overdue_only:
                query = query.filter(
                    Assignment.status.in_(["Pending", "In Progress"]),
                    Assignment.due_date < ref_date
                )

            records = query.order_by(Assignment.due_date).all()

            results = []
            for a, sname in records:
                is_overdue = (a.status in ["Pending", "In Progress"] and a.due_date < ref_date)
                results.append({
                    "assignment_id": a.assignment_id,
                    "assignment_type": a.assignment_type,
                    "subject_id": a.subject_id,
                    "subject_name": sname,
                    "description": a.description,
                    "assigned_date": a.assigned_date.isoformat(),
                    "due_date": a.due_date.isoformat(),
                    "status": a.status,
                    "priority": a.priority,
                    "is_overdue": is_overdue,
                    "assigned_by": a.assigned_by
                })

            counts_by_status = {}
            counts_by_type = {}
            for r in results:
                st = r["status"]
                tp = r["assignment_type"]
                counts_by_status[st] = counts_by_status.get(st, 0) + 1
                counts_by_type[tp] = counts_by_type.get(tp, 0) + 1

            return {
                "faculty_id": fac.faculty_id,
                "faculty_name": fac.faculty_name,
                "department_id": fac.department_id,
                "total_count": len(results),
                "counts_by_status": counts_by_status,
                "counts_by_type": counts_by_type,
                "assignments": results
            }

    @classmethod
    def get_department_assignments(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all assignments across a department (HOD/Admin only).
        """
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You cannot view assignments for department '{target_dept}'.")

        with get_db_session() as session:
            query = session.query(Assignment, Faculty.faculty_name, Subject.subject_name).join(
                Faculty, Assignment.faculty_id == Faculty.faculty_id
            ).outerjoin(
                Subject, Assignment.subject_id == Subject.subject_id
            )

            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            if status:
                query = query.filter(Assignment.status.ilike(status.strip()))

            records = query.order_by(Assignment.due_date).all()
            results = []
            for a, fname, sname in records:
                results.append({
                    "assignment_id": a.assignment_id,
                    "faculty_id": a.faculty_id,
                    "faculty_name": fname,
                    "assignment_type": a.assignment_type,
                    "subject_id": a.subject_id,
                    "subject_name": sname,
                    "due_date": a.due_date.isoformat(),
                    "status": a.status,
                    "priority": a.priority
                })

            return {
                "department_id": target_dept,
                "total_count": len(results),
                "assignments": results
            }

    @classmethod
    def get_all_assignments(
        cls,
        user_context: UserContext,
        status: Optional[str] = None,
        assignment_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all assignments across institution (Admin only).
        """
        if not user_context.is_admin():
            raise AccessDeniedError("Access Denied: University-wide assignment overview requires Admin role.")

        with get_db_session() as session:
            query = session.query(Assignment, Faculty.faculty_name, Subject.subject_name).join(
                Faculty, Assignment.faculty_id == Faculty.faculty_id
            ).outerjoin(
                Subject, Assignment.subject_id == Subject.subject_id
            )
            if status:
                query = query.filter(Assignment.status.ilike(status.strip()))
            if assignment_type:
                query = query.filter(Assignment.assignment_type.ilike(f"%{assignment_type.strip()}%"))

            records = query.order_by(Assignment.due_date).all()
            fac_cnt = session.query(Faculty).count()
            results = [
                {
                    "assignment_id": a.assignment_id,
                    "faculty_id": a.faculty_id,
                    "faculty_name": fname,
                    "assignment_type": a.assignment_type,
                    "subject_id": a.subject_id,
                    "subject_name": sname,
                    "due_date": a.due_date.isoformat(),
                    "status": a.status,
                    "priority": a.priority
                }
                for a, fname, sname in records
            ]
            return {
                "total_count": len(results),
                "total_faculty": fac_cnt,
                "assignments_per_faculty": round(len(results) / fac_cnt) if fac_cnt else 3,
                "assignments": results
            }

