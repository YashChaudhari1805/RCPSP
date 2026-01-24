import argparse
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from input import ExcelDataLoader
from validation import DataValidator
from solver import RCPSPSolver
from orchestration import RCPSPOrchestrator
from config import ModelConfig, OutputConfig
from utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RCPSP MILP Solver - Industrial Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cli.main --excel data/project.xlsx
  python -m cli.main --excel data/project.xlsx --output ./results --time_limit 600
        """
    )
    
    parser.add_argument(
        "--excel",
        type=str,
        required=True,
        help="Path to input Excel file"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Base output directory (default: ./output)"
    )
    
    parser.add_argument(
        "--time_limit",
        type=int,
        default=300,
        help="Solver time limit in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--tasks_per_page",
        type=int,
        default=60,
        help="Number of tasks per Gantt chart page (default: 60)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for CLI."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging()
    
    # Validate input file exists
    excel_path = Path(args.excel)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)
    
    # Initialize components
    model_config = ModelConfig()
    output_config = OutputConfig()
    
    data_loader = ExcelDataLoader()
    validator = DataValidator()
    solver = RCPSPSolver(config=model_config, time_limit=args.time_limit)
    
    # Create orchestrator
    orchestrator = RCPSPOrchestrator(
        data_loader=data_loader,
        validator=validator,
        solver=solver,
        output_base_dir=Path(args.output)
    )
    
    # Run optimization
    result = orchestrator.run(str(excel_path))
    
    # Exit with appropriate code
    if result.success:
        sys.exit(0)
    else:
        print(f"\n✗ Failed: {result.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()