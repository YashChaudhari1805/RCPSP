import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import logging

from models import SolverResults, ProjectData
from config import VisualizationConfig, OutputConfig, ModelConfig
from utils import now_stamp, safe_mkdir

logger = logging.getLogger(__name__)


class SummaryMetricsRenderer:
    """Renders summary metrics chart."""

    def __init__(
        self,
        viz_config: VisualizationConfig = None,
        output_config: OutputConfig = None,
        model_config: ModelConfig = None
    ):
        self.config = viz_config or VisualizationConfig()
        self.output_config = output_config or OutputConfig()
        # Fix #7: accept model_config to resolve dummy IDs from config
        self.model_config = model_config or ModelConfig()

    @property
    def _dummy_ids(self):
        return {self.model_config.DUMMY_START, self.model_config.DUMMY_END}

    def render(
        self,
        results: SolverResults,
        data: ProjectData,
        output_dir: Path,
        timestamp: str = None
    ) -> str:
        """Render summary metrics chart."""
        timestamp = timestamp or now_stamp()
        safe_mkdir(output_dir)

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

        self._render_makespan_panel(ax1, results)
        self._render_cpu_time_panel(ax2, results)
        self._render_duration_histogram(ax3, data, self._dummy_ids)
        self._render_statistics_table(ax4, results, data, self._dummy_ids)

        plt.tight_layout()

        filename = f"{self.output_config.SUMMARY_METRICS_PREFIX}_{timestamp}.png"
        filepath = output_dir / filename
        plt.savefig(filepath, dpi=self.config.CHART_DPI, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        logger.info(f"Summary metrics chart saved: {filepath}")
        print(f"✓ Summary metrics chart saved: {filepath}")

        return str(filepath)

    @staticmethod
    def _render_makespan_panel(ax, results):
        makespan = int(results.makespan)
        ax.text(0.5, 0.6, f"{makespan}", ha="center", va="center",
                fontsize=60, weight="bold", color="darkblue")
        ax.text(0.5, 0.3, "time units", ha="center", va="center",
                fontsize=18, style="italic")
        ax.text(0.5, 0.9, "Makespan", ha="center", va="top",
                fontsize=14, weight="bold")
        ax.axis("off")

    @staticmethod
    def _render_cpu_time_panel(ax, results):
        ax.text(0.5, 0.6, f"{results.cpu_time:.3f}", ha="center", va="center",
                fontsize=50, weight="bold", color="darkgreen")
        ax.text(0.5, 0.3, "seconds", ha="center", va="center",
                fontsize=18, style="italic")
        ax.text(0.5, 0.9, "CPU Time", ha="center", va="top",
                fontsize=14, weight="bold")
        ax.axis("off")

    @staticmethod
    def _render_duration_histogram(ax, data, dummy_ids):
        # Fix #7: use passed dummy_ids set instead of hardcoded ["0", "N"]
        activities = [a for aid, a in data.activities.items() if aid not in dummy_ids]
        durations = [a.duration for a in activities]

        if durations:
            ax.hist(
                durations,
                bins=min(15, len(set(durations))),
                color="coral",
                edgecolor="black",
                alpha=0.7
            )

        ax.set_title("Activity Duration Distribution", fontsize=11, weight="bold")
        ax.set_xlabel("Duration", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")

    @staticmethod
    def _render_statistics_table(ax, results, data, dummy_ids):
        # Fix #7: use passed dummy_ids set instead of hardcoded ["0", "N"]
        activities = [a for aid, a in data.activities.items() if aid not in dummy_ids]
        durations = [a.duration for a in activities]

        stats_data = [
            ["Total Activities", len(activities)],
            ["Renewable Resources", len(data.get_renewable_resources())],
            ["Non-Renewable Resources", len(data.get_non_renewable_resources())],
            ["Precedence Relations", len(data.precedence)],
            ["Avg Duration", f"{np.mean(durations):.2f}" if durations else "n/a"],
            ["Max Duration", f"{max(durations)}" if durations else "n/a"],
            ["Build Time (s)", f"{results.build_time:.3f}"],
            ["Solve Wall Time (s)", f"{results.wall_time:.3f}"],
        ]

        table = ax.table(
            cellText=stats_data,
            colLabels=["Metric", "Value"],
            cellLoc="left",
            loc="center",
            colWidths=[0.6, 0.4]
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.2)

        for i in range(len(stats_data) + 1):
            for j in range(2):
                cell = table[(i, j)]
                if i == 0:
                    cell.set_facecolor("#4CAF50")
                    cell.set_text_props(weight="bold", color="white")
                else:
                    cell.set_facecolor("#f0f0f0" if i % 2 == 0 else "white")

        ax.axis("off")
        ax.set_title("Project Statistics", fontsize=11, weight="bold", pad=16)
