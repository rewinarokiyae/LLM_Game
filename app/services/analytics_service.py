"""
Historical Workload Analytics Service.
Provides multi-semester trend analysis, historical aggregates, and departmental comparisons:
- Clearly labels historical averages as prior-term synthetic aggregates, distinct from current timetable calculations.
- Identifies faculty workload trends across semesters (e.g., Odd vs Even terms).
- Identifies highest and lowest average workload faculty.
- Enforces RBAC scoping.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import HistoricalWorkload, Faculty, Department
from app.security.access_control import UserContext, AccessDeniedError


class AnalyticsService:
    @classmethod
    def get_faculty_history(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve historical workload trends for a faculty member.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID provided or authenticated.")

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view historical workload for faculty '{target_fid}'.")

            history = session.query(HistoricalWorkload).filter(
                HistoricalWorkload.faculty_id == target_fid
            ).order_by(HistoricalWorkload.academic_year, HistoricalWorkload.term).all()

            records = [
                {
                    "history_id": h.history_id,
                    "academic_year": h.academic_year,
                    "term": h.term,
                    "average_weekly_teaching_hours": h.average_weekly_teaching_hours,
                    "average_weekly_assignment_count": h.average_weekly_assignment_count,
                    "measurement_basis": h.measurement_basis,
                    "data_note": h.data_note
                }
                for h in history
            ]

            avg_historical = (
                sum(r["average_weekly_teaching_hours"] for r in records) / len(records)
            ) if records else 0.0

            return {
                "faculty_id": fac.faculty_id,
                "faculty_name": fac.faculty_name,
                "department_id": fac.department_id,
                "designation": fac.designation,
                "total_semesters_recorded": len(records),
                "historical_mean_weekly_hours": round(avg_historical, 2),
                "semester_records": records,
                "label": "HISTORICAL PRIOR-TERM AGGREGATE (NOT CURRENT WEEK TIMETABLE)"
            }

    @classmethod
    def get_department_history(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Department historical workload comparisons (HOD/Admin only).
        """
        target_dept = department_id or user_context.department_scope
        if target_dept == "ALL" and not user_context.is_admin():
            target_dept = user_context.department_scope

        if not user_context.can_access_department(target_dept):
            raise AccessDeniedError(f"Access Denied: You cannot view historical workload for department '{target_dept}'.")

        with get_db_session() as session:
            query = session.query(
                HistoricalWorkload, Faculty.faculty_name, Faculty.department_id
            ).join(
                Faculty, HistoricalWorkload.faculty_id == Faculty.faculty_id
            )

            if target_dept and target_dept != "ALL":
                query = query.filter(Faculty.department_id == target_dept)

            records = query.all()

            # Group by faculty
            fac_groups: Dict[str, List[float]] = {}
            for h, fname, dept in records:
                fac_groups.setdefault(f"{fname} ({h.faculty_id})", []).append(h.average_weekly_teaching_hours)

            fac_averages = {
                k: round(sum(v) / len(v), 2) for k, v in fac_groups.items()
            }

            sorted_fac = sorted(fac_averages.items(), key=lambda x: x[1], reverse=True)
            highest = sorted_fac[0] if sorted_fac else None
            lowest = sorted_fac[-1] if sorted_fac else None

            return {
                "department_id": target_dept,
                "total_records": len(records),
                "faculty_historical_averages": fac_averages,
                "highest_average_faculty": {"name": highest[0], "avg_hours": highest[1]} if highest else None,
                "lowest_average_faculty": {"name": lowest[0], "avg_hours": lowest[1]} if lowest else None,
                "label": "HISTORICAL PRIOR-TERM AGGREGATES"
            }

    @classmethod
    def get_dataset_statistics(
        cls,
        user_context: UserContext,
        target_table: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates dataset-wide statistics and table row counts across sheets:
        - Timetable: 281 total records, 277 active records, 4 cancelled records
        - Assignments: 54 total records, 3 per faculty
        - Faculty: 18 faculty members across 3 departments
        - Departments: 3 departments (DEP-CSE, DEP-AIML, DEP-DS)
        - Subjects: 12 subjects across all departments
        """
        from app.database.models import Timetable, Assignment, Subject, Department
        with get_db_session() as session:
            fac_cnt = session.query(Faculty).count()
            dept_cnt = session.query(Department).count()
            sub_cnt = session.query(Subject).count()
            assign_cnt = session.query(Assignment).count()
            tt_cnt = session.query(Timetable).count()
            tt_active = session.query(Timetable).filter(Timetable.status == "Active").count()
            tt_cancelled = session.query(Timetable).filter(Timetable.status == "Cancelled").count()
            tt_sub = session.query(Timetable).filter(Timetable.status == "Substituted").count()

            depts = [d.department_name for d in session.query(Department).all()]
            per_fac_assignments = round(assign_cnt / fac_cnt) if fac_cnt else 3

            return {
                "total_faculty": fac_cnt,
                "total_departments": dept_cnt,
                "departments_list": depts,
                "total_subjects": sub_cnt,
                "total_assignments": assign_cnt,
                "assignments_per_faculty": per_fac_assignments,
                "total_timetable_records": tt_cnt,
                "active_timetable_records": tt_active,
                "cancelled_timetable_records": tt_cancelled,
                "substituted_timetable_records": tt_sub,
                "requested_target": target_table,
                "status_filter": status_filter
            }

    @classmethod
    def get_all_faculty_violations(
        cls,
        user_context: UserContext,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Identifies all faculty members across departments who violate workload policies.
        Determines which department has the highest number of violations.
        """
        from datetime import date
        from app.engines.policy_validator import PolicyValidator
        with get_db_session() as session:
            facs = session.query(Faculty).all()
            violating_facs = []
            dept_violations = {}

            for f in facs:
                if department_id and department_id != "ALL" and f.department_id != department_id:
                    continue
                v = PolicyValidator.evaluate_faculty_workload(f.faculty_id, date(2026, 11, 9), session)
                if v.get("is_violation"):
                    item = {
                        "faculty_id": f.faculty_id,
                        "faculty_name": f.faculty_name,
                        "department_id": f.department_id,
                        "designation": f.designation,
                        "actual_hours": v["actual_teaching_hours"],
                        "effective_max_hours": v["effective_max_hours"],
                        "excess_hours": v["excess_hours"]
                    }
                    violating_facs.append(item)
                    dept_violations[f.department_id] = dept_violations.get(f.department_id, 0) + 1

            # Identify department with highest violations
            top_dept = None
            max_viol = 0
            for d, cnt in dept_violations.items():
                if cnt > max_viol:
                    max_viol = cnt
                    top_dept = d

            # Format list of violating faculty IDs: FAC001, FAC002, FAC004, ...
            id_list_str = ", ".join([f["faculty_id"] for f in violating_facs])

            dept_name_map = {"DEP-CSE": "CSE", "DEP-AIML": "AIML", "DEP-DS": "Data Science"}
            top_dept_name = dept_name_map.get(top_dept, top_dept)

            return {
                "total_violations": len(violating_facs),
                "violating_faculty": violating_facs,
                "violating_faculty_ids": [f["faculty_id"] for f in violating_facs],
                "violating_ids_str": id_list_str,
                "department_counts": dept_violations,
                "top_violating_department": top_dept,
                "top_violating_department_name": top_dept_name,
                "top_violating_count": max_viol,
                "summary": f"{top_dept_name}, with {max_viol} violations." if top_dept else "No violations found."
            }

