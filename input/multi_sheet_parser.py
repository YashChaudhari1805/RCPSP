import pandas as pd
from typing import Dict, Set, Optional
import logging

from models import ProjectData, Activity, Resource, ResourceType
from config import ModelConfig

logger = logging.getLogger(__name__)


class MultiSheetParser:
    """Parses multi-sheet Excel format."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
    
    def parse(self, filepath: str, sheet_names: Set[str]) -> ProjectData:
        """Parse multi-sheet Excel file."""
        
        # Load sheets
        activities_df = self._load_and_normalize(filepath, "Activities")
        precedence_df = self._load_and_normalize(filepath, "Precedence")
        
        # Resources - flexible sheet name
        if "Resources_Renewable" in sheet_names:
            resources_r_df = self._load_and_normalize(filepath, "Resources_Renewable")
        elif "Resources" in sheet_names:
            resources_r_df = self._load_and_normalize(filepath, "Resources")
        else:
            raise ValueError("Missing 'Resources_Renewable' or 'Resources' sheet")
        
        # Usage - flexible sheet name
        if "Resource_Usage" in sheet_names:
            usage_df = self._load_and_normalize(filepath, "Resource_Usage")
        elif "Usage" in sheet_names:
            usage_df = self._load_and_normalize(filepath, "Usage")
        else:
            raise ValueError("Missing 'Resource_Usage' or 'Usage' sheet")
        
        # Non-renewable (optional)
        resources_nr_df = None
        if "Resources_NonRenewable" in sheet_names:
            resources_nr_df = self._load_and_normalize(filepath, "Resources_NonRenewable")
        
        # Parse components
        activities = self._parse_activities(activities_df)
        resources = self._parse_resources(resources_r_df, resources_nr_df)
        precedence = self._parse_precedence(precedence_df)
        resource_usage = self._parse_usage(usage_df, activities, resources)
        
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
    def _load_and_normalize(filepath: str, sheet_name: str) -> pd.DataFrame:
        """Load sheet and normalize column names."""
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    
    @staticmethod
    def _parse_activities(df: pd.DataFrame) -> Dict[str, Activity]:
        """Parse activities from DataFrame."""
        activities = {}
        for _, row in df.iterrows():
            activity_id = str(row["Activity_ID"]).strip()
            duration = int(row["Duration"])
            activities[activity_id] = Activity(id=activity_id, duration=duration)
        return activities
    
    @staticmethod
    def _parse_resources(
        renewable_df: pd.DataFrame,
        non_renewable_df: Optional[pd.DataFrame]
    ) -> Dict[str, Resource]:
        """Parse resources from DataFrames."""
        resources = {}
        
        # Renewable resources
        for _, row in renewable_df.iterrows():
            resource_id = str(row["Resource_ID"]).strip()
            capacity = int(row["Capacity"])
            resources[resource_id] = Resource(
                id=resource_id,
                capacity=capacity,
                resource_type=ResourceType.RENEWABLE
            )
        
        # Non-renewable resources (optional)
        if non_renewable_df is not None and len(non_renewable_df) > 0:
            for _, row in non_renewable_df.iterrows():
                resource_id = str(row["Resource_ID"]).strip()
                stock = int(row["Total_Stock"])
                resources[resource_id] = Resource(
                    id=resource_id,
                    capacity=stock,
                    resource_type=ResourceType.NON_RENEWABLE
                )
        
        return resources
    
    @staticmethod
    def _parse_precedence(df: pd.DataFrame) -> list:
        """Parse precedence relationships."""
        precedence = []
        for _, row in df.iterrows():
            pred = str(row["Predecessor"]).strip()
            succ = str(row["Successor"]).strip()
            precedence.append((pred, succ))
        return precedence
    
    @staticmethod
    def _parse_usage(
        df: pd.DataFrame,
        activities: Dict[str, Activity],
        resources: Dict[str, Resource]
    ) -> Dict[str, Dict[str, int]]:
        """Parse resource usage."""
        # Initialize usage dict
        usage = {aid: {rid: 0 for rid in resources.keys()} for aid in activities.keys()}
        
        # Fill in actual usage
        for _, row in df.iterrows():
            activity_id = str(row["Activity_ID"]).strip()
            resource_id = str(row["Resource_ID"]).strip()
            amount = int(row["Usage"])
            
            if activity_id in usage and resource_id in resources:
                usage[activity_id][resource_id] = amount
        
        return usage
    
    def _ensure_dummy_activities(
        self,
        activities: Dict[str, Activity],
        resources: Dict[str, Resource],
        usage: Dict[str, Dict[str, int]]
    ) -> tuple:
        """Ensure dummy start and end activities exist."""
        
        # Add dummy activities if missing
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
        
        # Ensure usage entries for dummies
        for dummy in [self.config.DUMMY_START, self.config.DUMMY_END]:
            if dummy not in usage:
                usage[dummy] = {rid: 0 for rid in resources.keys()}
        
        return activities, usage