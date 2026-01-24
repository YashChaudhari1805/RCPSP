"""
# RCPSP Solver - Refactored Industrial Version

## Project Structure

```
rcpsp_solver/
├── config/              # Configuration modules
│   ├── model_config.py
│   ├── visualization_config.py
│   └── output_config.py
├── models/              # Data models
│   ├── activity.py
│   ├── resource.py
│   ├── project_data.py
│   └── results.py
├── input/               # Data loading
│   ├── interfaces.py
│   ├── excel_parser.py
│   ├── multi_sheet_parser.py
│   └── single_sheet_parser.py
├── validation/          # Data validation
│   ├── interfaces.py
│   ├── data_validator.py
│   └── cycle_detector.py
├── solver/              # MILP solver
│   ├── interfaces.py
│   ├── rcpsp_solver.py
│   └── model_builder.py
├── visualization/       # Chart generation
│   ├── data_transformer.py
│   ├── gantt_renderer.py
│   ├── resource_chart_renderer.py
│   ├── metrics_renderer.py
│   └── flowchart_generator.py
├── export/              # Results export
│   ├── excel_exporter.py
│   ├── text_exporter.py
│   └── json_exporter.py
├── orchestration/       # Main workflow
│   ├── orchestrator.py
│   └── run_result.py
├── utils/               # Utilities
│   ├── file_utils.py
│   ├── time_utils.py
│   └── logging_utils.py
└── cli/                 # Command line interface
    └── main.py

## Usage

```bash
python -m cli.main --excel path/to/project.xlsx
python -m cli.main --excel data.xlsx --output ./results --time_limit 600
```

## Key Improvements

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Type Safety**: Using dataclasses for all data structures
3. **Dependency Injection**: Components receive dependencies via constructor
4. **Interface-Based Design**: Abstract interfaces for testability
5. **Configuration Management**: Centralized configuration with frozen dataclasses
6. **Clean Architecture**: Clear boundaries between layers
7. **No Magic Values**: All constants defined in config
8. **Proper Error Handling**: Structured validation results
9. **Testability**: All components can be mocked and tested
10. **Maintainability**: Small, focused modules that are easy to understand

## Testing Example

```python
from solver import RCPSPSolver
from models import ProjectData, Activity, Resource, ResourceType

# Create mock data
data = ProjectData(
    activities={"A1": Activity("A1", 5)},
    resources={"R1": Resource("R1", 10)},
    precedence=[],
    resource_usage={"A1": {"R1": 2}}
)

# Test solver
solver = RCPSPSolver()
results = solver.solve(data)

assert results.is_optimal()
```
"""