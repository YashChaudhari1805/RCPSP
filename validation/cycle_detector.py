from typing import Dict, List, Tuple, Set

class CycleDetector:
    """Detects cycles in precedence graphs."""
    
    @staticmethod
    def has_cycle(activities: Dict, precedence: List[Tuple[str, str]]) -> bool:
        """
        Detect if precedence graph contains cycles using DFS.
        
        Args:
            activities: Dictionary of activities
            precedence: List of (predecessor, successor) tuples
            
        Returns:
            True if cycle detected, False otherwise
        """
        # Build adjacency list
        graph = {aid: [] for aid in activities.keys()}
        for pred, succ in precedence:
            if pred in graph:
                graph[pred].append(succ)
        
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in activities.keys():
            if node not in visited:
                if dfs(node):
                    return True
        
        return False