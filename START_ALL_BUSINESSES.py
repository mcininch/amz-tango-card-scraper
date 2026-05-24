#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║         🚀 AUTOMATED BUSINESS SUITE — QUICKSTART LAUNCHER           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Run this file to start ALL 20 automated business systems.          ║
║                                                                     ║
║  First time? Run:  python START_ALL_BUSINESSES.py --setup           ║
║  Live dashboard:   python START_ALL_BUSINESSES.py --dashboard       ║
║  Run once now:     python START_ALL_BUSINESSES.py --once            ║
║  Run forever:      python START_ALL_BUSINESSES.py                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_wizard():
    """Interactive setup wizard for all businesses."""
    print("\n" + "=" * 60)
    print("🔧 AUTOMATED BUSINESS SUITE — SETUP WIZARD")
    print("=" * 60)
    print()
    print("This wizard will guide you through setting up each")
    print("business stream. You can skip any you don't want yet.")
    print()

    steps = [
        ("✅ Gmail Scraper", "Already configured in config.yaml", True),
        ("💳 PayPal Integration", "https://developer.paypal.com → My Apps → Create App", False),
        ("🃏 Gift Card Flipper", "Contact cardcash.com for partner API access", False),
        ("🔗 Amazon Affiliate", "https://affiliate-program.amazon.com → Sign up", False),
        ("🔍 Bing Rewards Farm", "Add Microsoft accounts to config.yaml bing_accounts", False),
        ("🛒 Shopify Store", "https://shopify.com → Start free trial → Get API key", False),
        ("📦 eBay Lister", "https://developer.ebay.com → Create keyset", False),
        ("💬 Discord Bot", "Create webhook in your Discord server settings", False),
        ("📧 Email Newsletter", "Gmail app password OR free SendGrid account", False),
        ("📊 Price Monitor", "Edit price_watchlist in config.yaml (ASINs added)", False),
    ]

    print("SETUP CHECKLIST:")
    print("-" * 60)
    for name, instruction, done in steps:
        status = "✅" if done else "⬜"
        print(f"  {status} {name}")
        if not done:
            print(f"       → {instruction}")
    print()
    print("Fill in the relevant sections of config.yaml to activate")
    print("each business stream. Then run: python START_ALL_BUSINESSES.py")
    print()
    print("💡 TIP: Start with PayPal + Gift Card Flipper for fastest ROI.")
    print("        Those two alone can generate $50–200/month with ZERO manual work.")


def show_income_estimate():
    """Show projected monthly income across all streams."""
    streams = [
        ("Gmail → Tango → Amazon (1 account)",  "$5–15",   "Immediately"),
        ("Multi-account × 5 accounts",           "$25–75",  "After setup"),
        ("Gift Card Flipper (CardCash)",          "$20–60",  "After API key"),
        ("PayPal Subscriptions (VIP newsletter)", "$50–500", "After 100 subs"),
        ("Amazon Affiliate Links",                "$20–200", "After 500 clicks"),
        ("Bing Rewards Farm (5 accounts)",        "$25–40",  "After setup"),
        ("eBay Arbitrage",                        "$50–500", "After eBay key"),
        ("Shopify Dropshipping",                  "$200–2K", "After store setup"),
        ("Discord Deals Channel",                 "$10–100", "After 500 members"),
        ("Email Newsletter",                      "$50–499", "After 1K subs"),
        ("Price Drop Sniper",                     "$50–300", "After 1st flip"),
        ("Report Selling (Gumroad)",              "$20–200", "After 1st sale"),
    ]

    print("\n" + "=" * 65)
    print("💰 PROJECTED MONTHLY INCOME (Conservative → Optimistic)")
    print("=" * 65)
    total_low = 0
    total_high = 0
    for name, income, timeline in streams:
        lo, hi = [int(x.replace("$", "").replace("K", "000").replace("+", "")) for x in income.replace("–", " ").split()]
        total_low += lo
        total_high += hi
        print(f"  {name:<45} {income:<12} {timeline}")

    print("-" * 65)
    print(f"  {'TOTAL (all streams active)':<45} ${total_low}–${total_high:,}/mo")
    print(f"  {'ANNUALIZED':<45} ${total_low*12:,}–${total_high*12:,}/yr")
    print("=" * 65)


def main():
    args = sys.argv[1:]

    if "--setup" in args:
        setup_wizard()
        show_income_estimate()
        return

    if "--estimate" in args:
        show_income_estimate()
        return

    if "--dashboard" in args:
        from businesses.dashboard.dashboard import run_live
        run_live()
        return

    if "--once" in args:
        print("🔄 Running all due business tasks once...")
        from businesses.scheduler.scheduler import MasterScheduler
        scheduler = MasterScheduler()
        # Force all tasks to run regardless of schedule
        for task in scheduler.tasks:
            task.last_run = None
        ran = scheduler.run_once()
        print(f"\n✅ Completed {len(ran)} tasks:")
        for name in ran:
            print(f"   • {name}")
        return

    if "--status" in args:
        from businesses.scheduler.scheduler import MasterScheduler
        MasterScheduler().status()
        return

    # Default: run forever
    print("🚀 Starting all automated businesses (24/7 mode)...")
    print("   Press Ctrl+C to stop\n")
    show_income_estimate()
    print()

    from businesses.scheduler.scheduler import MasterScheduler
    scheduler = MasterScheduler()
    scheduler.status()
    print()
    scheduler.run_forever(check_interval_seconds=60)


if __name__ == "__main__":
    main()
