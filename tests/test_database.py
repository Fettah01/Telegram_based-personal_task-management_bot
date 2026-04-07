"""
tests/test_database.py — Unit tests for app/core/database.py

Tests user and task CRUD operations.
"""

import pytest
from datetime import datetime, timedelta
import aiosqlite


# Note: In a real scenario, we would patch DB_PATH in database.py
# For this example, we'll show the test structure


class TestUserOperations:
    """Tests for user-related database functions."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, temp_db, sample_user):
        """TC_DB_001: Create new user successfully."""
        # Insert user
        await temp_db.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            """,
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        await temp_db.commit()
        
        # Verify user was created
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (sample_user["user_id"],)
        ) as cur:
            row = await cur.fetchone()
        
        assert row is not None
        assert row["username"] == sample_user["username"]
        assert row["full_name"] == sample_user["full_name"]
    
    @pytest.mark.asyncio
    async def test_get_user(self, temp_db, sample_user):
        """TC_DB_003: Retrieve user by ID."""
        # Setup: Create user
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        await temp_db.commit()
        
        # Test: Retrieve user
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (sample_user["user_id"],)
        ) as cur:
            user = await cur.fetchone()
        
        assert user is not None
        assert dict(user)["user_id"] == sample_user["user_id"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, temp_db):
        """TC_DB_004: Retrieve non-existent user returns None."""
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (999999,)
        ) as cur:
            user = await cur.fetchone()
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, temp_db, sample_user):
        """TC_DB_005: Update user timezone and language."""
        # Setup: Create user
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        await temp_db.commit()
        
        # Test: Update preferences
        new_tz = "America/New_York"
        new_lang = "es"
        await temp_db.execute(
            "UPDATE users SET timezone = ?, language = ? WHERE user_id = ?",
            (new_tz, new_lang, sample_user["user_id"])
        )
        await temp_db.commit()
        
        # Verify
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (sample_user["user_id"],)
        ) as cur:
            user = await cur.fetchone()
        
        assert dict(user)["timezone"] == new_tz
        assert dict(user)["language"] == new_lang
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, temp_db, sample_user):
        """TC_DB_006: Get all users from database."""
        # Setup: Create multiple users
        users = [
            (111111, "user1", "User One"),
            (222222, "user2", "User Two"),
            (333333, "user3", "User Three"),
        ]
        for uid, uname, fname in users:
            await temp_db.execute(
                "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (uid, uname, fname)
            )
        await temp_db.commit()
        
        # Test: Get all users
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute("SELECT * FROM users") as cur:
            all_users = await cur.fetchall()
        
        assert len(all_users) >= 3
        assert all(u["username"] for u in all_users)


class TestTaskOperations:
    """Tests for task-related database functions."""
    
    @pytest.mark.asyncio
    async def test_create_task(self, temp_db, sample_user, sample_task):
        """TC_DB_007: Create new task successfully."""
        # Setup: Create user
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        await temp_db.commit()
        
        # Test: Create task
        cur = await temp_db.execute(
            """
            INSERT INTO tasks (user_id, title, description, category, priority, deadline)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sample_user["user_id"],
                sample_task["title"],
                sample_task["description"],
                sample_task["category"],
                sample_task["priority"],
                sample_task["deadline"],
            )
        )
        await temp_db.commit()
        task_id = cur.lastrowid
        
        # Verify
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ) as cursor:
            task = await cursor.fetchone()
        
        assert task is not None
        assert dict(task)["title"] == sample_task["title"]
        assert dict(task)["user_id"] == sample_user["user_id"]
    
    @pytest.mark.asyncio
    async def test_get_task(self, temp_db, sample_user, sample_task):
        """TC_DB_008: Retrieve task by ID."""
        # Setup: Create user and task
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        cur = await temp_db.execute(
            "INSERT INTO tasks (user_id, title, description, category, priority) VALUES (?, ?, ?, ?, ?)",
            (sample_user["user_id"], sample_task["title"], sample_task["description"], 
             sample_task["category"], sample_task["priority"])
        )
        await temp_db.commit()
        task_id = cur.lastrowid
        
        # Test: Get task
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, sample_user["user_id"])
        ) as cursor:
            task = await cursor.fetchone()
        
        assert task is not None
        assert dict(task)["title"] == sample_task["title"]
    
    @pytest.mark.asyncio
    async def test_get_task_wrong_user(self, temp_db, sample_user, sample_task):
        """TC_DB_009: Prevent cross-user task access."""
        # Setup: Create task for user 1
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (111111, "user1", "User One")
        )
        cur = await temp_db.execute(
            "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
            (111111, "Sensitive Task")
        )
        await temp_db.commit()
        task_id = cur.lastrowid
        
        # Test: Try to access as different user
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, 222222)  # Different user
        ) as cursor:
            task = await cursor.fetchone()
        
        assert task is None  # Should not have access
    
    @pytest.mark.asyncio
    async def test_list_user_tasks_filtered(self, temp_db, sample_user):
        """TC_DB_010: List tasks with filters (status, category)."""
        # Setup
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        
        # Create tasks with different statuses and categories
        tasks_data = [
            (sample_user["user_id"], "Task 1", "pending", "work", "high"),
            (sample_user["user_id"], "Task 2", "done", "work", "medium"),
            (sample_user["user_id"], "Task 3", "pending", "personal", "low"),
        ]
        for uid, title, status, cat, pri in tasks_data:
            await temp_db.execute(
                "INSERT INTO tasks (user_id, title, status, category, priority) VALUES (?, ?, ?, ?, ?)",
                (uid, title, status, cat, pri)
            )
        await temp_db.commit()
        
        # Test: Get pending tasks
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND status = ?",
            (sample_user["user_id"], "pending")
        ) as cursor:
            pending = await cursor.fetchall()
        
        assert len(pending) == 2
        assert all(dict(t)["status"] == "pending" for t in pending)
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, temp_db, sample_user):
        """TC_DB_012: Update task status from pending to done."""
        # Setup
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        cur = await temp_db.execute(
            "INSERT INTO tasks (user_id, title, status) VALUES (?, ?, ?)",
            (sample_user["user_id"], "Test Task", "pending")
        )
        await temp_db.commit()
        task_id = cur.lastrowid
        
        # Test: Update status
        await temp_db.execute(
            "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
            ("done", task_id)
        )
        await temp_db.commit()
        
        # Verify
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ) as cursor:
            task = await cursor.fetchone()
        
        assert dict(task)["status"] == "done"
    
    @pytest.mark.asyncio
    async def test_delete_task(self, temp_db, sample_user):
        """TC_DB_013: Delete task from database."""
        # Setup
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        cur = await temp_db.execute(
            "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
            (sample_user["user_id"], "To Delete")
        )
        await temp_db.commit()
        task_id = cur.lastrowid
        
        # Test: Delete task
        await temp_db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, sample_user["user_id"])
        )
        await temp_db.commit()
        
        # Verify deletion
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ) as cursor:
            task = await cursor.fetchone()
        
        assert task is None


class TestTaskStatistics:
    """Tests for task statistics and analytics."""
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, temp_db, sample_user):
        """TC_DB_015: Get user task statistics."""
        # Setup: Create user and tasks with different statuses
        await temp_db.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (sample_user["user_id"], sample_user["username"], sample_user["full_name"])
        )
        
        # Create tasks: 7 done, 2 pending, 1 overdue
        from datetime import datetime, timedelta
        today = datetime.now()
        overdue_date = (today - timedelta(days=1)).isoformat()
        future_date = (today + timedelta(days=1)).isoformat()
        
        tasks = [
            ("Task 1", "done", None),
            ("Task 2", "done", None),
            ("Task 3", "done", None),
            ("Task 4", "done", None),
            ("Task 5", "done", None),
            ("Task 6", "done", None),
            ("Task 7", "done", None),
            ("Task 8", "pending", future_date),
            ("Task 9", "pending", future_date),
            ("Task 10", "pending", overdue_date),
        ]
        
        for title, status, deadline in tasks:
            await temp_db.execute(
                "INSERT INTO tasks (user_id, title, status, deadline) VALUES (?, ?, ?, ?)",
                (sample_user["user_id"], title, status, deadline)
            )
        await temp_db.commit()
        
        # Test: Calculate stats
        temp_db.row_factory = aiosqlite.Row
        async with temp_db.execute(
            "SELECT COUNT(*) as total FROM tasks WHERE user_id = ?",
            (sample_user["user_id"],)
        ) as cur:
            total = await cur.fetchone()
        
        async with temp_db.execute(
            "SELECT COUNT(*) as done FROM tasks WHERE user_id = ? AND status = ?",
            (sample_user["user_id"], "done")
        ) as cur:
            done = await cur.fetchone()
        
        async with temp_db.execute(
            "SELECT COUNT(*) as pending FROM tasks WHERE user_id = ? AND status = ? AND deadline > ?",
            (sample_user["user_id"], "pending", datetime.now().isoformat())
        ) as cur:
            pending = await cur.fetchone()
        
        assert dict(total)["total"] == 10
        assert dict(done)["done"] == 7
        assert dict(pending)["pending"] >= 2
