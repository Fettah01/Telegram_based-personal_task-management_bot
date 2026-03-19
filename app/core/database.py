"""
app/core/database.py — SQLite async database layer
Handles all DB operations for users and tasks.
"""

import aiosqlite
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from config.settings import DATABASE_PATH as DB_PATH

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Schema
# ─────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    timezone    TEXT    DEFAULT 'UTC',
    language    TEXT    DEFAULT 'en',
    created_at  TEXT    DEFAULT (datetime('now')),
    last_active TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'pending',
    category    TEXT    DEFAULT 'general',
    priority    TEXT    DEFAULT 'medium',
    deadline    TEXT,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now')),
    reminded_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id  ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
"""


# ─────────────────────────────────────────────
#  Bootstrap
# ─────────────────────────────────────────────

async def init_db():
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


# ─────────────────────────────────────────────
#  User operations
# ─────────────────────────────────────────────

async def upsert_user(user_id: int, username: str, full_name: str) -> None:
    """Register a new user or update last_active timestamp."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username    = excluded.username,
                    full_name   = excluded.full_name,
                    last_active = datetime('now')
                """,
                (user_id, username, full_name),
            )
            await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"[DB] upsert_user failed for user {user_id}: {e}")
        raise


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_user failed for user {user_id}: {e}")
        raise


async def update_user_preferences(user_id: int, timezone: str = None, language: str = None) -> None:
    parts, values = [], []
    if timezone:
        parts.append("timezone = ?")
        values.append(timezone)
    if language:
        parts.append("language = ?")
        values.append(language)
    if not parts:
        return
    values.append(user_id)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"UPDATE users SET {', '.join(parts)} WHERE user_id = ?", values
            )
            await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"[DB] update_user_preferences failed for user {user_id}: {e}")
        raise


async def get_all_users() -> List[Dict[str, Any]]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_all_users failed: {e}")
        raise


# ─────────────────────────────────────────────
#  Task operations
# ─────────────────────────────────────────────

async def create_task(
    user_id: int,
    title: str,
    description: str = "",
    category: str = "general",
    priority: str = "medium",
    deadline: Optional[str] = None,
) -> int:
    """Insert a task and return its new ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                """
                INSERT INTO tasks (user_id, title, description, category, priority, deadline)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, title, description, category, priority, deadline),
            )
            await db.commit()
            return cur.lastrowid
    except aiosqlite.Error as e:
        logger.error(f"[DB] create_task failed for user {user_id}: {e}")
        raise


async def get_task(task_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_task failed for task {task_id}: {e}")
        raise


async def get_user_tasks(
    user_id: int,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM tasks WHERE user_id = ? AND status != 'cancelled'"
    params: list = [user_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, deadline ASC NULLS LAST"

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_user_tasks failed for user {user_id}: {e}")
        raise


async def update_task(task_id: int, user_id: int, **fields) -> bool:
    """Update arbitrary task fields. Returns True if a row was changed."""
    allowed = {"title", "description", "status", "category", "priority", "deadline"}
    # Python 3.7+ dicts are insertion-ordered, so SET clause order is deterministic
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id, user_id]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ? AND user_id = ?", values
            )
            await db.commit()
            return cur.rowcount > 0
    except aiosqlite.Error as e:
        logger.error(f"[DB] update_task failed for task {task_id}: {e}")
        raise


async def delete_task(task_id: int, user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
            )
            await db.commit()
            return cur.rowcount > 0
    except aiosqlite.Error as e:
        logger.error(f"[DB] delete_task failed for task {task_id}: {e}")
        raise


async def mark_task_reminded(task_id: int) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tasks SET reminded_at = datetime('now') WHERE id = ?", (task_id,)
            )
            await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"[DB] mark_task_reminded failed for task {task_id}: {e}")
        raise


async def get_due_tasks() -> List[Dict[str, Any]]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT t.*, u.timezone FROM tasks t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.status IN ('pending', 'in_progress')
                  AND t.deadline IS NOT NULL
                  AND t.deadline <= datetime('now', '+30 minutes')
                  AND t.deadline >= datetime('now', '-5 minutes')
                  AND (t.reminded_at IS NULL OR t.reminded_at < datetime('now', '-60 minutes'))
                """
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_due_tasks failed: {e}")
        raise


# ─────────────────────────────────────────────
#  Stats — single connection for all 5 queries
# ─────────────────────────────────────────────

async def get_user_stats(user_id: int) -> Dict[str, Any]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT COUNT(*) as total FROM tasks WHERE user_id = ?", (user_id,)
            ) as cur:
                total = (await cur.fetchone())["total"]

            async with db.execute(
                "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND status = 'done'",
                (user_id,),
            ) as cur:
                done = (await cur.fetchone())["cnt"]

            async with db.execute(
                "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND status = 'pending'",
                (user_id,),
            ) as cur:
                pending = (await cur.fetchone())["cnt"]

            async with db.execute(
                """SELECT category, COUNT(*) as cnt FROM tasks
                   WHERE user_id = ? GROUP BY category ORDER BY cnt DESC LIMIT 1""",
                (user_id,),
            ) as cur:
                top_cat_row = await cur.fetchone()
                top_category = top_cat_row["category"] if top_cat_row else "general"

            async with db.execute(
                """SELECT COUNT(*) as cnt FROM tasks
                   WHERE user_id = ? AND status IN ('pending','in_progress')
                     AND deadline IS NOT NULL AND deadline < datetime('now')""",
                (user_id,),
            ) as cur:
                overdue = (await cur.fetchone())["cnt"]

        completion_rate = round((done / total * 100) if total else 0, 1)
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": completion_rate,
            "top_category": top_category,
        }
    except aiosqlite.Error as e:
        logger.error(f"[DB] get_user_stats failed for user {user_id}: {e}")
        raise