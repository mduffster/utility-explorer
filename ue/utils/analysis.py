"""Analysis utilities - block risk calculations, etc."""

from datetime import timedelta

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
