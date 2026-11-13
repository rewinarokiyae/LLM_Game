"""
Policy Validation Engine.
Validates faculty teaching workload against institutional policies, exceptions, and exemptions.
Deterministic logic:
- Standard maximum and minimum limits selected by designation and validity dates.
- Policy exceptions: ONLY Approved and active exceptions override maximum teaching hours.
  Pending and Rejected exceptions are explicitly ignored for cap overrides and reported.
- Workload exemptions: ONLY Approved and active exemptions reduce minimum expected teaching hours.
  Exemptions never raise the maximum teaching cap.
- Excess hours = max(0.0, actual_hours - effective_max_hours).
- Violation = excess_hours > 0.
"""

from datetime import date
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import Faculty, WorkloadPolicy, PolicyException, WorkloadExemption
from app.engines.workload_engine import WorkloadEngine, DEFAULT_TARGET_WEEK


class PolicyValidator:
    @classmethod
    def evaluate_faculty_workload(
        cls,
        faculty_id: str,
        week_start: Optional[date] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Evaluate full workload status and policy compliance for a given faculty member.
        """
        target_week = week_start or DEFAULT_TARGET_WEEK

        def _evaluate(db: Session) -> Dict[str, Any]:
            # 1. Compute actual teaching hours
            workload_data = WorkloadEngine.get_faculty_teaching_hours(faculty_id, target_week, db)
            actual_hours = workload_data["actual_teaching_hours"]
            designation = workload_data["designation"]
            dept_id = workload_data["department_id"]

            # 2. Lookup standard policy for designation and target week
            policy = db.query(WorkloadPolicy).filter(
                WorkloadPolicy.designation == designation,
                WorkloadPolicy.effective_from <= target_week,
                WorkloadPolicy.effective_to >= target_week
            ).first()

            if not policy:
                return {
                    "faculty_id": faculty_id,
                    "faculty_name": workload_data["faculty_name"],
                    "designation": designation,
                    "department_id": dept_id,
                    "week_start": target_week.isoformat(),
                    "actual_teaching_hours": actual_hours,
                    "policy_found": False,
                    "policy_violation": None,
                    "message": f"Applicable institutional workload policy could not be determined for designation '{designation}' during week {target_week}."
                }

            std_max = float(policy.max_teaching_hours_week)
            std_min = float(policy.min_teaching_hours_week)
            effective_max = std_max
            effective_min = std_min

            # 3. Check Policy Exceptions
            exceptions = db.query(PolicyException).filter(
                PolicyException.faculty_id == faculty_id,
                PolicyException.valid_from <= target_week,
                PolicyException.valid_to >= target_week
            ).all()

            applied_exception = None
            pending_exceptions = []
            rejected_exceptions = []

            for exc in exceptions:
                if exc.approval_status == "Approved":
                    applied_exception = {
                        "exception_id": exc.exception_id,
                        "max_hours_override": float(exc.max_hours_override),
                        "approval_status": "Approved",
                        "reason": exc.reason,
                        "approved_by": exc.approved_by,
                        "valid_from": exc.valid_from.isoformat(),
                        "valid_to": exc.valid_to.isoformat()
                    }
                    effective_max = float(exc.max_hours_override)
                elif exc.approval_status == "Pending":
                    pending_exceptions.append({
                        "exception_id": exc.exception_id,
                        "max_hours_override": float(exc.max_hours_override),
                        "approval_status": "Pending",
                        "reason": exc.reason
                    })
                elif exc.approval_status == "Rejected":
                    rejected_exceptions.append({
                        "exception_id": exc.exception_id,
                        "max_hours_override": float(exc.max_hours_override),
                        "approval_status": "Rejected",
                        "reason": exc.reason
                    })

            # 4. Check Workload Exemptions
            exemptions = db.query(WorkloadExemption).filter(
                WorkloadExemption.faculty_id == faculty_id,
                WorkloadExemption.valid_from <= target_week,
                WorkloadExemption.valid_to >= target_week
            ).all()

            applied_exemption = None
            for exm in exemptions:
                if exm.approval_status == "Approved":
                    relief = float(exm.relief_hours_per_week)
                    applied_exemption = {
                        "exemption_id": exm.exemption_id,
                        "relief_hours_per_week": relief,
                        "responsibility": exm.responsibility,
                        "approval_status": "Approved",
                        "reason": exm.reason,
                        "approved_by": exm.approved_by
                    }
                    effective_min = max(0.0, std_min - relief)

            # 5. Calculate excess hours & violation status
            excess_hours = max(0.0, actual_hours - effective_max)
            is_violation = (actual_hours > effective_max)

            # Build readable explanation
            explanation = []
            explanation.append(f"Faculty Member: {workload_data['faculty_name']} ({faculty_id}), Designation: {designation}")
            explanation.append(f"Teaching Week: {target_week.isoformat()} to {(target_week).isoformat()}")
            explanation.append(f"Actual Scheduled Teaching Hours: {actual_hours:.1f} hrs")
            explanation.append(f"Standard Policy Max Hours: {std_max:.1f} hrs (Policy ID: {policy.policy_id})")

            if applied_exception:
                explanation.append(
                    f"Approved Exception Applied: {applied_exception['exception_id']} overrides max cap to {effective_max:.1f} hrs (Reason: {applied_exception['reason']}, Approved by: {applied_exception['approved_by']})"
                )
            if pending_exceptions:
                for pe in pending_exceptions:
                    explanation.append(
                        f"Notice: Exception {pe['exception_id']} is PENDING ({pe['max_hours_override']} hrs request) and DOES NOT override policy cap."
                    )
            if rejected_exceptions:
                for re in rejected_exceptions:
                    explanation.append(
                        f"Notice: Exception {re['exception_id']} was REJECTED and DOES NOT override policy cap."
                    )

            if applied_exemption:
                explanation.append(
                    f"Approved Relief Applied: {applied_exemption['exemption_id']} provides {applied_exemption['relief_hours_per_week']:.1f} hrs relief on minimum workload for {applied_exemption['responsibility']} duties. Effective minimum: {effective_min:.1f} hrs. (Relief does not change maximum cap)."
                )

            explanation.append(f"Effective Maximum Cap: {effective_max:.1f} hrs")
            explanation.append(f"Excess Hours: {excess_hours:.1f} hrs")

            if is_violation:
                explanation.append(f"STATUS: POLICY VIOLATION DETECTED. Exceeds limit by {excess_hours:.1f} hours.")
            else:
                explanation.append(f"STATUS: COMPLIANT WITH POLICY. Teaching load is within the allowed limit.")

            return {
                "faculty_id": faculty_id,
                "faculty_name": workload_data["faculty_name"],
                "designation": designation,
                "department_id": dept_id,
                "week_start": target_week.isoformat(),
                "actual_teaching_hours": actual_hours,
                "standard_policy_max_hours": std_max,
                "effective_max_hours": effective_max,
                "min_teaching_hours_week": std_min,
                "effective_min_hours": effective_min,
                "excess_hours": excess_hours,
                "policy_violation": "Yes" if is_violation else "No",
                "is_violation": is_violation,
                "policy_id": policy.policy_id,
                "source_document": policy.source_document,
                "source_page": policy.source_page,
                "applied_exception": applied_exception,
                "applied_exemption": applied_exemption,
                "pending_exceptions": pending_exceptions,
                "rejected_exceptions": rejected_exceptions,
                "breakdown_hours": workload_data["breakdown_hours"],
                "explanation": "\n".join(explanation)
            }

        if session:
            return _evaluate(session)
        with get_db_session() as db:
            return _evaluate(db)

