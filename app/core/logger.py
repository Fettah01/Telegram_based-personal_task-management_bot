"""
app/core/logger.py — Centralized logging configuration.

Sets up both console and file logging with appropriate levels:
  • INFO — user actions (commands, task creation)
  • WARNING — invalid inputs, skipped operations
  • ERROR — database errors, API failures
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging():
    """Initialize logging to console and file (logs/bot.log)."""
    
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "bot.log"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,
        backupCount=5,       
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    
    return root_logger
