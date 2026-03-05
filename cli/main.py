"""
RCPSP MILP Solver  –  CLI entry point
======================================
All three priority-rule heuristics (LPT, CPP, MSS) are always run and
compared.  The MILP is applied where appropriate based on problem size.

Usage
-----
::

    python -m cli.main --excel path/to/project.xlsx
    python -m cli.main --excel data.xlsx --output ./results --time_limit 600
    python -m cli.main --excel data.xlsx --tasks_per_page 40
"""

import argparse
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from input import ExcelDataLoader
from validation import DataValidator
from solver import RCPSPSolver
from orchestration import RCPSPOrchestrator
from config import ModelConfig, OutputConfig, VisualizationConfig
from utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="RCPSP MILP Solver — Industrial Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Heuristic behaviour
-------------------
All three priority-rule heuristics (LPT, CPP, MSS) are always executed
and compared.  The best result is used as the heuristic solution.

Problem-size strategy selection
--------------------------------
  ≤ 30 activities   →  Exact MILP  (heuristics shown first as reference)
  31–100 activities →  Hybrid      (heuristics + MILP with half time budget)
  > 100 activities  →  Heuristic   (no MILP; heuristics only)

Examples
--------
  python -m cli.main --excel data/project.xlsx
  python -m cli.main --excel data.xlsx --output ./results --time_limit 600
  python -m cli.main --excel data.xlsx --tasks_per_page 40
        """,
    )

    parser.add_argument(
        "--excel", type=str, required=True,
        help="Path to input Excel file",
    )
    parser.add_argument(
        "--output", type=str, default="./output",
        help="Base output directory (default: ./output)",
    )
    parser.add_argument(
        "--time_limit", type=int, default=300,
        help="MILP solver time limit in seconds (default: 300)",
    )
    parser.add_argument(
        "--tasks_per_page", type=int, default=60,
        help="Number of tasks per Gantt chart page (default: 60)",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    setup_logging()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)

    model_config  = ModelConfig(DEFAULT_TIME_LIMIT=args.time_limit)
    output_config = OutputConfig(BASE_DIR=Path(args.output))
    viz_config    = VisualizationConfig(TASKS_PER_PAGE=args.tasks_per_page)

    data_loader = ExcelDataLoader(config=model_config)
    validator   = DataValidator()
    solver      = RCPSPSolver(config=model_config, time_limit=args.time_limit)

    orchestrator = RCPSPOrchestrator(
        data_loader=data_loader,
        validator=validator,
        solver=solver,
        output_config=output_config,
        visualization_config=viz_config,
    )

    result = orchestrator.run(str(excel_path))

    if result.success:
        sys.exit(0)
    else:
        print(f"\n✗ Failed: {result.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
