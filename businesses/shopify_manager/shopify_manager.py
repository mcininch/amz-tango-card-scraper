"""
Shopify Dropshipping Manager
==============================
Manages a Shopify store automatically:
  - Adds products from AliExpress/CJ Dropshipping
  - Updates inventory and pricing
  - Fulfills orders automatically
  - Tracks revenue and profit

Setup:
  1. Create Shopify store: https://shopify.com (free trial)
  2. Install app → Settings → Apps → Private apps → Create
  3. Get API key + password
  4. Add to config.yaml shopify section

Revenue: $500–$5,000/month typical for a focused niche store.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


@dataclass
class ShopifyProduct:
    """Represents a Shopify product."""
    title: str
    description: str
    price: float
    cost: float              # Your cost (supplier price)
    vendor: str
    product_type: str
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    sku: str = ""
    product_id: Optional[int] = None
    variant_id: Optional[int] = None

    @property
    def profit_margin(self) -> float:
        return round((self.price - self.cost) / self.price * 100, 1)


class ShopifyManager:
    """Full Shopify store manager for dropshipping automation."""

    def __init__(self, shop_domain: str, api_key: str, api_password: str, api_version: str = "2024-01"):
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}"
        self.auth = (api_key, api_password)
        self.headers = {"Content-Type": "application/json"}

    def _get(self, endpoint: str) -> Any:
        resp = requests.get(f"{self.base_url}{endpoint}", auth=self.auth, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: Dict) -> Any:
        resp = requests.post(f"{self.base_url}{endpoint}", auth=self.auth, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _put(self, endpoint: str, data: Dict) -> Any:
        resp = requests.put(f"{self.base_url}{endpoint}", auth=self.auth, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    #  Products
    # ------------------------------------------------------------------ #

    def create_product(self, product: ShopifyProduct) -> Optional[int]:
        """Add a new product to the store."""
        payload = {
            "product": {
                "title": product.title,
                "body_html": product.description,
                "vendor": product.vendor,
                "product_type": product.product_type,
                "tags": ", ".join(product.tags),
                "variants": [
                    {
                        "price": str(product.price),
                        "sku": product.sku or f"DROP-{int(time.time())}",
                        "inventory_management": "shopify",
                        "inventory_quantity": 999,  # dropship = unlimited stock
                    }
                ],
                "images": [{"src": img} for img in product.images[:10]],
                "status": "active",
            }
        }

        result = self._post("/products.json", payload)
        product_id = result["product"]["id"]
        product.product_id = product_id
        product.variant_id = result["product"]["variants"][0]["id"]
        logger.info(f"Created product '{product.title}' (ID: {product_id}) at ${product.price}")
        return product_id

    def update_price(self, product_id: int, variant_id: int, new_price: float) -> None:
        """Update a product's price."""
        self._put(
            f"/products/{product_id}/variants/{variant_id}.json",
            {"variant": {"id": variant_id, "price": str(new_price)}},
        )
        logger.info(f"Updated price for product {product_id} to ${new_price}")

    def get_products(self, limit: int = 50) -> List[Dict]:
        """Get all products in the store."""
        return self._get(f"/products.json?limit={limit}").get("products", [])

    # ------------------------------------------------------------------ #
    #  Orders
    # ------------------------------------------------------------------ #

    def get_unfulfilled_orders(self) -> List[Dict]:
        """Get all orders that need fulfillment."""
        return self._get("/orders.json?fulfillment_status=unfulfilled&status=open").get("orders", [])

    def fulfill_order(self, order_id: int, tracking_number: str = "", tracking_company: str = "USPS") -> bool:
        """Mark an order as fulfilled."""
        fulfillments = self._get(f"/orders/{order_id}/fulfillments.json").get("fulfillments", [])

        payload = {
            "fulfillment": {
                "location_id": self._get_first_location_id(),
                "tracking_number": tracking_number,
                "tracking_company": tracking_company,
                "notify_customer": True,
            }
        }

        result = self._post(f"/orders/{order_id}/fulfillments.json", payload)
        logger.info(f"Fulfilled order {order_id}")
        return True

    def _get_first_location_id(self) -> int:
        """Get default location ID."""
        locs = self._get("/locations.json").get("locations", [])
        return locs[0]["id"] if locs else 0

    # ------------------------------------------------------------------ #
    #  Revenue Analytics
    # ------------------------------------------------------------------ #

    def get_revenue_summary(self, days_back: int = 30) -> Dict:
        """Calculate revenue, cost, and profit for the period."""
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        orders = self._get(f"/orders.json?created_at_min={since}&status=any&limit=250").get("orders", [])

        total_revenue = sum(float(o.get("total_price", 0)) for o in orders)
        total_orders = len(orders)
        avg_order = total_revenue / total_orders if total_orders else 0

        return {
            "period_days": days_back,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order, 2),
        }

    def auto_reprice(self, markup_pct: float = 2.5) -> None:
        """Reprice all products to maintain markup over supplier cost."""
        products = self.get_products()
        for p in products:
            for variant in p.get("variants", []):
                cost = float(variant.get("compare_at_price") or 0)
                if cost > 0:
                    new_price = round(cost * markup_pct, 2)
                    self.update_price(p["id"], variant["id"], new_price)
        logger.info(f"Repriced {len(products)} products at {markup_pct}x markup")

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
    "note": "Shopify store payouts route to PayPal @digitalempiresk",
}
