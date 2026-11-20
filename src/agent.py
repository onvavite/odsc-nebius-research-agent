"""Template entry point (kept working): ``python src/agent.py "question"``.

Delegates to the shared implementation in :mod:`src.research_agent`.
Run from the repository root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.research_agent import main

if __name__ == "__main__":
    sys.exit(main())
