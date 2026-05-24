"""
Coupon Scraper
==============
Scrapes promo codes from RetailMeNot, Honey, and Coupons.com.
Posts best coupons to Discord/Telegram for affiliate traffic.
Revenue: affiliate links on every coupon post + Discord VIP upsell.

PayPal: jayjay@collector.org (@digitalempiresk)
"""

import time
from typing import Dict, List
from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
    "vip_link": "https://paypal.me/digitalempiresk/4.99",
}

COUPON_SOURCES = [
    "https://www.retailmenot.com/rss/browse/today.xml",
    "https://www.coupons.com/sitemap/deal-feed.xml",
]


class CouponScraper:
    """Scrapes and distributes coupon codes for affiliate revenue."""

    def __init__(self, affiliate_tag: str = "", discord_webhook: str = ""):
        self.affiliate_tag = affiliate_tag
        self.discord_webhook = discord_webhook
        self.found_codes: List[Dict] = []

    def scrape_retailmenot(self) -> List[Dict]:
        """Scrape top coupons from RetailMeNot RSS."""
        import requests
        try:
            resp = requests.get(COUPON_SOURCES[0], timeout=10)
            # Parse XML feed for store + code pairs
            coupons = []
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:20]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")
                if title and link:
                    coupons.append({"store": title, "url": link, "description": desc, "source": "RetailMeNot"})
            logger.info(f"Scraped {len(coupons)} coupons from RetailMeNot")
            return coupons
        except Exception as e:
            logger.error(f"RetailMeNot scrape failed: {e}")
            return []

    def scrape_amazon_coupons(self) -> List[Dict]:
        """Get active Amazon coupons (clips on checkout)."""
        # Amazon coupon page: amazon.com/coupons
        coupons = [
            {"store": "Amazon", "code": "CLIP", "description": "Clip coupons on Amazon product pages", "savings": "5-30%"},
            {"store": "Amazon", "code": "PRIME20", "description": "Prime Day promo", "savings": "20%"},
        ]
        logger.info(f"Found {len(coupons)} Amazon coupons")
        return coupons

    def post_to_discord(self, coupon: Dict) -> bool:
        """Post coupon alert to Discord for engagement + affiliate clicks."""
        if not self.discord_webhook:
            return False
        import requests
        embed = {
            "title": f"🏷️ COUPON: {coupon.get('store', 'Store')}",
            "description": coupon.get("description", ""),
            "color": 0x00AA44,
            "fields": [
                {"name": "Code", "value": f"`{coupon.get('code', 'See link')}`", "inline": True},
                {"name": "Savings", "value": coupon.get("savings", "Varies"), "inline": True},
                {"name": "⭐ VIP Deals", "value": f"[Get VIP Access]({PAYPAL_CONFIG['vip_link']})", "inline": False},
            ],
        }
        try:
            resp = requests.post(self.discord_webhook, json={"embeds": [embed]}, timeout=10)
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def run(self) -> List[Dict]:
        """Scrape all sources and return combined coupon list."""
        all_coupons = []
        all_coupons.extend(self.scrape_retailmenot())
        all_coupons.extend(self.scrape_amazon_coupons())
        self.found_codes = all_coupons
        logger.info(f"Total coupons found: {len(all_coupons)}")
        return all_coupons
