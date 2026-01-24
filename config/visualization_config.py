from dataclasses import dataclass

@dataclass(frozen=True)
class VisualizationConfig:
    """Configuration for visualization parameters."""
    
    TASKS_PER_PAGE: int = 60
    DPI: int = 200
    GANTT_DPI: int = 200
    CHART_DPI: int = 250
    
    FIGURE_WIDTH: int = 16
    MIN_FIGURE_HEIGHT: int = 6
    MAX_FIGURE_HEIGHT: int = 22
    
    BAR_HEIGHT: float = 0.65
    BAR_EDGE_WIDTH: float = 0.8
    
    MAX_TASKS_FOR_LABELS: int = 40
    
    GRID_ALPHA: float = 0.35
    FILL_ALPHA: float = 0.6