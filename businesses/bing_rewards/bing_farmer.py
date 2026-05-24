"""
Microsoft Bing Rewards Farmer
==============================
Automates Microsoft Rewards point earning:
  - Daily PC searches (30 pts)
  - Daily Mobile searches (20 pts)
  - Daily set (bonus activities, ~30–50 pts)
  - Punch cards / streaks

At ~80 pts/day → 2400 pts/month → ~$5 Amazon GC per month per account.
With 10 accounts: $50/month, fully automated.

Bing searches use randomized real-world search terms to appear human.
The browser uses undetected-chromedriver to avoid bot detection.
"""

import random
import time
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from amz_tango_card_scraper.browser.chrome import get_chrome_browser
from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

# Real-looking search terms pulled from trending categories
SEARCH_TERMS = [
    "best restaurants near me",
    "how to make pasta carbonara",
    "weather this week",
    "amazon prime day 2026 deals",
    "best budget smartphones 2026",
    "how to invest in index funds",
    "youtube to mp3 converter",
    "wordle today answer",
    "nba scores last night",
    "stock market news today",
    "how to lose weight fast",
    "best vpn service 2026",
    "chatgpt vs gemini comparison",
    "flights to miami cheap",
    "what is inflation",
    "how to start a business",
    "best streaming service 2026",
    "elon musk net worth",
    "amazon gift card balance check",
    "microsoft rewards redeem",
    "bing homepage quiz answers",
    "costco membership benefits",
    "how to save money fast",
    "best credit cards cashback",
    "tesla model 3 price 2026",
    "how to get free amazon gift cards",
    "roblox promo codes 2026",
    "minecraft seeds 2026",
    "how to make money online",
    "passive income ideas",
]

BING_SEARCH_URL = "https://www.bing.com/search?q="
MS_REWARDS_URL = "https://rewards.bing.com/"


class BingRewardsFarmer:
    """Automates Microsoft Rewards point collection via Bing searches."""

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
        pc_searches: int = 30,
        mobile_searches: int = 20,
    ):
        self.email = email
        self.password = password
        self.headless = headless
        self.pc_searches = pc_searches
        self.mobile_searches = mobile_searches

    def _human_delay(self, min_s: float = 1.5, max_s: float = 4.0) -> None:
        """Random human-like delay."""
        time.sleep(random.uniform(min_s, max_s))

    def _random_searches(self, browser, count: int) -> None:
        """Perform random searches on Bing."""
        used = random.sample(SEARCH_TERMS * 10, min(count, len(SEARCH_TERMS) * 10))[:count]
        for term in used:
            try:
                browser.get(f"{BING_SEARCH_URL}{term.replace(' ', '+')}")
                self._human_delay(2, 5)
                logger.debug(f"Searched: {term}")
            except Exception as e:
                logger.warning(f"Search failed for '{term}': {e}")

    def _login_microsoft(self, browser) -> bool:
        """Log into Microsoft account."""
        try:
            browser.get("https://login.microsoftonline.com/")
            wait = WebDriverWait(browser, 15)

            # Email
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
            email_field.send_keys(self.email)
            email_field.send_keys(Keys.RETURN)
            self._human_delay(2, 3)

            # Password
            pwd_field = wait.until(EC.presence_of_element_located((By.NAME, "passwd")))
            pwd_field.send_keys(self.password)
            pwd_field.send_keys(Keys.RETURN)
            self._human_delay(3, 5)

            logger.info(f"Microsoft login attempted for {self.email}")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def _complete_daily_set(self, browser) -> None:
        """Complete daily set activities on rewards.bing.com."""
        try:
            browser.get(MS_REWARDS_URL)
            self._human_delay(3, 5)

            # Click available daily activities
            cards = browser.find_elements(By.CSS_SELECTOR, "mee-card-group div.c-card-content")
            for card in cards[:5]:
                try:
                    card.click()
                    self._human_delay(2, 4)
                    browser.back()
                    self._human_delay(1, 2)
                except Exception:
                    pass

            logger.info("Daily set activities attempted")
        except Exception as e:
            logger.warning(f"Daily set failed: {e}")

    def run(self) -> dict:
        """
        Run the full farming session.

        Returns:
            Dict with points_earned estimate and status.
        """
        result = {"email": self.email, "status": "ok", "points_earned": 0, "error": None}

        # --- PC searches ---
        logger.info(f"Starting PC searches for {self.email}...")
        browser = get_chrome_browser(headless=self.headless, no_images=True)
        try:
            if self._login_microsoft(browser):
                self._random_searches(browser, self.pc_searches)
                self._complete_daily_set(browser)
                result["points_earned"] += self.pc_searches * 3  # ~3 pts per search
                logger.info(f"PC searches done ({self.pc_searches} searches)")
        finally:
            browser.quit()

        self._human_delay(5, 10)

        # --- Mobile searches ---
        logger.info(f"Starting mobile searches for {self.email}...")
        mobile_browser = get_chrome_browser(headless=self.headless, no_images=True)
        try:
            # Set mobile user agent
            mobile_browser.execute_cdp_cmd(
                "Emulation.setUserAgentOverride",
                {
                    "userAgent": (
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                        "Mobile/15E148 Safari/604.1"
                    )
                },
            )
            if self._login_microsoft(mobile_browser):
                self._random_searches(mobile_browser, self.mobile_searches)
                result["points_earned"] += self.mobile_searches * 3
                logger.info(f"Mobile searches done ({self.mobile_searches} searches)")
        finally:
            mobile_browser.quit()

        logger.info(f"Farming complete for {self.email} — ~{result['points_earned']} pts earned")
        return result

    def get_paypal_cashout_info(self) -> dict:
        """PayPal destination for cashing out Bing rewards → gift cards → cash."""
        return {
            "paypal_email": "jayjay@collector.org",
            "paypal_handle": "@digitalempiresk",
            "paypal_me": "https://paypal.me/digitalempiresk",
            "cashout_flow": "MS Rewards → Amazon GC → CardCash → PayPal @digitalempiresk",
        }
