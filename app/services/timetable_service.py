"""
Timetable Service.
Provides queries for faculty schedules, daily timetables, cancelled and substituted sessions,
room allocations, and free period detection with RBAC scoping.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Timetable, Faculty, Subject, Room
from app.security.access_control import UserContext, AccessDeniedError
from app.engines.workload_engine import DEFAULT_TARGET_WEEK


class TimetableService:
    @classmethod
    def get_faculty_timetable(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        day: Optional[str] = None,
        week_start: Optional[date] = None,
        include_cancelled: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve timetable sessions for a faculty member.
        - FACULTY: only their own timetable (defaults to user_context.faculty_id).
        - HOD: faculty within their department.
        - ADMIN: any faculty.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID specified or associated with user context.")

        target_week = week_start or DEFAULT_TARGET_WEEK

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You are not authorized to view timetable for faculty '{target_fid}'.")

            query = session.query(Timetable, Subject.subject_name).join(
                Subject, Timetable.subject_id == Subject.subject_id
            ).filter(
                Timetable.faculty_id == target_fid,
                Timetable.week_start == target_week
            )

            if day:
                query = query.filter(Timetable.day.ilike(day.strip()))

            if not include_cancelled:
                query = query.filter(Timetable.status != "Cancelled")

            # Sort chronologically by start_time
            sessions = query.order_by(Timetable.day, Timetable.start_time).all()

            results = []
            for tt, sub_name in sessions:
                results.append({
                    "timetable_id": tt.timetable_id,
                    "day": tt.day,
                    "start_time": tt.start_time,
                    "end_time": tt.end_time,
                    "duration_hours": tt.duration_hours,
                    "subject_id": tt.subject_id,
                    "subject_name": sub_name,
                    "section_id": tt.section_id,
                    "session_type": tt.session_type,
                    "room": tt.room,
                    "normalized_room": tt.normalized_room,
                    "status": tt.status,
                    "substitute_for_faculty_id": tt.substitute_for_faculty_id,
                    "substitution_of_timetable_id": tt.substitution_of_timetable_id
                })

            return {
                "faculty_id": fac.faculty_id,
                "faculty_name": fac.faculty_name,
                "department_id": fac.department_id,
                "week_start": target_week.isoformat(),
                "day_filter": day,
                "session_count": len(results),
                "sessions": results
            }

    @classmethod
    def get_cancelled_and_substituted(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify cancelled sessions and their substitute allocations.
        """
        target_fid = faculty_id or user_context.faculty_id
        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view substitution records for faculty '{target_fid}'.")

            # Find cancelled sessions for target_fid
            cancelled = session.query(Timetable).filter(
                Timetable.faculty_id == target_fid,
                Timetable.status == "Cancelled"
            ).all()

            reports = []
            for c in cancelled:
                # Find matching substitution row
                sub = session.query(Timetable, Faculty.faculty_name).join(
                    Faculty, Timetable.faculty_id == Faculty.faculty_id
                ).filter(
                    Timetable.substitution_of_timetable_id == c.timetable_id
                ).first()

                sub_fac_name = sub[1] if sub else None
                sub_fac_id = sub[0].faculty_id if sub else None
                sub_tt_id = sub[0].timetable_id if sub else None

                reports.append({
                    "cancelled_timetable_id": c.timetable_id,
                    "subject_id": c.subject_id,
                    "section_id": c.section_id,
                    "day": c.day,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "room": c.room,
                    "original_faculty_id": c.faculty_id,
                    "original_faculty_name": fac.faculty_name,
                    "cancellation_reason": c.substitution_of_timetable_id,
                    "substitute_faculty_id": sub_fac_id,
                    "substitute_faculty_name": sub_fac_name,
                    "substitute_timetable_id": sub_tt_id,
                    "substitution_status": "Substituted" if sub else "Unassigned Substitute"
                })

            return reports

    @classmethod
    def get_free_faculty(
        cls,
        user_context: UserContext,
        day: str,
        start_time: str,
        end_time: str,
        department_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify faculty members who have no scheduled teaching during a specified slot.
        """
        target_dept = department_id or user_context.department_scope
        if not user_context.can_access_department(target_dept) and not user_context.is_admin():
            raise AccessDeniedError(f"Access Denied: You cannot query free faculty for department '{target_dept}'.")

        with get_db_session() as session:
            # All faculty in department
            fac_query = session.query(Faculty)
            if target_dept and target_dept != "ALL":
                fac_query = fac_query.filter(Faculty.department_id == target_dept)
            all_faculty = fac_query.all()

            # Busy faculty in slot: start1 < end2 and start2 < end1
            busy_query = session.query(Timetable.faculty_id).filter(
                Timetable.day.ilike(day.strip()),
                Timetable.status.in_(["Active", "Substituted"]),
                Timetable.start_time < end_time,
                start_time < Timetable.end_time
            )
            busy_ids = {row[0] for row in busy_query.all()}

            free_list = []
            for f in all_faculty:
                if f.faculty_id not in busy_ids:
                    free_list.append({
                        "faculty_id": f.faculty_id,
                        "faculty_name": f.faculty_name,
                        "department_id": f.department_id,
                        "designation": f.designation
                    })
            return free_list

    @classmethod
    def get_next_class(
        cls,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        reference_day: Optional[str] = "Wednesday",
        reference_time: Optional[str] = "09:30"
    ) -> Dict[str, Any]:
        """
        Identify the next scheduled class for a faculty member after reference_time on reference_day
        or on upcoming days of the active week.
        """
        target_fid = faculty_id or user_context.faculty_id
        if not target_fid:
            raise ValueError("No faculty ID specified.")

        with get_db_session() as session:
            fac = session.query(Faculty).filter(Faculty.faculty_id == target_fid).first()
            if not fac:
                raise ValueError(f"Faculty with ID '{target_fid}' not found.")

            if not user_context.can_access_faculty(fac.faculty_id, fac.department_id):
                raise AccessDeniedError(f"Access Denied: You cannot view timetable for faculty '{target_fid}'.")

            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            ref_day = reference_day.capitalize() if reference_day else "Wednesday"
            ref_t = reference_time or "09:30"

            # 1. Check sessions today after reference_time
            today_query = session.query(Timetable, Subject.subject_name).join(
                Subject, Timetable.subject_id == Subject.subject_id
            ).filter(
                Timetable.faculty_id == target_fid,
                Timetable.day.ilike(ref_day),
                Timetable.status.in_(["Active", "Substituted"]),
                Timetable.start_time >= ref_t
            ).order_by(Timetable.start_time)

            next_session = today_query.first()
            if next_session:
                tt, sub_name = next_session
                return {
                    "has_next_class": True,
                    "faculty_id": fac.faculty_id,
                    "faculty_name": fac.faculty_name,
                    "day": tt.day,
                    "date": "2026-11-11",
                    "start_time": tt.start_time,
                    "end_time": tt.end_time,
                    "duration_hours": tt.duration_hours,
                    "subject_id": tt.subject_id,
                    "subject_name": sub_name,
                    "section_id": tt.section_id,
                    "session_type": tt.session_type,
                    "room": tt.room,
                    "is_today": True
                }

            # 2. Check subsequent days in the week
            if ref_day in day_order:
                curr_idx = day_order.index(ref_day)
                for d in day_order[curr_idx + 1:]:
                    sub_query = session.query(Timetable, Subject.subject_name).join(
                        Subject, Timetable.subject_id == Subject.subject_id
                    ).filter(
                        Timetable.faculty_id == target_fid,
                        Timetable.day.ilike(d),
                        Timetable.status.in_(["Active", "Substituted"])
                    ).order_by(Timetable.start_time)
                    sub_session = sub_query.first()
                    if sub_session:
                        tt, sub_name = sub_session
                        return {
                            "has_next_class": True,
                            "faculty_id": fac.faculty_id,
                            "faculty_name": fac.faculty_name,
                            "day": tt.day,
                            "date": None,
                            "start_time": tt.start_time,
                            "end_time": tt.end_time,
                            "duration_hours": tt.duration_hours,
                            "subject_id": tt.subject_id,
                            "subject_name": sub_name,
                            "section_id": tt.section_id,
                            "session_type": tt.session_type,
                            "room": tt.room,
                            "is_today": False
                        }

            return {
                "has_next_class": False,
                "faculty_id": fac.faculty_id,
                "faculty_name": fac.faculty_name,
                "message": "No upcoming classes found for the remainder of this academic week."
            }

    @classmethod
    def get_section_timetable(
        cls,
        user_context: UserContext,
        section_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve timetable for an entire section (e.g. CSE-S5-A).
        """
        with get_db_session() as session:
            query = session.query(Timetable, Subject.subject_name, Faculty.faculty_name).join(
                Subject, Timetable.subject_id == Subject.subject_id
            ).join(
                Faculty, Timetable.faculty_id == Faculty.faculty_id
            ).filter(
                Timetable.section_id.ilike(section_id.strip()),
                Timetable.status.in_(["Active", "Substituted"])
            ).order_by(Timetable.day, Timetable.start_time)

            rows = query.all()
            sessions = []
            for tt, sub_name, fac_name in rows:
                sessions.append({
                    "day": tt.day,
                    "start_time": tt.start_time,
                    "end_time": tt.end_time,
                    "duration_hours": tt.duration_hours,
                    "subject_id": tt.subject_id,
                    "subject_name": sub_name,
                    "faculty_id": tt.faculty_id,
                    "faculty_name": fac_name,
                    "session_type": tt.session_type,
                    "room": tt.room,
                    "section_id": tt.section_id
                })

            return {
                "section_id": section_id,
                "session_count": len(sessions),
                "sessions": sessions
            }


