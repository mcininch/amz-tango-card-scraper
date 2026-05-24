"""
Referral Manager
================
Tracks and automates referral programs across platforms:
  - Rakuten ($30 referral bonus per signup)
  - Ibotta ($20 per referral)
  - Fetch Rewards ($2 per referral)
  - Drop ($5 per referral)
  - Capital One Shopping (cashback referrals)

Strategy: Post referral links in Reddit, Facebook, Discord.
Revenue: 50 referrals/month × $10 avg = $500/month.
PayPal: jayjay@collector.org (@digitalempiresk)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
}

REFERRAL_PROGRAMS = {
    "rakuten": {
        "name": "Rakuten",
        "bonus": 30.00,
        "description": "$30 bonus when referral makes first purchase",
        "payout": "PayPal or check",
        "referral_url": "",  # Fill in your referral URL
    },
    "ibotta": {
        "name": "Ibotta",
        "bonus": 20.00,
        "description": "$20 when referral redeems first offer",
        "payout": "PayPal or Venmo",
        "referral_url": "",
    },
    "fetch": {
        "name": "Fetch Rewards",
        "bonus": 2.00,
        "description": "$2 per referral (paid in points)",
        "payout": "Gift cards",
        "referral_url": "",
    },
    "drop": {
        "name": "Drop",
        "bonus": 5.00,
        "description": "$5 per referral signup",
        "payout": "Gift cards / PayPal",
        "referral_url": "",
    },
    "capital_one": {
        "name": "Capital One Shopping",
        "bonus": 15.00,
        "description": "$15 per referral who installs and shops",
        "payout": "Credits",
        "referral_url": "",
    },
}


class ReferralManager:
    """Tracks referral signups and revenue across all programs."""

    def __init__(self, data_file: str = "referrals.json"):
        self.data_file = data_file
        self.referrals: List[Dict] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.data_file):
            with open(self.data_file) as f:
                self.referrals = json.load(f)
            logger.info(f"Loaded {len(self.referrals)} referral records")

    def _save(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump(self.referrals, f, indent=2)

    def record_referral(self, program: str, referral_email: str, status: str = "pending") -> Dict:
        """Log a new referral."""
        program_info = REFERRAL_PROGRAMS.get(program, {})
        record = {
            "program": program,
            "referral_email": referral_email,
            "bonus": program_info.get("bonus", 0),
            "status": status,  # pending / confirmed / paid
            "date": datetime.now().isoformat(),
            "payout_to": PAYPAL_CONFIG["email"],
        }
        self.referrals.append(record)
        self._save()
        logger.info(f"Referral recorded: {program} → {referral_email} (${record['bonus']:.2f} pending)")
        return record

    def confirm_referral(self, referral_email: str, program: str) -> bool:
        """Mark a referral as confirmed (paid out)."""
        for ref in self.referrals:
            if ref["referral_email"] == referral_email and ref["program"] == program:
                ref["status"] = "confirmed"
                self._save()
                logger.info(f"Referral confirmed: {program} → {referral_email} → ${ref['bonus']:.2f}")
                return True
        return False

    def get_summary(self) -> Dict:
        """Total referral earnings and pending bonuses."""
        total_earned = sum(r["bonus"] for r in self.referrals if r["status"] == "confirmed")
        total_pending = sum(r["bonus"] for r in self.referrals if r["status"] == "pending")
        by_program = {}
        for r in self.referrals:
            p = r["program"]
            if p not in by_program:
                by_program[p] = {"count": 0, "earned": 0.0}
            by_program[p]["count"] += 1
            if r["status"] == "confirmed":
                by_program[p]["earned"] += r["bonus"]

        return {
            "total_referrals": len(self.referrals),
            "total_earned": round(total_earned, 2),
            "total_pending": round(total_pending, 2),
            "by_program": by_program,
            "paypal_payout": PAYPAL_CONFIG["handle"],
        }

    def get_posting_templates(self) -> List[str]:
        """Get ready-to-post referral promotion copy for Reddit/Facebook."""
        templates = []
        for key, prog in REFERRAL_PROGRAMS.items():
            if prog.get("referral_url"):
                templates.append(
                    f"🎁 Get {prog['name']} FREE + ${prog['bonus']:.0f} bonus!\n"
                    f"{prog['description']}\n"
                    f"Sign up here: {prog['referral_url']}\n"
                    f"Questions? Email {PAYPAL_CONFIG['email']}"
                )
        return templates
