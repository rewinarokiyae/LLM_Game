"""
Subject Information Service.
Provides bidirectional lookup between subject codes and subject names, departments, semesters, and credits:
- CS501 -> Operating Systems (DEP-CSE, Semester 5, Credits 3)
- AI501 -> Machine Learning (DEP-AIML, Semester 5, Credits 4)
- DS503 -> Data Visualization (DEP-DS, Semester 7, Credits 4)
- AI504 -> Computer Vision (DEP-AIML, Semester 7, Credits 4)
- CS503 -> Database Systems (DEP-CSE, Semester 7, Credits 4)
"""

from typing import Dict, Any, List, Optional
from app.database.connection import get_db_session
from app.database.models import Subject, Department, Timetable, Faculty


class SubjectService:
    DEPARTMENT_NAMES = {
        "DEP-CSE": "Computer Science and Engineering (CSE)",
        "DEP-AIML": "Artificial Intelligence and Machine Learning (AIML)",
        "DEP-DS": "Data Science"
    }

    @classmethod
    def get_subject_details(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Lookup subject by ID (e.g. 'CS501') or name (e.g. 'Operating Systems').
        """
        clean_id = identifier.strip().upper()
        with get_db_session() as session:
            # 1. Try exact subject_id
            sub = session.query(Subject).filter(Subject.subject_id == clean_id).first()
            if not sub:
                # 2. Try subject_name partial match
                sub = session.query(Subject).filter(Subject.subject_name.ilike(f"%{identifier.strip()}%")).first()

            if not sub:
                return None

            dept_name = cls.DEPARTMENT_NAMES.get(sub.department_id, sub.department_id)

            # Query assigned faculty
            tts = session.query(Timetable, Faculty.faculty_name).join(
                Faculty, Timetable.faculty_id == Faculty.faculty_id
            ).filter(
                Timetable.subject_id == sub.subject_id,
                Timetable.status.in_(["Active", "Substituted"])
            ).all()

            instructors = {}
            for tt, fname in tts:
                instructors[tt.faculty_id] = fname

            return {
                "subject_id": sub.subject_id,
                "subject_name": sub.subject_name,
                "department_id": sub.department_id,
                "department_name": dept_name,
                "semester": f"Semester {sub.semester}",
                "semester_num": sub.semester,
                "credits": sub.credits,
                "instructors": instructors
            }

    @classmethod
    def get_all_subjects(cls) -> List[Dict[str, Any]]:
        """Retrieve all subjects across the university."""
        with get_db_session() as session:
            subs = session.query(Subject).order_by(Subject.subject_id).all()
            return [
                {
                    "subject_id": s.subject_id,
                    "subject_name": s.subject_name,
                    "department_id": s.department_id,
                    "department_name": cls.DEPARTMENT_NAMES.get(s.department_id, s.department_id),
                    "semester": f"Semester {s.semester}",
                    "credits": s.credits
                }
                for s in subs
            ]
