"""
Database Loader Module.
Loads cleaned dataframes into the relational database idempotently.
Ensures referential integrity order, atomic transaction management, and logging to IngestionHistory.
"""

from typing import Dict, Type
import pandas as pd
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session, init_db
from app.database.models import (
    Base, Department, Faculty, UserRole, Section, Subject,
    WorkloadPolicy, WorkloadRule, FacultySubjectAllocation,
    Timetable, Assignment, LeaveRecord, FacultyAvailability,
    WorkloadExemption, PolicyException, AcademicCalendar,
    HistoricalWorkload, WorkloadSummary, Room, TestQuery,
    IngestionHistory
)


# Ingestion dependency order to satisfy foreign keys
INGESTION_ORDER = [
    ("Departments", Department),
    ("Faculty", Faculty),
    ("Users_Roles", UserRole),
    ("Sections", Section),
    ("Subjects", Subject),
    ("Rooms", Room),
    ("Workload_Policies", WorkloadPolicy),
    ("Workload_Rules", WorkloadRule),
    ("Faculty_Subject_Allocations", FacultySubjectAllocation),
    ("Timetable", Timetable),
    ("Assignments", Assignment),
    ("Leave_Records", LeaveRecord),
    ("Faculty_Availability", FacultyAvailability),
    ("Workload_Exemptions", WorkloadExemption),
    ("Policy_Exceptions", PolicyException),
    ("Academic_Calendar", AcademicCalendar),
    ("Historical_Workload", HistoricalWorkload),
    ("Workload_Summary", WorkloadSummary),
    ("Test_Queries", TestQuery)
]


class DatabaseLoader:
    def __init__(self):
        init_db()

    def load_all(self, cleaned_dfs: Dict[str, pd.DataFrame], source_file: str) -> Dict[str, int]:
        counts = {}
        with get_db_session() as session:
            # Clear existing data in reverse order to ensure clean reload
            for sheet_name, model_cls in reversed(INGESTION_ORDER):
                deleted = session.query(model_cls).delete()
                logger.debug(f"Cleared {deleted} existing records from {model_cls.__tablename__}")

            # Insert in foreign key order
            for sheet_name, model_cls in INGESTION_ORDER:
                if sheet_name not in cleaned_dfs:
                    logger.warning(f"Sheet {sheet_name} not found in cleaned datasets; skipping.")
                    continue

                df = cleaned_dfs[sheet_name]
                records = []
                col_names = {c.name for c in model_cls.__table__.columns}

                for _, row in df.iterrows():
                    # Filter only fields matching model columns
                    row_dict = {k: v for k, v in row.to_dict().items() if k in col_names}
                    # Replace NaN with None for SQLAlchemy
                    for k, v in row_dict.items():
                        if pd.isna(v):
                            row_dict[k] = None
                    records.append(model_cls(**row_dict))

                session.bulk_save_objects(records)
                counts[sheet_name] = len(records)
                logger.info(f"Loaded {len(records)} records into {model_cls.__tablename__}")

                # Record in IngestionHistory
                history = IngestionHistory(
                    source_file=source_file,
                    sheet_name=sheet_name,
                    record_count=len(records),
                    status="SUCCESS",
                    notes=f"Idempotent load of {sheet_name}"
                )
                session.add(history)

        return counts

