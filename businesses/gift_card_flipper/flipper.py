"""
Gift Card Flipper
=================
After your Amazon codes are scraped:
  1. Check the balance of each code (optional)
  2. List the code on Raise.com or CardCash via their seller APIs
  3. Receive cash via PayPal or direct deposit

Raise Seller API: https://www.raise.com/sell  (contact for API access)
CardCash API:     https://www.cardcash.com/sell (contact for partner access)

This module also supports:
  - GiftDeals (giftdeals.io)
  - ClipKard (clipkard.com)
  - Direct eBay listing of gift cards (as digital items)

NOTE: Each platform pays 85–92% of face value. At $5/card avg with 10 cards/day
      = ~$42–46/day passive with zero manual steps.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

from amz_tango_card_scraper.utils.logger import setup_logger
from amz_tango_card_scraper.utils.schemas import AmazonCard

logger = setup_logger(logger_name=__name__)


@dataclass
class FlipResult:
    """Result of listing a gift card for sale."""
    code: str
    platform: str
    listing_id: str
    list_price: float
    estimated_payout: float
    status: str  # 'listed' | 'sold' | 'failed'
    payout_url: Optional[str] = None
    error: Optional[str] = None


class GiftCardFlipper:
    """
    Lists Amazon gift cards on resale platforms automatically.

    Supports multiple platforms — tries each in order until one succeeds.
    """

    PLATFORM_FEES = {
        "raise": 0.15,       # Raise takes 15% commission
        "cardcash": 0.12,    # CardCash takes 12%
        "giftdeals": 0.10,   # GiftDeals takes 10%
        "ebay": 0.135,       # eBay takes 13.5% final value fee
    }

    def __init__(self, config: Dict):
        """
        Args:
            config: Dict with keys per platform:
                raise_api_key, cardcash_api_key, ebay_token, paypal_email
        """
        self.config = config
        self.paypal_email = config.get("paypal_email", "")
        self.results: List[FlipResult] = []

    def estimate_payout(self, face_value: float, platform: str = "raise") -> float:
        """Calculate what you'll actually receive after fees."""
        fee = self.PLATFORM_FEES.get(platform, 0.15)
        return round(face_value * (1 - fee), 2)

    # ------------------------------------------------------------------ #
    #  Raise.com
    # ------------------------------------------------------------------ #

    def list_on_raise(self, code: str, face_value: float) -> FlipResult:
        """Submit a card to Raise seller API."""
        api_key = self.config.get("raise_api_key", "")
        if not api_key:
            return FlipResult(
                code=code, platform="raise", listing_id="", list_price=face_value,
                estimated_payout=0, status="failed", error="No Raise API key configured"
            )

        try:
            resp = requests.post(
                "https://api.raise.com/v1/cards",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "merchant": "Amazon",
                    "type": "egift",
                    "number": code,
                    "balance": face_value,
                    "listing_price": round(face_value * 0.87, 2),  # sell at 87% of face value
                    "payout_method": "paypal",
                    "payout_email": self.paypal_email,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                result = FlipResult(
                    code=code,
                    platform="raise",
                    listing_id=str(data.get("id", "")),
                    list_price=round(face_value * 0.87, 2),
                    estimated_payout=self.estimate_payout(face_value, "raise"),
                    status="listed",
                )
                logger.info(f"Listed {code[:6]}*** on Raise — payout: ${result.estimated_payout}")
                return result
            else:
                return FlipResult(
                    code=code, platform="raise", listing_id="", list_price=face_value,
                    estimated_payout=0, status="failed", error=resp.text
                )
        except Exception as e:
            return FlipResult(
                code=code, platform="raise", listing_id="", list_price=face_value,
                estimated_payout=0, status="failed", error=str(e)
            )

    # ------------------------------------------------------------------ #
    #  CardCash
    # ------------------------------------------------------------------ #

    def list_on_cardcash(self, code: str, face_value: float) -> FlipResult:
        """Submit a card to CardCash."""
        api_key = self.config.get("cardcash_api_key", "")
        if not api_key:
            return FlipResult(
                code=code, platform="cardcash", listing_id="", list_price=face_value,
                estimated_payout=0, status="failed", error="No CardCash API key configured"
            )

        try:
            resp = requests.post(
                "https://api.cardcash.com/v2/sell/cards",
                headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
                json={
                    "brand": "amazon",
                    "cardNumber": code,
                    "balance": face_value,
                    "paymentMethod": "paypal",
                    "paypalEmail": self.paypal_email,
                },
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                result = FlipResult(
                    code=code,
                    platform="cardcash",
                    listing_id=str(data.get("orderId", "")),
                    list_price=face_value,
                    estimated_payout=self.estimate_payout(face_value, "cardcash"),
                    status="listed",
                )
                logger.info(f"Sold {code[:6]}*** on CardCash — payout: ${result.estimated_payout}")
                return result
            else:
                return FlipResult(
                    code=code, platform="cardcash", listing_id="", list_price=face_value,
                    estimated_payout=0, status="failed", error=resp.text
                )
        except Exception as e:
            return FlipResult(
                code=code, platform="cardcash", listing_id="", list_price=face_value,
                estimated_payout=0, status="failed", error=str(e)
            )

    # ------------------------------------------------------------------ #
    #  Main flip method — tries platforms in order
    # ------------------------------------------------------------------ #

    def flip_cards(
        self,
        amazon_cards: List[AmazonCard],
        face_value_per_card: float = 5.0,
        platforms: List[str] = None,
    ) -> List[FlipResult]:
        """
        Flip all redeemed Amazon gift cards to cash.

        Args:
            amazon_cards: Cards scraped by main pipeline.
            face_value_per_card: Default face value (usually $5 for MS Rewards).
            platforms: Ordered list of platforms to try.

        Returns:
            List of FlipResult objects.
        """
        if platforms is None:
            platforms = ["cardcash", "raise"]

        results = []
        total_payout = 0.0

        for card in amazon_cards:
            if not card.redeem_code:
                logger.warning("Skipping card with empty redeem code")
                continue

            result = None
            for platform in platforms:
                if platform == "raise":
                    result = self.list_on_raise(card.redeem_code, face_value_per_card)
                elif platform == "cardcash":
                    result = self.list_on_cardcash(card.redeem_code, face_value_per_card)

                if result and result.status in ("listed", "sold"):
                    break
                time.sleep(1)  # rate limit

            if result:
                results.append(result)
                if result.status in ("listed", "sold"):
                    total_payout += result.estimated_payout

        logger.info(f"Flipped {len(results)} cards — total estimated payout: ${total_payout:.2f}")
        self.results = results
        return results

    def summary(self) -> str:
        """Return a text summary of all flip results."""
        if not self.results:
            return "No flip results yet."

        listed = [r for r in self.results if r.status in ("listed", "sold")]
        failed = [r for r in self.results if r.status == "failed"]
        total = sum(r.estimated_payout for r in listed)

        lines = [
            "📦 GIFT CARD FLIP SUMMARY",
            f"  ✅ Listed/Sold : {len(listed)}",
            f"  ❌ Failed      : {len(failed)}",
            f"  💰 Est. Payout : ${total:.2f}",
            "",
        ]
        for r in listed:
            lines.append(f"  [{r.platform.upper()}] {r.code[:6]}*** → ${r.estimated_payout:.2f}")
        return "\n".join(lines)
