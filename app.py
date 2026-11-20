"""Cookbook entry point: ``python app.py [question]``.

Runs one research pass and prints the final report prefixed with
``Deep research report:``, then exits zero. ``python app.py --offline-demo``
runs the stubbed demo instead (no API keys, no network).

Required environment variables (see .env.example):
  NEBIUS_API_KEY, TAVILY_API_KEY
Optional: NEBIUS_BASE_URL (default https://api.tokenfactory.nebius.com/v1),
NEBIUS_MODEL (default MiniMaxAI/MiniMax-M3).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.research_agent import main

if __name__ == "__main__":
    sys.exit(main())
