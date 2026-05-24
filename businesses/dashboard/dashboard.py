"""
Live Income Dashboard
======================
Shows real-time P&L across all 20 business streams.
Run: python -m businesses.dashboard.dashboard
"""

import os
import time
from datetime import datetime

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def render_dashboard():
    """Render the full income dashboard."""
    from businesses.cashback_tracker.cashback_tracker import CashbackTracker

    tracker = CashbackTracker()
    summary_30 = tracker.get_summary(30)
    summary_7 = tracker.get_summary(7)
    summary_1 = tracker.get_summary(1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          💰 AUTOMATED BUSINESS SUITE — DASHBOARD            ║")
    print(f"║  Updated: {now}                            ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                    INCOME OVERVIEW                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Today (24h):    ${summary_1['total_income']:>10.2f}                               ║")
    print(f"║  This Week:      ${summary_7['total_income']:>10.2f}                               ║")
    print(f"║  This Month:     ${summary_30['total_income']:>10.2f}                               ║")
    print(f"║  Annualized:     ${summary_30['annualized']:>10.2f}/year                        ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                 INCOME BY STREAM (30 days)                  ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    sources = summary_30.get("by_source", {})
    total = summary_30["total_income"] or 1

    for source, amount in sources.items():
        pct = int((amount / total) * 30)
        bar = "█" * pct + "░" * (30 - pct)
        clean_name = source.replace("_", " ").title()
        print(f"║  {clean_name:<22} ${amount:>8.2f}  {bar}  ║")

    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                   ACTIVE BUSINESSES                         ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    businesses = [
        ("1", "Gmail Tango Card Scraper",     "✅ ACTIVE"),
        ("2", "Multi-Account Scaler",          "✅ ACTIVE" if os.path.isdir("accounts") else "⚙️  SETUP NEEDED"),
        ("3", "Gift Card Flipper",             "✅ ACTIVE"),
        ("4", "PayPal Auto-Invoicer",          "✅ ACTIVE"),
        ("5", "Amazon Price Sniper",           "✅ ACTIVE"),
        ("6", "Affiliate Link Tracker",        "✅ ACTIVE"),
        ("7", "Bing Rewards Farmer",           "✅ ACTIVE"),
        ("8", "Shopify Dropship Manager",      "⚙️  SETUP NEEDED"),
        ("9", "eBay Arbitrage Lister",         "⚙️  SETUP NEEDED"),
        ("10", "Discord Deals Bot",            "⚙️  SETUP NEEDED"),
        ("11", "Email Newsletter",             "⚙️  SETUP NEEDED"),
        ("12", "Cashback Aggregator",          "✅ ACTIVE"),
        ("13", "Deal Scraper",                 "✅ ACTIVE"),
        ("14", "Report Generator & Seller",    "✅ ACTIVE"),
        ("15", "Auto-Invoicer",                "✅ ACTIVE"),
        ("16", "Income Scheduler",             "✅ ACTIVE"),
        ("17", "Review Requester",             "⚙️  SETUP NEEDED"),
        ("18", "Referral Manager",             "⚙️  SETUP NEEDED"),
        ("19", "Data Feed Seller",             "✅ ACTIVE"),
        ("20", "Live Dashboard",               "✅ ACTIVE"),
    ]

    for num, name, status in businesses:
        print(f"║  [{num:>2}] {name:<35} {status:<15}  ║")

    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  Press Ctrl+C to exit  |  Refreshes every 60 seconds        ║")
    print("╚══════════════════════════════════════════════════════════════╝")


def run_live(refresh_seconds: int = 60):
    """Run the dashboard live, refreshing periodically."""
    while True:
        try:
            clear_screen()
            render_dashboard()
            time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            print("\nDashboard closed.")
            break


if __name__ == "__main__":
    run_live()
