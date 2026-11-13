"""
Tests for Query Routing and Natural Language Processing.
"""

import pytest
from app.security.authentication import AuthenticationService
from app.nlp.query_router import QueryRouter
from app.nlp.intent_classifier import IntentClassifier


def test_intent_classification():
    intents = [
        ("How many hours am I teaching this week?", "faculty_workload"),
        ("Am I exceeding my weekly teaching-hour limit?", "workload_violation"),
        ("What classes do I have on Wednesday?", "timetable_lookup"),
        ("Which assignments are pending for me?", "pending_assignment_lookup"),
        ("Who is substituting my cancelled class?", "substitute_lookup"),
        ("Are there any timetable conflicts in my department?", "timetable_conflict"),
        ("Which department has the highest total scheduled teaching hours?", "institution_analytics"),
        ("Show data quality and integrity report", "data_quality"),
        ("/help", "help")
    ]
    for text, expected in intents:
        classified, conf = IntentClassifier.classify_intent(text)
        assert classified == expected, f"Failed for '{text}': got {classified}, expected {expected}"


def test_query_router_execution():
    user = AuthenticationService.authenticate_demo("FAC002")
    res = QueryRouter.process_query(user, "How many hours am I teaching this week?")
    assert res["intent"] == "faculty_workload"
    assert "17.0" in res["response"]

