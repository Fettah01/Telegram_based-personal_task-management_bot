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
#  /start
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username or "", user.full_name or user.first_name or "User")
    name = escape_md(user.first_name or "there")
    await update.message.reply_text(
        f"👋 *Welcome, {name}\\!*\n\n"
        "I'm your *AI\\-powered Task Manager*\\. Here's what I can do:\n\n"
        "🤖 *AI Features*\n"
        "• Parse tasks from plain English\n"
        "• Auto\\-categorize your tasks\n"
        "• Predict priority levels\n"
        "• Smart deadline reminders\n\n"
        "📌 *Quick Start*\n"
        "• /addtask\\_ai — _'Buy groceries tomorrow at 5 PM'_\n"
        "• /mytasks — see all your tasks\n"
        "• /help — full command list\n\n"
        "Let's get productive\\! 🚀",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# =============================================================================
#  /help
# =============================================================================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Command Reference*\n\n"
        "🆕 *Creating Tasks*\n"
        "/addtask — Step\\-by\\-step task wizard\n"
        "/addtask\\_ai — Natural language AI creation\n\n"
        "📋 *Managing Tasks*\n"
        "/mytasks — List all tasks \\(tap a task to view it\\)\n"
        "/mytasks pending — Filter by status\n"
        "/mytasks work — Filter by category\n"
        "/mytask \\<id\\> — View a single task\n"
        "/done \\<id\\> — Mark task as completed\n"
        "/edittask \\<id\\> — Edit a task\n"
        "/deletetask \\<id\\> — Delete a task\n\n"
        "📊 *Insights*\n"
        "/stats — Your productivity statistics\n\n"
        "⚙️ *Settings*\n"
        "/settimezone \\<tz\\> — e\\.g\\. Asia/Tashkent\n\n"
        "💡 *Tips*\n"
        "• Tap any task in /mytasks for full details \\+ action buttons\n"
        "• Every task card has Done / Edit / Delete buttons\n"
        "• AI understands: _'Finish report by Friday urgent'_",
        parse_mode=ParseMode.MARKDOWN_V2,
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
            await update.message.reply_text(f"⚠️ {err}", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=skip_keyboard())
            return AT_DEADLINE

    task_data["deadline"] = deadline
    user_id = update.effective_user.id
    task_id = await db.create_task(user_id=user_id, **task_data)
    task    = await db.get_task(task_id, user_id)

    await update.message.reply_text(
        f"✅ *Task created successfully\\!*\n\n{format_task_card(task)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        "What would you like to do with this task?",
        reply_markup=task_action_keyboard(task_id),
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
        reply_markup=task_action_keyboard(task_id),
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
        if arg in status_map:   status   = status_map[arg]
        elif arg in category_map: category = category_map[arg]

    tasks = await db.get_user_tasks(user_id, status=status, category=category)

    if not tasks:
        await update.message.reply_text("✅ No tasks found\\. You're all clear\\!", parse_mode=ParseMode.MARKDOWN_V2)
        return

    filter_label = ""
    if status:   filter_label = f" — {status.replace('_',' ').capitalize()}"
    elif category: filter_label = f" — {category.capitalize()}"

    await update.message.reply_text(
        f"📋 *Your Tasks{escape_md(filter_label)}* \\({len(tasks)} total\\)\n\n"
        "_Tap any task to view full details and actions:_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_list_keyboard(tasks),
    )


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
        reply_markup=task_action_keyboard(task_id),
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
        reply_markup=task_action_keyboard(task_id),
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

    await query.edit_message_text(
        f"🎉 *Marked as done\\!*\n\n{format_task_card(task)}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=task_action_keyboard(task_id),
    )


async def callback_task_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✏️ Edit button — launches edit conversation."""
    query   = update.callback_query
    task_id = int(query.data.split("_")[-1])
    await query.answer()

    context.user_data["edit_id"] = task_id
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
        await query.edit_message_text(f"🗑️ Task `\\#{task_id}` deleted\\.", parse_mode=ParseMode.MARKDOWN_V2)
    else:
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

    if updated and task:
        await update.message.reply_text(
            f"✅ *Task updated successfully\\!*\n\n{format_task_card(task)}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "What would you like to do next?",
            reply_markup=task_action_keyboard(task_id),
        )
    else:
        await update.message.reply_text("⚠️ Could not update task\\.", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())

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
        entry_points=[CommandHandler("addtask", addtask_start)],
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
        entry_points=[CommandHandler("addtask_ai", addtask_ai_start)],
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