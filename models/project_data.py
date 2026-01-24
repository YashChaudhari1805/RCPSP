from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class ProjectData:
    """Complete project data for RCPSP."""
    
    activities: Dict[str, 'Activity']
    resources: Dict[str, 'Resource']
    precedence: List[Tuple[str, str]]
    resource_usage: Dict[str, Dict[str, int]]  # {activity_id: {resource_id: usage}}
    
    def get_time_horizon(self) -> List[int]:
        """Calculate time horizon based on total duration."""
        total = sum(a.duration for a in self.activities.values())
        return list(range(total + 1))
    
    def get_renewable_resources(self) -> Dict[str, 'Resource']:
        """Get only renewable resources."""
        return {
            rid: r for rid, r in self.resources.items()
            if r.is_renewable
        }
    
    def get_non_renewable_resources(self) -> Dict[str, 'Resource']:
        """Get only non-renewable resources."""
        return {
            rid: r for rid, r in self.resources.items()
            if r.is_non_renewable
        }
    
    def get_activity_ids(self) -> List[str]:
        """Get sorted list of activity IDs."""
        return sorted(self.activities.keys())
    
    def get_resource_ids(self) -> List[str]:
        """Get sorted list of resource IDs."""
        return sorted(self.resources.keys())