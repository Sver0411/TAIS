"""Independent TAIS research package; upstream modules are imported unchanged."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'vendor/AdaptiveSense'))
