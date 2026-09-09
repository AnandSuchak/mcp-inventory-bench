# Package init for trace module
from pathlib import Path
import sys

# Ensure local package takes precedence
_pkg_root = str(Path(__file__).parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)
