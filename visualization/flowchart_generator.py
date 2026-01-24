import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

from models import ProjectData
from config import OutputConfig
from utils import safe_mkdir

logger = logging.getLogger(__name__)


class FlowchartGenerator:
    """Generates a vertical Project Network Diagram (Activity-on-Node)."""

    def __init__(self, config: OutputConfig = None):
        self.config = config or OutputConfig()

    def generate(self, data: ProjectData, output_dir: Path) -> str:
        """
        Generate and save the Project Network Diagram.
        
        Args:
            data: Project structure (activities and precedence).
            output_dir: Directory to save the image.
        """
        safe_mkdir(output_dir)
        
        if not data.activities:
            logger.warning("No activities to plot.")
            return ""

        # 1. Calculate Layout (Levels and Smart Coordinates)
        levels = self._calculate_levels(data)
        coords = self._calculate_coordinates_smart(data, levels)
        
        # 2. Calculate Plot Dimensions
        all_x = [pos[0] for pos in coords.values()]
        all_y = [pos[1] for pos in coords.values()]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Add generous padding
        padding_x = 2.5
        padding_y = 2.0
        
        # Determine figure size
        data_width = max_x - min_x + (2 * padding_x)
        data_height = max_y - min_y + (2 * padding_y)
        
        # Scale figure size (clamped to avoid massive images)
        figsize_w = max(12, min(data_width * 0.6, 30))
        figsize_h = max(10, min(data_height * 0.6, 50))
        
        fig, ax = plt.subplots(figsize=(figsize_w, figsize_h))
        
        # Set limits explicitly
        ax.set_xlim(min_x - padding_x, max_x + padding_x)
        ax.set_ylim(min_y - padding_y, max_y + padding_y)
        ax.axis('off')
        
        # 3. Draw Edges (Arrows)
        for pred_id, succ_id in data.precedence:
            if pred_id in coords and succ_id in coords:
                start = coords[pred_id]
                end = coords[succ_id]
                self._draw_arrow(ax, start, end)
        
        # 4. Draw Nodes
        for activity_id, (x, y) in coords.items():
            if activity_id not in data.activities:
                continue
                
            duration = data.activities[activity_id].duration
            is_dummy = duration == 0
            
            # Label format: ID on top, Duration below
            label = f"{activity_id}\n({duration})"
            
            # Styling
            color = "#E0E0E0" if is_dummy else "#ADD8E6"  # Grey vs LightBlue
            edge_color = "black"
            
            self._draw_node(ax, x, y, label, color, edge_color)

        # 5. Save
        plt.title("Project Precedence Network", fontsize=16, weight="bold", pad=20)
        
        filename = self.config.FLOWCHART_NAME
        filepath = output_dir / filename
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        
        logger.info(f"Network diagram saved to {filepath}")
        print(f"✓ Network diagram saved: {filepath}")
        
        return str(filepath)

    def _calculate_levels(self, data: ProjectData) -> Dict[int, List[str]]:
        """Assign vertical levels based on longest path (Topological layering)."""
        nodes = list(data.activities.keys())
        node_levels = {n: 0 for n in nodes}
        
        # Bellman-Ford-like relaxation
        # This pushes nodes down to the lowest possible level allowed by their parents
        for _ in range(len(nodes)):
            changed = False
            for p, s in data.precedence:
                if p in node_levels and s in node_levels:
                    if node_levels[p] + 1 > node_levels[s]:
                        node_levels[s] = node_levels[p] + 1
                        changed = True
            if not changed:
                break
                
        # Group by level
        level_map = {}
        for node, lvl in node_levels.items():
            if lvl not in level_map:
                level_map[lvl] = []
            level_map[lvl].append(node)
            
        return level_map

    def _calculate_coordinates_smart(self, data: ProjectData, level_map: Dict[int, List[str]]) -> Dict[str, Tuple[float, float]]:
        """
        Calculate (x, y) coords using Barycenter Heuristic to minimize crossings.
        Nodes are placed horizontally based on the average position of their parents.
        """
        coords = {}
        if not level_map:
            return coords
            
        max_level = max(level_map.keys())
        sorted_levels = sorted(level_map.keys())
        
        # Spacing config
        y_spacing = 3.0
        x_spacing = 3.5  # Wider spacing to prevent box overlap
        
        # Pre-process predecessors for fast lookup
        predecessors = {n: [] for n in data.activities.keys()}
        for p, s in data.precedence:
            if s in predecessors:
                predecessors[s].append(p)

        # Iterate level by level
        for lvl in sorted_levels:
            nodes = level_map[lvl]
            
            # --- Sorting Logic ---
            # If we are deeper than level 0, sort nodes by the average X of their parents
            if lvl > 0:
                node_weights = []
                for node in nodes:
                    parents = [p for p in predecessors[node] if p in coords]
                    if parents:
                        # Calculate average X of parents
                        avg_parent_x = statistics.mean([coords[p][0] for p in parents])
                        node_weights.append((avg_parent_x, node))
                    else:
                        # No parents (or parents not processed?), keep original relative order
                        # Use current index as weight to maintain stability
                        node_weights.append((float('inf'), node))
                
                # Sort nodes based on calculated weight, then by ID
                node_weights.sort(key=lambda x: (x[0], x[1]))
                nodes = [n for _, n in node_weights]
            else:
                # Level 0 (Roots): Just sort alphanumerically
                nodes.sort()
            
            # --- Placement Logic ---
            # Y coordinate: Inverted (0 is top)
            y = (max_level - lvl) * y_spacing
            
            # X coordinate: Center the group around 0
            width = len(nodes) * x_spacing
            start_x = -(width / 2) + (x_spacing / 2)
            
            for i, node in enumerate(nodes):
                x = start_x + (i * x_spacing)
                coords[node] = (x, y)
                
        return coords

    def _draw_node(self, ax, x, y, label, facecolor, edgecolor):
        """Draw a single activity node."""
        width = 2.4
        height = 1.4
        
        box = FancyBboxPatch(
            (x - width/2, y - height/2), width, height,
            boxstyle="round,pad=0.1",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=1.5,
            zorder=10
        )
        ax.add_patch(box)
        
        ax.text(x, y, label, ha="center", va="center", fontsize=9, fontweight="bold", zorder=11)

    def _draw_arrow(self, ax, start, end):
        """Draw a clean curved arrow."""
        x1, y1 = start
        x2, y2 = end
        
        # Vertical offset to connect to top/bottom of boxes
        offset = 0.7
        y1 -= offset  # Start from bottom of parent
        y2 += offset  # End at top of child
        
        # Connection style
        # 'arc3,rad=0.0' makes straight lines
        # 'arc3,rad=0.1' makes slight curves. 
        # Using angleB makes arrows enter the child node vertically
        arrow_args = dict(arrowstyle="->", color="#555555", lw=1.5, shrinkA=0, shrinkB=0)
        
        # If nodes are vertically aligned, straight line. Otherwise, curved.
        if abs(x1 - x2) < 0.1:
            conn_style = "arc3,rad=0"
        else:
            # Curve slightly to make it look like a flow diagram
            conn_style = "arc3,rad=-0.1"
            
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(connectionstyle=conn_style, **arrow_args),
            zorder=5
        )