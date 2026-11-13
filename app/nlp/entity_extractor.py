"""
Entity Extractor Module.
Extracts domain-specific entities from natural-language queries:
- Faculty IDs (FAC001 - FAC018)
- Faculty Names
- Department IDs (DEP-CSE, DEP-AIML, DEP-DS) and Department Codes (CSE, AIML, DS)
- Subject IDs (CS501 - DS704) and Names
- Section IDs (e.g. CSE-S5-A)
- Days of the week (Monday, Tuesday, Wednesday, Thursday, Friday, today, tomorrow)
- Dates (YYYY-MM-DD)
- Assignment types and statuses
"""

import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from app.engines.workload_engine import DEFAULT_TARGET_WEEK

# Known mappings from synthetic dataset
FACULTY_NAME_MAP = {
    "meera": "FAC001", "meera nair": "FAC001", "dr. meera nair": "FAC001",
    "arjun": "FAC002", "arjun menon": "FAC002",
    "kavya": "FAC003", "kavya sharma": "FAC003",
    "rahul": "FAC004", "rahul das": "FAC004",
    "sneha": "FAC005", "sneha thomas": "FAC005",
    "nikhil": "FAC006", "nikhil varma": "FAC006",
    "vikram": "FAC007", "vikram rao": "FAC007", "dr. vikram rao": "FAC007",
    "priya": "FAC008", "priya krishnan": "FAC008",
    "aditya": "FAC009", "aditya bose": "FAC009",
    "ishita": "FAC010", "ishita kapoor": "FAC010",
    "rohan": "FAC011", "rohan shetty": "FAC011",
    "divya": "FAC012", "divya pillai": "FAC012",
    "ananya": "FAC013", "ananya iyer": "FAC013", "dr. ananya iyer": "FAC013",
    "sanjay": "FAC014", "sanjay kulkarni": "FAC014",
    "neha": "FAC015", "neha reddy": "FAC015",
    "karthik": "FAC016", "karthik bhat": "FAC016",
    "farah": "FAC017", "farah khan": "FAC017",
    "manoj": "FAC018", "manoj joseph": "FAC018"
}

DEPT_NAME_MAP = {
    "cse": "DEP-CSE", "computer science": "DEP-CSE", "computer science and engineering": "DEP-CSE", "dep-cse": "DEP-CSE",
    "aiml": "DEP-AIML", "ai & ml": "DEP-AIML", "artificial intelligence": "DEP-AIML", "artificial intelligence and machine learning": "DEP-AIML", "dep-aiml": "DEP-AIML",
    "ds": "DEP-DS", "data science": "DEP-DS", "dep-ds": "DEP-DS"
}

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class EntityExtractor:
    @classmethod
    def extract_entities(cls, query: str, default_faculty_id: Optional[str] = None) -> Dict[str, Any]:
        text = query.strip()
        text_lower = text.lower()
        entities: Dict[str, Any] = {}

        # 1. Faculty ID regex (FAC\d{3})
        fac_match = re.search(r'\b(FAC\d{3})\b', text, re.IGNORECASE)
        if fac_match:
            entities["faculty_id"] = fac_match.group(1).upper()
        else:
            # Check by faculty name
            for name, fid in FACULTY_NAME_MAP.items():
                pattern = r'\b' + re.escape(name) + r'\b'
                if re.search(pattern, text_lower):
                    entities["faculty_id"] = fid
                    break

        # If user refers to self ("my", "i", "me") and default_faculty_id is present
        if not entities.get("faculty_id"):
            if re.search(r'\b(my|i|me|am i|myself)\b', text_lower) and default_faculty_id:
                entities["faculty_id"] = default_faculty_id

        # 2. Department ID / Code
        dept_match = re.search(r'\b(DEP-[A-Z]+)\b', text, re.IGNORECASE)
        if dept_match:
            entities["department_id"] = dept_match.group(1).upper()
        else:
            for dname, did in DEPT_NAME_MAP.items():
                pattern = r'\b' + re.escape(dname) + r'\b'
                if re.search(pattern, text_lower):
                    entities["department_id"] = did
                    break

        # 3. Subject ID (e.g. CS501, AI501, DS501)
        sub_match = re.search(r'\b([A-Z]{2}\d{3})\b', text, re.IGNORECASE)
        if sub_match:
            entities["subject_id"] = sub_match.group(1).upper()

        # 4. Section ID (e.g. CSE-S5-A, AIML-S7-B)
        sec_match = re.search(r'\b([A-Z]+-S\d-[A-Z])\b', text, re.IGNORECASE)
        if sec_match:
            entities["section_id"] = sec_match.group(1).upper()

        # 5. Day of week
        for d in DAYS_OF_WEEK:
            if re.search(r'\b' + re.escape(d.lower()) + r'\b', text_lower):
                entities["day"] = d
                break

        # Relative days (today, tomorrow) relative to sample week Wednesday 2026-11-11
        if not entities.get("day"):
            if "today" in text_lower:
                entities["day"] = "Wednesday"  # Midpoint of sample week
            elif "tomorrow" in text_lower:
                entities["day"] = "Thursday"

        # 6. Specific Date (YYYY-MM-DD or Month DD)
        date_match = re.search(r'\b(202[6-7]-\d{2}-\d{2})\b', text)
        if date_match:
            try:
                entities["date"] = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
            except Exception:
                pass

        # 7. Assignment / Activity Type
        if "project" in text_lower or "supervision" in text_lower:
            entities["assignment_type"] = "Project Supervision"
        elif "exam" in text_lower or "invigilation" in text_lower:
            entities["assignment_type"] = "Examination Duty"
        elif "question paper" in text_lower:
            entities["assignment_type"] = "Question Paper Preparation"
        elif "internal assessment" in text_lower or "evaluation" in text_lower:
            entities["assignment_type"] = "Internal Assessment Evaluation"

        # 8. Status filter
        if "pending" in text_lower:
            entities["status"] = "Pending"
        elif "completed" in text_lower:
            entities["status"] = "Completed"
        elif "approved" in text_lower:
            entities["status"] = "Approved"
        elif "rejected" in text_lower:
            entities["status"] = "Rejected"
        elif "overdue" in text_lower:
            entities["overdue"] = True

        # 9. Faculty Designation (Order longer specific designations before generic Professor)
        for desig in ["Associate Professor", "Assistant Professor", "Professor", "Lecturer"]:
            if desig.lower() in text_lower:
                entities["designation"] = desig
                break

        return entities

