from datetime import datetime

def now_stamp() -> str:
    """Generate timestamp string for file naming."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")