#!/usr/bin/env python3
"""
One-time OAuth2 setup for Gmail.

Run this script once to authorize Gmail access.
It will open a browser window — log in and click Allow.
The token is saved to token.json and reused automatically.

Usage:
    python setup_gmail_oauth.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from amz_tango_card_scraper.gmail_scraper.oauth2_helper import SCOPES

from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    print("=" * 50)
    print("  Gmail OAuth2 Setup")
    print("=" * 50)

    credentials_file = "credentials.json"
    token_file = "token.json"

    if not os.path.exists(credentials_file):
        print(f"\n❌  '{credentials_file}' not found!")
        print("\nTo get it:")
        print("  1. Go to: https://console.cloud.google.com/")
        print("  2. Create or select a project")
        print("  3. Go to: APIs & Services → Library → search 'Gmail API' → Enable")
        print("  4. Go to: APIs & Services → Credentials → Create Credentials → OAuth client ID")
        print("  5. Choose: Desktop app → Create → Download JSON")
        print(f"  6. Save the file as '{credentials_file}' in this folder")
        print("\nThen run this script again.")
        sys.exit(1)

    print(f"\n✅  Found '{credentials_file}'")
    print("\nA browser window will open — log in with YOUR_GMAIL_ADDRESS and click Allow.\n")

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅  Token saved to '{token_file}'")
    print("\nYour config.yaml gmail section should look like:")
    print("---")
    print("gmail:")
    print("  email: YOUR_GMAIL_ADDRESS")
    print(f"  token_file: {token_file}")
    print(f"  credentials_file: {credentials_file}")
    print("---")
    print("\nYou're all set! Run the scraper with: poetry run amz-tcs")


if __name__ == "__main__":
    main()
