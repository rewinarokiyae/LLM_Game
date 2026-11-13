# FACULTY WORKLOAD ASSISTANT — EVALUATION REPORT
**Timestamp:** 2026-11-12T04:18:43.354566
**Total Evaluated Queries:** 35
**Passed:** 35 / 35 (100.0%)

## Summary Table
| Test ID | Role | Intent | Question | Expected Outcome | Status |
|---|---|---|---|---|---|
| Q001 | FACULTY | faculty_workload | How many teaching hours does FAC001 have in the week starting 2026-11-09? | Compare with Workload_Summary. | **PASS** |
| Q002 | FACULTY | workload_violation | Am I exceeding my weekly teaching-hour limit? | Compare actual hours with effective policy limit. | **PASS** |
| Q003 | HOD | workload_violation | Which faculty members in DEP-CSE exceed their policy limit? | Return only department records. | **PASS** |
| Q004 | ADMIN | institution_analytics | Which department has the highest total scheduled teaching hours? | Aggregate Active and Substituted teaching hours. | **PASS** |
| Q005 | FACULTY | timetable_lookup | What classes do I have on Wednesday? | Show time, subject, section, room. | **PASS** |
| Q006 | FACULTY | pending_assignment_lookup | Which assignments are pending for me? | Do not show other faculty assignments. | **PASS** |
| Q007 | HOD | leave_lookup | Who is on approved leave in my department this week? | Pending/rejected leave is not approved absence. | **PASS** |
| Q008 | FACULTY | substitute_lookup | Who is substituting my cancelled class? | Return substitute faculty and class details. | **PASS** |
| Q009 | HOD | exemption_lookup | Which workload exemptions are approved in my department? | Do not treat Pending exemption as approved. | **PASS** |
| Q010 | ADMIN | historical_workload | Show workload changes for FAC001 over the last four semesters. | Historical values are synthetic aggregates. | **PASS** |
| Q011 | FACULTY | policy_lookup | What is the maximum teaching workload for my designation? | Cite policy ID, validity and source page. | **PASS** |
| Q012 | HOD | timetable_conflict | Are there any timetable conflicts in my department? | Do not claim conflict unless intervals overlap. | **PASS** |
| Q013 | ADMIN | exception_lookup | Which policy exceptions are approved, pending, and rejected? | Only approved and valid exceptions can override max hours. | **PASS** |
| Q014 | FACULTY | assignment_lookup | How many project supervision and exam duties are assigned to me? | Separate academic duties from teaching hours. | **PASS** |
| Q015 | ADMIN | academic_calendar | How many working and examination days are in the academic calendar? | Distinguish teaching, assessment, examination and vacation. | **PASS** |
| SCEN-01 | FACULTY | faculty_workload | How many hours am I teaching this week? | 17.0 hours | **PASS** |
| SCEN-02 | FACULTY | workload_violation | Am I exceeding the workload policy? | exceed | **PASS** |
| SCEN-03 | HOD | department_analytics | Show department-wide workload for DEP-CSE | DEP-CSE | **PASS** |
| SCEN-04 | ADMIN | institution_analytics | Show institution-wide workload comparison | Highest Total Scheduled | **PASS** |
| SCEN-05 | FACULTY | assignment_lookup | Show assignments for FAC001 | Access Denied | **PASS** |
| SCEN-06 | HOD | department_analytics | Show department workload for DEP-AIML | Access Denied | **PASS** |
| SCEN-07 | FACULTY | leave_lookup | Show my leave records | Pending | **PASS** |
| SCEN-08 | FACULTY | leave_lookup | Show my approved leave status | Approved | **PASS** |
| SCEN-09 | FACULTY | substitute_lookup | Who is substituting my cancelled class? | Sneha Thomas | **PASS** |
| SCEN-10 | FACULTY | exception_lookup | Show my policy exceptions | Rejected | **PASS** |
| SCEN-11 | HOD | workload_violation | Which faculty members in DEP-CSE exceed policy limits? | FAC001 | **PASS** |
| SCEN-12 | ADMIN | institution_analytics | Which department has the highest total scheduled teaching hours? | DEP-CSE | **PASS** |
| SCEN-13 | FACULTY | historical_workload | Show my historical workload trends | HISTORICAL | **PASS** |
| SCEN-14 | FACULTY | policy_lookup | What is the workload rule for laboratory sessions? | Laboratory | **PASS** |
| SCEN-15 | FACULTY | policy_lookup | What is the policy for Dean of Astronomy? | could not be found | **PASS** |
| SCEN-16 | ADMIN | faculty_lookup | Show details for faculty FAC999 | not found | **PASS** |
| SCEN-17 | FACULTY | historical_workload | Show historical workload for 2015-16 | HISTORICAL | **PASS** |
| SCEN-18 | FACULTY | substitute_lookup | What classes of mine have been cancelled? | TT0053 | **PASS** |
| SCEN-19 | FACULTY | pending_assignment_lookup | Which assignments are pending for me? | Pending | **PASS** |
| SCEN-20 | HOD | timetable_conflict | Are there any timetable conflicts in my department? | Conflict | **PASS** |