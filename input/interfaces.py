from abc import ABC, abstractmethod
from models import ProjectData

class IDataLoader(ABC):
    """Interface for data loading."""
    
    @abstractmethod
    def load(self, filepath: str) -> ProjectData:
        """Load project data from file."""
        pass