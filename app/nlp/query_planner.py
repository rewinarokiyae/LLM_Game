"""
Query Execution Planner.
Translates a StructuredQuery into an authorized execution plan, enforces RBAC,
invokes the appropriate specialized backend tool/engine, and produces structured outputs.
"""

from typing import Dict, Any, Optional
from datetime import date
from app.config.logging_config import logger
from app.security.access_control import UserContext, AccessDeniedError
from app.nlp.structured_query import (
    StructuredQuery, IntentEnum, TimeGranularity, QueryMetric, RequestedOutput
)
from app.tools.registry import tool_registry
from app.response.response_generator import ResponseGenerator
from app.services.timetable_service import TimetableService
from app.services.faculty_service import FacultyService
from app.database.connection import get_db_session
from app.database.models import Subject, Faculty, Timetable


class QueryPlanner:
    @classmethod
    def execute_plan(
        cls,
        sq: StructuredQuery,
        user_context: UserContext
    ) -> Dict[str, Any]:
        """
        Executes the plan defined by StructuredQuery with strict RBAC enforcement.
        """
        target_fid = sq.faculty_id or user_context.faculty_id

        # RBAC pre-check: faculty role cannot access other faculty records
        if sq.faculty_id and user_context.is_faculty() and sq.faculty_id != user_context.faculty_id:
            try:
                FacultyService.get_faculty_details(user_context, sq.faculty_id)
            except AccessDeniedError as e:
                return {
                    "intent": sq.intent.value,
                    "tool": "access_control",
                    "error": str(e),
                    "response": ResponseGenerator.format_access_denied(str(e))
                }

        intent = sq.intent

        try:
            # 1. HELP
            if intent == IntentEnum.HELP:
                return {
                    "intent": intent.value,
                    "tool": "help",
                    "response": (
                        "### Faculty Workload Intelligence Assistant\n\n"
                        "You can ask natural-language questions about:\n"
                        "- **Daily Workload:** *'How many hours do I have on Monday?'*\n"
                        "- **Monthly Workload:** *'How many hours do I have in total this month?'*\n"
                        "- **Timetables:** *'What classes do I have tomorrow?'* or *'Show the timetable for Section A.'*\n"
                        "- **Next Class:** *'When is my next class?'*\n"
                        "- **Session Specific Hours:** *'How many lectures do I teach this week?'* or *'How many laboratory hours on Tuesday?'*\n"
                        "- **Policy & Compliance:** *'Am I exceeding the workload policy?'* or *'What is the policy limit for an Associate Professor?'*\n"
                        "- **Assignments:** *'What assignments do I have pending?'*\n"
                        "- **Leave & Availability:** *'Who is on leave on Wednesday?'* or *'Which faculty members are available on Friday morning?'*\n"
                        "- **Conflicts:** *'Are there any timetable conflicts in my schedule?'*\n"
                        "- **Department Analytics:** *'Which department has the highest total scheduled hours?'*\n"
                        "- **Data Quality:** *'Show data quality and integrity report.'*\n\n"
                        "**Slash Commands:** `/whoami`, `/workload`, `/timetable`, `/assignments`, `/violations`, `/history`, `/data-quality`, `/logout`, `/exit`."
                    )
                }

            # 2. DAILY WORKLOAD
            elif intent == IntentEnum.DAILY_WORKLOAD:
                res = tool_registry.get_daily_teaching_hours(
                    user_context=user_context,
                    faculty_id=target_fid,
                    day_name=sq.day_of_week,
                    target_date=sq.date,
                    session_type=sq.session_type
                )
                return {
                    "intent": intent.value,
                    "tool": "get_daily_teaching_hours",
                    "data": res,
                    "response": ResponseGenerator.format_daily_workload(res)
                }

            # 3. WEEKLY WORKLOAD / TOTAL WORKLOAD
            elif intent in [IntentEnum.WEEKLY_WORKLOAD, IntentEnum.TOTAL_WORKLOAD]:
                res = tool_registry.get_teaching_hours(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_teaching_hours",
                    "data": res,
                    "response": ResponseGenerator.format_faculty_workload(res)
                }

            # 4. MONTHLY WORKLOAD
            elif intent == IntentEnum.MONTHLY_WORKLOAD:
                res = tool_registry.get_monthly_teaching_hours(
                    user_context=user_context,
                    faculty_id=target_fid,
                    year=sq.year or 2026,
                    month=sq.month or 11,
                    session_type=sq.session_type
                )
                return {
                    "intent": intent.value,
                    "tool": "get_monthly_teaching_hours",
                    "data": res,
                    "response": ResponseGenerator.format_monthly_workload(res)
                }

            # 5. SPECIFIC SESSION TYPE HOURS: LECTURE, TUTORIAL, LABORATORY
            elif intent in [IntentEnum.LECTURE_HOURS, IntentEnum.TUTORIAL_HOURS, IntentEnum.LABORATORY_HOURS]:
                stype = sq.session_type or ("Lecture" if intent == IntentEnum.LECTURE_HOURS else ("Tutorial" if intent == IntentEnum.TUTORIAL_HOURS else "Laboratory"))
                if sq.time_granularity == TimeGranularity.DAY and (sq.day_of_week or sq.date):
                    res = tool_registry.get_daily_teaching_hours(
                        user_context=user_context,
                        faculty_id=target_fid,
                        day_name=sq.day_of_week,
                        target_date=sq.date,
                        session_type=stype
                    )
                else:
                    res = tool_registry.get_teaching_hours(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_session_type_hours",
                    "data": res,
                    "response": ResponseGenerator.format_session_type_hours(res, session_type=stype)
                }

            # 6. CLASS COUNT
            elif intent == IntentEnum.CLASS_COUNT:
                res = tool_registry.get_daily_teaching_hours(
                    user_context=user_context,
                    faculty_id=target_fid,
                    day_name=sq.day_of_week,
                    target_date=sq.date
                )
                return {
                    "intent": intent.value,
                    "tool": "count_sessions",
                    "data": res,
                    "response": ResponseGenerator.format_class_count(res)
                }

            # 7. NEXT CLASS
            elif intent == IntentEnum.NEXT_CLASS:
                res = tool_registry.get_next_class(
                    user_context=user_context,
                    faculty_id=target_fid,
                    reference_day=sq.day_of_week or "Wednesday",
                    reference_time="09:30"
                )
                return {
                    "intent": intent.value,
                    "tool": "get_next_class",
                    "data": res,
                    "response": ResponseGenerator.format_next_class(res)
                }

            # 8. DAILY TIMETABLE
            elif intent == IntentEnum.DAILY_TIMETABLE:
                res = tool_registry.get_faculty_timetable(
                    user_context=user_context,
                    faculty_id=target_fid,
                    day=sq.day_of_week
                )
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_timetable",
                    "data": res,
                    "response": ResponseGenerator.format_timetable(res)
                }

            # 9. WEEKLY TIMETABLE
            elif intent == IntentEnum.WEEKLY_TIMETABLE:
                res = tool_registry.get_faculty_timetable(
                    user_context=user_context,
                    faculty_id=target_fid
                )
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_timetable",
                    "data": res,
                    "response": ResponseGenerator.format_timetable(res)
                }

            # 10. SECTION TIMETABLE
            elif intent == IntentEnum.SECTION_TIMETABLE:
                res = tool_registry.get_section_timetable(
                    user_context=user_context,
                    section_id=sq.section_id or "CSE-S5-A"
                )
                return {
                    "intent": intent.value,
                    "tool": "get_section_timetable",
                    "data": res,
                    "response": ResponseGenerator.format_section_timetable(res)
                }

            # 11. SUBJECT WORKLOAD
            elif intent == IntentEnum.SUBJECT_WORKLOAD:
                res = tool_registry.get_subject_teaching_hours(
                    user_context=user_context,
                    faculty_id=target_fid,
                    subject_id=sq.subject_id
                )
                return {
                    "intent": intent.value,
                    "tool": "get_subject_teaching_hours",
                    "data": res,
                    "response": ResponseGenerator.format_subject_workload(res)
                }

            # 12. WORKLOAD VIOLATION
            elif intent == IntentEnum.WORKLOAD_VIOLATION:
                if sq.department_id:
                    res = tool_registry.get_policy_violations(user_context=user_context, department_id=sq.department_id)
                    return {
                        "intent": intent.value,
                        "tool": "get_policy_violations",
                        "data": res,
                        "response": ResponseGenerator.format_department_violations(res)
                    }
                else:
                    res = tool_registry.get_workload_status(user_context=user_context, faculty_id=target_fid)
                    return {
                        "intent": intent.value,
                        "tool": "get_workload_status",
                        "data": res,
                        "response": ResponseGenerator.format_workload_violation(res)
                    }

            # 13. WORKLOAD LIMIT
            elif intent == IntentEnum.WORKLOAD_LIMIT:
                desig = sq.designation
                if not desig and target_fid:
                    try:
                        fac_info = tool_registry.get_faculty_details(user_context, faculty_id=target_fid)
                        desig = fac_info.get("designation")
                    except Exception:
                        pass
                pol = tool_registry.get_policy(user_context=user_context, designation=desig)
                if "policy_id" in pol:
                    resp = (
                        f"### Workload Policy for {pol['designation']}\n"
                        f"- **Policy ID:** {pol['policy_id']}\n"
                        f"- **Standard Maximum Teaching Hours:** **{pol['max_teaching_hours_week']} hrs/week**\n"
                        f"- **Minimum Expected Teaching Hours:** **{pol['min_teaching_hours_week']} hrs/week**\n"
                        f"- **Calculation Rule:** {pol['calculation_rule']}\n"
                        f"- **Validity Period:** {pol['effective_from']} to {pol['effective_to']}\n"
                        f"- **Source Document:** {pol['source_document']} (Page {pol['source_page']})\n\n"
                        f"[Policy Source: {pol['source_document']} | Policy ID: {pol['policy_id']} | Page {pol['source_page']}]"
                    )
                else:
                    resp = ResponseGenerator.format_insufficient_info(f"No policy limit found for {desig or 'specified role'}")
                return {
                    "intent": intent.value,
                    "tool": "get_policy",
                    "data": pol,
                    "response": resp
                }

            # 14. POLICY QUERY / RULES
            elif intent == IntentEnum.POLICY_QUERY:
                q_raw = sq.raw_query.lower()
                if any(w in q_raw for w in ["laboratory", "rule", "counting", "tutorial", "lecture"]):
                    rule_objs = [
                        {"rule_id": "RULE-001", "session_type": "Lecture", "weight": 1.0, "desc": "A 1-hour lecture contributes 1 workload hour (Actual duration)."},
                        {"rule_id": "RULE-002", "session_type": "Tutorial", "weight": 1.0, "desc": "A 1-hour tutorial contributes 1 workload hour (Actual duration)."},
                        {"rule_id": "RULE-003", "session_type": "Laboratory", "weight": 1.0, "desc": "For this synthetic dataset, lab hours count at actual duration; no multiplier (Weight 1.0)."},
                        {"rule_id": "RULE-004", "session_type": "Project Supervision", "weight": 0.0, "desc": "Tracked as an assignment/responsibility, not scheduled teaching hours."},
                        {"rule_id": "RULE-005", "session_type": "Exam Invigilation", "weight": 0.0, "desc": "Tracked separately as examination duty."},
                        {"rule_id": "RULE-006", "session_type": "Cancelled Session", "weight": 0.0, "desc": "Do not count cancelled sessions."},
                        {"rule_id": "RULE-007", "session_type": "Substituted Session", "weight": 1.0, "desc": "Count against substitute faculty; original faculty is not credited."}
                    ]
                    matching_rules = rule_objs
                    if "laboratory" in q_raw:
                        matching_rules = [r for r in rule_objs if r["session_type"] == "Laboratory"]
                    lines = ["### Institutional Workload Calculation Rules\n"]
                    for mr in matching_rules:
                        lines.append(f"- **{mr['rule_id']} ({mr['session_type']}):** {mr['desc']}")
                    lines.append("\n[Policy Source: Approved institutional workload policy - synthetic demo, v1.0 | Worksheet: Workload_Rules]")
                    return {
                        "intent": intent.value,
                        "tool": "get_workload_rules",
                        "data": matching_rules,
                        "response": "\n".join(lines)
                    }
                else:
                    res = tool_registry.query_policy_rag(user_context=user_context, query=sq.raw_query)
                    return {
                        "intent": intent.value,
                        "tool": "query_policy_rag",
                        "data": res,
                        "response": ResponseGenerator.format_rag_policy_response(res)
                    }

            # 15. EXCEPTIONS
            elif intent == IntentEnum.EXCEPTION_LOOKUP:
                res = tool_registry.get_policy_exceptions(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_policy_exceptions",
                    "data": res,
                    "response": ResponseGenerator.format_exceptions(res)
                }

            # 16. EXEMPTIONS
            elif intent == IntentEnum.EXEMPTION_LOOKUP:
                res = tool_registry.get_workload_exemptions(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_workload_exemptions",
                    "data": res,
                    "response": ResponseGenerator.format_exemptions(res)
                }

            # 17. PENDING ASSIGNMENTS
            elif intent == IntentEnum.PENDING_ASSIGNMENTS:
                res = tool_registry.get_faculty_assignments(user_context=user_context, faculty_id=target_fid, status="Pending")
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_assignments",
                    "data": res,
                    "response": ResponseGenerator.format_assignments(res)
                }

            # 18. OVERDUE ASSIGNMENTS
            elif intent == IntentEnum.OVERDUE_ASSIGNMENTS:
                res = tool_registry.get_faculty_assignments(user_context=user_context, faculty_id=target_fid, status="Pending")
                # Filter for overdue
                res_overdue = [a for a in res.get("assignments", []) if a.get("is_overdue")]
                res["assignments"] = res_overdue
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_assignments",
                    "data": res,
                    "response": ResponseGenerator.format_assignments(res)
                }

            # 19. ASSIGNMENT SUMMARY
            elif intent in [IntentEnum.ASSIGNMENT_SUMMARY, IntentEnum.UPCOMING_ASSIGNMENTS]:
                res = tool_registry.get_faculty_assignments(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_assignments",
                    "data": res,
                    "response": ResponseGenerator.format_assignments(res)
                }

            # 20. LEAVE INFORMATION
            elif intent == IntentEnum.LEAVE_INFORMATION:
                if "my" in sq.raw_query.lower() or (user_context.is_faculty() and not sq.department_id):
                    fid = sq.faculty_id or user_context.faculty_id
                    records = tool_registry.get_faculty_leave(user_context=user_context, faculty_id=fid).get("leave_records", [])
                    return {
                        "intent": intent.value,
                        "tool": "get_faculty_leave",
                        "data": {"faculty_id": fid, "leave_records": records},
                        "response": ResponseGenerator.format_leave_records({"faculty_id": fid, "leave_records": records})
                    }
                else:
                    dept = sq.department_id or user_context.department_scope
                    res = tool_registry.get_department_leave(user_context=user_context, department_id=dept, approved_only=False)
                    records = res.get("leave_records", [])
                    if sq.day_of_week or sq.date:
                        target_d = sq.date or date(2026, 11, 11)
                        records = [
                            r for r in records
                            if (r.get("start_date") and r.get("end_date") and r["start_date"] <= target_d.isoformat() <= r["end_date"])
                        ]
                        res["leave_records"] = records
                    return {
                        "intent": intent.value,
                        "tool": "get_department_leave",
                        "data": res,
                        "response": ResponseGenerator.format_leave_records(res)
                    }

            # 20b. SUBSTITUTE LOOKUP
            elif intent == IntentEnum.SUBSTITUTE_LOOKUP:
                res = tool_registry.get_substitute_allocations(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_substitute_allocations",
                    "data": res,
                    "response": ResponseGenerator.format_substitutions(res)
                }

            # 21. AVAILABILITY LOOKUP
            elif intent == IntentEnum.AVAILABILITY_LOOKUP:
                dept = sq.department_id or user_context.department_scope
                free_fac = TimetableService.get_free_faculty(
                    user_context=user_context,
                    day=sq.day_of_week or "Friday",
                    start_time="09:00",
                    end_time="12:00",
                    department_id=dept
                )
                return {
                    "intent": intent.value,
                    "tool": "get_free_faculty",
                    "data": {"day": sq.day_of_week or "Friday", "free_faculty": free_fac},
                    "response": ResponseGenerator.format_free_faculty({
                        "day": sq.day_of_week or "Friday",
                        "start_time": "09:00",
                        "end_time": "12:00",
                        "free_faculty": free_fac
                    })
                }

            # 22. TIMETABLE CONFLICT
            elif intent == IntentEnum.TIMETABLE_CONFLICT:
                res = tool_registry.detect_timetable_conflicts(user_context=user_context)
                return {
                    "intent": intent.value,
                    "tool": "detect_timetable_conflicts",
                    "data": res,
                    "response": ResponseGenerator.format_conflicts(res)
                }

            # 23. ACADEMIC CALENDAR
            elif intent == IntentEnum.ACADEMIC_CALENDAR:
                res = tool_registry.get_academic_events(user_context=user_context)
                events = res.get("academic_events", [])
                # Filter for next week if specified
                if sq.date_range:
                    events = [
                        e for e in events
                        if e.get("start_date") and sq.date_range.start.isoformat() <= e["start_date"] < sq.date_range.end.isoformat()
                    ]
                    res["academic_events"] = events
                return {
                    "intent": intent.value,
                    "tool": "get_academic_events",
                    "data": res,
                    "response": ResponseGenerator.format_academic_events(res)
                }

            # 24. HISTORICAL WORKLOAD
            elif intent == IntentEnum.HISTORICAL_WORKLOAD:
                res = tool_registry.get_historical_workload(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_historical_workload",
                    "data": res,
                    "response": ResponseGenerator.format_historical(res)
                }

            # 25. DEPARTMENT ANALYTICS
            elif intent == IntentEnum.DEPARTMENT_ANALYTICS:
                dept = sq.department_id or user_context.department_scope
                if not user_context.can_access_department(dept) and not user_context.is_admin():
                    raise AccessDeniedError(f"Access Denied: You cannot view department-wide workload for '{dept}'.")
                res = tool_registry.get_department_workload(user_context=user_context, department_id=dept)
                return {
                    "intent": intent.value,
                    "tool": "get_department_workload",
                    "data": res,
                    "response": ResponseGenerator.format_department_summary(res)
                }

            # 25b. INSTITUTION ANALYTICS
            elif intent == IntentEnum.INSTITUTION_ANALYTICS:
                res = tool_registry.get_institutional_analytics(user_context=user_context)
                return {
                    "intent": intent.value,
                    "tool": "get_institutional_analytics",
                    "data": res,
                    "response": ResponseGenerator.format_institutional_analytics(res)
                }

            # 26. SUBJECT INFORMATION (Who teaches ...)
            elif intent == IntentEnum.SUBJECT_INFORMATION:
                sub_target = sq.subject_id or "Database Systems"
                with get_db_session() as db:
                    # Find subject
                    sub = db.query(Subject).filter(
                        (Subject.subject_id.ilike(sub_target.strip())) |
                        (Subject.subject_name.ilike(f"%{sub_target.strip()}%"))
                    ).first()
                    if not sub:
                        return {
                            "intent": intent.value,
                            "tool": "subject_lookup",
                            "response": ResponseGenerator.format_insufficient_info(f"Subject '{sub_target}' not found in database.")
                        }

                    # Find faculty teaching this subject
                    tts = db.query(Timetable, Faculty.faculty_name).join(
                        Faculty, Timetable.faculty_id == Faculty.faculty_id
                    ).filter(
                        Timetable.subject_id == sub.subject_id,
                        Timetable.status.in_(["Active", "Substituted"])
                    ).all()

                    fac_map = {}
                    for tt, fname in tts:
                        fac_map[tt.faculty_id] = fname

                    lines = [f"### Faculty Allocated to {sub.subject_name} ({sub.subject_id})"]
                    lines.append(f"- **Department:** {sub.department_id}")
                    lines.append(f"- **Total Course Credits:** {sub.credits}\n")
                    if fac_map:
                        lines.append("**Instructors:**")
                        for fid, fname in fac_map.items():
                            lines.append(f"- **{fname}** ({fid})")
                    else:
                        lines.append("No active timetable sessions assigned for this subject.")
                    lines.append(f"\n[Source: Database table 'Timetable' & 'Subject' | Subject ID: {sub.subject_id}]")
                    return {
                        "intent": intent.value,
                        "tool": "subject_allocation",
                        "data": {"subject": sub.subject_name, "faculty": fac_map},
                        "response": "\n".join(lines)
                    }

            # 27. FACULTY INFORMATION
            elif intent == IntentEnum.FACULTY_INFORMATION:
                res = tool_registry.get_faculty_details(user_context=user_context, faculty_id=target_fid)
                return {
                    "intent": intent.value,
                    "tool": "get_faculty_details",
                    "data": res,
                    "response": ResponseGenerator.format_faculty_details(res)
                }

            # 28. DATA QUALITY
            elif intent == IntentEnum.DATA_QUALITY:
                res = tool_registry.get_data_quality_report(user_context=user_context)
                return {
                    "intent": intent.value,
                    "tool": "get_data_quality_report",
                    "data": res,
                    "response": ResponseGenerator.format_data_quality(res)
                }

            # 29. UNKNOWN / AMBIGUOUS
            else:
                return {
                    "intent": intent.value,
                    "tool": "unknown",
                    "response": sq.clarification_prompt or "I could not determine the specific intent of your question. Please ask about your daily hours, weekly workload, timetable, assignments, or policy limits."
                }

        except AccessDeniedError as e:
            return {
                "intent": intent.value,
                "tool": "access_control",
                "error": str(e),
                "response": ResponseGenerator.format_access_denied(str(e))
            }
        except Exception as e:
            logger.error(f"Error executing plan for intent {intent}: {e}", exc_info=True)
            return {
                "intent": intent.value,
                "tool": "error",
                "error": str(e),
                "response": f"An error occurred while retrieving data: {str(e)}"
            }
