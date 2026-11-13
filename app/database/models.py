"""
SQLAlchemy ORM Models corresponding to all worksheets and operational tables.
Maintains primary keys, foreign keys, relationships, indexes, and constraints.
"""

from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, Time, DateTime,
    ForeignKey, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==========================================
# 1. CORE ACADEMIC ENTITIES
# ==========================================

class Department(Base):
    __tablename__ = "departments"

    department_id = Column(String(50), primary_key=True)
    department_name = Column(String(100), nullable=False)
    hod_name = Column(String(100), nullable=True)
    hod_faculty_id = Column(String(50), nullable=True)
    department_code = Column(String(20), nullable=False)

    faculty_members = relationship("Faculty", back_populates="department")
    sections = relationship("Section", back_populates="department")
    subjects = relationship("Subject", back_populates="department")
    rooms = relationship("Room", back_populates="department")


class Faculty(Base):
    __tablename__ = "faculty"

    faculty_id = Column(String(50), primary_key=True)
    faculty_name = Column(String(100), nullable=False, index=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    designation = Column(String(50), nullable=False, index=True)
    faculty_category = Column(String(50), nullable=True)
    qualification = Column(String(100), nullable=True)
    specialization = Column(String(150), nullable=True)
    joining_date = Column(Date, nullable=True)
    employment_status = Column(String(50), nullable=True)
    employment_type = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True)

    department = relationship("Department", back_populates="faculty_members")
    user_account = relationship("UserRole", back_populates="faculty", uselist=False)
    allocations = relationship("FacultySubjectAllocation", back_populates="faculty")
    timetable_entries = relationship("Timetable", back_populates="faculty", foreign_keys="Timetable.faculty_id")
    assignments = relationship("Assignment", back_populates="faculty")
    leave_records = relationship("LeaveRecord", back_populates="faculty", foreign_keys="LeaveRecord.faculty_id")
    availability_records = relationship("FacultyAvailability", back_populates="faculty")
    exemptions = relationship("WorkloadExemption", back_populates="faculty")
    exceptions = relationship("PolicyException", back_populates="faculty")
    historical_workload = relationship("HistoricalWorkload", back_populates="faculty")


class UserRole(Base):
    __tablename__ = "users_roles"

    user_id = Column(String(50), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=True, index=True)
    role = Column(String(20), nullable=False, index=True)  # FACULTY, HOD, ADMIN
    department_scope = Column(String(50), nullable=False)  # e.g., DEP-CSE or ALL
    account_status = Column(String(20), default="Active")
    notes = Column(Text, nullable=True)

    faculty = relationship("Faculty", back_populates="user_account")


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(String(50), primary_key=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    program_code = Column(String(20), nullable=True)
    section_name = Column(String(50), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=False)

    department = relationship("Department", back_populates="sections")
    timetable_entries = relationship("Timetable", back_populates="section")


class Subject(Base):
    __tablename__ = "subjects"

    subject_id = Column(String(50), primary_key=True)
    subject_name = Column(String(150), nullable=False, index=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    semester = Column(Integer, nullable=False)
    weekly_theory_hours_reference = Column(Float, default=0.0)
    weekly_practical_hours_reference = Column(Float, default=0.0)
    weekly_tutorial_hours_reference = Column(Float, default=0.0)
    subject_type = Column(String(50), nullable=True)
    credits = Column(Integer, default=3)
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=False)

    department = relationship("Department", back_populates="subjects")
    timetable_entries = relationship("Timetable", back_populates="subject")


class Room(Base):
    __tablename__ = "rooms"

    room_id = Column(String(50), primary_key=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False)
    room_type = Column(String(50), nullable=False)
    capacity = Column(Integer, default=60)
    status = Column(String(20), default="Available")

    department = relationship("Department", back_populates="rooms")


# ==========================================
# 2. WORKLOAD POLICY & RULES
# ==========================================

class WorkloadPolicy(Base):
    __tablename__ = "workload_policies"

    policy_id = Column(String(50), primary_key=True)
    designation = Column(String(50), nullable=False, index=True)
    department_scope = Column(String(50), default="ALL")
    max_teaching_hours_week = Column(Float, nullable=False)
    min_teaching_hours_week = Column(Float, nullable=False)
    measurement_period = Column(String(50), default="weekly")
    calculation_rule = Column(Text, nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=False)
    source_document = Column(String(200), nullable=True)
    source_page = Column(Integer, nullable=True)


class WorkloadRule(Base):
    __tablename__ = "workload_rules"

    rule_id = Column(String(50), primary_key=True)
    session_type = Column(String(50), nullable=False, unique=True)
    weight = Column(Float, default=1.0)
    calculation_method = Column(String(100), nullable=True)
    included_in_teaching_hours = Column(String(20), default="Included")  # Included / Excluded
    rule_description = Column(Text, nullable=True)


class WorkloadExemption(Base):
    __tablename__ = "workload_exemptions"

    exemption_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    responsibility = Column(String(100), nullable=False)
    relief_hours_per_week = Column(Float, nullable=False)
    period = Column(String(50), default="weekly")
    approval_status = Column(String(20), nullable=False, index=True)  # Approved, Pending, Rejected
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)

    faculty = relationship("Faculty", back_populates="exemptions")


class PolicyException(Base):
    __tablename__ = "policy_exceptions"

    exception_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    policy_id = Column(String(50), ForeignKey("workload_policies.policy_id"), nullable=False)
    max_hours_override = Column(Float, nullable=False)
    approval_status = Column(String(20), nullable=False, index=True)  # Approved, Pending, Rejected
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    faculty = relationship("Faculty", back_populates="exceptions")


# ==========================================
# 3. SCHEDULES, ALLOCATIONS & TIMETABLE
# ==========================================

class FacultySubjectAllocation(Base):
    __tablename__ = "faculty_subject_allocations"

    allocation_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    subject_id = Column(String(50), ForeignKey("subjects.subject_id"), nullable=False, index=True)
    section_id = Column(String(50), ForeignKey("sections.section_id"), nullable=False, index=True)
    allocation_type = Column(String(50), default="Theory")
    approval_status = Column(String(20), default="Approved")
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)

    faculty = relationship("Faculty", back_populates="allocations")


class Timetable(Base):
    __tablename__ = "timetable"

    timetable_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    faculty_name = Column(String(100), nullable=True)
    subject_id = Column(String(50), ForeignKey("subjects.subject_id"), nullable=False, index=True)
    section_id = Column(String(50), ForeignKey("sections.section_id"), nullable=False, index=True)
    day = Column(String(20), nullable=False, index=True)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    duration_hours = Column(Float, nullable=False)
    session_type = Column(String(50), nullable=False)
    room = Column(String(50), nullable=True, index=True)
    normalized_room = Column(String(50), nullable=True, index=True)
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=False)
    week_start = Column(Date, nullable=False, index=True)
    week_end = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, index=True)  # Active, Cancelled, Substituted
    substitute_for_faculty_id = Column(String(50), nullable=True, index=True)
    substitution_of_timetable_id = Column(String(50), nullable=True, index=True)
    version = Column(String(20), default="v1")

    faculty = relationship("Faculty", back_populates="timetable_entries", foreign_keys=[faculty_id])
    subject = relationship("Subject", back_populates="timetable_entries")
    section = relationship("Section", back_populates="timetable_entries")

    __table_args__ = (
        Index("idx_timetable_fac_day", "faculty_id", "day", "week_start"),
        Index("idx_timetable_room_day", "room", "day", "week_start"),
        Index("idx_timetable_sec_day", "section_id", "day", "week_start"),
    )


# ==========================================
# 4. ASSIGNMENTS & LEAVE
# ==========================================

class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    assignment_type = Column(String(100), nullable=False, index=True)
    subject_id = Column(String(50), ForeignKey("subjects.subject_id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    assigned_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # Pending, In Progress, Completed
    priority = Column(String(20), default="Medium")
    academic_year = Column(String(20), nullable=False)
    term = Column(String(20), nullable=False)
    assigned_by = Column(String(100), nullable=True)

    faculty = relationship("Faculty", back_populates="assignments")


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    leave_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    approval_status = Column(String(20), nullable=False, index=True)  # Approved, Pending, Rejected
    replacement_faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=True)
    reason = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)

    faculty = relationship("Faculty", back_populates="leave_records", foreign_keys=[faculty_id])


class FacultyAvailability(Base):
    __tablename__ = "faculty_availability"

    availability_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    availability_status = Column(String(50), default="Available")
    available_from = Column(String(20), nullable=True)
    available_to = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    faculty = relationship("Faculty", back_populates="availability_records")


# ==========================================
# 5. CALENDAR, HISTORICAL & VALIDATION
# ==========================================

class AcademicCalendar(Base):
    __tablename__ = "academic_calendar"

    calendar_event_id = Column(String(50), primary_key=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    event_name = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)  # Teaching, Holiday, Assessment, Vacation
    description = Column(Text, nullable=True)
    scope = Column(String(50), default="University")


class HistoricalWorkload(Base):
    __tablename__ = "historical_workload"

    history_id = Column(String(50), primary_key=True)
    faculty_id = Column(String(50), ForeignKey("faculty.faculty_id"), nullable=False, index=True)
    academic_year = Column(String(20), nullable=False, index=True)
    term = Column(String(20), nullable=False)
    average_weekly_teaching_hours = Column(Float, nullable=False)
    average_weekly_assignment_count = Column(Float, nullable=False)
    measurement_basis = Column(String(100), nullable=True)
    data_note = Column(Text, nullable=True)

    faculty = relationship("Faculty", back_populates="historical_workload")


class WorkloadSummary(Base):
    """Reference summary sheet from dataset for validation comparisons."""
    __tablename__ = "workload_summary"

    faculty_id = Column(String(50), primary_key=True)
    faculty_name = Column(String(100), nullable=False)
    department_id = Column(String(50), nullable=False)
    designation = Column(String(50), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    actual_teaching_hours = Column(Float, nullable=False)
    standard_policy_max_hours = Column(Float, nullable=False)
    effective_max_hours = Column(Float, nullable=False)
    excess_hours = Column(Float, nullable=False)
    policy_violation = Column(String(10), nullable=False)
    calculation_note = Column(Text, nullable=True)


class TestQuery(Base):
    """Test queries from dataset for test runner validation."""
    __tablename__ = "test_queries"

    test_id = Column(String(50), primary_key=True)
    required_role = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    required_data_sheets = Column(String(200), nullable=True)
    expected_processing = Column(Text, nullable=True)
    validation_expectation = Column(Text, nullable=True)


# ==========================================
# 6. OPERATIONAL TABLES (AUDIT, CHAT, RAG, EVAL)
# ==========================================

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    username = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50), nullable=True, index=True)
    username = Column(String(50), nullable=True)
    role = Column(String(20), nullable=True)
    department_scope = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, DENIED, ERROR


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), unique=True, nullable=False)
    document_name = Column(String(200), nullable=False)
    department = Column(String(50), default="ALL")
    policy_id = Column(String(50), nullable=True)
    academic_year = Column(String(20), nullable=True)
    effective_date = Column(Date, nullable=True)
    version = Column(String(20), default="1.0")
    file_path = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestionHistory(Base):
    __tablename__ = "ingestion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(200), nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    sheet_name = Column(String(100), nullable=False)
    record_count = Column(Integer, nullable=False)
    status = Column(String(20), default="SUCCESS")
    notes = Column(Text, nullable=True)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(String(50), nullable=False, index=True)
    question = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)
    intent = Column(String(50), nullable=True)
    expected_answer = Column(Text, nullable=True)
    actual_answer = Column(Text, nullable=True)
    passed = Column(Boolean, nullable=False)
    run_timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

