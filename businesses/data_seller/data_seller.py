"""
Data Seller
===========
Packages and sells scraped market data as CSV/JSON datasets on:
  - Gumroad ($9.99 — Amazon price history dataset)
  - DataFiniti / RapidAPI marketplace
  - Direct PayPal purchase

Revenue: 20 sales/month × $9.99 = $200/month passive.
PayPal: jayjay@collector.org (@digitalempiresk)
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Dict, List

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
    "dataset_price": "https://paypal.me/digitalempiresk/9.99",
    "premium_price": "https://paypal.me/digitalempiresk/24.99",
}

GUMROAD_LISTING = {
    "name": "Amazon Price History Dataset — {month}",
    "price": 9.99,
    "description": "10,000+ Amazon product price snapshots. CSV + JSON. Updated weekly.",
    "tags": ["amazon", "price data", "market research", "ecommerce"],
}


class DataSeller:
    """Packages scraped data into sellable datasets."""

    def __init__(self, output_dir: str = "datasets"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def package_price_data(self, price_records: List[Dict]) -> str:
        """Save scraped price data as CSV dataset."""
        month = datetime.now().strftime("%Y-%m")
        filename = os.path.join(self.output_dir, f"amazon_prices_{month}.csv")

        fieldnames = ["asin", "title", "price", "original_price", "savings_pct", "category", "timestamp", "url"]

        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in price_records:
                writer.writerow({k: record.get(k, "") for k in fieldnames})

        logger.info(f"Dataset saved: {filename} ({len(price_records)} records)")
        return filename

    def package_gift_card_data(self, flip_records: List[Dict]) -> str:
        """Package gift card arbitrage data as sellable JSON."""
        month = datetime.now().strftime("%Y-%m")
        filename = os.path.join(self.output_dir, f"gc_arbitrage_{month}.json")

        dataset = {
            "title": f"Gift Card Arbitrage Data — {month}",
            "generated": datetime.now().isoformat(),
            "total_records": len(flip_records),
            "purchase_link": PAYPAL_CONFIG["dataset_price"],
            "contact": PAYPAL_CONFIG["email"],
            "records": flip_records,
        }

        with open(filename, "w") as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"GC dataset saved: {filename}")
        return filename

    def generate_product_listing(self, dataset_path: str) -> Dict:
        """Generate Gumroad/Payhip listing metadata for a dataset."""
        size = os.path.getsize(dataset_path)
        month = datetime.now().strftime("%B %Y")

        return {
            "title": GUMROAD_LISTING["name"].format(month=month),
            "price": GUMROAD_LISTING["price"],
            "description": GUMROAD_LISTING["description"],
            "file_path": dataset_path,
            "file_size_kb": round(size / 1024, 1),
            "payment_link": PAYPAL_CONFIG["dataset_price"],
            "seller_email": PAYPAL_CONFIG["email"],
            "seller_paypal": PAYPAL_CONFIG["handle"],
        }

    def estimate_monthly_revenue(self, sales_per_month: int = 20) -> Dict:
        """Project monthly data selling revenue."""
        basic = sales_per_month * GUMROAD_LISTING["price"]
        premium = int(sales_per_month * 0.3) * 24.99
        return {
            "basic_sales": sales_per_month,
            "basic_revenue": round(basic, 2),
            "premium_sales": int(sales_per_month * 0.3),
            "premium_revenue": round(premium, 2),
            "total_monthly": round(basic + premium, 2),
            "paypal": PAYPAL_CONFIG["handle"],
        }
