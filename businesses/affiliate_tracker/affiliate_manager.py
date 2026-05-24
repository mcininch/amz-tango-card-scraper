"""
Affiliate Link Manager & Auto-Poster
======================================
Monitors deal emails / RSS feeds and automatically:
  1. Rewrites product links with your Amazon affiliate tag
  2. Posts deals to Discord, Telegram, or a website
  3. Tracks clicks and estimates commission

Commission: Amazon pays 1–10% depending on category.
$10K in product sales → $100–$1,000 commission.

Setup:
  1. Join Amazon Associates: https://affiliate-program.amazon.com/
  2. Get your tracking ID (e.g. "johndoe-20")
  3. Set AFFILIATE_TAG in config or env
"""

import re
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

AMAZON_DOMAINS = [
    "amazon.com", "amzn.to", "amzn.com",
    "amazon.co.uk", "amazon.ca", "amazon.de",
]

# Commission rates by category (approximate)
COMMISSION_RATES = {
    "Electronics": 0.04,
    "Computers": 0.025,
    "Headphones": 0.06,
    "Kitchen": 0.045,
    "Books": 0.045,
    "Toys": 0.03,
    "Default": 0.03,
}


@dataclass
class AffiliateLink:
    """Represents an affiliate-tagged product link."""
    original_url: str
    affiliate_url: str
    asin: str
    tag: str
    category: str = "Default"
    estimated_commission_rate: float = 0.03
    clicks: int = 0


class AffiliateManager:
    """Manages Amazon affiliate link generation and tracking."""

    def __init__(self, affiliate_tag: str, telegram_token: str = "", telegram_chat_id: str = ""):
        self.tag = affiliate_tag
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.links: List[AffiliateLink] = []

    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from any Amazon URL format."""
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
            r"asin=([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def tag_url(self, url: str, category: str = "Default") -> Optional[AffiliateLink]:
        """
        Convert any Amazon URL to an affiliate-tagged URL.

        Args:
            url: Original Amazon product URL.
            category: Product category for commission estimation.

        Returns:
            AffiliateLink object or None if not an Amazon URL.
        """
        if not any(domain in url for domain in AMAZON_DOMAINS):
            return None

        asin = self._extract_asin(url)
        if not asin:
            return None

        # Build clean affiliate URL
        affiliate_url = f"https://www.amazon.com/dp/{asin}?tag={self.tag}"

        link = AffiliateLink(
            original_url=url,
            affiliate_url=affiliate_url,
            asin=asin,
            tag=self.tag,
            category=category,
            estimated_commission_rate=COMMISSION_RATES.get(category, COMMISSION_RATES["Default"]),
        )

        self.links.append(link)
        logger.info(f"Tagged ASIN {asin} with affiliate link")
        return link

    def tag_all_in_text(self, text: str) -> str:
        """Replace all Amazon URLs in a text block with affiliate URLs."""
        url_pattern = r"https?://(?:www\.)?(?:amazon\.com|amzn\.to)/[^\s]+"
        urls = re.findall(url_pattern, text)

        for url in urls:
            link = self.tag_url(url)
            if link:
                text = text.replace(url, link.affiliate_url)

        return text

    def post_deal_to_telegram(self, deal_text: str, product_url: str, price: str = "") -> None:
        """Post an affiliate deal to Telegram channel."""
        link = self.tag_url(product_url)
        affiliate_url = link.affiliate_url if link else product_url

        message = (
            f"🔥 <b>HOT DEAL!</b>\n\n"
            f"{deal_text}\n"
            f"{'💰 ' + price if price else ''}\n\n"
            f"🛒 <a href='{affiliate_url}'>Buy on Amazon</a>"
        )

        if not self.telegram_token:
            logger.info(f"[DEAL] {deal_text}")
            return

        try:
            requests.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            logger.info("Deal posted to Telegram")
        except Exception as e:
            logger.error(f"Failed to post deal: {e}")

    def scrape_deal_sites(self) -> List[dict]:
        """Scrape deals from SlickDeals RSS and tag with affiliate links."""
        deals = []
        rss_urls = [
            "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first_word&rss=1",
            "https://www.dealnews.com/c142/Electronics/?rss=1",
        ]

        for rss_url in rss_urls:
            try:
                resp = requests.get(rss_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    continue

                # Simple XML parse for deal titles and links
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if not channel:
                    continue

                for item in channel.findall("item")[:10]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    desc = item.findtext("description", "")

                    # Tag any Amazon links in description
                    tagged_desc = self.tag_all_in_text(desc)

                    deals.append({
                        "title": title,
                        "link": link,
                        "description": tagged_desc,
                        "has_amazon": "amazon.com" in desc,
                    })

                logger.info(f"Scraped {len(deals)} deals from {rss_url}")
            except Exception as e:
                logger.warning(f"Failed to scrape {rss_url}: {e}")

        return deals

    def estimate_monthly_income(self, monthly_clicks: int = 1000, conversion_rate: float = 0.05, avg_order: float = 50.0) -> float:
        """
        Estimate monthly affiliate income.

        Args:
            monthly_clicks: Expected clicks per month.
            conversion_rate: % of clicks that buy (typically 3–8%).
            avg_order: Average Amazon order value.

        Returns:
            Estimated monthly commission in dollars.
        """
        sales = monthly_clicks * conversion_rate
        revenue = sales * avg_order
        commission = revenue * COMMISSION_RATES["Default"]
        logger.info(
            f"Estimate: {monthly_clicks} clicks → {sales:.0f} sales → "
            f"${revenue:.0f} revenue → ${commission:.2f} commission/month"
        )
        return commission

    def get_paypal_payout_info(self) -> dict:
        """Return PayPal payout details for affiliate commissions."""
        return {
            "paypal_email": "jayjay@collector.org",
            "paypal_handle": "@digitalempiresk",
            "paypal_me": "https://paypal.me/digitalempiresk",
            "note": "Affiliate commissions paid via PayPal @digitalempiresk",
        }
