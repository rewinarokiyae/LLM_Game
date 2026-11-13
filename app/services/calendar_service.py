"""
Academic Calendar Service.
Provides event lookup, teaching week confirmation, assessment and holiday schedules.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import AcademicCalendar


class CalendarService:
    @classmethod
    def get_events(
        cls,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            query = session.query(AcademicCalendar)

            if start_date and end_date:
                query = query.filter(
                    AcademicCalendar.start_date <= end_date,
                    AcademicCalendar.end_date >= start_date
                )
            elif start_date:
                query = query.filter(AcademicCalendar.end_date >= start_date)

            if event_type:
                query = query.filter(AcademicCalendar.event_type.ilike(f"%{event_type.strip()}%"))

            events = query.order_by(AcademicCalendar.start_date).all()
            return [
                {
                    "calendar_event_id": e.calendar_event_id,
                    "event_name": e.event_name,
                    "event_type": e.event_type,
                    "start_date": e.start_date.isoformat(),
                    "end_date": e.end_date.isoformat(),
                    "description": e.description,
                    "scope": e.scope
                }
                for e in events
            ]

    @classmethod
    def is_teaching_day(cls, target_date: date) -> Dict[str, Any]:
        """Check if a specific date falls in a Teaching week vs Holiday or Assessment."""
        with get_db_session() as session:
            events = session.query(AcademicCalendar).filter(
                AcademicCalendar.start_date <= target_date,
                AcademicCalendar.end_date >= target_date
            ).all()

            if not events:
                return {
                    "date": target_date.isoformat(),
                    "is_teaching_day": False,
                    "message": "No specific academic event listed for this date."
                }

            teaching_events = [e for e in events if e.event_type.lower() == "teaching"]
            holiday_events = [e for e in events if e.event_type.lower() in ["holiday", "vacation"]]

            return {
                "date": target_date.isoformat(),
                "is_teaching_day": len(teaching_events) > 0 and len(holiday_events) == 0,
                "events": [{"name": e.event_name, "type": e.event_type} for e in events]
            }

