"""
Workload Service.
Coordinates deterministic workload calculation and policy evaluation across individuals,
departments, and the entire institution, strictly enforcing RBAC scopes.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Faculty, Department
from app.security.access_control import UserContext, AccessDeniedError
from app.engines.workload_engine import WorkloadEngine, DEFAULT_TARGET_WEEK
from app.engines.policy_validator import PolicyValidator


class WorkloadService:
    @classmethod
    def get_faculty_workload(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get full workload calculation and policy validation for a single faculty member.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID provided or authenticated.")

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view workload records for faculty '{target_fid}'.")

            return PolicyValidator.evaluate_faculty_workload(target_fid, week_start, session)

    @classmethod
    def get_department_workload_summary(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None,
        week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Department-level workload summary and distribution.
        - HOD: only their department_scope.
        - ADMIN: any department.
        - FACULTY: denied.
        """
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You are not authorized to view workload for department '{target_dept}'.")

        target_week = week_start or DEFAULT_TARGET_WEEK

        with get_db_session() as session:
            query = session.query(Faculty)
            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            faculty_members = query.all()
            summaries = []
            total_hours = 0.0
            violations = []

            for f in faculty_members:
                status = PolicyValidator.evaluate_faculty_workload(f.faculty_id, target_week, session)
                summaries.append(status)
                total_hours += status["actual_teaching_hours"]
                if status["is_violation"]:
                    violations.append(status)

            avg_hours = (total_hours / len(faculty_members)) if faculty_members else 0.0

            return {
                "department_id": target_dept,
                "week_start": target_week.isoformat(),
                "faculty_count": len(faculty_members),
                "total_scheduled_hours": total_hours,
                "average_hours_per_faculty": round(avg_hours, 2),
                "violation_count": len(violations),
                "violations": violations,
                "faculty_workloads": summaries
            }

    @classmethod
    def get_policy_violations(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None,
        week_start: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        List faculty members who exceed their effective maximum teaching hours.
        """
        summary = cls.get_department_workload_summary(user_context, department_id, week_start)
        return summary["violations"]

    @classmethod
    def get_institutional_workload(
        cls,
        user_context: UserContext,
        week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Institution-wide workload analytics across all departments (Admin only).
        """
        if not user_context.is_admin():
            raise AccessDeniedError("Access Denied: Institution-wide workload analysis requires ADMIN privileges.")

        target_week = week_start or DEFAULT_TARGET_WEEK

        with get_db_session() as session:
            departments = session.query(Department).all()
            dept_reports = []
            highest_dept = None
            max_hours = -1.0
            total_inst_hours = 0.0

            for d in departments:
                dept_sum = cls.get_department_workload_summary(user_context, d.department_id, target_week)
                dept_reports.append(dept_sum)
                total_inst_hours += dept_sum["total_scheduled_hours"]
                if dept_sum["total_scheduled_hours"] > max_hours:
                    max_hours = dept_sum["total_scheduled_hours"]
                    highest_dept = {
                        "department_id": d.department_id,
                        "department_name": d.department_name,
                        "total_scheduled_hours": dept_sum["total_scheduled_hours"]
                    }

            return {
                "week_start": target_week.isoformat(),
                "institution_total_hours": total_inst_hours,
                "department_count": len(departments),
                "highest_workload_department": highest_dept,
                "departments": dept_reports
            }

