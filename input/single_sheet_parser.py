import pandas as pd
from typing import Dict
import logging

from models import ProjectData, Activity, Resource, ResourceType
from config import ModelConfig

logger = logging.getLogger(__name__)


class SingleSheetParser:
    """Parses single-sheet Excel format."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
    
    def parse(self, filepath: str) -> ProjectData:
        """Parse single-sheet Excel file."""
        
        df = pd.read_excel(filepath, sheet_name=0)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Validate required columns
        required = {"ActivityID", "Duration"}
        if not required.issubset(set(df.columns)):
            raise ValueError(
                f"Single-sheet format requires columns {required}. Found: {list(df.columns)}"
            )
        
        activities = self._parse_activities(df)
        resources, resource_usage = self._parse_resources_and_usage(df, activities)
        precedence = self._parse_precedence(df, activities)
        
        # Ensure dummy activities
        activities, resource_usage = self._ensure_dummy_activities(
            activities, resources, resource_usage
        )
        
        return ProjectData(
            activities=activities,
            resources=resources,
            precedence=precedence,
            resource_usage=resource_usage
        )
    
    @staticmethod
    def _parse_activities(df: pd.DataFrame) -> Dict[str, Activity]:
        """Parse activities from DataFrame."""
        activities = {}
        for _, row in df.iterrows():
            if pd.notna(row.get("ActivityID")):
                activity_id = str(row["ActivityID"]).strip()
                if activity_id:
                    duration = int(row["Duration"]) if pd.notna(row.get("Duration")) else 0
                    activities[activity_id] = Activity(id=activity_id, duration=duration)
        return activities
    
    def _parse_resources_and_usage(
        self,
        df: pd.DataFrame,
        activities: Dict[str, Activity]
    ) -> tuple:
        """Parse resources and usage from 'Resource Usage (R1, R2)' column."""
        
        resource_set = set()
        usage = {aid: {} for aid in activities.keys()}
        
        if "Resource Usage (R1, R2)" in df.columns:
            for _, row in df.iterrows():
                activity_id = str(row.get("ActivityID")).strip() if pd.notna(row.get("ActivityID")) else None
                if not activity_id or activity_id not in activities:
                    continue
                
                usage_str = str(row.get("Resource Usage (R1, R2)", "")).strip()
                if usage_str and usage_str not in ["-", "nan"]:
                    # Parse "R1:2, R2:1"
                    parts = [p.strip() for p in usage_str.split(",")]
                    for part in parts:
                        if ":" in part:
                            resource_id, amount = part.split(":")
                            resource_id = resource_id.strip()
                            amount = int(amount.strip())
                            resource_set.add(resource_id)
                            usage[activity_id][resource_id] = amount
        
        # Create resources with estimated capacities
        resources = {}
        for rid in sorted(resource_set):
            max_usage = max(
                usage[aid].get(rid, 0) for aid in activities.keys()
            ) if activities else 0
            capacity = max(max_usage * self.config.DEFAULT_CAPACITY_MULTIPLIER, self.config.MIN_CAPACITY)
            resources[rid] = Resource(
                id=rid,
                capacity=capacity,
                resource_type=ResourceType.RENEWABLE
            )
        
        # Fill in zero usage for all activities
        for aid in activities.keys():
            for rid in resources.keys():
                if rid not in usage[aid]:
                    usage[aid][rid] = 0
        
        return resources, usage
    
    @staticmethod
    def _parse_precedence(df: pd.DataFrame, activities: Dict[str, Activity]) -> list:
        """Parse precedence from 'Predecessors' column."""
        precedence = []
        
        if "Predecessors" in df.columns:
            for _, row in df.iterrows():
                activity_id = str(row.get("ActivityID")).strip() if pd.notna(row.get("ActivityID")) else None
                if not activity_id or activity_id not in activities:
                    continue
                
                preds_str = str(row.get("Predecessors", "")).strip()
                if preds_str and preds_str not in ["-", "nan"]:
                    for pred in [p.strip() for p in preds_str.split(",")]:
                        if pred in activities:
                            precedence.append((pred, activity_id))
        
        return precedence
    
    def _ensure_dummy_activities(
        self,
        activities: Dict[str, Activity],
        resources: Dict[str, Resource],
        usage: Dict[str, Dict[str, int]]
    ) -> tuple:
        """Ensure dummy start and end activities exist."""
        
        if self.config.DUMMY_START not in activities:
            activities[self.config.DUMMY_START] = Activity(
                id=self.config.DUMMY_START,
                duration=0
            )
        
        if self.config.DUMMY_END not in activities:
            activities[self.config.DUMMY_END] = Activity(
                id=self.config.DUMMY_END,
                duration=0
            )
        
        for dummy in [self.config.DUMMY_START, self.config.DUMMY_END]:
            if dummy not in usage:
                usage[dummy] = {rid: 0 for rid in resources.keys()}
        
        return activities, usage