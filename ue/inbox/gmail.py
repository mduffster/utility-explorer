"""Gmail integration - fetch inbox and sent emails."""

import json
from datetime import datetime, timedelta
from typing import Optional

from googleapiclient.discovery import build

from ue.google_auth import get_google_credentials
from ue.db import upsert_inbox_item, log_activity, activity_exists


def get_gmail_service():
    """Get Gmail API service."""
    creds = get_google_credentials()
    return build("gmail", "v1", credentials=creds)


def parse_email_headers(headers: list[dict]) -> dict:
    """Extract useful headers from email."""
    result = {}
    for header in headers:
        name = header["name"].lower()
        if name in ("from", "to", "subject", "date"):
            result[name] = header["value"]
    return result


def sync_gmail_inbox(days: int = 7, max_results: int = 50) -> dict:
    """
    Sync recent inbox emails.

    Returns dict with counts: {"fetched": N, "new": M}
    """
    service = get_gmail_service()

    # Calculate date filter - only fetch primary inbox (skip Promotions, Social, etc.)
    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"in:inbox category:primary after:{after_date}"

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    fetched = 0

    for msg_stub in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_stub["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        headers = parse_email_headers(msg.get("payload", {}).get("headers", []))

        # Parse timestamp
        timestamp = headers.get("date", "")
        try:
            # Gmail dates are RFC 2822 format
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(timestamp)
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()

        upsert_inbox_item(
            id=f"gmail:{msg['id']}",
            source="gmail",
            item_type="email",
            sender=headers.get("from", "Unknown"),
            subject=headers.get("subject", "(no subject)"),
            snippet=msg.get("snippet", ""),
            timestamp=timestamp,
            raw_data=json.dumps(msg),
        )
        fetched += 1

    return {"fetched": fetched}


def sync_gmail_sent(days: int = 7, max_results: int = 50) -> dict:
    """
    Sync sent emails to activity log.

    Returns dict with counts.
    """
    service = get_gmail_service()

    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"in:sent after:{after_date}"

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    logged = 0
    skipped = 0

    for msg_stub in messages:
        # Check if this message was already logged
        if activity_exists("gmail", "message_id", msg_stub["id"]):
            skipped += 1
            continue

        msg = service.users().messages().get(
            userId="me",
            id=msg_stub["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        headers = parse_email_headers(msg.get("payload", {}).get("headers", []))

        timestamp = headers.get("date", "")
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(timestamp)
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()

        to = headers.get("to", "Unknown")
        subject = headers.get("subject", "(no subject)")

        log_activity(
            activity_type="email_sent",
            description=f"To: {to[:50]} - {subject[:50]}",
            timestamp=timestamp,
            source="gmail",
            metadata=json.dumps({"message_id": msg["id"], "to": to, "subject": subject}),
        )
        logged += 1

    return {"logged": logged, "skipped": skipped}
