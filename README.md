Based on the code structure and logic contained in the uploaded files, here is a comprehensive and detailed `README.md` for the project.

---

# RCPSP Solver - Industrial Version

## 📖 Overview

The **RCPSP Solver (Industrial Version)** is a robust, modular Python application designed to solve the **Resource-Constrained Project Scheduling Problem (RCPSP)**. It utilizes Mixed-Integer Linear Programming (MILP) to find optimal project schedules that minimize makespan while strictly adhering to precedence constraints and limited resource availability.

Unlike academic scripts, this project is engineered for **industrial use**, featuring separation of concerns, strong type safety, extensive validation, paginated visualizations for large projects, and support for multiple input formats.

## ✨ Key Features

* **Optimization Engine**: Uses `PuLP` with the CBC solver to guarantee optimal or near-optimal solutions based on a configurable time limit.
* **Flexible Inputs**: Automatically detects and parses three different Excel formats: PSPLIB (academic standard), Multi-sheet (Activities/Precedence), and Single-sheet.
* **Advanced Visualization**:
* **Paginated Gantt Charts**: Automatically splits large schedules across multiple images for readability.
* **Network Diagrams**: Generates flowcharts of the project network.
* **Resource Utilization**: Visualizes resource consumption over time.


* **Robust Architecture**: Implements Clean Architecture principles with strict separation between Input, Model, Solver, and Visualization layers.
* **Validation**: Includes cycle detection and data schema validation before attempting to solve.

## 📂 Project Structure

The codebase is organized into focused modules to ensure maintainability and testability:

```text
rcpsp_solver/
├── cli/                 # Command Line Interface entry point
├── config/              # Centralized configuration (Models, Output, Viz)
├── export/              # Exporters for Excel, JSON, and Text formats
├── input/               # Data loaders (Excel, PSPLIB parsers)
├── models/              # Dataclasses (Activity, Resource, ProjectData)
├── orchestration/       # Main workflow controller (Load -> Solve -> Viz)
├── solver/              # MILP implementation using PuLP
├── utils/               # Logging, file handling, and time utilities
├── validation/          # Cycle detection and data integrity checks
└── visualization/       # Matplotlib-based renderers (Gantt, Charts)

```

## 🚀 Installation

### Prerequisites

* Python 3.8 or higher
* pip (Python package manager)

### Dependencies

Install the required libraries:

```bash
pip install pandas pulp matplotlib openpyxl networkx

```

*Note: The COIN-OR CBC solver is usually included with PuLP, but on some Linux distributions, you may need to install it separately (e.g., `sudo apt-get install coinor-cbc`).*

## 💻 Usage

The project is executed via the Command Line Interface (CLI).

### Basic Command

Run the solver on an Excel file using default settings:

```bash
python -m cli.main --excel ./data/project_data.xlsx

```

### Advanced Usage

Customize the output location, solver time limit, and visualization settings:

```bash
python -m cli.main \
    --excel ./data/large_project.xlsx \
    --output ./my_results \
    --time_limit 600 \
    --tasks_per_page 50

```

### CLI Arguments

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `--excel` | string | **Yes** | N/A | Path to the input Excel file (.xlsx). |
| `--output` | string | No | `./output` | Base directory where results and charts will be saved. |
| `--time_limit` | int | No | `300` | Solver timeout in seconds. If the limit is reached, the best solution found so far is returned. |
| `--tasks_per_page` | int | No | `60` | Number of tasks to display per Gantt chart image. Useful for keeping charts readable. |

## 📊 Input Data Formats

The solver automatically detects the format based on the Excel sheet names.

### 1. PSPLIB Format (Recommended)

Based on the standard academic format. Requires the following sheets:

* **Project Info**: General project metadata.
* **Resource Avail**: Available capacity for each resource.
* **Requests**: Resource consumption per activity.
* **Precedence**: Successor/Predecessor relationships.

### 2. Multi-Sheet Format

A simplified relational format.

* **Activities**: Columns for `ActivityID`, `Duration`, and Resource demands (e.g., `Res1`, `Res2`).
* **Precedence**: Columns for `Predecessor` and `Successor`.

### 3. Single-Sheet Format

All data in one sheet. Expects columns for ID, Duration, Predecessors (comma-separated), and Resources.

## 📁 Outputs

For every execution, a timestamped run directory is created (e.g., `output/run_20231027_103000/`) containing:

1. **`RCPSP_Results_*.xlsx`**: Complete schedule, start/finish times, and metrics in Excel format.
2. **`Gantt_Chart_*_P1.png`**: High-resolution Gantt charts (split into P1, P2... if the project is large).
3. **`Resource_Profile.png`**: Graphs showing resource usage vs. capacity over time.
4. **`Program_Flowchart.png`**: Visual network diagram of task dependencies.
5. **`Summary_Metrics.png`**: Key performance indicators (Makespan, CPU time).
6. **`RCPSP_Summary.json`**: Machine-readable results for integration with other tools.

## ⚙️ Configuration

While CLI arguments control runtime parameters, internal logic is managed via configuration classes in the `config/` directory:

* **`model_config.py`**: Constants for the MILP model (Big-M, dummy activity names).
* **`visualization_config.py`**: DPI settings, bar heights, colors, and chart dimensions.
* **`output_config.py`**: Naming conventions for output files.

## 🛠 Architecture & Workflow

The `RCPSPOrchestrator` manages the end-to-end process:

1. **Load**: `ExcelDataLoader` identifies the schema and converts Excel data into standard `ProjectData` objects.
2. **Validate**: `DataValidator` checks for circular dependencies (cycles) and impossible resource requests.
3. **Visualize (Pre)**: `FlowchartGenerator` draws the project network.
4. **Solve**: `RCPSPSolver` builds a MILP model:
* *Variables*: Binary variables  (task  starts at time ).
* *Constraints*: Precedence enforcement and Resource capacity limits.
* *Objective*: Minimize  (Makespan).


5. **Visualize (Post)**: `GanttRenderer` and `MetricsRenderer` generate charts based on the optimal schedule.
6. **Export**: Results are serialized to Excel and JSON.

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/NewHeuristic`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## 📝 License

This project is open-source and available under the MIT License.