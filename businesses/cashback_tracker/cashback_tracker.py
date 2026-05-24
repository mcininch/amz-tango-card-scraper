"""
Cashback & Rewards Aggregator
===============================
Tracks cashback from all your sources in one place:
  - Microsoft Rewards points → cash value
  - Rakuten / BeFrugal cashback
  - Credit card rewards
  - Honey / Capital One Shopping savings
  - Gift card flip profits

Calculates true net income across all streams.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

# Microsoft Rewards: 1 point ≈ $0.01
MS_POINTS_VALUE = 0.01

# Cashback site rates (approximate)
CASHBACK_RATES = {
    "rakuten": {"amazon": 0.01, "walmart": 0.02, "ebay": 0.01, "default": 0.02},
    "befrugal": {"amazon": 0.01, "default": 0.025},
    "swagbucks": {"default": 0.01},
    "honey": {"default": 0.01},
}


@dataclass
class CashbackEntry:
    """A single cashback/reward event."""
    source: str          # 'microsoft_rewards' | 'rakuten' | 'gift_card_flip' | etc.
    amount: float        # Dollar value
    description: str
    date: str = ""
    redeemed: bool = False

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")


class CashbackTracker:
    """Tracks all income streams in one unified ledger."""

    def __init__(self, state_file: str = "cashback_ledger.json"):
        self.state_file = state_file
        self.entries: List[CashbackEntry] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                self.entries = [CashbackEntry(**e) for e in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.state_file, "w") as f:
            json.dump([vars(e) for e in self.entries], f, indent=2)

    def add_ms_rewards(self, points: int, description: str = "Microsoft Rewards") -> float:
        """Convert Microsoft Rewards points to dollar value and log it."""
        value = round(points * MS_POINTS_VALUE, 2)
        self.entries.append(CashbackEntry(source="microsoft_rewards", amount=value, description=description))
        self._save()
        logger.info(f"Logged {points} MS Rewards points = ${value:.2f}")
        return value

    def add_gift_card_flip(self, face_value: float, payout: float, platform: str = "cardcash") -> float:
        """Log a gift card flip profit."""
        profit = payout - 0  # Already net
        entry = CashbackEntry(
            source=f"gift_card_flip_{platform}",
            amount=payout,
            description=f"Flipped ${face_value:.2f} GC on {platform}",
        )
        self.entries.append(entry)
        self._save()
        logger.info(f"Logged GC flip: ${payout:.2f} from {platform}")
        return payout

    def add_cashback(self, source: str, amount: float, description: str = "") -> None:
        """Log any cashback amount."""
        self.entries.append(CashbackEntry(source=source, amount=amount, description=description or source))
        self._save()
        logger.info(f"Logged ${amount:.2f} cashback from {source}")

    def add_affiliate_commission(self, amount: float, clicks: int = 0) -> None:
        """Log affiliate commission earned."""
        self.entries.append(CashbackEntry(
            source="affiliate_amazon",
            amount=amount,
            description=f"Amazon affiliate commission ({clicks} clicks)",
        ))
        self._save()

    def add_paypal_payment(self, amount: float, from_name: str = "Client") -> None:
        """Log a PayPal payment received."""
        self.entries.append(CashbackEntry(
            source="paypal_invoice",
            amount=amount,
            description=f"Payment from {from_name}",
        ))
        self._save()

    def get_summary(self, days_back: int = 30) -> Dict:
        """Get income summary for the past N days."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        recent = [e for e in self.entries if e.date >= cutoff]

        by_source: Dict[str, float] = {}
        for entry in recent:
            by_source[entry.source] = by_source.get(entry.source, 0) + entry.amount

        total = sum(e.amount for e in recent)

        return {
            "period_days": days_back,
            "total_income": round(total, 2),
            "by_source": {k: round(v, 2) for k, v in sorted(by_source.items(), key=lambda x: -x[1])},
            "entry_count": len(recent),
            "annualized": round(total / days_back * 365, 2),
        }

    def print_dashboard(self) -> None:
        """Print a nice income dashboard to console."""
        summary = self.get_summary(30)
        print("\n" + "=" * 50)
        print("💰 INCOME DASHBOARD (Last 30 Days)")
        print("=" * 50)
        print(f"  Total Income:     ${summary['total_income']:.2f}")
        print(f"  Annualized:       ${summary['annualized']:.2f}/year")
        print(f"  Transactions:     {summary['entry_count']}")
        print()
        print("  By Source:")
        for source, amount in summary["by_source"].items():
            bar = "█" * int(amount / max(summary["by_source"].values()) * 20)
            print(f"  {source:<30} ${amount:>8.2f}  {bar}")
        print("=" * 50)
