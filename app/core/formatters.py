"""
app/core/formatters.py — Reusable message formatting helpers.

All public functions that return strings intended for Telegram MarkdownV2
must produce fully-escaped output. escape_md() is the single source of truth.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────
#  MarkdownV2 escaping  (defined first — used by everything below)
# ─────────────────────────────────────────────

# Every character Telegram's MarkdownV2 parser treats as special
_MD_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def escape_md(text: str) -> str:
    """Escape all MarkdownV2 special characters in a plain string."""
    if not isinstance(text, str):
        text = str(text)
    for ch in _MD_SPECIAL:
        text = text.replace(ch, f"\\{ch}")
    return text


# ─────────────────────────────────────────────
#  Emoji maps
# ─────────────────────────────────────────────

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_EMOJI   = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}
CATEGORY_EMOJI = {
    "work":     "💼",
    "study":    "📚",
    "personal": "🏠",
    "health":   "❤️",
    "finance":  "💰",
    "general":  "📋",
}


# ─────────────────────────────────────────────
#  Field formatters — all output is MD2-safe
# ─────────────────────────────────────────────

def fmt_priority(p: str) -> str:
    emoji = PRIORITY_EMOJI.get(p, "⚪")
    return f"{emoji} {escape_md(p.capitalize())}"


def fmt_status(s: str) -> str:
    emoji = STATUS_EMOJI.get(s, "❓")
    label = s.replace("_", " ").capitalize()
    return f"{emoji} {escape_md(label)}"


def fmt_category(c: str) -> str:
    emoji = CATEGORY_EMOJI.get(c, "📋")
    return f"{emoji} {escape_md(c.capitalize())}"


def fmt_deadline(deadline: Optional[str]) -> str:
    """Return a fully MD2-escaped deadline string with a human-readable label."""
    if not deadline:
        return escape_md("No deadline")
    try:
        dt   = datetime.fromisoformat(deadline)
        now  = datetime.now()
        days = (dt - now).days

        if days < 0:
            label = "Overdue"
        elif days == 0:
            label = "Today"
        elif days == 1:
            label = "Tomorrow"
        else:
            label = f"📅 In {days} days"

        # strftime output contains spaces and commas — escape it all
        date_str = dt.strftime("%d %b %Y, %H:%M")
        return f"{escape_md(date_str)} \\({escape_md(label)}\\)"
    except Exception:
        return escape_md(str(deadline))


# ─────────────────────────────────────────────
#  Task card  — full detail view
# ─────────────────────────────────────────────

def format_task_card(task: Dict[str, Any], show_id: bool = True) -> str:
    lines = []
    if show_id:
        lines.append(f"🔖 *Task \\#{task['id']}*")
    lines.append(f"📝 *{escape_md(task['title'])}*")
    if task.get("description"):
        lines.append(f"💬 {escape_md(task['description'])}")
    lines.append(f"📊 Status:    {fmt_status(task['status'])}")
    lines.append(f"⚡ Priority:  {fmt_priority(task['priority'])}")
    lines.append(f"🏷️ Category:  {fmt_category(task['category'])}")
    lines.append(f"🕐 Deadline:  {fmt_deadline(task.get('deadline'))}")
    lines.append(f"🗓️ Created:   {escape_md(task['created_at'][:10])}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  Task list  — compact multi-row view
# ─────────────────────────────────────────────

def format_task_list(tasks: List[Dict[str, Any]]) -> str:
    """Compact list used as fallback plain-text (not used for inline-button list)."""
    if not tasks:
        return "✅ No tasks found\\. You're all clear\\!"

    lines = [f"📋 *Your Tasks* \\({len(tasks)} total\\)\n"]
    for t in tasks:
        p_emoji = PRIORITY_EMOJI.get(t["priority"], "⚪")
        s_emoji = STATUS_EMOJI.get(t["status"], "❓")
        deadline_badge = ""
        if t.get("deadline"):
            try:
                dt   = datetime.fromisoformat(t["deadline"])
                diff = (dt - datetime.utcnow()).days
                if diff < 0:
                    deadline_badge = " ⚠️OD"
                elif diff == 0:
                    deadline_badge = " 🔥Today"
                elif diff == 1:
                    deadline_badge = " ⏰Tmrw"
                else:
                    deadline_badge = f" 📅{dt.strftime('%d/%m')}"
            except Exception:
                pass
        lines.append(
            f"{s_emoji}{p_emoji} `\\#{t['id']}` "
            f"{escape_md(t['title'][:40])}"
            f"{escape_md(deadline_badge)}"
        )
    lines.append("\n_Use /edittask \\<id\\> or /deletetask \\<id\\>_")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  Stats card
# ─────────────────────────────────────────────

def format_stats(stats: Dict[str, Any], name: str) -> str:
    bar_len = 10
    filled  = round(stats["completion_rate"] / 100 * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)
    # completion_rate is a float e.g. 66.7 — the dot must be escaped
    rate_str = escape_md(str(stats["completion_rate"]))
    return (
        f"📊 *Productivity Stats for {escape_md(name)}*\n\n"
        f"📦 Total tasks:     `{stats['total']}`\n"
        f"✅ Completed:       `{stats['done']}`\n"
        f"⏳ Pending:         `{stats['pending']}`\n"
        f"⚠️ Overdue:        `{stats['overdue']}`\n"
        f"🏷️ Top category:   `{escape_md(stats['top_category'].capitalize())}`\n\n"
        f"📈 Completion rate:\n"
        f"`{bar}` {rate_str}%"
    )