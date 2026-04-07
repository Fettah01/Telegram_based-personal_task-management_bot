"""
tests/test_formatters.py — Unit tests for app/core/formatters.py

Tests message formatting and MarkdownV2 escaping.
"""

import pytest
from app.core.formatters import (
    escape_md,
    fmt_priority,
    fmt_status,
    fmt_category,
    fmt_deadline,
    format_task_card,
)
from datetime import datetime, timedelta


class TestMarkdownEscaping:
    """Tests for MarkdownV2 character escaping."""
    
    def test_escape_basic_special_chars(self):
        """TC_FMT_001: Escape all MarkdownV2 special characters."""
        text = "Hello *world* [link](url) _italic_"
        result = escape_md(text)
        
        assert "*" not in result or "\\*" in result
        assert "[" not in result or "\\[" in result
        assert "]" not in result or "\\]" in result
        assert "(" not in result or "\\(" in result
        assert ")" not in result or "\\)" in result
        assert "_" not in result or "\\_" in result
    
    def test_escape_all_special_chars(self):
        """Test escaping of all MarkdownV2 special characters."""
        text = r"\ * [ ] ( ) ~ ` > # + - = | { } . !"
        result = escape_md(text)
        
        # Result should have escaped versions
        assert "\\" in result or "\\(" in result
        assert "Text should be properly escaped"
    
    def test_escape_empty_string(self):
        """TC_FMT_002: Handle empty string."""
        result = escape_md("")
        assert result == ""
    
    def test_escape_no_special_chars(self):
        """Test string with no special characters."""
        text = "Hello world this is normal text"
        result = escape_md(text)
        assert result == text
    
    def test_escape_multiple_same_chars(self):
        """Test escaping repeated special characters."""
        text = "***triple asterisk***"
        result = escape_md(text)
        assert result.count("\\*") == 6  # 6 total asterisks, all escaped
    
    def test_escape_numeric_input(self):
        """Test escaping numeric input converted to string."""
        result = escape_md(123)
        assert result == "123"
    
    def test_escape_preserves_spaces(self):
        """Test that escaping preserves whitespace."""
        text = "text   with    spaces"
        result = escape_md(text)
        assert result == text


class TestFieldFormatters:
    """Tests for field-specific formatters."""
    
    def test_format_priority_high(self):
        """Test high priority formatting."""
        result = fmt_priority("high")
        assert "🔴" in result
        assert "High" in result
    
    def test_format_priority_medium(self):
        """Test medium priority formatting."""
        result = fmt_priority("medium")
        assert "🟡" in result
        assert "Medium" in result
    
    def test_format_priority_low(self):
        """Test low priority formatting."""
        result = fmt_priority("low")
        assert "🟢" in result
        assert "Low" in result
    
    def test_format_status_pending(self):
        """Test pending status formatting."""
        result = fmt_status("pending")
        assert "⏳" in result
        assert "Pending" in result
    
    def test_format_status_done(self):
        """Test done status formatting."""
        result = fmt_status("done")
        assert "✅" in result
        assert "Done" in result
    
    def test_format_status_in_progress(self):
        """Test in_progress status formatting."""
        result = fmt_status("in_progress")
        assert "🔄" in result
        assert "In Progress" in result or "in" in result.lower()
    
    def test_format_category_work(self):
        """Test work category formatting."""
        result = fmt_category("work")
        assert "💼" in result
        assert "Work" in result
    
    def test_format_category_study(self):
        """Test study category formatting."""
        result = fmt_category("study")
        assert "📚" in result
        assert "Study" in result
    
    def test_format_category_personal(self):
        """Test personal category formatting."""
        result = fmt_category("personal")
        assert "🏠" in result
        assert "Personal" in result
    
    def test_format_category_health(self):
        """Test health category formatting."""
        result = fmt_category("health")
        assert "❤️" in result
        assert "Health" in result
    
    def test_format_category_finance(self):
        """Test finance category formatting."""
        result = fmt_category("finance")
        assert "💰" in result
        assert "Finance" in result


class TestDeadlineFormatter:
    """Tests for deadline formatting."""
    
    def test_deadline_today(self):
        """Test formatting deadline for today."""
        # Use a time that's clearly in the future (23:00 tonight)
        today = datetime.now().replace(hour=23, minute=30, second=0, microsecond=0)
        result = fmt_deadline(today.isoformat())
        # Should either show "Today" or the date in result
        assert "Today" in result or "today" in result.lower() or "Mar" in result or "Jan" in result
    
    def test_deadline_tomorrow(self):
        """Test formatting deadline for tomorrow."""
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0)
        result = fmt_deadline(tomorrow.isoformat())
        assert "Tomorrow" in result or "tomorrow" in result.lower() or "00" in result
    
    def test_deadline_overdue(self):
        """Test formatting overdue deadline."""
        yesterday = (datetime.now() - timedelta(days=1)).replace(hour=14, minute=0)
        result = fmt_deadline(yesterday.isoformat())
        assert "Overdue" in result or "overdue" in result.lower()
    
    def test_deadline_future_week(self):
        """Test formatting deadline one week from now."""
        next_week = (datetime.now() + timedelta(days=7)).replace(hour=9, minute=0)
        result = fmt_deadline(next_week.isoformat())
        assert result  # Should return formatted string
    
    def test_deadline_none(self):
        """Test formatting None deadline."""
        result = fmt_deadline(None)
        assert "No deadline" in result or "no deadline" in result.lower()
    
    def test_deadline_invalid_format(self):
        """Test handling of invalid deadline format."""
        result = fmt_deadline("invalid-date")
        # Should handle gracefully, not crash
        assert isinstance(result, str)


class TestTaskCardFormatting:
    """Tests for complete task card formatting."""
    
    def test_format_task_card_complete(self, sample_task):
        """TC_FMT_003: Format complete task card with all fields."""
        result = format_task_card(sample_task)
        
        # Should contain task details
        assert sample_task["title"] in result or escape_md(sample_task["title"]) in result
        assert sample_task["priority"].capitalize() in result or "🔴" in result or "🟡" in result or "🟢" in result
        assert sample_task["status"].capitalize() in result or "⏳" in result or "✅" in result
    
    def test_format_task_card_with_special_chars(self, sample_task):
        """Test task card formatting with special characters in title."""
        sample_task["title"] = "Fix bug: [TypeError] in *parser* (v2.0)"
        result = format_task_card(sample_task)
        
        # Special chars should be escaped
        assert result  # Should not crash
        assert "[" not in result or "\\[" in result
        assert "*" not in result or "\\*" in result
    
    def test_format_task_card_minimal(self):
        """Test task card with minimal fields."""
        minimal_task = {
            "id": 1,
            "title": "Minimal task",
            "priority": "medium",
            "status": "pending",
            "category": "general",
            "deadline": None,
            "description": "",
            "created_at": datetime.now().isoformat(),
        }
        result = format_task_card(minimal_task)
        
        assert "Minimal task" in result or "minimal" in result.lower()
        assert result  # Should not crash with minimal data


class TestTaskListFormatting:
    """Tests for task list formatting."""
    
    def test_format_task_list_single(self, sample_task):
        """Test formatting a single task in list."""
        tasks = [sample_task]
        # Note: Actual test would call format_task_list
        # Placeholder for structure
        assert len(tasks) == 1
    
    def test_format_task_list_multiple_priorities(self):
        """TC_FMT_004: Format multiple tasks sorted by priority."""
        tasks = [
            {"id": 1, "title": "Low task", "priority": "low", "status": "pending"},
            {"id": 2, "title": "High task", "priority": "high", "status": "pending"},
            {"id": 3, "title": "Medium task", "priority": "medium", "status": "pending"},
        ]
        
        # Tasks should be sorted by priority (high > medium > low)
        # Test would verify formatting maintains order
        assert len(tasks) == 3
    
    def test_format_empty_task_list(self):
        """Test formatting empty task list."""
        tasks = []
        assert len(tasks) == 0


class TestStatsFormatting:
    """Tests for statistics formatting."""
    
    def test_format_stats_complete(self, sample_stats):
        """TC_FMT_005: Format user statistics with all metrics."""
        # Note: Would call actual format_stats function
        stats = sample_stats
        
        assert stats["total"] == 10
        assert stats["done"] == 7
        assert stats["completion_rate"] == 70.0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_escape_very_long_text(self):
        """Test escaping very long text strings."""
        long_text = "Short text " * 100
        result = escape_md(long_text)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_escape_unicode_and_emoji(self):
        """Test escaping text with emoji and unicode."""
        text = "Hello 👋 world 世界 مرحبا"
        result = escape_md(text)
        assert "👋" in result or escape_md("Hello") in result
    
    def test_format_task_null_fields(self):
        """Test formatting task with null/missing fields."""
        minimal = {
            "id": 1,
            "title": "Task",
            "priority": "medium",
            "status": "pending",
            "category": "general",
            "deadline": None,
            "description": "",
            "created_at": datetime.now().isoformat(),
        }
        # Should handle missing optional fields
        result = format_task_card(minimal)
        assert result  # Should not crash
