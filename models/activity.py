from dataclasses import dataclass

@dataclass
class Activity:
    """Represents a project activity."""
    
    id: str
    duration: int
    
    def __post_init__(self):
        if self.duration < 0:
            raise ValueError(f"Activity {self.id} has negative duration: {self.duration}")