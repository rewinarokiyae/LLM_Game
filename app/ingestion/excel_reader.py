"""
Excel Reader Module.
Safely reads worksheets from the source Excel workbook without modifying the file.
Provides raw dataframes and metadata.
"""

import os
from typing import Dict, List
import pandas as pd
from app.config.logging_config import logger


class ExcelReader:
    def __init__(self, excel_path: str):
        self.excel_path = os.path.abspath(excel_path)
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Source Excel workbook not found at: {self.excel_path}")
        self.xl = pd.ExcelFile(self.excel_path)
        self.sheet_names = self.xl.sheet_names
        logger.info(f"Loaded Excel workbook with {len(self.sheet_names)} sheets from {self.excel_path}")

    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        if sheet_name not in self.sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' not found in workbook. Available: {self.sheet_names}")
        df = self.xl.parse(sheet_name)
        return df

    def read_all_sheets(self) -> Dict[str, pd.DataFrame]:
        return {s: self.read_sheet(s) for s in self.sheet_names}

