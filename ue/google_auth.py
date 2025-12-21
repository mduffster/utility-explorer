"""Google OAuth2 authentication."""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ue.config import CREDENTIALS_PATH, TOKEN_PATH, GOOGLE_SCOPES, ensure_data_dir


def get_google_credentials() -> Credentials:
    """Get valid Google credentials, refreshing or re-authenticating as needed."""
    ensure_data_dir()
    creds = None

    # Load existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Google credentials not found at {CREDENTIALS_PATH}\n"
                    "Run 'ue setup' for instructions on setting up Google API access."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def is_authenticated() -> bool:
    """Check if we have valid Google credentials."""
    try:
        creds = get_google_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False
