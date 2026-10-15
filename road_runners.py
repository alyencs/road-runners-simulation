"""
ROAD RUNNERS - Traffic Flow Simulation (System Dynamics), terminal version.
The impact of vehicle arrival rate and road capacity on traffic flow.

Start the program with:   python road_runners.py
The web version of the same simulation is app.py (streamlit run app.py).
The menu itself is in roadrunners/interface.py.
"""

import sys

for stream in (sys.stdout, sys.stderr):  # make sure all text prints correctly on Windows
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from roadrunners.interface import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
