"""
config/settings.py — Centralized configuration loaded from .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Google Gemini
GEMINI_API_KEY: str  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ── Database
DATABASE_PATH: str   = os.getenv("DATABASE_PATH", "data/taskbot.db")

# ── Scheduler
DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Tashkent")
DAILY_SUMMARY_HOUR: int = int(os.getenv("DAILY_SUMMARY_HOUR", "9"))