"""
eBay Arbitrage Auto-Lister
===========================
Find products cheap on Amazon → auto-list on eBay at higher price.
When someone buys on eBay, you order from Amazon and ship to buyer.
This is retail arbitrage / dropshipping — fully legal.

eBay API docs: https://developer.ebay.com/develop/apis
Get keys at:   https://developer.ebay.com/my/keys

Profit model:
  Buy on Amazon: $20 (with gift card = $15 net)
  Sell on eBay:  $35
  eBay fee:      ~$4.72 (13.5%)
  Net profit:    ~$15 per item

Setup:
  1. Register at https://developer.ebay.com
  2. Create a keyset (Sandbox first, then Production)
  3. Add token to config.yaml ebay section
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

EBAY_SANDBOX_BASE = "https://api.sandbox.ebay.com"
EBAY_PROD_BASE = "https://api.ebay.com"


@dataclass
class EbayListing:
    """Represents an eBay listing."""
    title: str
    asin: str                   # Amazon ASIN to source from
    amazon_price: float         # What you pay on Amazon
    ebay_price: float           # What you charge on eBay
    category_id: str            # eBay category ID
    condition: str = "NEW"
    description: str = ""
    quantity: int = 1
    listing_id: Optional[str] = None
    status: str = "draft"       # draft | active | sold


class EbayAutoLister:
    """Manages eBay listings for arbitrage."""

    POPULAR_CATEGORIES = {
        "Electronics": "CE",
        "Headphones": "112529",
        "Phones": "9355",
        "Computers": "58058",
        "Video Games": "139973",
        "Toys": "220",
        "Home": "11700",
    }

    def __init__(self, oauth_token: str, sandbox: bool = True):
        self.oauth_token = oauth_token
        self.base_url = EBAY_SANDBOX_BASE if sandbox else EBAY_PROD_BASE
        self.listings: List[EbayListing] = []

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.oauth_token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        }

    def create_listing(self, listing: EbayListing) -> Optional[str]:
        """
        Create an eBay listing via the Inventory API.

        Returns:
            eBay listing ID on success, None on failure.
        """
        sku = f"AMZ-{listing.asin}-{int(time.time())}"

        # Create inventory item
        inventory_payload = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": listing.quantity
                }
            },
            "condition": listing.condition,
            "product": {
                "title": listing.title,
                "description": listing.description or f"Brand new {listing.title}. Fast shipping!",
                "aspects": {"Brand": ["Generic"]},
            },
        }

        inv_resp = requests.put(
            f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}",
            headers=self._headers(),
            json=inventory_payload,
            timeout=30,
        )

        if inv_resp.status_code not in (200, 201, 204):
            logger.error(f"Inventory create failed: {inv_resp.text}")
            return None

        # Create offer
        offer_payload = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "listingDuration": "GTC",
            "availableQuantity": listing.quantity,
            "categoryId": listing.category_id,
            "pricingSummary": {
                "price": {"value": str(listing.ebay_price), "currency": "USD"}
            },
            "listingPolicies": {
                "fulfillmentPolicyId": "YOUR_FULFILLMENT_POLICY_ID",
                "paymentPolicyId": "YOUR_PAYMENT_POLICY_ID",
                "returnPolicyId": "YOUR_RETURN_POLICY_ID",
            },
        }

        offer_resp = requests.post(
            f"{self.base_url}/sell/inventory/v1/offer",
            headers=self._headers(),
            json=offer_payload,
            timeout=30,
        )

        if offer_resp.status_code not in (200, 201):
            logger.error(f"Offer create failed: {offer_resp.text}")
            return None

        offer_data = offer_resp.json()
        offer_id = offer_data.get("offerId")

        # Publish offer
        pub_resp = requests.post(
            f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish",
            headers=self._headers(),
            timeout=30,
        )

        if pub_resp.status_code in (200, 201):
            listing_id = pub_resp.json().get("listingId")
            listing.listing_id = listing_id
            listing.status = "active"
            self.listings.append(listing)
            logger.info(f"Listed '{listing.title}' on eBay at ${listing.ebay_price} (ID: {listing_id})")
            return listing_id
        else:
            logger.error(f"Publish failed: {pub_resp.text}")
            return None

    def bulk_list(self, items: List[Dict]) -> List[EbayListing]:
        """
        List multiple items at once.

        Args:
            items: List of dicts with listing data.

        Returns:
            List of created EbayListing objects.
        """
        results = []
        for item in items:
            listing = EbayListing(**item)
            listing_id = self.create_listing(listing)
            if listing_id:
                results.append(listing)
            time.sleep(2)  # rate limit
        logger.info(f"Bulk listed {len(results)}/{len(items)} items")
        return results

    def calculate_profit(self, amazon_price: float, ebay_price: float, ebay_fee_rate: float = 0.135) -> Dict:
        """Calculate profit on an arbitrage flip."""
        ebay_fee = ebay_price * ebay_fee_rate
        paypal_fee = ebay_price * 0.029 + 0.30  # legacy PayPal calc
        net_profit = ebay_price - amazon_price - ebay_fee - paypal_fee

        return {
            "amazon_cost": amazon_price,
            "ebay_price": ebay_price,
            "ebay_fee": round(ebay_fee, 2),
            "net_profit": round(net_profit, 2),
            "roi_pct": round((net_profit / amazon_price) * 100, 1),
        }


# Example profitable items to list
PROVEN_ARBITRAGE_ITEMS = [
    {
        "title": "Apple AirPods 3rd Generation Wireless Earbuds",
        "asin": "B09JQMJHXY",
        "amazon_price": 149.00,
        "ebay_price": 185.00,
        "category_id": "112529",
    },
    {
        "title": "Anker 65W USB-C Charging Brick Fast Charger",
        "asin": "B09C7DYG4J",
        "amazon_price": 19.99,
        "ebay_price": 29.99,
        "category_id": "67862",
    },
    {
        "title": "Fire TV Stick 4K Max Streaming Device",
        "asin": "B09BKDGG4Q",
        "amazon_price": 34.99,
        "ebay_price": 49.99,
        "category_id": "168058",
    },
]
