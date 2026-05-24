"""
Review Requester
================
Automates requesting product reviews from eBay/Amazon/Etsy buyers.
Positive reviews increase conversion rates by 15-30%.
Can also manage seller feedback removal requests.

Revenue boost: More reviews = more sales = more PayPal deposits.
PayPal: jayjay@collector.org (@digitalempiresk)
"""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from amz_tango_card_scraper.utils.logger import setup_logger

logger = setup_logger(logger_name=__name__)

PAYPAL_CONFIG = {
    "email": "jayjay@collector.org",
    "handle": "@digitalempiresk",
    "me_link": "https://paypal.me/digitalempiresk",
}

REVIEW_TEMPLATES = {
    "ebay": """Hi {name},

Thank you so much for your recent purchase of {product}!

I hope you're loving it. If you're happy with your order, would you mind leaving me a quick seller rating? It takes less than a minute and really helps my small shop grow.

⭐ Leave feedback here: {review_url}

If there's ANY issue with your order, please message me FIRST and I'll make it right — no questions asked.

Thanks again!
{seller_name}

P.S. Check out more deals: {paypal_me}""",

    "amazon": """Hi {name},

Thank you for ordering {product}!

If you enjoy the product, we'd be so grateful if you'd take 30 seconds to leave a review. Your honest feedback helps other shoppers and helps us keep making great products.

Leave your review: {review_url}

Any issues? Reply to this email — we'll fix it immediately.

Best,
{seller_name}""",

    "etsy": """Hi {name},

Thank you for your Etsy order of {product}! 🎉

I'd love to hear what you think! Leaving a review takes just a moment and means the world to small sellers like me.

⭐ Review here: {review_url}

Got a question or concern? Message me on Etsy and I'll respond within hours.

With gratitude,
{seller_name} | Digital Empire Shop""",
}


class ReviewRequester:
    """Sends review request emails to buyers after purchase."""

    def __init__(
        self,
        sender_email: str = "jayjay@collector.org",
        sender_name: str = "Digital Empire Shop",
        app_password: str = "",
        delay_days: int = 3,
    ):
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.app_password = app_password
        self.delay_days = delay_days
        self.sent: List[Dict] = []
        self.failed: List[Dict] = []

    def _build_email(self, platform: str, buyer_info: Dict) -> str:
        """Format review request email from template."""
        template = REVIEW_TEMPLATES.get(platform, REVIEW_TEMPLATES["ebay"])
        return template.format(
            name=buyer_info.get("name", "Valued Customer"),
            product=buyer_info.get("product", "your recent order"),
            review_url=buyer_info.get("review_url", ""),
            seller_name=self.sender_name,
            paypal_me=PAYPAL_CONFIG["me_link"],
        )

    def send_review_request(self, platform: str, buyer_info: Dict) -> bool:
        """
        Send a review request email to a buyer.

        Args:
            platform: "ebay", "amazon", or "etsy".
            buyer_info: Dict with name, email, product, review_url.

        Returns:
            True if sent successfully.
        """
        if not self.app_password:
            logger.warning("No Gmail app password configured — cannot send emails")
            return False

        to_email = buyer_info.get("email", "")
        if not to_email:
            return False

        subject_map = {
            "ebay": f"How did I do? Quick feedback for your {buyer_info.get('product', 'order')}",
            "amazon": f"Your thoughts on {buyer_info.get('product', 'your order')}?",
            "etsy": f"Love your new {buyer_info.get('product', 'purchase')}? ⭐",
        }

        subject = subject_map.get(platform, "How was your order?")
        body = self._build_email(platform, buyer_info)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.sender_email, self.app_password)
                smtp.send_message(msg)

            self.sent.append({"email": to_email, "platform": platform, "product": buyer_info.get("product")})
            logger.info(f"Review request sent: {to_email} ({platform})")
            return True

        except Exception as e:
            logger.error(f"Review request failed to {to_email}: {e}")
            self.failed.append({"email": to_email, "error": str(e)})
            return False

    def batch_send(self, platform: str, buyers: List[Dict], delay_seconds: float = 5.0) -> Dict:
        """Send review requests to a list of buyers."""
        sent = 0
        for buyer in buyers:
            if self.send_review_request(platform, buyer):
                sent += 1
            time.sleep(delay_seconds)

        summary = {"platform": platform, "total": len(buyers), "sent": sent, "failed": len(buyers) - sent}
        logger.info(f"Review campaign done: {sent}/{len(buyers)} sent on {platform}")
        return summary

    def get_stats(self) -> Dict:
        """Return review request statistics."""
        return {
            "total_sent": len(self.sent),
            "total_failed": len(self.failed),
            "sender": self.sender_email,
            "paypal_deposit_to": PAYPAL_CONFIG["handle"],
        }
