"""Web-based Gmail scraper using Selenium (no App Password or OAuth needed)."""

import os
import time
from typing import List

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from amz_tango_card_scraper.utils.logger import setup_logger
from amz_tango_card_scraper.utils.schemas import TangoCard

from .helpers import extract_tango_card_from_body

logger = setup_logger(logger_name=__name__)

GMAIL_URL = "https://mail.google.com"
PROFILE_DIR = os.path.expanduser("~/.config/amz-tcs-chrome")


def _is_logged_in(browser) -> bool:
    """Check if we're currently on a Gmail inbox page."""
    try:
        return "mail.google.com/mail" in browser.current_url
    except WebDriverException:
        return False


def _wait_for_login(browser, timeout: int = 300) -> bool:
    """Open Gmail and wait until user is logged in (up to timeout seconds)."""
    browser.get(GMAIL_URL)
    print("\n" + "=" * 55)
    print("  ACTION REQUIRED")
    print("  A Chrome window has opened.")
    print("  Please log in to Gmail (fuckerfred@gmail.com).")
    print("  Your session will be saved — you only do this ONCE.")
    print("=" * 55 + "\n")

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_logged_in(browser):
            print("✅  Logged in! Continuing...\n")
            return True
        time.sleep(2)

    logger.error("Timed out waiting for Gmail login.")
    return False


def _get_unread_email_bodies(browser, sender: str) -> List[str]:
    """Search Gmail for unread emails from a sender and return HTML bodies."""
    wait = WebDriverWait(browser, 15)
    bodies = []

    # Build search URL: unread emails from this sender
    query = f"from:{sender} is:unread"
    encoded = query.replace(" ", "+").replace(":", "%3A").replace("@", "%40")
    browser.get(f"https://mail.google.com/mail/u/0/#search/{encoded}")
    time.sleep(3)

    try:
        # Gmail marks unread rows with class 'zE', all rows have 'zA'
        rows = browser.find_elements(By.XPATH, "//tr[contains(@class,'zA') and contains(@class,'zE')]")
        logger.info(f"Found {len(rows)} unread email(s) from {sender}")

        for i in range(len(rows)):
            try:
                # Re-fetch to avoid stale element
                rows = browser.find_elements(By.XPATH, "//tr[contains(@class,'zA') and contains(@class,'zE')]")
                if i >= len(rows):
                    break

                # Scroll into view and click via JS to bypass interactability issues
                browser.execute_script("arguments[0].scrollIntoView(true);", rows[i])
                time.sleep(0.5)
                browser.execute_script("arguments[0].click();", rows[i])
                time.sleep(2)

                # Get the email body HTML
                try:
                    body_el = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".a3s.aiL, .a3s.aXjCH, .ii.gt"))
                    )
                    body_html = browser.execute_script("return arguments[0].innerHTML", body_el)
                    if body_html and "tango" in body_html.lower():
                        logger.info(f"Tango Card content found in email #{i + 1}")
                        bodies.append(body_html)
                    else:
                        logger.info(f"Email #{i + 1} does not contain Tango Card content, skipping.")
                except TimeoutException:
                    logger.warning(f"Could not locate email body for email #{i + 1}")

                # Return to search results
                browser.back()
                time.sleep(2)

            except Exception as e:
                logger.warning(f"Error processing email #{i + 1}: {e}")
                browser.back()
                time.sleep(2)

    except Exception as e:
        logger.warning(f"Error searching emails from {sender}: {e}")

    return bodies


def scrape_tango_cards_web(
    email: str,
    password: str,
    from_list: List[str],
    no_images: bool = True,
) -> List[TangoCard]:
    """
    Scrape Tango Cards from Gmail using the browser (no App Password needed).

    On first run, a Chrome window opens for you to log in.
    Your session is saved to ~/.config/amz-tcs-chrome so future
    runs are fully automatic.

    Args:
        email: Gmail address.
        password: Gmail password (used to remind user which account to log into).
        from_list: List of senders to search for Tango Card emails.
        no_images: Whether to disable image loading.

    Returns:
        List of scraped TangoCard objects.
    """
    import undetected_chromedriver as uc  # type: ignore

    os.makedirs(PROFILE_DIR, exist_ok=True)

    # Remove stale Chrome lock files that prevent startup after a crash
    for lock in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = os.path.join(PROFILE_DIR, lock)
        if os.path.exists(lock_path) or os.path.islink(lock_path):
            os.remove(lock_path)
            logger.debug(f"Removed stale lock: {lock_path}")

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=GmailScraper")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Force Google Chrome 148 (not system Chromium 147)
    options.binary_location = "/opt/google/chrome/google-chrome"
    if no_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    logger.info("Starting Chrome browser for Gmail web scraping (undetected mode)...")
    browser = uc.Chrome(options=options, version_main=148, headless=False)

    tango_cards: List[TangoCard] = []

    try:
        # Navigate to Gmail and log in if needed
        browser.get(GMAIL_URL)
        time.sleep(3)

        if not _is_logged_in(browser):
            if not _wait_for_login(browser):
                logger.error("Gmail login failed or timed out.")
                return tango_cards

        logger.info("Gmail session active. Starting email search...")

        for sender in from_list:
            logger.info(f"Searching for unread emails from: {sender}")
            bodies = _get_unread_email_bodies(browser, sender)

            for body in bodies:
                try:
                    card = extract_tango_card_from_body(body)
                    tango_cards.append(card)
                    logger.info(f"Extracted Tango Card: {card.security_code}")
                except Exception as e:
                    logger.warning(f"Failed to parse Tango Card from email: {e}")

    finally:
        browser.quit()

    return tango_cards
