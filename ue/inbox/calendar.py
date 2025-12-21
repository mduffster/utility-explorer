"""Google Calendar integration."""

import json
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from ue.google_auth import get_google_credentials
from ue.db import upsert_inbox_item


def get_calendar_service():
    """Get Calendar API service."""
    creds = get_google_credentials()
    return build("calendar", "v3", credentials=creds)


def sync_calendar(days_ahead: int = 7, days_back: int = 1) -> dict:
    """
    Sync calendar events.

    Fetches events from days_back ago to days_ahead from now.
    Returns dict with counts.
    """
    service = get_calendar_service()

    now = datetime.utcnow()
    time_min = (now - timedelta(days=days_back)).isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=100,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    fetched = 0

    for event in events:
        event_id = event["id"]

        # Get start time
        start = event.get("start", {})
        if "dateTime" in start:
            timestamp = start["dateTime"]
        elif "date" in start:
            timestamp = start["date"] + "T00:00:00"
        else:
            timestamp = datetime.now().isoformat()

        # Get attendees for context
        attendees = event.get("attendees", [])
        attendee_emails = [a.get("email", "") for a in attendees[:5]]

        summary = event.get("summary", "(no title)")
        description = event.get("description", "")

        upsert_inbox_item(
            id=f"calendar:{event_id}",
            source="calendar",
            item_type="event",
            sender=", ".join(attendee_emails) if attendee_emails else None,
            subject=summary,
            snippet=description[:200] if description else None,
            timestamp=timestamp,
            raw_data=json.dumps(event),
        )
        fetched += 1

    return {"fetched": fetched}


def get_upcoming_events(hours: int = 24) -> list[dict]:
    """Get events in the next N hours."""
    service = get_calendar_service()

    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(hours=hours)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=20,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])
