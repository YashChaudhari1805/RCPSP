from pathlib import Path
import logging

from input import IDataLoader
from validation import IDataValidator
from solver import ISolver
from visualization import (
    FlowchartGenerator,
    GanttChartRenderer,
    ResourceUtilizationRenderer,
    SummaryMetricsRenderer
)
from export import ExcelExporter
from .run_result import RunResult
from utils import now_stamp, safe_mkdir
from config import OutputConfig, VisualizationConfig, ModelConfig

logger = logging.getLogger(__name__)


class RCPSPOrchestrator:
    """Orchestrates the complete RCPSP solving process."""

    def __init__(
        self,
        data_loader: IDataLoader,
        validator: IDataValidator,
        solver: ISolver,
        output_config: OutputConfig = None,
        visualization_config: VisualizationConfig = None,
        model_config: ModelConfig = None
    ):
        self.data_loader = data_loader
        self.validator = validator
        self.solver = solver

        self.output_config = output_config or OutputConfig()
        self.viz_config = visualization_config or VisualizationConfig()
        # Fix #7: thread model_config through to all components that need dummy IDs
        self.model_config = model_config or ModelConfig()
        self.output_base_dir = self.output_config.BASE_DIR

        # Visualization components
        self.flowchart_gen = FlowchartGenerator(self.output_config)
        self.gantt_renderer = GanttChartRenderer(self.viz_config, self.output_config)
        self.resource_renderer = ResourceUtilizationRenderer(self.viz_config, self.output_config)
        self.metrics_renderer = SummaryMetricsRenderer(
            self.viz_config, self.output_config, self.model_config
        )

        # Export components — pass model_config so dummy filtering is config-driven
        self.excel_exporter = ExcelExporter(self.output_config, self.model_config)

    def run(self, excel_path: str) -> RunResult:
        """
        Run complete RCPSP optimization process.

        Args:
            excel_path: Path to input Excel file

        Returns:
            RunResult with success status and outputs
        """
        input_stem = Path(excel_path).stem  # e.g. "j1201_1" from "j1201_1.xlsx"

        # Fix (naming): run directory now includes the input filename so every
        # output folder is directly traceable to the file that produced it.
        # Format:  <base_dir>/<input_stem>_<timestamp>/
        run_dir = self._setup_run_directory(input_stem)

        print("=" * 70)
        print("RCPSP SOLVER — INDUSTRIAL VERSION")
        print("=" * 70)
        print(f"Input file  : {excel_path}")
        print(f"Output dir  : {run_dir}\n")

        # Load data
        print("--- Loading Input Data ---")
        try:
            data = self.data_loader.load(excel_path)
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return RunResult.failed(f"Data loading failed: {e}")

        # Validate data
        print("\n--- Validating Data ---")
        validation_result = self.validator.validate(data)

        if not validation_result.is_valid:
            for error in validation_result.errors:
                print(f"ERROR: {error}")
            return RunResult.failed("Data validation failed")

        print("✓ Data validation passed")

        # Generate flowchart
        print("\n--- Generating Project Network Diagram ---")
        try:
            self.flowchart_gen.generate(data, run_dir)
        except Exception as e:
            logger.error(f"Failed to generate network diagram: {e}")
            print(f"⚠ Warning: Could not generate network diagram: {e}")

        # Solve
        print("\n--- Solving Optimization Problem ---")
        solver_results = self.solver.solve(data)

        if not solver_results.is_success():
            return RunResult.failed(f"Solver failed with status: {solver_results.status}")

        # Print results
        self._print_results(solver_results)

        # Generate visualizations
        print("\n--- Generating Visualizations ---")
        vis_paths = self._generate_visualizations(solver_results, data, run_dir)

        # Export results
        print("\n--- Exporting Results ---")
        export_paths = self._export_results(solver_results, data, run_dir)

        # Summary
        self._print_summary(run_dir, vis_paths, export_paths, self.output_config)

        return RunResult.succeeded(solver_results, vis_paths, export_paths)

    def _setup_run_directory(self, input_stem: str) -> Path:
        """Create and return a run-specific output directory named after the input file.

        Fix (naming): directory is now '<input_stem>_<timestamp>' instead of a
        generic 'run_<timestamp>', making input-to-output traceability trivial.
        """
        safe_mkdir(self.output_base_dir)
        run_dir = self.output_base_dir / f"{input_stem}_{now_stamp()}"
        safe_mkdir(run_dir)
        return run_dir

    @staticmethod
    def _print_results(results):
        print("\n" + "=" * 70)
        print(f"--- SOLVER RESULTS ({results.status.upper()}) ---")
        print("=" * 70)
        print(f"Makespan       : {results.makespan}")
        print(f"CPU Time (s)   : {results.cpu_time:.6f}")
        print(f"Wall Time (s)  : {results.wall_time:.6f}")
        print(f"Build Time (s) : {results.build_time:.6f}")

    def _generate_visualizations(self, results, data, run_dir):
        timestamp = now_stamp()
        gantt_paths = self.gantt_renderer.render(results, data, run_dir, timestamp)
        resource_path = self.resource_renderer.render(results, data, run_dir, timestamp)
        metrics_path = self.metrics_renderer.render(results, data, run_dir, timestamp)
        return {
            "gantt_pages": gantt_paths,
            "resource_utilization": resource_path,
            "summary_metrics": metrics_path
        }

    def _export_results(self, results, data, run_dir):
        timestamp = now_stamp()
        excel_path = self.excel_exporter.export(results, data, run_dir, timestamp)
        return {"excel": excel_path}

    @staticmethod
    def _print_summary(run_dir, vis_paths, export_paths, output_config):
        print("\n" + "=" * 70)
        print("--- OUTPUT SUMMARY ---")
        print("=" * 70)

        print("\n📈 Flowchart (Network Diagram):")
        print(f"  • {run_dir / output_config.FLOWCHART_NAME}")

        print("\n📊 Gantt Charts (Paged):")
        if vis_paths["gantt_pages"]:
            for path in vis_paths["gantt_pages"]:
                print(f"  • {path}")
        else:
            print("  • (none)")

        print("\n📊 Other Visuals:")
        print(f"  • Resource Utilization : {vis_paths['resource_utilization']}")
        print(f"  • Summary Metrics      : {vis_paths['summary_metrics']}")

        print("\n📄 Data Exports:")
        print(f"  • Excel : {export_paths['excel']}")

        print("\n✓ COMPLETED SUCCESSFULLY")
