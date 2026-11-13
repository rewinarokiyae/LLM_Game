"""
Date and Time Resolution Engine.
Resolves natural language temporal expressions into structured dates, half-open date ranges,
and time granularities using the institutional dataset reference timeframe.
Supports:
- Relative days: today, tomorrow, yesterday
- Named weekdays: Monday .. Sunday (aligned to active academic week 9-13 Nov 2026)
- Weeks: this week, next week, last week, week starting YYYY-MM-DD
- Explicit dates: 2026-11-09, November 20, Nov 11, 20th November
- Months: this month, December 2026, November 2025
- Date ranges: December 2 to December 4, between X and Y
"""

from datetime import date, timedelta, datetime
import re
from typing import Optional, Tuple, Dict, Any
from app.nlp.structured_query import DateRange, TimeGranularity

# Institutional Reference Date: Midweek of the active academic timetable week (9-13 Nov 2026)
REFERENCE_DATE = date(2026, 11, 11)  # Wednesday
REFERENCE_WEEK_START = date(2026, 11, 9)  # Monday
REFERENCE_WEEK_END = date(2026, 11, 13)    # Friday

DAY_NAME_TO_OFFSET = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

MONTH_NAME_TO_INT = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}


class DateResolver:
    @classmethod
    def get_reference_date(cls) -> date:
        return REFERENCE_DATE

    @classmethod
    def resolve_date_and_range(
        cls,
        text: str,
        reference: Optional[date] = None
    ) -> Tuple[TimeGranularity, Optional[date], Optional[str], Optional[DateRange], Optional[int], Optional[int]]:
        """
        Parses text for temporal expressions.
        Returns:
            (TimeGranularity, specific_date, day_of_week_name, half_open_DateRange, month, year)
        Half-open convention: start <= date < end
        """
        ref = reference or REFERENCE_DATE
        q = text.lower().strip()

        # 1. Check relative days: today, tomorrow, yesterday
        if re.search(r"\btoday\b", q):
            d = ref
            return (
                TimeGranularity.DAY,
                d,
                d.strftime("%A"),
                DateRange(start=d, end=d + timedelta(days=1)),
                d.month,
                d.year
            )

        if re.search(r"\btomorrow\b", q):
            d = ref + timedelta(days=1)
            return (
                TimeGranularity.DAY,
                d,
                d.strftime("%A"),
                DateRange(start=d, end=d + timedelta(days=1)),
                d.month,
                d.year
            )

        if re.search(r"\byesterday\b", q):
            d = ref - timedelta(days=1)
            return (
                TimeGranularity.DAY,
                d,
                d.strftime("%A"),
                DateRange(start=d, end=d + timedelta(days=1)),
                d.month,
                d.year
            )

        # 2. Check ISO Dates e.g., 2026-11-09 or 2026-11-12
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", q)
        if iso_match:
            try:
                y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                parsed_d = date(y, m, d)
                return (
                    TimeGranularity.DAY,
                    parsed_d,
                    parsed_d.strftime("%A"),
                    DateRange(start=parsed_d, end=parsed_d + timedelta(days=1)),
                    m,
                    y
                )
            except Exception:
                pass

        # 3. Check explicit Month + Day: e.g. "November 20", "November 11", "Nov 12", "December 2"
        month_day_match = re.search(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*|\s+)?(\d{4})?\b",
            q
        )
        if month_day_match:
            m_str = month_day_match.group(1)
            day_num = int(month_day_match.group(2))
            yr_str = month_day_match.group(3)
            y = int(yr_str) if yr_str else 2026
            m_num = MONTH_NAME_TO_INT[m_str]
            try:
                parsed_d = date(y, m_num, day_num)
                return (
                    TimeGranularity.DAY,
                    parsed_d,
                    parsed_d.strftime("%A"),
                    DateRange(start=parsed_d, end=parsed_d + timedelta(days=1)),
                    m_num,
                    y
                )
            except Exception:
                pass

        # Check Day + Month: e.g. "20th November", "11 November"
        day_month_match = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:\s+(\d{4}))?\b",
            q
        )
        if day_month_match:
            day_num = int(day_month_match.group(1))
            m_str = day_month_match.group(2)
            yr_str = day_month_match.group(3)
            y = int(yr_str) if yr_str else 2026
            m_num = MONTH_NAME_TO_INT[m_str]
            try:
                parsed_d = date(y, m_num, day_num)
                return (
                    TimeGranularity.DAY,
                    parsed_d,
                    parsed_d.strftime("%A"),
                    DateRange(start=parsed_d, end=parsed_d + timedelta(days=1)),
                    m_num,
                    y
                )
            except Exception:
                pass

        # 4. Check explicit days of the week: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
        for day_name, offset in DAY_NAME_TO_OFFSET.items():
            pattern = rf"\b{day_name}\b"
            if re.search(pattern, q):
                # Target timetable week starts at Monday 2026-11-09
                target_date = REFERENCE_WEEK_START + timedelta(days=offset)
                return (
                    TimeGranularity.DAY,
                    target_date,
                    day_name.capitalize(),
                    DateRange(start=target_date, end=target_date + timedelta(days=1)),
                    target_date.month,
                    target_date.year
                )

        # 5. Check weeks: this week, next week, last week, week starting YYYY-MM-DD
        week_iso_match = re.search(r"\bweek\s+(?:starting|of|commencing)?\s*(\d{4}-\d{2}-\d{2})\b", q)
        if week_iso_match:
            try:
                parts = [int(x) for x in week_iso_match.group(1).split("-")]
                start = date(parts[0], parts[1], parts[2])
                end = start + timedelta(days=7)
                return (
                    TimeGranularity.WEEK,
                    start,
                    None,
                    DateRange(start=start, end=end),
                    start.month,
                    start.year
                )
            except Exception:
                pass

        if re.search(r"\bthis\s+week\b", q) or re.search(r"\bcurrent\s+week\b", q):
            start = REFERENCE_WEEK_START
            end = start + timedelta(days=7)  # Half-open: [2026-11-09, 2026-11-16)
            return (
                TimeGranularity.WEEK,
                start,
                None,
                DateRange(start=start, end=end),
                start.month,
                start.year
            )

        if re.search(r"\bnext\s+week\b", q):
            start = REFERENCE_WEEK_START + timedelta(days=7)
            end = start + timedelta(days=7)
            return (
                TimeGranularity.WEEK,
                start,
                None,
                DateRange(start=start, end=end),
                start.month,
                start.year
            )

        if re.search(r"\blast\s+week\b", q) or re.search(r"\bprevious\s+week\b", q):
            start = REFERENCE_WEEK_START - timedelta(days=7)
            end = REFERENCE_WEEK_START
            return (
                TimeGranularity.WEEK,
                start,
                None,
                DateRange(start=start, end=end),
                start.month,
                start.year
            )

        # 6. Check Date Ranges: e.g. "from December 2 to December 4" or "December 2 to December 4"
        range_match = re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\s+(?:to|until|-|through)\s+(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+)?(\d{1,2})\b",
            q
        )
        if range_match:
            try:
                m1_str = range_match.group(1)
                d1 = int(range_match.group(2))
                m2_str = range_match.group(3) or m1_str
                d2 = int(range_match.group(4))
                m1 = MONTH_NAME_TO_INT[m1_str]
                m2 = MONTH_NAME_TO_INT[m2_str]
                y = 2026
                y_match = re.search(r"\b(202[0-9])\b", q)
                if y_match:
                    y = int(y_match.group(1))
                start_dt = date(y, m1, d1)
                end_dt = date(y, m2, d2) + timedelta(days=1)  # Half-open
                return (
                    TimeGranularity.CUSTOM_RANGE,
                    start_dt,
                    None,
                    DateRange(start=start_dt, end=end_dt),
                    m1,
                    y
                )
            except Exception:
                pass

        # 7. Check months: this month, next month, last month, or named months
        if re.search(r"\bthis\s+month\b", q) or re.search(r"\bcurrent\s+month\b", q):
            start = date(ref.year, ref.month, 1)
            next_m = 1 if ref.month == 12 else ref.month + 1
            next_y = ref.year + 1 if ref.month == 12 else ref.year
            end = date(next_y, next_m, 1)
            return (
                TimeGranularity.MONTH,
                None,
                None,
                DateRange(start=start, end=end),
                ref.month,
                ref.year
            )

        if re.search(r"\bnext\s+month\b", q):
            nm = 1 if ref.month == 12 else ref.month + 1
            ny = ref.year + 1 if ref.month == 12 else ref.year
            start = date(ny, nm, 1)
            nnm = 1 if nm == 12 else nm + 1
            nny = ny + 1 if nm == 12 else ny
            end = date(nny, nnm, 1)
            return (
                TimeGranularity.MONTH,
                None,
                None,
                DateRange(start=start, end=end),
                nm,
                ny
            )

        if re.search(r"\blast\s+month\b", q) or re.search(r"\bprevious\s+month\b", q):
            pm = 12 if ref.month == 1 else ref.month - 1
            py = ref.year - 1 if ref.month == 1 else ref.year
            start = date(py, pm, 1)
            end = date(ref.year, ref.month, 1)
            return (
                TimeGranularity.MONTH,
                None,
                None,
                DateRange(start=start, end=end),
                pm,
                py
            )

        for m_name, m_num in MONTH_NAME_TO_INT.items():
            if re.search(rf"\b{m_name}\b", q):
                y = 2026
                y_match = re.search(r"\b(202[0-9])\b", q)
                if y_match:
                    y = int(y_match.group(1))
                start = date(y, m_num, 1)
                nm = 1 if m_num == 12 else m_num + 1
                ny = y + 1 if m_num == 12 else y
                end = date(ny, nm, 1)
                return (
                    TimeGranularity.MONTH,
                    None,
                    None,
                    DateRange(start=start, end=end),
                    m_num,
                    y
                )

        # 8. Check Semesters & Academic terms
        if re.search(r"\b(previous|last|past|prior)\s+semester\b", q):
            return (
                TimeGranularity.SEMESTER,
                None,
                None,
                DateRange(start=date(2026, 1, 1), end=date(2026, 7, 1)),
                None,
                2026
            )

        if re.search(r"\b(this|current)\s+semester\b", q):
            return (
                TimeGranularity.SEMESTER,
                None,
                None,
                DateRange(start=date(2026, 8, 1), end=date(2027, 1, 1)),
                None,
                2026
            )

        # Default: Unspecified
        return (TimeGranularity.UNSPECIFIED, None, None, None, None, None)
