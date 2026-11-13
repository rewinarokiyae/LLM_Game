"""
CLI Runner for Automated LLM Testing and Audit Framework.
Command:
python -m tests.run_audit

Supports:
  --category <name>     Filter audit to a specific category (e.g. 'Leave Management')
  --rerun-failed        Rerun only the test cases that failed in the last run
  --security            Execute the RBAC & Security Audit alongside the functional audit
  --user <id>           Run test queries as a specific identity (default: admin)
  --timeout <sec>       Configurable execution timeout per question
"""

import sys
import os
import csv
import argparse
from typing import List, Optional
from rich.console import Console
from rich.table import Table

from app.config.settings import settings
from app.llm.factory import LLMFactory
from tests.audit_framework import AuditFramework
from tests.security_audit import SecurityAuditRunner
from tests.test_cases import TEST_CASES


def main():
    parser = argparse.ArgumentParser(description="Faculty Workload LLM Automated Audit Framework")
    parser.add_argument("--category", type=str, default=None, help="Filter test cases by category name or code")
    parser.add_argument("--rerun-failed", action="store_true", help="Rerun only test cases that failed in previous run")
    parser.add_argument("--security", action="store_true", help="Run the separate RBAC and Security Audit")
    parser.add_argument("--user", type=str, default="admin", help="Identity to execute queries as (default: admin)")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout in seconds per query (default: 15)")

    args = parser.parse_args()

    console = Console()

    # 1. Print Startup Banner
    llm_status = LLMFactory.get_status()
    console.print("\n[bold cyan]====================================================[/bold cyan]")
    console.print("[bold white]       FACULTY WORKLOAD LLM - AUDIT FRAMEWORK[/bold white]")
    console.print(f"[dim]Active Provider: {llm_status} | Identity: {args.user}[/dim]")
    console.print("[bold cyan]====================================================[/bold cyan]\n")

    # 2. Check failed rerun
    previous_failed_ids: Optional[List[str]] = None
    if args.rerun_failed:
        failed_csv = "reports/failed_questions.csv"
        if os.path.exists(failed_csv):
            previous_failed_ids = []
            with open(failed_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tid = row.get("Test ID")
                    if tid:
                        previous_failed_ids.append(tid)
            console.print(f"[yellow]Loaded {len(previous_failed_ids)} previously failed questions to rerun.[/yellow]")
        else:
            console.print("[red]No previous failed_questions.csv found. Running all test cases.[/red]")

    # 3. Execute Functional Benchmark Audit
    runner = AuditFramework(output_dir="reports", default_user=args.user)
    summary = runner.run_audit(
        category_filter=args.category,
        only_failed=args.rerun_failed,
        previous_failed_ids=previous_failed_ids,
        timeout_seconds=args.timeout
    )

    # 4. Print Terminal Output Matching Specification
    print("\n====================================================")
    print("       FACULTY WORKLOAD LLM - AUDIT REPORT")
    print("====================================================")
    print(f"Total Questions       : {summary['total_questions']}")
    print(f"Passed                : {summary['passed']}")
    print(f"Partially Correct     : {summary['partially_correct']}")
    print(f"Failed                : {summary['failed']}")
    print(f"Hallucinations        : {summary['hallucinations']}")
    print(f"Execution Errors      : {summary['execution_errors']}")
    print(f"\nOverall Accuracy      : {summary['accuracy_percent']}%")
    print(f"Strict Accuracy       : {summary['strict_accuracy_percent']}%")
    print(f"Average Response Time : {summary['average_response_time_seconds']} seconds")

    print("\n====================================================")
    print("CATEGORY-WISE RESULTS")
    print("====================================================")
    for cname, d in summary["category_performance"].items():
        print(f"{cname:35} {d['accuracy_percent']:.0f}%")

    print("\n====================================================")
    print("FAILED QUESTIONS")
    print("====================================================")
    failed_items = [r for r in summary["results"] if r["status"] != "PASS"]
    if not failed_items:
        print("None. All evaluated questions passed successfully!")
    else:
        for r in failed_items:
            print(f"\n{r['test_id']} - {r['question']}")
            print(f"Expected: {r['expected_answer'].replace(chr(10), ' ')}")
            print(f"Actual  : {r['actual_answer'][:150].replace(chr(10), ' ')}...")
            print(f"Reason  : {r['reason']}")
            print(f"Category: {r['failure_category']}")
            print(f"Fix     : {r['suggested_correction']}")

    print("\n====================================================")
    print("AUDIT COMPLETED")
    print("====================================================\n")

    # 5. Execute Security Audit if requested
    if args.security:
        console.print("[bold yellow]Executing Role-Based Access Control (RBAC) Security Audit...[/bold yellow]")
        sec_runner = SecurityAuditRunner(output_dir="reports")
        sec_summary = sec_runner.run_security_audit()

        console.print("\n[bold cyan]====================================================[/bold cyan]")
        console.print("[bold white]       RBAC & ACCESS CONTROL SECURITY AUDIT[/bold white]")
        console.print("[bold cyan]====================================================[/bold cyan]")
        console.print(f"Total Scenarios : {sec_summary['total_security_scenarios']}")
        console.print(f"Passed          : {sec_summary['passed']}")
        console.print(f"Failed          : {sec_summary['failed']}")
        console.print(f"Pass Rate       : {sec_summary['pass_rate_percent']}%\n")

        sec_table = Table(title="RBAC Security Evaluation", header_style="bold magenta")
        sec_table.add_column("ID", style="cyan", width=8)
        sec_table.add_column("Scenario", width=32)
        sec_table.add_column("Status", width=10)
        sec_table.add_column("Audit Result Details", width=45)

        for s in sec_summary["scenarios"]:
            color = "green" if s["passed"] else "red"
            sec_table.add_row(s["scenario_id"], s["title"], f"[{color}]{s['status']}[/{color}]", s["details"])

        console.print(sec_table)

    # 6. Report locations
    console.print(f"[bold green]✓ Audit reports saved to:[/bold green]")
    console.print(f"  • HTML Report : [cyan]reports/llm_audit_report.html[/cyan]")
    console.print(f"  • JSON Data   : [cyan]reports/llm_audit_report.json[/cyan]")
    console.print(f"  • CSV Results : [cyan]reports/llm_audit_report.csv[/cyan]")
    console.print(f"  • Failed CSV  : [cyan]reports/failed_questions.csv[/cyan]")
    console.print(f"  • Summary TXT : [cyan]reports/audit_summary.txt[/cyan]\n")


if __name__ == "__main__":
    main()

