"""Gmail API OAuth2 authentication."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Full read/write access needed for organizing (modify labels, archive, delete)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

DEFAULT_CREDENTIALS_PATH = Path("credentials.json")
DEFAULT_TOKEN_PATH = Path("token.json")


def get_credentials(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> Credentials:
    """Obtain valid Gmail API credentials via OAuth2 flow.

    On first run, opens a browser for user authorization and saves the token.
    On subsequent runs, reuses or refreshes the saved token.
    """
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"OAuth credentials file not found: {credentials_path}\n"
                "Please download it from Google Cloud Console.\n"
                "See README.md for setup instructions."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json())
    return creds


def get_gmail_service(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
):
    """Build and return an authenticated Gmail API service."""
    creds = get_credentials(credentials_path, token_path)
    return build("gmail", "v1", credentials=creds)
