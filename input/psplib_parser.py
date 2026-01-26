import pandas as pd
from typing import Dict, List, Tuple, Set
import logging

from models import ProjectData, Activity, Resource, ResourceType
from config import ModelConfig

logger = logging.getLogger(__name__)

class PSPLibParser:
    """Parses PSPLIB Excel format (Project Info, Resource Avail, Requests, Precedence)."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
    
    def parse(self, filepath: str, sheet_names: Set[str]) -> ProjectData:
        """Parse PSPLIB format Excel file."""
        
        # 1. Load DataFrames
        try:
            # We don't strictly need Project Info for the model structure, but we check it exists
            resource_df = self._load_sheet(filepath, "Resource Avail")
            requests_df = self._load_sheet(filepath, "Requests")
            precedence_df = self._load_sheet(filepath, "Precedence")
        except Exception as e:
            raise ValueError(f"Failed to load required PSPLIB sheets: {e}")

        # 2. Parse Resources
        resources = self._parse_resources(resource_df)
        
        # 3. Parse Activities and Usage
        activities, resource_usage = self._parse_requests(requests_df, resources)
        
        # 4. Parse Precedence
        precedence = self._parse_precedence(precedence_df)
        
        # 5. Remap Start/End Nodes
        # PSPLIB usually uses "1" for Start and "N" (e.g. 122) for End.
        # We remap these to config.DUMMY_START (default "0") and config.DUMMY_END 
        # to ensure compatibility with the solver.
        activities, resource_usage, precedence = self._remap_dummies(
            activities, resource_usage, precedence
        )

        return ProjectData(
            activities=activities,
            resources=resources,
            precedence=precedence,
            resource_usage=resource_usage
        )
    
    @staticmethod
    def _load_sheet(filepath: str, sheet_name: str) -> pd.DataFrame:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    @staticmethod
    def _parse_resources(df: pd.DataFrame) -> Dict[str, Resource]:
        resources = {}
        # Columns are like "R1 Available", "R2 Available"
        for col in df.columns:
            if "Available" in col:
                # Extract "R1" from "R1 Available"
                res_id = col.replace("Available", "").strip()
                # Assuming single row for capacity
                capacity = int(df.iloc[0][col])
                resources[res_id] = Resource(
                    id=res_id,
                    capacity=capacity,
                    resource_type=ResourceType.RENEWABLE
                )
        return resources

    @staticmethod
    def _parse_requests(df: pd.DataFrame, resources: Dict[str, Resource]) -> Tuple[Dict, Dict]:
        activities = {}
        usage = {}
        
        for _, row in df.iterrows():
            activity_id = str(row["Job Nr"]).strip()
            duration = int(row["Duration"])
            
            activities[activity_id] = Activity(id=activity_id, duration=duration)
            
            # Parse usage for this activity
            act_usage = {}
            for res_id in resources.keys():
                # Check if column exists (e.g. "R1")
                if res_id in df.columns:
                    act_usage[res_id] = int(row[res_id])
                else:
                    act_usage[res_id] = 0
            usage[activity_id] = act_usage
            
        return activities, usage

    @staticmethod
    def _parse_precedence(df: pd.DataFrame) -> List[Tuple[str, str]]:
        precedence = []
        for _, row in df.iterrows():
            pred_id = str(row["Job Nr"]).strip()
            
            # Successors col is like "2, 3, 4" or just a number
            succ_str = str(row["Successors"]).strip()
            if succ_str and succ_str.lower() != "nan":
                # Handle comma separated list
                succ_ids = [s.strip() for s in succ_str.replace('"', '').split(',')]
                for succ_id in succ_ids:
                    if succ_id:
                        precedence.append((pred_id, succ_id))
        return precedence

    def _remap_dummies(self, activities, usage, precedence):
        """Remaps the file's Start/End IDs to the Config's Start/End IDs."""
        sorted_ids = sorted(activities.keys(), key=lambda x: int(x) if x.isdigit() else x)
        
        original_start = sorted_ids[0]  # Usually "1"
        original_end = sorted_ids[-1]   # Usually "122" or similar
        
        # If the file IDs are already "0" and "N", no need to remap (simple check)
        if original_start == self.config.DUMMY_START and original_end == self.config.DUMMY_END:
            return activities, usage, precedence

        mapping = {
            original_start: self.config.DUMMY_START,
            original_end: self.config.DUMMY_END
        }
        
        logger.info(f"Remapping PSPLIB nodes: {original_start}->{self.config.DUMMY_START}, {original_end}->{self.config.DUMMY_END}")

        # Remap Activities
        new_activities = {}
        for aid, act in activities.items():
            new_id = mapping.get(aid, aid)
            act.id = new_id # Update object ID
            new_activities[new_id] = act
            
        # Remap Usage
        new_usage = {}
        for aid, u in usage.items():
            new_id = mapping.get(aid, aid)
            new_usage[new_id] = u
            
        # Remap Precedence
        new_precedence = []
        for pred, succ in precedence:
            new_pred = mapping.get(pred, pred)
            new_succ = mapping.get(succ, succ)
            new_precedence.append((new_pred, new_succ))
            
        return new_activities, new_usage, new_precedence