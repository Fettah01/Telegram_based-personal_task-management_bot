"""
app/services/ai_service.py — Google Gemini-powered features with request/token logging:
  • Natural language task parsing
  • Auto-categorization
  • Priority prediction
  • Daily motivation messages
  • DETAILED REQUEST/RESPONSE LOGGING
  • TOKEN USAGE TRACKING
  • COST ESTIMATION

Uses: google-genai (Google AI Studio / Gemini API)
"""

import asyncio
import json
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import google.genai as genai
from google.genai.types import GenerateContentConfig

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  TOKEN & COST TRACKING
# ─────────────────────────────────────────────

class TokenTracker:
    """Track token usage across all Gemini API calls."""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.request_count = 0
        self.start_time = datetime.now()
        
    def add(self, input_tokens: int, output_tokens: int):
        """Log a request's token usage."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.request_count += 1
    
    def total_tokens(self) -> int:
        """Get cumulative token count."""
        return self.total_input_tokens + self.total_output_tokens
    
    def estimate_cost(self) -> Dict[str, float]:
        """
        Estimate API cost based on gemini-2.0-flash pricing.
        (Update these rates based on your actual Gemini pricing tier)
        """
        # Pricing per 1M tokens (adjust to your plan)
        input_cost_per_1m = 0.075   # $0.075 per 1M input tokens
        output_cost_per_1m = 0.30   # $0.30 per 1M output tokens
        
        input_cost = (self.total_input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (self.total_output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost
        
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
        }
    
    def get_stats(self) -> str:
        """Return formatted statistics."""
        elapsed = datetime.now() - self.start_time
        cost = self.estimate_cost()
        
        return (
            f"\n{'='*60}\n"
            f"📊 AI SERVICE STATISTICS\n"
            f"{'='*60}\n"
            f"Total Requests:        {self.request_count}\n"
            f"Input Tokens:          {self.total_input_tokens:,}\n"
            f"Output Tokens:         {self.total_output_tokens:,}\n"
            f"Total Tokens:          {self.total_tokens():,}\n"
            f"Estimated Cost:        ${cost['total_cost']:.6f}\n"
            f"  ├─ Input:   ${cost['input_cost']:.6f}\n"
            f"  └─ Output:  ${cost['output_cost']:.6f}\n"
            f"Elapsed Time:          {elapsed}\n"
            f"Avg Tokens/Request:    {self.total_tokens() // max(self.request_count, 1)}\n"
            f"{'='*60}\n"
        )


# Global tracker instance
_token_tracker = TokenTracker()


def get_token_stats() -> str:
    """Get current token statistics."""
    return _token_tracker.get_stats()


# ─────────────────────────────────────────────
#  Lazy client — initialized on first use
# ─────────────────────────────────────────────

_client: "genai.Client | None" = None


def _get_client() -> genai.Client:
    """Return the shared Gemini client, creating it on first call with key guard."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. "
                "Add it to your .env file and restart the bot."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# ─────────────────────────────────────────────
#  TOKEN COUNTING
# ─────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Rough estimate: ~1 token per 4 characters (for English)
    More accurate: use Gemini's built-in token counter if available
    """
    # Conservative estimate: 1 token ≈ 4 characters
    return max(1, len(text) // 4)


# ─────────────────────────────────────────────
#  CORE GEMINI CALL with LOGGING
# ─────────────────────────────────────────────

async def _gemini(
    prompt: str, 
    temperature: float = 0.2,
    function_name: str = "unknown"
) -> str:
    """
    Send a prompt to Gemini and return the text response.
    Logs all requests, responses, and token usage.
    """
    request_id = datetime.now().strftime("%H%M%S.%f")[:-3]  # HH:MM:SS.ms
    
    # Estimate input tokens
    input_tokens = count_tokens(prompt)
    
    logger.info(
        f"\n{'='*70}\n"
        f"🔵 AI REQUEST #{request_id} — {function_name}\n"
        f"{'='*70}\n"
        f"Model:        {GEMINI_MODEL}\n"
        f"Temperature:  {temperature}\n"
        f"Prompt Size:  {len(prompt)} chars\n"
        f"Est. Input Tokens: {input_tokens}\n"
        f"{'-'*70}\n"
        f"PROMPT:\n{'-'*70}\n"
        f"{prompt[:500]}"
        f"{'...[truncated]' if len(prompt) > 500 else ''}\n"
        f"{'-'*70}\n"
    )
    
    def _call():
        response = _get_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=512,
            ),
        )
        return response.text.strip()

    try:
        loop = asyncio.get_running_loop()
        response_text = await loop.run_in_executor(None, _call)
        
        # Estimate output tokens
        output_tokens = count_tokens(response_text)
        
        # Track tokens
        _token_tracker.add(input_tokens, output_tokens)
        
        logger.info(
            f"{'='*70}\n"
            f"🟢 AI RESPONSE #{request_id} — SUCCESS\n"
            f"{'='*70}\n"
            f"Response Size: {len(response_text)} chars\n"
            f"Est. Output Tokens: {output_tokens}\n"
            f"Total Tokens (this call): {input_tokens + output_tokens}\n"
            f"Cumulative Tokens: {_token_tracker.total_tokens():,}\n"
            f"{'-'*70}\n"
            f"RESPONSE:\n{'-'*70}\n"
            f"{response_text[:500]}"
            f"{'...[truncated]' if len(response_text) > 500 else ''}\n"
            f"{'-'*70}\n"
        )
        
        return response_text
        
    except Exception as e:
        logger.error(
            f"\n{'='*70}\n"
            f"🔴 AI REQUEST FAILED #{request_id}\n"
            f"{'='*70}\n"
            f"Function: {function_name}\n"
            f"Error Type: {type(e).__name__}\n"
            f"Error Message: {str(e)}\n"
            f"{'-'*70}\n"
        )
        raise


def _safe_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from model output safely."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# ─────────────────────────────────────────────
#  Natural Language Task Parsing
# ─────────────────────────────────────────────

PARSE_PROMPT_TEMPLATE = """You are a task-parsing assistant inside a Telegram productivity bot.
The user will describe a task in natural language.
Extract the structured information and return ONLY a valid JSON object — no explanation, no markdown fences.

JSON schema:
{{
  "title":       "<short action-oriented title, max 60 characters>",
  "description": "<any extra context or details, or empty string>",
  "category":    "<exactly one of: work | study | personal | health | finance | general>",
  "priority":    "<exactly one of: high | medium | low>",
  "deadline":    "<ISO 8601 datetime string YYYY-MM-DDTHH:MM:SS  or  null>"
}}

Rules:
- Infer priority from urgency: 'urgent'/'asap'/'critical'/'important' -> high; 'eventually'/'someday'/'when possible' -> low; otherwise medium.
- Infer category from context:
    meeting / report / project / work / office / client / deadline -> work
    exam / homework / course / lecture / study / assignment -> study
    gym / doctor / hospital / medicine / workout / health -> health
    bill / budget / tax / invoice / payment / salary / finance -> finance
    groceries / family / personal / home / friend / birthday -> personal
    anything else -> general
- Today's date and time is: {TODAY}
- Interpret relative expressions ('tomorrow', 'next Monday', 'in 3 days', 'at 5 PM', 'Friday evening') using the date above.
- If a date is given but no time, default to 09:00:00.
- If no deadline can be inferred, set "deadline" to null.
- Return ONLY the JSON object. No preamble. No explanation. No markdown.

User input: {INPUT}"""


async def parse_task_from_text(text: str, user_timezone: str = "UTC") -> Optional[Dict[str, Any]]:
    """
    Parse a free-text task description into structured fields using Gemini.
    Returns dict: { title, description, category, priority, deadline } or None on failure.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    prompt = PARSE_PROMPT_TEMPLATE.format(TODAY=today, INPUT=text)

    try:
        raw = await _gemini(prompt, temperature=0.1, function_name="parse_task_from_text")
        data = _safe_json(raw)

        if not data:
            logger.warning(f"[AI] parse_task: could not parse JSON from: {raw[:200]}")
            return None

        valid_categories = {"work", "study", "personal", "health", "finance", "general"}
        valid_priorities = {"high", "medium", "low"}

        return {
            "title":       str(data.get("title", text[:60])).strip(),
            "description": str(data.get("description", "")).strip(),
            "category":    data.get("category", "general") if data.get("category") in valid_categories else "general",
            "priority":    data.get("priority", "medium") if data.get("priority") in valid_priorities else "medium",
            "deadline":    data.get("deadline"),
        }
    except Exception as e:
        logger.error(f"[AI] parse_task_from_text error: {e}")
        return None


# ─────────────────────────────────────────────
#  Auto-Categorization
# ─────────────────────────────────────────────

CATEGORIZE_PROMPT_TEMPLATE = """You are a task categorization assistant inside a productivity bot.
Given a task title and optional description, respond with exactly ONE word - the category.
Choose from: work | study | personal | health | finance | general

Rules:
- work:     meetings, reports, projects, clients, office tasks
- study:    exams, homework, courses, lectures, assignments
- health:   gym, doctor, medicine, workouts, mental health
- finance:  bills, budgets, taxes, invoices, payments
- personal: groceries, family, home, friends, hobbies
- general:  anything else

Respond with ONLY the single category word. No punctuation. No explanation.

Task title: {TITLE}
Task description: {DESCRIPTION}"""


async def auto_categorize(title: str, description: str = "") -> str:
    """Classify a task into one of 6 categories using Gemini."""
    prompt = CATEGORIZE_PROMPT_TEMPLATE.format(
        TITLE=title,
        DESCRIPTION=description or "(none)",
    )
    try:
        result = (await _gemini(prompt, function_name="auto_categorize")).lower().strip().rstrip(".")
        valid = {"work", "study", "personal", "health", "finance", "general"}
        return result if result in valid else "general"
    except Exception as e:
        logger.error(f"[AI] auto_categorize error: {e}")
        return "general"


# ─────────────────────────────────────────────
#  Priority Prediction
# ─────────────────────────────────────────────

PRIORITY_PROMPT_TEMPLATE = """You are a productivity assistant inside a Telegram task manager.
Given a task, suggest its priority level.

Respond with ONLY one word: high | medium | low
No punctuation. No explanation.

Factors to consider:
- Proximity of deadline (< 1 day -> high, < 3 days -> likely medium+)
- Urgency language in the title/description
- Category: health and finance tasks often warrant higher priority
- Vague or distant deadlines -> low or medium

Task title: {TITLE}
Task description: {DESCRIPTION}
Deadline: {DEADLINE}
Days until deadline: {DAYS}"""


async def predict_priority(title: str, description: str = "", deadline: Optional[str] = None) -> str:
    """Predict task priority (high/medium/low) using Gemini."""
    days_str = "unknown"
    if deadline:
        try:
            dl = datetime.fromisoformat(deadline)
            days = (dl - datetime.utcnow()).days
            days_str = str(days)
        except Exception:
            pass

    prompt = PRIORITY_PROMPT_TEMPLATE.format(
        TITLE=title,
        DESCRIPTION=description or "(none)",
        DEADLINE=deadline or "none",
        DAYS=days_str,
    )
    try:
        result = (await _gemini(prompt, function_name="predict_priority")).lower().strip().rstrip(".")
        valid = {"high", "medium", "low"}
        return result if result in valid else "medium"
    except Exception as e:
        logger.error(f"[AI] predict_priority error: {e}")
        return "medium"


# ─────────────────────────────────────────────
#  Daily Motivational Message
# ─────────────────────────────────────────────

MOTIVATION_PROMPT_TEMPLATE = """You are a warm, friendly productivity coach inside a Telegram bot.
Write a short motivational message (2-3 sentences) for the user based on their task stats.
Be specific, encouraging, and avoid generic platitudes like "you can do it!".

User stats:
- Pending tasks: {PENDING}
- Completed tasks: {DONE}
- Completion rate: {RATE}%
- Overdue tasks: {OVERDUE}
- Most active category: {CATEGORY}

Write the message directly - no greeting, no sign-off. Just the motivational content."""


async def generate_daily_motivation(stats: Dict[str, Any]) -> str:
    """Generate a personalized motivational message based on user productivity stats."""
    prompt = MOTIVATION_PROMPT_TEMPLATE.format(
        PENDING=stats.get("pending", 0),
        DONE=stats.get("done", 0),
        RATE=stats.get("completion_rate", 0),
        OVERDUE=stats.get("overdue", 0),
        CATEGORY=stats.get("top_category", "general"),
    )
    try:
        return await _gemini(prompt, temperature=0.7, function_name="generate_daily_motivation")
    except Exception as e:
        logger.error(f"[AI] generate_daily_motivation error: {e}")
        return "Keep pushing forward - every completed task is a step toward your goals. 💪"