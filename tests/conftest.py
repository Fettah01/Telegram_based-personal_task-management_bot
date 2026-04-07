"""
tests/conftest.py — Pytest configuration and shared fixtures
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import aiosqlite

# Configure asyncio for pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def temp_db():
    """
    Provide a temporary in-memory SQLite database for testing.
    Database is auto-created with schema and cleaned up after test.
    """
    # Use in-memory database for speed
    db_path = ":memory:"
    db = await aiosqlite.connect(db_path)
    
    # Create schema
    schema = """
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
    await db.executescript(schema)
    await db.commit()
    
    yield db
    
    # Cleanup
    await db.close()


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API client for AI service tests."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """
    {
        "title": "Test Task",
        "description": "Test description",
        "category": "general",
        "priority": "medium",
        "deadline": "2026-03-25T14:00:00"
    }
    """
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_bot():
    """Mock Telegram bot for handler/reminder tests."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {
        "user_id": 123456,
        "username": "test_user",
        "full_name": "Test User",
        "timezone": "UTC",
        "language": "en",
    }


@pytest.fixture
def sample_task():
    """Sample task data for tests."""
    return {
        "id": 1,
        "user_id": 123456,
        "title": "Test task",
        "description": "Test description",
        "status": "pending",
        "category": "general",
        "priority": "medium",
        "deadline": "2026-03-25T14:00:00",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "reminded_at": None,
    }


@pytest.fixture
def sample_stats():
    """Sample user stats for tests."""
    return {
        "total": 10,
        "done": 7,
        "pending": 2,
        "overdue": 1,
        "completion_rate": 70.0,
    }
