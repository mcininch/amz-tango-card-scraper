"""
Dropship Monitor
================
Monitors AliExpress / Alibaba supplier prices and auto-updates
Shopify/eBay listings when costs change to protect margins.

Revenue: 40-60% margins on every dropshipped sale.
PayPal: jayjay@collector.org (@digitalempiresk)
"""

import time
from typing import Dict, List, Optional
from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
}

DEFAULT_MARKUP = 2.5  # Sell at 2.5x supplier cost


class DropshipMonitor:
    """Monitors supplier prices and keeps store listings profitable."""

    def __init__(
        self,
        shopify_domain: str = "",
        shopify_api_key: str = "",
        shopify_password: str = "",
        markup_multiplier: float = DEFAULT_MARKUP,
    ):
        self.shopify_domain = shopify_domain
        self.shopify_api_key = shopify_api_key
        self.shopify_password = shopify_password
        self.markup = markup_multiplier
        self.price_history: Dict[str, List] = {}

    def check_aliexpress_price(self, product_url: str) -> Optional[float]:
        """Fetch current AliExpress price for a product."""
        import requests
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0)"}
            resp = requests.get(product_url, headers=headers, timeout=15)
            # Look for price in page source
            import re
            match = re.search(r'"minActivityAmount":\s*"([\d.]+)"', resp.text)
            if match:
                price = float(match.group(1))
                logger.info(f"AliExpress price: ${price:.2f}")
                return price
        except Exception as e:
            logger.error(f"AliExpress price fetch failed: {e}")
        return None

    def calculate_sell_price(self, cost: float, markup: float = None) -> Dict:
        """Calculate profitable sell price with PayPal fee buffer."""
        m = markup or self.markup
        gross = round(cost * m, 2)
        paypal_fee = round(gross * 0.029 + 0.30, 2)  # 2.9% + $0.30
        net = round(gross - paypal_fee, 2)
        profit = round(net - cost, 2)
        margin_pct = round((profit / gross) * 100, 1) if gross > 0 else 0

        return {
            "cost": cost,
            "sell_price": gross,
            "paypal_fee": paypal_fee,
            "net_received": net,
            "profit": profit,
            "margin_pct": margin_pct,
            "paypal_account": PAYPAL_CONFIG["handle"],
        }

    def update_shopify_price(self, product_id: int, variant_id: int, new_price: float) -> bool:
        """Push updated price to Shopify store."""
        if not self.shopify_domain:
            logger.warning("No Shopify domain configured")
            return False
        import requests
        url = f"https://{self.shopify_domain}/admin/api/2024-01/variants/{variant_id}.json"
        try:
            resp = requests.put(
                url,
                json={"variant": {"id": variant_id, "price": str(new_price)}},
                auth=(self.shopify_api_key, self.shopify_password),
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"Shopify price updated: product {product_id} → ${new_price}")
                return True
        except Exception as e:
            logger.error(f"Shopify update failed: {e}")
        return False

    def monitor_products(self, products: List[Dict], interval_minutes: int = 60) -> None:
        """
        Continuously monitor supplier prices and auto-reprice.

        Args:
            products: List of dicts with supplier_url, product_id, variant_id.
            interval_minutes: How often to check.
        """
        logger.info(f"Dropship monitor started — {len(products)} products, {interval_minutes}min interval")
        while True:
            for p in products:
                cost = self.check_aliexpress_price(p["supplier_url"])
                if cost:
                    pricing = self.calculate_sell_price(cost)
                    logger.info(
                        f"Product {p['product_id']}: cost=${cost:.2f} → "
                        f"sell=${pricing['sell_price']:.2f} (profit=${pricing['profit']:.2f})"
                    )
                    self.update_shopify_price(p["product_id"], p["variant_id"], pricing["sell_price"])
                time.sleep(2)
            logger.info(f"Price check complete. Next check in {interval_minutes} min.")
            time.sleep(interval_minutes * 60)

    def estimate_monthly_revenue(self, monthly_orders: int = 50, avg_profit: float = 12.0) -> Dict:
        """Estimate monthly dropship profit."""
        gross = monthly_orders * avg_profit * self.markup
        profit = monthly_orders * avg_profit
        return {
            "monthly_orders": monthly_orders,
            "gross_revenue": round(gross, 2),
            "net_profit": round(profit, 2),
            "markup": self.markup,
            "paypal_payout": PAYPAL_CONFIG["handle"],
        }
