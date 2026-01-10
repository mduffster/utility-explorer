"""Analysis utilities - block risk calculations, streak tracking, etc."""

from datetime import timedelta, date

from ue.utils.dates import get_effective_date


def get_at_risk_blocks():
    """Calculate which blocks are at risk or behind pace this week."""
    from ue.db import get_block_targets, get_week_block_summary, get_block_completions
    from ue.config import load_config

    today = get_effective_date()
    today_str = today.isoformat()
    # Days elapsed and left in week (0 = Monday, 6 = Sunday)
    day_of_week = today.weekday()
    days_elapsed = day_of_week + 1  # Mon=1, Tue=2, etc.
    days_left = 6 - day_of_week  # Including today

    # Get workstream priorities
    config = load_config()
    workstreams = config.get("workstreams", {})

    def get_ws_priority(workstream):
        if workstream and workstream in workstreams:
            return workstreams[workstream].get("priority", "low")
        return None  # No workstream

    targets = get_block_targets()
    today_completions = {c["block_name"]: c for c in get_block_completions(since=today_str)}
    at_risk = []

    for target in targets:
        name = target["block_name"]
        weekly_target = target["weekly_target"]
        workstream = target.get("workstream")
        ws_priority = get_ws_priority(workstream)
        summary = get_week_block_summary(name)
        completed = summary["completed"]

        if weekly_target == 0:
            # Daily block - flag if not done today
            if name not in today_completions:
                at_risk.append({
                    "name": name,
                    "target": "daily",
                    "completed": completed,
                    "remaining": 1,
                    "days_left": days_left,
                    "workstream": workstream,
                    "status": "daily_pending"
                })
            continue

        remaining = weekly_target - completed

        if remaining <= 0:
            # Already hit target
            continue

        slack = days_left - remaining  # How many days we can skip and still hit target

        if remaining > days_left:
            # Can't possibly hit target
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "workstream": workstream,
                "status": "impossible"
            })
        elif slack <= 1:
            # At risk - only 0 or 1 day of slack
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "workstream": workstream,
                "status": "at_risk"
            })
        elif ws_priority in ("high", "mid") and completed < weekly_target / 2:
            # High/mid priority and under halfway - try to do
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "workstream": workstream,
                "status": "try_to_do"
            })
        elif ws_priority == "low" and slack <= 2:
            # Low priority - only flag when slack is tight (2 days or less)
            at_risk.append({
                "name": name,
                "target": weekly_target,
                "completed": completed,
                "remaining": remaining,
                "days_left": days_left,
                "workstream": workstream,
                "status": "try_to_do"
            })
        # No workstream and not urgent = don't show

    return at_risk


def calculate_block_streak(block_name: str, completions: list[dict]) -> int:
    """Calculate current consecutive completion streak for a block.

    Args:
        block_name: Name of the block to check
        completions: List of completion records (must include 'date' and 'status')

    Returns:
        Number of consecutive days with 'completed' status, counting back from today
    """
    # Filter to this block and completed status
    block_completions = [
        c for c in completions
        if c["block_name"] == block_name and c["status"] == "completed"
    ]

    if not block_completions:
        return 0

    # Get unique completion dates
    completion_dates = set(c["date"] for c in block_completions)

    # Count consecutive days back from today
    today = get_effective_date()
    streak = 0
    check_date = today

    while check_date.isoformat() in completion_dates:
        streak += 1
        check_date = check_date - timedelta(days=1)

    return streak


def calculate_completion_rate(completed: int, target: int, days: int) -> float:
    """Calculate completion rate as a percentage.

    Args:
        completed: Number of completions
        target: Weekly target (0 = daily)
        days: Number of days in the period

    Returns:
        Percentage (0-100) of target achieved
    """
    if target == 0:
        # Daily block - rate is completions / days
        if days == 0:
            return 0.0
        return (completed / days) * 100
    else:
        # Weekly block - rate is completions / target
        if target == 0:
            return 0.0
        return (completed / target) * 100


def compare_weeks(current: int, previous: int) -> str:
    """Return trend indicator comparing two values.

    Args:
        current: Current week's count
        previous: Previous week's count

    Returns:
        Trend string like "↑ (+2)", "↓ (-1)", or "→ (same)"
    """
    diff = current - previous
    if diff > 0:
        return f"↑ (+{diff})"
    elif diff < 0:
        return f"↓ ({diff})"
    else:
        return "→ (same)"


def get_week_bounds(reference_date: date, weeks_ago: int = 0) -> tuple[date, date]:
    """Get the Monday and Sunday of a week relative to reference date.

    Args:
        reference_date: The date to calculate from
        weeks_ago: How many weeks back (0 = current week)

    Returns:
        Tuple of (monday, sunday) as date objects
    """
    # Get to the Monday of the reference week
    monday = reference_date - timedelta(days=reference_date.weekday())
    # Go back N weeks
    monday = monday - timedelta(weeks=weeks_ago)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_consecutive_missed_days(max_lookback: int = 14) -> list[date]:
    """Find consecutive days with no block completions before today.

    Looks backwards from yesterday, counting consecutive days with zero
    block completions. Stops at the first day that has any completion.

    Args:
        max_lookback: Maximum number of days to look back

    Returns:
        List of dates (oldest first) with no completions, or empty list
    """
    from ue.db import get_block_completions, get_block_targets

    # Need at least one block target to check for missed days
    targets = get_block_targets()
    if not targets:
        return []

    today = get_effective_date()
    missed_days = []

    # Start from yesterday and work backwards
    for days_ago in range(1, max_lookback + 1):
        check_date = today - timedelta(days=days_ago)
        check_date_str = check_date.isoformat()

        # Get completions for this specific day
        completions = get_block_completions(since=check_date_str)
        day_completions = [c for c in completions if c["date"] == check_date_str]

        if day_completions:
            # Found a day with activity - stop looking
            break
        else:
            # No activity on this day
            missed_days.append(check_date)

    # Return oldest first
    return list(reversed(missed_days))
