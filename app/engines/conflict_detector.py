"""
Timetable Conflict Detector.
Performs deterministic interval-based overlap detection for:
1. Faculty double bookings: same faculty member assigned to overlapping sessions.
2. Room conflicts: same room assigned to overlapping sessions.
3. Section conflicts: same section assigned to overlapping sessions.
4. Overlap condition: (Start_A < End_B) and (Start_B < End_A).
Excludes cancelled sessions.
"""

from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Timetable, Faculty, Section
from app.engines.workload_engine import DEFAULT_TARGET_WEEK


class ConflictDetector:
    @classmethod
    def detect_conflicts(
        cls,
        department_id: Optional[str] = None,
        week_start: Optional[date] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Detect timetable conflicts within a department or across the institution.
        """
        target_week = week_start or DEFAULT_TARGET_WEEK

        def _detect(db: Session) -> Dict[str, Any]:
            query = db.query(Timetable, Faculty.department_id).join(
                Faculty, Timetable.faculty_id == Faculty.faculty_id
            ).filter(
                Timetable.week_start == target_week,
                Timetable.status.in_(["Active", "Substituted"])
            )

            if department_id and department_id != "ALL":
                query = query.filter(Faculty.department_id == department_id)

            entries = query.all()
            records = []
            for tt, dept in entries:
                records.append({
                    "timetable_id": tt.timetable_id,
                    "faculty_id": tt.faculty_id,
                    "faculty_name": tt.faculty_name,
                    "department_id": dept,
                    "subject_id": tt.subject_id,
                    "section_id": tt.section_id,
                    "day": tt.day,
                    "start_time": tt.start_time,
                    "end_time": tt.end_time,
                    "room": tt.room,
                    "normalized_room": tt.normalized_room or tt.room,
                    "status": tt.status
                })

            faculty_conflicts = []
            room_conflicts = []
            section_conflicts = []

            n = len(records)
            for i in range(n):
                r1 = records[i]
                for j in range(i + 1, n):
                    r2 = records[j]

                    # Must be same day
                    if r1["day"] != r2["day"]:
                        continue

                    # Overlap interval: start1 < end2 and start2 < end1
                    if r1["start_time"] < r2["end_time"] and r2["start_time"] < r1["end_time"]:
                        # 1. Faculty conflict
                        if r1["faculty_id"] == r2["faculty_id"]:
                            faculty_conflicts.append({
                                "conflict_type": "FACULTY_DOUBLE_BOOKING",
                                "faculty_id": r1["faculty_id"],
                                "faculty_name": r1["faculty_name"],
                                "day": r1["day"],
                                "tt1": r1["timetable_id"],
                                "tt2": r2["timetable_id"],
                                "time1": f"{r1['start_time']}-{r1['end_time']}",
                                "time2": f"{r2['start_time']}-{r2['end_time']}",
                                "subject1": r1["subject_id"],
                                "subject2": r2["subject_id"]
                            })

                        # 2. Room conflict (check normalized room as well)
                        room1 = r1["normalized_room"]
                        room2 = r2["normalized_room"]
                        if room1 and room2 and room1 == room2:
                            room_conflicts.append({
                                "conflict_type": "ROOM_DOUBLE_BOOKING",
                                "room": room1,
                                "raw_room1": r1["room"],
                                "raw_room2": r2["room"],
                                "day": r1["day"],
                                "tt1": r1["timetable_id"],
                                "tt2": r2["timetable_id"],
                                "time1": f"{r1['start_time']}-{r1['end_time']}",
                                "time2": f"{r2['start_time']}-{r2['end_time']}",
                                "faculty1": r1["faculty_name"],
                                "faculty2": r2["faculty_name"],
                                "subject1": r1["subject_id"],
                                "subject2": r2["subject_id"]
                            })

                        # 3. Section conflict
                        if r1["section_id"] == r2["section_id"]:
                            section_conflicts.append({
                                "conflict_type": "SECTION_DOUBLE_BOOKING",
                                "section_id": r1["section_id"],
                                "day": r1["day"],
                                "tt1": r1["timetable_id"],
                                "tt2": r2["timetable_id"],
                                "time1": f"{r1['start_time']}-{r1['end_time']}",
                                "time2": f"{r2['start_time']}-{r2['end_time']}",
                                "subject1": r1["subject_id"],
                                "subject2": r2["subject_id"]
                            })

            return {
                "department_scope": department_id or "ALL",
                "week_start": target_week.isoformat(),
                "total_sessions_analyzed": n,
                "faculty_conflicts_count": len(faculty_conflicts),
                "room_conflicts_count": len(room_conflicts),
                "section_conflicts_count": len(section_conflicts),
                "faculty_conflicts": faculty_conflicts,
                "room_conflicts": room_conflicts,
                "section_conflicts": section_conflicts,
                "has_conflicts": (len(faculty_conflicts) + len(room_conflicts) + len(section_conflicts)) > 0
            }

        if session:
            return _detect(session)
        with get_db_session() as db:
            return _detect(db)

