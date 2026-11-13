"""
Backend Tool Calling Registry.
Provides typed, validated, and authorized backend tool execution:
1. Validates arguments
2. Enforces UserContext authorization
3. Executes verified SQLAlchemy queries and engines
4. Returns structured results
5. Logs execution to audit_logs
"""

from typing import Dict, Any, Callable, Optional, List
from pydantic import BaseModel
from app.config.logging_config import logger
from app.security.access_control import UserContext, AccessDeniedError
from app.audit.audit_logger import AuditLogger

from app.services.faculty_service import FacultyService
from app.services.timetable_service import TimetableService
from app.services.workload_service import WorkloadService
from app.services.policy_service import PolicyService
from app.services.assignment_service import AssignmentService
from app.services.leave_service import LeaveService
from app.services.exemption_service import ExemptionService
from app.services.exception_service import ExceptionService
from app.services.calendar_service import CalendarService
from app.services.analytics_service import AnalyticsService
from app.engines.workload_engine import WorkloadEngine
from app.engines.conflict_detector import ConflictDetector
from app.ingestion.data_validator import DatasetAuditor
from app.rag.rag_service import RAGService


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolRegistry:
    def __init__(self):
        self._rag_service = None

    @property
    def rag(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = RAGService()
        return self._rag_service

    def get_current_user(self, user_context: UserContext, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_current_user", user_context)
        return {
            "user_id": user_context.user_id,
            "username": user_context.username,
            "role": user_context.role.value,
            "department_scope": user_context.department_scope,
            "faculty_id": user_context.faculty_id,
            "faculty_name": user_context.faculty_name
        }

    def get_faculty_details(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_faculty_details", user_context, resource=fid)
        return FacultyService.get_faculty_details(user_context, fid)

    def get_teaching_hours(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_teaching_hours", user_context, resource=fid)
        status = WorkloadService.get_faculty_workload(user_context, fid)
        return {
            "faculty_id": status["faculty_id"],
            "faculty_name": status["faculty_name"],
            "actual_teaching_hours": status["actual_teaching_hours"],
            "breakdown_hours": status["breakdown_hours"],
            "week_start": status["week_start"]
        }

    def get_daily_teaching_hours(
        self,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        day_name: Optional[str] = None,
        target_date: Optional[Any] = None,
        session_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_daily_teaching_hours", user_context, resource=fid, details=f"day={day_name}, session_type={session_type}")
        fac_details = FacultyService.get_faculty_details(user_context, fid)
        return WorkloadEngine.get_daily_teaching_hours(
            faculty_id=fid,
            target_date=target_date,
            day_name=day_name,
            session_type=session_type
        )

    def get_monthly_teaching_hours(
        self,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        year: Optional[int] = 2026,
        month: Optional[int] = 11,
        session_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_monthly_teaching_hours", user_context, resource=fid, details=f"year={year}, month={month}")
        fac_details = FacultyService.get_faculty_details(user_context, fid)
        return WorkloadEngine.get_monthly_teaching_hours(
            faculty_id=fid,
            year=year,
            month=month,
            session_type=session_type
        )

    def get_subject_teaching_hours(
        self,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_subject_teaching_hours", user_context, resource=fid, details=f"subject={subject_id}")
        fac_details = FacultyService.get_faculty_details(user_context, fid)
        return WorkloadEngine.get_subject_teaching_hours(
            faculty_id=fid,
            subject_id=subject_id or "CS101"
        )

    def get_next_class(
        self,
        user_context: UserContext,
        faculty_id: Optional[str] = None,
        reference_day: Optional[str] = "Wednesday",
        reference_time: Optional[str] = "09:30",
        **kwargs
    ) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_next_class", user_context, resource=fid)
        return TimetableService.get_next_class(
            user_context=user_context,
            faculty_id=fid,
            reference_day=reference_day,
            reference_time=reference_time
        )

    def get_section_timetable(
        self,
        user_context: UserContext,
        section_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        AuditLogger.log_event("get_section_timetable", user_context, details=f"section={section_id}")
        return TimetableService.get_section_timetable(
            user_context=user_context,
            section_id=section_id
        )

    def get_workload_status(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_workload_status", user_context, resource=fid)
        return WorkloadService.get_faculty_workload(user_context, fid)

    def get_policy(self, user_context: UserContext, designation: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_policy", user_context, details=f"designation={designation}")
        if designation:
            pol = PolicyService.get_policy_for_designation(designation)
            return pol or {"message": f"No policy found for designation '{designation}'."}
        return {"policies": PolicyService.list_all_policies()}

    def get_policy_violations(self, user_context: UserContext, department_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        dept = department_id or user_context.department_scope
        AuditLogger.log_event("get_policy_violations", user_context, resource=dept)
        violations = WorkloadService.get_policy_violations(user_context, dept)
        return {
            "department_id": dept,
            "violation_count": len(violations),
            "violations": violations
        }

    def get_faculty_timetable(self, user_context: UserContext, faculty_id: Optional[str] = None, day: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_faculty_timetable", user_context, resource=fid, details=f"day={day}")
        return TimetableService.get_faculty_timetable(user_context, fid, day=day)

    def get_faculty_assignments(self, user_context: UserContext, faculty_id: Optional[str] = None, status: Optional[str] = None, assignment_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_faculty_assignments", user_context, resource=fid, details=f"status={status}")
        return AssignmentService.get_faculty_assignments(user_context, fid, status=status, assignment_type=assignment_type)

    def get_department_workload(self, user_context: UserContext, department_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        dept = department_id or user_context.department_scope
        AuditLogger.log_event("get_department_workload", user_context, resource=dept)
        return WorkloadService.get_department_workload_summary(user_context, dept)

    def get_faculty_leave(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_faculty_leave", user_context, resource=fid)
        records = LeaveService.get_faculty_leave(user_context, fid)
        return {"faculty_id": fid, "leave_records": records}

    def get_department_leave(self, user_context: UserContext, department_id: Optional[str] = None, approved_only: bool = False, **kwargs) -> Dict[str, Any]:
        dept = department_id or user_context.department_scope
        AuditLogger.log_event("get_department_leave", user_context, resource=dept)
        records = LeaveService.get_department_leave(user_context, dept, approved_only=approved_only)
        return {"department_id": dept, "leave_records": records}

    def get_substitute_allocations(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_substitute_allocations", user_context, resource=fid)
        reps = TimetableService.get_cancelled_and_substituted(user_context, fid)
        return {"faculty_id": fid, "substitutions": reps}

    def get_workload_exemptions(self, user_context: UserContext, faculty_id: Optional[str] = None, department_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_workload_exemptions", user_context)
        if faculty_id:
            exm = ExemptionService.get_faculty_exemptions(user_context, faculty_id)
            return {"faculty_id": faculty_id, "exemptions": exm}
        dept = department_id or user_context.department_scope
        exm = ExemptionService.get_department_exemptions(user_context, dept)
        return {"department_id": dept, "exemptions": exm}

    def get_policy_exceptions(self, user_context: UserContext, faculty_id: Optional[str] = None, status: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_policy_exceptions", user_context)
        if faculty_id and user_context.is_faculty():
            exc = ExceptionService.get_faculty_exceptions(user_context, faculty_id)
            return {"faculty_id": faculty_id, "exceptions": exc}
        exc = ExceptionService.list_all_exceptions(user_context, status_filter=status)
        return {"exceptions": exc}

    def get_historical_workload(self, user_context: UserContext, faculty_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        fid = faculty_id or user_context.faculty_id
        AuditLogger.log_event("get_historical_workload", user_context, resource=fid)
        return AnalyticsService.get_faculty_history(user_context, fid)

    def get_academic_events(self, user_context: UserContext, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_academic_events", user_context)
        events = CalendarService.get_events()
        return {"academic_events": events}

    def detect_timetable_conflicts(self, user_context: UserContext, department_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        dept = department_id or user_context.department_scope
        AuditLogger.log_event("detect_timetable_conflicts", user_context, resource=dept)
        return ConflictDetector.detect_conflicts(dept)

    def get_institutional_analytics(self, user_context: UserContext, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_institutional_analytics", user_context)
        return WorkloadService.get_institutional_workload(user_context)

    def get_data_quality_report(self, user_context: UserContext, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("get_data_quality_report", user_context)
        auditor = DatasetAuditor("data/faculty_workload_dummy_dataset.xlsx")
        return auditor.run_full_audit()

    def query_policy_rag(self, user_context: UserContext, query: str, **kwargs) -> Dict[str, Any]:
        AuditLogger.log_event("query_policy_rag", user_context, details=query)
        return self.rag.query_policy(query, department=user_context.department_scope)


tool_registry = ToolRegistry()

