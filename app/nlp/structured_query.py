"""
Structured Query Representation & Pydantic Models.
Provides typed, validated, and normalized query representations for the Faculty Workload Intelligence Assistant.
Incorporates multi-dimensional semantic query understanding:
- Intent
- Query Scope (INDIVIDUAL, DEPARTMENT, INSTITUTION, SUBJECT, HISTORICAL, HYPOTHETICAL, DATASET_METRIC, DATA_AVAILABILITY)
- Requested Operation (LOOKUP, FILTER, COUNT, SUM, AVERAGE, MAXIMUM, MINIMUM, RANK, COMPARE, CALCULATE, EXPLAIN, CHECK_COMPLIANCE)
- Missing Field Types for explicit schema-aware unanswerability detection
- Hypothetical calculation parameters
"""

import datetime as dt
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    # Workload Granularities & Metrics
    DAILY_WORKLOAD = "DAILY_WORKLOAD"
    WEEKLY_WORKLOAD = "WEEKLY_WORKLOAD"
    MONTHLY_WORKLOAD = "MONTHLY_WORKLOAD"
    DATE_RANGE_WORKLOAD = "DATE_RANGE_WORKLOAD"
    TOTAL_WORKLOAD = "TOTAL_WORKLOAD"
    
    # Timetable & Scheduling
    DAILY_TIMETABLE = "DAILY_TIMETABLE"
    WEEKLY_TIMETABLE = "WEEKLY_TIMETABLE"
    MONTHLY_TIMETABLE = "MONTHLY_TIMETABLE"
    NEXT_CLASS = "NEXT_CLASS"
    CLASS_COUNT = "CLASS_COUNT"
    SECTION_TIMETABLE = "SECTION_TIMETABLE"
    FACULTY_TIMETABLE = "FACULTY_TIMETABLE"
    TIMETABLE_CONFLICT = "TIMETABLE_CONFLICT"
    
    # Session Specific Hours
    LECTURE_HOURS = "LECTURE_HOURS"
    TUTORIAL_HOURS = "TUTORIAL_HOURS"
    LABORATORY_HOURS = "LABORATORY_HOURS"
    SUBJECT_WORKLOAD = "SUBJECT_WORKLOAD"
    
    # Assignments & Duties
    ASSIGNMENT_SUMMARY = "ASSIGNMENT_SUMMARY"
    PENDING_ASSIGNMENTS = "PENDING_ASSIGNMENTS"
    OVERDUE_ASSIGNMENTS = "OVERDUE_ASSIGNMENTS"
    UPCOMING_ASSIGNMENTS = "UPCOMING_ASSIGNMENTS"
    
    # Leave & Availability
    LEAVE_INFORMATION = "LEAVE_INFORMATION"
    AVAILABILITY_LOOKUP = "AVAILABILITY_LOOKUP"
    SUBSTITUTE_LOOKUP = "SUBSTITUTE_LOOKUP"
    
    # Policy & Compliance
    WORKLOAD_LIMIT = "WORKLOAD_LIMIT"
    WORKLOAD_VIOLATION = "WORKLOAD_VIOLATION"
    POLICY_QUERY = "POLICY_QUERY"
    EXEMPTION_LOOKUP = "EXEMPTION_LOOKUP"
    EXCEPTION_LOOKUP = "EXCEPTION_LOOKUP"
    
    # Analytics & Information
    HISTORICAL_WORKLOAD = "HISTORICAL_WORKLOAD"
    DEPARTMENT_ANALYTICS = "DEPARTMENT_ANALYTICS"
    INSTITUTION_ANALYTICS = "INSTITUTION_ANALYTICS"
    ACADEMIC_CALENDAR = "ACADEMIC_CALENDAR"
    FACULTY_INFORMATION = "FACULTY_INFORMATION"
    SUBJECT_INFORMATION = "SUBJECT_INFORMATION"
    DATA_QUALITY = "DATA_QUALITY"
    
    # New Semantic Intents
    DATASET_STATISTICS = "DATASET_STATISTICS"
    HYPOTHETICAL_REASONING = "HYPOTHETICAL_REASONING"
    DATA_AVAILABILITY = "DATA_AVAILABILITY"
    
    HELP = "HELP"
    UNKNOWN_OR_AMBIGUOUS = "UNKNOWN_OR_AMBIGUOUS"


class QueryScope(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    DEPARTMENT = "DEPARTMENT"
    INSTITUTION = "INSTITUTION"
    SUBJECT = "SUBJECT"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"
    DATASET_METRIC = "DATASET_METRIC"
    DATA_AVAILABILITY = "DATA_AVAILABILITY"


class QueryOperation(str, Enum):
    LOOKUP = "LOOKUP"
    FILTER = "FILTER"
    COUNT = "COUNT"
    SUM = "SUM"
    AVERAGE = "AVERAGE"
    MAXIMUM = "MAXIMUM"
    MINIMUM = "MINIMUM"
    RANK = "RANK"
    COMPARE = "COMPARE"
    CALCULATE = "CALCULATE"
    EXPLAIN = "EXPLAIN"
    CHECK_COMPLIANCE = "CHECK_COMPLIANCE"


class MissingFieldType(str, Enum):
    NONE = "NONE"
    SALARY = "SALARY"
    HOME_ADDRESS = "HOME_ADDRESS"
    AGE = "AGE"
    ATTENDANCE_PERCENTAGE = "ATTENDANCE_PERCENTAGE"
    GPA = "GPA"
    DEAN_IDENTITY = "DEAN_IDENTITY"
    HISTORICAL_MONTHLY_BREAKDOWN = "HISTORICAL_MONTHLY_BREAKDOWN"


class TimeGranularity(str, Enum):
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    SEMESTER = "SEMESTER"
    ACADEMIC_YEAR = "ACADEMIC_YEAR"
    CUSTOM_RANGE = "CUSTOM_RANGE"
    UNSPECIFIED = "UNSPECIFIED"


class QueryMetric(str, Enum):
    TEACHING_HOURS = "TEACHING_HOURS"
    CLASS_COUNT = "CLASS_COUNT"
    LECTURE_HOURS = "LECTURE_HOURS"
    TUTORIAL_HOURS = "TUTORIAL_HOURS"
    LABORATORY_HOURS = "LABORATORY_HOURS"
    SESSION_LIST = "SESSION_LIST"
    NEXT_SESSION = "NEXT_SESSION"
    ASSIGNMENT_COUNT = "ASSIGNMENT_COUNT"
    VIOLATION_STATUS = "VIOLATION_STATUS"
    POLICY_LIMIT = "POLICY_LIMIT"
    CONFLICT_LIST = "CONFLICT_LIST"
    LEAVE_STATUS = "LEAVE_STATUS"
    GENERAL_INFO = "GENERAL_INFO"
    DATASET_COUNT = "DATASET_COUNT"


class RequestedOutput(str, Enum):
    TOTAL_HOURS = "TOTAL_HOURS"
    SESSION_COUNT = "SESSION_COUNT"
    TIMETABLE_SCHEDULE = "TIMETABLE_SCHEDULE"
    NEXT_SESSION = "NEXT_SESSION"
    BREAKDOWN = "BREAKDOWN"
    STATUS = "STATUS"
    POLICY_DETAILS = "POLICY_DETAILS"
    LIST = "LIST"
    TEXT_EXPLANATION = "TEXT_EXPLANATION"
    RANKING = "RANKING"


class DateRange(BaseModel):
    start: dt.date
    end: dt.date  # Half-open: start <= date < end

    def contains(self, d: dt.date) -> bool:
        return self.start <= d < self.end


class StructuredQuery(BaseModel):
    raw_query: str
    intent: IntentEnum
    scope: QueryScope = QueryScope.INDIVIDUAL
    operation: QueryOperation = QueryOperation.LOOKUP
    metric: QueryMetric = QueryMetric.TEACHING_HOURS
    time_granularity: TimeGranularity = TimeGranularity.UNSPECIFIED
    
    # Dates & Times
    date: Optional[dt.date] = None
    day_of_week: Optional[str] = None
    month: Optional[int] = None
    year: Optional[int] = None
    date_range: Optional[DateRange] = None
    use_default_week: bool = True
    
    # Entities
    faculty_id: Optional[str] = None
    faculty_name: Optional[str] = None
    department_id: Optional[str] = None
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None
    section_id: Optional[str] = None
    session_type: Optional[str] = None
    designation: Optional[str] = None
    
    # Filters & Constraints
    target_table: Optional[str] = None
    approval_status_filter: Optional[str] = None
    assignment_title_filter: Optional[str] = None
    missing_field: MissingFieldType = MissingFieldType.NONE
    
    # Hypothetical calculation parameters
    hypothetical_actual_hours: Optional[float] = None
    hypothetical_max_hours: Optional[float] = None
    hypothetical_override_hours: Optional[float] = None
    
    # Execution Flags
    requires_database: bool = True
    requires_calculation: bool = False
    requires_policy_engine: bool = False
    
    requested_output: RequestedOutput = RequestedOutput.TEXT_EXPLANATION
    confidence: float = 1.0
    is_follow_up: bool = False
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    extra_filters: Dict[str, Any] = Field(default_factory=dict)
