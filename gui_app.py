#!/usr/bin/env python3
"""TrailCam Animal ID GUI Application

Entry point for the TrailCam pipeline GUI.
Run this to launch the graphical interface.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gui.main_window import TrailCamApp


def main():
    """Launch the GUI application."""
    app = TrailCamApp()
    app.mainloop()


if __name__ == "__main__":
    main()
