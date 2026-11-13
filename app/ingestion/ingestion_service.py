"""
Data Ingestion Service Orchestrator.
Orchestrates:
1. Audit and data quality report generation
2. Source Excel reading
3. In-memory data cleaning and anomaly resolution
4. Idempotent relational database loading
5. Post-load verification

Runnable directly via:
python -m app.ingestion.ingestion_service
"""

import sys
import os
from typing import Dict, Any
from rich.console import Console
from rich.table import Table

from app.config.settings import settings
from app.config.logging_config import logger
from app.ingestion.data_validator import run_audit
from app.ingestion.excel_reader import ExcelReader
from app.ingestion.data_cleaner import DataCleaner
from app.ingestion.database_loader import DatabaseLoader
from app.database.connection import get_db_session
from app.database.models import Faculty, Timetable, WorkloadPolicy, IngestionHistory


class IngestionService:
    def __init__(self, excel_path: str = settings.DATASET_PATH):
        self.excel_path = excel_path
        self.console = Console()

    def run(self) -> Dict[str, Any]:
        self.console.print(f"[bold blue]Starting Ingestion Pipeline for:[/bold blue] {self.excel_path}")

        # Step 1: Audit and report
        self.console.print("[cyan]Step 1: Running dataset audit & data quality verification...[/cyan]")
        audit_results = run_audit(self.excel_path, settings.REPORTS_DIR + "/data_quality")

        # Step 2: Read Excel
        self.console.print("[cyan]Step 2: Reading Excel workbook sheets...[/cyan]")
        reader = ExcelReader(self.excel_path)
        raw_dfs = reader.read_all_sheets()

        # Step 3: Clean and Normalize
        self.console.print("[cyan]Step 3: Cleaning dataset & resolving reported anomalies...[/cyan]")
        cleaned_dfs = DataCleaner.clean_all(raw_dfs)

        # Step 4: Load into Database
        self.console.print("[cyan]Step 4: Loading records idempotently into relational database...[/cyan]")
        loader = DatabaseLoader()
        loaded_counts = loader.load_all(cleaned_dfs, source_file=self.excel_path)

        # Step 5: Post-load Verification
        self.console.print("[cyan]Step 5: Running post-load verification...[/cyan]")
        with get_db_session() as session:
            fac_count = session.query(Faculty).count()
            tt_count = session.query(Timetable).count()
            pol_count = session.query(WorkloadPolicy).count()
            hist_count = session.query(IngestionHistory).count()

        # Print Rich Summary Table
        table = Table(title="Data Ingestion Results Summary", show_header=True, header_style="bold green")
        table.add_column("Sheet Name", style="cyan")
        table.add_column("Records Loaded", justify="right")
        table.add_column("Status", style="bold green")

        for sheet, count in loaded_counts.items():
            table.add_row(sheet, str(count), "SUCCESS")

        self.console.print(table)
        self.console.print(f"[bold green]Ingestion Completed Successfully![/bold green] (Faculty: {fac_count}, Timetable Entries: {tt_count}, Policies: {pol_count})\n")

        return {
            "status": "SUCCESS",
            "loaded_counts": loaded_counts,
            "post_load_counts": {
                "faculty": fac_count,
                "timetable": tt_count,
                "policies": pol_count
            }
        }


if __name__ == "__main__":
    service = IngestionService()
    service.run()

