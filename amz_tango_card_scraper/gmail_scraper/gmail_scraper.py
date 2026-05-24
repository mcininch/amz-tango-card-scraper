"""Module to scrape Tango Cards from Gmail."""

import email as em
import imaplib
from typing import List

from amz_tango_card_scraper.utils.logger import setup_logger
from amz_tango_card_scraper.utils.schemas import TangoCard

from .constants import IMAP_GMAIL_URL
from .helpers import extract_tango_card_from_body, get_body_of_email
from .oauth2_helper import generate_xoauth2_string, get_oauth2_credentials

logger = setup_logger(logger_name=__name__)


def scrape_tango_cards(
    email: str,
    from_list: List[str],
    trash: bool = False,
    app_password: str = "",
    token_file: str = "",
    credentials_file: str = "",
) -> List[TangoCard]:
    """
    Scrape Tango Cards from Gmail using IMAP.

    Supports two authentication methods:
      - App Password (legacy): provide app_password
      - OAuth2 (recommended): provide token_file + credentials_file

    Args:
        email: Gmail email address.
        from_list: List of sender addresses to search for Tango Cards.
        trash: Whether to trash emails after scraping.
        app_password: Gmail app password (legacy auth).
        token_file: Path to OAuth2 token JSON file.
        credentials_file: Path to Google Cloud credentials JSON file.

    Returns:
        List of scraped TangoCard objects.
    """
    mail = imaplib.IMAP4_SSL(IMAP_GMAIL_URL)

    # --- Choose authentication method ---
    if token_file and credentials_file:
        logger.info("Authenticating with OAuth2...")
        creds = get_oauth2_credentials(token_file=token_file, credentials_file=credentials_file)
        auth_string = generate_xoauth2_string(username=email, access_token=creds.token)
        mail.authenticate("XOAUTH2", lambda x: auth_string)
        logger.info("OAuth2 authentication successful")
    elif app_password:
        logger.info("Authenticating with App Password...")
        mail.login(email, app_password)
        logger.info("App Password authentication successful")
    else:
        raise ValueError("No authentication method provided. Set either app_password OR (token_file + credentials_file) in config.yaml.")

    # Select inbox
    mail.select("inbox")

    tango_cards: List[TangoCard] = []

    for from_address in from_list:
        logger.info(f"Searching for Tango Cards from {from_address}...")
        _, msg_ids = mail.search(None, "FROM", from_address)

        for msg_id in msg_ids[0].split():
            _, flags_data = mail.fetch(msg_id, "(FLAGS)")
            _, msg_data = mail.fetch(msg_id, "(RFC822)")

            for response in msg_data:
                if isinstance(response, tuple):
                    msg = em.message_from_bytes(response[1])

                    if "\\Seen" in flags_data[0].decode("utf-8"):  # type: ignore
                        logger.info(f"Skipping email {msg_id.decode('utf-8')} as it has already been read...")
                        continue

                    body = get_body_of_email(msg)

                    if "tango" in body:
                        logger.info(f"Tango Card found in email {msg_id.decode('utf-8')}")
                        tango_cards.append(extract_tango_card_from_body(body))

                        if trash:
                            logger.info(f"Trashing email {msg_id.decode('utf-8')}...")
                            mail.store(msg_id, "+X-GM-LABELS", "\\Trash")

    mail.close()
    return tango_cards
