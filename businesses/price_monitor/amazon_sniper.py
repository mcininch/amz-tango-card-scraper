"""
Amazon Price Drop Sniper
=========================
Monitors Amazon product prices continuously.
When a product drops below your target price:
  1. Alerts you via Telegram
  2. Optionally auto-buys via Amazon (if redeem_amz is on, use the GC balance)
  3. Can re-list on eBay/Mercari for profit (arbitrage)

Revenue model: Buy low → sell higher = $5–50 profit per flip.

Usage:
  from businesses.price_monitor.amazon_sniper import PriceSniper
  sniper = PriceSniper(watchlist=[...], telegram_token="...", chat_id="...")
  sniper.run_forever(interval_minutes=30)
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


@dataclass
class WatchedProduct:
    """A product being monitored."""
    name: str
    asin: str
    target_price: float
    sell_price: float  # Price to re-list at for profit
    current_price: float = 0.0
    last_checked: float = 0.0
    alert_sent: bool = False

    @property
    def profit_margin(self) -> float:
        return self.sell_price - self.current_price

    @property
    def url(self) -> str:
        return f"https://www.amazon.com/dp/{self.asin}"


class PriceSniper:
    """Monitors Amazon prices and alerts / auto-buys when target hit."""

    def __init__(
        self,
        watchlist: List[Dict],
        telegram_token: str = "",
        telegram_chat_id: str = "",
        state_file: str = "price_monitor_state.json",
    ):
        self.products = [WatchedProduct(**p) for p in watchlist]
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.state_file = state_file
        self._load_state()

    def _load_state(self) -> None:
        """Load previous price state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                for p in self.products:
                    if p.asin in state:
                        p.current_price = state[p.asin].get("price", 0.0)
                        p.alert_sent = state[p.asin].get("alert_sent", False)
            except Exception:
                pass

    def _save_state(self) -> None:
        """Persist current prices to disk."""
        state = {p.asin: {"price": p.current_price, "alert_sent": p.alert_sent} for p in self.products}
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _get_price(self, product: WatchedProduct) -> Optional[float]:
        """Scrape current price from Amazon product page."""
        try:
            resp = requests.get(product.url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple price selectors (Amazon changes layout)
            selectors = [
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                ".a-price .a-offscreen",
                "#corePrice_feature_div .a-price .a-offscreen",
                ".a-price-whole",
            ]

            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    price_text = el.get_text(strip=True).replace("$", "").replace(",", "")
                    try:
                        return float(price_text.split()[0])
                    except ValueError:
                        continue

            return None
        except Exception as e:
            logger.warning(f"Price fetch failed for {product.asin}: {e}")
            return None

    def _send_telegram(self, message: str) -> None:
        """Send Telegram alert."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.info(f"[ALERT] {message}")
            return

        try:
            requests.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Telegram alert failed: {e}")

    def check_once(self) -> List[WatchedProduct]:
        """Check all products once. Returns list of triggered products."""
        triggered = []

        for product in self.products:
            price = self._get_price(product)
            if price is None:
                continue

            product.current_price = price
            product.last_checked = time.time()

            logger.info(f"{product.name}: ${price:.2f} (target: ${product.target_price:.2f})")

            if price <= product.target_price and not product.alert_sent:
                product.alert_sent = True
                triggered.append(product)

                msg = (
                    f"🎯 <b>PRICE ALERT!</b>\n"
                    f"📦 {product.name}\n"
                    f"💰 Current: <b>${price:.2f}</b>\n"
                    f"🎯 Target:  ${product.target_price:.2f}\n"
                    f"📈 Sell at: ${product.sell_price:.2f}\n"
                    f"💵 Profit:  ${product.profit_margin:.2f}\n"
                    f"🔗 {product.url}"
                )
                self._send_telegram(msg)
                logger.info(f"🎯 Price hit for {product.name}! ${price:.2f}")

            elif price > product.target_price and product.alert_sent:
                # Price went back up — reset alert so we catch it next time
                product.alert_sent = False

        self._save_state()
        return triggered

    def run_forever(self, interval_minutes: int = 30) -> None:
        """Run price checks in a loop forever."""
        logger.info(f"Price sniper started — checking {len(self.products)} products every {interval_minutes} min")
        while True:
            triggered = self.check_once()
            if triggered:
                logger.info(f"{len(triggered)} products hit target price!")
            time.sleep(interval_minutes * 60)


# Example watchlist — edit these to products you want to flip
DEFAULT_WATCHLIST = [
    {
        "name": "Apple AirPods Pro 2nd Gen",
        "asin": "B0BDHWDR12",
        "target_price": 179.00,   # buy below this
        "sell_price": 220.00,     # relist at this
    },
    {
        "name": "Nintendo Switch OLED",
        "asin": "B098RL6SBJ",
        "target_price": 249.00,
        "sell_price": 300.00,
    },
    {
        "name": "Sony WH-1000XM5 Headphones",
        "asin": "B09XS7JWHH",
        "target_price": 280.00,
        "sell_price": 340.00,
    },
]

PAYPAL_PAYOUT = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
    "note": "eBay flip profits → PayPal @digitalempiresk",
}
