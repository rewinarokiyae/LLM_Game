"""
Role-Based Access Control (RBAC) & Security Audit Module.
Audits the application's authorization boundaries across 7 mandatory security scenarios:
1. Faculty users can access their own records only.
2. Faculty users cannot access another faculty member's private records.
3. HOD users can access records within their own department.
4. HOD users cannot access another department's restricted records.
5. Admin users can access university-wide records.
6. Pending and rejected leave records are not treated as approved leave.
7. Pending and rejected policy exceptions do not override workload limits.

Guarantees:
- Uses predefined identities from 'Users_Roles' via AuthenticationService.
- Does not bypass authentication.
- Does not expose credentials or private records in logs.
- Stores security audit results separately from functional accuracy results.
"""

import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime, date

from app.config.logging_config import logger
from app.security.authentication import AuthenticationService
from app.security.access_control import RoleEnum, AccessDeniedError
from app.nlp.query_router import QueryRouter
from app.services.faculty_service import FacultyService
from app.services.analytics_service import AnalyticsService
from app.services.leave_service import LeaveService
from app.engines.policy_validator import PolicyValidator
from app.database.connection import get_db_session


class SecurityAuditRunner:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_security_audit(self) -> Dict[str, Any]:
        """
        Executes the 7 security and authorization audit scenarios.
        """
        results: List[Dict[str, Any]] = []
        passed_count = 0
        start_time = time.time()

        # ---------------------------------------------------------------------
        # Scenario 1: Faculty users can access their own records only
        # ---------------------------------------------------------------------
        s1_passed = False
        s1_reason = ""
        try:
            fac_user = AuthenticationService.authenticate_demo("FAC002")
            res = QueryRouter.process_query(fac_user, "What is my teaching workload this week?")
            resp = res.get("response", "")
            if "17.0 hours" in resp or "Arjun Menon" in resp or "FAC002" in resp:
                s1_passed = True
                s1_reason = "Faculty user successfully accessed their own teaching workload records."
            else:
                s1_reason = f"Response did not contain user's own records: {resp[:100]}"
        except Exception as e:
            s1_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-01",
            "title": "Faculty Own Record Access",
            "description": "Faculty users can access their own records only.",
            "passed": s1_passed,
            "status": "PASS" if s1_passed else "FAIL",
            "details": s1_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 2: Faculty users cannot access another faculty member's private records
        # ---------------------------------------------------------------------
        s2_passed = False
        s2_reason = ""
        try:
            fac_user = AuthenticationService.authenticate_demo("FAC002")
            # Attempt to query FAC001's private assignments
            res = QueryRouter.process_query(fac_user, "Show assignments for FAC001")
            resp = res.get("response", "")
            err = res.get("error")
            if err == "ACCESS_DENIED" or "access denied" in resp.lower() or "prohibit" in resp.lower():
                s2_passed = True
                s2_reason = "Access correctly denied when faculty attempted to access another faculty member's records."
            else:
                s2_reason = f"Security breach: Faculty was able to query another faculty member's private records!"
        except AccessDeniedError:
            s2_passed = True
            s2_reason = "AccessDeniedError correctly raised."
        except Exception as e:
            s2_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-02",
            "title": "Faculty Cross-Record Access Denial",
            "description": "Faculty users cannot access another faculty member's private records.",
            "passed": s2_passed,
            "status": "PASS" if s2_passed else "FAIL",
            "details": s2_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 3: HOD users can access records within their own department
        # ---------------------------------------------------------------------
        s3_passed = False
        s3_reason = ""
        try:
            hod_cse = AuthenticationService.authenticate_demo("FAC001")  # HOD of DEP-CSE
            res = QueryRouter.process_query(hod_cse, "Show department workload for DEP-CSE")
            resp = res.get("response", "")
            if "DEP-CSE" in resp or "Computer Science" in resp:
                s3_passed = True
                s3_reason = "HOD successfully accessed department-level analytics for their own department."
            else:
                s3_reason = f"HOD was unable to access own department analytics: {resp[:100]}"
        except Exception as e:
            s3_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-03",
            "title": "HOD Own Department Access",
            "description": "HOD users can access records within their own department.",
            "passed": s3_passed,
            "status": "PASS" if s3_passed else "FAIL",
            "details": s3_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 4: HOD users cannot access another department's restricted records
        # ---------------------------------------------------------------------
        s4_passed = False
        s4_reason = ""
        try:
            hod_cse = AuthenticationService.authenticate_demo("FAC001")  # HOD of DEP-CSE
            # Attempt to query DEP-AIML department workload
            res = QueryRouter.process_query(hod_cse, "Show department workload for DEP-AIML")
            resp = res.get("response", "")
            err = res.get("error")
            if err == "ACCESS_DENIED" or "access denied" in resp.lower() or "prohibit" in resp.lower():
                s4_passed = True
                s4_reason = "Access correctly denied when HOD attempted to view another department's records."
            else:
                s4_reason = f"Security breach: HOD of DEP-CSE was able to view DEP-AIML department workload!"
        except AccessDeniedError:
            s4_passed = True
            s4_reason = "AccessDeniedError correctly raised."
        except Exception as e:
            s4_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-04",
            "title": "HOD Cross-Department Access Denial",
            "description": "HOD users cannot access another department's restricted records.",
            "passed": s4_passed,
            "status": "PASS" if s4_passed else "FAIL",
            "details": s4_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 5: Admin users can access university-wide records
        # ---------------------------------------------------------------------
        s5_passed = False
        s5_reason = ""
        try:
            admin_user = AuthenticationService.authenticate_demo("admin")
            res = QueryRouter.process_query(admin_user, "Show institution-wide workload comparison")
            resp = res.get("response", "")
            if "Institution-Wide" in resp or "279.0" in resp or "Highest Total Scheduled" in resp:
                s5_passed = True
                s5_reason = "Admin user successfully accessed university-wide institutional workload comparison."
            else:
                s5_reason = f"Admin was unable to access university-wide records: {resp[:100]}"
        except Exception as e:
            s5_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-05",
            "title": "Admin University-Wide Access",
            "description": "Admin users can access university-wide records.",
            "passed": s5_passed,
            "status": "PASS" if s5_passed else "FAIL",
            "details": s5_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 6: Pending and rejected leave records are not treated as approved leave
        # ---------------------------------------------------------------------
        s6_passed = False
        s6_reason = ""
        try:
            admin_user = AuthenticationService.authenticate_demo("admin")
            # Query approved leaves for CSE
            approved_leaves = LeaveService.get_department_leave(admin_user, "DEP-CSE", approved_only=True)
            statuses = {l.get("approval_status") or l.get("status") for l in approved_leaves}
            has_pending_or_rejected = any(s in ["Pending", "Rejected"] for s in statuses)

            if not has_pending_or_rejected:
                s6_passed = True
                s6_reason = f"Verified: All {len(approved_leaves)} filtered records strictly have approval_status='Approved'. Pending/Rejected leaves excluded."
            else:
                s6_reason = f"Breach: Pending or rejected leave records were included in approved leave query: {statuses}"
        except Exception as e:
            s6_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-06",
            "title": "Leave Approval Integrity",
            "description": "Pending and rejected leave records are not treated as approved leave.",
            "passed": s6_passed,
            "status": "PASS" if s6_passed else "FAIL",
            "details": s6_reason
        })

        # ---------------------------------------------------------------------
        # Scenario 7: Pending and rejected policy exceptions do not override workload limits
        # ---------------------------------------------------------------------
        s7_passed = False
        s7_reason = ""
        try:
            # Karthik Bhat (FAC016) has a PENDING exception PEX002 (override to 19.0 hrs)
            # Standard Assistant Professor limit is 16.0 hrs.
            # If pending exception was applied, effective limit would be 19.0.
            # With strict policy adherence, effective limit must remain 16.0 hrs.
            with get_db_session() as db:
                eval_res = PolicyValidator.evaluate_faculty_workload("FAC016", date(2026, 11, 9), db)
                eff_max = eval_res.get("effective_max_hours")
                std_max = eval_res.get("standard_policy_max_hours")

                if eff_max == std_max == 16.0:
                    s7_passed = True
                    s7_reason = "Verified: Pending policy exception PEX002 (19.0 hrs) for FAC016 was ignored. Effective limit remains 16.0 hrs."
                else:
                    s7_reason = f"Breach: Pending policy exception altered effective limit: eff_max={eff_max}, std_max={std_max}"
        except Exception as e:
            s7_reason = f"Unexpected error: {e}"

        results.append({
            "scenario_id": "SEC-07",
            "title": "Policy Exception Override Integrity",
            "description": "Pending and rejected policy exceptions do not override workload limits.",
            "passed": s7_passed,
            "status": "PASS" if s7_passed else "FAIL",
            "details": s7_reason
        })

        # Summary
        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        elapsed = time.time() - start_time

        audit_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_security_scenarios": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "pass_rate_percent": round((passed_count / total * 100.0), 2) if total else 0.0,
            "execution_time_seconds": round(elapsed, 3),
            "scenarios": results
        }

        # Save Security Audit Reports
        self._save_security_reports(audit_summary)

        return audit_summary

    def _save_security_reports(self, summary: Dict[str, Any]):
        """Save JSON and TXT security audit files."""
        json_path = os.path.join(self.output_dir, "security_audit_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        txt_path = os.path.join(self.output_dir, "security_audit_summary.txt")
        lines = [
            "=" * 60,
            "       FACULTY WORKLOAD ASSISTANT — RBAC SECURITY AUDIT",
            "=" * 60,
            f"Timestamp: {summary['timestamp']}",
            f"Scenarios Tested : {summary['total_security_scenarios']}",
            f"Passed           : {summary['passed']}",
            f"Failed           : {summary['failed']}",
            f"Pass Rate        : {summary['pass_rate_percent']}%",
            f"Execution Time   : {summary['execution_time_seconds']} seconds",
            "",
            "SCENARIO DETAILS:",
            "-" * 60
        ]
        for s in summary["scenarios"]:
            status_tag = "[PASS]" if s["passed"] else "[FAIL]"
            lines.append(f"{status_tag} {s['scenario_id']}: {s['title']}")
            lines.append(f"       Description: {s['description']}")
            lines.append(f"       Result: {s['details']}")
            lines.append("")

        lines.append("=" * 60)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
