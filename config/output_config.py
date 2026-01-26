from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class OutputConfig:
    """Configuration for output directories and file names."""
    
    BASE_DIR: Path = Path("./output")
    LOG_FILE: str = "rcpsp_solver.log"
    
    FLOWCHART_NAME: str = "Program_Flowchart.png"
    GANTT_PREFIX: str = "Gantt_Chart"
    RESOURCE_UTIL_PREFIX: str = "Resource_Utilization"
    SUMMARY_METRICS_PREFIX: str = "Summary_Metrics"
    
    EXCEL_PREFIX: str = "RCPSP_Results"