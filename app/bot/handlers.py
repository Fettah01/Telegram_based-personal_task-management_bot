"""
app/bot/handlers.py — All Telegram command & callback handlers.

Commands:
    /start         — Register user + welcome
    /help          — Command reference
    /addtask       — Manual step-by-step task creation
    /addtask_ai    — Natural language AI task creation
    /mytasks       — List tasks with clickable ID buttons
    /mytask <id>   — View a single task with action buttons
    /edittask      — Edit a task
    /deletetask    — Delete a task
    /done          — Mark task as done
    /stats         — Productivity statistics
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pytz

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode

import app.core.database as db
import app.services.ai_service as ai
from app.core.formatters import (
    format_task_card,
    format_task_list,
    format_stats,
    fmt_priority,
    fmt_status,
    fmt_category,
    escape_md,
    PRIORITY_EMOJI,
    STATUS_EMOJI,
    CATEGORY_EMOJI,
)

logger = logging.getLogger(__name__)


# =============================================================================
#  DEADLINE PARSER
# =============================================================================

def parse_deadline(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a deadline from many input formats.
    Returns (iso_string, None) on success, or (None, error_hint) on failure.
    """
    text = text.strip().lower()
    now  = datetime.utcnow()

    # Natural language shortcuts
    if text == "today":
        return now.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
    if text == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
    if text == "next week":
        return (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    # "in X days/hours/weeks"
    m = re.match(r"in\s+(\d+)\s+(hour|hours|day|days|week|weeks)", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if "hour" in unit:
            return (now + timedelta(hours=n)).replace(second=0, microsecond=0).isoformat(), None
        if "day" in unit:
            return (now + timedelta(days=n)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None
        if "week" in unit:
            return (now + timedelta(weeks=n)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    # "next <weekday>" or bare weekday name
    weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    for i, day in enumerate(weekdays):
        if text.startswith(f"next {day}") or text == day:
            days_ahead = (i - now.weekday() + 7) % 7 or 7
            return (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(), None

    # Structured date/time formats
    formats = [
        "%Y-%m-%d %H:%M",    # 2026-03-15 14:30
        "%Y-%m-%d %H:%M:%S", # 2026-03-15 14:30:00
        "%Y-%m-%dT%H:%M:%S", # 2026-03-15T14:30:00  (ISO from AI)
        "%Y-%m-%dT%H:%M",    # 2026-03-15T14:30
        "%Y-%m-%d",          # 2026-03-15
        "%d/%m/%Y %H:%M",    # 15/03/2026 14:30
        "%d/%m/%Y",          # 15/03/2026
        "%d.%m.%Y %H:%M",    # 15.03.2026 14:30
        "%d.%m.%Y",          # 15.03.2026
        "%d-%m-%Y %H:%M",    # 15-03-2026 14:30
        "%d-%m-%Y",          # 15-03-2026
        "%m/%d/%Y %H:%M",    # 03/15/2026 14:30
        "%m/%d/%Y",          # 03/15/2026
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(text.strip(), fmt)
            if "%H" not in fmt:
                dt = dt.replace(hour=9, minute=0, second=0)
            return dt.isoformat(), None
        except ValueError:
            continue

    return None, (
        "I couldn't understand that date\\. Try one of these formats:\n"
        "`2026-03-15 14:30` or `15/03/2026 14:30`\n"
        "or type: `tomorrow`, `today`, `next monday`, `in 3 days`"
    )

# =============================================================================
#  INLINE KEYBOARD BUILDERS
# =============================================================================

def task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Done / Edit / Delete buttons shown under every task card."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Done",   callback_data=f"task_done_{task_id}"),
        InlineKeyboardButton("✏️ Edit",   callback_data=f"task_edit_{task_id}"),
        InlineKeyboardButton("🗑️ Delete", callback_data=f"task_del_{task_id}"),
    ]])


def task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """One button per task showing ID + truncated title."""
    rows = []
    for t in tasks:
        p = PRIORITY_EMOJI.get(t["priority"], "⚪")
        s = STATUS_EMOJI.get(t["status"], "❓")
        label = f"{s}{p} #{t['id']}  {t['title'][:32]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"task_view_{t['id']}")])
    return InlineKeyboardMarkup(rows)


def delete_confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ Yes, Delete", callback_data=f"task_del_confirm_{task_id}"),
        InlineKeyboardButton("↩️ Cancel",       callback_data=f"task_view_{task_id}"),
    ]])


# =============================================================================
#  CONVERSATION STATES
# =============================================================================

(AT_TITLE, AT_DESCRIPTION, AT_CATEGORY, AT_PRIORITY, AT_DEADLINE) = range(5)
(AI_INPUT,) = range(5, 6)
(EDIT_ID, EDIT_FIELD, EDIT_VALUE) = range(6, 9)

EDIT_FIELDS = ["Title", "Description", "Category", "Priority", "Deadline", "Status"]


# =============================================================================
#  REPLY KEYBOARD HELPERS
# =============================================================================

def category_keyboard():
    return ReplyKeyboardMarkup(
        [["💼 Work", "📚 Study"], ["🏠 Personal", "❤️ Health"], ["💰 Finance", "📋 General"]],
        one_time_keyboard=True, resize_keyboard=True,
    )

def priority_keyboard():
    return ReplyKeyboardMarkup(
        [["🔴 High", "🟡 Medium", "🟢 Low"]],
        one_time_keyboard=True, resize_keyboard=True,
    )

def skip_keyboard():
    return ReplyKeyboardMarkup([["⏭ Skip"]], one_time_keyboard=True, resize_keyboard=True)

def _parse_category(text: str) -> str:
    clean = (text.lower()
             .replace("💼 ", "").replace("📚 ", "").replace("🏠 ", "")
             .replace("❤️ ", "").replace("💰 ", "").replace("📋 ", "").strip())
    return clean if clean in {"work","study","personal","health","finance","general"} else "general"

def _parse_priority(text: str) -> str:
    clean = text.lower().replace("🔴 ","").replace("🟡 ","").replace("🟢 ","").strip()
    return clean if clean in {"high","medium","low"} else "medium"


# =============================================================================
#  MENU KEYBOARDS
# =============================================================================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Full bot menu as inline buttons — shown on /start and /help."""
    return InlineKeyboardMarkup([
        # ── Task creation
        [
            InlineKeyboardButton("➕ Add Task",        callback_data="menu_addtask"),
            InlineKeyboardButton("🤖 Add with AI",     callback_data="menu_addtask_ai"),
        ],
        # ── Task browsing
        [
            InlineKeyboardButton("📋 My Tasks",        callback_data="menu_mytasks"),
            InlineKeyboardButton("📊 Stats",           callback_data="menu_stats"),
        ],
        # ── Filters
        [
            InlineKeyboardButton("⏳ Pending",         callback_data="menu_filter_pending"),
            InlineKeyboardButton("✅ Done",            callback_data="menu_filter_done"),
            InlineKeyboardButton("🔄 In Progress",     callback_data="menu_filter_progress"),
        ],
        # ── Categories
        [
            InlineKeyboardButton("💼 Work",            callback_data="menu_filter_work"),
            InlineKeyboardButton("📚 Study",           callback_data="menu_filter_study"),
            InlineKeyboardButton("🏠 Personal",        callback_data="menu_filter_personal"),
        ],
        [
            InlineKeyboardButton("❤️ Health",          callback_data="menu_filter_health"),
            InlineKeyboardButton("💰 Finance",         callback_data="menu_filter_finance"),
        ],
        # ── Settings
        [
            InlineKeyboardButton("⚙️ Set Timezone",    callback_data="menu_settimezone"),
        ],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to return to main menu."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_main"),
    ]])


def task_action_with_menu_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Task action buttons + back to menu."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Done",   callback_data=f"task_done_{task_id}"),
            InlineKeyboardButton("✏️ Edit",   callback_data=f"task_edit_{task_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"task_del_{task_id}"),
        ],
        [
            InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_main"),
        ],
    ])


# =============================================================================
#  /start
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.full_name or user.first_name or "User")
    name = escape_md(user.first_name or "there")
    logger.info(f"User @{user.username} (ID: {user.id}) started the bot")
    await update.message.reply_text(
        f"👋 *Welcome, {name}\\!*\n\n"
        "I'm your *AI\\-powered Task Manager*\\.\n"
        "Use the buttons below to get started\\:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )


# =============================================================================
#  /help
# =============================================================================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User (ID: {user_id}) requested help")
    await update.message.reply_text(
        "📖 *Help \\& Menu*\n\n"
        "Tap a button to act, or use commands directly\\:\n\n"
        "*Creating*  ➕ Add Task \\| 🤖 Add with AI\n"
        "*Viewing*   📋 My Tasks \\| 📊 Stats\n"
        "*Filters*   ⏳ Pending \\| ✅ Done \\| 🔄 In Progress\n"
        "*Category*  💼 Work \\| 📚 Study \\| 🏠 Personal \\| ❤️ Health \\| 💰 Finance\n"
        "*Settings*  ⚙️ Set Timezone\n\n"
        "💡 _Tip: tap any task in My Tasks to see full details and Done \\/ Edit \\/ Delete buttons_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu_keyboard(),
    )


# =============================================================================
#  MENU BUTTON CALLBACKS
# =============================================================================

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all main_menu_keyboard button presses."""
    query  = update.callback_query
    action = query.data  # e.g. "menu_addtask", "menu_filter_pending"
    await query.answer()

    # ── Back to main menu
    if action == "menu_main":
        await query.message.reply_text(
            "🏠 *Main Menu*\n\nChoose what you'd like to do:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu_keyboard(),
        )
        return

    # ── Task creation buttons — launch the conversation via a fake command message
    if action == "menu_addtask":
        await query.message.reply_text(
            "📝 *New Task — Step 1/5*\n\nWhat's the task title?",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("new_task", None)
        context.user_data["_conv_start"] = "addtask"
        return AT_TITLE

    if action == "menu_addtask_ai":
        await query.message.reply_text(
            "🤖 *AI Task Creation*\n\n"
            "Describe your task in plain English\\. For example:\n"
            "• _'Submit the quarterly report by Friday, urgent'_\n"
            "• _'Buy groceries tomorrow at 5 PM'_\n"
            "• _'Study for math exam next Monday morning'_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )
        return AI_INPUT

    # ── My Tasks (all)
    if action == "menu_mytasks":
        context.args = []
        await _show_task_list(query.message, update.effective_user.id, status=None, category=None)
        return

    # ── Stats
    if action == "menu_stats":
        user_id  = update.effective_user.id
        user     = await db.get_user(user_id)
        stats    = await db.get_user_stats(user_id)
        name     = user["full_name"] if user else "User"
        wait_msg = await query.message.reply_text("📊 Generating your stats\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
        motivation = await ai.generate_daily_motivation(stats)
        await wait_msg.edit_text(
            f"{format_stats(stats, name)}\n\n💬 _{escape_md(motivation)}_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        return

    # ── Status filters
    filter_map = {
        "menu_filter_pending":  ("pending",     None),
        "menu_filter_done":     ("done",        None),
        "menu_filter_progress": ("in_progress", None),
        "menu_filter_work":     (None, "work"),
        "menu_filter_study":    (None, "study"),
        "menu_filter_personal": (None, "personal"),
        "menu_filter_health":   (None, "health"),
        "menu_filter_finance":  (None, "finance"),
    }
    if action in filter_map:
        status, category = filter_map[action]
        await _show_task_list_with_menu(query.message, update.effective_user.id, status=status, category=category)
        return

    # ── Timezone setting
    if action == "menu_settimezone":
        await query.message.reply_text(
            "⚙️ *Set your timezone*\n\n"
            "Enter timezone like: `Asia/Tashkent`, `UTC`, `Europe/London`, `America/New_York`\n\n"
            "Common examples:\n"
            "`Asia/Tashkent` \\| `UTC` \\| `Europe/London` \\| `America/New_York` \\| `Australia/Sydney`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        context.user_data["awaiting_timezone"] = True
        return ConversationHandler.END


async def _show_task_list(message, user_id: int, status=None, category=None):
    """Shared helper — fetch tasks and send the inline list."""
    tasks = await db.get_user_tasks(user_id, status=status, category=category)
    if not tasks:
        await message.reply_text(
            "✅ No tasks found\\. You're all clear\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        return

    filter_label = ""
    if status:   filter_label = f" — {status.replace('_',' ').capitalize()}"
    elif category: filter_label = f" — {category.capitalize()}"

    await message.reply_text(
        f"📋 *Your Tasks{escape_md(filter_label)}* \\({len(tasks)} total\\)\n\n"
        "_Tap any task to view full details and actions:_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_list_keyboard(tasks),
    )


async def _show_task_list_with_menu(message, user_id: int, status=None, category=None):
    """Helper — fetch tasks and send the inline list with back button."""
    tasks = await db.get_user_tasks(user_id, status=status, category=category)
    if not tasks:
        await message.reply_text(
            "✅ No tasks found\\. You're all clear\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        return

    filter_label = ""
    if status:   filter_label = f" — {status.replace('_',' ').capitalize()}"
    elif category: filter_label = f" — {category.capitalize()}"

    # Build keyboard with task buttons
    rows = []
    for t in tasks:
        p = PRIORITY_EMOJI.get(t["priority"], "⚪")
        s = STATUS_EMOJI.get(t["status"], "❓")
        label = f"{s}{p} #{t['id']}  {t['title'][:32]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"task_view_{t['id']}")])
    
    # Add back button at the bottom
    rows.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="menu_main")])
    
    await message.reply_text(
        f"📋 *Your Tasks{escape_md(filter_label)}* \\({len(tasks)} total\\)\n\n"
        "_Tap any task to view full details and actions:_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(rows),
    )


# =============================================================================
#  /addtask — Manual wizard
# =============================================================================

async def addtask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_task", None)
    await update.message.reply_text(
        "📝 *New Task — Step 1/5*\n\nWhat's the task title?",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    return AT_TITLE

async def addtask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"] = {"title": update.message.text.strip()}
    await update.message.reply_text(
        "💬 *Step 2/5* — Add a description \\(or skip\\):",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=skip_keyboard(),
    )
    return AT_DESCRIPTION

async def addtask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_task"]["description"] = "" if text == "⏭ Skip" else text
    await update.message.reply_text(
        "🏷️ *Step 3/5* — Choose a category:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=category_keyboard(),
    )
    return AT_CATEGORY

async def addtask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"]["category"] = _parse_category(update.message.text)
    await update.message.reply_text(
        "⚡ *Step 4/5* — Set priority:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=priority_keyboard(),
    )
    return AT_PRIORITY

async def addtask_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_task"]["priority"] = _parse_priority(update.message.text)
    await update.message.reply_text(
        "🕐 *Step 5/5* — Set a deadline or skip\\.\n\n"
        "Accepted: `2026-03-15 14:30` \\| `15/03/2026` \\| `tomorrow` \\| `in 3 days`",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=skip_keyboard(),
    )
    return AT_DEADLINE

async def addtask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text      = update.message.text.strip()
    task_data = context.user_data["new_task"]
    deadline  = None

    if text != "⏭ Skip":
        deadline, err = parse_deadline(text)
        if err:
            logger.warning(f"Invalid deadline input from user {update.effective_user.id}: '{text}'")
            await update.message.reply_text(f"⚠️ {err}", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=skip_keyboard())
            return AT_DEADLINE

    task_data["deadline"] = deadline
    user_id = update.effective_user.id
    task_id = await db.create_task(user_id=user_id, **task_data)
    task    = await db.get_task(task_id, user_id)
    logger.info(f"Task created: ID={task_id}, user={user_id}, title='{task_data['title']}'")

    await update.message.reply_text(
        f"✅ *Task created successfully\\!*\n\n{format_task_card(task)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        "What would you like to do with this task?",
        reply_markup=task_action_with_menu_keyboard(task_id),
    )
    context.user_data.pop("new_task", None)
    return ConversationHandler.END

async def addtask_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_task", None)
    await update.message.reply_text("❌ Task creation cancelled\\.", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# =============================================================================
#  /addtask_ai — NLP flow
# =============================================================================

async def addtask_ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *AI Task Creation*\n\n"
        "Describe your task in plain English\\. For example:\n"
        "• _'Submit the quarterly report by Friday, urgent'_\n"
        "• _'Buy groceries tomorrow at 5 PM'_\n"
        "• _'Study for math exam next Monday morning'_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    return AI_INPUT

async def addtask_ai_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text    = update.message.text.strip()

    processing_msg = await update.message.reply_text("🔄 Analyzing your task with AI\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

    user   = await db.get_user(user_id)
    tz     = user["timezone"] if user else "UTC"
    parsed = await ai.parse_task_from_text(text, tz)

    if not parsed:
        await processing_msg.edit_text(
            "⚠️ Couldn't parse that task\\. Please try /addtask for manual entry\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    task_id = await db.create_task(user_id=user_id, **parsed)
    task    = await db.get_task(task_id, user_id)

    await processing_msg.edit_text(
        f"✅ *AI created your task\\!*\n\n{format_task_card(task)}\n\n"
        "_AI auto\\-detected category, priority, and deadline\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await update.message.reply_text(
        "What would you like to do with this task?",
        reply_markup=task_action_with_menu_keyboard(task_id),
    )
    return ConversationHandler.END

async def addtask_ai_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled\\.", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# =============================================================================
#  /mytasks — list with clickable buttons
# =============================================================================

async def cmd_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args    = context.args

    status_map   = {"pending":"pending","done":"done","in_progress":"in_progress","progress":"in_progress"}
    category_map = {"work":"work","study":"study","personal":"personal","health":"health","finance":"finance","general":"general"}

    status = category = None
    if args:
        arg = args[0].lower()
        if arg in status_map:     status   = status_map[arg]
        elif arg in category_map: category = category_map[arg]

    await _show_task_list(update.message, user_id, status=status, category=category)


# =============================================================================
#  /mytask <id> — single task view
# =============================================================================

async def cmd_mytask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /mytask \\<task\\_id\\>", parse_mode=ParseMode.MARKDOWN_V2)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Task ID must be a number\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await update.message.reply_text(
        format_task_card(task),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_with_menu_keyboard(task_id),
    )


# =============================================================================
#  INLINE BUTTON CALLBACKS
# =============================================================================

async def callback_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User tapped a task button in /mytasks list."""
    query   = update.callback_query
    user_id = query.from_user.id
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    task = await db.get_task(task_id, user_id)
    if not task:
        await query.answer("Task not found.", show_alert=True)
        return

    await query.message.reply_text(
        format_task_card(task),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_with_menu_keyboard(task_id),
    )


async def callback_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Done button on a task card."""
    query   = update.callback_query
    user_id = query.from_user.id
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    task = await db.get_task(task_id, user_id)
    if not task:
        await query.answer("Task not found.", show_alert=True)
        return
    if task["status"] == "done":
        await query.answer("Already marked as done.", show_alert=True)
        return

    await db.update_task(task_id, user_id, status="done")
    task = await db.get_task(task_id, user_id)
    logger.info(f"Task marked as done: ID={task_id}, user={user_id}")

    await query.edit_message_text(
        f"🎉 *Marked as done\\!*\n\n{format_task_card(task)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_with_menu_keyboard(task_id),
    )


async def callback_task_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✏️ Edit button — launches edit conversation and stores origin message for in-place update."""
    query   = update.callback_query
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    context.user_data["edit_id"]         = task_id
    context.user_data["edit_origin_msg"] = query.message  # store to edit in-place later
    keyboard = ReplyKeyboardMarkup([[f] for f in EDIT_FIELDS], one_time_keyboard=True, resize_keyboard=True)
    await query.message.reply_text(
        f"✏️ Editing task `\\#{task_id}`\\. What field do you want to change?",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )
    return EDIT_FIELD


async def callback_task_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🗑️ Delete button — show confirmation."""
    query   = update.callback_query
    user_id = query.from_user.id
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    task = await db.get_task(task_id, user_id)
    if not task:
        await query.answer("Task not found.", show_alert=True)
        return

    await query.edit_message_text(
        f"⚠️ Delete task `\\#{task_id}`?\n\n*{escape_md(task['title'])}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=delete_confirm_keyboard(task_id),
    )


async def callback_task_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirmed delete."""
    query   = update.callback_query
    user_id = query.from_user.id
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    deleted = await db.delete_task(task_id, user_id)
    if deleted:
        logger.info(f"Task deleted: ID={task_id}, user={user_id}")
        await query.edit_message_text(f"🗑️ Task `\\#{task_id}` deleted\\.", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        logger.warning(f"Failed to delete task: ID={task_id}, user={user_id}")
        await query.edit_message_text("⚠️ Could not delete task\\.", parse_mode=ParseMode.MARKDOWN_V2)


# =============================================================================
#  /done <id>
# =============================================================================

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /done \\<task\\_id\\>", parse_mode=ParseMode.MARKDOWN_V2)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Task ID must be a number\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await db.update_task(task_id, user_id, status="done")
    await update.message.reply_text(
        f"✅ Task `\\#{task_id}` *{escape_md(task['title'])}* marked as done\\! 🎉",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# =============================================================================
#  /edittask — Edit conversation
# =============================================================================

async def edittask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        try:
            task_id = int(args[0])
            user_id = update.effective_user.id
            if not await db.get_task(task_id, user_id):
                await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return ConversationHandler.END
            context.user_data["edit_id"] = task_id
            return await _ask_edit_field(update, context)
        except ValueError:
            pass

    await update.message.reply_text("✏️ Enter the *Task ID* you want to edit:", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())
    return EDIT_ID


async def edittask_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid task ID number\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return EDIT_ID

    user_id = update.effective_user.id
    if not await db.get_task(task_id, user_id):
        await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return EDIT_ID

    context.user_data["edit_id"] = task_id
    return await _ask_edit_field(update, context)


async def _ask_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([[f] for f in EDIT_FIELDS], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        f"📝 Editing task `\\#{context.user_data['edit_id']}`\\. What do you want to change?",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )
    return EDIT_FIELD


async def edittask_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = update.message.text.strip().lower()
    context.user_data["edit_field"] = field

    prompts = {
        "title":       ("Enter the new title:", ReplyKeyboardRemove()),
        "description": ("Enter the new description \\(or skip\\):", skip_keyboard()),
        "category":    ("Choose a new category:", category_keyboard()),
        "priority":    ("Choose a new priority:", priority_keyboard()),
        "deadline":    ("Enter new deadline or skip\\.\n`2026-03-15 14:30` \\| `tomorrow` \\| `in 3 days`", skip_keyboard()),
        "status":      ("Choose a new status:", ReplyKeyboardMarkup(
            [["⏳ pending", "🔄 in_progress"], ["✅ done", "❌ cancelled"]],
            one_time_keyboard=True, resize_keyboard=True,
        )),
    }
    if field not in prompts:
        await update.message.reply_text("⚠️ Unknown field\\. Choose from the keyboard\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return EDIT_FIELD

    prompt, kbd = prompts[field]
    await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kbd)
    return EDIT_VALUE


async def edittask_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task_id = context.user_data["edit_id"]
    field   = context.user_data["edit_field"]
    raw     = update.message.text.strip()

    value = None
    if field == "title":
        value = raw
    elif field == "description":
        value = "" if raw == "⏭ Skip" else raw
    elif field == "category":
        value = _parse_category(raw)
    elif field == "priority":
        value = _parse_priority(raw)
    elif field == "deadline":
        if raw != "⏭ Skip":
            value, err = parse_deadline(raw)
            if err:
                await update.message.reply_text(f"⚠️ {err}", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=skip_keyboard())
                return EDIT_VALUE
    elif field == "status":
        value = raw.lower().replace("⏳ ","").replace("🔄 ","").replace("✅ ","").replace("❌ ","").strip()

    updated = await db.update_task(task_id, user_id, **{field: value})
    task    = await db.get_task(task_id, user_id)

    origin_msg = context.user_data.pop("edit_origin_msg", None)

    if updated and task:
        new_text   = f"✅ *Task updated\\!*\n\n{format_task_card(task)}"
        new_markup = task_action_with_menu_keyboard(task_id)

        if origin_msg:
            # Edit the original task card in-place — no new message
            try:
                await origin_msg.edit_text(
                    new_text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=new_markup,
                )
                await update.message.reply_text(
                    "✅ Updated\\!",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ReplyKeyboardRemove(),
                )
            except Exception:
                # Fallback: send as new message if edit fails
                await update.message.reply_text(
                    new_text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ReplyKeyboardRemove(),
                )
                await update.message.reply_text("What would you like to do next?", reply_markup=new_markup)
        else:
            # Started via /edittask command — send a single combined message
            await update.message.reply_text(
                new_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=new_markup,
            )
    else:
        await update.message.reply_text(
            "⚠️ Could not update task\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

    context.user_data.pop("edit_id", None)
    context.user_data.pop("edit_field", None)
    return ConversationHandler.END


async def edittask_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("edit_id", None)
    context.user_data.pop("edit_field", None)
    await update.message.reply_text("❌ Edit cancelled\\.", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# =============================================================================
#  /deletetask <id>
# =============================================================================

async def cmd_deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /deletetask \\<task\\_id\\>", parse_mode=ParseMode.MARKDOWN_V2)
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Task ID must be a number\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    task = await db.get_task(task_id, user_id)
    if not task:
        await update.message.reply_text(f"⚠️ Task `\\#{task_id}` not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await update.message.reply_text(
        f"⚠️ Delete task `\\#{task_id}`?\n\n*{escape_md(task['title'])}*",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=delete_confirm_keyboard(task_id),
    )


# =============================================================================
#  /stats
# =============================================================================

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = update.effective_user.id
    user     = await db.get_user(user_id)
    stats    = await db.get_user_stats(user_id)
    name     = user["full_name"] if user else "User"

    wait_msg = await update.message.reply_text("📊 Generating your stats\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
    motivation = await ai.generate_daily_motivation(stats)

    await wait_msg.edit_text(
        f"{format_stats(stats, name)}\n\n💬 _{escape_md(motivation)}_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# =============================================================================
#  /settimezone
# =============================================================================

async def cmd_settimezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "Usage: /settimezone \\<timezone\\>\nExamples: `Asia/Tashkent`, `UTC`, `America/New_York`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    tz_name = context.args[0]
    try:
        pytz.timezone(tz_name)
        await db.update_user_preferences(user_id, timezone=tz_name)
        await update.message.reply_text(f"✅ Timezone set to `{escape_md(tz_name)}`\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception:
        await update.message.reply_text(
            "⚠️ Invalid timezone\\. See https://en\\.wikipedia\\.org/wiki/List\\_of\\_tz\\_database\\_time\\_zones",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def handle_timezone_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timezone input from the menu button flow."""
    user_id = update.effective_user.id
    if not context.user_data.get("awaiting_timezone"):
        return

    tz_name = update.message.text.strip()
    context.user_data.pop("awaiting_timezone", None)

    try:
        pytz.timezone(tz_name)
        await db.update_user_preferences(user_id, timezone=tz_name)
        await update.message.reply_text(
            f"✅ Timezone set to `{escape_md(tz_name)}`\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        logger.info(f"Timezone updated: user={user_id}, tz={tz_name}")
    except Exception:
        await update.message.reply_text(
            "⚠️ Invalid timezone\\. Please try again\\.\n"
            "Examples: `Asia/Tashkent`, `UTC`, `Europe/London`, `America/New_York`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=back_to_menu_keyboard(),
        )
        logger.warning(f"Invalid timezone from user {user_id}: {tz_name}")


# =============================================================================
#  Fallback
# =============================================================================

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Unknown command\\. Type /help to see all available commands\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# =============================================================================
#  CONVERSATION HANDLER BUILDERS
# =============================================================================

def build_addtask_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addtask", addtask_start),
            CallbackQueryHandler(callback_menu, pattern=r"^menu_addtask$"),
        ],
        states={
            AT_TITLE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_title)],
            AT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_description)],
            AT_CATEGORY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_category)],
            AT_PRIORITY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_priority)],
            AT_DEADLINE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_deadline)],
        },
        fallbacks=[CommandHandler("cancel", addtask_cancel)],
        allow_reentry=True,
    )


def build_addtask_ai_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addtask_ai", addtask_ai_start),
            CallbackQueryHandler(callback_menu, pattern=r"^menu_addtask_ai$"),
        ],
        states={
            AI_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_ai_input)],
        },
        fallbacks=[CommandHandler("cancel", addtask_ai_cancel)],
        allow_reentry=True,
    )


def build_edittask_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("edittask", edittask_start),
            # Entry from the inline ✏️ Edit button on any task card
            CallbackQueryHandler(callback_task_edit, pattern=r"^task_edit_\d+$"),
        ],
        states={
            EDIT_ID:    [MessageHandler(filters.TEXT & ~filters.COMMAND, edittask_id)],
            EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edittask_field)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edittask_value)],
        },
        fallbacks=[CommandHandler("cancel", edittask_cancel)],
        allow_reentry=True,
    )