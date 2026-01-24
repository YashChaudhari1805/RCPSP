from abc import ABC, abstractmethod
from models import ProjectData, ValidationResult

class IDataValidator(ABC):
    """Interface for data validation."""
    
    @abstractmethod
    def validate(self, data: ProjectData) -> ValidationResult:
        """Validate project data."""
        pass