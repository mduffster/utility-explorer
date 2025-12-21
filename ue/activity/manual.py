"""Manual activity logging."""

import json
from datetime import datetime
from typing import Optional

from ue.db import log_activity


def log_application(
    company: str,
    role: Optional[str] = None,
    workstream: str = "ai-research",
    notes: Optional[str] = None,
) -> None:
    """Log a job application."""
    description = f"Applied to {company}"
    if role:
        description += f" for {role}"

    metadata = {"company": company, "role": role, "notes": notes}

    log_activity(
        activity_type="application",
        description=description,
        workstream=workstream,
        source="manual",
        metadata=json.dumps(metadata),
    )


def log_win(
    description: str,
    workstream: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    """Log a win or accomplishment."""
    metadata = {"notes": notes} if notes else None

    log_activity(
        activity_type="win",
        description=description,
        workstream=workstream,
        source="manual",
        metadata=json.dumps(metadata) if metadata else None,
    )


def log_custom(
    activity_type: str,
    description: str,
    workstream: Optional[str] = None,
) -> None:
    """Log a custom activity."""
    log_activity(
        activity_type=activity_type,
        description=description,
        workstream=workstream,
        source="manual",
    )
