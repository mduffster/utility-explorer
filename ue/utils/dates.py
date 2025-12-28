"""Date utilities - parsing and effective date logic."""

from datetime import datetime, timedelta


def get_effective_date():
    """Get the 'effective' date, treating 2am as the day boundary.

    If it's between midnight and 2am, returns yesterday's date.
    This matches natural sleep cycles - 12:41am still feels like 'tonight'.
    """
    now = datetime.now()
    if now.hour < 2:
        return (now - timedelta(days=1)).date()
    return now.date()


def parse_due_date(due: str) -> str:
    """Parse natural language dates into YYYY-MM-DD format."""
    if not due:
        return None

    due_lower = due.lower().strip()
    today = datetime.now().date()

    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    # Map all common abbreviations to day index (0=Monday, 6=Sunday)
    day_abbrevs_map = {
        "mon": 0,
        "tue": 1, "tues": 1,
        "wed": 2, "weds": 2,
        "thu": 3, "thur": 3, "thurs": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    if due_lower == "today":
        return today.isoformat()
    elif due_lower == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    elif due_lower.startswith("next "):
        # Handle "next monday", "next wed", "next tues", etc.
        day_part = due_lower[5:]  # Remove "next "
        if day_part in day_abbrevs_map:
            target_day = day_abbrevs_map[day_part]
        elif day_part in day_names:
            target_day = day_names.index(day_part)
        else:
            return due  # Can't parse, return as-is
        # "next X" means the X in the following week
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        days_ahead += 7  # Add a week for "next"
        return (today + timedelta(days=days_ahead)).isoformat()
    elif due_lower in day_names or due_lower in day_abbrevs_map:
        # Find next occurrence of that day
        if due_lower in day_abbrevs_map:
            target_day = day_abbrevs_map[due_lower]
        else:
            target_day = day_names.index(due_lower)
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).isoformat()
    else:
        # Assume YYYY-MM-DD format
        return due
