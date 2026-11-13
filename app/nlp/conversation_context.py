"""
Conversation Context Tracking Engine.
Tracks multi-turn context, resolves follow-up queries, pronouns, and ellipses,
while strictly isolating unrelated new queries to prevent context bleeding.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re

from app.nlp.structured_query import (
    StructuredQuery, IntentEnum, QueryMetric, TimeGranularity, DateRange, RequestedOutput
)
from app.nlp.date_resolver import DateResolver, DAY_NAME_TO_OFFSET, REFERENCE_WEEK_START
from datetime import timedelta


class ConversationTurn(BaseModel):
    query: str
    structured_query: StructuredQuery
    response_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationContext:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.turns: List[ConversationTurn] = []
        self.active_faculty_id: Optional[str] = None
        self.active_faculty_name: Optional[str] = None
        self.active_day: Optional[str] = None
        self.active_date: Optional[date] = None
        self.active_date_range: Optional[DateRange] = None
        self.active_time_granularity: Optional[TimeGranularity] = None
        self.active_metric: Optional[QueryMetric] = None
        self.active_intent: Optional[IntentEnum] = None
        self.active_subject_id: Optional[str] = None

    def add_turn(self, query: str, structured_query: StructuredQuery, response_text: str):
        turn = ConversationTurn(
            query=query,
            structured_query=structured_query,
            response_text=response_text
        )
        self.turns.append(turn)

        # Update persistent conversational state
        if structured_query.faculty_id:
            self.active_faculty_id = structured_query.faculty_id
        if structured_query.faculty_name:
            self.active_faculty_name = structured_query.faculty_name
        if structured_query.day_of_week:
            self.active_day = structured_query.day_of_week
        if structured_query.date:
            self.active_date = structured_query.date
        if structured_query.date_range:
            self.active_date_range = structured_query.date_range
        if structured_query.time_granularity != TimeGranularity.UNSPECIFIED:
            self.active_time_granularity = structured_query.time_granularity
        if structured_query.metric:
            self.active_metric = structured_query.metric
        if structured_query.intent != IntentEnum.UNKNOWN_OR_AMBIGUOUS:
            self.active_intent = structured_query.intent
        if structured_query.subject_id:
            self.active_subject_id = structured_query.subject_id

    def resolve_follow_up(self, query: str, initial_sq: StructuredQuery) -> StructuredQuery:
        """
        Inspects query to detect if it is an ellipsis or follow-up referring to previous turns.
        """
        q = query.strip().lower()

        # Check if query is explicitly standalone
        # E.g., asks about departments, policies, institution, specific faculty
        is_standalone = any([
            "which department" in q,
            "department-wide" in q,
            "across all" in q,
            "who teaches" in q,
            "what is the policy for" in q,
            "show the timetable for section" in q,
            "rules for counting" in q,
            "data quality" in q,
            "/help" in q or q == "help"
        ])

        if is_standalone:
            return initial_sq

        # Follow-up Pattern 1: "What about Tuesday?" / "How about Friday?" / "And Monday?"
        day_match = re.search(r"^(?:what\s+about|how\s+about|and|what\s+of)\s+([a-z]+)\??$", q)
        if day_match:
            day_candidate = day_match.group(1).lower()
            if day_candidate in DAY_NAME_TO_OFFSET:
                offset = DAY_NAME_TO_OFFSET[day_candidate]
                target_date = REFERENCE_WEEK_START + timedelta(days=offset)
                
                # Inherit previous intent & metric (e.g. DAILY_WORKLOAD or DAILY_TIMETABLE)
                inherited_intent = self.active_intent or IntentEnum.DAILY_WORKLOAD
                if inherited_intent not in [IntentEnum.DAILY_WORKLOAD, IntentEnum.DAILY_TIMETABLE, IntentEnum.CLASS_COUNT]:
                    inherited_intent = IntentEnum.DAILY_WORKLOAD

                inherited_metric = self.active_metric or QueryMetric.TEACHING_HOURS
                req_out = RequestedOutput.TOTAL_HOURS if inherited_metric == QueryMetric.TEACHING_HOURS else RequestedOutput.TIMETABLE_SCHEDULE

                return StructuredQuery(
                    raw_query=query,
                    intent=inherited_intent,
                    metric=inherited_metric,
                    time_granularity=TimeGranularity.DAY,
                    date=target_date,
                    day_of_week=day_candidate.capitalize(),
                    date_range=DateRange(start=target_date, end=target_date + timedelta(days=1)),
                    faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                    requested_output=req_out,
                    confidence=0.98,
                    is_follow_up=True
                )

        # If initial query already has an explicit temporal expression (e.g. this week, on tuesday), it is standalone
        if initial_sq.time_granularity != TimeGranularity.UNSPECIFIED and (initial_sq.day_of_week or initial_sq.date or "week" in q or "month" in q):
            return initial_sq

        # Follow-up Pattern 2: "How many of those are lectures?" / "How many lectures?"
        if re.search(r"how\s+many\s+(?:of\s+those\s+are\s+)?lectures?", q) or "are lectures" in q:
            return StructuredQuery(
                raw_query=query,
                intent=IntentEnum.LECTURE_HOURS,
                metric=QueryMetric.LECTURE_HOURS,
                time_granularity=self.active_time_granularity or TimeGranularity.DAY,
                date=self.active_date,
                day_of_week=self.active_day,
                date_range=self.active_date_range,
                session_type="Lecture",
                faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.95,
                is_follow_up=True
            )

        # Follow-up Pattern 3: "How many of those are tutorials?" / "How many tutorials?"
        if re.search(r"how\s+many\s+(?:of\s+those\s+are\s+)?tutorials?", q) or "are tutorials" in q:
            return StructuredQuery(
                raw_query=query,
                intent=IntentEnum.TUTORIAL_HOURS,
                metric=QueryMetric.TUTORIAL_HOURS,
                time_granularity=self.active_time_granularity or TimeGranularity.DAY,
                date=self.active_date,
                day_of_week=self.active_day,
                date_range=self.active_date_range,
                session_type="Tutorial",
                faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.95,
                is_follow_up=True
            )

        # Follow-up Pattern 4: "How many of those are labs / laboratory?"
        if re.search(r"how\s+many\s+(?:of\s+those\s+are\s+)?labs?", q) or "are labs" in q or "are laboratory" in q:
            return StructuredQuery(
                raw_query=query,
                intent=IntentEnum.LABORATORY_HOURS,
                metric=QueryMetric.LABORATORY_HOURS,
                time_granularity=self.active_time_granularity or TimeGranularity.DAY,
                date=self.active_date,
                day_of_week=self.active_day,
                date_range=self.active_date_range,
                session_type="Laboratory",
                faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.95,
                is_follow_up=True
            )

        # Follow-up Pattern 5: "Show me the schedule for that day" / "What classes do I have then?"
        if any(p in q for p in ["schedule for that day", "classes on that day", "what classes then", "show timetable for that"]):
            return StructuredQuery(
                raw_query=query,
                intent=IntentEnum.DAILY_TIMETABLE,
                metric=QueryMetric.SESSION_LIST,
                time_granularity=TimeGranularity.DAY,
                date=self.active_date,
                day_of_week=self.active_day,
                date_range=self.active_date_range,
                faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                requested_output=RequestedOutput.TIMETABLE_SCHEDULE,
                confidence=0.95,
                is_follow_up=True
            )

        # Follow-up Pattern 6: "Why am I over the limit?" / "Why is there a violation?"
        if any(p in q for p in ["why am i over", "why over the limit", "reason for violation", "explain violation"]):
            return StructuredQuery(
                raw_query=query,
                intent=IntentEnum.WORKLOAD_VIOLATION,
                metric=QueryMetric.VIOLATION_STATUS,
                faculty_id=self.active_faculty_id or initial_sq.faculty_id,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.95,
                is_follow_up=True,
                extra_filters={"explain_reason": True}
            )

        # If not a recognized follow-up pattern, return initial_sq
        return initial_sq
