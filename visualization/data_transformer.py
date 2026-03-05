from typing import List, Tuple
from models import SolverResults, ProjectData, ScheduledActivity
from config import ModelConfig


class VisualizationDataTransformer:
    """Transforms solver results for visualization."""

    def __init__(self, config: ModelConfig = None):
        # Fix #7: Accept config so dummy IDs come from config, not hardcoded strings
        self.config = config or ModelConfig()

    @property
    def _dummy_ids(self):
        return {self.config.DUMMY_START, self.config.DUMMY_END}

    def get_sorted_activities_for_gantt(
        self,
        results: SolverResults
    ) -> List[Tuple[str, ScheduledActivity]]:
        """Get activities sorted by start time for Gantt chart."""
        activities = results.get_scheduled_activities(exclude_dummies=True)
        return [(a.activity_id, a) for a in activities]

    def calculate_resource_utilization(
        self,
        results: SolverResults,
        data: ProjectData,
        resource_id: str
    ) -> List[float]:
        """Calculate resource utilization over time."""
        makespan = max(int(results.makespan), 1)
        time_points = range(makespan + 1)
        utilization = []

        dummy_ids = self._dummy_ids

        for t in time_points:
            usage = 0
            for activity in results.schedule.values():
                # Fix #7: use config-driven dummy IDs instead of hardcoded "0" and "N"
                if activity.activity_id in dummy_ids:
                    continue
                if activity.start <= t < activity.finish:
                    usage += data.resource_usage.get(
                        activity.activity_id, {}
                    ).get(resource_id, 0)
            utilization.append(usage)

        return utilization
