"""
Data Cleaner and Normalizer.
Applies explicit handling for reported dataset anomalies in memory,
ensuring clean types, dates, and referential integrity for database persistence.
Never alters the original source Excel workbook.
"""

from datetime import datetime, date, time
from typing import Dict, Any
import pandas as pd
import numpy as np
from app.config.logging_config import logger


class DataCleaner:
    @staticmethod
    def to_date(val: Any) -> Any:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return None
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return pd.to_datetime(val).date()
        except Exception:
            return None

    @staticmethod
    def clean_string(val: Any) -> Any:
        if pd.isna(val) or val is None:
            return None
        val_str = str(val).strip()
        return val_str if val_str != "" else None

    @staticmethod
    def clean_faculty_availability(df: pd.DataFrame) -> pd.DataFrame:
        """
        Explicitly corrects the reported shifted column anomaly in Faculty_Availability.
        Source headers: ['availability_id', 'faculty_id', 'period_start', 'period_end',
                         'availability_status', 'available_from', 'available_to', 'notes']
        Source data: ['AV-FAC001', '2026-11-09', '2026-11-13', 'Available', '08:30', '18:00',
                      'Standard working week', None]
        """
        cleaned_rows = []
        for _, row in df.iterrows():
            avail_id = str(row["availability_id"]).strip()
            # Derive faculty_id from availability_id (AV-FAC001 -> FAC001)
            derived_fac_id = avail_id.replace("AV-", "")

            # Recover shifted columns
            period_start = DataCleaner.to_date(row["faculty_id"])
            period_end = DataCleaner.to_date(row["period_start"])
            avail_status = DataCleaner.clean_string(row["period_end"]) or "Available"
            avail_from = DataCleaner.clean_string(row["availability_status"]) or "08:30"
            avail_to = DataCleaner.clean_string(row["available_from"]) or "18:00"
            notes = DataCleaner.clean_string(row["available_to"]) or "Standard working week"

            cleaned_rows.append({
                "availability_id": avail_id,
                "faculty_id": derived_fac_id,
                "period_start": period_start,
                "period_end": period_end,
                "availability_status": avail_status,
                "available_from": avail_from,
                "available_to": avail_to,
                "notes": notes
            })

        logger.info(f"Cleaned {len(cleaned_rows)} Faculty_Availability rows by resolving shifted columns.")
        return pd.DataFrame(cleaned_rows)

    @staticmethod
    def clean_timetable(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans timetable records and computes normalized_room for room lookup and conflict detection.
        Preserves original raw room name.
        """
        cleaned_rows = []
        for _, row in df.iterrows():
            r = row.to_dict()
            raw_room = DataCleaner.clean_string(r.get("room"))
            norm_room = raw_room

            if raw_room:
                if raw_room.startswith("IML-"):
                    norm_room = "A" + raw_room  # IML-202 -> AIML-202
                elif raw_room.startswith("-DS-"):
                    norm_room = raw_room[1:]  # -DS-203 -> DS-203

            r["room"] = raw_room
            r["normalized_room"] = norm_room
            r["week_start"] = DataCleaner.to_date(r.get("week_start"))
            r["week_end"] = DataCleaner.to_date(r.get("week_end"))
            r["duration_hours"] = float(r.get("duration_hours", 1.0))
            r["status"] = DataCleaner.clean_string(r.get("status")) or "Active"
            r["substitute_for_faculty_id"] = DataCleaner.clean_string(r.get("substitute_for_faculty_id"))
            r["substitution_of_timetable_id"] = DataCleaner.clean_string(r.get("substitution_of_timetable_id"))
            r["version"] = DataCleaner.clean_string(r.get("version")) or "v1"

            cleaned_rows.append(r)

        return pd.DataFrame(cleaned_rows)

    @classmethod
    def clean_all(cls, raw_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        cleaned = {}
        date_cols = [
            "joining_date", "valid_from", "valid_to", "effective_from",
            "effective_to", "assigned_date", "due_date", "start_date",
            "end_date", "week_start", "week_end", "period_start", "period_end"
        ]

        for name, df in raw_dfs.items():
            df_copy = df.copy()

            if name == "Faculty_Availability":
                cleaned[name] = cls.clean_faculty_availability(df_copy)
                continue

            if name == "Timetable":
                cleaned[name] = cls.clean_timetable(df_copy)
                continue

            # Clean all string columns except date columns
            for col in df_copy.columns:
                if col not in date_cols and df_copy[col].dtype == object:
                    df_copy[col] = df_copy[col].apply(cls.clean_string)

            # Standard date conversions based on column names
            for col in date_cols:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(cls.to_date)

            cleaned[name] = df_copy

        return cleaned
