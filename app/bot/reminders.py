"""
app/bot/reminders.py — APScheduler-powered reminder system.

Jobs:
  1. check_deadlines     — Every 10 min: fire alerts for upcoming deadlines
  2. daily_summary       — Every day at 09:00 (user timezone): productivity digest
"""

import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode

import app.core.database as db
import app.services.ai_service as ai
from app.core.formatters import escape_md, format_stats, PRIORITY_EMOJI, STATUS_EMOJI
from config.settings import DAILY_SUMMARY_HOUR

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Deadline reminder
# ─────────────────────────────────────────────

async def check_deadlines(bot: Bot):
    """Send reminders for tasks due within the next 30 minutes."""
    try:
        due_tasks = await db.get_due_tasks()
        for task in due_tasks:
            try:
                title     = escape_md(task["title"])
                deadline  = task.get("deadline", "")
                try:
                    dt_str = datetime.fromisoformat(deadline).strftime("%d %b %Y, %H:%M")
                except Exception:
                    dt_str = deadline

                await bot.send_message(
                    chat_id=task["user_id"],
                    text=(
                        f"⏰ *Deadline Reminder\\!*\n\n"
                        f"📝 *{title}*\n"
                        f"🕐 Due: `{escape_md(dt_str)}`\n"
                        f"⚡ Priority: {task['priority'].capitalize()}\n\n"
                        f"_Use /done {task['id']} to mark it complete\\._"
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await db.mark_task_reminded(task["id"])
                logger.info(f"Sent deadline reminder: task #{task['id']} → user {task['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send reminder for task #{task.get('id')}: {e}")
    except Exception as e:
        logger.error(f"check_deadlines error: {e}")


# ─────────────────────────────────────────────
#  Daily summary
# ─────────────────────────────────────────────

async def send_daily_summaries(bot: Bot):
    """Send a productivity digest to every user at their 9 AM local time."""
    current_utc_hour = datetime.utcnow().hour

    try:
        users = await db.get_all_users()
        for user in users:
            try:
                # Convert user's 9 AM to UTC and check if it matches now
                tz_name  = user.get("timezone", "UTC")
                try:
                    tz        = pytz.timezone(tz_name)
                    now_local = datetime.now(tz)
                    if now_local.hour != DAILY_SUMMARY_HOUR:
                        continue
                except Exception:
                    if current_utc_hour != DAILY_SUMMARY_HOUR:
                        continue

                tasks = await db.get_user_tasks(user["user_id"], status="pending")
                stats = await db.get_user_stats(user["user_id"])

                if stats["total"] == 0:
                    continue  # skip users with no tasks

                motivation = await ai.generate_daily_motivation(stats)

                # Build task list snippet (top 5 by priority)
                task_lines = []
                for t in tasks[:5]:
                    p = PRIORITY_EMOJI.get(t["priority"], "⚪")
                    task_lines.append(f"  {p} `#{t['id']}` {escape_md(t['title'][:35])}")

                tasks_block = "\n".join(task_lines) if task_lines else "  _None pending_"

                name = escape_md(user.get("full_name") or "there")
                await bot.send_message(
                    chat_id=user["user_id"],
                    text=(
                        f"☀️ *Good morning, {name}\\!*\n\n"
                        f"📊 *Today's Overview*\n"
                        f"✅ Done: `{stats['done']}` \\| ⏳ Pending: `{stats['pending']}` \\| ⚠️ Overdue: `{stats['overdue']}`\n\n"
                        f"🔝 *Top Pending Tasks:*\n{tasks_block}\n\n"
                        f"💬 _{escape_md(motivation)}_\n\n"
                        f"_Use /mytasks to see everything\\._"
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                logger.info(f"Sent daily summary to user {user['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send daily summary to {user.get('user_id')}: {e}")
    except Exception as e:
        logger.error(f"send_daily_summaries error: {e}")


# ─────────────────────────────────────────────
#  Scheduler setup
# ─────────────────────────────────────────────

def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Build and return the scheduler. Caller must call .start() inside a running event loop."""
    scheduler = AsyncIOScheduler(timezone=pytz.utc)

    # Check deadlines every 10 minutes
    scheduler.add_job(
        check_deadlines,
        trigger="interval",
        minutes=10,
        args=[bot],
        id="check_deadlines",
        replace_existing=True,
    )

    # Daily summary — check every hour (the function self-filters by user timezone)
    scheduler.add_job(
        send_daily_summaries,
        trigger="cron",
        minute=0,       # top of every hour
        args=[bot],
        id="daily_summary",
        replace_existing=True,
    )

    return scheduler
