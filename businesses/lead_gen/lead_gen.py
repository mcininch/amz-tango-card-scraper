"""
Lead Generator
==============
Scrapes buyer leads (emails) from deal forums, Reddit, Facebook Groups.
Builds subscriber list for email marketing campaigns.

Revenue: Each subscriber worth $1-5/year in affiliate + newsletter revenue.
1,000 leads = $1,000–$5,000/year.
PayPal: jayjay@collector.org (@digitalempiresk)
"""

import csv
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
    "vip_link": "https://paypal.me/digitalempiresk/4.99",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class LeadGenerator:
    """Builds and manages an email subscriber list for monetization."""

    def __init__(self, output_file: str = "subscribers.txt"):
        self.output_file = output_file
        self.leads: List[Dict] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing subscribers from file."""
        if os.path.exists(self.output_file):
            with open(self.output_file) as f:
                for line in f:
                    email = line.strip()
                    if email and "@" in email:
                        self.leads.append({"email": email, "source": "existing", "added": ""})
            logger.info(f"Loaded {len(self.leads)} existing subscribers")

    def add_lead(self, email: str, source: str = "manual") -> bool:
        """Add a new lead if not already in list."""
        email = email.strip().lower()
        if not EMAIL_REGEX.match(email):
            return False
        existing = {l["email"] for l in self.leads}
        if email in existing:
            return False
        lead = {"email": email, "source": source, "added": datetime.now().isoformat()}
        self.leads.append(lead)
        with open(self.output_file, "a") as f:
            f.write(f"{email}\n")
        logger.info(f"New lead: {email} (from {source})")
        return True

    def scrape_reddit_emails(self, subreddit: str = "frugal") -> List[str]:
        """
        Scrape publicly visible emails from Reddit deal posts.
        NOTE: Only collect emails that users voluntarily share publicly.
        """
        import requests
        found = []
        try:
            url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
            headers = {"User-Agent": "DealBot/1.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            posts = resp.json().get("data", {}).get("children", [])
            for post in posts:
                text = post["data"].get("selftext", "") + post["data"].get("title", "")
                emails = EMAIL_REGEX.findall(text)
                for email in emails:
                    if self.add_lead(email, source=f"reddit/r/{subreddit}"):
                        found.append(email)
            logger.info(f"Reddit r/{subreddit}: found {len(found)} new leads")
        except Exception as e:
            logger.error(f"Reddit scrape failed: {e}")
        return found

    def import_csv(self, csv_path: str, email_column: str = "email") -> int:
        """Import leads from a CSV file."""
        imported = 0
        try:
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get(email_column, "").strip()
                    if self.add_lead(email, source=f"csv:{csv_path}"):
                        imported += 1
            logger.info(f"Imported {imported} leads from {csv_path}")
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
        return imported

    def get_stats(self) -> Dict:
        """Return list statistics and revenue projection."""
        total = len(self.leads)
        sources = {}
        for lead in self.leads:
            s = lead.get("source", "unknown")
            sources[s] = sources.get(s, 0) + 1
        return {
            "total_leads": total,
            "sources": sources,
            "projected_annual_low": total * 1.0,
            "projected_annual_high": total * 5.0,
            "paypal_payout": PAYPAL_CONFIG["handle"],
            "vip_upsell_link": PAYPAL_CONFIG["vip_link"],
        }
