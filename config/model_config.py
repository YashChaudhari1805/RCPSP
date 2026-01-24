from dataclasses import dataclass

@dataclass(frozen=True)
class ModelConfig:
    """Configuration for RCPSP model parameters."""
    
    DUMMY_START: str = "0"
    DUMMY_END: str = "N"
    DEFAULT_TIME_LIMIT: int = 300
    DEFAULT_CAPACITY_MULTIPLIER: int = 2
    MIN_CAPACITY: int = 10
    SOLVER_MSG: int = 0  # 0 = silent, 1 = verbose