"""
Master Scheduler — Runs All 20 Businesses Automatically
=========================================================
Sets up cron-like scheduling for all automation modules.
Runs 24/7 in the background making money.

Schedule:
  Every 6 hours:  Gmail scrape + Tango card redemption
  Every 6 hours:  Multi-account runner
  Daily 9am:      Bing rewards farming (all accounts)
  Daily 10am:     Deal scraping + affiliate posting
  Daily 11am:     Price monitor check
  Daily 6pm:      Discord deal posts
  Daily 8pm:      Email newsletter send
  1st of month:   PayPal subscription invoicing
  Weekly Sunday:  Report generation

Usage:
  python -m businesses.scheduler.scheduler
  # Or run with cron: */5 * * * * cd /path && python -m businesses.scheduler.scheduler --check
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

STATE_FILE = "scheduler_state.json"


def load_business_config() -> Dict:
    """Load main config.yaml as well as businesses config."""
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Could not load config: {e}")
        return {}


class Task:
    """A scheduled task."""

    def __init__(
        self,
        name: str,
        fn: Callable,
        interval_hours: float = 24,
        run_at_hour: Optional[int] = None,  # If set, run at specific hour
        enabled: bool = True,
    ):
        self.name = name
        self.fn = fn
        self.interval_hours = interval_hours
        self.run_at_hour = run_at_hour
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0

    def is_due(self) -> bool:
        if not self.enabled:
            return False

        now = datetime.now()

        if self.run_at_hour is not None:
            # Run at specific hour of day
            if now.hour != self.run_at_hour:
                return False
            if self.last_run and self.last_run.date() == now.date():
                return False  # Already ran today
            return True

        # Run every N hours
        if self.last_run is None:
            return True
        return (now - self.last_run).total_seconds() >= self.interval_hours * 3600

    def run(self) -> bool:
        """Execute the task."""
        logger.info(f"▶ Running task: {self.name}")
        start = time.time()
        try:
            self.fn()
            elapsed = time.time() - start
            self.last_run = datetime.now()
            self.run_count += 1
            logger.info(f"✅ Task '{self.name}' completed in {elapsed:.1f}s")
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Task '{self.name}' failed: {e}")
            return False


class MasterScheduler:
    """Orchestrates all 20 automated business modules."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_business_config()
        self.tasks: List[Task] = []
        self._setup_tasks()

    def _setup_tasks(self) -> None:
        """Register all business automation tasks."""

        # ---------------------------------------------------------- #
        # TASK 1 & 2: Core scraper (every 6h)
        # ---------------------------------------------------------- #
        def task_main_scraper():
            from amz_tango_card_scraper.__main__ import main
            main()

        self.tasks.append(Task(
            name="Gmail → Tango → Amazon Scraper",
            fn=task_main_scraper,
            interval_hours=6,
        ))

        # ---------------------------------------------------------- #
        # TASK 3: Multi-account runner (every 6h)
        # ---------------------------------------------------------- #
        def task_multi_account():
            from businesses.multi_account.runner import run_all_accounts
            run_all_accounts(accounts_dir="accounts", max_workers=2)

        self.tasks.append(Task(
            name="Multi-Account Runner",
            fn=task_multi_account,
            interval_hours=6,
            enabled=os.path.isdir("accounts"),
        ))

        # ---------------------------------------------------------- #
        # TASK 4: Gift card flipper (after scraper)
        # ---------------------------------------------------------- #
        def task_flip_cards():
            flip_config = self.config.get("flipper", {})
            if not flip_config:
                logger.info("Flipper not configured — skipping")
                return

            from businesses.gift_card_flipper.flipper import GiftCardFlipper
            from amz_tango_card_scraper.utils.schemas import AmazonCard

            # Load cards from last scrape results
            results_path = "results.txt"
            if not os.path.exists(results_path):
                return

            with open(results_path) as f:
                content = f.read()

            import re
            codes = re.findall(r"Redeem code: ([A-Z0-9\-]{10,})", content)
            cards = [AmazonCard(redeem_code=c, redeem_status=True, amazon_link="") for c in codes]

            if cards:
                flipper = GiftCardFlipper(flip_config)
                results = flipper.flip_cards(cards)
                logger.info(flipper.summary())

        self.tasks.append(Task(
            name="Gift Card Flipper",
            fn=task_flip_cards,
            interval_hours=6,
        ))

        # ---------------------------------------------------------- #
        # TASK 5: Bing Rewards farming (daily at 9am)
        # ---------------------------------------------------------- #
        def task_bing_farming():
            bing_accounts = self.config.get("bing_accounts", [])
            if not bing_accounts:
                logger.info("No Bing accounts configured — skipping")
                return

            from businesses.bing_rewards.bing_farmer import BingRewardsFarmer
            for account in bing_accounts:
                farmer = BingRewardsFarmer(
                    email=account["email"],
                    password=account["password"],
                    headless=True,
                )
                result = farmer.run()
                logger.info(f"Bing farming: {result}")
                time.sleep(30)  # Cool down between accounts

        self.tasks.append(Task(
            name="Bing Rewards Farmer",
            fn=task_bing_farming,
            run_at_hour=9,
        ))

        # ---------------------------------------------------------- #
        # TASK 6: Deal scraping + affiliate posting (daily 10am)
        # ---------------------------------------------------------- #
        def task_deal_scraping():
            aff_config = self.config.get("affiliate", {})
            if not aff_config.get("tag"):
                logger.info("Affiliate tag not configured — skipping")
                return

            from businesses.affiliate_tracker.affiliate_manager import AffiliateManager
            mgr = AffiliateManager(
                affiliate_tag=aff_config["tag"],
                telegram_token=self.config.get("telegram", {}).get("token", ""),
                telegram_chat_id=self.config.get("telegram", {}).get("chat_id", ""),
            )
            deals = mgr.scrape_deal_sites()
            for deal in deals[:5]:  # Post top 5
                if deal.get("has_amazon"):
                    mgr.post_deal_to_telegram(
                        deal_text=deal["title"],
                        product_url=deal["link"],
                    )
            logger.info(f"Posted {min(5, len(deals))} affiliate deals")

        self.tasks.append(Task(
            name="Deal Scraper + Affiliate Poster",
            fn=task_deal_scraping,
            run_at_hour=10,
        ))

        # ---------------------------------------------------------- #
        # TASK 7: Price monitor (daily 11am)
        # ---------------------------------------------------------- #
        def task_price_monitor():
            from businesses.price_monitor.amazon_sniper import PriceSniper, DEFAULT_WATCHLIST
            sniper = PriceSniper(
                watchlist=DEFAULT_WATCHLIST,
                telegram_token=self.config.get("telegram", {}).get("token", ""),
                telegram_chat_id=self.config.get("telegram", {}).get("chat_id", ""),
            )
            sniper.check_once()

        self.tasks.append(Task(
            name="Amazon Price Monitor",
            fn=task_price_monitor,
            run_at_hour=11,
        ))

        # ---------------------------------------------------------- #
        # TASK 8: Discord deal posts (daily 6pm)
        # ---------------------------------------------------------- #
        def task_discord_deals():
            discord_cfg = self.config.get("discord", {})
            if not discord_cfg.get("webhook_url"):
                return

            from businesses.discord_bot.deals_bot import DiscordDealsBot
            from businesses.affiliate_tracker.affiliate_manager import AffiliateManager

            bot = DiscordDealsBot(
                webhook_url=discord_cfg["webhook_url"],
                affiliate_tag=self.config.get("affiliate", {}).get("tag", ""),
                vip_paypal_link=self.config.get("paypal", {}).get("vip_link", ""),
            )
            # Grab some deals to post
            mgr = AffiliateManager(affiliate_tag=self.config.get("affiliate", {}).get("tag", ""))
            deals = mgr.scrape_deal_sites()
            for deal in deals[:3]:
                bot.post_deal(
                    title=deal["title"][:100],
                    price="Check link",
                    original_price="",
                    product_url=deal["link"],
                    description=deal["description"][:200],
                )
                time.sleep(2)

        self.tasks.append(Task(
            name="Discord Deal Posts",
            fn=task_discord_deals,
            run_at_hour=18,
        ))

        # ---------------------------------------------------------- #
        # TASK 9: PayPal subscription invoicing (1st of month)
        # ---------------------------------------------------------- #
        def task_subscription_billing():
            paypal_cfg = self.config.get("paypal", {})
            if not paypal_cfg.get("client_id"):
                return

            from businesses.paypal.paypal_client import PayPalClient
            from businesses.invoicer.auto_invoicer import AutoInvoicer

            pp = PayPalClient(
                client_id=paypal_cfg["client_id"],
                client_secret=paypal_cfg["client_secret"],
                mode=paypal_cfg.get("mode", "sandbox"),
            )
            invoicer = AutoInvoicer(paypal_client=pp)
            invoiced = invoicer.process_due_subscriptions()
            if invoiced:
                logger.info(f"Invoiced {len(invoiced)} subscriptions")

        self.tasks.append(Task(
            name="PayPal Subscription Billing",
            fn=task_subscription_billing,
            interval_hours=24,
        ))

        # ---------------------------------------------------------- #
        # TASK 10: Income tracking update (daily 11pm)
        # ---------------------------------------------------------- #
        def task_update_ledger():
            from businesses.cashback_tracker.cashback_tracker import CashbackTracker
            tracker = CashbackTracker()
            tracker.print_dashboard()

        self.tasks.append(Task(
            name="Income Dashboard Update",
            fn=task_update_ledger,
            run_at_hour=23,
        ))

        logger.info(f"Scheduler initialized with {len(self.tasks)} tasks")

    def run_once(self) -> List[str]:
        """Check all tasks and run any that are due. Returns list of ran task names."""
        ran = []
        for task in self.tasks:
            if task.is_due():
                success = task.run()
                if success:
                    ran.append(task.name)
        return ran

    def run_forever(self, check_interval_seconds: int = 60) -> None:
        """Run scheduler loop forever."""
        logger.info("🚀 Master Scheduler started — all businesses running 24/7")
        logger.info(f"Checking tasks every {check_interval_seconds}s")

        while True:
            try:
                ran = self.run_once()
                if ran:
                    logger.info(f"Completed tasks: {ran}")
                time.sleep(check_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)

    def status(self) -> None:
        """Print status of all tasks."""
        print("\n" + "=" * 60)
        print("📅 SCHEDULER STATUS")
        print("=" * 60)
        for task in self.tasks:
            status = "✅ ON " if task.enabled else "⏸  OFF"
            last = task.last_run.strftime("%H:%M:%S") if task.last_run else "Never"
            due = "DUE NOW" if task.is_due() else "waiting"
            print(f"  {status} | {task.name:<35} | Last: {last} | {due}")
        print("=" * 60)


if __name__ == "__main__":
    scheduler = MasterScheduler()
    if "--status" in sys.argv:
        scheduler.status()
    elif "--once" in sys.argv:
        ran = scheduler.run_once()
        print(f"Ran {len(ran)} tasks: {ran}")
    else:
        scheduler.run_forever()
