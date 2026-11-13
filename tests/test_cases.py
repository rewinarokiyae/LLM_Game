"""
Predefined Test Dataset for LLM Audit Framework.
Contains 69 ground-truth test cases across Categories A through I:
- CATEGORY A: Faculty Workload Questions (1-10)
- CATEGORY B: Department-wise Workload (11-18)
- CATEGORY C: Workload Policies and Exemptions (19-25)
- CATEGORY D: Leave Management (26-31)
- CATEGORY E: Assignment Management (32-38)
- CATEGORY F: Timetable and Teaching-hour Calculation (39-48)
- CATEGORY G: Subject-related Questions (49-54)
- CATEGORY H: Advanced Reasoning Questions (55-62)
- CATEGORY I: Hallucination and Missing Information Tests (63-69)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class TestCase:
    __test__ = False
    id: str
    category: str
    category_name: str
    question: str
    expected_answer: str
    expected_numbers: List[float] = field(default_factory=list)
    expected_entities: List[str] = field(default_factory=list)
    is_missing_info: bool = False
    expected_negative: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


TEST_CASES: List[TestCase] = [
    # =========================================================================
    # CATEGORY A: Faculty Workload Questions (1-10)
    # =========================================================================
    TestCase(
        id="Q001",
        category="A",
        category_name="Faculty Workload",
        question="How many teaching hours does FAC001 have for the week starting 2026-11-09?",
        expected_answer="15 hours.",
        expected_numbers=[15.0],
        expected_entities=["FAC001", "Meera Nair"]
    ),
    TestCase(
        id="Q002",
        category="A",
        category_name="Faculty Workload",
        question="What is the weekly teaching workload of Arjun Menon?",
        expected_answer="17 hours.",
        expected_numbers=[17.0],
        expected_entities=["Arjun Menon", "FAC002"]
    ),
    TestCase(
        id="Q003",
        category="A",
        category_name="Faculty Workload",
        question="Is Dr. Meera Nair exceeding her workload limit?",
        expected_answer="Yes. Actual workload is 15 hours, maximum workload is 12 hours, and excess workload is 3 hours.",
        expected_numbers=[15.0, 12.0, 3.0],
        expected_entities=["Meera Nair", "Yes"]
    ),
    TestCase(
        id="Q004",
        category="A",
        category_name="Faculty Workload",
        question="What is the workload of Aditya Bose?",
        expected_answer="19 hours.",
        expected_numbers=[19.0],
        expected_entities=["Aditya Bose", "FAC009"]
    ),
    TestCase(
        id="Q005",
        category="A",
        category_name="Faculty Workload",
        question="Which faculty member has the highest teaching workload?",
        expected_answer="Aditya Bose (FAC009) and Manoj Joseph (FAC018) are tied at 19 hours each.",
        expected_numbers=[19.0],
        expected_entities=["Aditya Bose", "Manoj Joseph", "FAC009", "FAC018"]
    ),
    TestCase(
        id="Q006",
        category="A",
        category_name="Faculty Workload",
        question="Is Kavya Sharma violating the workload policy?",
        expected_answer="No. Actual workload is 13 hours and maximum workload is 16 hours.",
        expected_numbers=[13.0, 16.0],
        expected_entities=["Kavya Sharma", "No"]
    ),
    TestCase(
        id="Q007",
        category="A",
        category_name="Faculty Workload",
        question="How many hours above the limit is Neha Reddy?",
        expected_answer="2 hours. Actual workload is 18 hours and effective maximum is 16 hours.",
        expected_numbers=[2.0, 18.0, 16.0],
        expected_entities=["Neha Reddy", "FAC015"]
    ),
    TestCase(
        id="Q008",
        category="A",
        category_name="Faculty Workload",
        question="What is the effective workload limit of a Professor?",
        expected_answer="12 teaching hours per week.",
        expected_numbers=[12.0],
        expected_entities=["Professor"]
    ),
    TestCase(
        id="Q009",
        category="A",
        category_name="Faculty Workload",
        question="What is the maximum workload for an Associate Professor?",
        expected_answer="14 teaching hours per week.",
        expected_numbers=[14.0],
        expected_entities=["Associate Professor"]
    ),
    TestCase(
        id="Q010",
        category="A",
        category_name="Faculty Workload",
        question="What is the maximum workload for a Lecturer?",
        expected_answer="18 teaching hours per week.",
        expected_numbers=[18.0],
        expected_entities=["Lecturer"]
    ),

    # =========================================================================
    # CATEGORY B: Department-wise Workload (11-18)
    # =========================================================================
    TestCase(
        id="Q011",
        category="B",
        category_name="Department Workload",
        question="Which faculty members in DEP-CSE exceed their policy limits?",
        expected_answer="Dr. Meera Nair (FAC001), Arjun Menon (FAC002), Rahul Das (FAC004), and Sneha Thomas (FAC005).",
        expected_entities=["Meera Nair", "Arjun Menon", "Rahul Das", "Sneha Thomas", "FAC001", "FAC002", "FAC004", "FAC005"]
    ),
    TestCase(
        id="Q012",
        category="B",
        category_name="Department Workload",
        question="How many faculty members in CSE violate workload policy?",
        expected_answer="4.",
        expected_numbers=[4.0],
        expected_entities=["CSE"]
    ),
    TestCase(
        id="Q013",
        category="B",
        category_name="Department Workload",
        question="Which faculty members in AIML exceed their workload limits?",
        expected_answer="Dr. Vikram Rao (FAC007) and Priya Krishnan (FAC008).",
        expected_entities=["Vikram Rao", "Priya Krishnan", "FAC007", "FAC008"]
    ),
    TestCase(
        id="Q014",
        category="B",
        category_name="Department Workload",
        question="How many faculty members in Data Science exceed their workload limits?",
        expected_answer="3.",
        expected_numbers=[3.0],
        expected_entities=["Data Science"]
    ),
    TestCase(
        id="Q015",
        category="B",
        category_name="Department Workload",
        question="Which department has the highest number of workload violations?",
        expected_answer="CSE, with 4 violations.",
        expected_numbers=[4.0],
        expected_entities=["CSE"]
    ),
    TestCase(
        id="Q016",
        category="B",
        category_name="Department Workload",
        question="List all faculty members who violate workload policy across all departments.",
        expected_answer="FAC001, FAC002, FAC004, FAC005, FAC007, FAC008, FAC014, FAC015, and FAC018.",
        expected_entities=["FAC001", "FAC002", "FAC004", "FAC005", "FAC007", "FAC008", "FAC014", "FAC015", "FAC018"]
    ),
    TestCase(
        id="Q017",
        category="B",
        category_name="Department Workload",
        question="How many faculty members are there in the dataset?",
        expected_answer="18.",
        expected_numbers=[18.0]
    ),
    TestCase(
        id="Q018",
        category="B",
        category_name="Department Workload",
        question="How many departments are present?",
        expected_answer="3 departments: CSE, AIML, and Data Science.",
        expected_numbers=[3.0],
        expected_entities=["CSE", "AIML", "Data Science"]
    ),

    # =========================================================================
    # CATEGORY C: Workload Policies and Exemptions (19-25)
    # =========================================================================
    TestCase(
        id="Q019",
        category="C",
        category_name="Workload Policies",
        question="Does an approved HOD exemption increase the maximum teaching-hour limit?",
        expected_answer="No. Approved teaching relief reduces the minimum teaching expectation only. It does not increase the maximum limit.",
        expected_negative=True,
        expected_entities=["No", "minimum", "maximum"]
    ),
    TestCase(
        id="Q020",
        category="C",
        category_name="Workload Policies",
        question="What is Dr. Meera Nair's approved weekly workload relief?",
        expected_answer="4 hours per week for HOD responsibilities.",
        expected_numbers=[4.0],
        expected_entities=["HOD", "relief"]
    ),
    TestCase(
        id="Q021",
        category="C",
        category_name="Workload Policies",
        question="What is Aditya Bose's effective maximum workload?",
        expected_answer="20 hours per week due to approved policy exception PEX001.",
        expected_numbers=[20.0],
        expected_entities=["Aditya Bose", "PEX001"]
    ),
    TestCase(
        id="Q022",
        category="C",
        category_name="Workload Policies",
        question="Is Karthik Bhat's policy exception approved?",
        expected_answer="No. PEX002 is Pending.",
        expected_negative=True,
        expected_entities=["No", "Pending", "PEX002"]
    ),
    TestCase(
        id="Q023",
        category="C",
        category_name="Workload Policies",
        question="Should a pending policy exception override the standard workload limit?",
        expected_answer="No. Only approved and currently valid policy exceptions should override the standard limit.",
        expected_negative=True,
        expected_entities=["No", "approved"]
    ),
    TestCase(
        id="Q024",
        category="C",
        category_name="Workload Policies",
        question="What happens when a faculty member exceeds their effective workload limit?",
        expected_answer="A workload policy violation must be reported.",
        expected_entities=["violation"]
    ),
    TestCase(
        id="Q025",
        category="C",
        category_name="Workload Policies",
        question="What is the standard maximum workload for an Assistant Professor?",
        expected_answer="16 teaching hours per week.",
        expected_numbers=[16.0],
        expected_entities=["Assistant Professor"]
    ),

    # =========================================================================
    # CATEGORY D: Leave Management (26-31)
    # =========================================================================
    TestCase(
        id="Q026",
        category="D",
        category_name="Leave Management",
        question="Which faculty member has approved medical leave on 2026-11-12?",
        expected_answer="Ishita Kapoor (FAC010).",
        expected_entities=["Ishita Kapoor", "FAC010"]
    ),
    TestCase(
        id="Q027",
        category="D",
        category_name="Leave Management",
        question="Who replaces Ishita Kapoor during her medical leave?",
        expected_answer="Rohan Shetty (FAC011).",
        expected_entities=["Rohan Shetty", "FAC011"]
    ),
    TestCase(
        id="Q028",
        category="D",
        category_name="Leave Management",
        question="Does Karthik Bhat have approved leave on 2026-11-13?",
        expected_answer="No. His Official Duty leave is Pending and has not been approved.",
        expected_negative=True,
        expected_entities=["No", "Pending"]
    ),
    TestCase(
        id="Q029",
        category="D",
        category_name="Leave Management",
        question="Which faculty member has rejected leave in December 2026?",
        expected_answer="Kavya Sharma (FAC003). Her Earned Leave from December 2 to December 4 was Rejected.",
        expected_entities=["Kavya Sharma", "FAC003", "Rejected"]
    ),
    TestCase(
        id="Q030",
        category="D",
        category_name="Leave Management",
        question="Who is replacing Rahul Das during his approved leave on November 11?",
        expected_answer="Sneha Thomas (FAC005).",
        expected_entities=["Sneha Thomas", "FAC005"]
    ),
    TestCase(
        id="Q031",
        category="D",
        category_name="Leave Management",
        question="Which faculty member has approved leave on November 20?",
        expected_answer="Farah Khan (FAC017). Her replacement is Neha Reddy (FAC015).",
        expected_entities=["Farah Khan", "FAC017", "Neha Reddy", "FAC015"]
    ),

    # =========================================================================
    # CATEGORY E: Assignment Management (32-38)
    # =========================================================================
    TestCase(
        id="Q032",
        category="E",
        category_name="Assignment Management",
        question="How many assignments are assigned to Dr. Meera Nair?",
        expected_answer="3.",
        expected_numbers=[3.0],
        expected_entities=["Meera Nair"]
    ),
    TestCase(
        id="Q033",
        category="E",
        category_name="Assignment Management",
        question="What is Dr. Meera Nair's pending assignment?",
        expected_answer="Internal Assessment Evaluation for CS501, due on 2026-11-12.",
        expected_entities=["Internal Assessment Evaluation", "CS501"]
    ),
    TestCase(
        id="Q034",
        category="E",
        category_name="Assignment Management",
        question="What is the status of her Question Paper Preparation assignment?",
        expected_answer="In Progress. It is for CS502 and is due on 2026-11-13.",
        expected_entities=["In Progress", "CS502"]
    ),
    TestCase(
        id="Q035",
        category="E",
        category_name="Assignment Management",
        question="Which assignments are assigned to Arjun Menon?",
        expected_answer="- Question Paper Preparation.\n- Project Supervision.\n- Exam Invigilation.",
        expected_entities=["Question Paper Preparation", "Project Supervision", "Exam Invigilation"]
    ),
    TestCase(
        id="Q036",
        category="E",
        category_name="Assignment Management",
        question="What is the status of Arjun Menon's Exam Invigilation assignment?",
        expected_answer="Pending. Due date: 2026-11-15.",
        expected_entities=["Pending", "2026-11-15"]
    ),
    TestCase(
        id="Q037",
        category="E",
        category_name="Assignment Management",
        question="How many assignments are present in the dataset?",
        expected_answer="54.",
        expected_numbers=[54.0]
    ),
    TestCase(
        id="Q038",
        category="E",
        category_name="Assignment Management",
        question="How many assignments does each faculty member have?",
        expected_answer="3 assignments per faculty member.",
        expected_numbers=[3.0]
    ),

    # =========================================================================
    # CATEGORY F: Timetable and Teaching-hour Calculation (39-48)
    # =========================================================================
    TestCase(
        id="Q039",
        category="F",
        category_name="Timetable",
        question="How many timetable records are present?",
        expected_answer="281.",
        expected_numbers=[281.0]
    ),
    TestCase(
        id="Q040",
        category="F",
        category_name="Timetable",
        question="How many timetable sessions are Active?",
        expected_answer="277.",
        expected_numbers=[277.0]
    ),
    TestCase(
        id="Q041",
        category="F",
        category_name="Timetable",
        question="Are cancelled sessions included in workload calculations?",
        expected_answer="No. Cancelled sessions must be excluded.",
        expected_negative=True,
        expected_entities=["No", "excluded"]
    ),
    TestCase(
        id="Q042",
        category="F",
        category_name="Timetable",
        question="Do laboratory hours count towards teaching workload?",
        expected_answer="Yes. Laboratory hours count at actual scheduled duration, with a weight of 1.0.",
        expected_numbers=[1.0],
        expected_entities=["Yes", "Laboratory"]
    ),
    TestCase(
        id="Q043",
        category="F",
        category_name="Timetable",
        question="Do tutorial hours count towards teaching workload?",
        expected_answer="Yes. Tutorial hours count at actual scheduled duration, with a weight of 1.0.",
        expected_numbers=[1.0],
        expected_entities=["Yes", "Tutorial"]
    ),
    TestCase(
        id="Q044",
        category="F",
        category_name="Timetable",
        question="Does project supervision count as weekly teaching workload?",
        expected_answer="No. It is tracked separately as an assignment or responsibility.",
        expected_negative=True,
        expected_entities=["No", "assignment"]
    ),
    TestCase(
        id="Q045",
        category="F",
        category_name="Timetable",
        question="Does exam invigilation count towards weekly teaching hours?",
        expected_answer="No. It is tracked separately as examination duty.",
        expected_negative=True,
        expected_entities=["No", "examination duty"]
    ),
    TestCase(
        id="Q046",
        category="F",
        category_name="Timetable",
        question="How are substituted sessions counted?",
        expected_answer="The workload is credited to the substitute faculty member, not the original faculty member.",
        expected_entities=["substitute faculty"]
    ),
    TestCase(
        id="Q047",
        category="F",
        category_name="Timetable",
        question="What is the workload calculation period?",
        expected_answer="Weekly.",
        expected_entities=["Weekly"]
    ),
    TestCase(
        id="Q048",
        category="F",
        category_name="Timetable",
        question="What is the academic year?",
        expected_answer="2026-27.",
        expected_entities=["2026-27"]
    ),

    # =========================================================================
    # CATEGORY G: Subject-related Questions (49-54)
    # =========================================================================
    TestCase(
        id="Q049",
        category="G",
        category_name="Subject Retrieval",
        question="Which subject has ID CS501?",
        expected_answer="Operating Systems.",
        expected_entities=["Operating Systems", "CS501"]
    ),
    TestCase(
        id="Q050",
        category="G",
        category_name="Subject Retrieval",
        question="Which department offers AI501?",
        expected_answer="Artificial Intelligence and Machine Learning (AIML).",
        expected_entities=["Artificial Intelligence and Machine Learning", "AIML"]
    ),
    TestCase(
        id="Q051",
        category="G",
        category_name="Subject Retrieval",
        question="What is the subject name for DS503?",
        expected_answer="Data Visualization.",
        expected_entities=["Data Visualization", "DS503"]
    ),
    TestCase(
        id="Q052",
        category="G",
        category_name="Subject Retrieval",
        question="Which subject is associated with AI504?",
        expected_answer="Computer Vision.",
        expected_entities=["Computer Vision", "AI504"]
    ),
    TestCase(
        id="Q053",
        category="G",
        category_name="Subject Retrieval",
        question="How many subjects are available?",
        expected_answer="12.",
        expected_numbers=[12.0]
    ),
    TestCase(
        id="Q054",
        category="G",
        category_name="Subject Retrieval",
        question="Which semester is CS503 offered in?",
        expected_answer="Semester 7.",
        expected_numbers=[7.0],
        expected_entities=["Semester 7"]
    ),

    # =========================================================================
    # CATEGORY H: Advanced Reasoning Questions (55-62)
    # =========================================================================
    TestCase(
        id="Q055",
        category="H",
        category_name="Advanced Reasoning",
        question="If a faculty member teaches 18 hours and has a maximum limit of 16 hours, how much excess workload do they have?",
        expected_answer="2 hours.",
        expected_numbers=[2.0],
        expected_entities=["2 hours"]
    ),
    TestCase(
        id="Q056",
        category="H",
        category_name="Advanced Reasoning",
        question="If a faculty member has 19 hours and an approved maximum override of 20 hours, is there a violation?",
        expected_answer="No. The faculty member is within the approved limit.",
        expected_negative=True,
        expected_entities=["No", "within"]
    ),
    TestCase(
        id="Q057",
        category="H",
        category_name="Advanced Reasoning",
        question="If a policy exception is Pending, should it be considered when calculating the effective maximum?",
        expected_answer="No. Pending exceptions must not override the standard policy.",
        expected_negative=True,
        expected_entities=["No", "Pending"]
    ),
    TestCase(
        id="Q058",
        category="H",
        category_name="Advanced Reasoning",
        question="Does a faculty member with 12 teaching hours violate the Professor workload policy?",
        expected_answer="No. The Professor maximum is 12 hours. The faculty member is exactly at the maximum.",
        expected_negative=True,
        expected_numbers=[12.0],
        expected_entities=["No", "12"]
    ),
    TestCase(
        id="Q059",
        category="H",
        category_name="Advanced Reasoning",
        question="If a one-hour lecture is cancelled, should it count towards workload?",
        expected_answer="No.",
        expected_negative=True,
        expected_entities=["No"]
    ),
    TestCase(
        id="Q060",
        category="H",
        category_name="Advanced Reasoning",
        question="If a faculty member conducts a two-hour laboratory, how many teaching hours should be counted?",
        expected_answer="2 hours.",
        expected_numbers=[2.0],
        expected_entities=["2 hours"]
    ),
    TestCase(
        id="Q061",
        category="H",
        category_name="Advanced Reasoning",
        question="If a substitute conducts a one-hour class, who receives the workload credit?",
        expected_answer="The substitute faculty member receives one teaching hour. The original faculty member does not receive the credit.",
        expected_entities=["substitute faculty"]
    ),
    TestCase(
        id="Q062",
        category="H",
        category_name="Advanced Reasoning",
        question="Can an HOD's administrative relief be added to the maximum workload limit?",
        expected_answer="No. Approved administrative relief reduces the minimum teaching expectation only.",
        expected_negative=True,
        expected_entities=["No", "minimum"]
    ),

    # =========================================================================
    # CATEGORY I: Hallucination and Missing Information Tests (63-69)
    # =========================================================================
    TestCase(
        id="Q063",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the salary of Dr. Meera Nair?",
        expected_answer="Salary information is not available in the dataset. The LLM must not invent a salary.",
        is_missing_info=True,
        expected_entities=["not available", "not in the dataset", "salary"]
    ),
    TestCase(
        id="Q064",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the home address of FAC001?",
        expected_answer="Home address information is not available in the dataset.",
        is_missing_info=True,
        expected_entities=["not available", "not in the dataset", "address"]
    ),
    TestCase(
        id="Q065",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the age of Arjun Menon?",
        expected_answer="Age information is not available in the dataset.",
        is_missing_info=True,
        expected_entities=["not available", "not in the dataset", "age"]
    ),
    TestCase(
        id="Q066",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the attendance percentage of FAC005?",
        expected_answer="Attendance percentage is not available in the dataset.",
        is_missing_info=True,
        expected_entities=["not available", "not in the dataset", "attendance"]
    ),
    TestCase(
        id="Q067",
        category="I",
        category_name="Hallucination Prevention",
        question="What was the workload of FAC001 in November 2025?",
        expected_answer="The dataset does not contain November-specific records for 2025. It contains historical academic-year and term-level aggregates for 2024-25 and 2025-26. The LLM must not invent a November-specific value.",
        is_missing_info=True,
        expected_entities=["not contain", "historical", "not available"]
    ),
    TestCase(
        id="Q068",
        category="I",
        category_name="Hallucination Prevention",
        question="What is the GPA of FAC007?",
        expected_answer="GPA information is not available in the dataset.",
        is_missing_info=True,
        expected_entities=["not available", "not in the dataset", "GPA"]
    ),
    TestCase(
        id="Q069",
        category="I",
        category_name="Hallucination Prevention",
        question="Who is the Dean of the university?",
        expected_answer="The Dean's identity is not established by the available dataset. DEAN001 appears as an approver identifier, but no corresponding Dean name is provided.",
        is_missing_info=True,
        expected_entities=["not established", "not available", "DEAN001"]
    ),
]
