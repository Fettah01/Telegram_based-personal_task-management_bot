"""
run.py — Top-level entry point.

Usage:
    python run.py
"""

import sys
import os
import logging

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import main

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("TaskBot application started")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("TaskBot application stopped by user")
    except Exception as e:
        logger.error(f"TaskBot application failed: {e}", exc_info=True)
        raise