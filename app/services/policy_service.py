"""
Policy Service.
Provides retrieval of structured workload policies, calculation rules,
and institutional policy guidelines with accurate citations.
"""

from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import WorkloadPolicy, WorkloadRule
from app.engines.workload_engine import DEFAULT_TARGET_WEEK


class PolicyService:
    @classmethod
    def get_policy_for_designation(
        cls,
        designation: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        ref_date = target_date or DEFAULT_TARGET_WEEK
        with get_db_session() as session:
            pol = session.query(WorkloadPolicy).filter(
                WorkloadPolicy.designation.ilike(designation.strip()),
                WorkloadPolicy.effective_from <= ref_date,
                WorkloadPolicy.effective_to >= ref_date
            ).first()

            if not pol:
                return None

            return {
                "policy_id": pol.policy_id,
                "designation": pol.designation,
                "department_scope": pol.department_scope,
                "max_teaching_hours_week": pol.max_teaching_hours_week,
                "min_teaching_hours_week": pol.min_teaching_hours_week,
                "measurement_period": pol.measurement_period,
                "calculation_rule": pol.calculation_rule,
                "effective_from": pol.effective_from.isoformat(),
                "effective_to": pol.effective_to.isoformat(),
                "source_document": pol.source_document,
                "source_page": pol.source_page
            }

    @classmethod
    def list_all_policies(cls) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            policies = session.query(WorkloadPolicy).all()
            return [
                {
                    "policy_id": p.policy_id,
                    "designation": p.designation,
                    "department_scope": p.department_scope,
                    "max_teaching_hours_week": p.max_teaching_hours_week,
                    "min_teaching_hours_week": p.min_teaching_hours_week,
                    "measurement_period": p.measurement_period,
                    "calculation_rule": p.calculation_rule,
                    "effective_from": p.effective_from.isoformat(),
                    "effective_to": p.effective_to.isoformat(),
                    "source_document": p.source_document,
                    "source_page": p.source_page
                }
                for p in policies
            ]

    @classmethod
    def get_workload_rules(cls) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            rules = session.query(WorkloadRule).all()
            return [
                {
                    "rule_id": r.rule_id,
                    "session_type": r.session_type,
                    "weight": r.weight,
                    "calculation_method": r.calculation_method,
                    "included_in_teaching_hours": r.included_in_teaching_hours,
                    "rule_description": r.rule_description
                }
                for r in rules
            ]

