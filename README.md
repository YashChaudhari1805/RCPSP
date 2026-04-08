# RCPSP Solver - Industrial Version

## 📖 Overview
The **RCPSP Solver (Industrial Version)** is a professional-grade Python application designed to solve the **Resource-Constrained Project Scheduling Problem (RCPSP)**. It utilizes Mixed-Integer Linear Programming (MILP) and advanced heuristics to find optimal or near-optimal project schedules that minimize makespan while strictly adhering to precedence constraints and resource availability.

Unlike standard academic implementations, this project is engineered for **industrial scale**, featuring a modular architecture, strong type safety, iterative validation, and paginated visualizations for large projects.

---

## ✨ Key Features
* **Tiered Optimization Strategy**: Automatically selects the best solving method based on project size:
    * **Exact ($n \le 30$ tasks)**: Pure MILP for guaranteed optimality.
    * **Hybrid ($31–120$ tasks)**: Combines a greedy seed with an MILP improvement pass.
    * **Heuristic ($n > 120$ tasks)**: High-speed greedy scheduling for very large projects.
* **Optimized MILP Engine**: Uses a time-indexed $x_{a,t}$ formulation with **CPM-based variable pruning** (ES-bounded), reducing the search space by up to 50% compared to traditional models.
* **Automated Validation**: Includes iterative cycle detection (Kahn’s algorithm) and data schema validation before solving.
* **Advanced Visualization**:
    * **Paginated Gantt Charts**: Splits large schedules across multiple high-resolution images.
    * **Resource Profiles**: Visualizes renewable resource consumption versus capacity over time.
    * **Network Diagrams**: Automatically generates flowcharts of task dependencies.

---

## 🚀 Installation & Execution

### Prerequisites
* Python 3.8+
* Pip (Python package manager)

### Dependencies
```bash
pip install pandas pulp matplotlib openpyxl networkx
```

### Execution (Entry Point)
The project is executed via the CLI module:
```bash
# Basic execution
python -m cli.main --excel ./data/project.xlsx

# Advanced execution with custom settings
python -m cli.main --excel data.xlsx --output ./results --time_limit 600 --tasks_per_page 40
```

---

## 🛠 Project Control Flow

The project follows a strict linear control flow managed by the `RCPSPOrchestrator`.

### 1. Entry Point (`cli/main.py`)
* **Function**: Parses command-line arguments and initializes configurations (`ModelConfig`, `OutputConfig`, `VisualizationConfig`).
* **Action**: Instantiates the `RCPSPOrchestrator` and triggers the `run()` method with the provided Excel path.

### 2. Orchestration Layer (`orchestration/orchestrator.py`)
This is the "brain" of the application that manages the following lifecycle:
1.  **Load**: Uses `ExcelDataLoader` to detect the Excel format (PSPLIB, Multi-sheet, or Single-sheet) and transform it into a standard `ProjectData` object.
2.  **Validate**: Calls `DataValidator` to ensure no circular dependencies exist and resource requests are feasible.
3.  **Pre-Solve Visualization**: Generates a `Program_Flowchart.png` (Network Diagram).
4.  **Solve**: Delegates to `RCPSPSolver` to find the start times for every task.
5.  **Post-Solve Visualization**: Triggers the `GanttChartRenderer`, `ResourceUtilizationRenderer`, and `SummaryMetricsRenderer`.
6.  **Export**: Saves final schedules to Excel and machine-readable JSON formats.

### 3. Solver Logic (`solver/rcpsp_solver.py`)
* **Strategy Selection**: Analyzes task count to choose between Exact, Hybrid, or Heuristic modes.
* **MILP Building**: If using MILP, it calculates CPM bounds (Earliest Start) to prune the time-indexed variables ($x_{a,t}$).
* **Verification Pass**: After the solver finishes, it re-verifies the schedule. If CBC timed out and produced a corrupt or partial result, it automatically discards it and falls back to a guaranteed-feasible Greedy solution.

---

## 📂 File Directory Breakdown

| Directory | Key File | Responsibility |
| :--- | :--- | :--- |
| **`cli/`** | `main.py` | CLI argument parsing and high-level setup. |
| **`config/`** | `model_config.py` | Defines solver timeouts, dummy task IDs, and model constants. |
| **`input/`** | `excel_parser.py` | Auto-detects and parses various Excel formats into data models. |
| **`models/`** | `project_data.py` | Core dataclasses for Activities, Resources, and Projects. |
| **`orchestration/`**| `orchestrator.py` | Executes the sequential workflow from load to export. |
| **`solver/`** | `rcpsp_solver.py` | Contains the MILP formulation and tiered strategy selection. |
| **`validation/`** | `cycle_detector.py`| Implements Kahn's algorithm for precedence integrity. |
| **`visualization/`**| `gantt_renderer.py`| Handles paged Gantt chart rendering using Matplotlib. |

---

## 📊 Outputs
Results are saved in a folder named `<input_filename>_<timestamp>/`:
* **`RCPSP_Results_*.xlsx`**: Final start/finish times for all tasks.
* **`Gantt_Chart_*.png`**: Readable project schedules.
* **`Resource_Profile.png`**: Time-phased resource usage vs. capacity.
* **`Program_Flowchart.png`**: Network dependency diagram.

---

## 📝 License
This project is open-source and available under the **MIT License**.
