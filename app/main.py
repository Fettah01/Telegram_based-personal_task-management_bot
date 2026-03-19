"""
app/main.py — Application entry point (called from run.py).
"""

import logging
import os
import traceback

from telegram import Update
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config.settings import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
import app.core.database as db
from app.bot.reminders import create_scheduler
from app.bot.handlers import (
    # Simple commands
    cmd_start,
    cmd_help,
    cmd_mytasks,
    cmd_mytask,
    cmd_done,
    cmd_deletetask,
    cmd_stats,
    cmd_settimezone,
    unknown_command,
    # Inline button callbacks
    callback_task_view,
    callback_task_done,
    callback_task_delete,
    callback_task_delete_confirm,
    # Conversation handler builders
    build_addtask_handler,
    build_addtask_ai_handler,
    build_edittask_handler,
)

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Bot menu commands (shown in Telegram UI)
# ─────────────────────────────────────────────

BOT_COMMANDS = [
    BotCommand("start",        "Register and get started"),
    BotCommand("help",         "Show all commands"),
    BotCommand("addtask",      "Create task step-by-step"),
    BotCommand("addtask_ai",   "Create task with AI (natural language)"),
    BotCommand("mytasks",      "List your tasks"),
    BotCommand("mytask",       "View a single task: /mytask <id>"),
    BotCommand("done",         "Mark task as done: /done <id>"),
    BotCommand("edittask",     "Edit a task: /edittask <id>"),
    BotCommand("deletetask",   "Delete a task: /deletetask <id>"),
    BotCommand("stats",        "Your productivity stats"),
    BotCommand("settimezone",  "Set your timezone"),
]


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  Global error handler
# ─────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all exceptions and notify the user with a friendly message."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Try to tell the user something went wrong
    if isinstance(update, Update):
        msg = (
            "⚠️ Something went wrong while processing your request\\.\n"
            "Please try again or use /help\\."
        )
        try:
            if update.callback_query:
                await update.callback_query.answer("Something went wrong. Please try again.", show_alert=True)
            elif update.effective_message:
                await update.effective_message.reply_text(msg, parse_mode="MarkdownV2")
        except Exception:
            pass  # Don't crash the error handler itself


async def post_init(application: Application) -> None:
    """Runs inside the event loop after the application is initialised."""
    await db.init_db()
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Database initialised and bot commands registered.")

    # Start scheduler here — event loop is guaranteed to be running at this point
    scheduler = create_scheduler(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Reminder scheduler started.")


async def post_shutdown(application: Application) -> None:
    """Runs when the bot is shutting down — stop the scheduler cleanly."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped.")


def main():
    token = TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    gemini_key = GEMINI_API_KEY
    if not gemini_key:
        logger.warning("GEMINI_API_KEY not set — AI features will fail at runtime.")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Conversation handlers (must be registered first)
    app.add_handler(build_addtask_handler())
    app.add_handler(build_addtask_ai_handler())
    app.add_handler(build_edittask_handler())

    # ── Simple command handlers
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("mytasks",      cmd_mytasks))
    app.add_handler(CommandHandler("mytask",       cmd_mytask))
    app.add_handler(CommandHandler("done",         cmd_done))
    app.add_handler(CommandHandler("deletetask",   cmd_deletetask))
    app.add_handler(CommandHandler("stats",        cmd_stats))
    app.add_handler(CommandHandler("settimezone",  cmd_settimezone))

    # ── Inline button callbacks
    app.add_handler(CallbackQueryHandler(callback_task_view,          pattern=r"^task_view_\d+$"))
    app.add_handler(CallbackQueryHandler(callback_task_done,          pattern=r"^task_done_\d+$"))
    app.add_handler(CallbackQueryHandler(callback_task_delete,        pattern=r"^task_del_\d+$"))
    app.add_handler(CallbackQueryHandler(callback_task_delete_confirm,pattern=r"^task_del_confirm_\d+$"))

    # ── Fallback for unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # ── Global error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()