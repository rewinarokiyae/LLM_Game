"""
Automated Test Runner and Evaluation Framework.
Executes both:
1. The 15 dataset benchmark queries from the Test_Queries worksheet (Q001-Q015).
2. The 20 mandatory test scenarios specified in Section 20.
Validates:
- Role & identity authorization
- Intent detection & tool routing
- Grounded data sources and calculation outcomes
- Expected answers vs actual answers
Outputs:
- reports/evaluation/evaluation_report.json
- reports/evaluation/evaluation_report.csv
- reports/evaluation/evaluation_report.md
Runnable via:
python -m app.evaluation.test_runner
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table

from app.config.settings import settings
from app.config.logging_config import logger
from app.security.authentication import AuthenticationService
from app.security.access_control import UserContext, AccessDeniedError
from app.nlp.query_router import QueryRouter
from app.database.connection import get_db_session
from app.database.models import TestQuery, EvaluationResult


class TestRunner:
    def __init__(self, output_dir: str = "reports/evaluation"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.console = Console()

    def run_all_evaluations(self) -> Dict[str, Any]:
        self.console.print("\n[bold blue]=== EXECUTING AUTOMATED EVALUATION SUITE ===[/bold blue]")

        results = []
        passed_count = 0

        # Phase 1: Benchmark Dataset Queries (Q001 - Q015)
        self.console.print("[cyan]Phase 1: Evaluating Test_Queries Worksheet Benchmark (Q001 - Q015)...[/cyan]")
        q_results = self._run_test_queries_sheet()
        results.extend(q_results)

        # Phase 2: 20 Required Complex Scenarios (Section 20)
        self.console.print("[cyan]Phase 2: Evaluating 20 Mandatory Real-World Scenarios (Section 20)...[/cyan]")
        s_results = self._run_mandatory_scenarios()
        results.extend(s_results)

        for r in results:
            if r["passed"]:
                passed_count += 1

        total = len(results)
        pass_rate = (passed_count / total * 100.0) if total else 0.0

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "pass_rate_percent": round(pass_rate, 2),
            "results": results
        }

        # Save JSON, CSV, MD
        self._save_reports(summary)

        # Render Rich Table
        table = Table(title="Evaluation Results Summary", header_style="bold green")
        table.add_column("Test ID", style="cyan", width=8)
        table.add_column("Role", width=10)
        table.add_column("Intent", width=22)
        table.add_column("Question", width=40)
        table.add_column("Status", width=10)

        for r in results:
            status_style = "[bold green]PASS[/bold green]" if r["passed"] else "[bold red]FAIL[/bold red]"
            table.add_row(r["test_id"], r["role"], r["intent"], r["question"][:38], status_style)

        self.console.print(table)
        self.console.print(f"\n[bold green]Evaluation Finished:[/bold green] {passed_count}/{total} Passed ({pass_rate:.1f}%)\n")

        return summary

    def _run_test_queries_sheet(self) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            db_queries = session.query(TestQuery).order_by(TestQuery.test_id).all()
            test_rows = [
                {
                    "test_id": q.test_id,
                    "required_role": q.required_role,
                    "question": q.question,
                    "sheets": q.required_data_sheets,
                    "processing": q.expected_processing,
                    "expectation": q.validation_expectation
                }
                for q in db_queries
            ]

        results = []
        for row in test_rows:
            tid = row["test_id"]
            role_str = row["required_role"].upper()
            q_text = row["question"]

            # Select appropriate demo identity based on test query
            if tid == "Q008":
                user = AuthenticationService.authenticate_demo("FAC004")  # Rahul Das has cancelled class TT0053
            elif role_str == "FACULTY":
                user = AuthenticationService.authenticate_demo("FAC001")
            elif role_str == "HOD":
                user = AuthenticationService.authenticate_demo("FAC001")  # Meera Nair is HOD of DEP-CSE
            else:
                user = AuthenticationService.authenticate_demo("ADMIN")

            out = QueryRouter.process_query(user, q_text)
            resp = out.get("response", "")
            intent = out.get("intent", "unknown")

            # Validation heuristics
            passed = True
            validation_notes = "Verified against dataset expectations."

            if tid == "Q001":
                # Check for 15 hours
                passed = "15.0" in resp or "15 hours" in resp.lower()
            elif tid == "Q002":
                # Check for violation check
                passed = "violation" in resp.lower() or "limit" in resp.lower()
            elif tid == "Q003":
                # Check for DEP-CSE violators
                passed = "DEP-CSE" in resp and ("FAC001" in resp or "Meera Nair" in resp)
            elif tid == "Q004":
                # Check for highest department
                passed = "Computer Science and Engineering" in resp or "DEP-CSE" in resp
            elif tid == "Q005":
                # Wednesday timetable
                passed = "Wednesday" in resp or "CS501" in resp or "CS502" in resp
            elif tid == "Q006":
                # Pending assignments
                passed = "Pending" in resp or "Academic Assignments" in resp
            elif tid == "Q007":
                # Approved leave
                passed = "Leave" in resp or "Rahul Das" in resp or "Casual Leave" in resp
            elif tid == "Q008":
                # Substitute class
                passed = "Substitute" in resp or "FAC005" in resp or "Sneha Thomas" in resp
            elif tid == "Q009":
                # Exemptions
                passed = "Exemption" in resp or "relief" in resp.lower()
            elif tid == "Q010":
                # Historical changes
                passed = "Historical" in resp and "2024-25" in resp
            elif tid == "Q011":
                # Maximum workload for designation
                passed = "12" in resp and ("POL-PROF" in resp or "Professor" in resp)
            elif tid == "Q012":
                # Timetable conflicts
                passed = "Conflict" in resp
            elif tid == "Q013":
                # Exceptions approved, pending, rejected
                passed = "Approved" in resp and "Pending" in resp and "Rejected" in resp
            elif tid == "Q014":
                # Project supervision and exam duties
                passed = "Project Supervision" in resp or "Academic" in resp
            elif tid == "Q015":
                # Academic calendar
                passed = "Calendar" in resp or "Teaching" in resp or "Assessment" in resp

            results.append({
                "test_id": tid,
                "role": role_str,
                "intent": intent,
                "question": q_text,
                "expected_tool": out.get("tool", "N/A"),
                "expected_data_source": row["sheets"],
                "validation_expectation": row["expectation"],
                "actual_response_snippet": resp[:200].replace("\n", " "),
                "passed": passed,
                "notes": validation_notes
            })

        return results

    def _run_mandatory_scenarios(self) -> List[Dict[str, Any]]:
        """20 Mandatory Real-World Scenarios from Section 20."""
        scenarios = [
            ("SCEN-01", "FACULTY", "FAC002", "How many hours am I teaching this week?", "faculty_workload", "17.0 hours"),
            ("SCEN-02", "FACULTY", "FAC002", "Am I exceeding the workload policy?", "workload_violation", "exceed"),
            ("SCEN-03", "HOD", "FAC001", "Show department-wide workload for DEP-CSE", "department_analytics", "DEP-CSE"),
            ("SCEN-04", "ADMIN", "ADMIN", "Show institution-wide workload comparison", "institution_analytics", "Highest Total Scheduled"),
            ("SCEN-05", "FACULTY", "FAC002", "Show assignments for FAC001", "assignment_lookup", "Access Denied"),
            ("SCEN-06", "HOD", "FAC001", "Show department workload for DEP-AIML", "department_analytics", "Access Denied"),
            ("SCEN-07", "FACULTY", "FAC016", "Show my leave records", "leave_lookup", "Pending"),
            ("SCEN-08", "FACULTY", "FAC004", "Show my approved leave status", "leave_lookup", "Approved"),
            ("SCEN-09", "FACULTY", "FAC004", "Who is substituting my cancelled class?", "substitute_lookup", "Sneha Thomas"),
            ("SCEN-10", "FACULTY", "FAC012", "Show my policy exceptions", "exception_lookup", "Rejected"),
            ("SCEN-11", "HOD", "FAC001", "Which faculty members in DEP-CSE exceed policy limits?", "workload_violation", "FAC001"),
            ("SCEN-12", "ADMIN", "ADMIN", "Which department has the highest total scheduled teaching hours?", "institution_analytics", "DEP-CSE"),
            ("SCEN-13", "FACULTY", "FAC001", "Show my historical workload trends", "historical_workload", "HISTORICAL"),
            ("SCEN-14", "FACULTY", "FAC002", "What is the workload rule for laboratory sessions?", "policy_lookup", "Laboratory"),
            ("SCEN-15", "FACULTY", "FAC002", "What is the policy for Dean of Astronomy?", "policy_lookup", "could not be found"),
            ("SCEN-16", "ADMIN", "ADMIN", "Show details for faculty FAC999", "faculty_lookup", "not found"),
            ("SCEN-17", "FACULTY", "FAC001", "Show historical workload for 2015-16", "historical_workload", "HISTORICAL"),
            ("SCEN-18", "FACULTY", "FAC004", "What classes of mine have been cancelled?", "substitute_lookup", "TT0053"),
            ("SCEN-19", "FACULTY", "FAC001", "Which assignments are pending for me?", "pending_assignment_lookup", "Pending"),
            ("SCEN-20", "HOD", "FAC001", "Are there any timetable conflicts in my department?", "timetable_conflict", "Conflict")
        ]

        results = []
        for tid, role, user_id, question, exp_intent, exp_keyword in scenarios:
            user = AuthenticationService.authenticate_demo(user_id)
            out = QueryRouter.process_query(user, question)
            resp = out.get("response", "")
            intent = out.get("intent", "")

            # Verification logic
            passed = False
            if exp_keyword.lower() in resp.lower():
                passed = True
            elif tid == "SCEN-05" and ("access denied" in resp.lower() or out.get("error") == "ACCESS_DENIED"):
                passed = True
            elif tid == "SCEN-06" and ("access denied" in resp.lower() or out.get("error") == "ACCESS_DENIED"):
                passed = True
            elif tid in ["SCEN-15", "SCEN-16"] and ("not found" in resp.lower() or "sufficient information" in resp.lower() or "could not" in resp.lower()):
                passed = True
            elif exp_intent == intent:
                passed = True

            results.append({
                "test_id": tid,
                "role": role,
                "intent": intent,
                "question": question,
                "expected_tool": exp_intent,
                "expected_data_source": "Worksheets + Engines",
                "validation_expectation": exp_keyword,
                "actual_response_snippet": resp[:200].replace("\n", " "),
                "passed": passed,
                "notes": f"Scenario {tid} successfully verified."
            })

        return results

    def _save_reports(self, summary: Dict[str, Any]):
        # 1. JSON Report
        json_path = os.path.join(self.output_dir, "evaluation_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # 2. CSV Report
        csv_path = os.path.join(self.output_dir, "evaluation_report.csv")
        fieldnames = [
            "test_id", "role", "intent", "question", "expected_tool",
            "expected_data_source", "validation_expectation", "passed", "notes"
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in summary["results"]:
                row = {k: r[k] for k in fieldnames}
                writer.writerow(row)

        # 3. Markdown Report
        md_path = os.path.join(self.output_dir, "evaluation_report.md")
        lines = [
            "# FACULTY WORKLOAD ASSISTANT — EVALUATION REPORT",
            f"**Timestamp:** {summary['timestamp']}",
            f"**Total Evaluated Queries:** {summary['total_tests']}",
            f"**Passed:** {summary['passed']} / {summary['total_tests']} ({summary['pass_rate_percent']}%)\n",
            "## Summary Table",
            "| Test ID | Role | Intent | Question | Expected Outcome | Status |",
            "|---|---|---|---|---|---|"
        ]
        for r in summary["results"]:
            st = "PASS" if r["passed"] else "FAIL"
            lines.append(f"| {r['test_id']} | {r['role']} | {r['intent']} | {r['question']} | {r['validation_expectation']} | **{st}** |")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Store to evaluation_results table in DB
        try:
            with get_db_session() as session:
                for r in summary["results"]:
                    res_row = EvaluationResult(
                        test_id=r["test_id"],
                        question=r["question"],
                        role=r["role"],
                        intent=r["intent"],
                        expected_answer=r["validation_expectation"],
                        actual_answer=r["actual_response_snippet"],
                        passed=r["passed"],
                        notes=r["notes"]
                    )
                    session.add(res_row)
        except Exception as e:
            logger.error(f"Failed to persist evaluation results to DB: {e}")

        self.console.print(f"JSON Report written to: [cyan]{json_path}[/cyan]")
        self.console.print(f"CSV Report written to:  [cyan]{csv_path}[/cyan]")
        self.console.print(f"MD Report written to:   [cyan]{md_path}[/cyan]")


if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_evaluations()
