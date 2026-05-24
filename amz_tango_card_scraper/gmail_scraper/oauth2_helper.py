"""OAuth2 helper module for Gmail IMAP authentication."""

import base64
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Full Gmail access scope needed for IMAP
SCOPES = ["https://mail.google.com/"]


def get_oauth2_credentials(token_file: str, credentials_file: str) -> Credentials:
    """
    Get valid OAuth2 credentials, refreshing or re-authorizing as needed.

    Args:
        token_file: Path to saved token JSON file.
        credentials_file: Path to Google Cloud credentials JSON file.

    Returns:
        Valid Google OAuth2 Credentials object.
    """
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def generate_xoauth2_string(username: str, access_token: str) -> bytes:
    """
    Generate the XOAUTH2 base64 string required for IMAP AUTHENTICATE.

    Args:
        username: Gmail address.
        access_token: A valid OAuth2 access token.

    Returns:
        Base64-encoded XOAUTH2 auth string as bytes.
    """
    auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode("ascii"))
