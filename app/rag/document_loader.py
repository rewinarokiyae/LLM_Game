"""
Document Loader and Knowledge Base Generator.
Handles ingestion of documents into the RAG pipeline:
1. Extracts text and metadata from Markdown, TXT, PDF (via PyMuPDF), and DOCX.
2. Generates comprehensive synthetic institutional workload policy documents
   from the dataset policies, rules, and guidelines into storage/documents/.
3. Stores document records into document_metadata table.
"""

import os
from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from app.config.settings import settings
from app.config.logging_config import logger
from app.database.connection import get_db_session
from app.database.models import WorkloadPolicy, WorkloadRule, DocumentMetadata

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class DocumentLoader:
    def __init__(self, docs_dir: str = settings.DOCUMENTS_DIR):
        self.docs_dir = docs_dir
        os.makedirs(docs_dir, exist_ok=True)

    def generate_policy_documents_if_missing(self):
        """Generate structured institutional policy document from database models."""
        policy_file = os.path.join(self.docs_dir, "institutional_workload_policy_v1.0.md")
        if not os.path.exists(policy_file):
            lines = []
            lines.append("# UNIVERSITY ACADEMIC WORKLOAD POLICY REGULATIONS (2026-27)")
            lines.append("## Document ID: DOC-POL-2026-V1")
            lines.append("### Approved Institutional Workload Policy - Synthetic University Dataset, Version 1.0\n")

            lines.append("### Section 1: Purpose and Scope")
            lines.append("This regulation governs the allocation, computation, and maximum caps for academic teaching hours across all university departments (Computer Science and Engineering, Artificial Intelligence and Machine Learning, and Data Science). All figures apply weekly to full-time academic faculty.\n")

            lines.append("### Section 2: Designation Workload Thresholds")
            lines.append("| Policy ID | Designation | Max Teaching Hours/Week | Min Teaching Hours/Week | Effective Validity | Source Page |")
            lines.append("|---|---|---|---|---|---|")

            with get_db_session() as session:
                policies = session.query(WorkloadPolicy).all()
                rules = session.query(WorkloadRule).all()

                for p in policies:
                    lines.append(f"| {p.policy_id} | {p.designation} | {p.max_teaching_hours_week} hrs | {p.min_teaching_hours_week} hrs | {p.effective_from} to {p.effective_to} | Page {p.source_page} |")
                lines.append("\n")

                lines.append("### Section 3: Teaching Hour Computation Rules")
                lines.append("Teaching hours are calculated strictly by scheduled duration in the institutional timetable:")
                for r in rules:
                    lines.append(f"- **{r.rule_id} ({r.session_type}):** {r.rule_description} Calculation Method: {r.calculation_method}. Status: {r.included_in_teaching_hours}.")
                lines.append("\n")

            lines.append("### Section 4: Policy Exceptions and Approval Process")
            lines.append("1. **Temporary Workload Overrides:** A faculty member may be allocated teaching hours exceeding the standard maximum cap only if a formal policy exception has been officially APPROVED by the Dean/Registrar prior to the evaluation week.")
            lines.append("2. **Pending and Rejected Exceptions:** Applications with status 'Pending' or 'Rejected' do NOT override the policy maximum limit under any circumstances.")
            lines.append("3. **Validity Period:** Approved exceptions are strictly valid only between their valid_from and valid_to dates.\n")

            lines.append("### Section 5: Workload Exemptions and Administrative Relief")
            lines.append("1. **Relief on Minimum Workload:** Faculty holding administrative responsibilities (such as Head of Department - HOD) receive approved relief hours per week reducing their minimum expected teaching commitment.")
            lines.append("2. **Maximum Cap Invariance:** Workload exemptions do NOT raise the maximum teaching-hour cap. The standard maximum limit remains operative unless an approved policy exception exists.\n")

            lines.append("### Section 6: Non-Teaching Academic Responsibilities")
            lines.append("Academic responsibilities including Question Paper Preparation, Internal Assessment Evaluation, Project Supervision, and Examination Invigilation are tracked separately as assignments and are excluded from weekly timetable teaching-hour calculations.\n")

            with open(policy_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info(f"Generated synthetic institutional policy document at {policy_file}")

    def load_document(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from a file (.md, .txt, .pdf, .docx)."""
        ext = os.path.splitext(file_path)[1].lower()
        base_name = os.path.basename(file_path)

        metadata = {
            "document_id": f"DOC_{os.path.splitext(base_name)[0]}",
            "document_name": base_name,
            "department": "ALL",
            "policy_id": "POL-ALL",
            "academic_year": "2026-27",
            "effective_date": "2026-07-01",
            "source_page": 12,
            "version": "1.0",
            "file_path": file_path
        }

        text = ""
        if ext in [".md", ".txt"]:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

        elif ext == ".pdf":
            if HAS_PYMUPDF:
                doc = fitz.open(file_path)
                pages_text = []
                for pno in range(len(doc)):
                    pages_text.append(f"--- Page {pno + 1} ---\n" + doc[pno].get_text())
                text = "\n\n".join(pages_text)
                metadata["page_count"] = len(doc)
            else:
                raise ImportError("PyMuPDF (fitz) is required to extract PDF documents.")

        elif ext == ".docx":
            if HAS_DOCX:
                doc = docx.Document(file_path)
                text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            else:
                raise ImportError("python-docx is required to extract DOCX documents.")

        return text, metadata

    def load_all_documents(self) -> List[Tuple[str, Dict[str, Any]]]:
        self.generate_policy_documents_if_missing()
        docs = []
        for fname in os.listdir(self.docs_dir):
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".md", ".txt", ".pdf", ".docx"]:
                fpath = os.path.join(self.docs_dir, fname)
                try:
                    text, meta = self.load_document(fpath)
                    docs.append((text, meta))
                except Exception as e:
                    logger.error(f"Failed to load document {fpath}: {e}")
        return docs
