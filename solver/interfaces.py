from abc import ABC, abstractmethod
from models import ProjectData, SolverResults

class ISolver(ABC):
    """Interface for RCPSP solver."""
    
    @abstractmethod
    def solve(self, data: ProjectData) -> SolverResults:
        """Solve RCPSP problem and return results."""
        pass