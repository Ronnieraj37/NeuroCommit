#!/usr/bin/env python3
"""
Main entry point for the AI Code Modification Agent.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Import CLI module
from src.cli.main import main
import asyncio

if __name__ == "__main__":
    # Run the CLI
    asyncio.run(main())