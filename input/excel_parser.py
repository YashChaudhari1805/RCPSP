import pandas as pd
from pathlib import Path
import logging

from .interfaces import IDataLoader
from .multi_sheet_parser import MultiSheetParser
from .single_sheet_parser import SingleSheetParser
from .psplib_parser import PSPLibParser
from models import ProjectData
from config import ModelConfig

logger = logging.getLogger(__name__)


class ExcelDataLoader(IDataLoader):
    """Loads project data from Excel files."""

    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.multi_parser = MultiSheetParser(self.config)
        self.single_parser = SingleSheetParser(self.config)
        self.psplib_parser = PSPLibParser(self.config)

    def load(self, filepath: str) -> ProjectData:
        """
        Load project data from Excel file.

        Automatically detects format:
        1. PSPLIB format  — sheets: "Project Info", "Resource Avail", "Requests", "Precedence"
        2. Multi-sheet format — sheets: "Activities", "Precedence", "Resources*", "Usage*"
        3. Single-sheet format — single sheet with ActivityID / Duration columns

        Args:
            filepath: Path to Excel file

        Returns:
            ProjectData instance
        """
        logger.info(f"Loading data from {filepath}")

        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {filepath}")

        try:
            xls = pd.ExcelFile(filepath)
            sheet_names = {s.strip() for s in xls.sheet_names}

            if self._is_psplib_format(sheet_names):
                logger.info("Detected PSPLIB format")
                data = self.psplib_parser.parse(filepath, sheet_names)
            elif self._is_multi_sheet_format(sheet_names):
                logger.info("Detected multi-sheet format")
                data = self.multi_parser.parse(filepath, sheet_names)
            else:
                logger.info("Detected single-sheet format")
                data = self.single_parser.parse(filepath)

            logger.info("Data loaded successfully")
            return data

        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise ValueError(f"Failed to load Excel file: {e}")

    @staticmethod
    def _is_multi_sheet_format(sheet_names: set) -> bool:
        """Detect standard multi-sheet format."""
        return {"Activities", "Precedence"}.issubset(sheet_names)

    @staticmethod
    def _is_psplib_format(sheet_names: set) -> bool:
        """Detect PSPLIB Excel format."""
        return {"Project Info", "Resource Avail", "Requests", "Precedence"}.issubset(sheet_names)
