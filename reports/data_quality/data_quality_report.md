# DATA QUALITY AND AUDIT REPORT
**Generated:** 2026-11-11T13:07:55.298852
**Source File:** `./data/faculty_workload_dummy_dataset.xlsx`
**Status:** HEALTHY_WITH_REPORTED_ANOMALIES

## 1. Executive Summary
- **Total Sheets Inspected:** 21
- **Total Data Records:** 648
- **Primary Key Integrity:** 100% Unique
- **Workload Calculation Validation:** PASSED (18/18 faculty hours match Workload_Summary exactly)
- **Anomalies / Inconsistencies Reported:** 3

## 2. Sheet Inventory
| Sheet Name | Row Count | Column Count | Primary Key | PK Unique? |
|---|---|---|---|---|
| Departments | 3 | 5 | department_id | Yes |
| Faculty | 18 | 11 | faculty_id | Yes |
| Users_Roles | 19 | 7 | user_id | Yes |
| Sections | 12 | 7 | section_id | Yes |
| Subjects | 12 | 11 | subject_id | Yes |
| Workload_Policies | 4 | 11 | policy_id | Yes |
| Workload_Rules | 7 | 6 | rule_id | Yes |
| Faculty_Subject_Allocations | 36 | 10 | allocation_id | Yes |
| Timetable | 281 | 19 | timetable_id | Yes |
| Assignments | 54 | 12 | assignment_id | Yes |
| Leave_Records | 6 | 9 | leave_id | Yes |
| Faculty_Availability | 18 | 8 | availability_id | Yes |
| Workload_Exemptions | 5 | 10 | exemption_id | Yes |
| Policy_Exceptions | 3 | 10 | exception_id | Yes |
| Academic_Calendar | 8 | 7 | calendar_event_id | Yes |
| Historical_Workload | 72 | 8 | history_id | Yes |
| Workload_Summary | 18 | 12 | N/A | No |
| Rooms | 24 | 5 | room_id | Yes |
| Test_Queries | 15 | 6 | test_id | Yes |
| README | 20 | 2 | N/A | No |
| Data_Dictionary | 13 | 3 | N/A | No |

## 3. Inconsistencies and Anomalies Detected (Reported, Never Silently Altered)
### [INC-001] Faculty_Availability - Severity: HIGH
- **Description:** Column header shift detected: 'faculty_id' contains period_start date ('2026-11-09'), 'period_start' contains period_end ('2026-11-13'), 'period_end' contains availability_status ('Available'), 'availability_status' contains available_from ('08:30'), 'available_from' contains available_to ('18:00'), 'available_to' contains notes ('Standard working week'). The faculty_id is embedded in 'availability_id' (e.g. 'AV-FAC001' -> 'FAC001').
- **Explicit Handling Strategy:** In data ingestion cleaner, parse faculty_id from availability_id ('AV-FAC001' -> 'FAC001') and re-align shifted columns without modifying source workbook.

### [INC-002] Timetable - Severity: MEDIUM
- **Description:** Room identifier mismatch: 187 Timetable rows reference room IDs not directly present in Rooms sheet. Missing 'A' prefix for AIML rooms (e.g. 'IML-202' vs 'AIML-202') and leading hyphen prefix for DS rooms (e.g. '-DS-203' vs 'DS-203').
- **Explicit Handling Strategy:** Record the original room string in timetable record. Provide an explicit normalized room resolver: map 'IML-' -> 'AIML-' and strip leading '-' from '-DS-' -> 'DS-'. Preserve raw source string and log the normalization.

### [INC-003] Users_Roles - Severity: INFO
- **Description:** Admin user USR019 ('admin') has null faculty_id. This is valid by design as administrators operate at the institution level without personal faculty teaching records.
- **Explicit Handling Strategy:** Allow nullable faculty_id in Users_Roles schema.

## 4. Foreign Key Referential Integrity
| Foreign Key Relationship | Valid? | Invalid Count | Sample Invalid |
|---|---|---|---|
| Faculty.department_id -> Departments.department_id | PASS | 0 | None |
| Users_Roles.faculty_id -> Faculty.faculty_id (nullable for admin) | PASS | 0 | None |
| Sections.department_id -> Departments.department_id | PASS | 0 | None |
| Subjects.department_id -> Departments.department_id | PASS | 0 | None |
| Faculty_Subject_Allocations.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Faculty_Subject_Allocations.subject_id -> Subjects.subject_id | PASS | 0 | None |
| Faculty_Subject_Allocations.section_id -> Sections.section_id | PASS | 0 | None |
| Timetable.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Timetable.subject_id -> Subjects.subject_id | PASS | 0 | None |
| Timetable.section_id -> Sections.section_id | PASS | 0 | None |
| Timetable.room -> Rooms.room_id | FLAGGED | 187 | IML-LAB-1, IML-202, IML-LAB-2, IML-203, IML-LAB-3 |
| Assignments.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Assignments.subject_id -> Subjects.subject_id | PASS | 0 | None |
| Leave_Records.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Leave_Records.replacement_faculty_id -> Faculty.faculty_id (nullable) | PASS | 0 | None |
| Workload_Exemptions.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Policy_Exceptions.faculty_id -> Faculty.faculty_id | PASS | 0 | None |
| Policy_Exceptions.policy_id -> Workload_Policies.policy_id | PASS | 0 | None |
| Historical_Workload.faculty_id -> Faculty.faculty_id | PASS | 0 | None |

## 5. Timetable Conflict Analysis
- **Faculty Double-Booking Conflicts:** 0 (No faculty member double-booked)
- **Room Allocation Overlaps:** 11 detected
- **Section Scheduling Overlaps:** 70 detected

## 6. Independent Workload Arithmetic Verification
- **Status:** PASSED
- **Faculty Recomputed:** 18
- **Matches:** 18 / 18
- **Mismatches:** 0
