# Test Cases Document

## Overview

This document contains detailed test cases for the TaskBot application. All test cases are derived from the Test Plan and cover unit, integration, and system testing levels.

### Test Case Format

| Field | Description |
|-------|---|
| **Test ID** | Unique identifier (e.g., `TC_DB_001`) |
| **Component** | Module being tested |
| **Function** | Specific function or feature |
| **Type** | Unit / Integration / System / Manual |
| **Description** | What is being tested |
| **Prerequisites** | Setup requirements |
| **Test Data** | Input values and test data |
| **Expected Result** | Expected outcome |
| **Status** | Not Run / In Progress / Pass / Fail |

---

## 1. DATABASE MODULE (database.py)

### User Operations

#### TC_DB_001: Create New User
- **Component**: database.py
- **Function**: `upsert_user()`
- **Type**: Unit
- **Description**: Register a new user with username and full name
- **Prerequisites**: Database initialized, no existing user with same ID
- **Test Data**: `user_id=123456, username="john_doe", full_name="John Doe"`
- **Expected Result**: User record created successfully, fields populated correctly
- **Status**: Not Run

#### TC_DB_002: Update Existing User
- **Component**: database.py
- **Function**: `upsert_user()`
- **Type**: Unit
- **Description**: Update last_active timestamp for existing user
- **Prerequisites**: User already exists in database
- **Test Data**: `user_id=123456, username="john_doe", full_name="John Doe"`
- **Expected Result**: User record updated, last_active timestamp refreshed
- **Status**: Not Run

#### TC_DB_003: Retrieve User by ID
- **Component**: database.py
- **Function**: `get_user()`
- **Type**: Unit
- **Description**: Fetch user details by user_id
- **Prerequisites**: User exists in database
- **Test Data**: `user_id=123456`
- **Expected Result**: Returns dict with user data (id, username, full_name, timezone, language, created_at, last_active)
- **Status**: Not Run

#### TC_DB_004: Retrieve Non-Existent User
- **Component**: database.py
- **Function**: `get_user()`
- **Type**: Unit
- **Description**: Attempt to retrieve user that doesn't exist
- **Prerequisites**: User does not exist in database
- **Test Data**: `user_id=999999`
- **Expected Result**: Returns None
- **Status**: Not Run

#### TC_DB_005: Update User Preferences
- **Component**: database.py
- **Function**: `update_user_preferences()`
- **Type**: Unit
- **Description**: Update timezone and language preferences
- **Prerequisites**: User exists in database
- **Test Data**: `user_id=123456, timezone="America/New_York", language="en"`
- **Expected Result**: User preferences updated successfully
- **Status**: Not Run

#### TC_DB_006: Get All Users
- **Component**: database.py
- **Function**: `get_all_users()`
- **Type**: Unit
- **Description**: Retrieve list of all registered users
- **Prerequisites**: Multiple users exist in database
- **Test Data**: N/A (retrieves all)
- **Expected Result**: Returns list of user dicts, count matches database
- **Status**: Not Run

### Task Operations

#### TC_DB_007: Create New Task
- **Component**: database.py
- **Function**: `create_task()`
- **Type**: Unit
- **Description**: Create a task with all fields for a user
- **Prerequisites**: User exists in database
- **Test Data**: `user_id=123456, title="Finish report", description="Q1 report", category="work", priority="high", deadline="2026-03-25 17:00:00"`
- **Expected Result**: Task created with auto-incremented ID, all fields preserved
- **Status**: Not Run

#### TC_DB_008: Retrieve Task by ID
- **Component**: database.py
- **Function**: `get_task()`
- **Type**: Unit
- **Description**: Fetch task details by task_id
- **Prerequisites**: Task exists in database
- **Test Data**: `task_id=5, user_id=123456`
- **Expected Result**: Returns dict with task data (id, title, description, status, category, priority, deadline, etc.)
- **Status**: Not Run

#### TC_DB_009: Retrieve Task from Another User
- **Component**: database.py
- **Function**: `get_task()`
- **Type**: Unit
- **Description**: Attempt to access task from another user (permissions check)
- **Prerequisites**: Task belongs to different user
- **Test Data**: `task_id=5, user_id=999999` (wrong user)
- **Expected Result**: Returns None (no cross-user access)
- **Status**: Not Run

#### TC_DB_010: List User Tasks with Filters
- **Component**: database.py
- **Function**: `get_user_tasks()`
- **Type**: Unit
- **Description**: Retrieve all pending tasks for a user, sorted by priority
- **Prerequisites**: User has multiple tasks with different statuses
- **Test Data**: `user_id=123456, status="pending"`
- **Expected Result**: Returns list of pending tasks sorted by priority (high→medium→low), excluding cancelled
- **Status**: Not Run

#### TC_DB_011: Filter Tasks by Category
- **Component**: database.py
- **Function**: `get_user_tasks()`
- **Type**: Unit
- **Description**: Retrieve tasks filtered by category
- **Prerequisites**: User has tasks in multiple categories
- **Test Data**: `user_id=123456, category="work"`
- **Expected Result**: Returns only "work" category tasks
- **Status**: Not Run

#### TC_DB_012: Update Task Status
- **Component**: database.py
- **Function**: `update_task()`
- **Type**: Unit
- **Description**: Change task status from pending to done
- **Prerequisites**: Task exists with status="pending"
- **Test Data**: `task_id=5, user_id=123456, status="done"`
- **Expected Result**: Task status updated, updated_at timestamp refreshed
- **Status**: Not Run

#### TC_DB_013: Delete Task
- **Component**: database.py
- **Function**: `delete_task()`
- **Type**: Unit
- **Description**: Remove a task from database
- **Prerequisites**: Task exists in database
- **Test Data**: `task_id=5, user_id=123456`
- **Expected Result**: Task deleted successfully, returns True; subsequent get_task returns None
- **Status**: Not Run

#### TC_DB_014: Mark Task as Reminded
- **Component**: database.py
- **Function**: `mark_task_reminded()`
- **Type**: Unit
- **Description**: Update reminded_at timestamp when reminder is sent
- **Prerequisites**: Task exists, has upcoming deadline
- **Test Data**: `task_id=5`
- **Expected Result**: reminded_at timestamp set to current time
- **Status**: Not Run

#### TC_DB_015: Get User Statistics
- **Component**: database.py
- **Function**: `get_user_stats()`
- **Type**: Unit
- **Description**: Retrieve task statistics (total, done, pending, overdue)
- **Prerequisites**: User has tasks with various statuses and deadlines
- **Test Data**: `user_id=123456`
- **Expected Result**: Returns dict with {total, done, pending, overdue, completion_rate}
- **Status**: Not Run

---

## 2. AI SERVICE MODULE (ai_service.py)

#### TC_AI_001: Parse Task from Natural Language
- **Component**: ai_service.py
- **Function**: `parse_task_from_text()`
- **Type**: Unit
- **Description**: Parse natural language task description into structured fields
- **Prerequisites**: Gemini API key configured
- **Test Data**: `text="Submit quarterly report by Friday, urgent"`
- **Expected Result**: Returns dict with {title, description, category, priority, deadline}; category="work", priority="high", deadline is Friday 09:00
- **Status**: Not Run

#### TC_AI_002: Parse Task with Category Inference
- **Component**: ai_service.py
- **Function**: `parse_task_from_text()`
- **Type**: Unit
- **Description**: Verify correct category inference from context
- **Prerequisites**: Gemini API key configured
- **Test Data**: `text="Study for math exam next Monday morning"`
- **Expected Result**: category="study" inferred correctly, deadline set to Monday 09:00
- **Status**: Not Run

#### TC_AI_003: Parse Task with Invalid Input
- **Component**: ai_service.py
- **Function**: `parse_task_from_text()`
- **Type**: Unit
- **Description**: Handle malformed or unclear input gracefully
- **Prerequisites**: Gemini API key configured
- **Test Data**: `text="xyz abc 123 !@#"`
- **Expected Result**: Returns None or partial data with fallbacks
- **Status**: Not Run

#### TC_AI_004: API Error Handling
- **Component**: ai_service.py
- **Function**: `parse_task_from_text()`
- **Type**: Unit
- **Description**: Handle Gemini API errors gracefully
- **Prerequisites**: API key invalid or rate limited
- **Test Data**: Invalid API response or timeout
- **Expected Result**: Logs error, returns None, doesn't crash bot
- **Status**: Not Run

#### TC_AI_005: Generate Daily Motivation
- **Component**: ai_service.py
- **Function**: `generate_daily_motivation()`
- **Type**: Unit
- **Description**: Generate motivational message based on user stats
- **Prerequisites**: Gemini API configured, user has stats
- **Test Data**: `stats={total: 10, done: 8, pending: 2, overdue: 0}`
- **Expected Result**: Returns motivational string relevant to productivity
- **Status**: Not Run

#### TC_AI_006: Motivational Message on Low Activity
- **Component**: ai_service.py
- **Function**: `generate_daily_motivation()`
- **Type**: Unit
- **Description**: Generate appropriate message when few tasks completed
- **Prerequisites**: Gemini API configured
- **Test Data**: `stats={total: 5, done: 1, pending: 4, overdue: 1}`
- **Expected Result**: Returns encouraging/supportive message
- **Status**: Not Run

---

## 3. FORMATTERS MODULE (formatters.py)

#### TC_FMT_001: MarkdownV2 Escape Special Characters
- **Component**: formatters.py
- **Function**: `escape_md()`
- **Type**: Unit
- **Description**: Escape all special characters for Telegram MarkdownV2
- **Prerequisites**: N/A
- **Test Data**: `text="Hello *world* [link](url) _italic_"`
- **Expected Result**: All special chars escaped: `"Hello \\*world\\* \\[link\\]\\(url\\) \\_italic\\_"`
- **Status**: Not Run

#### TC_FMT_002: Escape Empty String
- **Component**: formatters.py
- **Function**: `escape_md()`
- **Type**: Unit
- **Description**: Handle empty string input
- **Prerequisites**: N/A
- **Test Data**: `text=""`
- **Expected Result**: Returns empty string
- **Status**: Not Run

#### TC_FMT_003: Format Task Card
- **Component**: formatters.py
- **Function**: `format_task_card()`
- **Type**: Unit
. **Description**: Display task with all details formatted nicely
- **Prerequisites**: Task dict exists with all fields
- **Test Data**: Task: `{id: 5, title: "Submit report", category: "work", priority: "high", status: "pending", deadline: "2026-03-25"}`
- **Expected Result**: Formatted string with emoji, escaped title, priority, deadline, status indicators
- **Status**: Not Run

#### TC_FMT_004: Format Task List
- **Component**: formatters.py
- **Function**: `format_task_list()`
- **Type**: Unit
- **Description**: Display multiple tasks in list format
- **Prerequisites**: List of task dicts
- **Test Data**: List of 5 tasks with various priorities and statuses
- **Expected Result**: Formatted list with line breaks, each task with emoji indicators sorted by priority
- **Status**: Not Run

#### TC_FMT_005: Format Stats Message
- **Component**: formatters.py
- **Function**: `format_stats()`
- **Type**: Unit
- **Description**: Display productivity statistics in readable format
- **Prerequisites**: Stats dict with counts
- **Test Data**: `stats={total: 15, done: 10, pending: 4, overdue: 1, completion_rate: 67%}`
- **Expected Result**: Formatted stats with emoji, percentages, and clean layout
- **Status**: Not Run

#### TC_FMT_006: Format Deadline with Various States
- **Component**: formatters.py
- **Function**: `fmt_deadline()`
- **Type**: Unit
- **Description**: Display deadline in human-readable format (Today, Tomorrow, Overdue, etc.)
- **Prerequisites**: Deadline datetime strings
- **Test Data**: 
  - Today: `"2026-03-23T14:30:00"`
  - Tomorrow: `"2026-03-24T14:30:00"`
  - Overdue: `"2026-03-20T14:30:00"`
- **Expected Result**: Displays "Today", "Tomorrow", "Overdue", or relative days
- **Status**: Not Run

---

## 4. BOT HANDLERS MODULE (handlers.py)

### Command Handlers

#### TC_CMD_001: /start Command
- **Component**: handlers.py
- **Function**: `cmd_start()`
- **Type**: Integration
- **Description**: User starts bot for first time or returns
- **Prerequisites**: User not registered or previously registered
- **Test Data**: User: `id=123456, first_name="John", username="john_doe"`
- **Expected Result**: User registered/updated, welcome message with main menu sent, INFO log entry
- **Status**: Not Run

#### TC_CMD_002: /help Command
- **Component**: handlers.py
- **Function**: `cmd_help()`
- **Type**: Integration
- **Description**: Display help and command reference
- **Prerequisites**: User registered
- **Test Data**: User invokes /help command
- **Expected Result**: Help message with command list and main menu keyboard sent, INFO log entry
- **Status**: Not Run

#### TC_CMD_003: /addtask Conversation (Manual Flow)
- **Component**: handlers.py
- **Function**: `build_addtask_handler()`
- **Type**: Integration
- **Description**: Complete task creation step-by-step conversation
- **Prerequisites**: User registered
- **Test Data**: 
  - Step 1 Title: "Finish report"
  - Step 2 Description: "Q1 quarterly report"
  - Step 3 Category: "Work"
  - Step 4 Priority: "High"
  - Step 5 Deadline: "2026-03-25 14:00"
- **Expected Result**: Task created with all fields, confirmation message with task card sent, INFO log
- **Status**: Not Run

#### TC_CMD_004: /addtask Skip Description
- **Component**: handlers.py
- **Function**: `build_addtask_handler()`
- **Type**: Integration
- **Description**: User skips optional description step
- **Prerequisites**: User in addtask conversation
- **Test Data**: User sends "⏭ Skip" at description step
- **Expected Result**: Description left empty, conversation continues to category
- **Status**: Not Run

#### TC_CMD_005: /addtask Invalid Deadline
- **Component**: handlers.py
- **Function**: `parse_deadline()`
- **Type**: Unit
- **Description**: User enters unparseable deadline format
- **Prerequisites**: User in addtask conversation at deadline step
- **Test Data**: User sends "xyz 123 invalid"
- **Expected Result**: WARNING log, error message with format hints sent, conversation re-prompts
- **Status**: Not Run

#### TC_CMD_006: /addtask_ai Natural Language
- **Component**: handlers.py
- **Function**: `build_addtask_ai_handler()`
- **Type**: Integration
- **Description**: Create task from single natural language input
- **Prerequisites**: User registered, Gemini API configured
- **Test Data**: User: "Buy groceries tomorrow at 5 PM"
- **Expected Result**: AI parses input, task created with parsed fields, confirmation sent, INFO log
- **Status**: Not Run

#### TC_CMD_007: /mytasks Display All
- **Component**: handlers.py
- **Function**: `cmd_mytasks()`
- **Type**: Integration
- **Description**: List all pending tasks with clickable buttons
- **Prerequisites**: User has pending tasks
- **Test Data**: User with 5 pending tasks of mixed priorities
- **Expected Result**: Numbered list with clickable task buttons, sorted by priority
- **Status**: Not Run

#### TC_CMD_008: /mytasks Empty List
- **Component**: handlers.py
- **Function**: `cmd_mytasks()`
- **Type**: Integration
- **Description**: Handle user with no pending tasks
- **Prerequisites**: User has no pending tasks
- **Test Data**: User with 0 pending tasks
- **Expected Result**: Message "No pending tasks" displayed
- **Status**: Not Run

#### TC_CMD_009: /done Command
- **Component**: handlers.py
- **Function**: `cmd_done()`
- **Type**: Integration
- **Description**: Mark task as completed via command
- **Prerequisites**: Task exists and is pending
- **Test Data**: User sends `/done 5` for task ID 5
- **Expected Result**: Task status changed to "done", confirmation message sent, INFO log
- **Status**: Not Run

#### TC_CMD_010: /done Invalid Task ID
- **Component**: handlers.py
- **Function**: `cmd_done()`
- **Type**: Integration
- **Description**: User provides non-existent task ID
- **Prerequisites**: Task does not exist
- **Test Data**: User sends `/done 99999`
- **Expected Result**: Error message "Task not found" sent, WARNING log
- **Status**: Not Run

#### TC_CMD_011: /stats Command
- **Component**: handlers.py
- **Function**: `cmd_stats()`
- **Type**: Integration
- **Description**: Display user productivity statistics
- **Prerequisites**: User has tasks with various statuses
- **Test Data**: User: 15 total tasks, 10 done, 5 pending
- **Expected Result**: Stats formatted and sent, includes completion % and motivational message, INFO log
- **Status**: Not Run

#### TC_CMD_012: /settimezone Command
- **Component**: handlers.py
- **Function**: `cmd_settimezone()`
- **Type**: Integration
- **Description**: Allow user to set timezone for reminders
- **Prerequisites**: User registered
- **Test Data**: User selects "America/New_York"
- **Expected Result**: Timezone updated in database, confirmation sent, INFO log
- **Status**: Not Run

### Callback Handlers

#### TC_CB_001: Task View Button
- **Component**: handlers.py
- **Function**: `callback_task_view()`
- **Type**: Integration
- **Description**: Display task details when button tapped
- **Prerequisites**: Task exists, user owns task
- **Test Data**: User taps button for task ID 5
- **Expected Result**: Task card shown with Done/Edit/Delete buttons
- **Status**: Not Run

#### TC_CB_002: Task Done Button
- **Component**: handlers.py
- **Function**: `callback_task_done()`
- **Type**: Integration
- **Description**: Mark task complete via inline button
- **Prerequisites**: Task is pending
- **Test Data**: User taps "✅ Done" button on task
- **Expected Result**: Task status → "done", message updated, INFO log, user sees success emoji
- **Status**: Not Run

#### TC_CB_003: Task Delete Confirmation
- **Component**: handlers.py
- **Function**: `callback_task_delete()`
- **Type**: Integration
- **Description**: Show confirmation before deleting
- **Prerequisites**: Task exists
- **Test Data**: User taps "🗑️ Delete" button
- **Expected Result**: Confirmation message with "Yes, Delete" and "Cancel" buttons shown
- **Status**: Not Run

#### TC_CB_004: Task Delete Confirmed
- **Component**: handlers.py
- **Function**: `callback_task_delete_confirm()`
- **Type**: Integration
- **Description**: Permanently remove task after confirmation
- **Prerequisites**: User confirmed deletion
- **Test Data**: User taps "🗑️ Yes, Delete" confirmation
- **Expected Result**: Task deleted, success message sent, INFO log
- **Status**: Not Run

#### TC_CB_005: Menu Filter - Pending
- **Component**: handlers.py
- **Function**: `callback_menu()`
- **Type**: Integration
- **Description**: Show only pending tasks when filter tapped
- **Prerequisites**: User has tasks in multiple statuses
- **Test Data**: User taps "⏳ Pending" menu button
- **Expected Result**: List shows only pending tasks
- **Status**: Not Run

#### TC_CB_006: Menu Filter - By Category
- **Component**: handlers.py
- **Function**: `callback_menu()`
- **Type**: Integration
- **Description**: Show only tasks in selected category
- **Prerequisites**: User has tasks in multiple categories
- **Test Data**: User taps "💼 Work" menu button
- **Expected Result**: List shows only work category tasks
- **Status**: Not Run

---

## 5. REMINDERS MODULE (reminders.py)

#### TC_REM_001: Deadline Reminder Scheduled
- **Component**: reminders.py
- **Function**: `check_deadlines()`
- **Type**: System
- **Description**: Bot sends reminder for task due within 30 minutes
- **Prerequisites**: Task deadline is 15 minutes from now, scheduler running
- **Test Data**: Task with deadline datetime = now + 15 minutes
- **Expected Result**: Reminder message sent to user, reminded_at timestamp set, INFO log
- **Status**: Not Run

#### TC_REM_002: Skip Already Reminded Task
- **Component**: reminders.py
- **Function**: `check_deadlines()`
- **Type**: System
- **Description**: Don't send duplicate reminders for same task
- **Prerequisites**: Task already has reminded_at timestamp
- **Test Data**: Task with old deadline and reminded_at set
- **Expected Result**: No duplicate reminder sent, WARNING log if applicable
- **Status**: Not Run

#### TC_REM_003: Daily Summary at User's 9 AM
- **Component**: reminders.py
- **Function**: `send_daily_summaries()`
- **Type**: System
- **Description**: Send daily summary at user's local 9 AM time
- **Prerequisites**: Scheduler running, user has tasks, user timezone set
- **Test Data**: Current time in user's timezone is 09:00 AM
- **Expected Result**: Summary message sent with stats and top tasks, INFO log
- **Status**: Not Run

#### TC_REM_004: Daily Summary Skip Inactive User
- **Component**: reminders.py
- **Function**: `send_daily_summaries()`
- **Type**: System
- **Description**: Don't send summary to user with no tasks
- **Prerequisites**: User exists but has no tasks
- **Test Data**: User with 0 tasks, current time is 09:00 AM their timezone
- **Expected Result**: No message sent to this user, summary sent to others
- **Status**: Not Run

#### TC_REM_005: Scheduler Start/Stop
- **Component**: reminders.py
- **Function**: `create_scheduler()`
- **Type**: System
- **Description**: Scheduler starts on bot init and stops gracefully on shutdown
- **Prerequisites**: Bot application initialized
- **Test Data**: Run bot, let it initialize, stop with Ctrl+C after 10 seconds
- **Expected Result**: INFO logs show "started" and "stopped", scheduler takes max 10 seconds to shutdown
- **Status**: Not Run

---

## 6. MANUAL TESTING (UI & END-TO-END)

### Bot Initialization & Basic Commands

#### TC_MAN_001: Bot Startup & /start Command
- **Type**: Manual
- **Description**: User launches bot for first time via Telegram
- **Prerequisites**: Bot running (`python run.py`), user has Telegram account
- **Actions**:
  1. Open Telegram app
  2. Search for TaskBot
  3. Tap "Start" button or type `/start`
  4. Verify welcome message displays
  5. Verify main menu keyboard appears with buttons
  6. Check: User can see ➕ Add Task, 🤖 Add with AI, 📋 My Tasks, 📊 Stats buttons
- **Expected Result**: 
  - Welcome message: "👋 Welcome, [Name]! I'm your AI-powered Task Manager..."
  - Main menu loads without errors
  - All buttons are clickable
  - No crashes or timeouts
- **Status**: Not Run

#### TC_MAN_002: /help Command
- **Type**: Manual
- **Description**: User requests help documentation
- **Prerequisites**: User registered, bot running
- **Actions**:
  1. Type `/help` or tap menu button
  2. Review help message display
  3. Verify all command categories listed
  4. Check menu buttons are present
  5. Tap different buttons from help menu
- **Expected Result**:
  - Help message displays: "📖 Help & Menu"
  - All command categories visible (Creating, Viewing, Filters, Category, Settings)
  - Menu keyboard appears below help text
  - Buttons navigate to correct functions
- **Status**: Not Run

#### TC_MAN_003: Return to Bot After /start
- **Type**: Manual
- **Description**: User returns to chat and bot still functional
- **Prerequisites**: User previously used `/start`
- **Actions**:
  1. Close Telegram app
  2. Reopen Telegram app
  3. Open TaskBot chat
  4. Type `/start` again
  5. Verify user greeting uses same name
- **Expected Result**:
  - User not registered twice (same user_id)
  - Last_active timestamp updated
  - Welcome message appears again
  - No duplicate user records
- **Status**: Not Run

---

### Task Creation - Manual Flow

#### TC_MAN_004: Create Task Step-by-Step (/addtask)
- **Type**: Manual
- **Description**: User creates task through conversational interface
- **Prerequisites**: Bot running, user registered
- **Actions**:
  1. Tap "➕ Add Task" button
  2. When prompted for title, type: `"Finish quarterly report"`
  3. When prompted for description, type: `"Complete Q1 2026 financial report with analysis"`
  4. Select category: Tap "💼 Work"
  5. Select priority: Tap "🔴 High"
  6. Enter deadline: Type `"2026-03-28 17:00"`
  7. Verify task card displays with all fields
  8. Tap action button on task card
- **Expected Result**:
  - Step 1: Prompt shows "📝 *New Task — Step 1/5* What's the task title?"
  - Step 2: Keyboard with category options appears
  - Step 3: Keyboard with priority options (High/Medium/Low) appears
  - Step 4: Deadline format accepted or error message with hints
  - Final: Task card shows ✅ Finish quarterly report, 💼 Work, 🔴 High, 📅 28 Mar 2026
  - Buttons "✅ Done", "✏️ Edit", "🗑️ Delete" appear below task
- **Status**: Not Run

#### TC_MAN_005: Skip Optional Description
- **Type**: Manual
- **Description**: User skips optional task description
- **Prerequisites**: In /addtask conversation
- **Actions**:
  1. Start /addtask flow
  2. Enter title: `"Buy groceries"`
  3. At description step, tap "⏭ Skip"
  4. Complete remaining steps
  5. Verify task card shows empty description
- **Expected Result**:
  - Description field skipped without error
  - Task created with empty description
  - Task card displays without description line
- **Status**: Not Run

#### TC_MAN_006: Invalid Deadline Formats
- **Type**: Manual
- **Description**: User enters unparseable deadline and sees helpful error
- **Prerequisites**: In /addtask deadline step
- **Actions**:
  1. Start /addtask, complete steps 1-4
  2. At deadline step, enter: `"tomorrow at 5 PM"` (valid)
  3. Verify it's accepted
  4. Create another task, try: `"xyz invalid 123"`
  5. Verify error message with format hints
  6. Try again with: `"2026-03-25 14:00"` (valid)
  7. Verify second attempt accepted
- **Expected Result**:
  - Valid formats accepted: "tomorrow", "today", "next Friday", "2026-03-25 14:00"
  - Invalid format shows: "I couldn't understand that date. Try one of these formats..."
  - Re-prompt appears for retry
  - User can correct and proceed
- **Status**: Not Run

#### TC_MAN_007: Cancel Task Creation
- **Type**: Manual
- **Description**: User aborts task creation mid-conversation
- **Prerequisites**: In /addtask conversation
- **Actions**:
  1. Start /addtask
  2. Enter title
  3. At description step, send: `/cancel` or similar
  4. Verify conversation ends
  5. Try sending `/help` to confirm bot still responsive
- **Expected Result**:
  - Conversation ends without creating task
  - No partial task saved
  - Bot returns to ready state
  - Subsequent commands work normally
- **Status**: Not Run

---

### Task Creation - AI Natural Language

#### TC_MAN_008: AI Task Creation - Simple Input
- **Type**: Manual
- **Description**: User creates task via natural language with AI parsing
- **Prerequisites**: Bot running, Gemini API configured
- **Actions**:
  1. Tap "🤖 Add with AI" button
  2. Type: `"Submit project proposal by Friday afternoon, high priority"`
  3. Wait for AI processing
  4. Verify parsed task details
  5. Confirm or edit as needed
- **Expected Result**:
  - AI extracts:
    - Title: "Submit project proposal"
    - Category: "work" (inferred)
    - Priority: "high"
    - Deadline: Friday 14:00 or 17:00
  - Task created with parsed values
  - Confirmation message displays
- **Status**: Not Run

#### TC_MAN_009: AI Task Creation - Complex Input
- **Type**: Manual
- **Description**: AI parses detailed natural language task
- **Prerequisites**: Gemini API configured
- **Actions**:
  1. Tap "🤖 Add with AI"
  2. Type: `"Study for chemistry exam on Monday morning, it's a midterm so urgent, also need to review chapters 5-8"`
  3. Wait for processing
  4. Verify extracted fields
- **Expected Result**:
  - Title: "Study for chemistry exam"
  - Category: "study" (inferred from context)
  - Priority: "high" (inferred from "urgent" and "midterm")
  - Deadline: Monday 09:00
  - Description: Contains extracted notes "review chapters 5-8"
- **Status**: Not Run

#### TC_MAN_010: AI Task Creation - Health/Finance Categories
- **Type**: Manual
- **Description**: Verify AI correctly categorizes health and finance tasks
- **Prerequisites**: Gemini API configured
- **Actions**:
  1. Create task: `"Have doctor appointment next Wednesday at 2 PM"` (should be health)
  2. Create task: `"Pay rent by March 27, important deadline"` (should be finance)
  3. Verify categories assigned correctly
- **Expected Result**:
  - Doctor appointment → category: "health"
  - Pay rent → category: "finance"
  - Priorities and deadlines correctly parsed
- **Status**: Not Run

---

### Task Management - Viewing & Filtering

#### TC_MAN_011: View All Tasks (/mytasks)
- **Type**: Manual
- **Description**: User views complete list of pending tasks
- **Prerequisites**: User has 3+ tasks, bot running
- **Actions**:
  1. Create 3 tasks with different priorities (high, medium, low)
  2. Mark one task as done
  3. Tap "📋 My Tasks"
  4. Verify list displays
  5. Check tasks are sorted by priority
- **Expected Result**:
  - List title: "📋 *Your Tasks*"
  - Tasks displayed as numbered buttons with emoji + ID + title
  - Sorted by priority: high (🔴) first, then medium (🟡), then low (🟢)
  - Done tasks NOT shown in pending view
  - Each task is clickable button
- **Status**: Not Run

#### TC_MAN_012: View Single Task Details
- **Type**: Manual
- **Description**: User taps task button to see full details
- **Prerequisites**: Tasks exist in list
- **Actions**:
  1. Create task: "Complete project proposal, work, high, 2026-03-28"
  2. Tap "📋 My Tasks"
  3. Tap task button from list
  4. Verify full task card displays
  5. Check all action buttons available
- **Expected Result**:
  - Task card shows:
    - Title with ✏️ edit icon
    - 📝 Description
    - 💼 Category
    - 🔴 Priority
    - ⏳ Status
    - 📅 Deadline (exact date/time)
  - Three action buttons below: ✅ Done | ✏️ Edit | 🗑️ Delete
- **Status**: Not Run

#### TC_MAN_013: Filter Tasks by Status
- **Type**: Manual
- **Description**: User filters task list by completion status
- **Prerequisites**: User has tasks in different statuses
- **Actions**:
  1. Create 3 tasks
  2. Mark 2 as done
  3. From main menu, tap "⏳ Pending"
  4. Verify only pending tasks shown
  5. Go back to menu, tap "✅ Done"
  6. Verify only done tasks shown
  7. Tap "🔄 In Progress"
  8. Verify in-progress tasks shown (or "No tasks" if none)
- **Expected Result**:
  - Pending filter shows only status="pending" tasks
  - Done filter shows only status="done" tasks
  - In Progress filter shows only status="in_progress" tasks
  - Each filter re-queries and updates list correctly
- **Status**: Not Run

#### TC_MAN_014: Filter Tasks by Category
- **Type**: Manual
- **Description**: User filters tasks by category from menu
- **Prerequisites**: Tasks in different categories exist
- **Actions**:
  1. Create tasks: "Submit report" (work), "Study math" (study), "Doctor appt" (health)
  2. From menu, tap "💼 Work"
  3. Verify only work tasks shown
  4. Go back, tap "📚 Study"
  5. Verify only study tasks shown
  6. Tap "❤️ Health"
  7. Verify only health tasks shown
- **Expected Result**:
  - Work filter shows only category="work" tasks
  - Study filter shows only category="study" tasks
  - Health filter shows only category="health" tasks
  - All other categories accessible and filtered correctly
- **Status**: Not Run

#### TC_MAN_015: Empty Task List
- **Type**: Manual
- **Description**: User views list when no matching tasks exist
- **Prerequisites**: User has no pending tasks or filtered results are empty
- **Actions**:
  1. Mark all tasks as done
  2. Tap "📋 My Tasks" or "⏳ Pending"
  3. Verify empty state message
- **Expected Result**:
  - Message displays: "No pending tasks" or similar friendly message
  - No crashes or empty white screen
  - "Back" or "Menu" button available to navigate
- **Status**: Not Run

---

### Task Actions - Mark Done, Edit, Delete

#### TC_MAN_016: Mark Task as Done via Button
- **Type**: Manual
- **Description**: User completes task using ✅ Done button
- **Prerequisites**: Pending task exists
- **Actions**:
  1. Create task: "Finish report"
  2. Tap "📋 My Tasks"
  3. Tap task to view details
  4. Tap "✅ Done" button
  5. Verify status changes in message
  6. View task list again
  7. Verify done task no longer in pending list
- **Expected Result**:
  - Message updates to: "🎉 *Marked as done!*"
  - Task card still shows but status = ✅ done
  - Task disappears from pending list
  - Reappears in "✅ Done" filter
  - Completion rate in stats increases
- **Status**: Not Run

#### TC_MAN_017: Mark Task as Done via Command
- **Type**: Manual
- **Description**: User marks task done using command
- **Prerequisites**: Task exists with known ID
- **Actions**:
  1. Create task, note ID from confirmation
  2. Type `/done 1` (or correct task ID)
  3. Verify task marked done
  4. Confirm in task list
- **Expected Result**:
  - Command accepted: `/done <id>`
  - Task status changes to done
  - Confirmation message sent
  - Task removed from pending view
- **Status**: Not Run

#### TC_MAN_018: Edit Task via Edit Button
- **Type**: Manual
- **Description**: User modifies task details after creation
- **Prerequisites**: Pending task exists
- **Actions**:
  1. Create task: "Study math, deadline 2026-03-25"
  2. Tap task to view
  3. Tap "✏️ Edit" button
  4. Change deadline to "2026-03-26 14:00"
  5. Confirm edit
  6. View task again
  7. Verify deadline updated
- **Expected Result**:
  - Edit prompt: "What would you like to edit?"
  - Options to edit: Title, Description, Category, Priority, Deadline, Status
  - User selects field and provides new value
  - Task updated in database
  - Task card shows new values
- **Status**: Not Run

#### TC_MAN_019: Delete Task with Confirmation
- **Type**: Manual
- **Description**: User deletes task with safety confirmation
- **Prerequisites**: Task exists
- **Actions**:
  1. Create task
  2. Tap task to view
  3. Tap "🗑️ Delete" button
  4. Verify confirmation prompt appears
  5. Tap "↩️ Cancel" button
  6. Verify task still exists
  7. Tap "🗑️ Delete" again
  8. Tap "🗑️ Yes, Delete" button
  9. Verify task deleted
- **Expected Result**:
  - Step 3: Confirmation message: "Are you sure? This cannot be undone."
  - Step 4: Cancel returns to task view
  - Step 8: Confirmation message: "🗑️ Task #X deleted."
  - Step 9: Task no longer appears in any list
- **Status**: Not Run

#### TC_MAN_020: Task Not Found Error
- **Type**: Manual
- **Description**: User attempts operation on non-existent task
- **Prerequisites**: No tasks created
- **Actions**:
  1. Type `/done 9999`
  2. Verify error message
  3. Try viewing task from empty list
  4. Verify appropriate error
- **Expected Result**:
  - Error message: "⚠️ Task not found" or similar
  - No crashes
  - Bot remains responsive
- **Status**: Not Run

---

### Productivity Features - Stats & Reminders

#### TC_MAN_021: View Productivity Stats
- **Type**: Manual
- **Description**: User views stats dashboard with motivation
- **Prerequisites**: User has multiple tasks in various statuses
- **Actions**:
  1. Create 10 tasks
  2. Mark 7 as done
  3. Let 1 deadline pass (overdue)
  4. Tap "📊 Stats" from menu
  5. Review stats display
  6. Check motivational message
- **Expected Result**:
  - Stats display shows:
    - ✅ Done: `7`
    - ⏳ Pending: `2`
    - ⚠️ Overdue: `1`
    - Completion rate: `70%`
  - Motivational message from AI: "You're on fire! Keep it up..." or similar
  - Message updates with each stats check
- **Status**: Not Run

#### TC_MAN_022: Deadline Reminders (10-minute check)
- **Type**: Manual
- **Description**: Bot sends reminder when task deadline approaches
- **Prerequisites**: Scheduler running, task with deadline 15 min from now
- **Actions**:
  1. Create task: "Finish slides", deadline = now + 15 minutes
  2. Wait 10+ minutes
  3. Check if reminder message arrives
  4. Verify reminder contains task title and deadline
  5. Ensure reminder only sent once
- **Expected Result**:
  - Reminder message: "⏰ *Deadline Reminder!*"
  - Contains task title and deadline time
  - Message includes "Use /done <id> to mark complete"
  - Reminder sent exactly once (not repeated)
- **Status**: Not Run

#### TC_MAN_023: Daily Summary (Morning Digest)
- **Type**: Manual
- **Description**: User receives daily task summary at 9 AM local time
- **Prerequisites**: Timezone set, scheduler running, has pending tasks
- **Actions**:
  1. Set timezone to local time: `/settimezone` → select your timezone
  2. Create 5 pending tasks
  3. Wait until your local 9:00 AM
  4. Verify morning summary arrives
  5. Check message content
- **Expected Result**:
  - Message arrives at 9:00 AM user's timezone
  - Shows: "☀️ *Good morning, [Name]!*"
  - Displays: ✅ Done count, ⏳ Pending count, ⚠️ Overdue count
  - Lists top 5 pending tasks with priorities
  - Includes motivational message
- **Status**: Not Run

#### TC_MAN_024: Set Timezone for Reminders
- **Type**: Manual
- **Description**: User configures timezone for daily summaries
- **Prerequisites**: Bot running
- **Actions**:
  1. Type `/settimezone` or tap "⚙️ Set Timezone"
  2. Verify timezone list appears
  3. Select your timezone, e.g., "America/New_York"
  4. Verify confirmation message
  5. Check user profile (via /help menu)
- **Expected Result**:
  - Timezone selection keyboard appears with common zones
  - Selection confirmed: "✅ Timezone set to America/New_York"
  - Future reminders use this timezone
  - Setting persists across sessions
- **Status**: Not Run

---

### UI/UX Validation

#### TC_MAN_025: Text Escaping & Markdown Display
- **Type**: Manual
- **Description**: Special characters in task titles display correctly
- **Prerequisites**: Task creation capability
- **Actions**:
  1. Create task: "Fix bug: [TypeError] in parser (v2.0)*"
  2. Create task: "Meeting with CEO & CTO @ office"
  3. View tasks in list
  4. View in task card
  5. Check formatting in stats message
- **Expected Result**:
  - Special characters (*, [], (), @, &, etc.) display safely
  - No MarkdownV2 parsing errors
  - Text readable and properly escaped
  - Emoji and Unicode characters work correctly
- **Status**: Not Run

#### TC_MAN_026: Emoji Display & Visual Clarity
- **Type**: Manual
- **Description**: Emoji indicators display correctly across features
- **Prerequisites**: Create tasks with different priority/category/status
- **Actions**:
  1. Create: High priority → see 🔴 High
  2. Create: Medium → see 🟡 Medium
  3. Create: Low → see 🟢 Low
  4. Create: Work category → see 💼 Work
  5. Create: Study category → see 📚 Study
  6. Mark done → see ✅ done
  7. Check stats → verify emoji displays
- **Expected Result**:
  - All emoji render correctly on Telegram
  - Priority emoji consistent: 🔴 high, 🟡 medium, 🟢 low
  - Category emoji distinct and recognizable
  - Status emoji clear: ✅ done, ⏳ pending, 🔄 in_progress
- **Status**: Not Run

#### TC_MAN_027: Long Text Truncation
- **Type**: Manual
- **Description**: Very long task titles/descriptions display properly
- **Prerequisites**: Task creation capability
- **Actions**:
  1. Create task with title 100+ characters
  2. Create task with description 500+ characters
  3. View in task list (buttons)
  4. View in full task card
  5. Check if truncated appropriately in list
- **Expected Result**:
  - Task list buttons truncate title: "This is a very long task ti..." (showing ~35 chars)
  - Full task card shows complete title
  - Description wrapped/readable
  - No broken formatting
- **Status**: Not Run

#### TC_MAN_028: Keyboard Navigation
- **Type**: Manual
- **Description**: All buttons and keyboards are responsive and clickable
- **Prerequisites**: Using Telegram mobile or web
- **Actions**:
  1. Tap "➕ Add Task" button
  2. Select category from keyboard → Tap "💼 Work"
  3. Select priority from keyboard → Tap "🔴 High"
  4. From task view, tap "✅ Done"
  5. From task list, tap task button
  6. From menu, tap filter button
- **Expected Result**:
  - All buttons click-responsive
  - Keyboard selections register immediately
  - Inline buttons (Done/Edit/Delete) work
  - No stuck states or unresponsive buttons
- **Status**: Not Run

---

### Error Handling & Edge Cases

#### TC_MAN_029: Bot Command Without Arguments
- **Type**: Manual
- **Description**: User sends command missing required info
- **Prerequisites**: Bot running
- **Actions**:
  1. Type `/done` (without task ID)
  2. Type `/mytask` (without ID)
  3. Check error messages
- **Expected Result**:
  - Error message shows proper usage: "Usage: /done <task_id>"
  - User guided on correct format
  - Bot doesn't crash
- **Status**: Not Run

#### TC_MAN_030: Rapid Clicks
- **Type**: Manual
- **Description**: User rapidly clicks buttons multiple times
- **Prerequisites**: Task exists with action buttons
- **Actions**:
  1. View task card with ✅ Done button
  2. Rapidly click "✅ Done" button 5 times
  3. Verify message updates once
  4. Click "✅ Done" again on already-done task
  5. Check response
- **Expected Result**:
  - First click marks done
  - Rapid clicks don't create duplicates
  - Subsequent clicks on done task show: "Already marked as done"
  - No database corruption
- **Status**: Not Run

#### TC_MAN_031: Very Large Task List
- **Type**: Manual
- **Description**: User has many tasks in one category
- **Prerequisites**: Create 50+ tasks
- **Actions**:
  1. Create 50+ pending tasks
  2. Tap "📋 My Tasks"
  3. Verify list loads (may paginate)
  4. Scroll through list
  5. Verify all tasks accessible
  6. Tap different tasks
- **Expected Result**:
  - List loads without excessive delay
  - All tasks eventually visible (with pagination or scrolling)
  - Can click any task regardless of position
  - Bot performance acceptable
- **Status**: Not Run

#### TC_MAN_032: Multiple Category/Priority Filters
- **Type**: Manual
- **Description**: User filters by status AND category together
- **Prerequisites**: Tasks exist in multiple categories with various statuses
- **Actions**:
  1. Filter by "⏳ Pending" (shows all pending)
  2. Then tap "💼 Work" (should show pending work tasks only)
  3. Verify intersection works correctly
- **Expected Result**:
  - Shows only tasks matching BOTH filters
  - Using category filter refreshes from current status
  - User can clear filters via menu
- **Status**: Not Run

---

### Session & Data Management

#### TC_MAN_033: Session Persistence
- **Type**: Manual
- **Description**: User data persists across Telegram sessions
- **Prerequisites**: Create multiple tasks
- **Actions**:
  1. Create 3 tasks in bot
  2. Close Telegram app completely
  3. Reopen Telegram
  4. Open TaskBot chat
  5. Tap "📋 My Tasks"
  6. Verify all 3 tasks still present
- **Expected Result**:
  - All tasks saved in database
  - No data loss after app close
  - Task details (title, deadline, priority) intact
- **Status**: Not Run

#### TC_MAN_034: Multi-User Isolation
- **Type**: Manual
- **Description**: Different users see only their own tasks
- **Prerequisites**: 2 user accounts available
- **Actions**:
  1. User A: Create task "User A's secret task"
  2. User B: Create task "User B's secret task"
  3. User A: View "📋 My Tasks"
  4. Verify only User A's task shown
  5. User B: View "📋 My Tasks"
  6. Verify only User B's task shown
- **Expected Result**:
  - Each user sees only their tasks
  - No cross-user data leakage
  - User can't access other user's tasks by ID guessing
- **Status**: Not Run

#### TC_MAN_035: Database Integrity After Restart
- **Type**: Manual
- **Description**: Bot restart doesn't corrupt data
- **Prerequisites**: Bot running with data
- **Actions**:
  1. Create task A with deadline
  2. Mark task B as done
  3. Delete task C
  4. Stop bot: `Ctrl+C`
  5. Restart bot: `python run.py`
  6. Check all data preserved
- **Expected Result**:
  - Task A deadline unchanged
  - Task B still marked done
  - Task C deletion persists
  - No rollback of changes
  - Database file intact
- **Status**: Not Run

---

### Performance & Stability

#### TC_MAN_036: Message Load Time
- **Type**: Manual
- **Description**: Bot responds quickly to user actions
- **Prerequisites**: Bot running with data
- **Actions**:
  1. Tap "📋 My Tasks" with 20+ tasks
  2. Note response time (should be <2 seconds)
  3. Tap task to view details
  4. Note response time
  5. Create new task via /addtask
  6. Note each step completes in <1 second
- **Expected Result**:
  - Task list loads: <2 seconds
  - Task view displays: <1 second
  - Each conversation step: <1 second
  - No noticeable delays
- **Status**: Not Run

#### TC_MAN_037: Concurrent Command Processing
- **Type**: Manual
- **Description**: Bot handles rapid successive commands
- **Prerequisites**: Bot running
- **Actions**:
  1. Rapidly send multiple commands:
     - `/stats`
     - Tap "📋 My Tasks"
     - `/help`
     - Tap "💼 Work"
  2. Verify each command processes
  3. Check no messages duplicated or lost
- **Expected Result**:
  - All commands process in order
  - No message loss
  - Bot doesn't skip or ignore commands
  - Order maintained
- **Status**: Not Run

#### TC_MAN_038: Extended Session Stability
- **Type**: Manual
- **Description**: Bot remains stable during long interaction
- **Prerequisites**: Bot initialized
- **Actions**:
  1. Keep bot running for 30+ minutes
  2. Create multiple tasks gradually
  3. Mark some done
  4. Filter by different categories
  5. Check stats multiple times
  6. Reconnect and check again
- **Expected Result**:
  - No memory leaks or crashes
  - Bot responsive throughout
  - Data consistent after 30+ minutes
  - Scheduler still functions (reminders fire)
- **Status**: Not Run

---

### Network & Error Recovery

#### TC_MAN_039: Network Interruption Recovery
- **Type**: Manual
- **Description**: Bot recovers gracefully if internet briefly drops
- **Prerequisites**: Bot running
- **Actions**:
  1. Temporarily disable WiFi/data
  2. Try to send command in Telegram
  3. Re-enable connection
  4. Observe bot behavior
- **Expected Result**:
  - Telegram shows "Sending..." state
  - Message eventually sends when reconnected
  - Bot processes without error
  - No data corruption
- **Status**: Not Run

#### TC_MAN_040: Timeout Handling (API delays)
- **Type**: Manual
- **Description**: Bot handles slow Gemini API responses gracefully
- **Prerequisites**: Bot running, AI feature enabled
- **Actions**:
  1. Use "🤖 Add with AI" feature
  2. If API is slow, observe handling
  3. Wait for response
  4. Verify no timeout/crash message shown to user
- **Expected Result**:
  - Bot waits for API response
  - May show "Processing..." indicator
  - Returns after reasonable timeout (10+ seconds)
  - Shows error gracefully if API fails
- **Status**: Not Run

---

## Test Summary

| Category | Count | Type | Status |
|----------|-------|------|--------|
| Initialization & Commands | 3 | Manual | Not Run |
| Task Creation - Manual | 4 | Manual | Not Run |
| Task Creation - AI | 4 | Manual | Not Run |
| Task Management - Viewing & Filtering | 5 | Manual | Not Run |
| Task Actions - Done/Edit/Delete | 5 | Manual | Not Run |
| Productivity Features - Stats & Reminders | 4 | Manual | Not Run |
| UI/UX Validation | 4 | Manual | Not Run |
| Error Handling & Edge Cases | 4 | Manual | Not Run |
| Session & Data Management | 3 | Manual | Not Run |
| Performance & Stability | 3 | Manual | Not Run |
| Network & Error Recovery | 2 | Manual | Not Run |
| **Total Manual Tests** | **41** | **Manual** | **Not Run** |

---

## Manual Testing Guide

### Overview
Since this project focuses on **manual UI testing only**, all 41 test cases must be executed manually via Telegram. This document provides step-by-step instructions for testers to validate each feature.

### Testing Environment Setup

**Requirements:**
1. Bot running: `python run.py`
2. .env file configured with:
   - `TELEGRAM_BOT_TOKEN`
   - `GEMINI_API_KEY`
3. Telegram app on phone or web
4. Bot username/token ready
5. Test user account (can be personal Telegram account)
6. Database initialized (creates on first run)

### How to Execute Tests

**For Each Test Case:**
1. Read the **Description** to understand what is being tested
2. Verify **Prerequisites** are met (bot running, data setup, etc.)
3. Follow **Actions** step-by-step in order
4. Compare actual result with **Expected Result**
5. Mark **Status**: Pass ✅ or Fail ❌
6. Record any issues or unexpected behavior in notes

**Test Execution Checklist:**
- [ ] Bot initialized without errors
- [ ] All commands recognized
- [ ] UI displays correctly with emoji and formatting
- [ ] No crashes or timeout errors
- [ ] Data persists across sessions
- [ ] User isolation maintained (no data leaks)

### Tools for Manual Testing

| Tool | Purpose |
|------|---------|
| **Telegram Mobile** | Primary UI testing platform |
| **Telegram Web** | Alternative browser-based testing |
| **SQLite Browser** | View/verify database changes |
| **Bot Logs** | Monitor INFO/WARNING/ERROR messages |
| **Timer/Stopwatch** | Measure response times |

### Common Test Scenarios

#### Positive Testing (What Should Work)
- Valid task creation with all fields
- Editing existing tasks
- Filtering by multiple criteria
- Natural language AI parsing
- Reminder scheduling

#### Negative Testing (What Should Fail Gracefully)
- Invalid deadline formats → shows error with hints
- Non-existent task IDs → shows "Task not found"
- Missing command arguments → shows usage format
- Rapid clicks → no duplicates created
- Very long text → truncates or wraps appropriately

### Logging & Verification

**Check log file for entries:**
```bash
logs/bot.log
```

Expected log entries:
- INFO: "User @username (ID: 123456) started the bot"
- INFO: "Task created: ID=5, user=123456, title='...'"
- INFO: "Task marked as done: ID=5, user=123456"
- WARNING: "Invalid deadline input from user 123456: '...'"
- ERROR: "[DB] create_task failed for user 123456: ..."

### Test Data Scenarios

**Setup for comprehensive testing:**

**Scenario 1: Single User, Multiple Tasks**
- Create 10 tasks with varied priorities (high, medium, low)
- Create tasks with different categories (work, study, personal, health, finance)
- Set different statuses (pending, done, in_progress)
- Include overdue, today, and future deadlines

**Scenario 2: Multi-User Testing**
- Use 2+ Telegram accounts
- Verify data isolation
- Test concurrent operations
- Check that each user sees only their tasks

**Scenario 3: Edge Cases**
- Very long task titles (100+ chars)
- Special characters: * [ ] ( ) ~ ` > # + - = | { } . !
- Unicode emoji: 😀 中文 العربية
- Empty descriptions (test skip functionality)
- Rapid clicks and multi-step operations

### Reporting Test Results

**Test Status Format:**
- **Not Run**: Test not yet executed
- **In Progress**: Test currently being executed
- **Pass ✅**: All expected results verified
- **Fail ❌**: One or more issues found

**For Failed Tests, Record:**
1. What action triggered the failure
2. Expected vs actual result
3. Error messages shown
4. Steps to reproduce
5. Severity (Critical / High / Medium / Low)

### Execution Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Core Features** | Day 1 | TC_MAN_001-020 (Initialization, Task Creation, Management) |
| **Phase 2: Advanced Features** | Day 2 | TC_MAN_021-028 (Stats, Reminders, UI, Formatting) |
| **Phase 3: Robustness** | Day 3 | TC_MAN_029-040 (Errors, Edge Cases, Performance, Network) |
| **Phase 4: Review & Report** | Day 4 | Document findings, create test execution report |

### Success Criteria for Testing

✅ **Pass threshold:** 95%+ manual tests pass
✅ **Critical bugs:** 0 (must be fixed before release)
✅ **High severity bugs:** ≤2 (documented for future release)
✅ **No data loss:** Verified data persistence across restarts
✅ **User isolation:** Confirmed no cross-user data access
✅ **Response times:** <2 seconds for all operations
✅ **Stability:** No crashes during extended session
