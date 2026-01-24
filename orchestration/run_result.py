from dataclasses import dataclass
from typing import Dict, List, Optional

from models import SolverResults


@dataclass
class RunResult:
    """Result of a complete RCPSP run."""
    
    success: bool
    message: str
    solver_results: Optional[SolverResults] = None
    visualization_paths: Optional[Dict[str, any]] = None
    export_paths: Optional[Dict[str, str]] = None
    
    @classmethod
    def failed(cls, message: str) -> 'RunResult':
        """Create a failed result."""
        return cls(success=False, message=message)
    
    @classmethod
    def succeeded(
        cls,
        solver_results: SolverResults,
        visualization_paths: Dict,
        export_paths: Dict
    ) -> 'RunResult':
        """Create a successful result."""
        return cls(
            success=True,
            message="Optimization completed successfully",
            solver_results=solver_results,
            visualization_paths=visualization_paths,
            export_paths=export_paths
        )