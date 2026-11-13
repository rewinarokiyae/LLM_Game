"""
Tests for Data Ingestion and Validation.
"""

import os
import pytest
from app.ingestion.excel_reader import ExcelReader
from app.ingestion.data_cleaner import DataCleaner
from app.ingestion.data_validator import DatasetAuditor
from app.config.settings import settings


def test_excel_reader_loads_all_sheets():
    reader = ExcelReader(settings.DATASET_PATH)
    assert len(reader.sheet_names) == 21
    assert "Departments" in reader.sheet_names
    assert "Faculty" in reader.sheet_names
    assert "Timetable" in reader.sheet_names
    assert "Workload_Policies" in reader.sheet_names


def test_data_cleaner_faculty_availability():
    reader = ExcelReader(settings.DATASET_PATH)
    raw_df = reader.read_sheet("Faculty_Availability")
    cleaned_df = DataCleaner.clean_faculty_availability(raw_df)

    assert "faculty_id" in cleaned_df.columns
    # Check that faculty_id was correctly extracted from availability_id (AV-FAC001 -> FAC001)
    assert cleaned_df["faculty_id"].iloc[0] == "FAC001"
    assert cleaned_df["availability_status"].iloc[0] in ["Available", "Partially Unavailable"]


def test_data_cleaner_timetable_rooms():
    reader = ExcelReader(settings.DATASET_PATH)
    raw_df = reader.read_sheet("Timetable")
    cleaned_df = DataCleaner.clean_timetable(raw_df)

    assert "normalized_room" in cleaned_df.columns
    # Verify no normalized room starts with '-DS-' or 'IML-'
    for r in cleaned_df["normalized_room"].dropna():
        assert not r.startswith("-DS-")
        assert not r.startswith("IML-")


def test_dataset_auditor_workload_validation():
    auditor = DatasetAuditor(settings.DATASET_PATH)
    results = auditor.run_full_audit()

    assert results["summary"]["independent_workload_validation"] == "PASSED"
    assert results["workload_calculation_validation"]["perfect_matches"] == 18
    assert len(results["workload_calculation_validation"]["mismatches"]) == 0

