"""AI-powered focus recommendations."""

import os
from datetime import datetime, timedelta

from anthropic import Anthropic

from ue.db import (
    get_overdue_tasks,
    get_upcoming_tasks,
    get_inbox_items,
    get_block_targets,
    get_week_block_summary,
)


def get_at_risk_blocks() -> list[dict]:
    """Get blocks at risk of missing weekly target."""
    today = datetime.now().date()
    days_left = 6 - today.weekday()

    targets = get_block_targets()
    at_risk = []

    for target in targets:
        name = target["block_name"]
        weekly_target = target["weekly_target"]

        if weekly_target == 0:  # Daily blocks tracked differently
            continue

        summary = get_week_block_summary(name)
        completed = summary["completed"]
        remaining = weekly_target - completed

        if remaining > 0 and remaining >= days_left:
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
            })

    return at_risk


def gather_context() -> dict:
    """Gather current state for AI analysis."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Overdue tasks
    overdue = get_overdue_tasks()

    # Tasks due in next 3 days
    upcoming = [t for t in get_upcoming_tasks(days=3) if t["due_date"] >= today_str]

    # Blocks at risk
    at_risk = get_at_risk_blocks()

    # Items needing response (top 5)
    needs_response = get_inbox_items(needs_response=True, limit=5)

    # Today's calendar - try to get from db
    from ue.db import get_db
    db = get_db()
    calendar_items = db.execute(
        """
        SELECT subject, timestamp FROM inbox_items
        WHERE source = 'calendar'
        AND date(timestamp) = date('now', 'localtime')
        ORDER BY timestamp
        LIMIT 5
        """,
    ).fetchall()
    db.close()

    return {
        "now": now.strftime("%A, %B %d at %I:%M %p"),
        "overdue_tasks": [{"title": t["title"], "due": t["due_date"]} for t in overdue],
        "upcoming_tasks": [{"title": t["title"], "due": t["due_date"], "priority": t["priority"]} for t in upcoming],
        "blocks_at_risk": at_risk,
        "needs_response": [{"source": i["source"], "from": i["sender"], "subject": i["subject"]} for i in needs_response],
        "todays_calendar": [{"event": r["subject"], "time": r["timestamp"]} for r in calendar_items],
    }


def build_prompt(context: dict) -> str:
    """Build the prompt for Claude."""
    lines = [
        f"Current time: {context['now']}",
        "",
    ]

    if context["overdue_tasks"]:
        lines.append("OVERDUE TASKS:")
        for t in context["overdue_tasks"]:
            lines.append(f"  - {t['title']} (was due {t['due']})")
        lines.append("")

    if context["upcoming_tasks"]:
        lines.append("TASKS DUE SOON:")
        for t in context["upcoming_tasks"]:
            pri = f" [{t['priority']}]" if t["priority"] != "normal" else ""
            lines.append(f"  - {t['title']} (due {t['due']}){pri}")
        lines.append("")

    if context["blocks_at_risk"]:
        lines.append("BLOCKS AT RISK THIS WEEK:")
        for b in context["blocks_at_risk"]:
            lines.append(f"  - {b['name']}: {b['completed']}/{b['target']} done, {b['remaining']} needed, {b['days_left']} days left")
        lines.append("")

    if context["needs_response"]:
        lines.append("ITEMS NEEDING RESPONSE:")
        for i in context["needs_response"]:
            lines.append(f"  - [{i['source']}] {i['from']}: {i['subject']}")
        lines.append("")

    if context["todays_calendar"]:
        lines.append("TODAY'S CALENDAR:")
        for e in context["todays_calendar"]:
            time_str = e["time"][11:16] if len(e["time"]) > 11 else e["time"]
            lines.append(f"  - {time_str}: {e['event']}")
        lines.append("")

    if not any([context["overdue_tasks"], context["upcoming_tasks"],
                context["blocks_at_risk"], context["needs_response"]]):
        lines.append("No urgent items. You have flexibility today.")
        lines.append("")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a focus coach for someone with ADHD. Your job is to cut through overwhelm and suggest ONE clear next action.

Rules:
- Be direct and concise (2-3 sentences max)
- Give ONE specific action, not a list
- Consider time of day and energy (mornings often better for hard tasks)
- If someone has overdue tasks, those usually take priority
- Blocks "at risk" mean they might miss their weekly goal
- Don't moralize or add productivity platitudes
- If nothing is urgent, it's okay to say so

Format your response as:
FOCUS: [the one thing to do]
WHY: [brief reasoning]"""


def get_focus() -> str:
    """Get AI-powered focus recommendation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. Export it in your shell:\n"
            "  export ANTHROPIC_API_KEY='your-key-here'"
        )

    context = gather_context()
    user_prompt = build_prompt(context)

    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def print_context() -> str:
    """Return formatted context for manual use (copy/paste to claude.ai)."""
    context = gather_context()
    prompt = build_prompt(context)
    return f"{SYSTEM_PROMPT}\n\n---\n\n{prompt}"
