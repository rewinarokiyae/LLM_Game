"""
Intent Classification Engine.
Determines user intent from natural language questions across the 29 required domain intents:
- DAILY_WORKLOAD, WEEKLY_WORKLOAD, MONTHLY_WORKLOAD, DATE_RANGE_WORKLOAD, TOTAL_WORKLOAD
- DAILY_TIMETABLE, WEEKLY_TIMETABLE, MONTHLY_TIMETABLE, NEXT_CLASS, CLASS_COUNT
- LECTURE_HOURS, TUTORIAL_HOURS, LABORATORY_HOURS, SUBJECT_WORKLOAD
- SECTION_TIMETABLE, FACULTY_TIMETABLE, TIMETABLE_CONFLICT
- ASSIGNMENT_SUMMARY, PENDING_ASSIGNMENTS, OVERDUE_ASSIGNMENTS, UPCOMING_ASSIGNMENTS
- LEAVE_INFORMATION, AVAILABILITY_LOOKUP, SUBSTITUTE_LOOKUP
- WORKLOAD_LIMIT, WORKLOAD_VIOLATION, POLICY_QUERY, EXEMPTION_LOOKUP, EXCEPTION_LOOKUP
- HISTORICAL_WORKLOAD, DEPARTMENT_ANALYTICS, INSTITUTION_ANALYTICS, ACADEMIC_CALENDAR
- FACULTY_INFORMATION, SUBJECT_INFORMATION, DATA_QUALITY, HELP, UNKNOWN_OR_AMBIGUOUS
"""

import re
from typing import Tuple, Optional, Dict, Any

from app.nlp.structured_query import (
    IntentEnum, TimeGranularity, QueryMetric, RequestedOutput, StructuredQuery
)
from app.nlp.date_resolver import DateResolver
from app.nlp.entity_extractor import EntityExtractor


class IntentClassifier:
    LEGACY_INTENT_MAP = {
        IntentEnum.WEEKLY_WORKLOAD: "faculty_workload",
        IntentEnum.TOTAL_WORKLOAD: "faculty_workload",
        IntentEnum.DAILY_TIMETABLE: "timetable_lookup",
        IntentEnum.WEEKLY_TIMETABLE: "timetable_lookup",
        IntentEnum.SECTION_TIMETABLE: "timetable_lookup",
        IntentEnum.FACULTY_TIMETABLE: "timetable_lookup",
        IntentEnum.PENDING_ASSIGNMENTS: "pending_assignment_lookup",
        IntentEnum.OVERDUE_ASSIGNMENTS: "pending_assignment_lookup",
        IntentEnum.ASSIGNMENT_SUMMARY: "assignment_lookup",
        IntentEnum.SUBSTITUTE_LOOKUP: "substitute_lookup",
        IntentEnum.INSTITUTION_ANALYTICS: "institution_analytics",
        IntentEnum.DEPARTMENT_ANALYTICS: "department_analytics",
        IntentEnum.LEAVE_INFORMATION: "leave_lookup",
        IntentEnum.AVAILABILITY_LOOKUP: "availability_lookup",
        IntentEnum.EXEMPTION_LOOKUP: "exemption_lookup",
        IntentEnum.EXCEPTION_LOOKUP: "exception_lookup",
        IntentEnum.WORKLOAD_VIOLATION: "workload_violation",
        IntentEnum.WORKLOAD_LIMIT: "policy_lookup",
        IntentEnum.POLICY_QUERY: "policy_lookup",
        IntentEnum.HISTORICAL_WORKLOAD: "historical_workload",
        IntentEnum.ACADEMIC_CALENDAR: "academic_calendar",
        IntentEnum.TIMETABLE_CONFLICT: "timetable_conflict",
        IntentEnum.FACULTY_INFORMATION: "faculty_lookup",
        IntentEnum.SUBJECT_INFORMATION: "subject_lookup",
        IntentEnum.DATA_QUALITY: "data_quality",
        IntentEnum.HELP: "help",
    }

    @classmethod
    def classify_intent(cls, query: str) -> Tuple[str, float]:
        """
        Classifies query to string intent name for backward compatibility.
        """
        sq = cls.classify_to_structured_query(query)
        legacy = cls.LEGACY_INTENT_MAP.get(sq.intent, sq.intent.value.lower())
        return legacy, sq.confidence

    @classmethod
    def classify_to_structured_query(
        cls,
        query: str,
        default_faculty_id: Optional[str] = None
    ) -> StructuredQuery:
        """
        Classifies incoming natural language into a fully populated StructuredQuery.
        """
        q = query.strip()
        q_lower = q.lower()
        entities = EntityExtractor.extract_entities(q, default_faculty_id=default_faculty_id)
        
        time_granularity, parsed_date, day_of_week, date_range, month, year = DateResolver.resolve_date_and_range(q)
        
        # If day was found by entity extractor but not by date resolver, align it
        if entities.get("day") and not day_of_week:
            day_of_week = entities.get("day")

        # 1. HELP / COMMANDS
        if q_lower in ["/help", "help", "what can you do", "commands", "menu"]:
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.HELP,
                metric=QueryMetric.GENERAL_INFO,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=1.0
            )

        # 2. DATA QUALITY
        if any(w in q_lower for w in ["data quality", "integrity report", "missing values", "duplicate records", "anomalies", "/data-quality"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.DATA_QUALITY,
                metric=QueryMetric.GENERAL_INFO,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.98
            )

        # 3. TIMETABLE CONFLICTS
        if any(w in q_lower for w in ["conflict", "overlapping", "overlap", "double booking", "double booked", "clash"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.TIMETABLE_CONFLICT,
                metric=QueryMetric.CONFLICT_LIST,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        # 4. POLICY RULES & CALCULATION RULES (Check before session type hours)
        # e.g. "What are the rules for counting laboratory hours?"
        if any(w in q_lower for w in ["rules for counting", "calculation rule", "rule for counting", "rules for", "rule for laboratory", "rule for lecture"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.POLICY_QUERY,
                metric=QueryMetric.POLICY_LIMIT,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.98
            )

        # 5. NEXT CLASS
        if any(w in q_lower for w in ["when is my next class", "next class", "upcoming class"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.NEXT_CLASS,
                metric=QueryMetric.NEXT_SESSION,
                time_granularity=TimeGranularity.DAY,
                date=DateResolver.get_reference_date(),
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.NEXT_SESSION,
                confidence=0.98
            )

        # 6. CLASS COUNT
        if any(w in q_lower for w in ["how many classes", "number of classes", "class count", "how many sessions"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.CLASS_COUNT,
                metric=QueryMetric.CLASS_COUNT,
                time_granularity=time_granularity if time_granularity != TimeGranularity.UNSPECIFIED else TimeGranularity.DAY,
                date=parsed_date,
                day_of_week=day_of_week,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.SESSION_COUNT,
                confidence=0.95
            )

        # 7. SPECIFIC SESSION TYPE HOURS: LECTURE, TUTORIAL, LABORATORY
        # e.g. "How many lectures do I teach this week?", "How many laboratory hours do I have on Tuesday?"
        if any(w in q_lower for w in ["laboratory hour", "lab hour", "laboratory hours", "lab hours", "labs on", "laboratories on"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.LABORATORY_HOURS,
                metric=QueryMetric.LABORATORY_HOURS,
                session_type="Laboratory",
                time_granularity=time_granularity if time_granularity != TimeGranularity.UNSPECIFIED else TimeGranularity.DAY,
                date=parsed_date,
                day_of_week=day_of_week,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.98
            )

        if any(w in q_lower for w in ["lecture hour", "how many lectures", "lecture hours", "lectures do i teach"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.LECTURE_HOURS,
                metric=QueryMetric.LECTURE_HOURS,
                session_type="Lecture",
                time_granularity=time_granularity if time_granularity != TimeGranularity.UNSPECIFIED else TimeGranularity.WEEK,
                date=parsed_date,
                day_of_week=day_of_week,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.98
            )

        if any(w in q_lower for w in ["tutorial hour", "how many tutorials", "tutorial hours"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.TUTORIAL_HOURS,
                metric=QueryMetric.TUTORIAL_HOURS,
                session_type="Tutorial",
                time_granularity=time_granularity if time_granularity != TimeGranularity.UNSPECIFIED else TimeGranularity.DAY,
                date=parsed_date,
                day_of_week=day_of_week,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.98
            )

        # 7. SUBJECT WORKLOAD
        # e.g. "How many hours of CS101 do I teach?", "teaching hours for CS502"
        if entities.get("subject_id") and any(w in q_lower for w in ["hour", "workload", "teach"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.SUBJECT_WORKLOAD,
                metric=QueryMetric.TEACHING_HOURS,
                subject_id=entities.get("subject_id"),
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.98
            )

        # 8. WORKLOAD VIOLATIONS & COMPLIANCE
        # e.g. "Am I exceeding the workload policy?", "Why am I over the limit?", "Which faculty members in CSE are exceeding their workload?"
        if any(w in q_lower for w in ["exceed", "violation", "violat", "over limit", "over the limit", "above limit", "breach", "exceeding"]):
            # Check if department-wide or individual
            dept_id = entities.get("department_id")
            if dept_id or "department" in q_lower or "faculty members" in q_lower:
                return StructuredQuery(
                    raw_query=q,
                    intent=IntentEnum.WORKLOAD_VIOLATION,
                    metric=QueryMetric.VIOLATION_STATUS,
                    department_id=dept_id,
                    requested_output=RequestedOutput.LIST,
                    confidence=0.98
                )
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.WORKLOAD_VIOLATION,
                metric=QueryMetric.VIOLATION_STATUS,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.STATUS,
                confidence=0.98
            )

        # 9. POLICY LIMITS & RULES
        # e.g. "What is the policy limit for an Associate Professor?", "What are the rules for counting laboratory hours?"
        if any(w in q_lower for w in ["rules for counting", "calculation rule", "rule for counting", "rule for laboratory", "rule for lecture"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.POLICY_QUERY,
                metric=QueryMetric.POLICY_LIMIT,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.98
            )

        if any(w in q_lower for w in ["policy limit", "maximum teaching workload", "maximum workload", "max teaching", "minimum workload", "standard maximum"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.WORKLOAD_LIMIT,
                metric=QueryMetric.POLICY_LIMIT,
                designation=entities.get("designation"),
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.POLICY_DETAILS,
                confidence=0.98
            )

        # 10. EXCEPTIONS & EXEMPTIONS
        if any(w in q_lower for w in ["exception", "override", "approved exception"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.EXCEPTION_LOOKUP,
                metric=QueryMetric.GENERAL_INFO,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        if any(w in q_lower for w in ["exemption", "relief", "administrative relief", "relief hours"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.EXEMPTION_LOOKUP,
                metric=QueryMetric.GENERAL_INFO,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        # 11. HISTORICAL WORKLOAD (Check before general workload)
        if any(w in q_lower for w in ["historical", "previous semester", "past semester", "last four semesters", "prior term", "history"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.HISTORICAL_WORKLOAD,
                metric=QueryMetric.TEACHING_HOURS,
                time_granularity=TimeGranularity.SEMESTER,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.98
            )

        # 12. DEPARTMENT & INSTITUTION ANALYTICS (Check before general timetable/schedule)
        if any(w in q_lower for w in ["institution-wide", "across all department", "highest total scheduled", "which department has the highest", "compare department"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.INSTITUTION_ANALYTICS,
                metric=QueryMetric.TEACHING_HOURS,
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        if any(w in q_lower for w in ["department workload", "workload of the department", "workload for dep-", "department-wide", "distribution in"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.DEPARTMENT_ANALYTICS,
                metric=QueryMetric.TEACHING_HOURS,
                department_id=entities.get("department_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        # 12b. SUBSTITUTE & CANCELLED SESSIONS
        if any(w in q_lower for w in ["substitut", "replac", "cover", "cancell"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.SUBSTITUTE_LOOKUP,
                metric=QueryMetric.SESSION_LIST,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        # 13. TIMETABLE QUERIES: DAILY vs WEEKLY vs SECTION vs FACULTY
        # e.g. "What classes do I have tomorrow?", "Show the timetable for Section A", "timetable for Monday"
        if entities.get("section_id") or ("section" in q_lower and ("timetable" in q_lower or "schedule" in q_lower)):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.SECTION_TIMETABLE,
                metric=QueryMetric.SESSION_LIST,
                section_id=entities.get("section_id") or "CSE-S5-A",
                requested_output=RequestedOutput.TIMETABLE_SCHEDULE,
                confidence=0.98
            )

        if any(w in q_lower for w in ["what classes", "classes do i have", "classes on", "class on", "class today", "class tomorrow", "schedule on", "timetable on"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.DAILY_TIMETABLE,
                metric=QueryMetric.SESSION_LIST,
                time_granularity=TimeGranularity.DAY,
                date=parsed_date,
                day_of_week=day_of_week,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TIMETABLE_SCHEDULE,
                confidence=0.95
            )

        if any(w in q_lower for w in ["timetable", "schedule"]):
            if day_of_week or time_granularity == TimeGranularity.DAY:
                return StructuredQuery(
                    raw_query=q,
                    intent=IntentEnum.DAILY_TIMETABLE,
                    metric=QueryMetric.SESSION_LIST,
                    time_granularity=TimeGranularity.DAY,
                    date=parsed_date,
                    day_of_week=day_of_week,
                    date_range=date_range,
                    faculty_id=entities.get("faculty_id"),
                    requested_output=RequestedOutput.TIMETABLE_SCHEDULE,
                    confidence=0.95
                )
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.WEEKLY_TIMETABLE,
                metric=QueryMetric.SESSION_LIST,
                time_granularity=TimeGranularity.WEEK,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TIMETABLE_SCHEDULE,
                confidence=0.95
            )

        # 14. GENERAL WORKLOAD: DISCRIMINATE DAILY, WEEKLY, MONTHLY, DATE RANGE
        # e.g. "How many hours do I have on Monday?", "How many hours do I have in total this month?", "What is my total teaching workload this week?"
        if any(w in q_lower for w in ["how many hours", "teaching hours", "my workload", "total workload", "teaching workload", "workload hours"]):
            # Check Day
            if time_granularity == TimeGranularity.DAY or day_of_week or any(d in q_lower for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "today", "tomorrow"]):
                return StructuredQuery(
                    raw_query=q,
                    intent=IntentEnum.DAILY_WORKLOAD,
                    metric=QueryMetric.TEACHING_HOURS,
                    time_granularity=TimeGranularity.DAY,
                    date=parsed_date,
                    day_of_week=day_of_week,
                    date_range=date_range,
                    faculty_id=entities.get("faculty_id"),
                    requested_output=RequestedOutput.TOTAL_HOURS,
                    confidence=0.98
                )
            # Check Month
            if time_granularity == TimeGranularity.MONTH or "month" in q_lower or any(m in q_lower for m in ["november", "december", "october"]):
                return StructuredQuery(
                    raw_query=q,
                    intent=IntentEnum.MONTHLY_WORKLOAD,
                    metric=QueryMetric.TEACHING_HOURS,
                    time_granularity=TimeGranularity.MONTH,
                    month=month,
                    year=year,
                    date_range=date_range,
                    faculty_id=entities.get("faculty_id"),
                    requested_output=RequestedOutput.TOTAL_HOURS,
                    confidence=0.98
                )
            # Check Week
            if time_granularity == TimeGranularity.WEEK or "week" in q_lower:
                return StructuredQuery(
                    raw_query=q,
                    intent=IntentEnum.WEEKLY_WORKLOAD,
                    metric=QueryMetric.TEACHING_HOURS,
                    time_granularity=TimeGranularity.WEEK,
                    date_range=date_range,
                    faculty_id=entities.get("faculty_id"),
                    requested_output=RequestedOutput.TOTAL_HOURS,
                    confidence=0.98
                )
            # Default to weekly workload
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.WEEKLY_WORKLOAD,
                metric=QueryMetric.TEACHING_HOURS,
                time_granularity=TimeGranularity.WEEK,
                date_range=date_range,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.90
            )

        # 13. ASSIGNMENTS: PENDING, OVERDUE, SUMMARY
        if "overdue" in q_lower:
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.OVERDUE_ASSIGNMENTS,
                metric=QueryMetric.ASSIGNMENT_COUNT,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        if "pending" in q_lower and "assignment" in q_lower:
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.PENDING_ASSIGNMENTS,
                metric=QueryMetric.ASSIGNMENT_COUNT,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.98
            )

        if any(w in q_lower for w in ["assignment", "question paper", "project supervision", "exam dut", "academic dut", "responsibilit"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.ASSIGNMENT_SUMMARY,
                metric=QueryMetric.ASSIGNMENT_COUNT,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.90
            )

        # 14. LEAVE & AVAILABILITY
        if any(w in q_lower for w in ["leave", "absent", "absence", "sick"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.LEAVE_INFORMATION,
                metric=QueryMetric.LEAVE_STATUS,
                time_granularity=time_granularity,
                date=parsed_date,
                day_of_week=day_of_week,
                department_id=entities.get("department_id"),
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.95
            )

        if any(w in q_lower for w in ["available", "free period", "free faculty", "availability"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.AVAILABILITY_LOOKUP,
                metric=QueryMetric.SESSION_LIST,
                time_granularity=time_granularity,
                date=parsed_date,
                day_of_week=day_of_week,
                department_id=entities.get("department_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.95
            )

        # 15. ACADEMIC CALENDAR
        if any(w in q_lower for w in ["academic calendar", "calendar next week", "events on the academic", "calendar event", "holiday", "break"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.ACADEMIC_CALENDAR,
                metric=QueryMetric.GENERAL_INFO,
                time_granularity=time_granularity,
                date_range=date_range,
                requested_output=RequestedOutput.LIST,
                confidence=0.95
            )


        # 18. SUBJECT LOOKUP / WHO TEACHES
        if any(w in q_lower for w in ["who teaches", "teach this subject", "handling subject", "subject allocation"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.SUBJECT_INFORMATION,
                metric=QueryMetric.GENERAL_INFO,
                subject_id=entities.get("subject_id"),
                requested_output=RequestedOutput.LIST,
                confidence=0.90
            )

        # 19. FACULTY INFORMATION LOOKUP
        if any(w in q_lower for w in ["records for", "details for faculty", "faculty profile", "faculty details", "who is dr", "who is prof", "show details for"]):
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.FACULTY_INFORMATION,
                metric=QueryMetric.GENERAL_INFO,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.90
            )

        # 20. POLICY LOOKUP FALLBACK
        if "policy" in q_lower:
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.POLICY_QUERY,
                metric=QueryMetric.POLICY_LIMIT,
                requested_output=RequestedOutput.TEXT_EXPLANATION,
                confidence=0.75
            )

        # 21. WORKLOAD FALLBACK
        if "hour" in q_lower or "workload" in q_lower:
            return StructuredQuery(
                raw_query=q,
                intent=IntentEnum.WEEKLY_WORKLOAD,
                metric=QueryMetric.TEACHING_HOURS,
                time_granularity=TimeGranularity.WEEK,
                faculty_id=entities.get("faculty_id"),
                requested_output=RequestedOutput.TOTAL_HOURS,
                confidence=0.70
            )

        # UNKNOWN
        return StructuredQuery(
            raw_query=q,
            intent=IntentEnum.UNKNOWN_OR_AMBIGUOUS,
            metric=QueryMetric.GENERAL_INFO,
            requested_output=RequestedOutput.TEXT_EXPLANATION,
            confidence=0.40,
            needs_clarification=True,
            clarification_prompt="I couldn't identify the specific workload, timetable, or policy request. Please specify whether you are asking about daily hours, weekly workload, assignments, or policy rules."
        )
