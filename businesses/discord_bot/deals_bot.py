"""
Discord Deals Alert Bot
========================
Runs a Discord bot that:
  1. Posts deal alerts to a channel automatically
  2. Lets users subscribe to deal categories
  3. Charges for a "VIP Deals" role via PayPal link
  4. Sends Amazon affiliate links for commission

Revenue model:
  - Free tier: general deals
  - VIP ($4.99/mo): exclusive deals, early alerts
  - Affiliate commission on every link clicked

Setup:
  1. Go to https://discord.com/developers/applications
  2. Create app → Bot → Copy token
  3. Invite bot to your server
  4. Add token to config.yaml discord section

Install: pip install discord.py
"""

import asyncio
import random
import time
from datetime import datetime
from typing import List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


class DiscordDealsBot:
    """
    Discord bot for automated deal posting.
    Uses discord.py webhook API (no bot token needed for posting).
    """

    def __init__(
        self,
        webhook_url: str,
        affiliate_tag: str = "",
        vip_paypal_link: str = "",
    ):
        self.webhook_url = webhook_url
        self.affiliate_tag = affiliate_tag
        self.vip_paypal_link = vip_paypal_link

    def _tag_amazon_url(self, url: str) -> str:
        """Add affiliate tag to Amazon URL."""
        if self.affiliate_tag and "amazon.com" in url:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}tag={self.affiliate_tag}"
        return url

    def post_deal(
        self,
        title: str,
        price: str,
        original_price: str,
        product_url: str,
        image_url: str = "",
        category: str = "General",
        description: str = "",
    ) -> bool:
        """
        Post a deal embed to Discord webhook.

        Args:
            title: Product name.
            price: Sale price string e.g. "$19.99".
            original_price: Original price e.g. "$34.99".
            product_url: Amazon/store URL.
            image_url: Product image URL.
            category: Deal category.
            description: Short deal description.

        Returns:
            True if posted successfully.
        """
        import requests

        tagged_url = self._tag_amazon_url(product_url)

        # Calculate savings
        try:
            sale = float(price.replace("$", "").replace(",", ""))
            orig = float(original_price.replace("$", "").replace(",", ""))
            savings = orig - sale
            savings_pct = int((savings / orig) * 100)
            savings_text = f"Save ${savings:.2f} ({savings_pct}% off)"
        except (ValueError, ZeroDivisionError):
            savings_text = "Great deal!"

        embed = {
            "title": f"🔥 {title}",
            "url": tagged_url,
            "description": description or savings_text,
            "color": 0xFF6600,  # Orange
            "fields": [
                {"name": "💰 Sale Price", "value": f"**{price}**", "inline": True},
                {"name": "~~Original~~", "value": f"~~{original_price}~~", "inline": True},
                {"name": "💵 Savings", "value": savings_text, "inline": True},
                {"name": "📦 Category", "value": category, "inline": True},
            ],
            "footer": {
                "text": f"Posted at {datetime.now().strftime('%H:%M')} • Click to buy!"
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if image_url:
            embed["thumbnail"] = {"url": image_url}

        if self.vip_paypal_link:
            embed["fields"].append({
                "name": "⭐ Get VIP Deals",
                "value": f"[Join VIP ($4.99/mo)]({self.vip_paypal_link}) — exclusive deals before anyone else!",
                "inline": False,
            })

        payload = {
            "username": "🤖 DealBot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/3132/3132693.png",
            "embeds": [embed],
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info(f"Deal posted: {title} at {price}")
                return True
            else:
                logger.error(f"Discord post failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Discord post exception: {e}")
            return False

    def post_multiple_deals(self, deals: List[dict], delay_seconds: float = 2.0) -> int:
        """Post a batch of deals with delay between each."""
        posted = 0
        for deal in deals:
            if self.post_deal(**deal):
                posted += 1
            time.sleep(delay_seconds)
        logger.info(f"Posted {posted}/{len(deals)} deals to Discord")
        return posted

    def post_gift_card_alert(self, code: str, value: float, expires: str = "") -> bool:
        """Post a free gift card giveaway (drives engagement)."""
        import requests

        embed = {
            "title": "🎁 FREE Amazon Gift Card Giveaway!",
            "description": (
                f"**Code:** ||{code}||\n"
                f"**Value:** ${value:.2f}\n"
                f"{'**Expires:** ' + expires if expires else ''}\n\n"
                "⚡ First come, first served! React 🎉 if you got it!"
            ),
            "color": 0x00CC44,
            "footer": {"text": "More freebies in #vip-deals | Subscribe for early access"},
        }

        if self.vip_paypal_link:
            embed["fields"] = [
                {
                    "name": "🔔 Want MORE free codes?",
                    "value": f"[Get VIP Access]({self.vip_paypal_link}) — daily exclusive codes!",
                }
            ]

        payload = {"username": "🎁 GiftBot", "embeds": [embed]}

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception:
            return False
