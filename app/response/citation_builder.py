"""
Citation Builder.
Constructs verifiable, grounded institutional citations for policy and dataset sources.
"""

from typing import Dict, Any, List, Optional


class CitationBuilder:
    @staticmethod
    def build_policy_citation(
        policy_id: str,
        source_document: Optional[str] = None,
        source_page: Optional[Any] = None,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        rule_id: Optional[str] = None
    ) -> str:
        doc = source_document or "Approved institutional workload policy - synthetic demo, v1.0"
        page = f"Page {source_page}" if source_page is not None else "Page information unavailable in source metadata"
        dates = f" (Effective: {effective_from} to {effective_to})" if effective_from else ""
        rule = f" | Rule: {rule_id}" if rule_id else ""

        return f"[Policy Source: {doc} | Policy ID: {policy_id} | {page}{dates}{rule}]"

    @staticmethod
    def build_data_sheet_citation(sheet_name: str, key_col: str, key_val: str) -> str:
        return f"[Data Source: Worksheet '{sheet_name}' (Record: {key_col}={key_val})]"

