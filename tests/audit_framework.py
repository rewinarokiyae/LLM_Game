"""
Automated LLM Testing and Audit Framework.
Executes the predefined 69-question benchmark against the existing inference pipeline,
evaluates generated answers against ground-truth keys, and generates comprehensive audit reports.
"""

import os
import re
import csv
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.config.logging_config import logger
from app.config.settings import settings
from app.security.authentication import AuthenticationService
from app.nlp.query_router import QueryRouter
from app.llm.factory import LLMFactory
from tests.test_cases import TEST_CASES, TestCase
from tests.evaluator import ResponseEvaluator, EvaluationStatus


class AuditFramework:
    def __init__(self, output_dir: str = "reports", default_user: str = "admin"):
        self.output_dir = output_dir
        self.history_dir = os.path.join(output_dir, "history")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        self.default_user_id = default_user
        self.user_context = AuthenticationService.authenticate_demo(self.default_user_id)

    def run_audit(
        self,
        category_filter: Optional[str] = None,
        only_failed: bool = False,
        previous_failed_ids: Optional[List[str]] = None,
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes benchmark test cases and compiles the audit report.
        """
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        logger.info(f"Starting LLM Audit Run: {run_id}")

        # 1. Filter test cases
        cases_to_run = TEST_CASES
        if category_filter:
            c_filter_lower = category_filter.lower()
            cases_to_run = [
                tc for tc in cases_to_run
                if c_filter_lower in tc.category.lower() or c_filter_lower in tc.category_name.lower()
            ]

        if only_failed and previous_failed_ids:
            cases_to_run = [tc for tc in cases_to_run if tc.id in previous_failed_ids]

        total_cases = len(cases_to_run)
        logger.info(f"Executing {total_cases} test cases...")

        results: List[Dict[str, Any]] = []
        start_total_time = time.time()

        # 2. Sequential execution
        for idx, tc in enumerate(cases_to_run, 1):
            t_start = time.time()
            actual_resp = ""
            err_msg = None
            metadata = {}

            # Reset conversation context between independent test questions to prevent context bleeding
            QueryRouter.reset_context(self.user_context.user_id)

            try:
                # Send ONLY the question to the existing pipeline
                query_res = QueryRouter.process_query(self.user_context, tc.question)
                actual_resp = query_res.get("response", "")
                metadata["intent"] = query_res.get("intent")
                metadata["tool"] = query_res.get("tool")
                if query_res.get("error"):
                    err_msg = query_res.get("error")
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Error executing test case {tc.id}: {e}", exc_info=True)

            elapsed_case = round(time.time() - t_start, 3)

            # 3. Evaluate response against ground truth
            eval_res = ResponseEvaluator.evaluate(tc, actual_resp, err_msg)

            item = {
                "test_id": tc.id,
                "category_code": tc.category,
                "category_name": tc.category_name,
                "question": tc.question,
                "expected_answer": tc.expected_answer,
                "actual_answer": actual_resp,
                "status": eval_res["status"],
                "score": eval_res["score"],
                "reason": eval_res["reason"],
                "what_went_wrong": eval_res["what_went_wrong"],
                "failure_category": eval_res["failure_category"],
                "suggested_correction": eval_res["suggested_correction"],
                "execution_time": elapsed_case,
                "metadata": metadata
            }
            results.append(item)

        total_elapsed = round(time.time() - start_total_time, 3)

        # 4. Aggregations & Statistics
        pass_count = sum(1 for r in results if r["status"] == EvaluationStatus.PASS)
        partial_count = sum(1 for r in results if r["status"] == EvaluationStatus.PARTIAL)
        fail_count = sum(1 for r in results if r["status"] == EvaluationStatus.FAIL)
        hallucination_count = sum(1 for r in results if r["status"] == EvaluationStatus.HALLUCINATION)
        error_count = sum(1 for r in results if r["status"] == EvaluationStatus.ERROR)

        accuracy = round((pass_count / total_cases * 100.0), 2) if total_cases > 0 else 0.0
        strict_accuracy = accuracy  # Strict accuracy means PARTIAL does not count as PASS
        avg_resp_time = round((total_elapsed / total_cases), 3) if total_cases > 0 else 0.0

        # Category-wise metrics
        category_metrics = self._calculate_category_metrics(results)
        weakest_category = min(category_metrics.items(), key=lambda x: x[1]["accuracy_percent"])[0] if category_metrics else "None"

        # Failure category breakdown
        failure_breakdown = {}
        for r in results:
            if r["status"] != EvaluationStatus.PASS and r["failure_category"] != "None":
                cat = r["failure_category"]
                failure_breakdown[cat] = failure_breakdown.get(cat, 0) + 1

        summary = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "llm_provider": LLMFactory.get_status(),
            "evaluated_user": self.default_user_id,
            "total_questions": total_cases,
            "passed": pass_count,
            "partially_correct": partial_count,
            "failed": fail_count,
            "hallucinations": hallucination_count,
            "execution_errors": error_count,
            "accuracy_percent": accuracy,
            "strict_accuracy_percent": strict_accuracy,
            "total_execution_time_seconds": total_elapsed,
            "average_response_time_seconds": avg_resp_time,
            "weakest_category": weakest_category,
            "category_performance": category_metrics,
            "failure_diagnostics": failure_breakdown,
            "results": results
        }

        # 5. Generate and preserve all report files
        self._generate_reports(summary)

        return summary

    def _calculate_category_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate performance per test category."""
        metrics: Dict[str, Any] = {}
        for r in results:
            cname = r["category_name"]
            if cname not in metrics:
                metrics[cname] = {
                    "total": 0,
                    "passed": 0,
                    "partial": 0,
                    "failed": 0,
                    "hallucinations": 0,
                    "errors": 0,
                    "accuracy_percent": 0.0
                }
            metrics[cname]["total"] += 1
            st = r["status"]
            if st == EvaluationStatus.PASS:
                metrics[cname]["passed"] += 1
            elif st == EvaluationStatus.PARTIAL:
                metrics[cname]["partial"] += 1
            elif st == EvaluationStatus.FAIL:
                metrics[cname]["failed"] += 1
            elif st == EvaluationStatus.HALLUCINATION:
                metrics[cname]["hallucinations"] += 1
            elif st == EvaluationStatus.ERROR:
                metrics[cname]["errors"] += 1

        for cname, data in metrics.items():
            tot = data["total"]
            data["accuracy_percent"] = round((data["passed"] / tot * 100.0), 2) if tot > 0 else 0.0

        return metrics

    def _generate_reports(self, summary: Dict[str, Any]):
        """Generate all required output files and archive historical run."""
        run_id = summary["run_id"]

        # 1. JSON Report
        json_path = os.path.join(self.output_dir, "llm_audit_report.json")
        hist_json_path = os.path.join(self.history_dir, f"llm_audit_report_{run_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        with open(hist_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # 2. Question-wise CSV Report
        csv_path = os.path.join(self.output_dir, "llm_audit_report.csv")
        fieldnames = [
            "Test ID", "Category", "Question", "Expected Answer", "Actual Answer",
            "Status", "Score", "Reason", "What Went Wrong", "Failure Category",
            "Suggested Correction", "Execution Time (s)"
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for r in summary["results"]:
                writer.writerow([
                    r["test_id"],
                    r["category_name"],
                    r["question"],
                    r["expected_answer"].replace("\n", " "),
                    r["actual_answer"].replace("\n", " "),
                    r["status"],
                    r["score"],
                    r["reason"],
                    r["what_went_wrong"],
                    r["failure_category"],
                    r["suggested_correction"],
                    r["execution_time"]
                ])

        # 3. Failed Questions CSV Report
        failed_csv_path = os.path.join(self.output_dir, "failed_questions.csv")
        failed_rows = [r for r in summary["results"] if r["status"] != EvaluationStatus.PASS]
        with open(failed_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Test ID", "Category", "Question", "Expected Answer", "Actual Answer",
                "Status", "What Went Wrong", "Failure Category", "Suggested Correction"
            ])
            for r in failed_rows:
                writer.writerow([
                    r["test_id"],
                    r["category_name"],
                    r["question"],
                    r["expected_answer"].replace("\n", " "),
                    r["actual_answer"].replace("\n", " "),
                    r["status"],
                    r["what_went_wrong"],
                    r["failure_category"],
                    r["suggested_correction"]
                ])

        # 4. Text Summary Report
        summary_txt_path = os.path.join(self.output_dir, "audit_summary.txt")
        self._write_summary_text(summary, summary_txt_path)

        # 5. HTML Report
        html_path = os.path.join(self.output_dir, "llm_audit_report.html")
        hist_html_path = os.path.join(self.history_dir, f"llm_audit_report_{run_id}.html")
        html_content = self._render_html_report(summary)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(hist_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _write_summary_text(self, summary: Dict[str, Any], path: str):
        lines = [
            "=" * 60,
            "       FACULTY WORKLOAD LLM - AUDIT REPORT",
            "=" * 60,
            f"Run ID                : {summary['run_id']}",
            f"Timestamp             : {summary['timestamp']}",
            f"LLM Provider          : {summary['llm_provider']}",
            f"Total Questions       : {summary['total_questions']}",
            f"Passed                : {summary['passed']}",
            f"Partially Correct     : {summary['partially_correct']}",
            f"Failed                : {summary['failed']}",
            f"Hallucinations        : {summary['hallucinations']}",
            f"Execution Errors      : {summary['execution_errors']}",
            "",
            f"Overall Accuracy      : {summary['accuracy_percent']}%",
            f"Strict Accuracy       : {summary['strict_accuracy_percent']}%",
            f"Average Response Time : {summary['average_response_time_seconds']} seconds",
            f"Weakest Category      : {summary['weakest_category']}",
            "",
            "=" * 60,
            "CATEGORY-WISE RESULTS",
            "=" * 60
        ]
        for cname, d in summary["category_performance"].items():
            lines.append(f"{cname:35} : {d['accuracy_percent']:5.1f}% ({d['passed']}/{d['total']})")

        lines.extend([
            "",
            "=" * 60,
            "FAILED / UNRESOLVED QUESTIONS",
            "=" * 60
        ])
        failed_items = [r for r in summary["results"] if r["status"] != EvaluationStatus.PASS]
        if not failed_items:
            lines.append("All questions passed successfully! Zero failures recorded.")
        else:
            for r in failed_items:
                lines.append(f"{r['test_id']} - {r['question']}")
                lines.append(f"  Status   : {r['status']}")
                lines.append(f"  Category : {r['failure_category']}")
                lines.append(f"  Expected : {r['expected_answer'][:120]}...")
                lines.append(f"  Actual   : {r['actual_answer'][:120]}...")
                lines.append(f"  Issue    : {r['what_went_wrong']}")
                lines.append(f"  Fix      : {r['suggested_correction']}")
                lines.append("-" * 50)

        lines.extend([
            "",
            "=" * 60,
            "AUDIT COMPLETED",
            "=" * 60
        ])
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _render_html_report(self, summary: Dict[str, Any]) -> str:
        """Render a standalone, styled HTML report."""
        run_id = summary["run_id"]
        timestamp = summary["timestamp"]
        total = summary["total_questions"]
        passed = summary["passed"]
        partial = summary["partially_correct"]
        failed = summary["failed"]
        hallucinations = summary["hallucinations"]
        errors = summary["execution_errors"]
        acc = summary["accuracy_percent"]
        avg_time = summary["average_response_time_seconds"]

        # Category rows
        cat_rows_html = ""
        for cname, d in summary["category_performance"].items():
            pct = d["accuracy_percent"]
            bar_color = "#22c55e" if pct >= 80 else ("#eab308" if pct >= 50 else "#ef4444")
            cat_rows_html += f"""
            <tr>
                <td><strong>{cname}</strong></td>
                <td>{d['total']}</td>
                <td><span class="badge badge-pass">{d['passed']}</span></td>
                <td><span class="badge badge-partial">{d['partial']}</span></td>
                <td><span class="badge badge-fail">{d['failed']}</span></td>
                <td>
                    <div class="progress-bar-container">
                        <div class="progress-bar" style="width: {pct}%; background-color: {bar_color};"></div>
                    </div>
                    <span>{pct}%</span>
                </td>
            </tr>
            """

        # Failed questions cards
        failed_items = [r for r in summary["results"] if r["status"] != EvaluationStatus.PASS]
        failed_cards_html = ""
        if not failed_items:
            failed_cards_html = "<div class='alert alert-success'>🎉 All 69 questions passed successfully! Zero failures or hallucinations detected.</div>"
        else:
            for r in failed_items:
                badge_class = f"badge-{r['status'].lower()}"
                failed_cards_html += f"""
                <div class="fail-card">
                    <div class="fail-header">
                        <span class="badge {badge_class}">{r['status']}</span>
                        <strong>{r['test_id']} ({r['category_name']}):</strong> {r['question']}
                    </div>
                    <div class="fail-body">
                        <div class="row"><strong>Expected:</strong> <span class="text-expected">{r['expected_answer']}</span></div>
                        <div class="row"><strong>Actual:</strong> <pre>{r['actual_answer'][:300]}</pre></div>
                        <div class="row"><strong>What Went Wrong:</strong> {r['what_went_wrong']}</div>
                        <div class="row"><strong>Failure Category:</strong> <span class="tag">{r['failure_category']}</span></div>
                        <div class="row"><strong>Suggested Correction:</strong> <em>{r['suggested_correction']}</em></div>
                    </div>
                </div>
                """

        # All questions table
        all_rows_html = ""
        for r in summary["results"]:
            badge_class = f"badge-{r['status'].lower()}"
            all_rows_html += f"""
            <tr>
                <td><code>{r['test_id']}</code></td>
                <td>{r['category_name']}</td>
                <td>{r['question']}</td>
                <td><span class="badge {badge_class}">{r['status']}</span></td>
                <td><strong>{r['score']}</strong></td>
                <td>{r['execution_time']}s</td>
                <td><small>{r['reason']}</small></td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faculty Workload LLM Audit Report - {run_id}</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --border: #e2e8f0;
            --pass: #16a34a;
            --partial: #d97706;
            --fail: #dc2626;
            --hallucination: #7c3aed;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: #1e293b;
            color: white;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0 0 6px 0; font-size: 24px; }}
        .header p {{ margin: 0; opacity: 0.8; font-size: 14px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: var(--card-bg);
            padding: 18px;
            border-radius: 8px;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .metric-card .value {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .metric-card .label {{
            font-size: 13px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border);
            padding: 20px;
            margin-bottom: 24px;
        }}
        h2 {{ margin-top: 0; font-size: 18px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: #f1f5f9; font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: white;
        }}
        .badge-pass {{ background: var(--pass); }}
        .badge-partial {{ background: var(--partial); }}
        .badge-fail {{ background: var(--fail); }}
        .badge-hallucination {{ background: var(--hallucination); }}
        .badge-error {{ background: #000; }}
        .progress-bar-container {{
            width: 100px;
            background: #e2e8f0;
            border-radius: 4px;
            height: 10px;
            display: inline-block;
            margin-right: 8px;
            overflow: hidden;
            vertical-align: middle;
        }}
        .progress-bar {{
            height: 100%;
        }}
        .fail-card {{
            background: #fff;
            border: 1px solid #fecaca;
            border-left: 4px solid var(--fail);
            border-radius: 6px;
            padding: 14px;
            margin-bottom: 14px;
        }}
        .fail-header {{
            font-size: 15px;
            margin-bottom: 8px;
        }}
        .fail-body .row {{ margin-bottom: 6px; font-size: 13px; }}
        .tag {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            color: #334155;
        }}
        pre {{
            background: #f8fafc;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            overflow-x: auto;
            margin: 4px 0;
            border: 1px solid #e2e8f0;
            white-space: pre-wrap;
        }}
        .alert-success {{
            background: #dcfce7;
            color: #166534;
            padding: 14px;
            border-radius: 6px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Faculty Workload Intelligence Assistant</h1>
                <p>Automated LLM Testing & Audit Framework Report | Run ID: {run_id}</p>
            </div>
            <div style="text-align: right;">
                <p><strong>Generated:</strong> {timestamp}</p>
                <p><strong>Status:</strong> {summary['llm_provider']}</p>
            </div>
        </div>

        <!-- Metrics Overview -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="value" style="color: #2563eb;">{total}</div>
                <div class="label">Total Questions</div>
            </div>
            <div class="metric-card">
                <div class="value" style="color: var(--pass);">{passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="metric-card">
                <div class="value" style="color: var(--partial);">{partial}</div>
                <div class="label">Partial</div>
            </div>
            <div class="metric-card">
                <div class="value" style="color: var(--fail);">{failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="metric-card">
                <div class="value" style="color: var(--hallucination);">{hallucinations}</div>
                <div class="label">Hallucinations</div>
            </div>
            <div class="metric-card">
                <div class="value" style="color: #0284c7;">{acc}%</div>
                <div class="label">Accuracy</div>
            </div>
            <div class="metric-card">
                <div class="value">{avg_time}s</div>
                <div class="label">Avg Response Time</div>
            </div>
        </div>

        <!-- Category Performance -->
        <div class="card">
            <h2>Category-Wise Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Total</th>
                        <th>Pass</th>
                        <th>Partial</th>
                        <th>Fail</th>
                        <th>Accuracy</th>
                    </tr>
                </thead>
                <tbody>
                    {cat_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Failed Questions Analysis -->
        <div class="card">
            <h2>Failed & Unresolved Questions Diagnostic Report</h2>
            {failed_cards_html}
        </div>

        <!-- All Questions Table -->
        <div class="card">
            <h2>Complete Question-Wise Audit Log (69 Test Cases)</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Category</th>
                        <th>Question</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Time</th>
                        <th>Evaluation Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {all_rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        return html

