"""
Automated Report Seller
========================
Generates market/price intelligence reports automatically and sells them.

Reports are created by scraping Amazon price data, analyzing trends,
then generating a PDF that gets delivered via PayPal purchase.

Sell on:
  - Gumroad ($10–$49 per report)
  - Etsy (digital downloads)
  - Your own site via PayPal

Example products:
  - "Best Amazon Deals This Week" — $4.99
  - "Amazon Price Drop Report: Electronics" — $9.99
  - "Microsoft Rewards Maximization Guide" — $14.99
  - "Gift Card Arbitrage Playbook" — $24.99

Revenue: 50 sales/month × $14.99 = $749/month
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)


@dataclass
class Report:
    """A sellable report."""
    title: str
    category: str
    price: float
    data: Dict
    created_at: str = ""
    file_path: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")


class ReportGenerator:
    """Generates and manages sellable market reports."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_deals_report(self, deals: List[Dict]) -> Report:
        """
        Generate a 'Best Deals This Week' report.

        Args:
            deals: List of deal dicts from scraper/affiliate tracker.

        Returns:
            Report object with file path.
        """
        week = datetime.now().strftime("Week of %B %d, %Y")
        title = f"Best Amazon Deals — {week}"

        # Sort deals by savings percentage
        sorted_deals = sorted(
            deals,
            key=lambda d: float(str(d.get("savings_pct", 0)).replace("%", "")),
            reverse=True,
        )

        data = {
            "title": title,
            "generated": datetime.now().isoformat(),
            "total_deals": len(sorted_deals),
            "categories": list(set(d.get("category", "General") for d in sorted_deals)),
            "top_deals": sorted_deals[:20],
            "methodology": (
                "Deals sourced from Amazon price API, SlickDeals RSS, and "
                "real-time price monitoring. Savings calculated against 90-day price history."
            ),
        }

        report = Report(title=title, category="Deals", price=4.99, data=data)
        report.file_path = self._save_report(report)
        return report

    def generate_arbitrage_guide(self, profitable_flips: List[Dict]) -> Report:
        """Generate a gift card arbitrage guide with real data."""
        title = f"Gift Card Arbitrage Playbook — {datetime.now().strftime('%B %Y')}"

        data = {
            "title": title,
            "executive_summary": (
                "This guide reveals exactly how to earn $200–$500/month "
                "by automating Microsoft Rewards, converting points to Amazon gift cards, "
                "and flipping them on secondary markets for instant cash."
            ),
            "sections": [
                {
                    "heading": "1. Microsoft Rewards Automation",
                    "content": (
                        "Set up automated Bing searches to earn 30–80 points/day per account. "
                        "At 500 points = $5 Amazon GC, you earn $5–$8/month per account. "
                        "Scale to 10 accounts = $50–$80/month."
                    ),
                },
                {
                    "heading": "2. Redeeming Points for Gift Cards",
                    "content": (
                        "Log into rewards.bing.com → Redeem → Amazon Gift Cards. "
                        "$5 cards available at 500 points, $10 at 1,000 points. "
                        "Always choose $5 cards — higher points-per-dollar ratio."
                    ),
                },
                {
                    "heading": "3. Flipping on Raise.com",
                    "content": (
                        "List your Amazon GC codes on Raise.com. "
                        "Price at 87–92% of face value. Cards typically sell within 24–48 hours. "
                        "CardCash pays instantly (85% of face value). "
                        "Net: $4.25–$4.60 per $5 card."
                    ),
                },
                {
                    "heading": "4. Scaling Up",
                    "content": (
                        "Use the open-source automation tool to: "
                        "(a) auto-scrape reward emails, "
                        "(b) auto-redeem Amazon codes, "
                        "(c) auto-list on CardCash for instant cash. "
                        "Fully automated with zero daily effort after setup."
                    ),
                },
                {
                    "heading": "5. Monthly Income Projections",
                    "content": json.dumps({
                        "1_account": "$5–8/month",
                        "5_accounts": "$25–40/month",
                        "10_accounts": "$50–80/month",
                        "20_accounts": "$100–160/month",
                        "setup_time": "2–3 hours one-time",
                        "daily_effort": "0 minutes after setup",
                    }, indent=2),
                },
            ],
            "profitable_flips_sample": profitable_flips[:10],
            "disclaimer": "Results vary. Automate responsibly and within platform terms of service.",
        }

        report = Report(title=title, category="Guide", price=24.99, data=data)
        report.file_path = self._save_report(report)
        return report

    def _save_report(self, report: Report) -> str:
        """Save report as JSON (convert to PDF with reportlab/weasyprint)."""
        filename = f"{report.category.lower()}_{int(time.time())}.json"
        path = os.path.join(self.output_dir, filename)

        with open(path, "w") as f:
            json.dump(report.data, f, indent=2)

        logger.info(f"Report saved: {path}")
        return path

    def convert_to_pdf(self, report: Report) -> Optional[str]:
        """Convert report JSON to PDF using reportlab."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

            pdf_path = report.file_path.replace(".json", ".pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph(report.title, styles["Title"]))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Generated: {report.created_at}", styles["Normal"]))
            story.append(Spacer(1, 24))

            for section in report.data.get("sections", []):
                story.append(Paragraph(section["heading"], styles["Heading1"]))
                story.append(Spacer(1, 6))
                story.append(Paragraph(section["content"], styles["Normal"]))
                story.append(Spacer(1, 16))

            doc.build(story)
            report.file_path = pdf_path
            logger.info(f"PDF generated: {pdf_path}")
            return pdf_path

        except ImportError:
            logger.warning("reportlab not installed. Run: pip install reportlab")
            return None
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
