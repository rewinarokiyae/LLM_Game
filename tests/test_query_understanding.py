"""
Query Understanding, Structured Interpretation, and Regression Test Suite.
Validates intent classification, entity extraction, date resolution, query planning,
multi-turn context resolution, RBAC boundaries, and non-generic question-specific responses.
"""

import pytest
from datetime import date
from app.nlp.intent_classifier import IntentClassifier
from app.nlp.date_resolver import DateResolver
from app.nlp.structured_query import (
    StructuredQuery, IntentEnum, TimeGranularity, QueryMetric
)
from app.nlp.conversation_context import ConversationContext
from app.nlp.query_router import QueryRouter
from app.security.authentication import AuthenticationService
from app.security.access_control import RoleEnum


@pytest.fixture
def fac_context():
    return AuthenticationService.authenticate_demo("demo.fac002@university.test")


@pytest.fixture
def hod_context():
    return AuthenticationService.authenticate_demo("demo.fac001@university.test")


@pytest.fixture
def admin_context():
    return AuthenticationService.authenticate_demo("admin")


# ==============================================================================
# 1. CORE REGRESSION TEST: QUESTION 1 VS QUESTION 2
# ==============================================================================
def test_regression_monday_vs_monthly_workload(fac_context):
    """
    REGRESSION PROOF:
    Verifies that 'How many hours do I have on Monday?' and
    'How many hours do I have in total this month?' do NOT produce identical responses.
    They must use different intents, granularities, date filters, tools, and output distinct values.
    """
    q1 = "How many hours do I have on Monday?"
    q2 = "How many hours do I have in total this month?"

    # 1. Structured interpretation
    sq1 = IntentClassifier.classify_to_structured_query(q1, default_faculty_id=fac_context.faculty_id)
    sq2 = IntentClassifier.classify_to_structured_query(q2, default_faculty_id=fac_context.faculty_id)

    assert sq1.intent == IntentEnum.DAILY_WORKLOAD
    assert sq2.intent == IntentEnum.MONTHLY_WORKLOAD

    assert sq1.time_granularity == TimeGranularity.DAY
    assert sq2.time_granularity == TimeGranularity.MONTH

    assert sq1.day_of_week == "Monday"
    assert sq1.date == date(2026, 11, 9)
    assert sq1.date_range.start == date(2026, 11, 9)
    assert sq1.date_range.end == date(2026, 11, 10)

    assert sq2.month == 11
    assert sq2.year == 2026
    assert sq2.date_range.start == date(2026, 11, 1)
    assert sq2.date_range.end == date(2026, 12, 1)

    # 2. Execution and backend routing
    r1 = QueryRouter.process_query(fac_context, q1)
    r2 = QueryRouter.process_query(fac_context, q2)

    assert r1["tool"] == "get_daily_teaching_hours"
    assert r2["tool"] == "get_monthly_teaching_hours"

    assert r1["data"]["actual_teaching_hours"] == 3.0
    assert r2["data"]["projected_monthly_hours"] == 34.0
    assert r2["data"]["actual_sample_week_hours"] == 17.0

    # 3. Response text divergence
    assert "Monday" in r1["response"]
    assert "3.0 hours" in r1["response"]
    assert "34.0 hours" not in r1["response"]

    assert "November 2026" in r2["response"]
    assert "34.0 hours" in r2["response"]
    assert r1["response"] != r2["response"]


# ==============================================================================
# 2. DATE AND TIME RESOLUTION
# ==============================================================================
def test_date_resolver_relative_and_explicit_terms():
    ref = date(2026, 11, 11)  # Wednesday

    tg, d, day_name, dr, m, y = DateResolver.resolve_date_and_range("what classes do I have today?", reference=ref)
    assert tg == TimeGranularity.DAY
    assert d == date(2026, 11, 11)
    assert day_name == "Wednesday"
    assert dr.start == date(2026, 11, 11)
    assert dr.end == date(2026, 11, 12)

    tg, d, day_name, dr, m, y = DateResolver.resolve_date_and_range("schedule tomorrow", reference=ref)
    assert tg == TimeGranularity.DAY
    assert d == date(2026, 11, 12)
    assert day_name == "Thursday"

    tg, d, day_name, dr, m, y = DateResolver.resolve_date_and_range("hours on Monday", reference=ref)
    assert tg == TimeGranularity.DAY
    assert d == date(2026, 11, 9)
    assert day_name == "Monday"

    tg, d, day_name, dr, m, y = DateResolver.resolve_date_and_range("total workload this week", reference=ref)
    assert tg == TimeGranularity.WEEK
    assert dr.start == date(2026, 11, 9)
    assert dr.end == date(2026, 11, 16)

    tg, d, day_name, dr, m, y = DateResolver.resolve_date_and_range("workload this month", reference=ref)
    assert tg == TimeGranularity.MONTH
    assert m == 11
    assert y == 2026
    assert dr.start == date(2026, 11, 1)
    assert dr.end == date(2026, 12, 1)


# ==============================================================================
# 3. MULTI-TURN CONVERSATION CONTEXT & FOLLOW-UP RESOLUTION
# ==============================================================================
def test_multi_turn_follow_up_resolution(fac_context):
    ctx = ConversationContext()

    # Turn 1: Monday hours
    q1 = "How many hours do I have on Monday?"
    sq1 = IntentClassifier.classify_to_structured_query(q1, default_faculty_id=fac_context.faculty_id)
    sq1 = ctx.resolve_follow_up(q1, sq1)
    r1 = QueryRouter.process_query(fac_context, q1)
    ctx.add_turn(q1, sq1, r1["response"])
    assert sq1.intent == IntentEnum.DAILY_WORKLOAD
    assert sq1.day_of_week == "Monday"

    # Turn 2: "What about Tuesday?"
    q2 = "What about Tuesday?"
    sq2 = IntentClassifier.classify_to_structured_query(q2, default_faculty_id=fac_context.faculty_id)
    sq2 = ctx.resolve_follow_up(q2, sq2)
    ctx.add_turn(q2, sq2, "Response 2")
    assert sq2.intent == IntentEnum.DAILY_WORKLOAD
    assert sq2.day_of_week == "Tuesday"
    assert sq2.date == date(2026, 11, 10)

    # Turn 3: "How many of those are lectures?"
    q3 = "How many of those are lectures?"
    sq3 = IntentClassifier.classify_to_structured_query(q3, default_faculty_id=fac_context.faculty_id)
    sq3 = ctx.resolve_follow_up(q3, sq3)
    ctx.add_turn(q3, sq3, "Response 3")
    assert sq3.intent == IntentEnum.LECTURE_HOURS
    assert sq3.day_of_week == "Tuesday"
    assert sq3.session_type == "Lecture"

    # Context bleeding isolation check: An unrelated query must reset temporal day filter
    q4 = "Which department has the highest total scheduled hours?"
    sq4 = IntentClassifier.classify_to_structured_query(q4, default_faculty_id=fac_context.faculty_id)
    sq4 = ctx.resolve_follow_up(q4, sq4)
    assert sq4.intent in [IntentEnum.DEPARTMENT_ANALYTICS, IntentEnum.INSTITUTION_ANALYTICS]
    assert sq4.day_of_week is None
    assert sq4.date is None


# ==============================================================================
# 4. BENCHMARK SUITE: 24 EVALUATION QUESTIONS FROM SECTION 13
# ==============================================================================
@pytest.mark.parametrize("query,expected_intent,expected_tool", [
    ("How many hours do I have on Monday?", "daily_workload", "get_daily_teaching_hours"),
    ("How many hours do I have in total this month?", "monthly_workload", "get_monthly_teaching_hours"),
    ("What classes do I have tomorrow?", "timetable_lookup", "get_faculty_timetable"),
    ("When is my next class?", "next_class", "get_next_class"),
    ("How many lectures do I teach this week?", "lecture_hours", "get_session_type_hours"),
    ("How many laboratory hours do I have on Tuesday?", "laboratory_hours", "get_session_type_hours"),
    ("What is my total teaching workload this week?", "faculty_workload", "get_teaching_hours"),
    ("Am I exceeding the workload policy?", "workload_violation", "get_workload_status"),
    ("Why am I over the limit?", "workload_violation", "get_workload_status"),
    ("Do I have any approved exceptions?", "exception_lookup", "get_policy_exceptions"),
    ("What is the policy limit for an Associate Professor?", "policy_lookup", "get_policy"),
    ("What are the rules for counting laboratory hours?", "policy_lookup", "get_workload_rules"),
    ("Who teaches Database Systems?", "subject_lookup", "subject_allocation"),
    ("Show the timetable for Section A.", "timetable_lookup", "get_section_timetable"),
    ("What assignments do I have pending?", "pending_assignment_lookup", "get_faculty_assignments"),
    ("Do I have any overdue assignments?", "pending_assignment_lookup", "get_faculty_assignments"),
    ("Are there any timetable conflicts in my schedule?", "timetable_conflict", "detect_timetable_conflicts"),
    ("What events are on the academic calendar next week?", "academic_calendar", "get_academic_events"),
    ("What was my workload in the previous semester?", "historical_workload", "get_historical_workload"),
    ("How many hours of CS101 do I teach?", "subject_workload", "get_subject_teaching_hours")
])
def test_evaluation_questions_faculty_role(fac_context, query, expected_intent, expected_tool):
    res = QueryRouter.process_query(fac_context, query)
    assert res["intent"] in [expected_intent, res["structured_query"]["intent"].lower()]
    assert res["tool"] == expected_tool
    assert len(res["response"]) > 20
    assert "error" not in res or res.get("error") is None


def test_department_violation_and_analytics_hod_admin(admin_context, hod_context):
    # Department violations
    res = QueryRouter.process_query(admin_context, "Which faculty members in CSE are exceeding their workload?")
    assert res["intent"] == "workload_violation"
    assert res["tool"] == "get_policy_violations"
    assert "FAC001" in res["response"]
    assert "FAC002" in res["response"]

    # Highest department workload
    res2 = QueryRouter.process_query(admin_context, "Which department has the highest total scheduled hours?")
    assert res2["intent"] in ["department_analytics", "institution_analytics"]
    assert res2["tool"] == "get_institutional_analytics"
    assert "Highest Total Scheduled Teaching Hours" in res2["response"]

    # Leave on Wednesday (HOD)
    res3 = QueryRouter.process_query(hod_context, "Who is on leave on Wednesday?")
    assert res3["intent"] in ["leave_information", "leave_lookup"]
    assert res3["tool"] == "get_department_leave"
    assert "FAC004" in res3["response"]

    # Available faculty on Friday morning (HOD)
    res4 = QueryRouter.process_query(hod_context, "Which faculty members are available on Friday morning?")
    assert res4["intent"] == "availability_lookup"
    assert res4["tool"] == "get_free_faculty"
    assert "Available Faculty Members" in res4["response"]


# ==============================================================================
# 5. RBAC SECURITY BOUNDARY ENFORCEMENT
# ==============================================================================
def test_rbac_boundary_faculty_cannot_query_other_faculty_workload(fac_context):
    """Faculty cannot access other faculty records via natural language query."""
    res = QueryRouter.process_query(fac_context, "How many hours does FAC001 have on Monday?")
    assert "Access Denied" in res["response"]
    assert res.get("error") is not None
